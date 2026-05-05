"""Custom tool: shedding_risk

Assesses whether a target is at risk of ectodomain shedding or secretion.
Score 0-1 where lower = better for drug targeting (low shedding risk).

Data sources:
- UniProt: subcellular location (Secreted flag), signal peptide, TM domains,
  GPI anchor, domain annotations for protease substrates
- EPMC: literature count for shedding/cleavage evidence
"""
from __future__ import annotations
import json, logging, re

log = logging.getLogger(__name__)

# Proteases known to cleave ectodomains
_SHEDDASE_KEYWORDS = [
    "adam10", "adam17", "tace", "mmp", "matrix metalloproteinase",
    "furin", "proprotein convertase", "bace1", "bace2",
    "gamma-secretase", "presenilin", "rhomboid",
]


def fetch_uniprot_shedding_data(gene_symbol, timeout=20):
    """Fetch UniProt data relevant to shedding risk assessment.

    Returns dict with: is_secreted, has_signal_peptide, has_tm, is_gpi,
    domain_annotations (text), subcellular_locations (list).
    """
    import requests as _rq
    try:
        r = _rq.get("https://rest.uniprot.org/uniprotkb/search", params={
            "query": f"gene_exact:{gene_symbol} AND organism_id:9606 AND reviewed:true",
            "size": "1",
            "fields": ("accession,cc_subcellular_location,ft_transmem,"
                       "ft_signal,ft_lipid,ft_domain,keyword"),
        }, headers={"Accept": "application/json"}, timeout=timeout)
        r.raise_for_status()
        entries = r.json().get("results") or []
        if not entries:
            return None
        entry = entries[0]

        # Keywords
        keywords = [kw.get("name", "").lower() for kw in entry.get("keywords") or []]
        is_secreted = "secreted" in keywords

        # Signal peptide
        features = entry.get("features") or []
        has_signal_peptide = any(f.get("type") == "Signal" for f in features)

        # Transmembrane
        tm_features = [f for f in features if f.get("type") == "Transmembrane"]
        has_tm = len(tm_features) > 0

        # GPI anchor
        lipid_features = [f for f in features if f.get("type") == "Lipidation"]
        is_gpi = any("gpi" in (f.get("description") or "").lower() for f in lipid_features)

        # Subcellular location comments
        sub_locs = []
        for comment in entry.get("comments") or []:
            if comment.get("commentType") == "SUBCELLULAR LOCATION":
                for sl in comment.get("subcellularLocations") or []:
                    loc_val = (sl.get("location") or {}).get("value", "")
                    if loc_val:
                        sub_locs.append(loc_val)
                    topo_val = (sl.get("topology") or {}).get("value", "")
                    if topo_val:
                        sub_locs.append(topo_val)
        is_gpi = is_gpi or any("gpi" in s.lower() for s in sub_locs)
        secreted_in_loc = any("secreted" in s.lower() for s in sub_locs)

        # Domain annotations — look for sheddase substrates
        domain_features = [f for f in features if f.get("type") == "Domain"]
        domain_texts = " ".join(
            (f.get("description") or "") for f in domain_features
        ).lower()

        return {
            "is_secreted": is_secreted or secreted_in_loc,
            "has_signal_peptide": has_signal_peptide,
            "has_tm": has_tm,
            "is_gpi": is_gpi,
            "tm_count": len(tm_features),
            "domain_text": domain_texts,
            "subcellular_locations": sub_locs,
            "keywords": keywords,
        }
    except Exception as e:
        log.warning("fetch_uniprot_shedding_data(%s): %s", gene_symbol, e)
        return None


def fetch_epmc_shedding_count(gene_symbol, timeout=20):
    """Fetch EPMC hit count for shedding/cleavage literature."""
    import requests as _rq
    query = (
        f'{gene_symbol} AND '
        f'(shedding OR "ectodomain cleavage" OR "ectodomain shedding" '
        f'OR ADAM10 OR ADAM17 OR TACE OR "soluble form")'
    )
    try:
        r = _rq.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={
            "query": query,
            "resultType": "lite", "pageSize": "1", "format": "json",
        }, timeout=timeout)
        r.raise_for_status()
        return r.json().get("hitCount", 0)
    except Exception as e:
        log.warning("fetch_epmc_shedding_count(%s): %s", gene_symbol, e)
        return 0


