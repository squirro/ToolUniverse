"""The server runs the process: it holds the state, makes each step's calls and
evaluates every gateway itself, with no model in the control loop. The executor is
injected here, so these tests need no ToolUniverse and no network.
"""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_graph import GRAPHS_DIR, SkillGraphError, load_graph  # noqa: E402
from tooluniverse.skill_runner import (  # noqa: E402
    SkillPathError, SkillRunner, _derive, _dig, _fewest, _flag, _prevalence_tier, absorb, apply,
    carries, check_facts, new_run, next_runnable, normalised_executor, placed_mapping,
    question_for, resolved, source_total, substitute)

pytestmark = pytest.mark.unit


def test_a_mapped_path_keeps_one_entry_per_record():
    payload = {"records": [{"id": "A"}, {"other": "x"}, {"id": "C"}]}

    assert _dig(payload, "records[].id") == ["A", None, "C"]


def test_two_mapped_paths_over_the_same_records_stay_in_step():
    payload = {"records": [{"id": "A", "doi": "10.1/a"},
                           {"id": "B"},
                           {"id": "C", "doi": "10.1/c"}]}

    ids = _dig(payload, "records[].id")
    dois = _dig(payload, "records[].doi")

    assert len(ids) == len(dois) == 3
    assert ids[1] == "B" and dois[1] is None


def test_a_nested_mapped_segment_is_refused_rather_than_read_as_nothing():
    payload = {"a": [{"b": [{"c": 1}]}]}

    with pytest.raises(SkillPathError) as refused:
        _dig(payload, "a[].b[].c")

    assert "a[].b[].c" in str(refused.value)


def test_a_mapped_segment_over_something_that_is_not_a_list_is_refused():
    payload = {"records": {"id": "A"}}

    with pytest.raises(SkillPathError) as refused:
        _dig(payload, "records[].id")

    assert "records" in str(refused.value)


def test_a_malformed_path_is_blocked_rather_than_crashing_the_run():
    spec = {"id": "identity", "extract": {"ids": "a[].b[].c"}}

    outcome = absorb(spec, [{"a": [{"b": [{"c": 1}]}]}], {})

    assert "ids" not in outcome["facts"]
    assert any("a[].b[].c" in b["reason"] for b in outcome["blocked"])


def test_two_extract_rules_over_the_same_heterogeneous_records_stay_in_step_through_absorb():
    """The brief's `_dig`-level claim, proven through the step-execution path that actually runs it."""
    spec = {"id": "s", "extract": {"ids": "records[].id", "dois": "records[].doi"}}
    results = [{"records": [{"id": "A", "doi": "10.1/a"},
                            {"id": "B"},
                            {"id": "C", "doi": "10.1/c"}]}]

    outcome = absorb(spec, results, {})
    ids, dois = outcome["facts"]["ids"], outcome["facts"]["dois"]

    assert len(ids) == len(dois) == 3
    assert ids[1] == "B" and dois[1] is None


def test_two_collect_rules_over_the_same_heterogeneous_records_stay_in_step_through_absorb():
    spec = {"id": "s", "collect": {"ids": {"path": "records[].id", "flatten": True},
                                   "dois": {"path": "records[].doi", "flatten": True}}}
    results = [{"records": [{"id": "A", "doi": "10.1/a"},
                            {"id": "B"},
                            {"id": "C", "doi": "10.1/c"}]}]

    outcome = absorb(spec, results, {})
    ids, dois = outcome["facts"]["ids"], outcome["facts"]["dois"]

    assert len(ids) == len(dois) == 3
    assert ids[1] == "B" and dois[1] is None


def test_one_badly_shaped_payload_costs_only_that_payload_not_the_rule():
    """A mapped segment over something that is not a list depends on that one payload's shape;
    the payloads either side of it must still contribute what they hold."""
    spec = {"id": "s", "collect": {"ids": "records[].id"}}
    results = [{"records": [{"id": "A"}]}, {"records": "not a list"}, {"records": [{"id": "C"}]}]

    outcome = absorb(spec, results, {})

    assert outcome["facts"]["ids"] == [["A"], ["C"]]
    assert len([b for b in outcome["blocked"] if "ids" in b["reason"]]) == 1


def test_an_ontology_outage_reads_differently_from_a_term_no_ontology_knows():
    spec = {"mapping": {"requested_meddra": {}}}
    outcome = {"facts": {"requested_meddra": [{"term": "NEPHROTOXICITY", "concept": ["kidney"]}]}}

    def failed(term):
        return {"hp": {"error": "URLError: timed out"},
                "mondo": {"error": "URLError: timed out"}}

    def unknown(term):
        return {"hp": {"search": [], "ancestors": []},
                "mondo": {"search": [], "ancestors": []}}

    outage = placed_mapping(spec, outcome, failed)["facts"]["requested_meddra"][0]
    absent = placed_mapping(spec, outcome, unknown)["facts"]["requested_meddra"][0]

    assert outage["placing"] == absent["placing"] == "unknown"
    assert "the lookup service failed" in outage["note"]
    assert absent.get("note") is None


GRAPH = {
    "skill": "demo", "inputs": ["drug_name"],
    "steps": [
        {"id": "resolve",
         "calls": [{"tool": "resolve_drug", "arguments": {"name": "{drug_name}"}}],
         "extract": {"chembl_id": "data.id"}},
        {"id": "signals", "requires": ["resolve"],
         "calls": [{"tool": "disproportionality", "arguments": {"chembl_id": "{chembl_id}"}}],
         "extract": {"rows": "data.rows"},
         "derive": {"strong_signal": {"from": "rows", "field": "prr", "op": ">=",
                                      "value": 5, "mode": "any"}}},
        {"id": "stratify", "requires": ["signals"], "when": "strong_signal",
         "calls": [{"tool": "stratify", "arguments": {"chembl_id": "{chembl_id}"}}]},
        {"id": "report", "requires": ["signals"], "calls": []},
    ],
}
OK = {"resolve_drug": {"data": {"id": "CHEMBL88"}},
      "disproportionality": {"data": {"rows": [{"prr": 17.7}, {"prr": 1.2}]}},
      "stratify": {"data": {"sex": "F"}}}
WEAK = dict(OK, disproportionality={"data": {"rows": [{"prr": 1.1}]}})


def _runner(responses):
    """Injected executor: tool name -> response, or an Exception to raise."""
    calls = []

    def execute(tool, arguments):
        calls.append((tool, arguments))
        value = responses[tool]
        if isinstance(value, Exception):
            raise value
        return value

    return SkillRunner(GRAPH, execute=execute), calls


def _run_to_end(runner, inputs=None, limit=100):
    """Start a run, advance it until it finishes, and give back its run_id."""
    run_id = runner.start(inputs or {})["run_id"]
    for _ in range(limit):
        if runner.advance(run_id)["finished"]:
            return run_id
    raise AssertionError("the run did not finish")


def test_starting_a_run_returns_an_id_and_the_first_step():
    runner, _ = _runner(OK)
    run = runner.start({"drug_name": "cisplatin"})
    assert run["run_id"] and run["step"]["id"] == "resolve"


def test_two_runs_do_not_share_state():
    runner, _ = _runner(OK)
    a = runner.start({"drug_name": "cisplatin"})
    b = runner.start({"drug_name": "lutetium"})
    assert a["run_id"] != b["run_id"]
    runner.advance(a["run_id"])
    assert runner.state(b["run_id"])["done"] == []


def test_advancing_executes_the_step_s_calls_without_the_model():
    runner, calls = _runner(OK)
    runner.advance(runner.start({"drug_name": "cisplatin"})["run_id"])
    assert calls[0] == ("resolve_drug", {"name": "cisplatin"})


def test_what_a_step_extracts_composes_the_next_call():
    """An id out of step one becomes an argument of step two, unseen by the model."""
    runner, calls = _runner(OK)
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    runner.advance(run_id)
    runner.advance(run_id)
    assert calls[1] == ("disproportionality", {"chembl_id": "CHEMBL88"})


def test_the_caller_gets_the_extracted_values_not_the_raw_payload():
    runner, _ = _runner(OK)
    out = runner.advance(runner.start({"drug_name": "cisplatin"})["run_id"])
    assert out["extracted"] == {"chembl_id": "CHEMBL88"} and "data" not in out


@pytest.mark.parametrize("responses, decided, then", [(OK, True, "stratify"),
                                                      (WEAK, False, "report")])
def test_a_gateway_is_computed_from_the_data_not_reported_by_the_model(responses, decided, then):
    """prr 17.7 opens the gate, prr 1.1 leaves it shut: code decides, not the model."""
    runner, _ = _runner(responses)
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    runner.advance(run_id)
    out = runner.advance(run_id)
    assert out["extracted"]["strong_signal"] is decided
    assert out["next_step"]["id"] == then


def test_a_failing_call_is_recorded_and_the_run_carries_on():
    """A broken tool is not a reason to abandon the procedure."""
    runner, _ = _runner(dict(OK, disproportionality=RuntimeError("HTTP 500")))
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    runner.advance(run_id)
    out = runner.advance(run_id)
    assert out["failures"][0]["tool"] == "disproportionality"
    assert out["next_step"] is not None


def test_the_run_finishes_when_every_runnable_step_is_done():
    runner, _ = _runner(WEAK)
    run_id = _run_to_end(runner, {"drug_name": "cisplatin"})
    assert runner.state(run_id)["done"] == ["resolve", "signals", "report"]


FAERS_GRAPH = {
    "skill": "faers", "inputs": ["drug_name"],
    "steps": [
        {"id": "counts",
         "calls": [{"tool": "counts", "arguments": {"medicinalproduct": "{drug_name}"}}],
         "extract": {"top_aes": {"path": "result[].term", "limit": 2}}},
        {"id": "signals", "requires": ["counts"], "for_each": "top_aes", "as": "adverse_event",
         "calls": [{"tool": "dispro", "arguments": {"adverse_event": "{adverse_event}"}}]},
    ],
}
FAERS_OK = {"counts": {"result": [{"term": "DEATH", "count": 1598},
                                  {"term": "HOT FLUSH", "count": 784},
                                  {"term": "FALL", "count": 475}]},
            "dispro": {"data": {"prr": 2.0}}}


def _faers():
    """MedDRA terms are case- and spelling-strict, so they are carried, never retyped."""
    calls = []
    runner = SkillRunner(FAERS_GRAPH, execute=lambda t, a: calls.append((t, a)) or FAERS_OK[t])
    return runner, calls, runner.start({"drug_name": "enzalutamide"})["run_id"]


def test_a_list_of_records_maps_to_the_field_the_next_step_needs():
    runner, _, run_id = _faers()
    assert runner.advance(run_id)["extracted"]["top_aes"] == ["DEATH", "HOT FLUSH"]


def test_the_mapped_terms_drive_one_call_each_verbatim():
    runner, calls, run_id = _faers()
    runner.advance(run_id)
    runner.advance(run_id)
    assert [a["adverse_event"] for t, a in calls if t == "dispro"] == ["DEATH", "HOT FLUSH"]


def test_a_dotted_path_into_the_first_record_still_works():
    """DailyMed puts the setid the label phases need at data.0.setid."""
    graph = {"skill": "dm", "inputs": ["drug_name"], "steps": [
        {"id": "spl", "calls": [{"tool": "spls", "arguments": {"query": "{drug_name}"}}],
         "extract": {"setid": "data.0.setid"}}]}
    runner = SkillRunner(graph, execute=lambda t, a: {
        "data": [{"title": "XTANDI", "setid": "b129fdc9-1d8e-425c"}]})
    out = runner.advance(runner.start({"drug_name": "enzalutamide"})["run_id"])
    assert out["extracted"]["setid"] == "b129fdc9-1d8e-425c"


BLOCKED_GRAPH = {
    "skill": "blocked", "inputs": ["drug_name"],
    "steps": [
        {"id": "counts", "calls": [{"tool": "counts", "arguments": {}}],
         "extract": {"top_aes": "nowhere.at.all"}},
        {"id": "signals", "requires": ["counts"], "for_each": "top_aes", "as": "ae",
         "calls": [{"tool": "dispro", "arguments": {"ae": "{ae}"}}]},
        {"id": "trials", "requires": ["counts"],
         "calls": [{"tool": "trials", "arguments": {"q": "{drug_name}"}}]},
    ],
}


def test_a_step_whose_inputs_are_missing_is_blocked_not_fatal():
    runner = SkillRunner(BLOCKED_GRAPH, execute=lambda t, a: {"result": []})
    run_id = runner.start({"drug_name": "enzalutamide"})["run_id"]
    runner.advance(run_id)                   # counts — the extraction misses
    out = runner.advance(run_id)             # signals — cannot be built
    assert "top_aes" in out["blocked"][0]["reason"]


def test_the_run_continues_past_a_blocked_step():
    """The other sources do not depend on FAERS terms — they must still run."""
    ran = []
    runner = SkillRunner(BLOCKED_GRAPH, execute=lambda t, a: ran.append(t) or {"result": []})
    run_id = _run_to_end(runner, {"drug_name": "enzalutamide"})
    assert "trials" in ran and runner.state(run_id)["blocked"]


DERIVE_GRAPH = {
    "skill": "d", "inputs": ["drug"],
    "steps": [
        {"id": "signals", "calls": [{"tool": "dispro", "arguments": {}}],
         "extract": {"rows": "data.results"},
         "derive": {"strong": {"from": "rows", "field": "prr", "op": ">=", "value": 5,
                               "mode": "any"}}},
        {"id": "stratify", "requires": ["signals"], "when": "strong",
         "calls": [{"tool": "strat", "arguments": {}}]},
        {"id": "report", "requires": ["signals"], "calls": []},
    ],
}


