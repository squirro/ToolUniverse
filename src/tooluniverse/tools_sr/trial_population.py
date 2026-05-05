"""Custom tool: trial_population_summary (DSR-403).

For each NCT ID (chained from a previous step or comma-separated input),
fetch the CT.gov v2 study and emit one row per trial × arm with patient-
population data: arm sizes, eligibility text (raw blob), baseline
characteristics (raw JSON blob), and PMIDs from CT.gov references.

LLM is used downstream to interpret raw fields. This tool only extracts —
it never invents numerics.
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

_CT_STUDY_URL = "https://clinicaltrials.gov/api/v2/studies/{nct_id}"

# Group title strings used by CT.gov for combined / total arms — these
# appear in baselineCharacteristicsModule.groups but don't correspond to
# real treatment arms in armGroups.
_AGGREGATE_GROUP_TITLES = {"total", "all participants", "overall"}


# --- Pure helpers -----------------------------------------------------------

def _extract_arms(study: Dict[str, Any]) -> List[Dict[str, str]]:
    """Project armGroups[] into a flat list of arm dicts."""
    proto = study.get("protocolSection") or {}
    arms_mod = proto.get("armsInterventionsModule") or {}
    arms_out: List[Dict[str, str]] = []
    for ag in arms_mod.get("armGroups") or []:
        arms_out.append({
            "arm_label": ag.get("label", "") or "",
            "arm_id": ag.get("id", "") or "",
            "arm_type": ag.get("type", "") or "",
            "arm_intervention": "; ".join(ag.get("interventionNames") or []),
        })
    return arms_out


def _extract_eligibility(study: Dict[str, Any]) -> Dict[str, str]:
    """Pull eligibility fields verbatim. Free-text criteria stays raw."""
    proto = study.get("protocolSection") or {}
    elig = proto.get("eligibilityModule") or {}
    hv = elig.get("healthyVolunteers")
    return {
        "min_age": elig.get("minimumAge", "") or "",
        "max_age": elig.get("maximumAge", "") or "",
        "sex": elig.get("sex", "") or "",
        "healthy_volunteers": "" if hv is None else str(hv),
        "eligibility_criteria": elig.get("eligibilityCriteria", "") or "",
    }


def _extract_pmids(study: Dict[str, Any]) -> List[str]:
    """PMIDs from CT.gov referencesModule. May be empty (coverage is patchy)."""
    proto = study.get("protocolSection") or {}
    refs_mod = proto.get("referencesModule") or {}
    out: List[str] = []
    for r in refs_mod.get("references") or []:
        pmid = r.get("pmid")
        if pmid:
            out.append(str(pmid))
    return out


def _extract_baseline_for_arm(
    study: Dict[str, Any], arm_label: str,
) -> Tuple[str, Dict[str, Any]]:
    """For one arm, return (arm_size_string, baseline_dict).

    arm_size: per-arm participant count from baselineCharacteristicsModule
              .denoms[0].counts[] (matched on title==arm_label).
    baseline: dict keyed by measure title. Continuous measures collapse
              to {param_type, unit, value, lowerLimit?, upperLimit?}.
              Categorical measures (multi-category) collapse to
              {param_type, unit, categories: {cat_title: value}}.
    Returns ("", {}) if the trial has no baseline section or no matching
    arm group.
    """
    results = study.get("resultsSection") or {}
    baseline = results.get("baselineCharacteristicsModule") or {}
    if not baseline:
        return ("", {})

    # Find the baseline group whose title matches the arm label,
    # skipping aggregate groups like "Total".
    arm_group_id = ""
    for g in baseline.get("groups") or []:
        title = (g.get("title") or "").strip()
        if title.lower() in _AGGREGATE_GROUP_TITLES:
            continue
        if title == arm_label:
            arm_group_id = g.get("id", "")
            break
    if not arm_group_id:
        return ("", {})

    # arm_size from denoms
    arm_size = ""
    for d in baseline.get("denoms") or []:
        for c in d.get("counts") or []:
            if c.get("groupId") == arm_group_id:
                arm_size = c.get("value", "") or ""
                break
        if arm_size:
            break

    # Per-arm projection of measures
    bl: Dict[str, Any] = {}
    for m in baseline.get("measures") or []:
        title = m.get("title", "")
        if not title:
            continue
        param_type = m.get("paramType", "")
        unit = m.get("unitOfMeasure", "")
        # Walk classes -> categories -> measurements, filtering by groupId
        classes = m.get("classes") or []
        if not classes:
            continue
        categories = classes[0].get("categories") or []
        if not categories:
            continue

        if len(categories) == 1:
            # Continuous measure — single value with optional range
            measurements = categories[0].get("measurements") or []
            for meas in measurements:
                if meas.get("groupId") == arm_group_id:
                    rec: Dict[str, Any] = {
                        "param_type": param_type,
                        "unit": unit,
                        "value": meas.get("value", "") or "",
                    }
                    if meas.get("lowerLimit"):
                        rec["lowerLimit"] = meas["lowerLimit"]
                    if meas.get("upperLimit"):
                        rec["upperLimit"] = meas["upperLimit"]
                    if meas.get("spread"):
                        rec["spread"] = meas["spread"]
                    bl[title] = rec
                    break
        else:
            # Categorical measure — emit dict of category -> value
            cat_values: Dict[str, str] = {}
            for cat in categories:
                cat_title = cat.get("title", "") or ""
                for meas in cat.get("measurements") or []:
                    if meas.get("groupId") == arm_group_id:
                        cat_values[cat_title] = meas.get("value", "") or ""
                        break
            if cat_values:
                bl[title] = {
                    "param_type": param_type,
                    "unit": unit,
                    "categories": cat_values,
                }

    return (arm_size, bl)


def _row_for_arm(
    study: Dict[str, Any], arm: Dict[str, str], input_query: str = "",
) -> Dict[str, Any]:
    """Project one trial × arm into the output schema."""
    proto = study.get("protocolSection") or {}
    ident = proto.get("identificationModule") or {}
    design = proto.get("designModule") or {}

    nct_id = ident.get("nctId", "") or input_query
    enrollment = (design.get("enrollmentInfo") or {}).get("count")
    enrollment_str = "" if enrollment is None else str(enrollment)

    elig = _extract_eligibility(study)
    pmids = _extract_pmids(study)
    arm_size, baseline_dict = _extract_baseline_for_arm(study, arm["arm_label"])

    return {
        "nct_id": nct_id,
        "arm_label": arm["arm_label"],
        "arm_id": arm["arm_id"],
        "arm_type": arm["arm_type"],
        "arm_intervention": arm["arm_intervention"],
        "arm_size": arm_size,
        "enrollment_total": enrollment_str,
        **elig,
        "baseline_json": json.dumps(baseline_dict, ensure_ascii=False),
        "references_pmids": "; ".join(pmids),
        "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
        "_input_query": input_query or nct_id,
    }


# --- Fetch primitive --------------------------------------------------------

# Cap on how long we'll honor a 429 Retry-After response. CT.gov has been
# observed to return Retry-After=600 (10 minutes) which is unreasonable for
# an interactive chat agent — better to fail fast and let the user retry.
_MAX_RETRY_AFTER_SECS = 30


def _fetch_study_by_id(
    nct_id: str, timeout: int = 30, max_retries: int = 3,
) -> Dict[str, Any]:
    """GET CT.gov v2 /studies/{nct_id} with full sections.

    Retries on 429 (rate-limit). Honors Retry-After header up to
    `_MAX_RETRY_AFTER_SECS`; falls back to exponential backoff
    (2s, 4s, 8s) when no header. If the server demands a longer wait,
    we give up immediately rather than block the chat agent.

    Returns {} on terminal failure (caller skips/warns).
    """
    import requests as _rq
    import time as _time

    nct_id = (nct_id or "").strip()
    if not nct_id:
        return {}

    url = _CT_STUDY_URL.format(nct_id=nct_id)
    params = {"format": "json"}
    backoff = 2
    for attempt in range(max_retries):
        r = None
        try:
            r = _rq.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            status = getattr(r, "status_code", None) if r is not None else None
            if status == 429 and attempt + 1 < max_retries:
                ra = (r.headers.get("Retry-After") if r is not None and r.headers
                      else None)
                wait = int(ra) if ra and str(ra).isdigit() else backoff
                if wait > _MAX_RETRY_AFTER_SECS:
                    log.warning(
                        "_fetch_study_by_id(%s): 429 with Retry-After=%ds "
                        "exceeds cap %ds — giving up",
                        nct_id, wait, _MAX_RETRY_AFTER_SECS,
                    )
                    return {}
                log.info("_fetch_study_by_id(%s): 429, sleeping %ds (attempt %d/%d)",
                         nct_id, wait, attempt + 1, max_retries)
                _time.sleep(wait)
                backoff *= 2
                continue
            log.warning("_fetch_study_by_id(%s): %s", nct_id, e)
            return {}
    return {}


# --- exec function ----------------------------------------------------------

def exec_trial_population(arguments, input_table, output_table, db_path):
    """Extract patient-population summary per arm for a list of NCT IDs.

    Two execution paths:

    1. **Cache-projection mode** (preferred). When `input_table` has a
       `_raw_study_json` column (populated by `successful_trials_classifier`),
       we parse those JSON blobs in-process. No HTTP calls, no rate limits.
    2. **Fetch fallback mode**. When the input table lacks the cache column
       OR when called standalone with `nct_ids=`, we GET each NCT from
       CT.gov. Sequential + politeness delay + 429 retry to be polite.
    """
    import json as _json
    import sqlite3

    # (nct_id, optional cached_study_dict) — when cached, no fetch is needed.
    todo: List[Tuple[str, Optional[Dict[str, Any]]]] = []

    # Chained mode: read from input table.
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

        nct_col = None
        for cand in ["nct_id", "NCT ID", "nctid", "_input_query"]:
            if any(c.lower() == cand.lower() for c in cols):
                nct_col = next(c for c in cols if c.lower() == cand.lower())
                break

        cache_col = None
        for cand in ["_raw_study_json", "_raw_study"]:
            if any(c.lower() == cand.lower() for c in cols):
                cache_col = next(c for c in cols if c.lower() == cand.lower())
                break

        if nct_col:
            seen = set()
            for r in rows:
                nct = r.get(nct_col)
                if not nct or nct in seen:
                    continue
                seen.add(nct)
                cached = None
                if cache_col:
                    raw = r.get(cache_col)
                    if raw:
                        try:
                            cached = _json.loads(raw)
                        except (ValueError, TypeError) as e:
                            log.warning("exec_trial_population: %s cached "
                                        "JSON unparseable, will refetch: %s", nct, e)
                            cached = None
                todo.append((nct, cached))

    # Standalone fallback (only when no chained input).
    if not todo and arguments.get("nct_ids"):
        seen = set()
        for v in str(arguments["nct_ids"]).split(","):
            v = v.strip()
            if v and v not in seen:
                seen.add(v)
                todo.append((v, None))

    if not todo:
        raise ValueError(
            "No NCT IDs provided — chain from a successful_trials_classifier "
            "table (column 'nct_id') or pass `nct_ids` as comma-separated.")

    cached_count = sum(1 for _, c in todo if c is not None)
    log.info(
        "exec_trial_population: %d NCT IDs (%d cached, %d to fetch)",
        len(todo), cached_count, len(todo) - cached_count,
    )

    # CT.gov rate-limits aggressively on per-NCT GETs. Sequential with a
    # ~0.5s politeness delay (validation.py:280 pattern) stays under the
    # per-IP threshold. 429 retries (with Retry-After cap) are the safety
    # net. Only used when we have NCTs WITHOUT a cached study dict.
    import time as _time

    def _fetch_with_delay(n: str) -> Dict[str, Any]:
        _time.sleep(0.5)
        return _fetch_study_by_id(n)

    rows_out: List[Dict[str, Any]] = []

    # Cached entries — process in-process, no I/O.
    for nct, cached in todo:
        if cached is None:
            continue
        arms = _extract_arms(cached)
        if not arms:
            arms = [{
                "arm_label": "", "arm_id": "", "arm_type": "",
                "arm_intervention": "",
            }]
        for arm in arms:
            rows_out.append(_row_for_arm(cached, arm, input_query=nct))

    # Uncached entries — fall back to fetch.
    to_fetch = [nct for nct, cached in todo if cached is None]
    if to_fetch:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future_to_nct = {pool.submit(_fetch_with_delay, n): n for n in to_fetch}
            for fut in as_completed(future_to_nct):
                nct = future_to_nct[fut]
                try:
                    study = fut.result()
                except Exception as e:
                    log.warning("exec_trial_population: %s failed: %s", nct, e)
                    continue
                if not study:
                    continue
                arms = _extract_arms(study)
                if not arms:
                    arms = [{
                        "arm_label": "", "arm_id": "", "arm_type": "",
                        "arm_intervention": "",
                    }]
                for arm in arms:
                    rows_out.append(_row_for_arm(study, arm, input_query=nct))

    log.info("exec_trial_population: %d arm rows for %d NCTs",
             len(rows_out), len(todo))
    return rows_out
