"""Custom tool: competition_landscape

Analyzes the competitive landscape for a target gene by drug modality and
development phase. Uses OpenTargets knownDrugs GraphQL to get all drugs
targeting a gene, grouped by molecule type (antibody, small molecule, ADC,
radioligand, etc.).

Score 0-1 where lower = more competition (worse for new entrants).
Modality whitespace score indicates opportunity in specific drug classes.
"""
from __future__ import annotations
import json, logging

log = logging.getLogger(__name__)

# Targets with approved radioligand drugs (not tracked in OT drugType).
# These are APPROVAL-stage radioligands only:
#   SSTR2: [177Lu]DOTATATE (Lutathera, FDA 2018)
#   FOLH1/PSMA: [177Lu]PSMA-617 (Pluvicto, FDA 2022)
_KNOWN_RADIOLIGAND_TARGETS = {"SSTR2", "FOLH1", "PSMA"}

# Normalize OT molecule types into broad modality buckets.
# OT drugType values (as of 2025): "Antibody", "Small molecule", "Protein",
# "Antibody Drug Conjugate", "Gene therapy", "Cell therapy", "Oligonucleotide",
# "Oligosaccharide", "Unknown", "Enzyme".
_MODALITY_MAP = {
    "antibody": "antibody",
    "protein": "protein",
    "small molecule": "small_molecule",
    "enzyme": "protein",
    "oligonucleotide": "oligonucleotide",
    "oligosaccharide": "other",
    "unknown": "other",
    "gene": "gene_therapy",
    "cell": "cell_therapy",
    # ADC: OT returns "Antibody Drug Conjugate" as the drugType
    "antibody drug conjugate": "antibody_drug_conjugate",
}

# Phase weight for competition scoring (higher phase = more competitive pressure)
_PHASE_WEIGHT = {
    4: 1.0,   # approved
    3: 0.7,
    2: 0.4,
    1: 0.2,
    0: 0.05,  # preclinical / discovery
}


def fetch_ot_known_drugs(gene_symbol, timeout=30):
    """Fetch known drugs from OpenTargets GraphQL for a given gene.

    Returns list of dicts with: drug_name, phase, molecule_type, mechanism, drug_id.
    """
    import requests as _rq

    # OT v4 API: knownDrugs renamed to drugAndClinicalCandidates;
    # maximumClinicalTrialPhase renamed to maximumClinicalStage;
    # mechanismOfAction and phase are not on the row — use maxClinicalStage.
    query = """
    query knownDrugs($ensemblId: String!) {
      target(ensemblId: $ensemblId) {
        drugAndClinicalCandidates {
          count
          rows {
            id
            maxClinicalStage
            drug {
              id
              name
              drugType
              maximumClinicalStage
            }
          }
        }
      }
    }
    """
    # First resolve gene symbol to Ensembl ID via OT search
    ensembl_id = _resolve_ensembl_id(gene_symbol, timeout)
    if not ensembl_id:
        log.warning("fetch_ot_known_drugs(%s): could not resolve Ensembl ID", gene_symbol)
        return []

    try:
        r = _rq.post(
            "https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": query, "variables": {"ensemblId": ensembl_id}},
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("fetch_ot_known_drugs(%s): GraphQL failed: %s", gene_symbol, e)
        return []

    target_data = (data.get("data") or {}).get("target") or {}
    if not target_data:
        return []
    known = (target_data.get("drugAndClinicalCandidates") or {}).get("rows") or []

    # Convert OT stage strings (PHASE_3, APPROVAL) to integer for scoring
    _STAGE_TO_INT = {
        "APPROVAL": 4, "PHASE_4": 4,
        "PHASE_3": 3, "PHASE_2": 2, "PHASE_1": 1,
        "PHASE_0": 0,
    }

    drugs = []
    seen = set()
    for row in known:
        drug = row.get("drug") or {}
        drug_id = drug.get("id", "")
        if drug_id in seen:
            continue
        seen.add(drug_id)
        stage_str = (row.get("maxClinicalStage") or drug.get("maximumClinicalStage") or "PHASE_0").upper()
        phase_int = _STAGE_TO_INT.get(stage_str, 0)
        drugs.append({
            "drug_name": drug.get("name", ""),
            "drug_id": drug_id,
            "molecule_type": (drug.get("drugType") or "unknown").lower(),
            "max_phase": phase_int,
            "mechanism": "",
            "phase": phase_int,
        })

    return drugs


def _resolve_ensembl_id(gene_symbol, timeout=20):
    """Resolve gene symbol to Ensembl ID via OpenTargets search."""
    import requests as _rq
    query = """
    query search($q: String!) {
      search(queryString: $q, entityNames: ["target"], page: {size: 1, index: 0}) {
        hits { id }
      }
    }
    """
    try:
        r = _rq.post(
            "https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": query, "variables": {"q": gene_symbol}},
            timeout=timeout,
        )
        r.raise_for_status()
        hits = (r.json().get("data") or {}).get("search", {}).get("hits") or []
        if hits:
            return hits[0]["id"]
    except Exception as e:
        log.warning("_resolve_ensembl_id(%s): %s", gene_symbol, e)
    return None


