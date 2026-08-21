"""Skills as a process graph: the server holds the plan, the agent runs one step.

Measured on sr-dev (2026-08-21, 3 probes per skill): four of the first eight
skills returned a DIFFERENT verdict across three identical runs —
`rare-disease-diagnosis` gave fail, warn and pass. The plan currently lives in the
model's head, restated as ~14k characters of standing operating procedure on every
turn, and adherence degrades as that instruction set grows. The footnote rule was
delivered on every turn and ignored on 29 of 76 answers, which is the evidence that
soft pressure has plateaued.

So the plan moves out of the prose and into data. `next_step` is pure: given the
graph and the steps already done, it returns the one step to run now, with the
exact tool calls and their arguments. No LLM planning, no state on the server.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_graph import (
    SkillGraphError,
    load_graph,
    next_step,
)

pytestmark = pytest.mark.unit

GRAPH = {
    "skill": "demo",
    "inputs": ["drug_name"],
    "steps": [
        {"id": "resolve", "label": "Resolve the drug",
         "calls": [{"tool": "OpenTargets_get_drug_chembId_by_generic_name",
                    "arguments": {"drugName": "{drug_name}"}}],
         "produces": ["chembl_id"]},
        {"id": "profile", "label": "Count reactions", "requires": ["resolve"],
         "calls": [{"tool": "FAERS_count_reactions_by_drug_event",
                    "arguments": {"medicinalproduct": "{drug_name}"}}],
         "produces": ["top_aes"]},
        {"id": "stratify", "label": "Stratify strong signals",
         "requires": ["profile"], "when": "strong_signal",
         "calls": [{"tool": "FAERS_stratify_by_demographics",
                    "arguments": {"drug_name": "{drug_name}"}}]},
        {"id": "report", "label": "Write the report", "requires": ["profile"],
         "calls": []},
    ],
}


def _step(done=(), facts=None):
    return next_step(GRAPH, done=list(done), facts=facts or {"drug_name": "cisplatin"})


# --- ordering and dependencies ---------------------------------------------

def test_the_first_step_is_offered_when_nothing_is_done():
    assert _step()["id"] == "resolve"


def test_a_step_whose_dependency_is_unmet_is_never_offered():
    """`profile` requires `resolve`, so it cannot come first."""
    assert _step()["id"] != "profile"


def test_the_next_step_follows_once_its_dependency_is_done():
    assert _step(done=["resolve"])["id"] == "profile"


def test_the_graph_ends_when_every_runnable_step_is_done():
    assert _step(done=["resolve", "profile", "report"]) is None


# --- gateways ---------------------------------------------------------------

def test_a_conditional_step_is_skipped_when_its_condition_is_absent():
    """No strong signal was found, so stratification must not be demanded —
    this is the "pick the first applicable, then STOP" gateway the prose bodies
    express in capital letters and the agent sometimes ignores."""
    assert _step(done=["resolve", "profile"])["id"] == "report"


def test_a_conditional_step_runs_when_its_condition_is_present():
    step = _step(done=["resolve", "profile"], facts={"drug_name": "cisplatin",
                                                     "strong_signal": True})
    assert step["id"] == "stratify"


def test_an_unmet_conditional_step_does_not_block_the_end():
    assert _step(done=["resolve", "profile", "report"]) is None


# --- what the agent receives -------------------------------------------------

def test_the_step_carries_its_tool_calls_with_arguments_filled_in():
    """The agent is handed the call, not asked to compose it — that is what
    removes the schema guesswork and the invented tool names."""
    call = _step()["calls"][0]
    assert call["tool"] == "OpenTargets_get_drug_chembId_by_generic_name"
    assert call["arguments"] == {"drugName": "cisplatin"}


def test_a_missing_input_is_named_rather_than_templated_into_the_call():
    with pytest.raises(SkillGraphError) as exc:
        next_step(GRAPH, done=[], facts={})
    assert "drug_name" in str(exc.value)


def test_the_step_says_what_it_produces_so_the_agent_knows_what_to_extract():
    assert _step()["produces"] == ["chembl_id"]


# --- loops -------------------------------------------------------------------
# Phase 2 of adverse-event-detection is "for the top 15-20 reactions, calculate
# disproportionality" — one call per reaction. Left as a placeholder the agent has
# to fill, it is exactly the guesswork this design removes.

LOOP_GRAPH = {
    "skill": "loopy",
    "inputs": ["drug_name"],
    "steps": [
        {"id": "profile", "calls": [], "produces": ["top_aes"]},
        {"id": "signals", "requires": ["profile"],
         "for_each": "top_aes", "as": "adverse_event",
         "calls": [{"tool": "FAERS_calculate_disproportionality",
                    "arguments": {"drug_name": "{drug_name}",
                                  "adverse_event": "{adverse_event}"}}]},
    ],
}


def test_a_loop_step_emits_one_call_per_item():
    step = next_step(LOOP_GRAPH, done=["profile"],
                     facts={"drug_name": "cisplatin",
                            "top_aes": ["nephropathy toxic", "acute renal failure"]})
    events = [c["arguments"]["adverse_event"] for c in step["calls"]]
    assert events == ["nephropathy toxic", "acute renal failure"]
    assert all(c["arguments"]["drug_name"] == "cisplatin" for c in step["calls"])


def test_a_loop_step_says_which_list_it_needs_when_it_is_missing():
    with pytest.raises(SkillGraphError) as exc:
        next_step(LOOP_GRAPH, done=["profile"], facts={"drug_name": "cisplatin"})
    assert "top_aes" in str(exc.value)


def test_a_loop_over_an_empty_list_is_not_a_step_to_run():
    """No reactions came back, so there is nothing to test for disproportionality —
    the procedure must move on rather than demand an impossible call."""
    step = next_step(LOOP_GRAPH, done=["profile"],
                     facts={"drug_name": "cisplatin", "top_aes": []})
    assert step is None


# --- loading -----------------------------------------------------------------

def test_a_graph_loads_by_skill_name():
    graph = load_graph("adverse-event-detection")
    assert graph["skill"] == "adverse-event-detection"
    assert graph["steps"], graph


def test_an_unknown_skill_has_no_graph():
    with pytest.raises(SkillGraphError):
        load_graph("no-such-skill")


def test_every_call_in_a_shipped_graph_names_a_tool():
    """A graph that names a tool the registry does not hold would reintroduce the
    invented-tool-name defect on a surface the agent cannot argue with."""
    graph = load_graph("adverse-event-detection")
    for step in graph["steps"]:
        for call in step.get("calls", []):
            assert call.get("tool"), step


def _registry_tool_names() -> set[str]:
    import glob
    import json
    names: set[str] = set()
    root = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
    for path in glob.glob(str(root / "*.json")):
        try:
            with open(path) as handle:
                loaded = json.load(handle)
        except (ValueError, OSError):
            continue
        if isinstance(loaded, list):
            names.update(t["name"] for t in loaded
                         if isinstance(t, dict) and "name" in t)
    return names


@pytest.mark.parametrize("skill", [p.stem for p in
                                   (Path(__file__).resolve().parents[2] / "src" / "tooluniverse"
                                    / "data" / "skill_graphs").glob("*.yaml")])
def test_every_shipped_graph_calls_only_registered_tools(skill):
    """The whole point of moving the plan into data is that the agent stops
    guessing tool names. A graph that guesses one is worse than the prose, because
    the agent is told to trust it."""
    registry = _registry_tool_names()
    assert registry, "no tools found in the registry"
    graph = load_graph(skill)
    unknown = sorted({call["tool"] for step in graph["steps"]
                      for call in step.get("calls", [])
                      if call["tool"] not in registry})
    assert not unknown, f"{skill} names tools the registry does not hold: {unknown}"


def test_every_step_of_a_shipped_graph_is_reachable():
    """A step whose dependency is never satisfiable is dead procedure — it would
    silently drop a phase, which is the defect this design exists to remove."""
    graph = load_graph("adverse-event-detection")
    ids = {s["id"] for s in graph["steps"]}
    for step in graph["steps"]:
        missing = [d for d in step.get("requires", []) if d not in ids]
        assert not missing, f"{step['id']} requires unknown steps: {missing}"
