"""Custom tool: successful_trials_classifier (DSR-402).

Each output row includes a hidden `_raw_study_json` column with the
full CT.gov v2 study dict. This lets downstream tools (DSR-403
patient population, DSR-404 outcome extraction, DSR-406 responder
characterisation) be pure projections over the cached data — no
re-fetch, no rate-limit pain.

Given a condition (e.g. 'epilepsy'), search ClinicalTrials.gov v2 for
interventional trials and classify each one as successful / failed /
inconclusive using deterministic rules on the resultsSection. No LLM
judgement — every classification is reproducible from audit columns.

Three input modes:
  1. Condition-only: pass `condition` only.
  2. Condition + drugs: comma-separated `drugs` narrows the search via
     intervention synonyms.
  3. Chained from upstream table column: input_table column 'drug_name'
     (or 'drug', 'intervention', ...) is read and looped over.

Optional `since` / `until` filter by trial completion date. Optional
`limit` keeps the top N by completion date desc.
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

_CT_URL = "https://clinicaltrials.gov/api/v2/studies"

_TERMINATED_STATUSES = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}
_ONGOING_STATUSES = {
    "RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
}
_NON_INFERIORITY_TYPES = {"NON_INFERIORITY", "EQUIVALENCE"}

# Classification priority for sorting.
_CLASSIFICATION_PRIORITY = {
    "successful": 0,
    "successful_noninferiority": 1,
    "ongoing": 2,
    "completed_no_stats": 3,
    "completed_no_results": 4,
    "failed_efficacy": 5,
    "failed_other": 6,
    "unknown": 7,
}


# --- Pure helpers -----------------------------------------------------------

def _parse_pvalue(raw: Any) -> Optional[float]:
    """Parse CT.gov pValue strings.

    '<0.001' -> a value just below 0.001
    '>0.05'  -> a value just above 0.05
    '0.03'   -> 0.03
    None / unparseable -> None
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.startswith("<"):
            return max(float(s[1:]) - 1e-6, 0.0)
        if s.startswith(">"):
            return float(s[1:]) + 1e-6
        if s.startswith("="):
            return float(s[1:])
        return float(s)
    except ValueError:
        return None


