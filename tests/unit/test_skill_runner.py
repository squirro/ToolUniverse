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

from tooluniverse.skill_runner import SkillRunner, normalised_executor

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


# --- repair: ask the agent, then retry ---------------------------------------
# Measured: the agent binds "lutetium Lu-177 dotatate" from the question, three
# times identically — and DailyMed returns 0 SPLs for it, while "lutetium lu 177
# dotatate" returns 1. A correct, repeatable binding would have produced a
# confidently wrong report. The variant is world knowledge (Lu-177 is an isotope
# notation), which the agent has and the server does not.
#
# So the server asks, but stays in charge: it decides the lookup failed, frames
# the question, validates by re-querying, and gives up after two attempts. The
# model is an oracle for one narrow thing, never the scheduler.

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
    execute, seen = _executor("lutetium lu 177 dotatate")
    runner = SkillRunner(REPAIR_GRAPH, execute=execute,
                         ask=lambda q: ["lutetium lu 177 dotatate"])
    run = runner.start({"drug_name": "lutetium Lu-177 dotatate"})
    out = runner.advance(run["run_id"])
    assert out["extracted"]["setid"] == "72d1a024"
    assert seen == ["lutetium Lu-177 dotatate", "lutetium lu 177 dotatate"]


def test_the_repair_question_names_the_tool_and_what_came_back():
    execute, _ = _executor("never")
    asked = {}
    runner = SkillRunner(REPAIR_GRAPH, execute=execute,
                         ask=lambda q: asked.update(q) or [])
    run = runner.start({"drug_name": "lutetium Lu-177 dotatate"})
    runner.advance(run["run_id"])
    assert asked["tool"] == "spls"
    assert asked["argument"] == "drug_name"
    assert asked["value"] == "lutetium Lu-177 dotatate"


def test_repair_gives_up_after_two_attempts():
    """Two is enough for a spelling or a brand, and not enough to spend a minute
    on a lookup that will never resolve."""
    execute, seen = _executor("never")
    runner = SkillRunner(REPAIR_GRAPH, execute=execute,
                         ask=lambda q: ["variant one", "variant two", "variant three"])
    run = runner.start({"drug_name": "original"})
    out = runner.advance(run["run_id"])
    assert seen == ["original", "variant one", "variant two"]
    assert any("could not be resolved" in b["reason"] for b in out["blocked"])


def test_a_lookup_that_works_first_time_never_asks():
    execute, seen = _executor("lutetium lu 177 dotatate")
    called = []
    runner = SkillRunner(REPAIR_GRAPH, execute=execute,
                         ask=lambda q: called.append(q) or [])
    run = runner.start({"drug_name": "lutetium lu 177 dotatate"})
    runner.advance(run["run_id"])
    assert called == [] and len(seen) == 1


def test_without_an_ask_callback_the_runner_behaves_exactly_as_before():
    execute, seen = _executor("never")
    runner = SkillRunner(REPAIR_GRAPH, execute=execute)
    run = runner.start({"drug_name": "original"})
    runner.advance(run["run_id"])
    assert seen == ["original"]


# --- a declared value that never arrives must be recorded --------------------
# Live, without the repair callback: the identity step declares it produces
# `setid`, DailyMed returned nothing for the agent's binding, and the run carried
# on with setid=None and blocked=[] — no trace anywhere. Everything downstream
# then answered on the wrong drug form. Repair is the recovery; this is the
# honesty when there is no recovery.

MISS_GRAPH = {
    "skill": "m", "inputs": ["drug_name"],
    "steps": [{"id": "identity",
               "calls": [{"tool": "spls", "arguments": {}}],
               "extract": {"setid": "data.0.setid"},
               "produces": ["setid"]},
              {"id": "report", "requires": ["identity"], "calls": []}],
}


def test_a_declared_value_that_never_arrives_is_recorded():
    runner = SkillRunner(MISS_GRAPH, execute=lambda t, a: {"data": []})
    run = runner.start({"drug_name": "lutetium Lu-177 dotatate"})
    out = runner.advance(run["run_id"])
    assert out["unresolved"] == [{"step": "identity", "fact": "setid"}]


