"""Custom tool: trial_outcomes_extractor (DSR-404a).

For each trial (chained from successful_trials_classifier OR comma-separated
nct_ids), extract response-level statistics from CT.gov v2 resultsSection.
Output is a flat table: one row per trial × arm × endpoint, carrying
point estimates per arm AND per-comparison analyses (effect size, CI,
p-value, statistical method).

Per the ticket: "All values include provenance — no LLM-invented numbers."
Every row carries a `source_field` pointer back into the raw study JSON for
audit traceability.

This is a pure cache projection over `_raw_study_json` when chained from
successful_trials_classifier (no I/O). Falls back to per-NCT fetch only
in standalone mode.
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

_CT_STUDY_URL = "https://clinicaltrials.gov/api/v2/studies/{nct_id}"
_MAX_RETRY_AFTER_SECS = 30


# --- Pure helpers -----------------------------------------------------------

def _resolve_arm_label(study: Dict[str, Any], group_id: str) -> str:
    """Map an outcome `groupId` (e.g. OG000) to a human-readable arm label.

    Strategy:
      1. Look in resultsSection.outcomeMeasuresModule.groups[] (when present,
         CT.gov maps OG000 -> arm title here).
      2. Fall back to position match against protocolSection.armGroups[]:
         OG000 -> armGroups[0], OG001 -> armGroups[1], etc.
      3. Last resort: return the raw group_id so provenance is preserved
         (caller can still see which group the row came from).
    """
    rs = study.get("resultsSection") or {}
    om = rs.get("outcomeMeasuresModule") or {}
    for g in om.get("groups") or []:
        if g.get("id") == group_id and g.get("title"):
            return g["title"]
    # Position fallback
    if group_id.startswith("OG"):
        try:
            idx = int(group_id[2:])
        except ValueError:
            return group_id
        proto = study.get("protocolSection") or {}
        arms = (proto.get("armsInterventionsModule") or {}).get("armGroups") or []
        if 0 <= idx < len(arms):
            return arms[idx].get("label", group_id)
    return group_id


def _extract_outcome_rows(study: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Project resultsSection.outcomeMeasuresModule into per-arm × per-endpoint rows.

    For each outcomeMeasure:
      - Walk classes[0].categories[0].measurements[] for per-arm point estimates.
      - Walk analyses[0] for per-comparison statistics (denormalised onto
        EVERY arm row, since the same comparison statistic applies to all
        groups it spans — chat-friendly for downstream filtering).

    Returns [] when no resultsSection (trial has no posted results).
    """
    rs = study.get("resultsSection") or {}
    om = rs.get("outcomeMeasuresModule") or {}
    measures = om.get("outcomeMeasures") or []

    rows: List[Dict[str, Any]] = []
    for m_idx, m in enumerate(measures):
        title = m.get("title", "")
        if not title:
            continue
        endpoint_type = m.get("type", "")
        param_type = m.get("paramType", "")
        unit = m.get("unitOfMeasure", "")
        time_frame = m.get("timeFrame", "")

        # Per-comparison analysis (one analysis row applies to multiple groups)
        analyses = m.get("analyses") or []
        a = analyses[0] if analyses else {}
        analysis_param_type = a.get("paramType", "") or ""
        analysis_param_value = a.get("paramValue", "") or ""
        ci_pct = a.get("ciPctValue", "") or ""
        ci_lower = a.get("ciLowerLimit", "") or ""
        ci_upper = a.get("ciUpperLimit", "") or ""
        pvalue = a.get("pValue", "") or ""
        statistical_method = a.get("statisticalMethod", "") or ""
        ni_type = a.get("nonInferiorityType", "") or ""

        # Per-arm point estimates
        classes = m.get("classes") or []
        if not classes:
            continue
        # We only consume the first class/category — multi-category measures
        # (e.g. Sex with Female/Male) belong in trial_population_summary, not
        # outcomes. Outcomes are typically single-category.
        categories = classes[0].get("categories") or []
        if not categories:
            continue
        measurements = categories[0].get("measurements") or []

        if not measurements:
            # No per-arm values, but maybe an analysis was posted across the
            # whole trial. Emit one synthetic row so the analysis is preserved.
            rows.append({
                "endpoint_name": title,
                "endpoint_type": endpoint_type,
                "param_type": param_type,
                "unit": unit,
                "time_frame": time_frame,
                "arm": "",
                "arm_group_id": "",
                "point_estimate": "",
                "lower_limit": "",
                "upper_limit": "",
                "analysis_param_type": analysis_param_type,
                "analysis_param_value": analysis_param_value,
                "ci_pct": ci_pct,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "pvalue": pvalue,
                "statistical_method": statistical_method,
                "non_inferiority_type": ni_type,
                "source_field": (
                    f"resultsSection.outcomeMeasuresModule.outcomeMeasures[{m_idx}]"
                ),
            })
            continue

        for meas in measurements:
            group_id = meas.get("groupId", "") or ""
            arm = _resolve_arm_label(study, group_id) if group_id else ""
            rows.append({
                "endpoint_name": title,
                "endpoint_type": endpoint_type,
                "param_type": param_type,
                "unit": unit,
                "time_frame": time_frame,
                "arm": arm,
                "arm_group_id": group_id,
                "point_estimate": meas.get("value", "") or "",
                "lower_limit": meas.get("lowerLimit", "") or "",
                "upper_limit": meas.get("upperLimit", "") or "",
                "analysis_param_type": analysis_param_type,
                "analysis_param_value": analysis_param_value,
                "ci_pct": ci_pct,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "pvalue": pvalue,
                "statistical_method": statistical_method,
                "non_inferiority_type": ni_type,
                "source_field": (
                    f"resultsSection.outcomeMeasuresModule.outcomeMeasures[{m_idx}]"
                ),
            })

    return rows


