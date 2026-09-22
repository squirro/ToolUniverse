"""Custom tool: patent_landscape

Searches patent databases for IP encumbrance around a target.
Supports three entity types via `entity_type` parameter:
  - gene: searches gene symbol + protein name (cross-refs UniProt)
  - drug: searches drug name + synonyms
  - topic: raw keyword search

Data sources:
  - EuropePMC patent search (primary, free, no API key)
  - EPO OPS (secondary, needs EPO_OPS_KEY/EPO_OPS_SECRET)

Score 0-1 where higher = more freedom to operate (fewer patents).
"""
from __future__ import annotations
import json
import logging
import os
import re
from datetime import datetime

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entity-type specific query builders
# ---------------------------------------------------------------------------

def _build_gene_query(term, indication=""):
    """Build EPMC patent query for a gene target."""
    parts = [f'"{term}"']
    if indication:
        parts.append(f'("{indication}")')
    return " AND ".join(parts)


def _build_drug_query(term, indication=""):
    """Build EPMC patent query for a drug name."""
    parts = [f'"{term}"']
    if indication:
        parts.append(f'("{indication}")')
    return " AND ".join(parts)


def _build_topic_query(term, indication=""):
    """Build EPMC patent query for a freeform topic."""
    parts = [term]
    if indication:
        parts.append(f'("{indication}")')
    return " AND ".join(parts)


_QUERY_BUILDERS = {
    "gene": _build_gene_query,
    "drug": _build_drug_query,
    "topic": _build_topic_query,
}


# ---------------------------------------------------------------------------
# EPMC patent search
# ---------------------------------------------------------------------------

def fetch_epmc_patents(query, max_results=100, timeout=30):
    """Search EuropePMC for patents matching query.

    Returns list of dicts with: title, authorString, pubYear, source, id.
    """
    import requests as _rq
    results = []
    cursor = "*"
    page_size = min(100, max_results)

    while len(results) < max_results:
        try:
            r = _rq.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={
                "query": f"({query}) AND SRC:PAT",
                "resultType": "lite",
                "pageSize": str(page_size),
                "cursorMark": cursor,
                "format": "json",
            }, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning("fetch_epmc_patents: %s", e)
            break

        result_list = data.get("resultList", {}).get("result", [])
        if not result_list:
            break

        for item in result_list:
            results.append({
                "title": item.get("title", ""),
                "applicant": item.get("authorString", ""),
                "year": item.get("pubYear", ""),
                "source": item.get("source", "PAT"),
                "patent_id": item.get("id", ""),
            })

        next_cursor = data.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    log.info("fetch_epmc_patents: %d results for '%s'", len(results), query[:60])
    return results


# ---------------------------------------------------------------------------
# EPO OPS patent search (optional, needs API keys)
# ---------------------------------------------------------------------------

def _get_epo_token(timeout=20):
    """Get EPO OPS OAuth2 access token. Returns token string or None."""
    key = os.environ.get("EPO_OPS_KEY", "").strip()
    secret = os.environ.get("EPO_OPS_SECRET", "").strip()
    if not key or not secret:
        return None

    import subprocess
    try:
        result = subprocess.run(
            ["curl", "--http1.1", "-s", "-X", "POST",
             "https://ops.epo.org/3.2/auth/accesstoken",
             "-H", "Content-Type: application/x-www-form-urlencoded",
             "-d", "grant_type=client_credentials",
             "-u", f"{key}:{secret}"],
            capture_output=True, text=True, timeout=timeout,
        )
        data = json.loads(result.stdout)
        return data.get("access_token")
    except Exception as e:
        log.warning("_get_epo_token: %s", e)
        return None


