"""Spike: the SERVER runs the process, the way Novartis's navigator does.

The gap we measured is not the notation, it is the runtime. In the Novartis PoC a
Python navigator holds SessionState, calls `advance()`, evaluates every gateway
with a predicate over state IT computed, and invokes the action functions itself —
no LLM in the control loop. Our first port left all four of those with the model,
and the model duly failed to start the loop (2 of 3 runs) or to finish it (1 of 3).

SMCP can close that gap because it already holds the whole registry in-process:
ExecuteTool is constructed with `tooluniverse=self`. So the server can run a step's
calls itself and hand back only what the next step needs.

The executor is injected here, so these tests need no ToolUniverse and no network.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_runner import SkillRunner

pytestmark = pytest.mark.unit

GRAPH = {
    "skill": "demo",
    "inputs": ["drug_name"],
    "steps": [
        {"id": "resolve",
         "calls": [{"tool": "resolve_drug", "arguments": {"name": "{drug_name}"}}],
         "extract": {"chembl_id": "data.id"}},
        {"id": "signals", "requires": ["resolve"],
         "calls": [{"tool": "disproportionality",
                    "arguments": {"chembl_id": "{chembl_id}"}}],
         "extract": {"rows": "data.rows"},
         "derive": {"strong_signal": {"from": "rows", "field": "prr",
                                      "op": ">=", "value": 5, "mode": "any"}}},
        {"id": "stratify", "requires": ["signals"], "when": "strong_signal",
         "calls": [{"tool": "stratify", "arguments": {"chembl_id": "{chembl_id}"}}]},
        {"id": "report", "requires": ["signals"], "calls": []},
    ],
}


def _runner(responses):
    """Injected executor: tool name -> response, or a callable raising."""
    calls = []

    def execute(tool, arguments):
        calls.append((tool, arguments))
        value = responses[tool]
        if isinstance(value, Exception):
            raise value
        return value

    return SkillRunner(GRAPH, execute=execute), calls


OK = {
    "resolve_drug": {"data": {"id": "CHEMBL88"}},
    "disproportionality": {"data": {"rows": [{"prr": 17.7}, {"prr": 1.2}]}},
    "stratify": {"data": {"sex": "F"}},
}
WEAK = dict(OK, disproportionality={"data": {"rows": [{"prr": 1.1}]}})


# --- the server holds the state ---------------------------------------------

def test_starting_a_run_returns_an_id_and_the_first_step():
    runner, _ = _runner(OK)
    run = runner.start({"drug_name": "cisplatin"})
    assert run["run_id"]
    assert run["step"]["id"] == "resolve"


def test_two_runs_do_not_share_state():
    runner, _ = _runner(OK)
    a = runner.start({"drug_name": "cisplatin"})
    b = runner.start({"drug_name": "lutetium"})
    assert a["run_id"] != b["run_id"]
    runner.advance(a["run_id"])
    assert runner.state(b["run_id"])["done"] == []


# --- the server runs the calls ----------------------------------------------

def test_advancing_executes_the_step_s_calls_without_the_model():
    runner, calls = _runner(OK)
    run = runner.start({"drug_name": "cisplatin"})
    runner.advance(run["run_id"])
    assert calls[0] == ("resolve_drug", {"name": "cisplatin"})


def test_what_a_step_extracts_composes_the_next_call():
    """The chain that the model used to carry by hand: an id out of step one
    becomes an argument of step two, without the model ever seeing it."""
    runner, calls = _runner(OK)
    run = runner.start({"drug_name": "cisplatin"})
    runner.advance(run["run_id"])          # resolve
    runner.advance(run["run_id"])          # signals
    assert calls[1] == ("disproportionality", {"chembl_id": "CHEMBL88"})


def test_the_caller_gets_the_extracted_values_not_the_raw_payload():
    runner, _ = _runner(OK)
    run = runner.start({"drug_name": "cisplatin"})
    out = runner.advance(run["run_id"])
    assert out["extracted"] == {"chembl_id": "CHEMBL88"}
    assert "data" not in out


# --- gateways decided by code, from real results ----------------------------

def test_a_gateway_is_computed_from_the_data_not_reported_by_the_model():
    runner, _ = _runner(OK)
    run = runner.start({"drug_name": "cisplatin"})
    runner.advance(run["run_id"])          # resolve
    out = runner.advance(run["run_id"])    # signals -> prr 17.7 means strong
    assert out["extracted"]["strong_signal"] is True
    assert out["next_step"]["id"] == "stratify"


def test_the_same_gateway_stays_shut_when_the_data_does_not_support_it():
    runner, _ = _runner(WEAK)
    run = runner.start({"drug_name": "cisplatin"})
    runner.advance(run["run_id"])
    out = runner.advance(run["run_id"])    # prr 1.1 -> no strong signal
    assert out["extracted"]["strong_signal"] is False
    assert out["next_step"]["id"] == "report"


# --- failure and completion --------------------------------------------------

def test_a_failing_call_is_recorded_and_the_run_carries_on():
    """A broken tool is not a reason to abandon the procedure — that was the
    fda_pharmacogenomic_biomarkers case, where one bot-blocked tool ended a run."""
    runner, _ = _runner(dict(OK, disproportionality=RuntimeError("HTTP 500")))
    run = runner.start({"drug_name": "cisplatin"})
    runner.advance(run["run_id"])
    out = runner.advance(run["run_id"])
    assert out["failures"], out
    assert out["failures"][0]["tool"] == "disproportionality"
    assert out["next_step"] is not None


def test_the_run_finishes_when_every_runnable_step_is_done():
    runner, _ = _runner(WEAK)
    run = runner.start({"drug_name": "cisplatin"})
    for _ in range(6):
        out = runner.advance(run["run_id"])
        if out.get("finished"):
            break
    assert out["finished"] is True
    assert runner.state(run["run_id"])["done"] == ["resolve", "signals", "report"]


# --- list mapping, from real payload shapes ---------------------------------
# FAERS returns a bare list of {term, count}; the next step needs the term
# STRINGS, in order, capped. The prose body spends five lines telling the model
# not to retype them (MedDRA is case- and spelling-strict, "Haemorrhage" not
# "hemorrhage") — carrying them mechanically is the whole point.

FAERS_GRAPH = {
    "skill": "faers",
    "inputs": ["drug_name"],
    "steps": [
        {"id": "counts",
         "calls": [{"tool": "counts", "arguments": {"medicinalproduct": "{drug_name}"}}],
         "extract": {"top_aes": {"path": "result[].term", "limit": 2}}},
        {"id": "signals", "requires": ["counts"],
         "for_each": "top_aes", "as": "adverse_event",
         "calls": [{"tool": "dispro",
                    "arguments": {"adverse_event": "{adverse_event}"}}]},
    ],
}

FAERS_OK = {
    "counts": {"result": [{"term": "DEATH", "count": 1598},
                          {"term": "HOT FLUSH", "count": 784},
                          {"term": "FALL", "count": 475}]},
    "dispro": {"data": {"prr": 2.0}},
}


def test_a_list_of_records_maps_to_the_field_the_next_step_needs():
    def execute(tool, arguments):
        return FAERS_OK[tool]
    runner = SkillRunner(FAERS_GRAPH, execute=execute)
    run = runner.start({"drug_name": "enzalutamide"})
    out = runner.advance(run["run_id"])
    assert out["extracted"]["top_aes"] == ["DEATH", "HOT FLUSH"]


def test_the_mapped_terms_drive_one_call_each_verbatim():
    calls = []

    def execute(tool, arguments):
        calls.append((tool, arguments))
        return FAERS_OK[tool]
    runner = SkillRunner(FAERS_GRAPH, execute=execute)
    run = runner.start({"drug_name": "enzalutamide"})
    runner.advance(run["run_id"])
    runner.advance(run["run_id"])
    assert [a["adverse_event"] for t, a in calls if t == "dispro"] == ["DEATH", "HOT FLUSH"]


def test_a_dotted_path_into_the_first_record_still_works():
    """DailyMed puts the setid the label phases need at data.0.setid."""
    graph = {"skill": "dm", "inputs": ["drug_name"],
             "steps": [{"id": "spl",
                        "calls": [{"tool": "spls", "arguments": {"query": "{drug_name}"}}],
                        "extract": {"setid": "data.0.setid"}}]}
    runner = SkillRunner(graph, execute=lambda t, a: {
        "data": [{"title": "XTANDI", "setid": "b129fdc9-1d8e-425c"}]})
    run = runner.start({"drug_name": "enzalutamide"})
    out = runner.advance(run["run_id"])
    assert out["extracted"]["setid"] == "b129fdc9-1d8e-425c"


# --- a step that cannot be built must not end the run ------------------------
# Live: the FAERS extraction missed, so the next step's for_each list was absent
# and SkillGraphError propagated out of advance(), killing a ten-step run at
# step four. A navigator that dies because one value is missing is worse than the
# model it replaced — Novartis's would have taken the other branch.

BLOCKED_GRAPH = {
    "skill": "blocked",
    "inputs": ["drug_name"],
    "steps": [
        {"id": "counts", "calls": [{"tool": "counts", "arguments": {}}],
         "extract": {"top_aes": "nowhere.at.all"}},
        {"id": "signals", "requires": ["counts"], "for_each": "top_aes",
         "as": "ae", "calls": [{"tool": "dispro", "arguments": {"ae": "{ae}"}}]},
        {"id": "trials", "requires": ["counts"],
         "calls": [{"tool": "trials", "arguments": {"q": "{drug_name}"}}]},
    ],
}


def test_a_step_whose_inputs_are_missing_is_blocked_not_fatal():
    runner = SkillRunner(BLOCKED_GRAPH, execute=lambda t, a: {"result": []})
    run = runner.start({"drug_name": "enzalutamide"})
    runner.advance(run["run_id"])            # counts — extraction misses
    out = runner.advance(run["run_id"])      # signals — cannot be built
    assert out["blocked"], out
    assert "top_aes" in out["blocked"][0]["reason"]


def test_the_run_continues_past_a_blocked_step():
    """The other four sources do not depend on FAERS terms — they must still run."""
    ran = []
    runner = SkillRunner(BLOCKED_GRAPH,
                         execute=lambda t, a: ran.append(t) or {"result": []})
    run = runner.start({"drug_name": "enzalutamide"})
    for _ in range(5):
        out = runner.advance(run["run_id"])
        if out.get("finished"):
            break
    assert "trials" in ran
    assert runner.state(run["run_id"])["blocked"]


# --- a gateway must not decide on data it never got --------------------------
# Live on enzalutamide: `signals` failed to extract, so `strong_signal` derived
# from an empty list and came out False — and the stratify step was skipped as if
# the data had said "no strong signal". A missing input and a genuine negative
# are different answers, and only one of them is safe to branch on.

DERIVE_GRAPH = {
    "skill": "d", "inputs": ["drug"],
    "steps": [
        {"id": "signals", "calls": [{"tool": "dispro", "arguments": {}}],
         "extract": {"rows": "data.results"},
         "derive": {"strong": {"from": "rows", "field": "prr",
                               "op": ">=", "value": 5, "mode": "any"}}},
        {"id": "stratify", "requires": ["signals"], "when": "strong",
         "calls": [{"tool": "strat", "arguments": {}}]},
        {"id": "report", "requires": ["signals"], "calls": []},
    ],
}


def test_a_gateway_over_a_missing_fact_is_unknown_not_false():
    runner = SkillRunner(DERIVE_GRAPH, execute=lambda t, a: {"data": {}})
    run = runner.start({"drug": "enzalutamide"})
    out = runner.advance(run["run_id"])
    assert out["extracted"]["strong"] is None, out["extracted"]


def test_an_unknown_gateway_is_reported_so_the_skip_is_not_silent():
    runner = SkillRunner(DERIVE_GRAPH, execute=lambda t, a: {"data": {}})
    run = runner.start({"drug": "enzalutamide"})
    out = runner.advance(run["run_id"])
    assert any("strong" in b["reason"] for b in out["blocked"]), out["blocked"]


def test_a_gateway_over_real_but_empty_rows_is_a_genuine_no():
    """Rows came back and none reached the threshold — that IS a decision."""
    runner = SkillRunner(DERIVE_GRAPH,
                         execute=lambda t, a: {"data": {"results": []}})
    run = runner.start({"drug": "enzalutamide"})
    out = runner.advance(run["run_id"])
    assert out["extracted"]["strong"] is False
    assert out["next_step"]["id"] == "report"


# --- gathering across a loop step's calls ------------------------------------
# FAERS_calculate_disproportionality answers ONE metrics object per call —
# data.metrics.PRR.value — and the step makes one call per reaction. `extract`
# takes the first match, which is the wrong shape: the gateway needs every PRR.

COLLECT_GRAPH = {
    "skill": "c", "inputs": ["drug"],
    "steps": [
        {"id": "counts", "calls": [{"tool": "counts", "arguments": {}}],
         "extract": {"terms": "[].term"}},
        {"id": "signals", "requires": ["counts"], "for_each": "terms", "as": "t",
         "calls": [{"tool": "dispro", "arguments": {"ae": "{t}"}}],
         "collect": {"prrs": "data.metrics.PRR.value"},
         "derive": {"strong": {"from": "prrs", "op": ">=", "value": 5,
                               "mode": "any"}}},
    ],
}


def _dispro(prr):
    return {"data": {"metrics": {"PRR": {"value": prr}}}}


def test_a_loop_step_gathers_the_value_from_every_call():
    prrs = iter([7.5, 1.2])

    def execute(tool, arguments):
        return ({"result": None} if tool == "counts" else _dispro(next(prrs))) \
            if tool != "counts" else [{"term": "A"}, {"term": "B"}]
    runner = SkillRunner(COLLECT_GRAPH, execute=execute)
    run = runner.start({"drug": "x"})
    runner.advance(run["run_id"])
    out = runner.advance(run["run_id"])
    assert out["extracted"]["prrs"] == [7.5, 1.2]


def test_the_gateway_decides_from_the_gathered_values():
    prrs = iter([7.5, 1.2])

    def execute(tool, arguments):
        return [{"term": "A"}, {"term": "B"}] if tool == "counts" \
            else _dispro(next(prrs))
    runner = SkillRunner(COLLECT_GRAPH, execute=execute)
    run = runner.start({"drug": "x"})
    runner.advance(run["run_id"])
    out = runner.advance(run["run_id"])
    assert out["extracted"]["strong"] is True


def test_no_value_reaching_the_threshold_is_a_genuine_negative():
    prrs = iter([1.1, 1.2])

    def execute(tool, arguments):
        return [{"term": "A"}, {"term": "B"}] if tool == "counts" \
            else _dispro(next(prrs))
    runner = SkillRunner(COLLECT_GRAPH, execute=execute)
    run = runner.start({"drug": "x"})
    runner.advance(run["run_id"])
    out = runner.advance(run["run_id"])
    assert out["extracted"]["strong"] is False


# --- one door, not two -------------------------------------------------------
# execute_tool is not a second implementation: its class calls run_one_function
# and then NORMALISES — JSON-decoding a string return and wrapping any non-dict
# as {"result": ...}. Calling run_one_function directly skipped that, so the
# runner saw a bare list where the agent (and every saved trace) sees
# {"result": [...]}, and an extraction path written from a trace missed. The
# runner goes through the same normalisation the agent does.

def test_a_bare_return_is_wrapped_the_way_execute_tool_wraps_it():
    from tooluniverse.skill_runner import normalised_executor
    execute = normalised_executor(lambda call: [{"term": "DEATH"}])
    assert execute("counts", {}) == {"result": [{"term": "DEATH"}]}


def test_a_dict_return_passes_through_untouched():
    from tooluniverse.skill_runner import normalised_executor
    payload = {"status": "success", "data": {"id": "CHEMBL88"}}
    execute = normalised_executor(lambda call: payload)
    assert execute("resolve", {}) == payload


def test_a_json_string_return_is_decoded():
    from tooluniverse.skill_runner import normalised_executor
    execute = normalised_executor(lambda call: '{"data": {"id": "X"}}')
    assert execute("resolve", {}) == {"data": {"id": "X"}}


def test_a_non_json_string_return_is_wrapped_not_lost():
    from tooluniverse.skill_runner import normalised_executor
    execute = normalised_executor(lambda call: "no studies found")
    assert execute("trials", {}) == {"result": "no studies found"}


def test_the_call_is_passed_in_the_shape_run_one_function_expects():
    from tooluniverse.skill_runner import normalised_executor
    seen = {}

    def dispatch(call):
        seen.update(call)
        return {}
    normalised_executor(dispatch)("counts", {"medicinalproduct": "X"})
    assert seen == {"name": "counts", "arguments": {"medicinalproduct": "X"}}


# --- the evidence has to survive the run -------------------------------------
# The runner extracted what the NEXT step needed and threw the rest away, which
# is fine for control and useless for the report: the model still has to see the
# label text, the trial list, the papers. The run keeps them, per step, and hands
# them over once at the end — so raw payloads never pass through the transcript
# on the way, which is what makes this cheaper than the model relaying calls.

def test_a_run_keeps_each_step_s_results_for_the_report():
    runner = SkillRunner(GRAPH, execute=lambda t, a: {"data": {"id": "CHEMBL88"}})
    run = runner.start({"drug_name": "cisplatin"})
    runner.advance(run["run_id"])
    bundle = runner.bundle(run["run_id"])
    assert bundle["results"]["resolve"] == [{"data": {"id": "CHEMBL88"}}]


def test_the_bundle_carries_the_facts_and_what_went_wrong():
    runner = SkillRunner(GRAPH, execute=lambda t, a: {"data": {"id": "CHEMBL88"}})
    run = runner.start({"drug_name": "cisplatin"})
    runner.advance(run["run_id"])
    bundle = runner.bundle(run["run_id"])
    assert bundle["facts"]["chembl_id"] == "CHEMBL88"
    assert bundle["steps_done"] == ["resolve"]
    assert bundle["failures"] == [] and bundle["blocked"] == []


def test_a_huge_payload_is_capped_so_the_bundle_stays_sendable():
    runner = SkillRunner(GRAPH, execute=lambda t, a: {"data": {"id": "x" * 200_000}})
    run = runner.start({"drug_name": "cisplatin"})
    runner.advance(run["run_id"])
    import json as _json
    assert len(_json.dumps(runner.bundle(run["run_id"])["results"])) < 120_000


# --- pulling a value out of a string, not just a path ------------------------
# Measured: FAERS returns 3 reaction terms for "lutetium lu 177 dotatate" and 100
# for "LUTATHERA" — case is irrelevant, the BRAND is what is indexed. The label
# lookup already knows the brand: DailyMed's SPL title starts with it. So the
# graph can chain brand -> FAERS instead of hoping the model remembers to retry,
# which is what the prose body asks it to do.

def test_a_regex_lifts_a_value_out_of_a_returned_string():
    graph = {"skill": "b", "inputs": ["drug_name"],
             "steps": [{"id": "spl",
                        "calls": [{"tool": "spls", "arguments": {}}],
                        "extract": {"brand": {"path": "data.0.title",
                                              "regex": r"^([A-Za-z0-9-]+)"}}}]}
    title = "LUTATHERA (LUTETIUM LU 177 DOTATATE) INJECTION [AAA USA, INC.]"
    runner = SkillRunner(graph, execute=lambda t, a: {"data": [{"title": title}]})
    run = runner.start({"drug_name": "lutetium lu 177 dotatate"})
    assert runner.advance(run["run_id"])["extracted"]["brand"] == "LUTATHERA"


def test_a_value_falls_back_to_another_fact_when_the_lift_fails():
    """No brand in the title is not a reason to stall the FAERS phase — fall back
    to the name the question gave us and carry on."""
    graph = {"skill": "b", "inputs": ["drug_name"],
             "steps": [{"id": "spl",
                        "calls": [{"tool": "spls", "arguments": {}}],
                        "extract": {"faers_name": {"path": "data.0.title",
                                                   "regex": r"^([A-Z]{4,})",
                                                   "default_from": "drug_name"}}}]}
    runner = SkillRunner(graph, execute=lambda t, a: {"data": [{"title": "x"}]})
    run = runner.start({"drug_name": "cisplatin"})
    assert runner.advance(run["run_id"])["extracted"]["faers_name"] == "cisplatin"


# --- what the QUESTION asks for is an input, not a derivable ------------------
# "What does FAERS show for Lutathera — especially myelodysplastic syndrome and
# renal impairment?" Neither term is in the twelve the graph picks by report
# count, so the run came back full of correct numbers that did not answer the
# question. Those terms exist only in the question; they must be bound as an
# input and UNIONED with the frequency-ranked ones.

UNION_GRAPH = {
    "skill": "u", "inputs": ["drug_name", "requested_aes"],
    "steps": [
        {"id": "counts", "calls": [{"tool": "counts", "arguments": {}}],
         "extract": {"top_aes": {"path": "result[].term", "limit": 3}},
         "combine": {"signal_aes": {"union": ["requested_aes", "top_aes"],
                                    "limit": 5}}},
        {"id": "signals", "requires": ["counts"], "for_each": "signal_aes",
         "as": "ae", "calls": [{"tool": "d", "arguments": {"ae": "{ae}"}}]},
    ],
}
COUNTS = {"result": [{"term": "DEATH"}, {"term": "NAUSEA"}, {"term": "FATIGUE"}]}


def test_the_terms_the_question_named_are_kept_even_when_they_are_not_frequent():
    runner = SkillRunner(UNION_GRAPH, execute=lambda t, a: COUNTS)
    run = runner.start({"drug_name": "LUTATHERA",
                        "requested_aes": ["MYELODYSPLASTIC SYNDROME",
                                          "RENAL IMPAIRMENT"]})
    got = runner.advance(run["run_id"])["extracted"]["signal_aes"]
    assert got[:2] == ["MYELODYSPLASTIC SYNDROME", "RENAL IMPAIRMENT"]
    assert "DEATH" in got


def test_the_requested_terms_come_first_so_a_cap_cannot_drop_them():
    runner = SkillRunner(UNION_GRAPH, execute=lambda t, a: COUNTS)
    run = runner.start({"drug_name": "LUTATHERA",
                        "requested_aes": ["MYELODYSPLASTIC SYNDROME",
                                          "RENAL IMPAIRMENT"]})
    got = runner.advance(run["run_id"])["extracted"]["signal_aes"]
    assert len(got) == 5 and got[0] == "MYELODYSPLASTIC SYNDROME"


def test_a_question_that_names_nothing_still_runs_on_frequency():
    runner = SkillRunner(UNION_GRAPH, execute=lambda t, a: COUNTS)
    run = runner.start({"drug_name": "LUTATHERA"})
    got = runner.advance(run["run_id"])["extracted"]["signal_aes"]
    assert got == ["DEATH", "NAUSEA", "FATIGUE"]


def test_a_duplicate_between_requested_and_frequent_is_not_run_twice():
    runner = SkillRunner(UNION_GRAPH, execute=lambda t, a: COUNTS)
    run = runner.start({"drug_name": "LUTATHERA", "requested_aes": ["DEATH"]})
    got = runner.advance(run["run_id"])["extracted"]["signal_aes"]
    assert got.count("DEATH") == 1