def test_an_unresolved_value_does_not_stop_the_run():
    """The other steps may not need it — but the report must be able to say so."""
    runner = SkillRunner(MISS_GRAPH, execute=lambda t, a: {"data": []})
    run = runner.start({"drug_name": "x"})
    runner.advance(run["run_id"])
    out = runner.advance(run["run_id"])
    assert out["finished"] is True


def test_the_bundle_carries_what_never_resolved():
    runner = SkillRunner(MISS_GRAPH, execute=lambda t, a: {"data": []})
    run = runner.start({"drug_name": "x"})
    runner.advance(run["run_id"])
    assert runner.bundle(run["run_id"])["unresolved"] == [
        {"step": "identity", "fact": "setid"}]


def test_a_value_that_does_arrive_is_not_recorded_as_unresolved():
    runner = SkillRunner(MISS_GRAPH,
                         execute=lambda t, a: {"data": [{"setid": "72d1a024"}]})
    run = runner.start({"drug_name": "x"})
    assert runner.advance(run["run_id"])["unresolved"] == []


# --- the pure pieces, shared with the Temporal host (DSR-707) ----------------
# `absorb`, `resolved`, `substitute`, `trim` and `apply` never touch the network,
# the clock or a random source, so an async driver can await the calls and hand
# the results to the same functions the sync driver uses.

from tooluniverse.skill_runner import absorb  # noqa: E402


def test_absorb_extracts_by_path_regex_limit_and_default():
    spec = {"id": "s", "extract": {
        "setid": "data.0.setid",
        "brand": {"path": "data.0.title", "regex": "^([A-Za-z0-9-]{3,})"},
        "terms": {"path": "result[].term", "limit": 2},
        "name": {"path": "data.0.missing", "default_from": "drug_name"},
        "never": "data.0.absent",
    }}
    results = [{"data": [{"setid": "72d1", "title": "LUTATHERA (lutetium) kit"}]},
               {"result": [{"term": "A"}, {"term": "B"}, {"term": "C"}]}]

    out = absorb(spec, results, facts={"drug_name": "lutathera"})

    assert out["facts"] == {"setid": "72d1", "brand": "LUTATHERA",
                            "terms": ["A", "B"], "name": "lutathera"}
    assert out["unresolved"] == ["never"]
    assert out["blocked"] == []


def test_absorb_collects_combines_and_derives_and_blocks_an_unknown():
    spec = {"id": "prr",
            "collect": {"prrs": "data.metrics.PRR.value"},
            "combine": {"signal_aes": {"union": ["requested", "top"], "limit": 3}},
            "derive": {"strong": {"from": "prrs", "op": ">=", "value": 5, "mode": "any"},
                       "ghost": {"from": "never_extracted", "op": ">", "value": 0}}}
    results = [{"data": {"metrics": {"PRR": {"value": 7.1}}}},
               {"data": {"metrics": {"PRR": {"value": 0.9}}}},
               {"data": {}}]

    out = absorb(spec, results, facts={"requested": ["MDS"], "top": ["MDS", "Nausea", "Rash"]})

    assert out["facts"]["prrs"] == [7.1, 0.9]
    assert out["facts"]["signal_aes"] == ["MDS", "Nausea", "Rash"]
    assert out["facts"]["strong"] is True
    assert "ghost" not in out["facts"]
    assert out["undecided"] == ["ghost"]
    assert out["blocked"] == [{"step": "prr",
                               "reason": "cannot decide ghost: never_extracted was "
                                         "never extracted, so the branch was not taken"}]


from tooluniverse.skill_runner import resolved, substitute  # noqa: E402


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


from tooluniverse.skill_runner import apply, new_run, trim  # noqa: E402


def test_apply_records_everything_a_step_leaves_on_the_run():
    run = new_run({"drug_name": "x"})
    outcome = {"facts": {"setid": "72d1"}, "unresolved": ["brand"],
               "blocked": [{"step": "identity", "reason": "r"}], "undecided": []}

    apply(run, "identity", results=[{"data": 1}],
          failures=[{"tool": "t", "error": "E"}], outcome=outcome)

    assert run["done"] == ["identity"]
    assert run["results"] == {"identity": [{"data": 1}]}
    assert run["facts"] == {"drug_name": "x", "setid": "72d1"}
    assert run["failures"] == [{"tool": "t", "error": "E"}]
    assert run["unresolved"] == [{"step": "identity", "fact": "brand"}]
    assert run["blocked"] == [{"step": "identity", "reason": "r"}]


