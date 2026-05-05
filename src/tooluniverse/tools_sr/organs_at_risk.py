"""Custom tool: organs_at_risk

Identifies normal tissues with high expression of a target gene,
flagging toxicity risk for theranostics (radioligand therapy, ADCs).
Uses EBI Expression Atlas baseline experiment E-MTAB-2836 (HPA RNA-seq,
29 human tissues) for normal tissue TPM values.

Score 0-1 where lower = fewer organs at risk (better safety profile).
"""
from __future__ import annotations
import json, logging, re

log = logging.getLogger(__name__)

# Organ risk tiers for theranostics toxicity
# Keywords matched by substring against GxA tissue column names (lowercased).
# High-risk: radiation/drug damage here is life-threatening or dose-limiting
_HIGH_RISK_KEYWORDS = ["cerebral cortex", "bone marrow", "heart", "liver", "kidney"]
# Moderate-risk: significant but more recoverable toxicity
_MODERATE_RISK_KEYWORDS = [
    "colon", "duodenum", "small intestine", "stomach", "esophag",
    "lung", "spleen", "pancreas",
]


def _organ_weight(tissue_name):
    """Return risk weight for a tissue (3=high, 2=moderate, 1=low)."""
    t = tissue_name.lower()
    for kw in _HIGH_RISK_KEYWORDS:
        if kw in t:
            return 3.0
    for kw in _MODERATE_RISK_KEYWORDS:
        if kw in t:
            return 2.0
    return 1.0


def _is_high_risk(tissue_name):
    t = tissue_name.lower()
    return any(kw in t for kw in _HIGH_RISK_KEYWORDS)


# Map indication keywords to tissue-matching substrings.
# resolve_target_tissue will match these against actual GxA column names
# (e.g. "prostate" matches "prostate gland", "skin" matches "zone of skin").
_INDICATION_TISSUE_MAP = {
    "prostate": "prostate",
    "breast": "endometri",  # closest in HPA panel
    "lung": "lung",
    "colon": "colon",
    "colorectal": "colon",
    "liver": "liver",
    "hepatocellular": "liver",
    "kidney": "kidney",
    "renal": "kidney",
    "pancrea": "pancreas",
    "stomach": "stomach",
    "gastric": "stomach",
    "ovari": "ovary",
    "endometri": "endometri",
    "thyroid": "thyroid",
    "bladder": "urinary bladder",
    "esophag": "esophag",
    "brain": "cerebral cortex",
    "glioblastoma": "cerebral cortex",
    "bone": "bone marrow",
    "lymphoma": "lymph node",
    "leukemia": "bone marrow",
    "skin": "skin",
    "melanoma": "skin",
    "testicular": "testis",
    "adrenal": "adrenal",
    "salivary": "saliva",
    "neuroendocrine": "stomach",  # NETs commonly arise in GI tract
    "cervical": "cervix",
    "head and neck": "saliva",
    "glioma": "cerebral cortex",
    "astrocytoma": "cerebral cortex",
    "meningioma": "cerebral cortex",
    "neuroblastoma": "adrenal",
    "sarcoma": "bone marrow",
    "myeloma": "bone marrow",
    "cholangiocarcinoma": "liver",
    "mesothelioma": "lung",
    "retinoblastoma": "cerebral cortex",
    "pheochromocytoma": "adrenal",
    "carcinoid": "stomach",
    "thymoma": "thymus",
    "epilepsy": "cerebral cortex",
}

# Default baseline experiment (HPA RNA-seq, 29 tissues)
_DEFAULT_EXPERIMENT = "E-MTAB-2836"
# In-process cache: avoids re-downloading the ~40K-row TSV on every call
# when exec_organs_at_risk is called multiple times in the same Python process.
_BASELINE_CACHE: dict = {}  # accession -> (tissue_cols, gene_data)