def fetch_epo_patents(query, token, max_results=25, timeout=30):
    """Search EPO OPS published-data for patents. Uses curl --http1.1."""
    import subprocess
    import urllib.parse
    if not token:
        return []

    # URL-encode the query so multi-word terms (topics, drug names) work correctly.
    # EPO expects the q parameter to be properly percent-encoded in the URL.
    epo_query = urllib.parse.quote(f'ta="{query}"', safe='="')
    try:
        result = subprocess.run(
            ["curl", "--http1.1", "-s",
             f"https://ops.epo.org/3.2/rest-services/published-data/search?"
             f"q={epo_query}&Range=1-{min(max_results, 100)}",
             "-H", f"Authorization: Bearer {token}",
             "-H", "Accept: application/json"],
            capture_output=True, text=True, timeout=timeout,
        )
        data = json.loads(result.stdout)
    except Exception as e:
        log.warning("fetch_epo_patents: %s", e)
        return []

    results = []
    search_result = (data.get("ops:world-patent-data") or {}).get(
        "ops:biblio-search") or {}
    docs = search_result.get("ops:search-result", {}).get(
        "ops:publication-reference") or []
    if isinstance(docs, dict):
        docs = [docs]

    for doc in docs:
        doc_id = doc.get("document-id") or {}
        if isinstance(doc_id, list):
            doc_id = doc_id[0] if doc_id else {}
        country = doc_id.get("country", {}).get("$", "")
        doc_number = doc_id.get("doc-number", {}).get("$", "")
        kind = doc_id.get("kind", {}).get("$", "")
        pub_date = doc_id.get("date", {}).get("$", "")
        patent_id = f"{country}{doc_number}{kind}"
        # Extract year: prefer pub_date field; fall back to year embedded in WO/EP number
        # e.g. "WO2026076198A1" → 2026, "EP3876975B1" → year not deducible from number alone
        year = pub_date[:4] if pub_date else ""
        if not year:
            m = re.search(r'^(?:WO|EP|US)(\d{4})\d', patent_id)
            if m:
                year = m.group(1)
        results.append({
            "patent_id": patent_id,
            "year": year,
            "title": "",  # EPO search doesn't return titles — need biblio fetch
            "applicant": "",
            "source": "EPO",
        })

    log.info("fetch_epo_patents: %d results for '%s'", len(results), query[:60])
    return results


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def assess_patent_landscape(query_term, patents):
    """Score IP freedom based on patent count and recency.

    Returns dict with ip_freedom_score (0-1, higher = more freedom),
    patent counts, and top titles.
    """
    if not patents:
        return {
            "ip_freedom_score": 1.0,
            "patent_count": 0,
            "recent_patent_count": 0,
            "top_patent_titles": "",
            "patent_applicants": "",
            "evidence": ["no patents found"],
        }

    current_year = datetime.now().year
    recent_cutoff = current_year - 5

    total = len(patents)
    recent = 0
    applicants = {}
    titles = []

    for p in patents:
        try:
            year = int(p.get("year", 0))
        except (ValueError, TypeError):
            year = 0
        if year >= recent_cutoff:
            recent += 1
        app = p.get("applicant", "").strip()
        if app:
            applicants[app] = applicants.get(app, 0) + 1
        title = p.get("title", "").strip()
        if title and len(titles) < 5:
            titles.append(title)

    # Scoring: weighted by recency
    # Recent patents count 2x
    weighted_count = (total - recent) + recent * 2.0

    if weighted_count == 0:
        score = 1.0
    elif weighted_count <= 5:
        score = 0.7
    elif weighted_count <= 20:
        score = 0.4
    else:
        score = max(0.05, 0.2 - (weighted_count - 20) * 0.005)

    score = round(score, 3)

    # Top applicants
    top_applicants = sorted(applicants.items(), key=lambda x: -x[1])[:5]
    applicant_str = "; ".join(f"{a} ({c})" for a, c in top_applicants)

    evidence = [f"{total} patents ({recent} recent, last 5 years)"]
    if top_applicants:
        evidence.append(f"top applicants: {applicant_str}")

    return {
        "ip_freedom_score": score,
        "patent_count": total,
        "recent_patent_count": recent,
        "top_patent_titles": "; ".join(titles),
        "patent_applicants": applicant_str,
        "evidence": evidence,
    }


# ---------------------------------------------------------------------------
# Auto-detect entity type from input table columns
# ---------------------------------------------------------------------------

_GENE_COLUMNS = {"approvedsymbol", "gene_symbol", "gene_name", "symbol",
                  "gene", "target.approvedsymbol", "_input_gene_name"}
