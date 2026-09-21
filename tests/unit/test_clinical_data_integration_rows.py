"""DSR-726: the FAERS signal table travels to the writer as rows, and the literature
search is one query per flagged reaction.

Rung 1 handed the writer three parallel lists (`signal_aes`, `prrs`, `prr_urls`) and
one run mis-indexed two footnotes. A row cannot be mis-indexed.
"""
import re

import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner, _COMPUTE_OPS, loop_items

TERMS = ["MYELODYSPLASTIC SYNDROME", "NAUSEA", "RENAL IMPAIRMENT"]
PRR = {"MYELODYSPLASTIC SYNDROME": 7.5, "NAUSEA": 1.1, "RENAL IMPAIRMENT": 2.3}


def _url(term):
    return f"https://api.fda.gov/drug/event.json?search={term.replace(' ', '+')}"


_INDICATION = re.compile(r"TUMOU?R|NEOPLASM|CARCINOMA|CANCER|METASTA|PROGRESSION", re.I)


def _agent(question):
    """The agent's side of a run: it does the compute step's arithmetic, as the task asks."""
    if "prr_table" not in question["wants"]:
        return {name: ["stub"] for name in question["wants"]}
    rows = question["calls"][0]["arguments"]["rows"]
    table = [{**row, "flagged": row.get("prr") is not None and row["prr"] >= 2}
             for row in sorted(rows, key=lambda r: (r.get("prr") is None, -(r.get("prr") or 0)))]
    flagged = [row["term"] for row in table if row["flagged"]]
    return {"prr_table": table,
            "flagged_aes": [t for t in flagged if not _INDICATION.search(t)],
            "excluded_aes": [t for t in flagged if _INDICATION.search(t)],
            "method": "computed without code"}


def _drive(prr=PRR, graph=None, drug_name="lutetium Lu 177 dotatate", terms=TERMS):
    calls, asked = [], []

    def execute(tool, a):
        calls.append((tool, a))
        if tool == "DailyMed_search_spls":
            return {"data": [{"setid": "s1", "title": "LUTATHERA (lutetium Lu 177 dotatate)"}]}
        if tool == "FAERS_count_reactions_by_drug_event":
            return {"result": [{"term": t} for t in terms]}
        if tool == "FAERS_calculate_disproportionality":
            ae = a["adverse_event"]
            return {"data": {"metrics": {"PRR": {"value": prr[ae]}}}, "source_url": _url(ae)}
        if tool == "PubMed_search_articles":
            # the shape recorded from the live tool on sr-dev, 2026-09-21
            return {"status": "success",
                    "data": [{"pmid": "1", "title": "t", "pub_year": 2024, "doi_url": "d"}],
                    "metadata": {"count": 1, "total": 4120, "query": a["query"], "source": "PubMed"}}
        if tool == "search_clinical_trials":
            return {"data": {"total_count": 866, "studies": [
                {"NCT ID": "NCT1", "brief_title": "A", "overall_status": "COMPLETED", "phase": "PHASE3"},
                {"NCT ID": "NCT2", "brief_title": "B", "overall_status": "TERMINATED"}]}}
        return {}

    runner = SkillRunner(graph or load_graph("clinical-data-integration"), execute=execute,
                         ask=lambda q: asked.append(q) or _agent(q))
    run_id = runner.start({"drug_name": drug_name})["run_id"]
    for _ in range(100):
        if runner.advance(run_id)["finished"]:
            break
    else:
        raise AssertionError("the run did not finish")
    return runner.state(run_id), calls, asked


# --- rows, not lists ------------------------------------------------------------

def test_each_signal_row_carries_the_term_its_prr_its_flag_and_its_own_query_url():
    state, _, asked = _drive()
    assert state["facts"]["prr_table"] == [
        {"term": "MYELODYSPLASTIC SYNDROME", "prr": 7.5, "flagged": True, "url": _url("MYELODYSPLASTIC SYNDROME")},
        {"term": "RENAL IMPAIRMENT", "prr": 2.3, "flagged": True, "url": _url("RENAL IMPAIRMENT")},
        {"term": "NAUSEA", "prr": 1.1, "flagged": False, "url": _url("NAUSEA")},
    ]
    compute = [q for q in asked if q["step"] == "compute"]
    assert len(compute) == 1, "the agent does the arithmetic once; the check found nothing to re-ask"
    assert "problem" not in compute[0]


def test_the_signals_travel_as_rows_only_and_the_gateway_reads_the_rows():
    """The parallel lists are gone: a reaction without a PRR dropped out of one list and
    not the other. The rows carry term, value and link together."""
    state, _, _ = _drive()
    facts = state["facts"]
    assert facts["signal_aes"] == TERMS
    assert "prrs" not in facts and "prr_urls" not in facts
    assert [(r["term"], r["prr"], r["url"]) for r in facts["prr_rows"]] == [
        (t, PRR[t], _url(t)) for t in TERMS]
    assert facts["strong_signal"] is True