def assess_shedding(gene_symbol, uniprot_data, lit_count):
    """Score shedding risk (0-1, lower = better for drug targeting).

    Logic:
    - Fully secreted (signal peptide + no TM) → 0.9
    - Secreted keyword/location → 0.8
    - GPI-anchored → 0.5 base (sheddable via GPI-PLD/ADAM17)
    - Membrane-anchored: check for sheddase substrate evidence
    - Literature shedding evidence modulates score
    - No evidence of shedding → 0.1 (low risk)
    """
    if uniprot_data is None:
        return {
            "risk": 0.5, "evidence": ["no UniProt data"],
            "is_secreted": False, "has_signal_peptide": False,
            "shedding_evidence": "unknown",
        }

    is_secreted = uniprot_data["is_secreted"]
    has_sp = uniprot_data["has_signal_peptide"]
    has_tm = uniprot_data["has_tm"]
    is_gpi = uniprot_data["is_gpi"]
    domain_text = uniprot_data["domain_text"]

    evidence = []
    risk = 0.1  # baseline: membrane-anchored, no shedding evidence

    # Check domain annotations for sheddase substrate motifs
    sheddase_hits = []
    for kw in _SHEDDASE_KEYWORDS:
        if kw in domain_text:
            sheddase_hits.append(kw)

    # Scoring hierarchy (most specific first)
    if has_sp and not has_tm and not is_gpi:
        # Fully secreted protein — no membrane anchor at all
        risk = 0.9
        evidence.append("signal peptide + no TM domain (likely fully secreted)")
    elif is_gpi:
        # GPI-anchored: sheddable but not freely secreted — check is_gpi BEFORE
        # is_secreted so GPI proteins with a "Secreted" sublocation entry (e.g. MSLN,
        # FOLR1) get the correct 0.5 score instead of being overscored as 0.8.
        risk = 0.5
        evidence.append("GPI-anchored (sheddable via GPI-PLD/ADAM17)")
    elif is_secreted and not has_tm:
        risk = 0.8
        evidence.append("UniProt 'Secreted' keyword, no TM domain")
    elif is_secreted and has_tm:
        # Dual-topology: has both secreted and membrane forms
        risk = 0.6
        evidence.append("dual-topology: Secreted + membrane-anchored")
    elif has_tm:
        risk = 0.1
        evidence.append(f"membrane-anchored ({uniprot_data['tm_count']} TM)")
    else:
        risk = 0.5
        evidence.append("unknown topology")

    # Sheddase substrate evidence from domain annotations
    if sheddase_hits:
        risk = min(1.0, risk + 0.2)
        evidence.append(f"sheddase substrates in domains: {', '.join(sheddase_hits)}")

    # Literature modulation
    if lit_count >= 20:
        risk = min(1.0, risk + 0.2)
        evidence.append(f"strong shedding literature ({lit_count} papers)")
    elif lit_count >= 5:
        risk = min(1.0, risk + 0.1)
        evidence.append(f"moderate shedding literature ({lit_count} papers)")
    elif lit_count > 0:
        evidence.append(f"sparse shedding literature ({lit_count} papers)")
    else:
        if risk <= 0.3:
            evidence.append("no shedding literature (supports low risk)")

    # Determine shedding evidence summary
    if sheddase_hits and lit_count >= 5:
        shedding_evidence = "strong"
    elif sheddase_hits or lit_count >= 5:
        shedding_evidence = "moderate"
    elif lit_count > 0:
        shedding_evidence = "weak"
    else:
        shedding_evidence = "none"

    return {
        "risk": round(min(1.0, risk), 2),
        "evidence": evidence,
        "is_secreted": is_secreted,
        "has_signal_peptide": has_sp,
        "is_gpi": is_gpi,
        "shedding_evidence": shedding_evidence,
    }


def exec_shedding_risk(arguments, input_table, output_table, db_path):
    """Assess shedding risk for genes. Reads gene symbols from input table,
    fetches UniProt + EPMC data in parallel, runs scoring."""
    import sqlite3, time
    from concurrent.futures import ThreadPoolExecutor as _TPE, as_completed

    genes = []
    gene_col = None
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
        for candidate in ["approvedSymbol", "approvedsymbol", "gene_symbol",
                           "gene_name", "symbol", "gene",
                           "target.approvedSymbol", "_input_gene_name"]:
            if any(c.lower() == candidate.lower() for c in all_cols):
                gene_col = next(c for c in all_cols if c.lower() == candidate.lower())
                break
        if gene_col:
            genes = [r[gene_col] for r in rows if r.get(gene_col)]

    if not genes:
        gene_arg = arguments.get("gene", arguments.get("gene_name",
                   arguments.get("target", arguments.get("symbol", ""))))
        if gene_arg:
            genes = [g.strip() for g in gene_arg.split(",") if g.strip()]
    genes = list(dict.fromkeys(genes))  # deduplicate preserving order

    if not genes:
        raise ValueError("No genes found — provide an input table or 'gene' parameter")
    log.info("exec_shedding_risk: %d genes from column '%s'", len(genes), gene_col or "arguments")

    def _score_one(gene):
        time.sleep(0.1)  # rate limit
        uniprot = fetch_uniprot_shedding_data(gene)
        lit_count = fetch_epmc_shedding_count(gene)
        result = assess_shedding(gene, uniprot, lit_count)
        return {
            "_input_gene_name": gene,
            "shedding_risk": result["risk"],
            "is_secreted": str(result["is_secreted"]),
            "has_signal_peptide": str(result["has_signal_peptide"]),
            "is_gpi": str(result["is_gpi"]),
            "shedding_evidence": result["shedding_evidence"],
            "shedding_literature_count": str(lit_count),
            "shedding_details": "; ".join(result["evidence"]),
        }

    results = []
    with _TPE(max_workers=4) as pool:
        futures = {pool.submit(_score_one, g): g for g in genes}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                log.warning("exec_shedding_risk: %s failed: %s", futures[future], e)

    results.sort(key=lambda r: float(r["shedding_risk"]))

    log.info("exec_shedding_risk: %d/%d genes scored", len(results), len(genes))
    return results
