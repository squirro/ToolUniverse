"""Custom tool: differential_expression

Compares cancer vs normal tissue expression using EBI Expression Atlas.
Returns log2 fold change and p-value per gene from matched-tissue studies.
"""
from __future__ import annotations
import json, logging

log = logging.getLogger(__name__)


# Module-level cache of the EBI GxA experiment catalog. The full human catalog
# is ~2.6 MB / 4500+ experiments and the listing endpoint is slow and highly
# variable (15-40s, intermittently exceeding the request timeout). Downloading
# it on every differential_expression call made the tool time out and return
# zero experiments (then an empty "n_studies: 0" stub). Cache it process-wide so
# only the first call per process pays the cost — a module-level dict survives
# even if the Squirro runnable is rebuilt per turn, since the module imports once.
_CATALOG_CACHE: dict = {"data": None, "ts": 0.0}
_CATALOG_TTL = 12 * 3600  # seconds; the catalog changes rarely


def _get_experiments_catalog(timeout=60, retries=1):
    """Return the cached GxA human-experiment list, fetching if stale.

    Retries once on failure and serves a stale cache rather than returning
    nothing when a refresh fails.
    """
    import urllib.request as _ur
    import time as _time
    now = _time.time()
    cached = _CATALOG_CACHE["data"]
    if cached is not None and (now - _CATALOG_CACHE["ts"]) < _CATALOG_TTL:
        return cached
    url = "https://www.ebi.ac.uk/gxa/json/experiments?species=homo+sapiens"
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            exps = json.loads(_ur.urlopen(req, timeout=timeout).read()).get("experiments", [])
            _CATALOG_CACHE["data"] = exps
            _CATALOG_CACHE["ts"] = now
            return exps
        except Exception as e:
            last_err = e
            log.warning("gxa catalog fetch attempt %d/%d failed: %s", attempt + 1, retries + 1, e)
    if cached is not None:
        log.warning("gxa catalog refresh failed (%s); serving stale cache", last_err)
        return cached
    return []


def _is_cancer_indication(indication):
    """Check if the indication is cancer-related."""
    cancer_kws = ["cancer", "carcinoma", "adenocarcinoma", "tumor", "tumour",
                  "neoplasm", "malignant", "sarcoma", "lymphoma", "leukemia",
                  "leukaemia", "melanoma", "myeloma", "glioma", "glioblastoma",
                  "blastoma", "mesothelioma"]
    ind_l = indication.lower()
    return any(ck in ind_l for ck in cancer_kws)


# Map tissue keywords to cancer-specific synonyms that appear in experiment
# descriptions.  E.g. "brain cancer" should also match "glioma", "glioblastoma".
_CANCER_SYNONYMS = {
    "brain":    ["glioma", "glioblastoma", "astrocytoma", "medulloblastoma",
                 "meningioma", "brain tumor", "brain tumour", "brain neoplasm",
                 "neuroblastoma", "oligodendroglioma", "ependymoma"],
    "breast":   ["breast cancer", "breast carcinoma", "breast tumor",
                 "breast tumour", "mammary"],
    "lung":     ["lung cancer", "lung carcinoma", "lung adenocarcinoma",
                 "nsclc", "sclc", "mesothelioma", "pulmonary neoplasm"],
    "prostate": ["prostate cancer", "prostate carcinoma", "prostate adenocarcinoma",
                 "prostate tumor", "prostate tumour"],
    "colon":    ["colon cancer", "colorectal", "colon carcinoma", "colon adenocarcinoma",
                 "rectal cancer", "bowel cancer"],
    "liver":    ["hepatocellular", "liver cancer", "liver carcinoma", "hepatoblastoma",
                 "liver tumor", "liver tumour"],
    "kidney":   ["renal cell", "kidney cancer", "renal carcinoma", "wilms",
                 "kidney tumor", "kidney tumour"],
    "skin":     ["melanoma", "skin cancer", "basal cell", "squamous cell",
                 "cutaneous", "merkel cell"],
    "blood":    ["leukemia", "leukaemia", "lymphoma", "myeloma", "myeloid",
                 "lymphoblastic", "lymphocytic"],
    "ovar":     ["ovarian cancer", "ovarian carcinoma", "ovarian tumor",
                 "ovarian tumour"],
    "pancrea":  ["pancreatic cancer", "pancreatic carcinoma", "pancreatic adenocarcinoma",
                 "pancreatic ductal"],
    "stomach":  ["gastric cancer", "gastric carcinoma", "stomach cancer",
                 "stomach tumor"],
    "bladder":  ["bladder cancer", "urothelial", "bladder carcinoma",
                 "transitional cell"],
    "thyroid":  ["thyroid cancer", "thyroid carcinoma", "papillary thyroid",
                 "follicular thyroid"],
    "head":     ["head and neck", "oral cancer", "pharyngeal", "laryngeal",
                 "nasopharyngeal", "oropharyngeal"],
    "bone":     ["osteosarcoma", "bone cancer", "ewing sarcoma", "chondrosarcoma"],
    "cervix":   ["cervical cancer", "cervical carcinoma", "cervical neoplasm"],
    "uterus":   ["endometrial", "uterine cancer", "uterine carcinoma"],
    "esophag":  ["esophageal", "oesophageal", "esophagus cancer",
                 "barrett"],
}