def test_trim_caps_each_payload_and_marks_the_cut():
    small, big = {"a": 1}, {"a": "x" * 50}

    out = trim([small, big], cap=20)

    assert out[0] == small
    assert out[1]["truncated"] is True and len(out[1]["preview"]) == 20


def test_start_accepts_the_run_id_a_host_already_has():
    """Temporal names the run; the runner must not invent a second identity."""
    runner, _ = _runner(OK)

    out = runner.start({"drug_name": "x"}, run_id="skill-demo-42")

    assert out["run_id"] == "skill-demo-42"
    assert runner.state("skill-demo-42")["facts"] == {"drug_name": "x"}


# --- judgement facts and matched collection (DSR-708) -------------------------


def test_collect_with_match_keeps_the_first_matching_item_per_call():
    """Live, get_HPO_ID_by_phenotype answers UPHENO:, MP:, then HP: — the human
    phenotype is third. One HP id per symptom, mechanically."""
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
    "skill": "judged",
    "inputs": ["symptoms"],
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

    def execute(tool, arguments):
        return responses[tool]

    def ask(question):
        asked.append(question)
        return answers.get(question.get("kind"), {})

    return SkillRunner(JUDGED, execute=execute, ask=ask), asked


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
    """Phase 1: the HP ids come from the lookups; which two discriminate is judged,
    and the judge must see the ids to choose among them."""
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
    run_id = runner.start({"symptoms": ["x"]})["run_id"]

    out = runner.advance(run_id)

    assert out["step_id"] == "hypothesis"
    assert [u["fact"] for u in out["unresolved"]] == ["primary_keyword", "working_hypothesis"]


# --- every shipped process runs to the end server-side ------------------------

from tooluniverse.skill_graph import GRAPHS_DIR, load_graph  # noqa: E402


def _run_to_end(runner, inputs, limit=100):
    run_id = runner.start(inputs)["run_id"]
    for _ in range(limit):
        if runner.advance(run_id)["finished"]:
            return run_id
    raise AssertionError("the run did not finish")


@pytest.mark.parametrize("skill", sorted(p.stem for p in GRAPHS_DIR.glob("*.yaml")))
def test_every_shipped_process_finishes_with_stub_tools_and_a_stub_oracle(skill):
    """The standing net: a YAML edit that the runner cannot execute fails here,
    not in a live run. Tools answer nothing; the oracle answers every judged name."""
    graph = load_graph(skill)
    runner = SkillRunner(graph, execute=lambda tool, a: {},
                         ask=lambda q: {name: ["stub"] for name in q["wants"]})
    inputs = {name: ["stub"] for name in graph.get("inputs", [])}

    run_id = _run_to_end(runner, inputs)

    state = runner.state(run_id)
    facts = state["facts"]
    off = {s["id"] for s in graph["steps"]
           if (s.get("when") and not facts.get(s["when"]))            # gate closed
           or (s.get("for_each") in facts and not facts[s["for_each"]])}  # empty loop
    accounted = set(state["done"]) | set(state["skipped"]) | off
    assert accounted == {s["id"] for s in graph["steps"]}