def assess_competition(gene_symbol, drugs):
    """Score competitive landscape.

    Returns dict with competition_score (0-1, lower = more competition),
    modality breakdown, and whitespace analysis.
    """
    if not drugs:
        if gene_symbol.upper() in _KNOWN_RADIOLIGAND_TARGETS:
            whitespace_str = "; ".join(sorted(
                {"antibody", "small_molecule", "protein", "oligonucleotide",
                 "gene_therapy", "cell_therapy", "antibody_drug_conjugate", "other"}
            ))
        else:
            whitespace_str = "all modalities open"
        return {
            "competition_score": 1.0,  # no competition
            "total_drugs": 0,
            "max_phase": 0,
            "drugs_by_modality": "{}",
            "modality_whitespace": whitespace_str,
            "top_competitors": "",
            "evidence": ["no known drugs"],
        }

    # Group by modality
    modality_drugs = {}
    for d in drugs:
        raw_type = d["molecule_type"]
        modality = _MODALITY_MAP.get(raw_type, raw_type)
        modality_drugs.setdefault(modality, []).append(d)

    # Build modality summary: {modality: {phase: count}}
    modality_summary = {}
    for modality, mdrugs in modality_drugs.items():
        phase_counts = {}
        for d in mdrugs:
            phase = min(4, max(0, d["max_phase"]))
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        modality_summary[modality] = phase_counts

    # Competition score: weighted sum of all drugs by phase
    total_weight = 0.0
    for d in drugs:
        phase = min(4, max(0, d["max_phase"]))
        total_weight += _PHASE_WEIGHT.get(phase, 0.05)

    # Normalize: 0 drugs = 1.0 (no competition), scale down with more/higher-phase drugs
    # Use a saturation curve so score approaches 0 as competition grows
    competition_score = round(1.0 / (1.0 + total_weight), 3)

    max_phase = max(d["max_phase"] for d in drugs)
    total_drugs = len(drugs)

    # Whitespace: which modalities have NO drugs?
    all_modalities = {"antibody", "small_molecule", "protein", "oligonucleotide",
                      "gene_therapy", "cell_therapy", "antibody_drug_conjugate", "other"}
    present_modalities = set(modality_drugs.keys())
    open_modalities = all_modalities - present_modalities
    # Radioligand is not in OT drugType, so check manually.
    # Targets with approved radioligands: report as occupied, not open.
    if gene_symbol.upper() in _KNOWN_RADIOLIGAND_TARGETS:
        present_modalities.add("radioligand")
    else:
        open_modalities.add("radioligand")

    whitespace_str = "; ".join(sorted(open_modalities)) if open_modalities else "none"

    # Top competitors: approved and phase 3 drugs
    top = sorted(drugs, key=lambda d: -d["max_phase"])
    top_str = "; ".join(
        f"{d['drug_name']} (phase {d['max_phase']}, {d['molecule_type']})"
        for d in top[:5]
    )

    evidence = [f"{total_drugs} drugs, max phase {max_phase}"]
    for modality, pcounts in modality_summary.items():
        parts = [f"P{p}:{c}" for p, c in sorted(pcounts.items(), reverse=True)]
        evidence.append(f"{modality}: {', '.join(parts)}")

    return {
        "competition_score": competition_score,
        "total_drugs": total_drugs,
        "max_phase": max_phase,
        "drugs_by_modality": json.dumps(modality_summary),
        "modality_whitespace": whitespace_str,
        "top_competitors": top_str,
        "evidence": evidence,
    }


def exec_competition_landscape(arguments, input_table, output_table, db_path):
    """Analyze competitive landscape for target genes. Reads gene symbols from
    input table, fetches OpenTargets knownDrugs, scores competition."""
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
    log.info("exec_competition_landscape: %d genes from column '%s'", len(genes), gene_col or "arguments")

    def _score_one(gene):
        time.sleep(0.5)  # OT rate limit
        drugs = fetch_ot_known_drugs(gene)
        result = assess_competition(gene, drugs)
        return {
            "_input_gene_name": gene,
            "competition_score": result["competition_score"],
            "total_drugs": str(result["total_drugs"]),
            "max_phase": str(result["max_phase"]),
            "drugs_by_modality": result["drugs_by_modality"],
            "modality_whitespace": result["modality_whitespace"],
            "top_competitors": result["top_competitors"],
            "competition_details": "; ".join(result["evidence"]),
        }

    results = []
    with _TPE(max_workers=2) as pool:  # conservative: OT rate limits
        futures = {pool.submit(_score_one, g): g for g in genes}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                log.warning("exec_competition_landscape: %s failed: %s",
                            futures[future], e)

    results.sort(key=lambda r: float(r["competition_score"]), reverse=True)

    log.info("exec_competition_landscape: %d/%d genes scored", len(results), len(genes))
    return results