# Row shape the downstream table pipeline reads. Kept in one place so the empty
# and populated paths cannot drift apart.
_EMPTY_ROW = {
    "median_log2fc": "", "best_p_value": "", "direction": "",
    "consensus": "0/0", "n_studies": 0, "overexpressed": "", "experiments": "",
}

# Why a zero came back. These were previously indistinguishable: both empty paths
# returned byte-identical rows, so a dead network read as a biological negative.
_STATUS_DETAIL = {
    "no_matching_studies": (
        "No GxA study survived the filter. This is NOT evidence the gene is "
        "unchanged — it means no human differential study matching these terms "
        "also named a normal/control/adjacent comparison."
    ),
    "studies_found_fetch_failed": (
        "Studies DID match, but every analytics fetch failed. This is a transport "
        "failure, NOT a biological result, and is not evidence of anything. Retry "
        "before drawing any conclusion."
    ),
    "gene_not_measured": (
        "Studies matched and parsed, but this gene was not measured in them. This "
        "is NOT evidence the gene is unchanged."
    ),
    "catalog_unavailable": (
        "The GxA experiment catalogue could not be fetched, so no filtering "
        "happened at all. This is a transport failure, not a result."
    ),
}

_WIDEN_WITH = (
    "Pass experiment=<GxA accession> to bypass the description filter entirely "
    "(it is applied only when no experiment is named), or retry with a broader "
    "indication term. See `rejected` in diagnostics for accessions that matched "
    "the search term but were dropped by a later filter."
)


def empty_rows(genes, status, funnel):
    """Zero-result rows that say WHICH zero this is, and how to widen.

    The pipeline's original columns are preserved verbatim so downstream table
    consumers keep working; the diagnostic fields are additive.
    """
    diagnostics = json.dumps(
        {
            "search_terms": funnel.get("search_terms", []),
            "stages": funnel.get("stages", {}),
            # Capped: a rejection list is for reading, not for reprocessing.
            "rejected": funnel.get("rejected", [])[:10],
            "rejected_total": len(funnel.get("rejected", [])),
        },
        default=str,
    )
    return [
        {
            "_input_gene_name": g,
            **_EMPTY_ROW,
            "status": status,
            "status_detail": _STATUS_DETAIL.get(status, ""),
            "widen_with": _WIDEN_WITH,
            "diagnostics": diagnostics,
        }
        for g in genes
    ]