# --- literature as a loop --------------------------------------------------------

def test_the_literature_loop_fans_over_exactly_the_flagged_reactions():
    state, calls, _ = _drive()
    queries = [a["query"] for tool, a in calls if tool == "PubMed_search_articles"]
    # Untagged on purpose: PubMed maps the INN to its substance record and the
    # reaction to its MeSH heading. Tagged [Title/Abstract], "Lutathera AND
    # myelodysplastic syndrome" found 0 papers; untagged, 12 (probed 2026-09-07).
    assert queries == ["lutetium Lu 177 dotatate AND MYELODYSPLASTIC SYNDROME",
                       "lutetium Lu 177 dotatate AND RENAL IMPAIRMENT"]
    # One row for each paper, carrying its reaction and its own links: a paper without a
    # DOI cannot shift the DOI of the next one.
    assert state["facts"]["literature_rows"] == [
        {"reaction": reaction, "pmid": "1", "title": "t", "year": 2024, "doi": "d"}
        for reaction in ("MYELODYSPLASTIC SYNDROME", "RENAL IMPAIRMENT")]


def test_no_flagged_reaction_means_no_literature_search():
    state, calls, _ = _drive(prr={t: 1.0 for t in TERMS})
    assert [tool for tool, _ in calls if tool == "PubMed_search_articles"] == []
    assert state["facts"]["flagged_aes"] == []


# --- the two compute ops ---------------------------------------------------------

def test_flag_sorts_the_rows_by_the_field_and_flags_at_the_threshold():
    rows = [{"term": "a", "prr": 1.1}, {"term": "b", "prr": 7.5}, {"term": "c", "prr": 2.0}]
    out = _COMPUTE_OPS["flag"]({"rows": "r", "field": "prr", "threshold": 2}, {"r": rows})
    assert out == [{"term": "b", "prr": 7.5, "flagged": True},
                   {"term": "c", "prr": 2.0, "flagged": True},
                   {"term": "a", "prr": 1.1, "flagged": False}]


def test_flag_is_unresolved_when_the_rows_never_arrived():
    assert _COMPUTE_OPS["flag"]({"rows": "r", "field": "prr", "threshold": 2}, {}) is None


def test_pluck_takes_one_field_from_the_rows_that_pass():
    rows = [{"term": "b", "flagged": True}, {"term": "a", "flagged": False}, {"term": "c", "flagged": True}]
    assert _COMPUTE_OPS["pluck"]({"rows": "r", "field": "term", "where": "flagged"}, {"r": rows}) == ["b", "c"]
    assert _COMPUTE_OPS["pluck"]({"rows": "r", "field": "term"}, {"r": rows}) == ["b", "a", "c"]
    assert _COMPUTE_OPS["pluck"]({"rows": "r", "field": "term"}, {}) is None


# --- the loop item inside a longer template --------------------------------------

def test_the_loop_item_is_recovered_when_its_marker_sits_inside_a_longer_argument():
    spec = {"for_each": "flagged_aes", "as": "reaction",
            "calls": [{"tool": "PubMed_search_articles",
                       "arguments": {"query": "{drug_name}[Title/Abstract] AND {reaction}[Title/Abstract]"}}]}
    calls = [{"tool": "PubMed_search_articles",
              "arguments": {"query": "Lutathera[Title/Abstract] AND RENAL IMPAIRMENT[Title/Abstract]"}}]
    assert loop_items(spec, calls) == ["RENAL IMPAIRMENT"]


# --- compute rules resolve regardless of the order a store hands them back -------

def test_a_compute_that_reads_another_compute_resolves_whatever_the_declared_order():
    """GraphDB hands the rules back alphabetically; live, `flagged_aes` ran before
    `prr_table` existed and the literature loop was blocked."""
    from tooluniverse.skill_runner import absorb
    spec = {"id": "compute", "calls": [],
            "compute": {"flagged_aes": {"op": "pluck", "rows": "prr_table", "field": "term", "where": "flagged"},
                        "prr_table": {"op": "flag", "rows": "prr_rows", "field": "prr", "threshold": 2}}}
    out = absorb(spec, [], {"prr_rows": [{"term": "a", "prr": 7.5}, {"term": "b", "prr": 1.0}]})
    assert out["unresolved"] == []
    assert out["facts"]["flagged_aes"] == ["a"]


def test_the_process_read_back_from_the_store_still_searches_per_flagged_reaction():
    from rdflib import Graph
    from tooluniverse.skill_graph_bbo import from_bbo, to_bbo
    stored = from_bbo(Graph().parse(data=to_bbo(load_graph("clinical-data-integration")), format="turtle"))
    state, calls, _ = _drive(graph=stored)
    assert [u for u in state["unresolved"] if u["step"] == "compute"] == []
    assert [b for b in state["blocked"] if b["step"] == "literature"] == []
    assert state["facts"]["flagged_aes"] == ["MYELODYSPLASTIC SYNDROME", "RENAL IMPAIRMENT"]
    assert len([1 for tool, _ in calls if tool == "PubMed_search_articles"]) == 2


