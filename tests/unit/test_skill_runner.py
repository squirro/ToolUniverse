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