def filter_experiments(experiments, indication):
    """Apply the description filter, returning ``(candidates, funnel)``.

    Split out of ``gxa_find_experiments`` so the funnel is observable. The filter
    rules and their ORDER are unchanged -- this is strictly about reporting what
    was dropped and by which rule, never about loosening anything.

    Only candidates that matched the search term are recorded in ``rejected``:
    everything before that stage is the other 4,000-odd experiments in the
    catalogue, which is noise rather than a near miss.
    """
    ind_l = indication.lower()
    is_cancer = _is_cancer_indication(ind_l)

    # Extract the tissue keyword by stripping common cancer suffixes
    tissue_kw = ind_l
    for strip in ["cancer", "carcinoma", "adenocarcinoma", "tumor", "tumour",
                  "neoplasm", "malignant"]:
        tissue_kw = tissue_kw.replace(strip, "")
    tissue_kw = " ".join(tissue_kw.split()).strip()

    # Build search terms: tissue keyword + cancer-specific synonyms
    search_terms = [tissue_kw] if tissue_kw else []
    if is_cancer:
        for prefix, synonyms in _CANCER_SYNONYMS.items():
            if prefix in tissue_kw or prefix in ind_l:
                search_terms.extend(synonyms)
                break
        # Also add the full indication as a search term
        search_terms.append(ind_l)

    cancer_desc_kws = ["cancer", "carcinoma", "tumor", "tumour", "neoplasm",
                       "malignant", "sarcoma", "lymphoma", "leukemia", "leukaemia",
                       "melanoma", "myeloma", "glioma", "glioblastoma", "blastoma"]

    normal_kws = ["normal", "non-tumor", "non-tumour", "adjacent", "healthy",
                  "matched normal", "control", "versus", " vs "]
    exclude_kws = ["cell line", "knockdown", "sirna", "shrna", "knockout",
                   "transgenic", "mouse", "mice", "murine", "overexpression",
                   "ectopic", "resistant", "treated with", "treatment", "drug",
                   "inhibitor", "agonist", "antagonist", "stromal",
                   "epithelial cells", "lymphocyte", "chemopreventive",
                   "phytochemical", "xenograft", "organoid", "spheroid"]
    funnel = {
        "indication_as_searched": ind_l,
        "search_terms": [st for st in search_terms if st],
        "stages": {
            "catalog": len(experiments), "differential": 0, "human": 0,
            "term_match": 0, "normal_comparison": 0, "not_excluded": 0,
            "cancer_word": 0, "final": 0,
        },
        "rejected": [],
    }
    stages = funnel["stages"]

    candidates = []
    for exp in experiments:
        etype = exp.get("experimentType", "")
        if "differential" not in etype.lower():
            continue
        stages["differential"] += 1
        # Only human experiments
        species = exp.get("species", "")
        if isinstance(species, str) and "homo sapiens" not in species.lower():
            continue
        stages["human"] += 1
        desc_raw = exp.get("experimentDescription", "")
        desc = desc_raw.lower()
        # Must match at least one search term
        if not any(st in desc for st in search_terms if st):
            continue
        stages["term_match"] += 1

        # Past this point a candidate is a NEAR MISS -- it is about the right
        # subject -- so every drop is recorded with the rule that caused it.
        def _reject(rule):
            funnel["rejected"].append({
                "accession": exp.get("experimentAccession", ""),
                "description": desc_raw,
                "dropped_by": rule,
            })

        if not any(nk in desc for nk in normal_kws):
            _reject("no_normal_comparison")
            continue
        stages["normal_comparison"] += 1
        if any(ek in desc for ek in exclude_kws):
            _reject("excluded_keyword")
            continue
        stages["not_excluded"] += 1
        # For cancer indications, require a cancer-related word in description
        # to avoid matching psychiatric/neurological studies
        if is_cancer and not any(ck in desc for ck in cancer_desc_kws):
            _reject("no_cancer_word")
            continue
        stages["cancer_word"] += 1
        score = 1
        if "rnaseq" in etype.lower() or "rna-seq" in desc:
            score += 5
        if "tissue" in desc or "sample" in desc or "patient" in desc:
            score += 3
        # Boost if description contains exact indication
        if ind_l in desc:
            score += 4
        # Boost if cancer synonym matches
        if is_cancer:
            for prefix, synonyms in _CANCER_SYNONYMS.items():
                if prefix in tissue_kw:
                    if any(syn in desc for syn in synonyms):
                        score += 3
                    break
        candidates.append((exp["experimentAccession"], exp.get("experimentDescription", ""), score))
    candidates.sort(key=lambda x: -x[2])
    stages["final"] = len(candidates)
    return candidates, funnel