def test_the_literature_search_uses_the_inn_from_the_label_even_when_the_agent_bound_the_brand():
    """Live 2026-09-07 the agent bound "Lutathera"; untagged, the brand maps to the
    element and the PSMA prostate papers came back. DailyMed's title carries the INN."""
    _, calls, _ = _drive(drug_name="Lutathera")
    queries = [a["query"] for tool, a in calls if tool == "PubMed_search_articles"]
    assert queries == ["lutetium Lu 177 dotatate AND MYELODYSPLASTIC SYNDROME",
                       "lutetium Lu 177 dotatate AND RENAL IMPAIRMENT"]


# --- reported disease is not searched as an adverse event -------------------------

def test_pluck_sets_aside_the_rows_whose_field_matches_the_exclude_pattern():
    rows = [{"term": "NEUROENDOCRINE TUMOUR", "flagged": True}, {"term": "MDS", "flagged": True},
            {"term": "METASTASES TO LIVER", "flagged": True}, {"term": "NAUSEA", "flagged": False}]
    rule = {"rows": "r", "field": "term", "where": "flagged", "exclude_pattern": "TUMOU?R|METASTA"}
    assert _COMPUTE_OPS["pluck"](rule, {"r": rows}) == ["MDS"]


def test_the_literature_loop_skips_indication_terms_and_the_bundle_says_which():
    """Neuroendocrine tumour and liver metastases top Lutathera's PRR table: they are the
    disease treated, not adverse events. They stay in the table, flagged; the loop does
    not spend a search on them, and `excluded` names them."""
    terms = ["NEUROENDOCRINE TUMOUR", "METASTASES TO LIVER", "MYELODYSPLASTIC SYNDROME", "NAUSEA"]
    prr = {"NEUROENDOCRINE TUMOUR": 393.4, "METASTASES TO LIVER": 21.4, "MYELODYSPLASTIC SYNDROME": 7.5, "NAUSEA": 1.1}
    state, calls, _ = _drive(prr=prr, terms=terms)
    facts = state["facts"]
    assert [r["term"] for r in facts["prr_table"] if r["flagged"]] == terms[:3]
    assert facts["flagged_aes"] == ["MYELODYSPLASTIC SYNDROME"]
    assert [a["query"] for tool, a in calls if tool == "PubMed_search_articles"] == [
        "lutetium Lu 177 dotatate AND MYELODYSPLASTIC SYNDROME"]
    assert facts["excluded_aes"] == ["NEUROENDOCRINE TUMOUR", "METASTASES TO LIVER"]


# --- fetch wide: the source's maximum, and its total beside the rows ---------------

def test_trials_are_asked_for_at_the_sources_maximum_and_kept_as_one_row_each():
    """Four parallel lists cut at ten gave ten trials of 866, with nothing to say so."""
    state, calls, _ = _drive()
    (sent,) = [a for tool, a in calls if tool == "search_clinical_trials"]

    assert sent["pageSize"] == 1000
    assert state["facts"]["trial_rows"] == [
        {"nct_id": "NCT1", "title": "A", "status": "COMPLETED", "phase": "PHASE3"},
        {"nct_id": "NCT2", "title": "B", "status": "TERMINATED"}]
    assert "nct_ids" not in state["facts"]


def test_the_process_names_where_each_wide_source_reports_its_total():
    process = load_graph("clinical-data-integration")
    totals = {s["id"]: s.get("total") for s in process["steps"] if s["id"] in ("trials", "literature")}

    assert totals == {"trials": "data.total_count", "literature": "metadata.total"}
    assert process["tables"]["trial_rows"] == "evidence"


def test_the_declared_paths_find_the_totals_in_the_recorded_payloads(tmp_path):
    """A path that matches an invented payload proves nothing: live, every literature total read "unknown"."""
    from tooluniverse.skill_runner import source_total

    process = load_graph("clinical-data-integration")
    literature = next(s for s in process["steps"] if s["id"] == "literature")
    trials = next(s for s in process["steps"] if s["id"] == "trials")
    pubmed = {"status": "success", "data": [], "source_url": "u",
              "metadata": {"count": 200, "total": 4120, "query": "q", "source": "PubMed"}}
    ctgov = {"status": "success", "data": {"studies": [], "total_count": 866, "next_page_token": None},
             "metadata": {"source": "ClinicalTrials.gov API v2", "operation": "search"}}

    assert source_total(literature, [pubmed], ["DEAFNESS"]) == {"DEAFNESS": 4120}
    assert source_total(trials, [ctgov], None) == 866