def gxa_fetch_baseline(accession=_DEFAULT_EXPERIMENT, timeout=120):
    """Download full baseline expression matrix from EBI Expression Atlas.

    Returns (tissue_columns: list[str], gene_data: dict[str, dict[str, float]])
    where gene_data maps gene_symbol -> {tissue: tpm, ...}.
    Result is cached in-process to avoid repeated downloads within a session.
    """
    if accession in _BASELINE_CACHE:
        log.debug("gxa_fetch_baseline: cache hit for %s", accession)
        return _BASELINE_CACHE[accession]

    import urllib.request as _ur

    url = (f"https://www.ebi.ac.uk/gxa/experiments-content/{accession}"
           f"/resources/ExperimentDownloadSupplier.RnaSeqBaseline/tpmss.tsv")
    log.info("gxa_fetch_baseline: downloading %s", url)
    try:
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = _ur.urlopen(req, timeout=timeout)
        data = resp.read().decode("utf-8")
    except Exception as e:
        log.warning("gxa_fetch_baseline(%s): failed: %s", accession, e)
        return [], {}

    lines = data.strip().split("\n")
    # Skip comment lines (start with #)
    data_lines = [l for l in lines if not l.startswith("#")]
    if len(data_lines) < 2:
        log.warning("gxa_fetch_baseline: no data rows in %s", accession)
        return [], {}

    header = data_lines[0].split("\t")
    # Columns: Gene ID, Gene Name, tissue1, tissue2, ...
    tissue_cols = [h.strip() for h in header[2:]]
    log.info("gxa_fetch_baseline: %d tissues: %s", len(tissue_cols), tissue_cols[:5])

    gene_data = {}
    for line in data_lines[1:]:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        gene_id = parts[0].strip()
        gene_name = parts[1].strip().upper()
        tpm_values = {}
        for i, tissue in enumerate(tissue_cols):
            raw = parts[i + 2].strip() if i + 2 < len(parts) else ""
            try:
                tpm_values[tissue.lower()] = float(raw)
            except (ValueError, TypeError):
                tpm_values[tissue.lower()] = 0.0
        # Index by both gene symbol and Ensembl ID
        if gene_name:
            gene_data[gene_name] = tpm_values
        if gene_id:
            gene_data[gene_id] = tpm_values

    log.info("gxa_fetch_baseline: parsed %d gene entries", len(gene_data) // 2)
    result = ([t.lower() for t in tissue_cols], gene_data)
    _BASELINE_CACHE[accession] = result
    return result


def resolve_target_tissue(indication, tissue_cols):
    """Map an indication string to the best-matching GxA tissue column.

    Uses substring matching: _INDICATION_TISSUE_MAP values are substrings
    matched against actual GxA column names (e.g. "prostate" matches
    "prostate gland").

    Returns the tissue column name (lowercase) or None.
    """
    ind_lower = indication.lower()
    # Try the indication→tissue keyword map first
    for keyword, tissue_substr in _INDICATION_TISSUE_MAP.items():
        if keyword in ind_lower:
            # Find a GxA column containing the tissue substring
            for tc in tissue_cols:
                if tissue_substr in tc:
                    return tc
    # Fallback: try matching indication words against tissue columns
    words = re.findall(r"[a-z]+", ind_lower)
    for w in words:
        if len(w) < 4:
            continue
        for tc in tissue_cols:
            if w in tc:
                return tc
    return None


def assess_organs_at_risk(gene_symbol, tissue_tpms, target_tissue, indication):
    """Score organ risk for theranostics.

    Args:
        gene_symbol: gene name
        tissue_tpms: dict of tissue -> TPM
        target_tissue: the tissue to compare against (from indication)
        indication: original indication string

    Returns dict with risk score and details.
    """
    if not tissue_tpms:
        return {
            "organ_risk_score": 0.5,
            "target_tissue_nTPM": "",
            "at_risk_organs": "",
            "high_risk_organs": "",
            "safe_organs_count": 0,
            "total_organs_checked": 0,
            "evidence": ["no expression data"],
        }

    target_tpm = tissue_tpms.get(target_tissue, 0.0) if target_tissue else 0.0

    # If target tissue has no expression, use max expression as reference
    if target_tpm <= 0:
        target_tpm = max(tissue_tpms.values()) if tissue_tpms else 1.0

    # Threshold: flag tissues with expression > 50% of target
    threshold = target_tpm * 0.5

    at_risk = []
    high_risk = []
    weighted_risk_count = 0.0
    total_weight = 0.0

    for tissue, tpm in tissue_tpms.items():
        if tissue == target_tissue:
            continue  # skip the target tissue itself

        weight = _organ_weight(tissue)
        total_weight += weight

        if tpm >= threshold:
            at_risk.append((tissue, tpm, weight))
            weighted_risk_count += weight
            if _is_high_risk(tissue):
                high_risk.append(f"{tissue} ({tpm:.1f})")

    # Score = weighted at-risk count / total weight
    score = weighted_risk_count / total_weight if total_weight > 0 else 0.0
    score = round(min(1.0, score), 3)

    safe_count = sum(1 for t in tissue_tpms if t != target_tissue) - len(at_risk)

    # Sort at-risk organs by weighted severity (weight * tpm)
    at_risk.sort(key=lambda x: -(x[2] * x[1]))
    at_risk_str = "; ".join(f"{t} ({tpm:.1f})" for t, tpm, _ in at_risk)

    evidence = []
    if target_tissue:
        evidence.append(f"target tissue: {target_tissue} ({target_tpm:.1f} TPM)")
    evidence.append(f"{len(at_risk)} organs above 50% threshold ({threshold:.1f} TPM)")
    if high_risk:
        evidence.append(f"high-risk: {', '.join(high_risk)}")

    return {
        "organ_risk_score": score,
        "target_tissue_nTPM": f"{target_tpm:.1f}",
        "at_risk_organs": at_risk_str,
        "high_risk_organs": "; ".join(high_risk),
        "safe_organs_count": safe_count,
        "total_organs_checked": len(tissue_tpms) - (1 if target_tissue in tissue_tpms else 0),
        "evidence": evidence,
    }


def fetch_gene_aliases(gene_symbol, timeout=10):
    """Fetch gene aliases via MyGene.info REST API.

    Used when a gene symbol is not found in GxA (e.g. NIS → SLC5A5).
    Returns a list of alias symbols (may be empty on failure).
    """
    import requests as _rq
    try:
        r = _rq.get(
            "https://mygene.info/v3/query",
            params={
                "q": f"symbol:{gene_symbol}",
                "species": "human",
                "fields": "symbol,alias",
                "size": "1",
            },
            timeout=timeout,
        )
        r.raise_for_status()
        hits = r.json().get("hits") or []
        if not hits:
            return []
        hit = hits[0]
        raw = hit.get("alias", [])
        # alias can be a str (single alias) or list[str]
        if isinstance(raw, str):
            return [raw]
        return list(raw)
    except Exception as e:
        log.warning("fetch_gene_aliases(%s): %s", gene_symbol, e)
        return []


def exec_organs_at_risk(arguments, input_table, output_table, db_path):
    """Identify organs at risk for theranostics. Downloads EBI Expression Atlas
    baseline expression, scores each gene's normal tissue expression profile."""
    import sqlite3

    indication = arguments.get("indication", arguments.get("disease_name", arguments.get("cancer", "")))
    if not indication:
        raise ValueError("'indication' parameter required (e.g., 'prostate cancer')")

    experiment = arguments.get("experiment", _DEFAULT_EXPERIMENT)

    genes = []
    if input_table:
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            all_cols = [d[0] for d in
                        conn.execute(f"SELECT * FROM [{input_table}] LIMIT 0").description]
            rows = [dict(zip(all_cols, r))
                    for r in conn.execute(f"SELECT * FROM [{input_table}]").fetchall()]
        except sqlite3.OperationalError as e:
            conn.close()
            raise ValueError(f"Input table '{input_table}' not found: {e}")
        conn.close()
        gene_col = None
        for candidate in ["approvedSymbol", "approvedsymbol", "gene_symbol",
                           "gene_name", "symbol", "gene",
                           "target.approvedSymbol", "_input_gene_name"]:
            if any(c.lower() == candidate.lower() for c in all_cols):
                gene_col = next(c for c in all_cols if c.lower() == candidate.lower())
                break
        if gene_col:
            genes = [r[gene_col] for r in rows if r.get(gene_col)]

    # Standalone mode: extract gene from arguments
    if not genes:
        gene_arg = arguments.get("gene", arguments.get("gene_name",
                   arguments.get("target", arguments.get("symbol", ""))))
        if gene_arg:
            genes = [g.strip() for g in gene_arg.split(",") if g.strip()]
    # Deduplicate preserving order (prevents redundant API calls + duplicate output rows)
    genes = list(dict.fromkeys(genes))

    if not genes:
        raise ValueError("No genes found — provide an input table or 'gene' parameter")
    log.info("exec_organs_at_risk: %d genes, indication='%s', experiment=%s",
             len(genes), indication, experiment)

    # Download baseline expression (one HTTP call for all genes)
    tissue_cols, gene_expression = gxa_fetch_baseline(experiment)
    if not gene_expression:
        raise RuntimeError(f"Failed to download baseline expression from {experiment}")

    # Resolve target tissue from indication
    target_tissue = resolve_target_tissue(indication, tissue_cols)
    log.info("exec_organs_at_risk: target tissue='%s' for indication='%s'",
             target_tissue, indication)

    results = []
    for gene in genes:
        tpms = gene_expression.get(gene.upper(), {})
        # If primary symbol not in GxA, try aliases from MyGene.info
        if not tpms:
            aliases = fetch_gene_aliases(gene)
            for alias in aliases:
                tpms = gene_expression.get(alias.upper(), {})
                if tpms:
                    log.info("exec_organs_at_risk: resolved %s → %s via MyGene alias", gene, alias)
                    break
        assessment = assess_organs_at_risk(gene, tpms, target_tissue, indication)
        results.append({
            "_input_gene_name": gene,
            "organ_risk_score": assessment["organ_risk_score"],
            "target_tissue": target_tissue or "unknown",
            "target_tissue_nTPM": assessment["target_tissue_nTPM"],
            "at_risk_organs": assessment["at_risk_organs"],
            "high_risk_organs": assessment["high_risk_organs"],
            "safe_organs_count": str(assessment["safe_organs_count"]),
            "total_organs_checked": str(assessment["total_organs_checked"]),
            "organ_risk_details": "; ".join(assessment["evidence"]),
        })

    results.sort(key=lambda r: float(r["organ_risk_score"]))

    log.info("exec_organs_at_risk: %d/%d genes scored", len(results), len(genes))
    return results