def _run_derive_graph(payload):
    runner = SkillRunner(DERIVE_GRAPH, execute=lambda t, a: payload)
    return runner.advance(runner.start({"drug": "enzalutamide"})["run_id"])


def test_a_gateway_over_a_missing_fact_is_unknown_not_false():
    """A missing input and a genuine negative are different answers, and only one
    of them is safe to branch on."""
    assert _run_derive_graph({"data": {}})["extracted"]["strong"] is None


def test_an_unknown_gateway_is_reported_so_the_skip_is_not_silent():
    out = _run_derive_graph({"data": {}})
    assert any("strong" in b["reason"] for b in out["blocked"]), out["blocked"]


def test_a_gateway_over_real_but_empty_rows_is_a_genuine_no():
    """Rows came back and none reached the threshold — that IS a decision."""
    out = _run_derive_graph({"data": {"results": []}})
    assert out["extracted"]["strong"] is False and out["next_step"]["id"] == "report"


def test_a_derive_over_rows_that_all_lack_the_field_is_undecided():
    rule = {"from": "rows", "field": "prr", "op": ">=", "value": 5, "mode": "any"}
    facts = {"rows": [{"ror": 9.0}, {"ror": 12.0}]}

    assert _derive(rule, facts) is None


def test_a_derive_over_rows_of_the_wrong_type_is_undecided():
    rule = {"from": "rows", "field": "prr", "op": ">=", "value": 5, "mode": "any"}
    facts = {"rows": [{"prr": "not reported"}, {"prr": "n/a"}]}

    assert _derive(rule, facts) is None


def test_a_derive_with_mode_all_over_zero_usable_rows_is_not_vacuously_true():
    rule = {"from": "rows", "field": "prr", "op": ">=", "value": 5, "mode": "all"}
    facts = {"rows": [{"ror": 9.0}]}

    assert _derive(rule, facts) is None


def test_a_genuinely_empty_result_is_still_a_no():
    rule = {"from": "rows", "field": "prr", "op": ">=", "value": 5, "mode": "any"}

    assert _derive(rule, {"rows": []}) is False


def test_one_usable_row_among_unusable_ones_still_decides():
    rule = {"from": "rows", "field": "prr", "op": ">=", "value": 5, "mode": "any"}
    facts = {"rows": [{"prr": "n/a"}, {"prr": 17.7}]}

    assert _derive(rule, facts) is True


def test_a_bare_none_row_is_unusable_not_a_field_lookup():
    """_dig maps a record missing the field to a bare None; _derive must read that as
    unusable, not attempt row.get(field) on a non-dict."""
    rule = {"from": "rows", "field": "prr", "op": ">=", "value": 5, "mode": "any"}
    facts = {"rows": [None, None]}

    assert _derive(rule, facts) is None


def test_a_row_whose_flagged_field_will_not_parse_is_recorded_as_unparseable():
    rule = {"rows": "prr_rows", "field": "prr", "threshold": 5}
    facts = {"prr_rows": [{"term": "A", "prr": 17.7},
                          {"term": "B", "prr": "3.1 (0.8-9.4)"}]}

    rows = _flag(rule, facts)
    unparseable = [r for r in rows if r["term"] == "B"][0]

    assert unparseable["flagged"] is None
    assert unparseable["unparseable"] == "3.1 (0.8-9.4)"


COLLECT_GRAPH = {
    "skill": "c", "inputs": ["drug"],
    "steps": [
        {"id": "counts", "calls": [{"tool": "counts", "arguments": {}}],
         "extract": {"terms": "[].term"}},
        {"id": "signals", "requires": ["counts"], "for_each": "terms", "as": "t",
         "calls": [{"tool": "dispro", "arguments": {"ae": "{t}"}}],
         "collect": {"prrs": "data.metrics.PRR.value"},
         "derive": {"strong": {"from": "prrs", "op": ">=", "value": 5, "mode": "any"}}},
    ],
}


@pytest.mark.parametrize("prrs, strong", [([7.5, 1.2], True), ([5.0, 1.2], True),
                                          ([1.1, 1.2], False)])
def test_a_loop_step_gathers_every_value_and_the_gateway_decides_from_them(prrs, strong):
    """One metrics object per call, so `extract` would take only the first."""
    values = iter(prrs)

    def execute(tool, arguments):
        if tool == "counts":
            return [{"term": "A"}, {"term": "B"}]
        return {"data": {"metrics": {"PRR": {"value": next(values)}}}}

    runner = SkillRunner(COLLECT_GRAPH, execute=execute)
    run_id = runner.start({"drug": "x"})["run_id"]
    runner.advance(run_id)
    out = runner.advance(run_id)
    assert out["extracted"]["prrs"] == prrs
    assert out["extracted"]["strong"] is strong


@pytest.mark.parametrize("returned, expected", [
    ([{"term": "DEATH"}], {"result": [{"term": "DEATH"}]}),
    ({"status": "success", "data": {"id": "X"}}, {"status": "success", "data": {"id": "X"}}),
    ('{"data": {"id": "X"}}', {"data": {"id": "X"}}),
    ("no studies found", {"result": "no studies found"}),
])
def test_every_return_shape_is_normalised_the_way_execute_tool_normalises_it(returned, expected):
    """One door: the runner sees exactly what the agent sees."""
    assert normalised_executor(lambda call: returned)("t", {}) == expected


def test_the_call_is_passed_in_the_shape_run_one_function_expects():
    seen = {}
    normalised_executor(lambda call: seen.update(call) or {})("counts", {"medicinalproduct": "X"})
    assert seen == {"name": "counts", "arguments": {"medicinalproduct": "X"}}


def test_the_bundle_carries_the_facts_and_what_went_wrong():
    """Payloads are kept per step and handed over once at the end, so they never
    pass through the transcript on the way."""
    runner = SkillRunner(GRAPH, execute=lambda t, a: {"data": {"id": "CHEMBL88"}})
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    runner.advance(run_id)
    bundle = runner.handover(run_id)
    assert bundle["facts"]["chembl_id"] == "CHEMBL88"
    assert bundle["steps_done"] == ["resolve"]
    assert bundle["failures"] == [] and bundle["blocked"] == []


def test_a_regex_lifts_a_value_out_of_a_returned_string():
    """FAERS indexes the brand and the SPL title starts with it, so the graph chains
    brand -> FAERS instead of hoping the model retries."""
    graph = {"skill": "b", "inputs": ["drug_name"], "steps": [
        {"id": "spl", "calls": [{"tool": "spls", "arguments": {}}],
         "extract": {"brand": {"path": "data.0.title", "regex": r"^([A-Za-z0-9-]+)"}}}]}
    title = "LUTATHERA (LUTETIUM LU 177 DOTATATE) INJECTION [AAA USA, INC.]"
    runner = SkillRunner(graph, execute=lambda t, a: {"data": [{"title": title}]})
    run_id = runner.start({"drug_name": "lutetium lu 177 dotatate"})["run_id"]
    assert runner.advance(run_id)["extracted"]["brand"] == "LUTATHERA"


def test_a_value_falls_back_to_another_fact_when_the_lift_fails():
    """No brand in the title falls back to the name the question gave us."""
    graph = {"skill": "b", "inputs": ["drug_name"], "steps": [
        {"id": "spl", "calls": [{"tool": "spls", "arguments": {}}],
         "extract": {"faers_name": {"path": "data.0.title", "regex": r"^([A-Z]{4,})",
                                    "default_from": "drug_name"}}}]}
    runner = SkillRunner(graph, execute=lambda t, a: {"data": [{"title": "x"}]})
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    assert runner.advance(run_id)["extracted"]["faers_name"] == "cisplatin"


# A term that exists only in the question is an input, unioned with the ranked ones.
UNION_GRAPH = {
    "skill": "u", "inputs": ["drug_name", "requested_aes"],
    "steps": [
        {"id": "counts", "calls": [{"tool": "counts", "arguments": {}}],
         "extract": {"top_aes": {"path": "result[].term", "limit": 3}},
         "combine": {"signal_aes": {"union": ["requested_aes", "top_aes"], "limit": 5}}},
        {"id": "signals", "requires": ["counts"], "for_each": "signal_aes", "as": "ae",
         "calls": [{"tool": "d", "arguments": {"ae": "{ae}"}}]},
    ],
}
COUNTS = {"result": [{"term": "DEATH"}, {"term": "NAUSEA"}, {"term": "FATIGUE"}]}
REQUESTED = ["MYELODYSPLASTIC SYNDROME", "RENAL IMPAIRMENT"]


def _union(**inputs):
    runner = SkillRunner(UNION_GRAPH, execute=lambda t, a: COUNTS)
    run_id = runner.start({"drug_name": "LUTATHERA", **inputs})["run_id"]
    return runner.advance(run_id)["extracted"]["signal_aes"]


def test_the_terms_the_question_named_are_kept_even_when_they_are_not_frequent():
    got = _union(requested_aes=REQUESTED)
    assert got[:2] == REQUESTED and "DEATH" in got


def test_the_requested_terms_come_first_so_a_cap_cannot_drop_them():
    got = _union(requested_aes=REQUESTED)
    assert len(got) == 5 and got[0] == "MYELODYSPLASTIC SYNDROME"


def test_a_question_that_names_nothing_still_runs_on_frequency():
    assert _union() == ["DEATH", "NAUSEA", "FATIGUE"]


def test_a_duplicate_between_requested_and_frequent_is_not_run_twice():
    assert _union(requested_aes=["DEATH"]).count("DEATH") == 1


REPAIR_GRAPH = {
    "skill": "r", "inputs": ["drug_name"],
    "steps": [{"id": "spl",
               "calls": [{"tool": "spls", "arguments": {"drug_name": "{drug_name}"}}],
               "extract": {"setid": "data.0.setid"},
               "repair": {"argument": "drug_name", "when_missing": "setid"}}],
}
GOOD = {"data": [{"setid": "72d1a024"}]}


def _executor(good_for):
    seen = []

    def execute(tool, arguments):
        seen.append(arguments.get("drug_name"))
        return GOOD if arguments.get("drug_name") == good_for else {"data": []}

    return execute, seen


def test_a_failed_lookup_is_retried_with_what_the_agent_suggests():
    """A name variant is world knowledge the agent has and the server does not, so
    the model is an oracle for one narrow lookup; the server still validates."""
    execute, seen = _executor("lutetium lu 177 dotatate")
    runner = SkillRunner(REPAIR_GRAPH, execute=execute,
                         ask=lambda q: ["lutetium lu 177 dotatate"])
    out = runner.advance(runner.start({"drug_name": "lutetium Lu-177 dotatate"})["run_id"])
    assert out["extracted"]["setid"] == "72d1a024"
    assert seen == ["lutetium Lu-177 dotatate", "lutetium lu 177 dotatate"]


def test_the_repair_question_names_the_tool_and_what_came_back():
    execute, _ = _executor("never")
    asked = {}
    runner = SkillRunner(REPAIR_GRAPH, execute=execute, ask=lambda q: asked.update(q) or [])
    runner.advance(runner.start({"drug_name": "lutetium Lu-177 dotatate"})["run_id"])
    assert asked["tool"] == "spls" and asked["argument"] == "drug_name"
    assert asked["value"] == "lutetium Lu-177 dotatate"


def test_repair_gives_up_after_two_attempts():
    """Two is enough for a spelling or a brand, and not enough to spend a minute
    on a lookup that will never resolve."""
    execute, seen = _executor("never")
    runner = SkillRunner(REPAIR_GRAPH, execute=execute,
                         ask=lambda q: ["variant one", "variant two", "variant three"])
    out = runner.advance(runner.start({"drug_name": "original"})["run_id"])
    assert seen == ["original", "variant one", "variant two"]
    assert any("could not be resolved" in b["reason"] for b in out["blocked"])


def test_a_lookup_that_works_first_time_never_asks():
    execute, seen = _executor("lutetium lu 177 dotatate")
    called = []
    runner = SkillRunner(REPAIR_GRAPH, execute=execute, ask=lambda q: called.append(q) or [])
    runner.advance(runner.start({"drug_name": "lutetium lu 177 dotatate"})["run_id"])
    assert called == [] and len(seen) == 1


def test_without_an_ask_callback_the_runner_behaves_exactly_as_before():
    execute, seen = _executor("never")
    runner = SkillRunner(REPAIR_GRAPH, execute=execute)
    runner.advance(runner.start({"drug_name": "original"})["run_id"])
    assert seen == ["original"]


# Repair is the recovery; a declared value that never arrives is the honesty when
# there is none.
MISS_GRAPH = {
    "skill": "m", "inputs": ["drug_name"],
    "steps": [{"id": "identity", "calls": [{"tool": "spls", "arguments": {}}],
               "extract": {"setid": "data.0.setid"}, "produces": ["setid"]},
              {"id": "report", "requires": ["identity"], "calls": []}],
}


def _miss(data):
    return SkillRunner(MISS_GRAPH, execute=lambda t, a: {"data": data})


def test_a_declared_value_that_never_arrives_is_recorded():
    runner = _miss([])
    out = runner.advance(runner.start({"drug_name": "x"})["run_id"])
    assert out["unresolved"] == [{"step": "identity", "fact": "setid"}]


def test_an_unresolved_value_does_not_stop_the_run():
    """The other steps may not need it — but the report must be able to say so."""
    runner = _miss([])
    run_id = runner.start({"drug_name": "x"})["run_id"]
    runner.advance(run_id)
    assert runner.advance(run_id)["finished"] is True


def test_the_bundle_carries_what_never_resolved():
    runner = _miss([])
    run_id = runner.start({"drug_name": "x"})["run_id"]
    runner.advance(run_id)
    assert runner.handover(run_id)["unresolved"] == [{"step": "identity", "fact": "setid"}]