def gxa_find_experiments_with_funnel(indication, timeout=60):
    """``filter_experiments`` over the live catalogue, keeping the funnel."""
    experiments = _get_experiments_catalog(timeout=timeout)
    if not experiments:
        log.warning("gxa_find_experiments: empty experiment catalog")
        return [], {
            "indication_as_searched": indication.lower(),
            "search_terms": [],
            "stages": {"catalog": 0, "final": 0},
            "rejected": [],
            "catalog_unavailable": True,
        }
    return filter_experiments(experiments, indication)


def gxa_find_experiments(indication, timeout=60):
    """Search EBI Expression Atlas for cancer vs normal experiments.

    Returns all matching (accession, description, score) sorted by relevance.
    """
    candidates, _ = gxa_find_experiments_with_funnel(indication, timeout=timeout)
    return candidates


def gxa_fetch_analytics(accession, timeout=60):
    """Fetch full differential expression analytics from Expression Atlas.

    Handles both RNA-seq format (Gene ID, Gene Name, p-value, log2fc, ...)
    and Microarray format (Gene ID, Gene Name, Design Element, p-value, t-stat, log2fc, ...).
    Microarray files may contain multiple comparison triplets — we take the first.

    Returns (list of dicts, comparison_string).
    """
    import urllib.request as _ur
    url = (f"https://www.ebi.ac.uk/gxa/experiments-content/{accession}"
           f"/resources/DifferentialSecondaryDataFiles.RnaSeq/analytics")
    try:
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = _ur.urlopen(req, timeout=timeout)
        data = resp.read().decode()
    except Exception as e:
        url2 = url.replace("RnaSeq", "Microarray")
        try:
            req2 = _ur.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
            resp2 = _ur.urlopen(req2, timeout=timeout)
            data = resp2.read().decode()
        except Exception as e2:
            log.warning("gxa_fetch_analytics(%s): both RnaSeq and Microarray failed: %s / %s", accession, e, e2)
            return [], ""
    lines = data.strip().split("\n")
    if len(lines) < 2:
        return [], ""
    header = lines[0]
    cols = header.split("\t")

    # Detect column layout by finding the first ".p-value" column
    pval_idx = fc_idx = None
    comparison = ""
    for i, c in enumerate(cols):
        if ".p-value" in c:
            pval_idx = i
            # log2foldchange is typically 2 columns after p-value (p-value, t-stat, log2fc)
            # but check explicitly
            for j in range(i + 1, min(i + 3, len(cols))):
                if "log2foldchange" in cols[j].lower() or "foldchange" in cols[j].lower():
                    fc_idx = j
                    break
            if fc_idx is None and i + 2 < len(cols):
                fc_idx = i + 2  # fallback: assume p-value, t-stat, log2fc triplet
            comparison = c.rsplit(".p-value", 1)[0].strip("'\"")
            break

    # Fallback for RNA-seq format: Gene ID, Gene Name, p-value, log2fc
    if pval_idx is None:
        pval_idx = 2
        fc_idx = 3
        if len(cols) >= 3:
            comparison = cols[2].rsplit(".p-value", 1)[0].strip("'\"")

    results = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) <= max(pval_idx, fc_idx or 0):
            continue
        gene_id, gene_name = parts[0], parts[1]
        try:
            pval = float(parts[pval_idx]) if parts[pval_idx] != "NA" else None
        except (ValueError, IndexError):
            pval = None
        try:
            log2fc = float(parts[fc_idx]) if parts[fc_idx] != "NA" else None
        except (ValueError, IndexError):
            log2fc = None
        results.append({
            "gene_id": gene_id, "gene_name": gene_name,
            "p_value": pval, "log2fc": log2fc,
        })
    return results, comparison