def _extract_pmids(study: Dict[str, Any]) -> str:
    """Free passthrough of CT.gov references[].pmid; semicolon-joined."""
    proto = study.get("protocolSection") or {}
    refs_mod = proto.get("referencesModule") or {}
    pmids = []
    for r in refs_mod.get("references") or []:
        pmid = r.get("pmid")
        if pmid:
            pmids.append(str(pmid))
    return "; ".join(pmids)


# --- Fetch primitive --------------------------------------------------------

def _fetch_study_by_id(
    nct_id: str, timeout: int = 30, max_retries: int = 3,
) -> Dict[str, Any]:
    """GET CT.gov v2 /studies/{nct_id}. Honors Retry-After up to 30s.

    Same retry/cap semantics as trial_population.py — the standalone
    fallback path. Chained mode (cache-projection) bypasses this entirely.
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
                _time.sleep(wait)
                backoff *= 2
                continue
            log.warning("_fetch_study_by_id(%s): %s", nct_id, e)
            return {}
    return {}


# --- exec function ----------------------------------------------------------

def exec_trial_outcomes(arguments, input_table, output_table, db_path):
    """Extract per-arm × per-endpoint outcome rows from CT.gov resultsSection.

    Two paths:
      1. Cache-projection (preferred): when input_table has _raw_study_json
         (populated by successful_trials_classifier), parse in-process — no
         HTTP, no rate limits.
      2. Fetch fallback: standalone with `nct_ids=` arg, or chained input
         lacking the cache column.
    """
    import sqlite3

    todo: List[Tuple[str, Optional[Dict[str, Any]]]] = []

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
                            cached = json.loads(raw)
                        except (ValueError, TypeError) as e:
                            log.warning("exec_trial_outcomes: %s cached JSON "
                                        "unparseable, will refetch: %s", nct, e)
                            cached = None
                todo.append((nct, cached))

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
        "exec_trial_outcomes: %d NCTs (%d cached, %d to fetch)",
        len(todo), cached_count, len(todo) - cached_count,
    )

    rows_out: List[Dict[str, Any]] = []

    # Cached entries — process in-process, no I/O.
    for nct, cached in todo:
        if cached is None:
            continue
        outcome_rows = _extract_outcome_rows(cached)
        pmids = _extract_pmids(cached)
        for r in outcome_rows:
            r["nct_id"] = nct
            r["references_pmids"] = pmids
            r["url"] = f"https://clinicaltrials.gov/study/{nct}" if nct else ""
            r["_input_query"] = nct
            rows_out.append(r)

    # Uncached entries — fall back to fetch.
    to_fetch = [nct for nct, c in todo if c is None]
    if to_fetch:
        import time as _time

        def _fetch_with_delay(n: str) -> Dict[str, Any]:
            _time.sleep(0.5)
            return _fetch_study_by_id(n)

        with ThreadPoolExecutor(max_workers=1) as pool:
            fut_to_nct = {pool.submit(_fetch_with_delay, n): n for n in to_fetch}
            for fut in as_completed(fut_to_nct):
                nct = fut_to_nct[fut]
                try:
                    study = fut.result()
                except Exception as e:
                    log.warning("exec_trial_outcomes: %s failed: %s", nct, e)
                    continue
                if not study:
                    continue
                outcome_rows = _extract_outcome_rows(study)
                pmids = _extract_pmids(study)
                for r in outcome_rows:
                    r["nct_id"] = nct
                    r["references_pmids"] = pmids
                    r["url"] = f"https://clinicaltrials.gov/study/{nct}" if nct else ""
                    r["_input_query"] = nct
                    rows_out.append(r)

    log.info("exec_trial_outcomes: %d outcome rows for %d NCTs",
             len(rows_out), len(todo))
    return rows_out