def test_a_value_that_does_arrive_is_not_recorded_as_unresolved():
    runner = _miss([{"setid": "72d1a024"}])
    assert runner.advance(runner.start({"drug_name": "x"})["run_id"])["unresolved"] == []


def test_absorb_extracts_by_path_regex_limit_and_default():
    """The pure pieces touch no network, clock or random source, so an async driver
    hands its results to the same functions the sync driver uses."""
    spec = {"id": "s", "extract": {
        "setid": "data.0.setid",
        "brand": {"path": "data.0.title", "regex": "^([A-Za-z0-9-]{3,})"},
        "terms": {"path": "result[].term", "limit": 2},
        "name": {"path": "data.0.missing", "default_from": "drug_name"},
        "never": "data.0.absent"}}
    results = [{"data": [{"setid": "72d1", "title": "LUTATHERA (lutetium) kit"}]},
               {"result": [{"term": "A"}, {"term": "B"}, {"term": "C"}]}]
    out = absorb(spec, results, facts={"drug_name": "lutathera"})
    assert out["facts"] == {"setid": "72d1", "brand": "LUTATHERA",
                            "terms": ["A", "B"], "name": "lutathera"}
    assert out["unresolved"] == ["never"] and out["blocked"] == []


def test_absorb_collects_combines_and_derives_and_blocks_an_unknown():
    spec = {"id": "prr",
            "collect": {"prrs": "data.metrics.PRR.value"},
            "combine": {"signal_aes": {"union": ["requested", "top"], "limit": 3}},
            "derive": {"strong": {"from": "prrs", "op": ">=", "value": 5, "mode": "any"},
                       "ghost": {"from": "never_extracted", "op": ">", "value": 0}}}
    results = [{"data": {"metrics": {"PRR": {"value": 7.1}}}},
               {"data": {"metrics": {"PRR": {"value": 0.9}}}}, {"data": {}}]
    out = absorb(spec, results, facts={"requested": ["MDS"],
                                       "top": ["MDS", "Nausea", "Rash"]})
    assert out["facts"]["prrs"] == [7.1, 0.9]
    assert out["facts"]["signal_aes"] == ["MDS", "Nausea", "Rash"]
    assert out["facts"]["strong"] is True and "ghost" not in out["facts"]
    assert out["undecided"] == ["ghost"]
    assert out["blocked"] == [{"step": "prr",
                               "reason": "cannot decide ghost: never_extracted was "
                                         "never extracted, so the branch was not taken"}]


def test_a_collect_that_gathers_nothing_is_named_in_unresolved():
    spec = {"id": "literature", "collect": {"papers": {"path": "resultList.result",
                                                      "fields": ["pmid", "title"]}}}

    outcome = absorb(spec, [{"resultList": {"result": []}}], {})

    assert "papers" not in outcome["facts"]
    assert "papers" in outcome["unresolved"]


def test_a_declared_produces_name_that_nothing_created_is_named_in_unresolved():
    spec = {"id": "identity", "extract": {"chembl_id": "data.id"},
            "produces": ["chembl_id", "approval_history"]}

    outcome = absorb(spec, [{"data": {"id": "CHEMBL88"}}], {})

    assert outcome["facts"]["chembl_id"] == "CHEMBL88"
    assert "approval_history" in outcome["unresolved"]


def test_a_combine_over_an_empty_gathering_writes_no_fact():
    spec = {"id": "candidates", "combine": {"shortlist": {"union": ["from_a", "from_b"]}}}

    outcome = absorb(spec, [{}], {"from_a": [], "from_b": []})

    assert "shortlist" not in outcome["facts"]
    assert "shortlist" in outcome["unresolved"]


def test_a_source_answering_two_hundred_with_an_empty_list_does_not_vanish():
    """The live shape: a 200 with an empty collection is not a missing fact, and not an answer."""
    spec = {"id": "trials", "collect": {"trial_rows": {"path": "studies",
                                                       "fields": ["nctId", "phase"]}}}

    outcome = absorb(spec, [{"studies": []}], {})

    assert "trial_rows" in outcome["unresolved"]
    assert "trial_rows" not in outcome["facts"]


def test_resolved_is_true_only_when_the_guarded_value_arrived():
    spec = {"id": "identity", "extract": {"setid": "data.0.setid", "title": "data.0.title"}}
    repair = {"argument": "drug_name", "when_missing": "setid"}
    assert resolved(spec, repair, [{"data": []}, {"data": [{"setid": "72d1"}]}])
    assert not resolved(spec, repair, [{"data": []}, {"data": [{"title": "no id"}]}])


def test_substitute_replaces_the_argument_only_where_a_call_carries_it():
    calls = [{"tool": "DailyMed_search_spls", "arguments": {"drug_name": "lu 177"}},
             {"tool": "OpenFDA_history", "arguments": {"operation": "history",
                                                       "drug_name": "lu 177"}},
             {"tool": "unrelated", "arguments": {"query": "x"}}]
    out = substitute(calls, "drug_name", "Lutathera")
    assert [c["arguments"] for c in out] == [
        {"drug_name": "Lutathera"},
        {"operation": "history", "drug_name": "Lutathera"},
        {"query": "x"}]
    assert calls[0]["arguments"]["drug_name"] == "lu 177", "the input is not mutated"


def test_apply_records_everything_a_step_leaves_on_the_run():
    run = new_run({"drug_name": "x"})
    outcome = {"facts": {"setid": "72d1"}, "unresolved": ["brand"],
               "blocked": [{"step": "identity", "reason": "r"}], "undecided": []}
    apply(run, "identity", failures=[{"tool": "t", "error": "E"}], outcome=outcome)
    assert run["done"] == ["identity"]
    assert "results" not in run, "results live in the Working Record, never on the run"
    assert run["facts"] == {"drug_name": "x", "setid": "72d1"}
    assert run["failures"] == [{"tool": "t", "error": "E", "step": "identity"}], \
        "a failure names its step, so a step blocked on a missing fact can name its cause"
    assert run["unresolved"] == [{"step": "identity", "fact": "brand"}]
    assert run["blocked"] == [{"step": "identity", "reason": "r"}]


def test_start_accepts_the_run_id_a_host_already_has():
    """Temporal names the run; the runner must not invent a second identity."""
    runner, _ = _runner(OK)
    out = runner.start({"drug_name": "x"}, run_id="skill-demo-42")
    assert out["run_id"] == "skill-demo-42"
    assert runner.state("skill-demo-42")["facts"] == {"drug_name": "x"}


def test_collect_with_match_keeps_the_first_matching_item_per_call():
    """The lookup answers UPHENO:, MP: and HP: ids; one HP id per symptom is picked."""
    spec = {"id": "phenotypes",
            "collect": {"hpo_ids": {"path": "data.items[].id", "match": "^HP:"},
                        "everything": "data.items[].id"}}
    results = [{"data": {"items": [{"id": "UPHENO:7000263"}, {"id": "MP:0031058"},
                                   {"id": "HP:0001433"}, {"id": "HP:5210171"}]}},
               {"data": {"items": [{"id": "MP:0000001"}]}},
               {"data": {"items": [{"id": "HP:0000252"}]}}]
    out = absorb(spec, results, facts={})
    assert out["facts"]["hpo_ids"] == ["HP:0001433", "HP:0000252"]
    assert out["facts"]["everything"] == [["UPHENO:7000263", "MP:0031058", "HP:0001433",
                                           "HP:5210171"], ["MP:0000001"], ["HP:0000252"]]


JUDGED = {
    "skill": "judged", "inputs": ["symptoms"],
    "steps": [
        {"id": "hypothesis", "calls": [],
         "produces": ["primary_keyword", "working_hypothesis"],
         "judge": ["primary_keyword", "working_hypothesis"]},
        {"id": "phenotypes", "requires": ["hypothesis"],
         "for_each": "symptoms", "as": "symptom",
         "calls": [{"tool": "hpo", "arguments": {"query": "{symptom}"}}],
         "collect": {"hpo_ids": {"path": "data.items[].id", "match": "^HP:"}},
         "produces": ["hpo_ids", "discriminating_hpo_ids"],
         "judge": ["discriminating_hpo_ids"]},
        {"id": "search", "requires": ["phenotypes"],
         "calls": [{"tool": "orphanet", "arguments": {"query": "{primary_keyword}"}}]},
    ],
}
HPO = {"hpo": {"data": {"items": [{"id": "MP:1"}, {"id": "HP:0001433"}]}},
       "orphanet": {"data": []}}


def _judged_runner(answers, responses=HPO):
    asked = []

    def ask(question):
        asked.append(question)
        return answers.get(question.get("kind"), {})

    return SkillRunner(JUDGED, execute=lambda tool, a: responses[tool], ask=ask), asked


def test_a_judge_step_asks_once_after_its_calls_and_keeps_the_answer():
    runner, asked = _judged_runner({"judge": {"primary_keyword": "storage disorder",
                                              "working_hypothesis": "Gaucher"}})
    run_id = runner.start({"symptoms": ["hepatosplenomegaly"]})["run_id"]
    out = runner.advance(run_id)
    assert out["step_id"] == "hypothesis"
    assert asked == [{"kind": "judge", "step": "hypothesis",
                      "wants": ["primary_keyword", "working_hypothesis"],
                      "context": {"symptoms": ["hepatosplenomegaly"]}}]
    assert runner.state(run_id)["facts"]["primary_keyword"] == "storage disorder"
    assert out["extracted"]["working_hypothesis"] == "Gaucher"
    assert out["unresolved"] == []


def test_a_judge_step_sees_what_its_own_calls_extracted():
    """The HP ids come from the lookups, and the judge must see them to choose
    which two discriminate."""
    runner, asked = _judged_runner({"judge": {"primary_keyword": "k",
                                              "working_hypothesis": "h",
                                              "discriminating_hpo_ids": ["HP:0001433"]}})
    run_id = runner.start({"symptoms": ["hepatosplenomegaly"]})["run_id"]
    runner.advance(run_id)
    runner.advance(run_id)
    assert asked[-1]["step"] == "phenotypes"
    assert asked[-1]["wants"] == ["discriminating_hpo_ids"]
    assert asked[-1]["context"]["hpo_ids"] == ["HP:0001433"]
    assert runner.state(run_id)["facts"]["discriminating_hpo_ids"] == ["HP:0001433"]


def test_a_judged_name_the_model_does_not_answer_is_unresolved():
    runner, _ = _judged_runner({"judge": {"primary_keyword": "k"}})
    run_id = runner.start({"symptoms": ["x"]})["run_id"]
    out = runner.advance(run_id)
    assert out["unresolved"] == [{"step": "hypothesis", "fact": "working_hypothesis"}]
    assert "working_hypothesis" not in runner.state(run_id)["facts"]


def test_a_produced_name_that_is_not_judged_is_a_defect_not_a_question():
    """A missed extraction path must never become something the model invents."""
    graph = {"skill": "g", "inputs": [], "steps": [
        {"id": "s", "calls": [{"tool": "t", "arguments": {}}],
         "extract": {"setid": "data.0.setid"}, "produces": ["setid"]}]}
    asked = []
    runner = SkillRunner(graph, execute=lambda tool, a: {"data": []},
                         ask=lambda q: asked.append(q) or {"setid": "invented"})
    run_id = runner.start({})["run_id"]
    out = runner.advance(run_id)
    assert asked == []
    assert out["unresolved"] == [{"step": "s", "fact": "setid"}]
    assert "setid" not in runner.state(run_id)["facts"]


def test_without_an_oracle_a_judge_step_records_its_names_as_unresolved():
    runner = SkillRunner(JUDGED, execute=lambda tool, a: HPO[tool])
    out = runner.advance(runner.start({"symptoms": ["x"]})["run_id"])
    assert out["step_id"] == "hypothesis"
    assert [u["fact"] for u in out["unresolved"]] == ["primary_keyword", "working_hypothesis"]


@pytest.mark.parametrize("skill", sorted(p.stem for p in GRAPHS_DIR.glob("*.yaml")))
def test_every_shipped_process_finishes_with_stub_tools_and_a_stub_oracle(skill):
    """The standing net: a YAML edit that the runner cannot execute fails here,
    not in a live run. Tools answer nothing; the oracle answers every judged name."""
    graph = load_graph(skill)
    runner = SkillRunner(graph, execute=lambda tool, a: {},
                         ask=lambda q: {name: ["stub"] for name in q["wants"]})
    run_id = _run_to_end(runner, {name: ["stub"] for name in graph.get("inputs", [])})
    state = runner.state(run_id)
    facts = state["facts"]
    off = {s["id"] for s in graph["steps"]
           if (s.get("when") and not facts.get(s["when"]))            # gate closed
           or (s.get("for_each") in facts and not facts[s["for_each"]])}  # empty loop
    assert set(state["done"]) | set(state["skipped"]) | off == {s["id"] for s in graph["steps"]}


