"""Custom tool: ClinicalTrials_search_by_intervention_and_condition

Searches ClinicalTrials.gov by intervention AND condition with synonym
expansion for precise recall. Uses query.intr (intervention name/description
fields) with OR'd synonyms from PubChem, OLS, NCI EVS, and isotope variant
generation.

Returns the actual trial list as a table (NCT ID, title, status, phase,
drugs, sponsor, etc.) — not just summary stats.
"""
from __future__ import annotations
import json, logging, re

log = logging.getLogger(__name__)

_CT_URL = "https://clinicaltrials.gov/api/v2/studies"

# Terms that genuinely indicate a biomarker-selected trial design.
# Intentionally narrow: "positive/negative/expression" alone match too many
# non-molecular contexts (ECOG performance, pregnancy test, etc.).
_BIOMARKER_TERMS = [
    "biomarker", "companion diagnostic", "molecularly selected",
    "genomically selected", "molecularly defined", "biomarker-selected",
    "tumor agnostic", "tumour agnostic", "basket trial", "basket study",
    "tissue agnostic",
]
# Regex for gene-specific molecular markers in eligibility text:
# matches "HER2-positive", "EGFR mutation", "NTRK fusion", "KRAS mutant", etc.
_GENE_MARKER_RE = re.compile(
    r'[A-Z][A-Z0-9]{1,8}[- ]?'
    r'(?:positive|negative|mutant|mutated|wild.?type|amplified|fusion|rearrangement|overexpression)',
)


def _has_biomarker(title, eligibility_text):
    """Return True if trial uses biomarker-selected design."""
    combined = f"{title} {eligibility_text}".lower()
    if any(t in combined for t in _BIOMARKER_TERMS):
        return True
    # Gene-specific molecular markers in eligibility criteria
    if eligibility_text and _GENE_MARKER_RE.search(eligibility_text):
        return True
    return False


def _sanitize_for_ctgov(s):
    """Strip IUPAC bracket notation that breaks CT.gov Lucene query parsing.

    CT.gov v2 uses Lucene under the hood where '[' and ']' are reserved
    range-query characters. Even percent-encoded, the decoded form triggers
    a 400 from Lucene's parser. Strip bracket groups (e.g. '[1,2,3]am')
    and collapse whitespace.
    """
    sanitized = re.sub(r'\[[^\]]*\]', '', s).strip()
    return ' '.join(sanitized.split()) or s


def _expand_intervention(term, timeout=15):
    """Expand an intervention term into OR'd synonyms for query.intr."""
    try:
        try:
            from ..sr_synonyms import expand_synonyms
        except (ImportError, SystemError):
            try:
                from ..sr_synonyms import expand_synonyms
            except ImportError:
                from integration.genai.research_pipeline.tools.synonyms import expand_synonyms
    except ImportError:
        log.warning("synonym expansion not available, using raw term")
        return f'"{_sanitize_for_ctgov(term)}"'

    synonyms = expand_synonyms(term, timeout=timeout, max_terms=12)
    # Sanitize each synonym: PubChem returns IUPAC names which may contain
    # bracket groups that break CT.gov's Lucene query parser.
    synonyms = [_sanitize_for_ctgov(s) for s in synonyms]
    synonyms = [s for s in synonyms if s]
    return " OR ".join(f'"{s}"' for s in synonyms)


def search_ctgov(intervention, condition="", page_size=100, timeout=30):
    """Search ClinicalTrials.gov v2 with query.intr + query.cond.

    Args:
        intervention: already-expanded OR'd synonym string for query.intr
        condition: disease/condition string for query.cond
        page_size: max results per page

    Returns list of normalized trial dicts.
    """
    import requests as _rq

    params = {
        "query.intr": intervention,
        "pageSize": str(page_size),
        "countTotal": "true",
        "format": "json",
    }
    if condition:
        params["query.cond"] = condition

    try:
        r = _rq.get(_CT_URL, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("search_ctgov: %s", e)
        return [], 0

    studies = data.get("studies") or []
    total = data.get("totalCount", len(studies))

    trials = []
    for study in studies:
        proto = study.get("protocolSection") or {}
        ident = proto.get("identificationModule") or {}
        stat = proto.get("statusModule") or {}
        design = proto.get("designModule") or {}
        sponsor = (proto.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
        arms_mod = proto.get("armsInterventionsModule") or {}
        cond_mod = proto.get("conditionsModule") or {}
        elig_mod = proto.get("eligibilityModule") or {}

        interventions = arms_mod.get("interventions") or []
        drug_names = [i["name"] for i in interventions
                      if i.get("name") and i.get("type") == "DRUG"]
        all_intv = [i["name"] for i in interventions if i.get("name")]

        nct_id = ident.get("nctId", "")
        title = ident.get("briefTitle", "")
        eligibility_text = elig_mod.get("eligibilityCriteria", "")
        trials.append({
            "nct_id": nct_id,
            "title": title,
            "status": stat.get("overallStatus", ""),
            "phases": "; ".join(design.get("phases") or []),
            "enrollment": str((design.get("enrollmentInfo") or {}).get("count", "")),
            "sponsor": sponsor.get("name", ""),
            "drug_names": "; ".join(drug_names),
            "interventions": "; ".join(all_intv),
            "conditions": "; ".join(cond_mod.get("conditions") or []),
            "start_date": (stat.get("startDateStruct") or {}).get("date", ""),
            "completion_date": (stat.get("completionDateStruct") or {}).get("date", ""),
            "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
            "has_biomarker": _has_biomarker(title, eligibility_text),
        })

    log.info("search_ctgov: %d / %d trials", len(trials), total)
    return trials, total


def exec_ct_search(arguments, input_table, output_table, db_path):
    """Search ClinicalTrials.gov by intervention and condition.

    Standalone mode: pass intervention + condition as arguments.
    Chained mode: reads intervention names from input table, searches for each.
    """
    import sqlite3

    intervention = arguments.get("intervention", arguments.get("drug", ""))
    condition = arguments.get("condition", arguments.get("indication",
                arguments.get("disease", "")))

    terms = []

    # Chained mode: read intervention names from input table
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

        # Find intervention/drug column
        drug_col = None
        for candidate in ["drug_name", "drug_names", "drug.name", "drug",
                           "intervention", "interventions", "_input_drug_name",
                           "approvedSymbol", "gene_name", "gene", "symbol",
                           "_input_gene_name"]:
            if any(c.lower() == candidate.lower() for c in all_cols):
                drug_col = next(c for c in all_cols if c.lower() == candidate.lower())
                break
        if drug_col:
            terms = [r[drug_col] for r in rows if r.get(drug_col)]

    # Standalone mode
    if not terms and intervention:
        terms = [t.strip() for t in intervention.split(",") if t.strip()]

    if not terms:
        raise ValueError(
            "No intervention/drug specified — provide 'intervention' parameter "
            "or chain from a table with drug names")

    log.info("exec_ct_search: %d terms, condition='%s'", len(terms), condition)

    all_results = []
    for term in terms:
        expanded = _expand_intervention(term)
        log.info("exec_ct_search: '%s' expanded to: %s", term, expanded[:100])
        trials, total = search_ctgov(expanded, condition)
        for t in trials:
            t["_input_query"] = term
            t["total_matching"] = str(total)
        all_results.extend(trials)

    log.info("exec_ct_search: %d total trials for %d terms",
             len(all_results), len(terms))
    return all_results
