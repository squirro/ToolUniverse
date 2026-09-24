"""rare-disease-diagnosis driven whole against recorded responses, once with the variant
bound and once with the patient's age bound.

The case is a child with splenomegaly, thrombocytopenia and bone pain. Every tool call is
answered from its recording, keyed by the exact arguments; a call that was not recorded
fails the test. The agent's judgements are answered by a stub that reads them from the
question, as the agent would.
"""
import json
from pathlib import Path

import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner

pytestmark = pytest.mark.unit

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "skill_processes" / "rare_disease"
SYMPTOMS = ["splenomegaly", "thrombocytopenia", "bone pain"]
VARIANT = "1-155235843-T-C"


def _recorded(tool, arguments):
    rows = json.loads((RECORDED / f"{tool}_2026-09-24.json").read_text())
    return rows[json.dumps(arguments, sort_keys=True)]


def _agent(question):
    answers = {
        "primary_keyword": "Gaucher disease",
        "working_hypothesis": "a lysosomal storage disease",
        "discriminating_features": ["splenomegaly", "bone pain"],
        # splenomegaly and thrombocytopenia both sit at the tool's ceiling of 500
        "discriminating_hpo_ids": ["HP:0002653", "HP:0001744"],
        "top_candidate": "Gaucher disease",
        "optimuskg_genes": [],
    }
    return {name: answers[name] for name in question["wants"] if name in answers}


def _drive(**optional):
    calls = []

    def execute(tool, arguments):
        calls.append((tool, arguments))
        return _recorded(tool, arguments)

    runner = SkillRunner(load_graph("rare-disease-diagnosis"), execute=execute, ask=_agent)
    run_id = runner.start({"symptoms": SYMPTOMS, **optional})["run_id"]
    for _ in range(200):
        if runner.advance(run_id)["finished"]:
            break
    else:
        raise AssertionError("the run did not finish")
    return runner.handover(run_id), calls


def test_with_the_variant_bound_the_variant_step_runs_on_it():
    handed, calls = _drive(variant_id=VARIANT)

    assert [a for tool, a in calls if tool == "gnomad_get_variant"] == [
        {"variant_id": VARIANT, "dataset": "gnomad_r4"}]
    assert "variant" in handed["steps_done"]
    assert "variant" not in {s["step"] for s in handed["steps_skipped"]}
    assert handed["failures"] == [] and handed["blocked"] == [] and "stalled" not in handed


def test_without_a_variant_the_step_is_skipped_as_never_decided():
    handed, calls = _drive()

    assert [a for tool, a in calls if tool == "gnomad_get_variant"] == []
    assert {"step": "variant", "gate": "variant_id", "decided": False} in handed["steps_skipped"]


def test_with_the_age_bound_the_differential_is_ranked_on_onset_fit():
    handed, _ = _drive(age_years=4)

    ranked = handed["facts"]["ranked_rows"]
    assert [(r["preferred_term"], r["onset_fit"], r["rank"]) for r in ranked] == [
        ("Hypocalcemic vitamin D-dependent rickets", "fits", 1),
        ("Majeed syndrome", "fits", 2)]
    assert {r["carries_discriminating"] for r in ranked} == {"both"}
    assert "rank_differential" in handed["steps_done"]
    assert handed["failures"] == [] and handed["blocked"] == [] and "stalled" not in handed


def test_without_an_age_onset_is_not_assessed():
    handed, _ = _drive()

    assert {r["onset_fit"] for r in handed["facts"]["ranked_rows"]} == {"not assessed (no patient age)"}