def test_rare_disease_diagnosis_runs_start_to_finish_with_judgement():
    """Three judgement points, one HP id per symptom, genes per resolved candidate,
    no step blocked and no fact unresolved."""
    responses = {
        "get_HPO_ID_by_phenotype": {"data": {"items": [{"id": "MP:1"}, {"id": "HP:0001433"}]}},
        # a bare list is wrapped as {"result": [...]}, the way the runner sees it
        "get_joint_associated_diseases_by_HPO_ID_list": {"result": ["Gaucher disease"]},
        "Orphanet_search_diseases": {"data": {"results": [
            {"ORPHAcode": 355, "Preferred term": "Gaucher disease"}]}},
        "Orphanet_get_genes": {"data": {"orpha_code": "355", "genes": [{"Symbol": "GBA"}]}},
        "HPO_get_diseases_by_phenotype": {"data": {"diseases": [{"id": f"D{i}"} for i in range(190)]}},
        "HPO_get_term_hierarchy": {"data": [{"id": "HP:0003271", "name": "Visceromegaly"}]},
        "Orphanet_get_phenotypes": {"data": {"orpha_code": "355", "preferred_term": "Gaucher disease",
                                             "phenotypes": [{"hpo_id": "HP:0001433", "hpo_term": "Hepatosplenomegaly"}]}},
        "Orphanet_get_natural_history": {"data": {"orpha_code": "355", "preferred_term": "Gaucher disease",
                                                  "type_of_inheritance": ["Autosomal recessive"],
                                                  "average_age_of_onset": ["All ages"]}},
        "Orphanet_get_epidemiology": {"data": {"orpha_code": "355", "preferred_term": "Gaucher disease",
                                               "prevalences": [{"class": "1-9 / 100 000"}]}},
        "OpenTargets_get_disease_ids_by_name": {"data": {"search": {"hits": [
            {"id": "MONDO_0018150", "name": "Gaucher disease"}]}}},
        "OpenTargets_get_associated_targets_by_disease_efoId": {"data": {"disease": {
            "id": "MONDO_0018150", "name": "Gaucher disease", "associatedTargets": {"rows": [
                {"target": {"approvedSymbol": "GBA"}, "score": 0.9}]}}}},
        "EuropePMC_search_articles": {"data": [{"title": "GBA in Gaucher"}]},
        "MyGene_query_genes": {"data": {"hits": [{"symbol": "GBA"}]}},
        "GTEx_get_expression_summary": {"data": []},
    }
    answers = {"primary_keyword": "lysosomal storage disorder",
               "working_hypothesis": "Gaucher disease",
               "discriminating_features": ["hepatosplenomegaly"],
               "discriminating_hpo_ids": ["HP:0001433"],
               "top_candidate": "Gaucher disease",
               "optimuskg_genes": [{"gene": "GBA", "relation": "CAUSES", "evidence_score": 0.8}],
               "overlap_rows": [{"orpha_code": "355", "preferred_term": "Gaucher disease", "n": 1, "N": 1,
                                 "overlap_pct": 100, "grade": "T1", "matched_hpo_ids": ["HP:0001433"]}]}
    calls, asked = [], []
    runner = SkillRunner(
        load_graph("rare-disease-diagnosis"),
        execute=lambda tool, a: calls.append((tool, a)) or responses[tool],
        ask=lambda q: asked.append(q) or {n: answers[n] for n in q["wants"]})
    run_id = _run_to_end(runner, {"symptoms": ["hepatosplenomegaly", "coarse facies"]})
    state = runner.state(run_id)
    assert state["blocked"] == [] and state["unresolved"] == []
    assert state["facts"]["hpo_ids"] == ["HP:0001433", "HP:0001433"]
    assert [(q["step"], q["kind"]) for q in asked if q["kind"] == "judge"] == [
        ("hypothesis", "judge"), ("discriminating", "judge"), ("keyword_search", "judge")]
    assert {q["step"] for q in asked if q["kind"] == "delegate"} == {"gene_evidence_optimuskg"}
    assert state["facts"]["overlap_rows"][0]["grade"] == "T1"
    assert state["facts"]["genes"] == ["GBA"]
    assert ("get_joint_associated_diseases_by_HPO_ID_list",
            {"HPO_ID_list": ["HP:0001433"], "limit": 30}) in calls
    assert ("Orphanet_search_diseases",
            {"query": "lysosomal storage disorder", "limit": 20}) in calls
    assert ("MyGene_query_genes", {"query": "GBA",
            "fields": "symbol,name,entrezgene,ensembl.gene,summary"}) in calls
    assert "variant" not in state["done"], "no variant supplied, so that phase is off"


def test_the_bundle_says_which_tools_the_server_called_per_step():
    """The agent's trace shows no execute_tool for a server-side run, so the bundle
    carries the record of what ran, repair retries included."""
    runner, _ = _runner(OK)
    run_id = _run_to_end(runner, {"drug_name": "cisplatin"})
    assert runner.handover(run_id)["calls"] == {
        "resolve": ["resolve_drug"], "signals": ["disproportionality"],
        "stratify": ["stratify"], "report": []}


def test_the_bundle_carries_step_notes_and_the_report_guidance():
    """The writer must see what the author knows is noise."""
    graph = {"skill": "g", "inputs": [],
             "report": "Classify every signal against the label. Say which terms are nonspecific.",
             "steps": [{"id": "a", "calls": [], "notes": "A NOT_FOUND here is normal."},
                       {"id": "b", "calls": []}]}
    runner = SkillRunner(graph, execute=lambda t, a: {})
    bundle = runner.handover(_run_to_end(runner))
    assert bundle["report"] == ("Classify every signal against the label. "
                                "Say which terms are nonspecific.")
    assert bundle["notes"] == {"a": "A NOT_FOUND here is normal."}


def test_extract_can_exclude_values_the_author_knows_are_noise():
    spec = {"id": "faers_counts",
            "extract": {"top_aes": {"path": "result[].term", "limit": 4,
                                    "exclude": ["ILL-DEFINED DISORDER", "DEATH"]}}}
    results = [{"result": [{"term": "ILL-DEFINED DISORDER"}, {"term": "NAUSEA"},
                           {"term": "DEATH"}, {"term": "FATIGUE"}, {"term": "RASH"},
                           {"term": "COUGH"}]}]
    out = absorb(spec, results, facts={})
    assert out["facts"]["top_aes"] == ["NAUSEA", "FATIGUE", "RASH", "COUGH"], "excluded before the cap"
    assert out["excluded"] == {"top_aes": ["ILL-DEFINED DISORDER", "DEATH"]}


def test_a_delegated_step_asks_the_agent_to_make_the_calls_and_takes_the_answer():
    graph = {"skill": "d", "inputs": ["drug_name"], "steps": [
        {"id": "web_context",
         "delegate": [{"tool": "exa_web_search", "arguments": {"query": "{drug_name} safety"}}],
         "produces": ["web_context"]}]}
    asked = []
    runner = SkillRunner(graph, execute=lambda t, a: {},
                         ask=lambda q: asked.append(q) or {"web_context": ["hit 1", "hit 2"]})
    run_id = runner.start({"drug_name": "Lutathera"})["run_id"]
    out = runner.advance(run_id)
    assert asked == [{"kind": "delegate", "step": "web_context", "wants": ["web_context"],
                      "context": {"drug_name": "Lutathera"},
                      "calls": [{"tool": "exa_web_search",
                                 "arguments": {"query": "Lutathera safety"}}]}]
    assert runner.state(run_id)["facts"]["web_context"] == ["hit 1", "hit 2"]
    assert out["finished"] and runner.handover(run_id)["calls"] == {"web_context": ["exa_web_search"]}


def test_a_question_carries_the_steps_notes_so_the_agent_knows_what_shape_to_answer_in():
    """A delegated call comes back in the wrong shape when the step's notes never
    reach the agent."""
    graph = {"skill": "n", "inputs": [], "steps": [
        {"id": "web", "delegate": [{"tool": "exa_web_search", "arguments": {"query": "x"}}],
         "produces": ["web_context"], "notes": "Return a list of {title, url, snippet}."},
        {"id": "judge", "requires": ["web"], "calls": [], "produces": ["pick"], "judge": ["pick"],
         "notes": "Pick the rarest two."}]}
    asked = []
    runner = SkillRunner(graph, execute=lambda t, a: {},
                         ask=lambda q: asked.append(q) or {n: "v" for n in q["wants"]})
    _run_to_end(runner)
    assert [q["notes"] for q in asked] == ["Return a list of {title, url, snippet}.",
                                           "Pick the rarest two."]


# The shipped rare-disease process resolves its differential to Orphanet: the joint
# tool answers bare names, so each candidate is looked up by name and its code carried.
HITS = {"Hunter syndrome": [{"ORPHAcode": 580, "Preferred term": "Mucopolysaccharidosis type 2"}],
        "GM1 gangliosidosis": [{"ORPHAcode": 354, "Preferred term": "GM1 gangliosidosis"}],
        "lysosomal storage disorder": [{"ORPHAcode": 93448, "Preferred term": "LSD group"}]}


def _rare_disease_run(orphanet_hits):
    calls = []
    responses = {
        "get_HPO_ID_by_phenotype": {"data": {"items": [{"id": "MP:1"}, {"id": "HP:0000280"}]}},
        "get_joint_associated_diseases_by_HPO_ID_list": ["Hunter syndrome", "GM1 gangliosidosis",
                                                         "Sialuria"],
        "EuropePMC_search_articles": {"data": []},
        "MyGene_query_genes": {"data": {"hits": [{"_id": "3423", "symbol": "IDS",
                                                  "name": "iduronate 2-sulfatase", "entrezgene": "3423",
                                                  "ensembl": {"gene": "ENSG00000010404"}}]}},
        "GTEx_get_expression_summary": {"data": []},
        "OpenTargets_get_associated_targets_by_disease_efoId": {"data": {"disease": {
            "id": "MONDO_0011758", "name": "Hurler syndrome", "associatedTargets": {"rows": [
                {"target": {"approvedSymbol": "IDUA"}, "score": 0.85},
                {"target": {"approvedSymbol": "SLC26A1"}, "score": 0.56}]}}}},
    }
    orphanet_genes = {580: [{"Symbol": "IDS"}], 354: [{"Symbol": "GLB1"}, {"Symbol": "IDS"}]}
    mondo_ids = {"Hunter syndrome": "MONDO_0010674", "GM1 gangliosidosis": "MONDO_0018149"}

    def dispatch(call):
        tool, arguments = call["name"], call["arguments"]
        calls.append((tool, arguments))
        code = int(arguments["orphacode"]) if "orphacode" in arguments else None
        term = {580: "MPS II", 354: "GM1"}.get(code, "?")
        if tool == "Orphanet_search_diseases":
            hits = orphanet_hits.get(arguments["query"], [])
            return {"status": "success", "data": {"results": hits, "count": len(hits)}}
        if tool == "Orphanet_get_genes":
            return {"status": "success", "data": {"orpha_code": str(code),
                                                  "genes": orphanet_genes.get(code, [])}}
        if tool == "Orphanet_get_natural_history":
            return {"status": "success", "data": {
                "orpha_code": str(code), "preferred_term": term,
                "type_of_inheritance": ["X-linked recessive"] if code == 580 else ["Autosomal recessive"],
                "average_age_of_onset": ["Childhood"]}}
        if tool == "Orphanet_get_phenotypes":
            return {"status": "success", "data": {
                "orpha_code": str(code), "preferred_term": term,
                "phenotypes": [{"hpo_id": "HP:0000280", "hpo_term": "Coarse facial features",
                                "frequency": "Very frequent (99-80%)"}]}}
        if tool == "Orphanet_get_epidemiology":
            return {"status": "success", "data": {
                "orpha_code": str(code), "preferred_term": "?",
                "prevalences": [{"class": "1-9 / 100 000"}] if code == 580 else []}}
        if tool == "HPO_get_diseases_by_phenotype":
            return {"data": {"diseases": [{"id": f"D{i}"} for i in range(190)]}}
        if tool == "HPO_get_term_hierarchy":
            return {"data": [{"id": "HP:0000271", "name": "Abnormal facial shape"}]
                    if arguments["direction"] == "parents"
                    else [{"id": "HP:0000339", "name": "Pugilistic facies"}]}
        if tool == "OpenTargets_get_disease_ids_by_name":
            mondo = mondo_ids.get(arguments["name"])
            return {"data": {"search": {"hits": [{"id": mondo, "name": arguments["name"]}] if mondo else []}}}
        return responses[tool]

    answers = {"primary_keyword": "lysosomal storage disorder",
               "working_hypothesis": ["storage disorder"],
               "discriminating_features": ["coarse facies"],
               "discriminating_hpo_ids": ["HP:0000280"],
               "top_candidate": "Hunter syndrome", "genes": [],
               "optimuskg_genes": [{"gene": "IDS", "relation": "CAUSES", "evidence_score": 0.9}],
               "overlap_rows": [{"orpha_code": "580", "preferred_term": "MPS II", "n": 1, "N": 1,
                                 "overlap_pct": 100, "grade": "T1", "matched_hpo_ids": ["HP:0000280"]}]}
    asked = []

    def ask(question):
        asked.append(question)
        return {name: answers[name] for name in question["wants"]}

    # Through the same door the worker uses: a bare list becomes {"result": [...]}.
    runner = SkillRunner(load_graph("rare-disease-diagnosis"),
                         execute=normalised_executor(dispatch), ask=ask)
    state = runner.state(_run_to_end(runner, {"symptoms": ["coarse facies"]}, limit=60))
    state["asked"] = asked
    return state, calls


def test_every_decisive_candidate_is_looked_up_in_orphanet_by_name():
    state, calls = _rare_disease_run(HITS)
    by_name = [a["query"] for t, a in calls if t == "Orphanet_search_diseases"]
    assert sorted(by_name) == sorted(["lysosomal storage disorder", "Hunter syndrome",
                                      "GM1 gangliosidosis", "Sialuria"])
    assert all(a["limit"] == 1 for t, a in calls
               if t == "Orphanet_search_diseases" and a["query"] != "lysosomal storage disorder")
    assert state["facts"]["decisive_candidates"] == ["Hunter syndrome", "GM1 gangliosidosis", "Sialuria"]
    # Rows, not aligned lists: Sialuria had no hit and is simply absent.
    assert state["facts"]["orphanet_matches"] == [
        {"ORPHAcode": 580, "Preferred term": "Mucopolysaccharidosis type 2"},
        {"ORPHAcode": 354, "Preferred term": "GM1 gangliosidosis"}]
    assert "resolve_candidates" in state["done"]