def test_rare_disease_diagnosis_runs_start_to_finish_with_judgement():
    """The skill that could not run server-side: three judgement points, one
    mechanical HP id per symptom, genes looked up per resolved candidate, no
    step blocked and no fact unresolved."""
    responses = {
        "get_HPO_ID_by_phenotype": {"data": {"items": [{"id": "MP:1"}, {"id": "HP:0001433"}]}},
        # Real shapes as the runner sees them: the joint tool answers a bare list
        # of names, which normalised_executor wraps as {"result": [...]}; Orphanet
        # a results list with the code and the preferred term.
        "get_joint_associated_diseases_by_HPO_ID_list": {"result": ["Gaucher disease"]},
        "Orphanet_search_diseases": {"data": {"results": [
            {"ORPHAcode": 355, "Preferred term": "Gaucher disease"}]}},
        "Orphanet_get_genes": {"data": {"orpha_code": "355", "genes": [{"Symbol": "GBA"}]}},
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
               "optimuskg_genes": [{"gene": "GBA", "relation": "CAUSES", "evidence_score": 0.8}]}
    calls, asked = [], []
    runner = SkillRunner(
        load_graph("rare-disease-diagnosis"),
        execute=lambda tool, a: calls.append((tool, a)) or responses[tool],
        ask=lambda q: asked.append(q) or {n: answers[n] for n in q["wants"]})

    run_id = _run_to_end(runner, {"symptoms": ["hepatosplenomegaly", "coarse facies"]})

    state = runner.state(run_id)
    assert state["blocked"] == [] and state["unresolved"] == []
    assert state["facts"]["hpo_ids"] == ["HP:0001433", "HP:0001433"]
    assert [(q["step"], q["kind"]) for q in asked] == [
        ("hypothesis", "judge"), ("phenotypes", "judge"), ("keyword_search", "judge"),
        ("gene_evidence_optimuskg", "delegate")]
    assert state["facts"]["genes"] == ["GBA"]
    assert ("get_joint_associated_diseases_by_HPO_ID_list",
            {"HPO_ID_list": ["HP:0001433"], "limit": 30}) in calls
    assert ("Orphanet_search_diseases",
            {"query": "lysosomal storage disorder", "limit": 20}) in calls
    assert ("MyGene_query_genes", {"query": "GBA",
            "fields": "symbol,name,entrezgene,ensembl.gene,summary"}) in calls
    assert "variant" not in state["done"], "no variant supplied, so that phase is off"


def test_the_bundle_says_which_tools_the_server_called_per_step():
    """The agent's trace shows no execute_tool for a server-side run; the bundle
    itself must carry the record of what ran, repair retries included."""
    runner, _ = _runner(OK)
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass

    calls = runner.bundle(run_id)["calls"]

    assert calls == {"resolve": ["resolve_drug"], "signals": ["disproportionality"],
                     "stratify": ["stratify"], "report": []}


# --- the author's judgement travels with the data (Rung 2, report quality) ------
# Blind-judged 2026-09-03: the modelled reports printed FAERS coding noise as
# signals because the step notes stayed on the server. The bundle now carries
# every step's notes and the process's report guidance; extraction can exclude
# what the author knows is noise; and a step can delegate calls to the agent's
# own tools (web search, code) through the same pause the judgement uses.


def test_the_bundle_carries_step_notes_and_the_report_guidance():
    graph = {"skill": "g", "inputs": [],
             "report": "Classify every signal against the label. Say which terms are nonspecific.",
             "steps": [{"id": "a", "calls": [], "notes": "A NOT_FOUND here is normal."},
                       {"id": "b", "calls": []}]}
    runner = SkillRunner(graph, execute=lambda t, a: {})
    run_id = runner.start({})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass

    bundle = runner.bundle(run_id)

    assert bundle["report"] == "Classify every signal against the label. Say which terms are nonspecific."
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
    assert out["finished"] and runner.bundle(run_id)["calls"] == {"web_context": ["exa_web_search"]}


def test_a_question_carries_the_steps_notes_so_the_agent_knows_what_shape_to_answer_in():
    """Live, a delegated web search came back as bare URLs: the notes asked for
    {title, url, snippet}, and the agent never saw them."""
    graph = {"skill": "n", "inputs": [], "steps": [
        {"id": "web", "delegate": [{"tool": "exa_web_search", "arguments": {"query": "x"}}],
         "produces": ["web_context"], "notes": "Return a list of {title, url, snippet}."},
        {"id": "judge", "requires": ["web"], "calls": [], "produces": ["pick"], "judge": ["pick"],
         "notes": "Pick the rarest two."}]}
    asked = []
    runner = SkillRunner(graph, execute=lambda t, a: {}, ask=lambda q: asked.append(q) or {n: "v" for n in q["wants"]})
    run_id = runner.start({})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass

    assert [q["notes"] for q in asked] == ["Return a list of {title, url, snippet}.", "Pick the rarest two."]