def exec_differential_expression(arguments, input_table, output_table, db_path):
    """Compare cancer vs normal tissue expression using EBI Expression Atlas.

    Fetches ALL matching experiments for the indication, aggregates log2FC
    per gene across studies (median + direction consensus).
    """
    import sqlite3, re
    from concurrent.futures import ThreadPoolExecutor as _TPE, as_completed
    from statistics import median

    indication = arguments.get("indication", arguments.get("disease_name", arguments.get("cancer", "")))
    if not indication:
        raise ValueError("'indication' parameter required (e.g., 'prostate cancer')")

    # Clean indication for experiment search
    clean_indication = re.sub(r"ENSG\d{11}", "", indication)
    clean_indication = re.sub(r"\bvs\b.*$", "", clean_indication, flags=re.IGNORECASE)
    clean_indication = re.sub(r"\b(in|for|of|the|vs|normal|expression|differential)\b", "", clean_indication, flags=re.IGNORECASE)
    clean_indication = " ".join(clean_indication.split()).strip()
    if not clean_indication:
        clean_indication = indication

    accession = arguments.get("experiment", "")
    _funnel = {}
    if accession:
        experiments = [(accession, "", 0)]
    else:
        experiments, _funnel = gxa_find_experiments_with_funnel(clean_indication)
        if not experiments:
            log.warning("exec_de: no GxA experiments found for '%s' — returning empty rows", clean_indication)
            # Extract query genes for empty-row output rather than crashing
            _empty_genes: list[str] = []
            gene_arg = arguments.get("gene", arguments.get("gene_name", ""))
            if gene_arg:
                _empty_genes = [g.strip() for g in gene_arg.split(",") if g.strip()]
            elif input_table:
                try:
                    _conn = sqlite3.connect(db_path, timeout=30)
                    _all_cols = [d[0] for d in _conn.execute(
                        f"SELECT * FROM [{input_table}] LIMIT 0").description]
                    _rows = [dict(zip(_all_cols, r)) for r in _conn.execute(
                        f"SELECT * FROM [{input_table}]").fetchall()]
                    _conn.close()
                    for _cand in ["approvedSymbol", "approvedsymbol", "gene_symbol",
                                  "gene_name", "symbol", "gene", "_input_gene_name"]:
                        if any(c.lower() == _cand.lower() for c in _all_cols):
                            _gcol = next(c for c in _all_cols if c.lower() == _cand.lower())
                            _empty_genes = [r[_gcol] for r in _rows if r.get(_gcol)]
                            break
                except Exception:
                    pass
            if not _empty_genes:
                _empty_genes = [clean_indication]
            return empty_rows(
                _empty_genes,
                status=(
                    "catalog_unavailable"
                    if _funnel.get("catalog_unavailable")
                    else "no_matching_studies"
                ),
                funnel=_funnel,
            )
    log.info("exec_de: indication='%s', %d experiments found", indication, len(experiments))

    # Fetch analytics from all experiments in parallel
    all_analytics = {}

    def _fetch(acc_desc_score):
        acc, desc, _ = acc_desc_score
        analytics, comparison = gxa_fetch_analytics(acc)
        return acc, analytics, comparison

    with _TPE(max_workers=4) as pool:
        futures = {pool.submit(_fetch, e): e[0] for e in experiments}
        for future in as_completed(futures):
            acc, analytics, comparison = future.result()
            if analytics:
                all_analytics[acc] = (analytics, comparison)
                log.info("exec_de: %s -> %d genes", acc, len(analytics))

    if not all_analytics:
        log.warning("exec_de: all analytics fetches failed for '%s' — returning empty rows", indication)
        gene_arg = arguments.get("gene", arguments.get("gene_name", ""))
        _fallback = [g.strip() for g in gene_arg.split(",") if g.strip()] if gene_arg else [clean_indication]
        # NOT the same zero as "no study matched": these studies DID match and we
        # failed to fetch them. Reporting that as a biological negative was the
        # defect (DSR-629).
        _failed = dict(_funnel)
        _failed["experiments_matched"] = [e[0] for e in experiments]
        return empty_rows(_fallback, status="studies_found_fetch_failed", funnel=_failed)

    # Build per-gene aggregation
    gene_data = {}
    gene_id_map = {}
    for acc, (analytics, _) in all_analytics.items():
        for row in analytics:
            gn = (row.get("gene_name") or "").upper()
            gid = row.get("gene_id", "")
            if not gn:
                continue
            if gid:
                gene_id_map[gid] = gn
            if row["log2fc"] is not None:
                gene_data.setdefault(gn, []).append({
                    "log2fc": row["log2fc"],
                    "p_value": row["p_value"],
                    "accession": acc,
                })

    # Determine query genes
    query_genes = []
    if input_table:
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            all_cols = [d[0] for d in conn.execute(f"SELECT * FROM [{input_table}] LIMIT 0").description]
            rows = [dict(zip(all_cols, r)) for r in conn.execute(f"SELECT * FROM [{input_table}]").fetchall()]
        except sqlite3.OperationalError as e:
            conn.close()
            raise ValueError(f"Input table '{input_table}' not found: {e}")
        conn.close()
        gene_col = ensembl_col = None
        for candidate in ["approvedSymbol", "approvedsymbol", "gene_symbol", "gene_name", "symbol", "gene",
                           "target.approvedSymbol", "_input_gene_name"]:
            if any(c.lower() == candidate.lower() for c in all_cols):
                gene_col = next(c for c in all_cols if c.lower() == candidate.lower())
                break
        for candidate in ["target.id", "ensembl_id", "ensemblId", "id", "gene_id"]:
            if any(c.lower() == candidate.lower() for c in all_cols):
                ensembl_col = next(c for c in all_cols if c.lower() == candidate.lower())
                break
        for row in rows:
            g = (row.get(gene_col, "") or "").strip() if gene_col else ""
            e = (row.get(ensembl_col, "") or "").strip() if ensembl_col else ""
            query_genes.append((g or e, g or e))
    else:
        gene_arg = arguments.get("gene", arguments.get("gene_name", arguments.get("ensembl_id", "")))
        if not gene_arg:
            ens_match = re.search(r"(ENSG\d{11})", indication)
            if ens_match:
                gene_arg = ens_match.group(1)
            else:
                words = indication.split()
                for w in words:
                    if re.match(r"^[A-Z][A-Z0-9]{1,10}$", w) and w not in ("AND", "OR", "NOT", "THE", "FOR", "IN"):
                        gene_arg = w
                        break
        if gene_arg:
            # Support comma-separated gene lists (consistent with other SR tools)
            query_genes = [(g.strip(), g.strip()) for g in gene_arg.split(",") if g.strip()]
        else:
            log.info("exec_de: no input table or gene specified, returning top DE genes")
            query_genes = None

    # Aggregation helper
    exp_names = "; ".join(all_analytics.keys())

    def _agg(display_name, measurements):
        if measurements:
            fc_values = [m["log2fc"] for m in measurements]
            p_values = [m["p_value"] for m in measurements if m["p_value"] is not None]
            median_fc = median(fc_values)
            min_p = min(p_values) if p_values else None
            n_up = sum(1 for f in fc_values if f > 0)
            n_down = sum(1 for f in fc_values if f < 0)
            n_studies = len(fc_values)
            return {
                "_input_gene_name": display_name,
                "median_log2fc": round(median_fc, 3),
                "best_p_value": f"{min_p:.2e}" if min_p is not None else "",
                "direction": "up" if n_up > n_down else ("down" if n_down > n_up else "mixed"),
                "consensus": f"{max(n_up, n_down)}/{n_studies}",
                "n_studies": n_studies,
                "overexpressed": "yes" if median_fc > 0 else "no",
                "experiments": exp_names,
                "status": "ok",
                "status_detail": "",
                "widen_with": "",
            }
        # Studies matched AND parsed; this gene was simply not among them. Before
        # DSR-629 this was distinguishable from "no study matched" only by whether
        # `experiments` happened to be non-empty, which nothing documented.
        return {
            "_input_gene_name": display_name,
            "median_log2fc": "", "best_p_value": "", "direction": "",
            "consensus": "0/0", "n_studies": 0, "overexpressed": "",
            "experiments": exp_names,
            "status": "gene_not_measured",
            "status_detail": _STATUS_DETAIL["gene_not_measured"],
            "widen_with": _WIDEN_WITH,
        }

    results = []
    if query_genes is None:
        ranked = sorted(gene_data.items(),
            key=lambda kv: min((m["p_value"] for m in kv[1] if m["p_value"] is not None), default=1))
        for gn_key, meas in ranked:
            results.append(_agg(gn_key, meas))
    else:
        for gene_key, display in query_genes:
            gn_upper = gene_key.upper()
            meas = gene_data.get(gn_upper) or gene_data.get(gene_id_map.get(gene_key, ""), [])
            results.append(_agg(display, meas))

    matched = sum(1 for r in results if r.get("n_studies"))
    log.info("exec_de: %d/%d genes matched across %d experiments",
             matched, len(results), len(all_analytics))
    return results