def test_collect_can_flatten_one_list_per_call_into_one_list():
    """One gene list per disease, but the panel loops over genes."""
    spec = {"collect": {"genes": {"path": "data.genes[].Symbol", "flatten": True}}}
    results = [{"data": {"genes": [{"Symbol": "IDUA"}]}},
               {"data": {"genes": [{"Symbol": "IDS"}, {"Symbol": "GLB1"}]}},
               {"data": {"genes": []}}]
    assert absorb(spec, results, facts={})["facts"]["genes"] == ["IDUA", "IDS", "GLB1"]


def test_collect_can_keep_only_the_first_occurrence_of_a_value():
    spec = {"collect": {"genes": {"path": "data.genes[].Symbol", "flatten": True, "unique": True}}}
    results = [{"data": {"genes": [{"Symbol": "GLB1"}]}},
               {"data": {"genes": [{"Symbol": "NEU1"}, {"Symbol": "GLB1"}]}}]
    assert absorb(spec, results, facts={})["facts"]["genes"] == ["GLB1", "NEU1"]


def test_genes_come_from_orphanet_per_resolved_candidate_never_from_the_model():
    """A gene list is a claim the Run Record must vouch for, so it is an extraction,
    one lookup per resolved candidate, and never asked of the model."""
    state, calls = _rare_disease_run(HITS)
    assert sorted(int(a["orphacode"]) for t, a in calls if t == "Orphanet_get_genes") == [354, 580]
    assert state["facts"]["genes"] == ["IDS", "GLB1"]
    assert "genes" not in {n for q in state["asked"] for n in q["wants"] if q["kind"] == "judge"}
    assert [q["step"] for q in state["asked"] if q["kind"] == "judge"] == [
        "hypothesis", "discriminating", "keyword_search"]   # one symptom in the stub: the cut ties


def test_a_step_that_cannot_be_built_is_the_one_recorded_as_blocked():
    """The step that raised is the one to record, not the steps after it."""
    graph = {"skill": "blame", "inputs": [], "steps": [
        {"id": "a", "for_each": "first_list", "as": "x",
         "calls": [{"tool": "t", "arguments": {"q": "{x}"}}]},
        {"id": "b", "requires": ["a"], "for_each": "second_list", "as": "y",
         "calls": [{"tool": "t", "arguments": {"q": "{y}"}}]},
        {"id": "c", "calls": []}]}
    run = new_run({})
    offered = next_runnable(graph, run)
    assert offered["id"] == "c"
    assert [b["step"] for b in run["blocked"]] == ["a", "b"]
    assert "second_list" in run["blocked"][1]["reason"]


def test_open_targets_scored_targets_are_fetched_per_candidate_and_kept_as_returned():
    """The second gene source: name -> MONDO id -> scored targets. Scores are kept as
    Open Targets returns them; the reader sees the drop-off, no cut."""
    state, calls = _rare_disease_run(HITS)
    names = sorted(a["name"] for t, a in calls if t == "OpenTargets_get_disease_ids_by_name")
    assert names == ["GM1 gangliosidosis", "Hunter syndrome", "Sialuria"]
    ids = sorted(a["efoId"] for t, a in calls
                 if t == "OpenTargets_get_associated_targets_by_disease_efoId")
    assert ids == ["MONDO_0010674", "MONDO_0018149"]           # Sialuria had no id: no call
    rows = state["facts"]["opentargets_rows"]
    assert [r["name"] for r in rows] == ["Hurler syndrome", "Hurler syndrome"]  # the stub's one answer
    assert rows[0]["associatedTargets"]["rows"][0] == {"target": {"approvedSymbol": "IDUA"}, "score": 0.85}


def test_optimuskg_is_asked_once_as_a_delegated_call_on_the_top_candidate():
    """The third source is the agent's own tool, so the run pauses and hands the agent
    the exact calls: search the disease, then evidence on its CURIE restricted to genes."""
    state, calls = _rare_disease_run(HITS)
    delegated = [q for q in state["asked"]
                 if q["kind"] == "delegate" and q["step"] == "gene_evidence_optimuskg"]
    assert len(delegated) == 1
    assert [c["tool"] for c in delegated[0]["calls"]] == ["OptimusKG_Search", "OptimusKG_Search"]
    search, evidence = delegated[0]["calls"]
    assert search["arguments"] == {"action": "search", "query": "Hunter syndrome",
                                   "node_types": ["disease"]}
    assert evidence["arguments"]["action"] == "evidence"
    assert evidence["arguments"]["node_types"] == ["gene"]
    assert state["facts"]["optimuskg_genes"] == [
        {"gene": "IDS", "relation": "CAUSES", "evidence_score": 0.9}]
    assert "OptimusKG_Search" not in [t for t, _ in calls]      # never executed server-side


def test_a_failed_iteration_is_recorded_with_its_arguments():
    """The report must say which item is missing, not only that the tool failed once."""
    graph = {"skill": "loop", "inputs": ["terms"], "steps": [
        {"id": "prr", "for_each": "terms", "as": "term",
         "calls": [{"tool": "FAERS_calculate_disproportionality",
                    "arguments": {"drug": "x", "event": "{term}"}}],
         "collect": {"prrs": {"path": "data.prr"}}}]}

    def execute(tool, arguments):
        if arguments["event"] == "nausea":
            raise RuntimeError("429 Too Many Requests")
        return {"data": {"prr": 2.0}}

    runner = SkillRunner(graph, execute=execute)
    run_id = runner.start({"terms": ["rash", "nausea", "fever"]})["run_id"]
    runner.advance(run_id)
    state = runner.state(run_id)
    assert state["facts"]["prrs"] == [2.0, 2.0]
    assert state["failures"] == [{"tool": "FAERS_calculate_disproportionality",
                                  "arguments": {"drug": "x", "event": "nausea"},
                                  "error": "RuntimeError: 429 Too Many Requests", "step": "prr"}]


# A failed call keeps its slot: dropping the result shifts every later row onto the
# previous item and loses the last.
def _loop_graph(fields: list[str]) -> dict:
    return {"skill": "loop", "inputs": ["terms"], "steps": [
        {"id": "prr", "for_each": "terms", "as": "term",
         "calls": [{"tool": "FAERS_calculate_disproportionality",
                    "arguments": {"drug": "x", "event": "{term}"}}],
         "total": "data.reports",
         "collect": {"rows": {"path": "data", "fields": fields}}}]}


def _one_term_fails(tool, arguments):
    if arguments["event"] == "nausea":
        raise RuntimeError("429 Too Many Requests")
    return {"data": {"prr": {"rash": 1.0, "fever": 3.0}[arguments["event"]],
                     "reports": {"rash": 11, "fever": 33}[arguments["event"]]}}


@pytest.mark.parametrize("field", ["$item as term", "$call.event as term"])
def test_a_failed_iteration_does_not_relabel_the_items_after_it(field):
    runner = SkillRunner(_loop_graph([field, "prr"]), execute=_one_term_fails)
    run_id = runner.start({"terms": ["rash", "nausea", "fever"]})["run_id"]
    runner.advance(run_id)

    assert runner.state(run_id)["facts"]["rows"] == [
        {"term": "rash", "prr": 1.0},
        {"term": "fever", "prr": 3.0},
    ]


def test_the_total_of_a_failed_call_is_unknown_and_the_others_keep_theirs():
    """A missing slot must not slide the next item's total onto the failed one."""
    assert source_total(
        {"total": "data.reports"},
        [{"data": {"reports": 11}}, None, {"data": {"reports": 33}}],
        ["rash", "nausea", "fever"],
    ) == {"rash": 11, "nausea": "unknown", "fever": 33}


def test_the_run_keeps_every_call_with_its_arguments_per_step():
    """The Run Record needs the arguments, which the agent's trace no longer shows."""
    graph = {"skill": "calls", "inputs": ["terms"], "steps": [
        {"id": "prr", "for_each": "terms", "as": "term",
         "calls": [{"tool": "FAERS_calculate_disproportionality",
                    "arguments": {"drug": "x", "event": "{term}"}}],
         "collect": {"prrs": {"path": "data.prr"}}}]}
    runner = SkillRunner(graph, execute=lambda tool, a: {"data": {"prr": 1.0}})
    run_id = runner.start({"terms": ["rash", "fever"]})["run_id"]
    runner.advance(run_id)
    assert runner.state(run_id)["calls_made"] == {"prr": [
        {"tool": "FAERS_calculate_disproportionality", "arguments": {"drug": "x", "event": "rash"}},
        {"tool": "FAERS_calculate_disproportionality", "arguments": {"drug": "x", "event": "fever"}},
    ]}
    assert runner.handover(run_id)["calls"] == {"prr": ["FAERS_calculate_disproportionality"] * 2}


def test_the_run_keeps_each_question_with_the_answer_it_got():
    runner, asked = _judged_runner({"judge": {"primary_keyword": "storage disorder",
                                              "working_hypothesis": "MPS",
                                              "discriminating_hpo_ids": ["HP:0001433"]}})
    run_id = _run_to_end(runner, {"symptoms": ["hepatosplenomegaly"]})
    questions = runner.state(run_id)["questions"]
    assert [(q["step"], q["kind"], q["wants"]) for q in questions] == [
        ("hypothesis", "judge", ["primary_keyword", "working_hypothesis"]),
        ("phenotypes", "judge", ["discriminating_hpo_ids"])]
    assert questions[0]["answer"] == {"primary_keyword": "storage disorder",
                                      "working_hypothesis": "MPS",
                                      "discriminating_hpo_ids": ["HP:0001433"]}
    assert "context" not in questions[0]          # the record holds no payloads


def test_an_unanswered_question_is_kept_with_its_empty_answer():
    runner, _ = _judged_runner({})                # the oracle answers nothing
    run_id = _run_to_end(runner, {"symptoms": ["x"]})
    assert [q["answer"] for q in runner.state(run_id)["questions"]] == [{}, {}]


def test_collect_can_project_each_call_to_named_fields():
    """The run needs the disease and its HPO ids as one row, not the whole payload."""
    spec = {"collect": {"disease_phenotypes": {
        "path": "data",
        "fields": ["orpha_code", "preferred_term", "phenotypes[].hpo_id as hpo_ids"]}}}
    results = [{"data": {"orpha_code": "93473", "preferred_term": "Hurler syndrome",
                         "phenotypes": [{"hpo_id": "HP:0000280", "hpo_term": "Coarse facial features"},
                                        {"hpo_id": "HP:0001433", "hpo_term": "Hepatosplenomegaly"}]}},
               {"data": {"orpha_code": "580", "preferred_term": "MPS II", "phenotypes": []}}]
    out = absorb(spec, results, facts={})
    assert out["facts"]["disease_phenotypes"] == [
        {"orpha_code": "93473", "preferred_term": "Hurler syndrome",
         "hpo_ids": ["HP:0000280", "HP:0001433"]},
        {"orpha_code": "580", "preferred_term": "MPS II", "hpo_ids": []}]


def test_each_resolved_candidate_gets_its_phenotype_set_and_inheritance_as_rows():
    state, calls = _rare_disease_run(HITS)
    assert sorted(int(a["orphacode"]) for t, a in calls if t == "Orphanet_get_phenotypes") == [354, 580]
    assert sorted(int(a["orphacode"]) for t, a in calls if t == "Orphanet_get_natural_history") == [354, 580]
    rows = {r["orpha_code"]: r for r in state["facts"]["disease_phenotypes"]}
    assert rows["580"]["hpo_ids"] == ["HP:0000280"] and "phenotypes" not in rows["580"]
    inh = {r["orpha_code"]: r for r in state["facts"]["disease_inheritance"]}
    assert inh["580"]["type_of_inheritance"] == ["X-linked recessive"]


def test_overlap_and_grade_are_computed_by_the_server_without_a_question():
    state, calls = _rare_disease_run(HITS)
    assert "compute_overlap" not in {q["step"] for q in state["asked"]}
    rows = {r["orpha_code"]: r for r in state["facts"]["overlap_rows"]}
    assert rows["580"]["n"] == 1 and rows["580"]["N"] == 1 and rows["580"]["overlap_pct"] == 100
    assert rows["580"]["grade"] == "T1" and rows["354"]["grade"] == "T1"   # both have Orphanet genes
    assert rows["580"]["matched_hpo_ids"] == ["HP:0000280"]


def test_a_question_stubs_facts_larger_than_a_payload_cap():
    """A cap per payload cannot bound a loop, so each step's results get a budget."""
    facts = {"top_candidate": "MPS II", "opentargets_rows": [{"t": "x" * 100}] * 200}
    q = question_for("keyword_search", "judge", ["top_candidate"], facts)
    assert q["context"]["top_candidate"] == "MPS II"
    assert q["context"]["opentargets_rows"] == {"omitted": "200 items — in the bundle"}


def test_the_gene_panel_collects_a_row_per_gene_for_the_writer():
    """With loop results bounded, the writer reads Ensembl and Entrez ids from rows."""
    state, _ = _rare_disease_run(HITS)
    rows = state["facts"]["gene_rows"]
    assert rows and rows[0] == {"symbol": "IDS", "name": "iduronate 2-sulfatase",
                                "entrezgene": "3423", "ensembl": "ENSG00000010404"}


def test_a_stubbed_fact_says_it_travels_whole_in_the_questions_own_calls():
    """A stub must point at where the value is, or the model computes over rows it
    cannot see."""
    rows = [{"orpha_code": str(i), "hpo_ids": ["HP:%07d" % j for j in range(60)]} for i in range(20)]
    facts = {"hpo_ids": ["HP:0000280"], "disease_phenotypes": rows}
    calls = [{"tool": "code_interpreter",
              "arguments": {"diseases": rows, "case_hpo_ids": ["HP:0000280"]}}]
    q = question_for("compute_overlap", "delegate", ["overlap_rows"], facts, calls=calls)
    assert q["context"]["disease_phenotypes"] == {
        "omitted": "20 items — passed whole in this question's calls, and in the bundle"}
    assert q["calls"][0]["arguments"]["diseases"] == rows          # the arguments are never stubbed


