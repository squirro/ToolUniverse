"""DSR-726: the FAERS signal table travels to the writer as rows, and the literature
search is one query per flagged reaction.

Rung 1 handed the writer three parallel lists (`signal_aes`, `prrs`, `prr_urls`) and
one run mis-indexed two footnotes. A row cannot be mis-indexed.
"""
import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner, _COMPUTE_OPS, loop_items

TERMS = ["MYELODYSPLASTIC SYNDROME", "NAUSEA", "RENAL IMPAIRMENT"]
PRR = {"MYELODYSPLASTIC SYNDROME": 7.5, "NAUSEA": 1.1, "RENAL IMPAIRMENT": 2.3}


def _url(term):
    return f"https://api.fda.gov/drug/event.json?search={term.replace(' ', '+')}"


def _drive(prr=PRR, graph=None):
    calls, asked = [], []

    def execute(tool, a):
        calls.append((tool, a))
        if tool == "DailyMed_search_spls":
            return {"data": [{"setid": "s1", "title": "LUTATHERA (lutetium Lu 177 dotatate)"}]}
        if tool == "FAERS_count_reactions_by_drug_event":
            return {"result": [{"term": t} for t in TERMS]}
        if tool == "FAERS_calculate_disproportionality":
            ae = a["adverse_event"]
            return {"data": {"metrics": {"PRR": {"value": prr[ae]}}}, "source_url": _url(ae)}
        if tool == "PubMed_search_articles":
            return {"data": [{"pmid": "1", "title": "t", "pub_year": 2024, "doi_url": "d"}]}
        return {}

    runner = SkillRunner(graph or load_graph("clinical-data-integration"), execute=execute,
                         ask=lambda q: asked.append(q) or {n: ["stub"] for n in q["wants"]})
    run_id = runner.start({"drug_name": "lutetium Lu 177 dotatate"})["run_id"]
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
    assert "compute" not in {q["step"] for q in asked}, "the table is arithmetic; nobody is asked"


def test_the_three_lists_stay_in_the_bundle_for_this_rung():
    state, _, _ = _drive()
    facts = state["facts"]
    assert facts["signal_aes"] == TERMS
    assert facts["prrs"] == [7.5, 1.1, 2.3]
    assert facts["prr_urls"] == [_url(t) for t in TERMS]


# --- literature as a loop --------------------------------------------------------

def test_the_literature_loop_fans_over_exactly_the_flagged_reactions():
    state, calls, _ = _drive()
    queries = [a["query"] for tool, a in calls if tool == "PubMed_search_articles"]
    assert len(queries) == 2
    assert "MYELODYSPLASTIC SYNDROME" in queries[0] and "lutetium Lu 177 dotatate" in queries[0]
    assert "RENAL IMPAIRMENT" in queries[1]
    rows = state["facts"]["literature_rows"]
    assert [r["reaction"] for r in rows] == ["MYELODYSPLASTIC SYNDROME", "RENAL IMPAIRMENT"]
    assert rows[0]["pmids"] == ["1"]


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