# --- the shipped rare-disease process resolves its differential to Orphanet ----
#
# Live 2026-09-04: the HPO joint tool returns bare disease names, so the report
# could link no ranked disease to Orphanet and said so. The process now looks
# each decisive candidate up by name and carries the hit — name and code — so
# every ranked disease gets its own link, and one Orphanet does not know is
# reported as such rather than dropped by index misalignment.

def _rare_disease_run(orphanet_hits):
    from tooluniverse.skill_graph import load_graph
    calls = []
    responses = {
        "get_HPO_ID_by_phenotype": {"data": {"items": [{"id": "MP:1"}, {"id": "HP:0000280"}]}},
        "get_joint_associated_diseases_by_HPO_ID_list": ["Hunter syndrome", "GM1 gangliosidosis",
                                                         "Sialuria"],
        "EuropePMC_search_articles": {"data": []},
        "MyGene_query_genes": {"hits": []},
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
        if tool == "Orphanet_search_diseases":
            hits = orphanet_hits.get(arguments["query"], [])
            return {"status": "success", "data": {"results": hits, "count": len(hits)}}
        if tool == "Orphanet_get_genes":
            return {"status": "success", "data": {"orpha_code": str(arguments["orphacode"]),
                                                  "genes": orphanet_genes.get(int(arguments["orphacode"]), [])}}
        if tool == "OpenTargets_get_disease_ids_by_name":
            mondo = mondo_ids.get(arguments["name"])
            return {"data": {"search": {"hits": [{"id": mondo, "name": arguments["name"]}] if mondo else []}}}
        return responses[tool]

    # Through the same door the worker uses: a bare list becomes {"result": [...]}.
    execute = normalised_executor(dispatch)

    answers = {"primary_keyword": "lysosomal storage disorder",
               "working_hypothesis": ["storage disorder"],
               "discriminating_features": ["coarse facies"],
               "discriminating_hpo_ids": ["HP:0000280"],
               "top_candidate": "Hunter syndrome", "genes": [],
               "optimuskg_genes": [{"gene": "IDS", "relation": "CAUSES", "evidence_score": 0.9}]}
    asked = []

    def ask(question):
        asked.append(question)
        return {name: answers[name] for name in question["wants"]}

    runner = SkillRunner(load_graph("rare-disease-diagnosis"), execute=execute, ask=ask)
    run_id = runner.start({"symptoms": ["coarse facies"]})["run_id"]
    for _ in range(60):
        if runner.advance(run_id)["finished"]:
            break
    state = runner.state(run_id)
    state["asked"] = asked
    return state, calls


def test_every_decisive_candidate_is_looked_up_in_orphanet_by_name():
    hits = {"Hunter syndrome": [{"ORPHAcode": 580, "Preferred term": "Mucopolysaccharidosis type 2"}],
            "GM1 gangliosidosis": [{"ORPHAcode": 354, "Preferred term": "GM1 gangliosidosis"}],
            "lysosomal storage disorder": [{"ORPHAcode": 93448, "Preferred term": "LSD group"}]}
    state, calls = _rare_disease_run(hits)

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


# --- collect can flatten a list-of-lists into one gene set ---------------------
#
# Orphanet answers one gene list per disease. The gene panel loops over genes,
# not over diseases, so the rows must fold into one list — and a gene shared by
# two candidates must be characterised once, not twice.

def test_collect_can_flatten_one_list_per_call_into_one_list():
    spec = {"collect": {"genes": {"path": "data.genes[].Symbol", "flatten": True}}}
    results = [{"data": {"genes": [{"Symbol": "IDUA"}]}},
               {"data": {"genes": [{"Symbol": "IDS"}, {"Symbol": "GLB1"}]}},
               {"data": {"genes": []}}]

    out = absorb(spec, results, facts={})

    assert out["facts"]["genes"] == ["IDUA", "IDS", "GLB1"]


def test_collect_can_keep_only_the_first_occurrence_of_a_value():
    spec = {"collect": {"genes": {"path": "data.genes[].Symbol", "flatten": True, "unique": True}}}
    results = [{"data": {"genes": [{"Symbol": "GLB1"}]}},
               {"data": {"genes": [{"Symbol": "NEU1"}, {"Symbol": "GLB1"}]}}]

    out = absorb(spec, results, facts={})

    assert out["facts"]["genes"] == ["GLB1", "NEU1"]


HITS = {"Hunter syndrome": [{"ORPHAcode": 580, "Preferred term": "Mucopolysaccharidosis type 2"}],
        "GM1 gangliosidosis": [{"ORPHAcode": 354, "Preferred term": "GM1 gangliosidosis"}],
        "lysosomal storage disorder": [{"ORPHAcode": 93448, "Preferred term": "LSD group"}]}


def test_genes_come_from_orphanet_per_resolved_candidate_never_from_the_model():
    """DSR-730: the model answered four genes once and none twice on identical
    data. A gene list is a claim the Run Record must vouch for, so it is an
    extraction — one Orphanet lookup per resolved candidate, folded into one
    de-duplicated list for the panel — and no step asks the model for it."""
    state, calls = _rare_disease_run(HITS)

    looked_up = sorted(int(a["orphacode"]) for t, a in calls if t == "Orphanet_get_genes")
    assert looked_up == [354, 580]
    assert state["facts"]["genes"] == ["IDS", "GLB1"]
    assert "genes" not in {n for q in state["asked"] for n in q["wants"] if q["kind"] == "judge"}
    assert [q["step"] for q in state["asked"] if q["kind"] == "judge"] == [
        "hypothesis", "phenotypes", "keyword_search"]


# --- a step that cannot be built is blamed by name, not by search ---------------
#
# Live 2026-09-04 (rare-disease, tools answering nothing): a loop whose list came
# from a step that was itself blocked could not be built, and the runner marked
# the NEXT two steps as blocked with its reason. The step that raised is the one
# to record.

def test_a_step_that_cannot_be_built_is_the_one_recorded_as_blocked():
    from tooluniverse.skill_runner import next_runnable, new_run
    graph = {"skill": "blame", "inputs": [], "steps": [
        {"id": "a", "for_each": "first_list", "as": "x",
         "calls": [{"tool": "t", "arguments": {"q": "{x}"}}]},
        {"id": "b", "requires": ["a"], "for_each": "second_list", "as": "y",
         "calls": [{"tool": "t", "arguments": {"q": "{y}"}}]},
        {"id": "c", "calls": []},
    ]}
    run = new_run({})

    offered = next_runnable(graph, run)

    assert offered["id"] == "c"
    assert [b["step"] for b in run["blocked"]] == ["a", "b"]
    assert "second_list" in run["blocked"][1]["reason"]


def test_open_targets_scored_targets_are_fetched_per_candidate_and_kept_as_returned():
    """The second gene source: name -> MONDO id -> scored targets. Scores are
    kept as Open Targets returns them; the reader sees the drop-off, no cut."""
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
    """The third source is the agent's own tool, so the run pauses and hands the
    agent the exact calls: search the disease, then evidence on its CURIE
    restricted to genes. What comes back is recorded like any other result."""
    state, calls = _rare_disease_run(HITS)

    delegated = [q for q in state["asked"] if q["kind"] == "delegate"]
    assert len(delegated) == 1
    tools = [c["tool"] for c in delegated[0]["calls"]]
    assert tools == ["OptimusKG_Search", "OptimusKG_Search"]
    search, evidence = delegated[0]["calls"]
    assert search["arguments"] == {"action": "search", "query": "Hunter syndrome",
                                   "node_types": ["disease"]}
    assert evidence["arguments"]["action"] == "evidence"
    assert evidence["arguments"]["node_types"] == ["gene"]
    assert state["facts"]["optimuskg_genes"] == [
        {"gene": "IDS", "relation": "CAUSES", "evidence_score": 0.9}]
    assert "OptimusKG_Search" not in [t for t, _ in calls]      # never executed server-side


# --- a failed loop iteration names the item it was for --------------------------
#
# Fourteen FAERS calls, one rate-limited: the report must say WHICH reaction is
# missing, not only that "FAERS_calculate_disproportionality" failed once.

def test_a_failed_iteration_is_recorded_with_its_arguments():
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
                                  "error": "RuntimeError: 429 Too Many Requests"}]