# Ranking is arithmetic over rows the run already holds, so the runtime does it, with
# the author's rule: onset fit, then prevalence, then overlap.
RANK_SPEC = {"compute": {"ranked_rows": {
    "op": "rank_differential",
    "overlap": "overlap_rows", "inheritance": "disease_inheritance",
    "epidemiology": "disease_prevalence", "patient_age_years": "age_years",
    "early_onset": ["Antenatal", "Neonatal", "Infancy", "Childhood", "All ages"],
    "late_onset": ["Adolescent", "Adult", "Elderly"]}}}

RANK_FACTS = {
    "age_years": 4,
    "overlap_rows": [
        {"orpha_code": "3166", "preferred_term": "Sialuria", "n": 4, "N": 4, "overlap_pct": 100, "grade": "T1"},
        {"orpha_code": "93399", "preferred_term": "Juvenile sialidosis type 2", "n": 4, "N": 4, "overlap_pct": 100, "grade": "T1"},
        {"orpha_code": "580", "preferred_term": "MPS II", "n": 3, "N": 4, "overlap_pct": 75, "grade": "T2"},
        {"orpha_code": "93473", "preferred_term": "Hurler", "n": 2, "N": 4, "overlap_pct": 50, "grade": "T3"},
        {"orpha_code": "79255", "preferred_term": "GM1 type 1", "n": 3, "N": 4, "overlap_pct": 75, "grade": "T2"},
    ],
    "disease_inheritance": [{"orpha_code": c, "average_age_of_onset": onset} for c, onset in [
        ("3166", ["Infancy"]), ("93399", ["Adolescent"]), ("580", ["Childhood"]),
        ("93473", ["Infancy", "Neonatal"]), ("79255", ["Infancy"])]],
    # 93399 has no epidemiology row at all: unknown, neither punished nor rewarded
    "disease_prevalence": [{"orpha_code": c, "classes": classes} for c, classes in [
        ("3166", ["<1 / 1 000 000"]), ("580", ["1-9 / 100 000", "1-9 / 1 000 000"]),
        ("93473", ["1-9 / 1 000 000"]), ("79255", ["Unknown"])]],
}


def test_the_differential_is_ranked_by_onset_fit_then_prevalence_then_overlap():
    rows = absorb(RANK_SPEC, results=[], facts=RANK_FACTS)["facts"]["ranked_rows"]
    assert [r["preferred_term"] for r in rows] == [
        "MPS II",                      # fits age; commonest (1-9/100 000); 75%
        "Hurler",                      # fits age; 1-9/1 000 000; 50%
        "GM1 type 1",                  # fits age; prevalence unknown (middle tier); 75%
        "Sialuria",                    # fits age; rarest (<1/1 000 000); 100%
        "Juvenile sialidosis type 2",  # onset excludes a four-year-old: last, whatever the overlap
    ]
    assert rows[0]["rank"] == 1 and rows[0]["onset_fit"] == "fits"
    assert rows[0]["prevalence_tier"] == "1-9 / 100 000"
    assert rows[-1]["onset_fit"] == "later than patient" and rows[-1]["rank"] == 5
    assert rows[2]["prevalence_tier"] == "unknown"
    assert rows[0]["overlap_pct"] == 75 and rows[0]["grade"] == "T2"   # both travel with the row


def test_ranking_without_a_patient_age_uses_prevalence_then_overlap_and_says_so():
    facts = {k: v for k, v in RANK_FACTS.items() if k != "age_years"}
    rows = absorb(RANK_SPEC, results=[], facts=facts)["facts"]["ranked_rows"]
    assert [r["preferred_term"] for r in rows][:2] == ["MPS II", "Hurler"]
    assert all(r["onset_fit"] == "not assessed (no patient age)" for r in rows)


def test_ranking_needs_the_overlap_rows_and_is_unresolved_without_them():
    out = absorb(RANK_SPEC, results=[], facts={"age_years": 4})
    assert "ranked_rows" in out["unresolved"] and "ranked_rows" not in out["facts"]


def test_the_shipped_process_ranks_the_differential_on_the_server_from_its_rows():
    state, calls = _rare_disease_run(HITS)
    assert sorted(int(a["orphacode"]) for t, a in calls if t == "Orphanet_get_epidemiology") == [354, 580]
    assert "rank_differential" not in {q["step"] for q in state["asked"]}     # no question asked
    ranked = state["facts"]["ranked_rows"]                 # both stubbed candidates, on the server
    assert [r["rank"] for r in ranked] == [1, 2]
    assert [r["orpha_code"] for r in ranked] == ["580", "354"]            # known prevalence beats unknown
    assert ranked[0]["prevalence_tier"] == "1-9 / 100 000" and ranked[1]["prevalence_tier"] == "unknown"
    assert ranked[0]["onset_fit"] == "not assessed (no patient age)"   # the stub binds no age_years
    assert ranked[0]["grade"] == "T1" and ranked[0]["overlap_pct"] == 100   # overlap travels with the row


def test_prevalence_tier_is_the_class_most_studies_agree_on_not_one_outlier():
    """One outlier entry cannot rank a disease first; ties go to the commoner class."""
    assert _prevalence_tier(["1-9 / 1 000 000", "<1 / 1 000 000", "1-9 / 1 000 000",
                             "1-9 / 1 000 000", "<1 / 1 000 000", "1-5 / 10 000"])[0] == "1-9 / 1 000 000"
    assert _prevalence_tier(["1-9 / 100 000", "1-9 / 1 000 000"])[0] == "1-9 / 100 000"   # tie → commoner
    assert _prevalence_tier(["Unknown", "1-9 / 1 000 000"])[0] == "1-9 / 1 000 000"       # not a class
    assert _prevalence_tier([])[0] == "unknown"


def test_a_candidate_with_no_matching_phenotype_never_outranks_one_that_fits():
    """Prevalence orders the candidates that match at all; zero overlap goes to the
    bottom of its onset band."""
    facts = {"age_years": 4,
             "overlap_rows": [{"orpha_code": "1", "preferred_term": "Common but 0/4", "overlap_pct": 0, "grade": "T4"},
                              {"orpha_code": "2", "preferred_term": "Rare but 2/4", "overlap_pct": 50, "grade": "T3"}],
             "disease_inheritance": [{"orpha_code": "1", "average_age_of_onset": ["Infancy"]},
                                     {"orpha_code": "2", "average_age_of_onset": ["Infancy"]}],
             "disease_prevalence": [{"orpha_code": "1", "classes": ["1-5 / 10 000"]},
                                    {"orpha_code": "2", "classes": ["<1 / 1 000 000"]}]}
    rows = absorb(RANK_SPEC, results=[], facts=facts)["facts"]["ranked_rows"]
    assert [r["preferred_term"] for r in rows] == ["Rare but 2/4", "Common but 0/4"]


# Counting shared HPO ids is not a judgement: the runtime does it from the rows it
# already holds, with the author's thresholds.
OVERLAP_SPEC = {"compute": {"overlap_rows": {
    "op": "overlap",
    "rows": "disease_phenotypes", "row_ids": "hpo_ids", "against": "hpo_ids",
    "gene_rows": "orphanet_gene_rows",
    "grades": [{"grade": "T1", "min_pct": 80, "needs_gene": True},
               {"grade": "T2", "min_pct": 60}, {"grade": "T3", "min_pct": 40},
               {"grade": "T4", "min_pct": 0}]}}}

OVERLAP_FACTS = {
    "hpo_ids": ["HP:0001263", "HP:0001250", "HP:0000280", "HP:0001433"],
    "disease_phenotypes": [
        {"orpha_code": "580", "preferred_term": "MPS II", "hpo_ids": ["HP:0000280", "HP:0001433", "HP:0001250", "HP:0009999"]},
        {"orpha_code": "3166", "preferred_term": "Sialuria", "hpo_ids": ["HP:0000280", "HP:0001433", "HP:0001250", "HP:0001263"]},
        {"orpha_code": "821", "preferred_term": "Sotos", "hpo_ids": ["HP:0001263"]},
    ],
    "orphanet_gene_rows": [{"orpha_code": "580", "genes": [{"Symbol": "IDS"}]},
                           {"orpha_code": "3166", "genes": []}],
}


def test_overlap_rows_are_computed_from_the_rows_with_the_authors_grades():
    rows = absorb(OVERLAP_SPEC, results=[], facts=OVERLAP_FACTS)["facts"]["overlap_rows"]
    assert [(r["preferred_term"], r["n"], r["N"], r["overlap_pct"], r["grade"]) for r in rows] == [
        ("Sialuria", 4, 4, 100, "T2"),      # 100% but no causal gene in Orphanet: not T1
        ("MPS II", 3, 4, 75, "T2"),
        ("Sotos", 1, 4, 25, "T4"),
    ]
    assert rows[1]["matched_hpo_ids"] == ["HP:0001250", "HP:0000280", "HP:0001433"]   # case order
    assert rows[1]["orpha_code"] == "580"


def test_overlap_without_its_source_rows_is_unresolved_not_empty():
    out = absorb(OVERLAP_SPEC, results=[], facts={"hpo_ids": ["HP:1"]})
    assert "overlap_rows" not in out["facts"] and "overlap_rows" in out["unresolved"]


def test_a_collected_row_can_keep_the_loop_item_it_was_made_for():
    """The tool does not echo the term, so a collect field may name the loop item."""
    graph = {"skill": "loop", "inputs": ["hpo_ids"], "steps": [
        {"id": "counts", "for_each": "hpo_ids", "as": "hpo",
         "calls": [{"tool": "HPO_get_diseases_by_phenotype",
                    "arguments": {"term_id": "{hpo}", "limit": 500}}],
         "collect": {"term_counts": {"path": "data",
                                     "fields": ["$item as hpo_id", "diseases[].id as diseases"]}}}]}
    sizes = {"HP:0001433": 190, "HP:0000280": 340, "HP:0001250": 500}
    runner = SkillRunner(graph, execute=lambda tool, a: {
        "data": {"diseases": [{"id": f"D{i}"} for i in range(sizes[a["term_id"]])]}})
    run_id = runner.start({"hpo_ids": list(sizes)})["run_id"]
    runner.advance(run_id)
    rows = runner.state(run_id)["facts"]["term_counts"]
    assert [r["hpo_id"] for r in rows] == ["HP:0001433", "HP:0000280", "HP:0001250"]
    assert [len(r["diseases"]) for r in rows] == [190, 340, 500]


# "Fewest annotated diseases" is arithmetic; the model is asked only when counts tie.
FEWEST_SPEC = {"compute": {"discriminating_hpo_ids": {
    "op": "fewest", "rows": "term_counts", "id": "hpo_id", "count": "diseases", "take": 2}}}


def test_the_two_terms_with_the_fewest_annotated_diseases_are_chosen():
    facts = {"term_counts": [{"hpo_id": "HP:0001263", "diseases": ["d"] * 500},
                             {"hpo_id": "HP:0001250", "diseases": ["d"] * 500},
                             {"hpo_id": "HP:0000280", "diseases": ["d"] * 340},
                             {"hpo_id": "HP:0001433", "diseases": ["d"] * 190}]}
    out = absorb(FEWEST_SPEC, results=[], facts=facts)
    assert out["facts"]["discriminating_hpo_ids"] == ["HP:0001433", "HP:0000280"]


def test_a_tie_at_the_cut_is_left_unresolved_for_the_model_to_break():
    facts = {"term_counts": [{"hpo_id": "HP:A", "diseases": ["d"] * 100},
                             {"hpo_id": "HP:B", "diseases": ["d"] * 200},
                             {"hpo_id": "HP:C", "diseases": ["d"] * 200}]}
    out = absorb(FEWEST_SPEC, results=[], facts=facts)
    assert "discriminating_hpo_ids" not in out["facts"]
    assert "discriminating_hpo_ids" in out["unresolved"]


def test_the_shipped_process_computes_the_discriminating_pair_and_asks_only_on_a_tie():
    """One symptom in the stub → one HP id → fewer than two rows → the compute cannot
    cut, the name stays unresolved, and the judge on `discriminating` fills it."""
    state, calls = _rare_disease_run(HITS)
    assert [a["term_id"] for t, a in calls if t == "HPO_get_diseases_by_phenotype"] == ["HP:0000280"]
    asked = [(q["step"], q["kind"]) for q in state["asked"]]
    assert ("phenotypes", "judge") not in asked
    assert ("discriminating", "judge") in asked                  # the tie/short-list fallback
    assert state["facts"]["discriminating_hpo_ids"] == ["HP:0000280"]


def test_a_judged_name_a_compute_already_resolved_is_not_asked():
    """A judgement is for what the step could not resolve itself; a name already in
    hand is never put to the model."""
    graph = {"skill": "j", "inputs": ["term_counts"], "steps": [
        {"id": "discriminating", "calls": [],
         "compute": {"pair": {"op": "fewest", "rows": "term_counts", "id": "hpo_id",
                              "count": "diseases", "take": 2}},
         "produces": ["pair"], "judge": ["pair"]}]}
    asked = []
    runner = SkillRunner(graph, execute=lambda t, a: {},
                         ask=lambda q: asked.append(q) or {"pair": ["X"]})
    counts = [{"hpo_id": "A", "diseases": ["d"] * 10}, {"hpo_id": "B", "diseases": ["d"] * 20},
              {"hpo_id": "C", "diseases": ["d"] * 30}]
    run_id = runner.start({"term_counts": counts})["run_id"]
    runner.advance(run_id)
    assert asked == []
    assert runner.state(run_id)["facts"]["pair"] == ["A", "B"]

    # and when the cut ties, the judge IS asked, for that name only
    tied = [{"hpo_id": "A", "diseases": ["d"] * 10}, {"hpo_id": "B", "diseases": ["d"] * 20},
            {"hpo_id": "C", "diseases": ["d"] * 20}]
    run_id = runner.start({"term_counts": tied})["run_id"]
    runner.advance(run_id)
    assert [q["wants"] for q in asked] == [["pair"]]
    assert runner.state(run_id)["facts"]["pair"] == ["X"]


