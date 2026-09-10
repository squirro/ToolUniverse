"""Custom tool: validation_level

Assesses the clinical validation level of a target gene by combining
OpenTargets max clinical phase with ClinicalTrials.gov trial counts
and status breakdown for a given indication.

Score 0-1 where higher = more validated (more evidence of drugability).
"""
from __future__ import annotations
import json
import logging

log = logging.getLogger(__name__)

# Phase-to-score mapping for base validation
_PHASE_SCORE = {
    0: 0.05,  # preclinical only
    1: 0.2,
    2: 0.4,
    3: 0.7,
    4: 0.9,   # approved
}


_PHASE_MAP = {
    "PHASE_0": 0, "PHASE_I": 1, "PHASE_1": 1,
    "PHASE_II": 2, "PHASE_2": 2,
    "PHASE_III": 3, "PHASE_3": 3,
    "PHASE_IV": 4, "PHASE_4": 4,
    "APPROVED": 4, "APPROVAL": 4,
}


def fetch_ot_max_phase(gene_symbol, timeout=20):
    """Fetch max clinical trial phase from OpenTargets for a gene.

    Returns int (0-4) or 0 if not found.
    Uses the v4 `drugAndClinicalCandidates` field (knownDrugs was removed).
    """
    import requests as _rq
    ensembl_id = _resolve_ensembl_id(gene_symbol, timeout)
    if not ensembl_id:
        return 0

    query = """
    query maxPhase($ensemblId: String!) {
      target(ensemblId: $ensemblId) {
        drugAndClinicalCandidates {
          rows {
            drug { name }
            maxClinicalStage
          }
        }
      }
    }
    """
    try:
        r = _rq.post(
            "https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": query, "variables": {"ensemblId": ensembl_id}},
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        target = (data.get("data") or {}).get("target") or {}
        rows = (target.get("drugAndClinicalCandidates") or {}).get("rows") or []
        phases = []
        for row in rows:
            stage = row.get("maxClinicalStage", "")
            if isinstance(stage, int):
                phases.append(stage)
            elif isinstance(stage, str):
                phases.append(_PHASE_MAP.get(stage.upper(), 0))
        return max(phases) if phases else 0
    except Exception as e:
        log.warning("fetch_ot_max_phase(%s): %s", gene_symbol, e)
        return 0


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