_DRUG_COLUMNS = {"drug_name", "drug.name", "drug.id", "chemblid", "_input_drug_name"}


def _detect_entity_type(col_names):
    """Guess entity_type from input table column names."""
    lower_cols = {c.lower() for c in col_names}
    if lower_cols & _DRUG_COLUMNS:
        return "drug"
    if lower_cols & _GENE_COLUMNS:
        return "gene"
    return "topic"


def _find_query_column(entity_type, all_cols):
    """Find the column to pull search terms from, based on entity_type."""
    if entity_type == "gene":
        candidates = ["approvedSymbol", "approvedsymbol", "gene_symbol",
                       "gene_name", "symbol", "gene",
                       "target.approvedSymbol", "_input_gene_name"]
    elif entity_type == "drug":
        candidates = ["drug_name", "drug.name", "name",
                       "_input_drug_name", "drug"]
    else:
        # topic: try any text-like column
        candidates = ["query", "topic", "term", "name", "gene_name", "drug_name"]

    for candidate in candidates:
        if any(c.lower() == candidate.lower() for c in all_cols):
            return next(c for c in all_cols if c.lower() == candidate.lower())
    return None


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

def exec_patent_landscape(arguments, input_table, output_table, db_path):
    """Search patents for entities in input table. Supports gene, drug, or topic
    entity types with different search strategies."""
    import sqlite3
    import time
    from concurrent.futures import ThreadPoolExecutor as _TPE, as_completed

    indication = arguments.get("indication", "")
    entity_type = arguments.get("entity_type", "").lower()

    terms = []
    query_col = None  # initialize before conditional block to avoid UnboundLocalError
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

        if not entity_type:
            entity_type = _detect_entity_type(all_cols)

        query_col = _find_query_column(entity_type, all_cols)
        if query_col:
            terms = [r[query_col] for r in rows if r.get(query_col)]

    # Standalone mode: extract search term from arguments
    if not terms:
        if not entity_type:
            entity_type = "topic"
        query_arg = arguments.get("query", arguments.get("gene", arguments.get(
                    "gene_name", arguments.get("drug", arguments.get(
                    "drug_name", arguments.get("target", arguments.get("topic", "")))))))
        if query_arg:
            terms = [t.strip() for t in query_arg.split(",") if t.strip()]

    if not terms:
        raise ValueError("No search terms found — provide an input table or 'query'/'gene'/'drug' parameter")

    log.info("exec_patent_landscape: entity_type='%s'", entity_type)
    log.info("exec_patent_landscape: %d terms from column '%s', indication='%s'",
             len(terms), query_col or "arguments", indication)

    # Try to get EPO token (optional)
    epo_token = _get_epo_token()

    query_builder = _QUERY_BUILDERS.get(entity_type, _build_topic_query)

    def _search_one(term):
        time.sleep(0.2)  # rate limit
        query = query_builder(term, indication)
        # EPMC as primary
        patents = fetch_epmc_patents(query)
        # EPO as supplement (if token available)
        if epo_token:
            epo_patents = fetch_epo_patents(term, epo_token)
            # Merge, deduplicate by patent_id
            seen_ids = {p["patent_id"] for p in patents}
            for ep in epo_patents:
                if ep["patent_id"] not in seen_ids:
                    patents.append(ep)
                    seen_ids.add(ep["patent_id"])

        result = assess_patent_landscape(term, patents)
        return {
            "_input_query": term,
            "ip_freedom_score": result["ip_freedom_score"],
            "patent_count": str(result["patent_count"]),
            "recent_patent_count": str(result["recent_patent_count"]),
            "top_patent_titles": result["top_patent_titles"],
            "patent_applicants": result["patent_applicants"],
            "patent_details": "; ".join(result["evidence"]),
        }

    results = []
    with _TPE(max_workers=3) as pool:
        futures = {pool.submit(_search_one, t): t for t in terms}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                log.warning("exec_patent_landscape: %s failed: %s",
                            futures[future], e)

    results.sort(key=lambda r: -float(r["ip_freedom_score"]))

    log.info("exec_patent_landscape: %d/%d terms scored", len(results), len(terms))
    return results