def _extract_primary_pvalues(study: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract per-PRIMARY-outcome p-value info.

    Returns a list of dicts (one per PRIMARY outcome), each with:
        title, pvalue_raw, pvalue_float, non_inferiority_type
    Empty list if no resultsSection.
    """
    rs = study.get("resultsSection") or {}
    om_module = rs.get("outcomeMeasuresModule") or {}
    measures = om_module.get("outcomeMeasures") or []
    out: List[Dict[str, Any]] = []
    for o in measures:
        if o.get("type") != "PRIMARY":
            continue
        analyses = o.get("analyses") or []
        a = analyses[0] if analyses else {}
        out.append({
            "title": o.get("title", ""),
            "pvalue_raw": a.get("pValue"),
            "pvalue_float": _parse_pvalue(a.get("pValue")),
            "non_inferiority_type": a.get("nonInferiorityType"),
        })
    return out


def classify_trial(
    study: Dict[str, Any], threshold: float = 0.05,
) -> Tuple[str, Dict[str, Any]]:
    """Classify a CT.gov v2 study dict.

    Returns (classification, evidence) where evidence carries the audit
    columns: pvalue_primary, pvalue_raw, non_inferiority_type, whyStopped,
    has_results, n_primary_total, n_primary_significant.
    """
    proto = study.get("protocolSection") or {}
    status_mod = proto.get("statusModule") or {}
    status = status_mod.get("overallStatus", "")
    why_stopped = status_mod.get("whyStopped", "") or ""
    has_results = bool(study.get("hasResults", False))

    primaries = _extract_primary_pvalues(study)
    sig_primaries = [
        p for p in primaries
        if p["pvalue_float"] is not None and p["pvalue_float"] < threshold
    ]
    primaries_with_analyses = [p for p in primaries if p["pvalue_raw"] is not None]

    # Smallest parseable p-value (for audit) and worst-case NI type.
    pvalue_floats = [p["pvalue_float"] for p in primaries if p["pvalue_float"] is not None]
    pvalue_primary = min(pvalue_floats) if pvalue_floats else None
    pvalue_raws = [p["pvalue_raw"] for p in primaries if p["pvalue_raw"] is not None]
    pvalue_raw = "; ".join(str(p) for p in pvalue_raws)
    ni_types = [p["non_inferiority_type"] for p in primaries
                if p["non_inferiority_type"]]
    ni_type_label = "; ".join(sorted(set(ni_types))) if ni_types else ""

    evidence = {
        "pvalue_primary": pvalue_primary,
        "pvalue_raw": pvalue_raw,
        "non_inferiority_type": ni_type_label,
        "whyStopped": why_stopped,
        "has_results": has_results,
        "n_primary_total": len(primaries),
        "n_primary_significant": len(sig_primaries),
    }

    if status == "COMPLETED" and has_results:
        # Any primary explicitly non-significant (parsed pValue >= threshold)
        # => trial failed regardless of other primaries' completeness.
        any_explicit_failure = any(
            p["pvalue_float"] is not None and p["pvalue_float"] >= threshold
            for p in primaries
        )
        if any_explicit_failure:
            return ("failed_efficacy", evidence)

        # Need >=1 primary AND every primary must have a parseable significant
        # pValue (ALL rule, user-confirmed). Anything less => completed_no_stats:
        # missing analyses, no primaries declared, or unparseable pValue strings.
        all_certifiably_significant = (
            len(primaries) >= 1
            and len(sig_primaries) == len(primaries)
            and len(primaries_with_analyses) == len(primaries)
        )
        if all_certifiably_significant:
            any_ni = any(
                p["non_inferiority_type"] in _NON_INFERIORITY_TYPES
                for p in primaries
            )
            return ("successful_noninferiority" if any_ni else "successful", evidence)

        return ("completed_no_stats", evidence)

    if status == "COMPLETED" and not has_results:
        return ("completed_no_results", evidence)

    if status in _TERMINATED_STATUSES:
        return ("failed_other", evidence)

    if status in _ONGOING_STATUSES:
        return ("ongoing", evidence)

    return ("unknown", evidence)


def _build_filter_advanced(
    condition_only: bool,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> str:
    """Compose CT.gov v2 filter.advanced query string.

    Condition-only mode adds AREA[StudyType]INTERVENTIONAL; drug-narrowing
    mode skips it because query.intr already implies an intervention.
    """
    clauses: List[str] = []
    if condition_only:
        clauses.append("AREA[StudyType]INTERVENTIONAL")
    if since or until:
        lo = since if since else "MIN"
        hi = until if until else "MAX"
        clauses.append(f"AREA[CompletionDate]RANGE[{lo},{hi}]")
    return " AND ".join(clauses)


# --- Search primitives ------------------------------------------------------

def _fetch_studies(params: Dict[str, str], max_pages: int = 20) -> List[Dict[str, Any]]:
    """Page through CT.gov v2 /studies and return raw study dicts.

    Adds nextPageToken pagination on top of the existing search params.
    Logs WARNING when capped at max_pages (truncation visible to caller).
    """
    import requests as _rq

    studies: List[Dict[str, Any]] = []
    next_token: Optional[str] = None
    pages = 0
    base_params = dict(params)
    base_params.setdefault("pageSize", "100")
    base_params.setdefault("countTotal", "true")
    base_params.setdefault("format", "json")
    # Default response omits resultsSection — request it explicitly.
    base_params.setdefault("fields", "NCTId,HasResults,ProtocolSection,ResultsSection")

    while pages < max_pages:
        page_params = dict(base_params)
        if next_token:
            page_params["pageToken"] = next_token
        try:
            r = _rq.get(_CT_URL, params=page_params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning("_fetch_studies page %d: %s", pages, e)
            break
        page_studies = data.get("studies") or []
        studies.extend(page_studies)
        pages += 1
        next_token = data.get("nextPageToken")
        if not next_token:
            break

    if next_token:
        log.warning(
            "_fetch_studies: capped at max_pages=%d (next_token still set, "
            "trials beyond page %d are dropped)",
            max_pages, max_pages,
        )
    log.info("_fetch_studies: %d studies across %d page(s)", len(studies), pages)
    return studies


def _expand_intervention(term: str, timeout: int = 15) -> str:
    """Expand a drug term into OR'd quoted synonyms for query.intr.

    Mirrors the logic in tools_sr/clinical_trials.py — synonym expansion
    via PubChem/OLS/NCI + isotope variants, with bracket sanitization.
    """
    import re as _re

    def _sanitize(s: str) -> str:
        return " ".join(_re.sub(r"\[[^\]]*\]", "", s).strip().split()) or s

    try:
        try:
            from ..sr_synonyms import expand_synonyms
        except (ImportError, SystemError):
            try:
                from integration.genai.research_pipeline.tools.synonyms import expand_synonyms
            except ImportError:
                log.warning("synonym expansion not available, using raw term")
                return f'"{_sanitize(term)}"'
    except ImportError:
        return f'"{_sanitize(term)}"'

    synonyms = expand_synonyms(term, timeout=timeout, max_terms=12)
    synonyms = [_sanitize(s) for s in synonyms if s]
    return " OR ".join(f'"{s}"' for s in synonyms) if synonyms else f'"{_sanitize(term)}"'


# --- Row projection ---------------------------------------------------------

def _row_from_study(
    study: Dict[str, Any],
    classification: str,
    evidence: Dict[str, Any],
    input_query: str = "",
) -> Dict[str, Any]:
    """Project a raw CT.gov study + classification into the output row."""
    proto = study.get("protocolSection") or {}
    ident = proto.get("identificationModule") or {}
    stat = proto.get("statusModule") or {}
    design = proto.get("designModule") or {}
    sponsor = (proto.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
    arms = proto.get("armsInterventionsModule") or {}

    interventions = arms.get("interventions") or []
    drugs = [i["name"] for i in interventions
             if i.get("name") and i.get("type") == "DRUG"]
    nct_id = ident.get("nctId", "")
    primaries = _extract_primary_pvalues(study)
    primary_titles = "; ".join(p["title"] for p in primaries if p["title"])

    return {
        "nct_id": nct_id,
        "drug": "; ".join(drugs),
        "phase": "; ".join(design.get("phases") or []),
        "status": stat.get("overallStatus", ""),
        "classification": classification,
        "primary_endpoint": primary_titles,
        "completion_date": (stat.get("completionDateStruct") or {}).get("date", ""),
        "sponsor": sponsor.get("name", ""),
        "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
        # Audit columns
        "pvalue_primary": "" if evidence["pvalue_primary"] is None
                          else f"{evidence['pvalue_primary']:.4g}",
        "pvalue_raw": evidence["pvalue_raw"],
        "non_inferiority_type": evidence["non_inferiority_type"],
        "whyStopped": evidence["whyStopped"],
        "has_results": str(evidence["has_results"]),
        "n_primary_total": str(evidence["n_primary_total"]),
        "n_primary_significant": str(evidence["n_primary_significant"]),
        "_input_query": input_query,
        # Hidden cache column — full CT.gov study dict serialised for
        # downstream tools. _summ truncates to 60 chars so chat doesn't
        # show this. SQLite carries the full string for chained tools
        # to read via json.loads().
        "_raw_study_json": json.dumps(study, ensure_ascii=False),
    }


# --- exec function ----------------------------------------------------------

def exec_successful_trials(arguments, input_table, output_table, db_path):
    """Classify clinical trials as successful / failed / inconclusive."""
    import sqlite3

    condition = arguments.get("condition", "")
    if not condition:
        raise ValueError("`condition` is required (e.g. 'epilepsy').")

    threshold = float(arguments.get("pvalue_threshold", 0.05))
    since = arguments.get("since") or None
    until = arguments.get("until") or None
    limit_arg = arguments.get("limit")
    limit = int(limit_arg) if limit_arg else None

    # Resolve drug list.
    drugs: List[str] = []
    if input_table:
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            cols = [d[0] for d in
                    conn.execute(f"SELECT * FROM [{input_table}] LIMIT 0").description]
            rows = [dict(zip(cols, r)) for r in
                    conn.execute(f"SELECT * FROM [{input_table}]").fetchall()]
        except sqlite3.OperationalError as e:
            conn.close()
            raise ValueError(f"Input table '{input_table}' not found: {e}")
        conn.close()

        drug_col = None
        for cand in ["drug_name", "drug_names", "drug", "intervention",
                     "interventions", "_input_drug_name"]:
            if any(c.lower() == cand.lower() for c in cols):
                drug_col = next(c for c in cols if c.lower() == cand.lower())
                break
        if drug_col:
            drugs = [r[drug_col] for r in rows if r.get(drug_col)]

    if not drugs and arguments.get("drugs"):
        drugs = [d.strip() for d in str(arguments["drugs"]).split(",") if d.strip()]

    log.info("exec_successful_trials: condition=%s, drugs=%d, since=%s, until=%s, limit=%s",
             condition, len(drugs), since, until, limit)

    raw_studies: List[Tuple[Dict[str, Any], str]] = []  # (study, input_query)

    if drugs:
        filter_adv = _build_filter_advanced(
            condition_only=False, since=since, until=until,
        )

        def _search_drug(drug: str):
            params = {
                "query.intr": _expand_intervention(drug),
                "query.cond": condition,
            }
            if filter_adv:
                params["filter.advanced"] = filter_adv
            return drug, _fetch_studies(params, max_pages=5)

        with ThreadPoolExecutor(max_workers=4) as pool:
            futs = [pool.submit(_search_drug, d) for d in drugs]
            for f in as_completed(futs):
                drug, studies = f.result()
                for s in studies:
                    raw_studies.append((s, drug))
    else:
        params = {"query.cond": condition}
        filter_adv = _build_filter_advanced(
            condition_only=True, since=since, until=until,
        )
        params["filter.advanced"] = filter_adv
        for s in _fetch_studies(params, max_pages=20):
            raw_studies.append((s, ""))

    # Classify and project.
    rows: List[Dict[str, Any]] = []
    for study, input_query in raw_studies:
        cls, ev = classify_trial(study, threshold)
        rows.append(_row_from_study(study, cls, ev, input_query=input_query))

    # Sort by completion_date desc (so 'last N' is meaningful), then by
    # classification priority (so successful surfaces first within the same
    # completion-date tie).
    def _sort_key(r):
        return (
            r.get("completion_date", "") or "",
            -_CLASSIFICATION_PRIORITY.get(r["classification"], 99),
        )

    rows.sort(key=_sort_key, reverse=True)

    if limit is not None and limit > 0:
        rows = rows[:limit]

    log.info("exec_successful_trials: returning %d rows", len(rows))
    return rows