def fetch_ctgov_trials(gene_symbol, indication="", timeout=30, search_mode="target"):
    """Search ClinicalTrials.gov v2 API for trials.

    Args:
        gene_symbol: gene symbol, drug name, or intervention term
        indication: disease/cancer type to narrow search
        search_mode: 'target' (gene target, uses query.term) or
                     'intervention' (drug/intervention, uses query.intr with
                     synonym expansion for precise intervention-field matching)

    Returns dict with: total_count, status_breakdown, has_biomarker.
    """
    import requests as _rq

    params = {
        "pageSize": 100,
        "countTotal": "true",
        "format": "json",
    }

    if search_mode == "intervention":
        # Expand synonyms for precise intervention search
        try:
            from ..sr_synonyms import expand_synonyms
        except (ImportError, SystemError):
            try:
                from ..sr_synonyms import expand_synonyms
            except ImportError:
                from integration.genai.research_pipeline.tools.synonyms import expand_synonyms

        synonyms = expand_synonyms(gene_symbol, timeout=min(timeout, 15))
        # Use query.intr (searches InterventionName + OtherName + Description)
        intr_query = " OR ".join(f'"{s}"' for s in synonyms)
        params["query.intr"] = intr_query
        if indication:
            params["query.cond"] = indication
        # Only interventional studies
        params["filter.advanced"] = "AREA[StudyType]INTERVENTIONAL"
    else:
        # Target/gene mode: broad query.term
        query_parts = [gene_symbol]
        if indication:
            query_parts.append(indication)
        params["query.term"] = " AND ".join(query_parts)

    try:
        r = _rq.get("https://clinicaltrials.gov/api/v2/studies",
                     params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("fetch_ctgov_trials(%s): %s", gene_symbol, e)
        return {"total_count": 0, "status_breakdown": {}, "has_biomarker": False}

    studies = data.get("studies") or []
    total_count = data.get("totalCount", len(studies))

    status_counts = {}
    has_biomarker = False
    for study in studies:
        proto = (study.get("protocolSection") or {})
        status_mod = proto.get("statusModule") or {}
        status = status_mod.get("overallStatus", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

        design_mod = proto.get("identificationModule") or {}
        title = (design_mod.get("briefTitle") or "").lower()
        if "biomarker" in title or "companion diagnostic" in title:
            has_biomarker = True

    return {
        "total_count": total_count,
        "status_breakdown": status_counts,
        "has_biomarker": has_biomarker,
    }


def assess_validation(gene_symbol, max_phase, trial_data):
    """Score clinical validation level.

    Combines OT max_phase with ClinicalTrials.gov trial count and status.
    """
    base_score = _PHASE_SCORE.get(min(4, max(0, max_phase)), 0.05)

    total_trials = trial_data.get("total_count", 0)
    status = trial_data.get("status_breakdown", {})
    has_biomarker = trial_data.get("has_biomarker", False)

    # Trial count bonus (more trials = more validated)
    if total_trials >= 20:
        trial_bonus = 0.1
    elif total_trials >= 5:
        trial_bonus = 0.05
    else:
        trial_bonus = 0.0

    # Active trials bonus
    recruiting = status.get("RECRUITING", 0) + status.get("NOT_YET_RECRUITING", 0)
    if recruiting >= 3:
        active_bonus = 0.05
    else:
        active_bonus = 0.0

    score = min(1.0, base_score + trial_bonus + active_bonus)

    # Extract status summary
    recruiting_count = status.get("RECRUITING", 0)
    completed_count = status.get("COMPLETED", 0)
    terminated_count = status.get("TERMINATED", 0) + status.get("WITHDRAWN", 0)

    evidence = [f"max phase {max_phase}"]
    if total_trials > 0:
        evidence.append(f"{total_trials} trials")
    if recruiting_count > 0:
        evidence.append(f"{recruiting_count} recruiting")
    if completed_count > 0:
        evidence.append(f"{completed_count} completed")
    if terminated_count > 0:
        evidence.append(f"{terminated_count} terminated/withdrawn")
    if has_biomarker:
        evidence.append("biomarker-driven trial exists")

    return {
        "validation_score": round(score, 3),
        "max_phase": max_phase,
        "trial_count": total_trials,
        "recruiting_trials": recruiting_count,
        "completed_trials": completed_count,
        "has_biomarker": has_biomarker,
        "evidence": evidence,
    }


def exec_validation_level(arguments, input_table, output_table, db_path):
    """Assess clinical validation level for target genes. Combines OpenTargets
    max phase with ClinicalTrials.gov trial data."""
    import sqlite3
    import time
    from concurrent.futures import ThreadPoolExecutor as _TPE, as_completed

    indication = arguments.get("indication", arguments.get("disease_name", ""))
    search_mode = arguments.get("search_mode", "target")

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

    if not genes:
        gene_arg = arguments.get("gene", arguments.get("gene_name",
                   arguments.get("target", arguments.get("symbol", ""))))
        if gene_arg:
            genes = [g.strip() for g in gene_arg.split(",") if g.strip()]
    genes = list(dict.fromkeys(genes))  # deduplicate preserving order

    if not genes:
        raise ValueError("No genes found — provide an input table or 'gene' parameter")
    log.info("exec_validation_level: %d genes, indication='%s'",
             len(genes), indication)

    def _score_one(gene):
        time.sleep(0.5)  # rate limit for OT + CTgov
        max_phase = fetch_ot_max_phase(gene)
        trial_data = fetch_ctgov_trials(gene, indication, search_mode=search_mode)
        result = assess_validation(gene, max_phase, trial_data)
        return {
            "_input_gene_name": gene,
            "validation_score": result["validation_score"],
            "max_phase": str(result["max_phase"]),
            "trial_count": str(result["trial_count"]),
            "recruiting_trials": str(result["recruiting_trials"]),
            "completed_trials": str(result["completed_trials"]),
            "has_biomarker": str(result["has_biomarker"]),
            "validation_details": "; ".join(result["evidence"]),
        }

    results = []
    with _TPE(max_workers=2) as pool:  # conservative: OT rate limits
        futures = {pool.submit(_score_one, g): g for g in genes}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                log.warning("exec_validation_level: %s failed: %s",
                            futures[future], e)

    results.sort(key=lambda r: -float(r["validation_score"]))

    log.info("exec_validation_level: %d/%d genes scored", len(results), len(genes))
    return results