def test_fewest_counts_distinct_ids_so_two_symptoms_on_one_term_do_not_make_a_pair():
    """Two symptoms resolving to the same HP id are one phenotype, not two."""
    rule = {"rows": "t", "id": "hpo_id", "count": "diseases", "take": 2}
    same = [{"hpo_id": "HP:1", "diseases": ["d"] * 190}, {"hpo_id": "HP:1", "diseases": ["d"] * 190}]
    assert _fewest(rule, {"t": same}) is None                       # one distinct id: cannot cut two
    assert _fewest(rule, {"t": same + [{"hpo_id": "HP:2", "diseases": ["d"] * 340}]}) == ["HP:1", "HP:2"]


# The process computes the discriminating pair, so the ranking must gate on it.
GATED_SPEC = {"compute": {"ranked_rows": {**RANK_SPEC["compute"]["ranked_rows"],
                                          "must_carry": "discriminating_hpo_ids",
                                          "rows_ids": "disease_phenotypes"}}}


def test_a_candidate_lacking_a_discriminating_phenotype_ranks_below_all_that_carry_both():
    facts = {
        "age_years": 4,
        "discriminating_hpo_ids": ["HP:0001433", "HP:0000280"],
        "disease_phenotypes": [
            {"orpha_code": "821", "hpo_ids": ["HP:0001263", "HP:0001250", "HP:0000280"]},          # Sotos: no hepatosplenomegaly
            {"orpha_code": "580", "hpo_ids": ["HP:0000280", "HP:0001433", "HP:0001250"]},          # MPS II: both
            {"orpha_code": "93473", "hpo_ids": ["HP:0000280", "HP:0001433"]},                      # Hurler: both
            {"orpha_code": "3166", "hpo_ids": ["HP:0000280", "HP:0001433", "HP:0001250", "HP:0001263"]},  # Sialuria: both
        ],
        "overlap_rows": [
            {"orpha_code": "821", "preferred_term": "Sotos", "overlap_pct": 75, "grade": "T2"},
            {"orpha_code": "580", "preferred_term": "MPS II", "overlap_pct": 75, "grade": "T2"},
            {"orpha_code": "93473", "preferred_term": "Hurler", "overlap_pct": 50, "grade": "T3"},
            {"orpha_code": "3166", "preferred_term": "Sialuria", "overlap_pct": 100, "grade": "T1"},
        ],
        "disease_inheritance": [{"orpha_code": c, "average_age_of_onset": ["Infancy"]}
                                for c in ("821", "580", "93473", "3166")],
        "disease_prevalence": [{"orpha_code": "821", "classes": ["1-9 / 100 000"]},
                               {"orpha_code": "580", "classes": ["1-9 / 1 000 000"]},
                               {"orpha_code": "93473", "classes": ["1-9 / 1 000 000"]},
                               {"orpha_code": "3166", "classes": ["<1 / 1 000 000"]}],
    }
    rows = absorb(GATED_SPEC, results=[], facts=facts)["facts"]["ranked_rows"]
    assert [r["preferred_term"] for r in rows] == ["MPS II", "Hurler", "Sialuria", "Sotos"]
    assert rows[0]["carries_discriminating"] == "both" and rows[-1]["carries_discriminating"] == "1 of 2"


def test_without_a_computed_pair_the_gate_is_not_applied_and_says_so():
    rows = absorb(GATED_SPEC, results=[], facts=dict(RANK_FACTS))["facts"]["ranked_rows"]
    assert [r["preferred_term"] for r in rows][:2] == ["MPS II", "Hurler"]   # as in the ungated test
    assert all(r["carries_discriminating"] == "not assessed (no discriminating pair)" for r in rows)


# Hepatomegaly and Splenomegaly together are the case's Hepatosplenomegaly, so an
# exact-id match is not enough: the match is ontological, from rows the run fetches.
HIER = [  # one row per case term, from HPO_get_term_hierarchy (parents) and (children)
    {"hpo_id": "HP:0001433", "parents": ["HP:0002240", "HP:0001744"], "children": []},
    {"hpo_id": "HP:0000280", "parents": ["HP:0000271"], "children": ["HP:0000339"]},
    {"hpo_id": "HP:0001250", "parents": ["HP:0012638"], "children": ["HP:0002123", "HP:0011097"]},
]


def test_a_term_is_carried_by_itself_by_all_its_parents_or_by_a_child():
    hier = {h["hpo_id"]: h for h in HIER}
    assert carries("HP:0001433", {"HP:0001433"}, hier)                                # itself
    assert carries("HP:0001433", {"HP:0002240", "HP:0001744"}, hier)                  # both parents
    assert not carries("HP:0001433", {"HP:0002240"}, hier)                            # one is not enough
    assert carries("HP:0000280", {"HP:0000339"}, hier)                                # a child
    assert not carries("HP:0000280", {"HP:0000271"}, hier)                            # a lone parent is broader
    assert carries("HP:0001250", {"HP:0002123"}, hier)                                # generalized seizures ⊂ seizures
    assert carries("HP:0009999", {"HP:0009999"}, {})                                  # no row: exact match counts
    assert not carries("HP:0009999", {"HP:0000001"}, {})


def test_overlap_and_the_gate_use_the_ontological_match_when_a_hierarchy_is_given():
    spec = {"compute": {"overlap_rows": {**OVERLAP_SPEC["compute"]["overlap_rows"],
                                         "hierarchy": "hpo_hierarchy"}}}
    facts = {**OVERLAP_FACTS, "hpo_hierarchy": HIER,
             "disease_phenotypes": [
                 {"orpha_code": "93473", "preferred_term": "Hurler", "hpo_ids": ["HP:0000280", "HP:0002240", "HP:0001744", "HP:0001263"]},
                 {"orpha_code": "821", "preferred_term": "Sotos", "hpo_ids": ["HP:0000280", "HP:0001263", "HP:0001250"]},
             ]}
    rows = {r["preferred_term"]: r for r in absorb(spec, results=[], facts=facts)["facts"]["overlap_rows"]}
    assert rows["Hurler"]["n"] == 3 and "HP:0001433" in rows["Hurler"]["matched_hpo_ids"]    # hepato+spleno
    assert rows["Sotos"]["n"] == 3 and "HP:0001433" not in rows["Sotos"]["matched_hpo_ids"]

    gated = {"compute": {"ranked_rows": {**GATED_SPEC["compute"]["ranked_rows"],
                                         "hierarchy": "hpo_hierarchy"}}}
    gfacts = {"age_years": 4, "discriminating_hpo_ids": ["HP:0001433", "HP:0000280"], "hpo_hierarchy": HIER,
              "disease_phenotypes": facts["disease_phenotypes"],
              "overlap_rows": list(rows.values()),
              "disease_inheritance": [{"orpha_code": c, "average_age_of_onset": ["Infancy"]} for c in ("93473", "821")],
              "disease_prevalence": [{"orpha_code": "821", "classes": ["1-9 / 100 000"]},
                                     {"orpha_code": "93473", "classes": ["1-9 / 1 000 000"]}]}
    ranked = absorb(gated, results=[], facts=gfacts)["facts"]["ranked_rows"]
    assert [r["preferred_term"] for r in ranked] == ["Hurler", "Sotos"]
    assert ranked[0]["carries_discriminating"] == "both" and ranked[1]["carries_discriminating"] == "1 of 2"


def test_the_shipped_process_fetches_the_hierarchy_and_matches_ontologically():
    """Hurler's row lists Hepatomegaly and Splenomegaly; the case's Hepatosplenomegaly
    must count as carried, and the discriminating pair must gate the ranking."""
    state, calls = _rare_disease_run(HITS)
    hierarchy_calls = [a for t, a in calls if t == "HPO_get_term_hierarchy"]
    assert sorted(a["term_id"] for a in hierarchy_calls) == ["HP:0000280", "HP:0000280"]
    assert {a["direction"] for a in hierarchy_calls} == {"parents", "children"}
    assert state["facts"]["hpo_hierarchy"] == [
        {"hpo_id": "HP:0000280", "parents": ["HP:0000271"], "children": ["HP:0000339"]}]
    assert all("carries_discriminating" in r for r in state["facts"]["ranked_rows"])


# check: the server cannot make the agent use a tool, but it can refuse an answer that
# does not hold against the rows it has. One re-ask, then the fact stays unresolved.
PRR_ROWS = [{"term": "NEUROENDOCRINE TUMOUR", "prr": 393.571, "url": "u1"},
            {"term": "MYELODYSPLASTIC SYNDROME", "prr": 7.528, "url": "u2"},
            {"term": "FATIGUE"},
            {"term": "NAUSEA", "prr": 1.089, "url": "u4"}]
PRR_TABLE = [{"term": "NEUROENDOCRINE TUMOUR", "prr": 393.571, "url": "u1", "flagged": True},
             {"term": "MYELODYSPLASTIC SYNDROME", "prr": 7.528, "url": "u2", "flagged": True},
             {"term": "NAUSEA", "prr": 1.089, "url": "u4", "flagged": False},
             {"term": "FATIGUE", "prr": None, "flagged": False}]
DISEASE_PATTERN = "TUMOU?R|NEOPLASM|METASTA"
CHECK_RULES = {
    "prr_table": [{"rows_of": "prr_rows"},
                  {"sorted_by": {"field": "prr", "order": "desc"}},
                  {"flag": {"field": "flagged", "from": "prr", "op": ">=", "value": 2}}],
    "flagged_aes": [{"subset_of": {"rows": "prr_table", "field": "term", "where": "flagged"}},
                    {"excludes": DISEASE_PATTERN},
                    {"covers": {"rows": "prr_table", "field": "term", "where": "flagged",
                                "together_with": ["excluded_aes"]}}],
    "excluded_aes": [{"subset_of": {"rows": "prr_table", "field": "term", "where": "flagged"}},
                     {"only": DISEASE_PATTERN}],
}
GOOD_ANSWER = {"prr_table": PRR_TABLE, "flagged_aes": ["MYELODYSPLASTIC SYNDROME"],
               "excluded_aes": ["NEUROENDOCRINE TUMOUR"]}
PRR_FACTS = {"prr_rows": PRR_ROWS}


def test_a_faithful_answer_passes_every_check():
    assert check_facts(CHECK_RULES, GOOD_ANSWER, PRR_FACTS) == []


def test_rows_of_rejects_an_invented_dropped_or_retyped_row():
    invented = {**GOOD_ANSWER, "prr_table": PRR_TABLE + [{"term": "RASH", "prr": 3.0, "flagged": True}]}
    dropped = {**GOOD_ANSWER, "prr_table": PRR_TABLE[:-1]}
    retyped = {**GOOD_ANSWER, "prr_table": [{**PRR_TABLE[0], "prr": 393.6}] + PRR_TABLE[1:]}
    for bad in (invented, dropped, retyped):
        failures = check_facts(CHECK_RULES, bad, PRR_FACTS)
        assert any(f["fact"] == "prr_table" and f["check"] == "rows_of" for f in failures), bad


def test_sorted_by_and_flag_read_a_missing_number_as_last_and_unflagged():
    unsorted = {**GOOD_ANSWER, "prr_table": [PRR_TABLE[1], PRR_TABLE[0]] + PRR_TABLE[2:]}
    assert [f["check"] for f in check_facts(CHECK_RULES, unsorted, PRR_FACTS)] == ["sorted_by"]
    # A wrong flag also breaks `covers` on the selection: both are reported.
    misflagged = {**GOOD_ANSWER, "prr_table": PRR_TABLE[:2] + [{**PRR_TABLE[2], "flagged": True}, PRR_TABLE[3]]}
    assert {f["check"] for f in check_facts(CHECK_RULES, misflagged, PRR_FACTS)} == {"flag", "covers"}
    null_flagged = {**GOOD_ANSWER, "prr_table": PRR_TABLE[:3] + [{**PRR_TABLE[3], "flagged": True}]}
    assert {f["check"] for f in check_facts(CHECK_RULES, null_flagged, PRR_FACTS)} == {"flag", "covers"}


def test_check_flag_reads_a_none_flag_as_not_flagged_not_an_error():
    """`_flag` marks a cell it cannot parse `flagged: None`. The check must read that as
    "did not reach the threshold" -- not as a mismatch, and not as a pass for `flagged: True`."""
    rule = {"prr_table": {"flag": {"field": "flagged", "from": "prr", "op": ">=", "value": 5}}}
    rows = [{"term": "A", "prr": "3.1 (0.8-9.4)", "flagged": None},
            {"term": "B", "prr": 17.7, "flagged": True}]

    assert check_facts(rule, {"prr_table": rows}, {}) == []

    wrongly_true = [{**rows[0], "flagged": True}, rows[1]]
    assert [f["check"] for f in check_facts(rule, {"prr_table": wrongly_true}, {})] == ["flag"]


def test_list_checks_hold_the_selection_to_the_table():
    foreign = {**GOOD_ANSWER, "flagged_aes": ["MYELODYSPLASTIC SYNDROME", "HEADACHE"]}
    assert [f["check"] for f in check_facts(CHECK_RULES, foreign, PRR_FACTS)] == ["subset_of"]
    unflagged = {**GOOD_ANSWER, "flagged_aes": ["MYELODYSPLASTIC SYNDROME", "NAUSEA"]}
    assert [f["check"] for f in check_facts(CHECK_RULES, unflagged, PRR_FACTS)] == ["subset_of"]
    kept_disease = {**GOOD_ANSWER, "flagged_aes": ["MYELODYSPLASTIC SYNDROME", "NEUROENDOCRINE TUMOUR"]}
    assert [f["check"] for f in check_facts(CHECK_RULES, kept_disease, PRR_FACTS)] == ["excludes"]
    lost_one = {**GOOD_ANSWER, "flagged_aes": [], "excluded_aes": ["NEUROENDOCRINE TUMOUR"]}
    assert [f["check"] for f in check_facts(CHECK_RULES, lost_one, PRR_FACTS)] == ["covers"]
    wrong_side = {**GOOD_ANSWER, "excluded_aes": ["MYELODYSPLASTIC SYNDROME"]}
    assert "only" in [f["check"] for f in check_facts(CHECK_RULES, wrong_side, PRR_FACTS)]


def test_a_check_on_a_fact_the_answer_did_not_supply_is_not_a_failure():
    """An unanswered name is already unresolved; the check has nothing to judge."""
    failures = check_facts(CHECK_RULES, {"prr_table": PRR_TABLE}, PRR_FACTS)
    assert all(f["fact"] == "flagged_aes" and f["check"] == "covers" for f in failures)


def test_an_unknown_check_kind_is_a_graph_error_not_a_pass():
    with pytest.raises(SkillGraphError):
        check_facts({"x": [{"looks_fine": True}]}, {"x": [1]}, {})


def _compute_graph():
    return {"skill": "c", "inputs": ["prr_rows"], "steps": [
        {"id": "compute",
         "delegate": [{"tool": "OpenAI_Code_Interpreter", "arguments": {"rows": "{prr_rows}"}}],
         "produces": ["prr_table", "flagged_aes", "excluded_aes"],
         "check": CHECK_RULES}]}


def test_a_failing_check_is_asked_once_more_with_the_failure_named_then_accepted():
    answers = iter([{**GOOD_ANSWER, "prr_table": PRR_TABLE[:-1]}, GOOD_ANSWER])
    asked = []
    runner = SkillRunner(_compute_graph(), execute=lambda t, a: {},
                         ask=lambda q: asked.append(q) or next(answers))
    run_id = runner.start({"prr_rows": PRR_ROWS})["run_id"]
    out = runner.advance(run_id)
    assert len(asked) == 2
    assert "problem" not in asked[0] and "rows_of" in asked[1]["problem"]
    assert asked[1]["calls"] == asked[0]["calls"], "the same composed call, the failure added"
    assert runner.state(run_id)["facts"]["prr_table"] == PRR_TABLE
    assert out["unresolved"] == [] and runner.state(run_id)["blocked"] == []
    assert [q["answer"] is not None for q in runner.state(run_id)["questions"]] == [True, True]


def test_a_second_failure_leaves_the_fact_unresolved_and_says_why():
    bad = {**GOOD_ANSWER, "prr_table": [{**PRR_TABLE[0], "prr": 393.6}] + PRR_TABLE[1:]}  # one retyped
    runner = SkillRunner(_compute_graph(), execute=lambda t, a: {}, ask=lambda q: bad)
    run_id = runner.start({"prr_rows": PRR_ROWS})["run_id"]
    out = runner.advance(run_id)
    state = runner.state(run_id)
    assert "prr_table" not in state["facts"], "a fact that fails its check never enters facts"
    assert state["facts"]["excluded_aes"] == ["NEUROENDOCRINE TUMOUR"], "the names that held are kept"
    assert {u["fact"] for u in out["unresolved"]} == {"prr_table"}
    assert state["blocked"] and "rows_of" in state["blocked"][0]["reason"]
    assert len(state["questions"]) == 2


GATED = {
    "skill": "gated", "inputs": ["drug_name"], "optional_inputs": ["requested"],
    "steps": [
        {"id": "counts",
         "calls": [{"tool": "count_reactions", "arguments": {"drug": "{drug_name}"}}],
         "extract": {"top_terms": "data.terms"}},
        {"id": "map_terms", "requires": ["counts"], "when": "requested",
         "calls": [{"tool": "map_terms", "arguments": {"terms": "{requested}"}}],
         "extract": {"mapped": "data.mapped"}},
        {"id": "signals", "requires": ["map_terms"],
         "calls": [{"tool": "signal", "arguments": {"terms": "{top_terms}"}}],
         "extract": {"prr": "data.prr"}},
    ],
}
GATED_RESPONSES = {"count_reactions": {"data": {"terms": ["NAUSEA"]}},
                   "map_terms": {"data": {"mapped": ["DEAFNESS"]}},
                   "signal": {"data": {"prr": 2.5}}}


def _gated_handover():
    runner = SkillRunner(GATED, execute=lambda tool, a: GATED_RESPONSES[tool])
    return runner.handover(_run_to_end(runner, {"drug_name": "x"}))


def test_a_step_that_requires_a_skipped_gated_step_still_runs():
    """A question that names no reaction skips the mapping; signals must still run."""
    handed = _gated_handover()
    assert handed["steps_done"] == ["counts", "signals"]
    assert handed["facts"]["prr"] == 2.5


def test_a_skipped_gated_step_is_handed_over_as_skipped_with_its_gate():
    """Not done, not blocked: the report can say what did not run and why."""
    handed = _gated_handover()
    # "requested" is an optional input never supplied, so the gate was never decided.
    assert handed["steps_skipped"] == [{"step": "map_terms", "gate": "requested", "decided": False}]
    assert handed["blocked"] == []


EARLY = {
    "skill": "early", "inputs": ["drug_name"],
    "steps": [
        {"id": "after_gate", "requires": ["stratify"],
         "calls": [{"tool": "summarise", "arguments": {"drug": "{drug_name}"}}]},
        {"id": "signals",
         "calls": [{"tool": "signal", "arguments": {"drug": "{drug_name}"}}],
         "extract": {"rows": "data.rows"},
         "derive": {"strong": {"from": "rows", "field": "prr", "op": ">=", "value": 5,
                               "mode": "any"}}},
        {"id": "stratify", "when": "strong",
         "calls": [{"tool": "stratify", "arguments": {"drug": "{drug_name}"}}]},
    ],
}


@pytest.mark.parametrize("prr, expected", [
    (17.7, ["signal", "stratify", "summarise"]),
    (1.1, ["signal", "summarise"]),
])
def test_a_gate_whose_fact_is_not_decided_yet_is_not_closed_early(prr, expected):
    """Absent is not false: the step that derives the gate's fact has not run yet."""
    called = []
    runner = SkillRunner(EARLY, execute=lambda tool, a: called.append(tool) or
                         {"data": {"rows": [{"prr": prr}]}})
    _run_to_end(runner, {"drug_name": "x"})
    assert called == expected


def test_a_step_that_could_never_start_is_named_with_what_it_waited_for():
    """A run that stops early must not read as a run that finished."""
    stuck = {"skill": "stuck", "inputs": ["drug_name"], "steps": [
        {"id": "counts",
         "calls": [{"tool": "count_reactions", "arguments": {"drug": "{drug_name}"}}]},
        {"id": "signals", "requires": ["counts", "map_terms"],
         "calls": [{"tool": "signal", "arguments": {"drug": "{drug_name}"}}]}]}
    runner = SkillRunner(stuck, execute=lambda tool, a: GATED_RESPONSES[tool])
    handed = runner.handover(_run_to_end(runner, {"drug_name": "x"}))
    assert handed["steps_done"] == ["counts"]
    assert handed["stalled"] == [{"step": "signals", "waiting_for": ["map_terms"]}]


PAPERS = {
    "skill": "papers", "inputs": ["reactions"], "tables": {"papers": "fact"},
    "steps": [{"id": "literature", "for_each": "reactions", "as": "reaction",
               "calls": [{"tool": "search_papers", "arguments": {"query": "{reaction}"}}],
               "collect": {"papers": {"path": "data", "flatten": True, "fields": [
                   "$item as reaction", "pmid", "title", "doi_url as doi"]}}}],
}


def test_fields_over_a_list_of_records_give_one_row_for_each_record():
    """A paper without a DOI is a row without a `doi`: nothing after it moves up."""
    found = {"DEAFNESS": [{"pmid": "1", "title": "A", "doi_url": "https://doi.org/a", "x": 0},
                          {"pmid": "2", "title": "B"},
                          {"pmid": "3", "title": "C", "doi_url": "https://doi.org/c"}],
             "TINNITUS": [{"pmid": "4", "title": "D", "doi_url": "https://doi.org/d"}]}
    runner = SkillRunner(PAPERS, execute=lambda tool, a: {"data": found[a["query"]]})
    run_id = _run_to_end(runner, {"reactions": ["DEAFNESS", "TINNITUS"]})
    assert runner.handover(run_id)["facts"]["papers"] == [
        {"reaction": "DEAFNESS", "pmid": "1", "title": "A", "doi": "https://doi.org/a"},
        {"reaction": "DEAFNESS", "pmid": "2", "title": "B"},
        {"reaction": "DEAFNESS", "pmid": "3", "title": "C", "doi": "https://doi.org/c"},
        {"reaction": "TINNITUS", "pmid": "4", "title": "D", "doi": "https://doi.org/d"}]


def test_an_answer_whose_rows_are_not_objects_is_refused_not_a_crash():
    """A model can hand back strings where rows were asked for; the run must ask again."""
    rules = {"prr_table": [{"flag": {"field": "flagged", "from": "prr", "op": ">=", "value": 2}}]}
    (failure,) = check_facts(rules, {"prr_table": ["stub"]}, {})
    assert failure["fact"] == "prr_table" and "not an object" in failure["reason"]


# A judged mapping is checked for membership, then shown with its reason and placing.
MAPPED = {
    "skill": "mapped", "inputs": ["drug_name"], "optional_inputs": ["requested_aes"],
    "tables": {"faers_term_rows": "fact", "requested_meddra": "fact"},
    "steps": [
        {"id": "faers_counts",
         "calls": [{"tool": "count_reactions", "arguments": {"drug": "{drug_name}"}}],
         "collect": {"faers_term_rows": {"path": "result", "flatten": True, "fields": ["term"]}}},
        {"id": "requested_terms", "requires": ["faers_counts"], "when": "requested_aes",
         "judge": ["requested_meddra"],
         "mapping": {"requested_meddra": {"of": "requested_aes",
                                          "onto": {"rows": "faers_term_rows", "field": "term"}}},
         "produces": ["requested_meddra"]},
    ],
}
FAERS_TERMS = {"result": [{"term": t} for t in ("DEAFNESS", "TINNITUS", "FALL", "NAUSEA")]}
ANSWER = {"requested_meddra": [
    {"of": "ototoxicity", "term": "DEAFNESS", "reason": "hearing loss is the ototoxic injury",
     "concept": ["ear", "hearing", "vestibular"]},
    {"of": "ototoxicity", "term": "FALL", "reason": "may follow from dizziness",
     "concept": ["ear", "hearing", "vestibular"]}]}
MAPPED_INPUTS = {"drug_name": "x", "requested_aes": ["ototoxicity"]}


def _recorded_lookup(term):
    recorded = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ols"
                           / "placing_probe_2026-09-21.json").read_text())
    return recorded.get(term, {})


def _mapped_handover(execute=lambda tool, a: FAERS_TERMS, ask=lambda q: ANSWER):
    runner = SkillRunner(MAPPED, execute=execute, ask=ask, lookup=_recorded_lookup)
    return runner.handover(_run_to_end(runner, MAPPED_INPUTS))


def test_a_judged_mapping_becomes_a_table_with_the_reason_and_the_placing_of_each_term():
    facts = _mapped_handover()["facts"]
    assert [(r["of"], r["term"], r["placing"]) for r in facts["requested_meddra"]] == [
        ("ototoxicity", "DEAFNESS", "placed"), ("ototoxicity", "FALL", "not placed")]
    assert facts["requested_meddra"][0]["reason"] == "hearing loss is the ototoxic injury"
    assert re.search(r"ear|hearing", facts["requested_meddra"][0]["under"], re.I)
    assert facts["requested_meddra_terms"] == ["DEAFNESS", "FALL"]


def test_a_mapped_term_that_is_not_in_the_sources_list_is_refused_and_asked_again():
    """"KIDNEY DAMAGE" is not a FAERS term: an invented term never reaches a query."""
    asked = []
    answers = iter([{"requested_meddra": [{"of": "ototoxicity", "term": "HEARING DAMAGE",
                                           "reason": "r", "concept": ["ear"]}]}, ANSWER])
    handed = _mapped_handover(ask=lambda q: asked.append(q) or next(answers))
    assert "HEARING DAMAGE" in asked[1]["problem"]
    assert [r["term"] for r in handed["facts"]["requested_meddra"]] == ["DEAFNESS", "FALL"]


def test_the_mapping_question_carries_the_sources_whole_term_list_past_the_payload_cap():
    """The agent must see the whole term list it is asked to copy from, however long."""
    terms = [f"REACTION TERM {n}" for n in range(1000)]
    wide = {"result": [{"term": t, "count": 1000 - n} for n, t in enumerate(terms)]}
    asked = []
    reply = {"requested_meddra": [{"of": "ototoxicity", "term": "REACTION TERM 500",
                                   "reason": "r", "concept": ["ear"]}]}
    handed = _mapped_handover(execute=lambda tool, a: wide,
                              ask=lambda q: asked.append(q) or reply)
    (question,) = asked
    assert "omitted" in question["context"]["faers_term_rows"], "the rows stay under the cap"
    assert question["choices"] == {"requested_meddra": terms}
    assert handed["facts"]["requested_meddra_terms"] == ["REACTION TERM 500"]


def test_the_handover_names_which_facts_are_judged_mappings():
    """The report check needs to know which tables must be shown to the reader."""
    assert _mapped_handover()["mappings"] == ["requested_meddra"]
