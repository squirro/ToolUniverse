"""A check on a judged value sees the lists its own step extracted.

A step that extracts a list and asks the agent to choose from it checks the choice
against that list, not against the facts held before the step.
"""

import pytest

from tooluniverse.skill_runner import SkillRunner

pytestmark = pytest.mark.unit


PROCESS = {
    "skill": "comparator", "inputs": ["class_id"],
    "steps": [
        {"id": "choose", "calls": [{"tool": "RxClass_get_class_members",
                                    "arguments": {"class_id": "{class_id}"}}],
         "extract": {"class_members": "data[].name"},
         "judge": ["comparator"],
         "check": {"comparator": [{"only_in": "class_members"}]},
         "produces": ["class_members", "comparator"]},
    ],
}
MEMBERS = {"data": [{"name": "cisplatin"}, {"name": "carboplatin"}, {"name": "oxaliplatin"}]}


def _run(*answers):
    asked, queue = [], list(answers)
    runner = SkillRunner(PROCESS, execute=lambda tool, args: MEMBERS,
                         ask=lambda q: asked.append(q) or {"comparator": queue[min(len(asked), len(queue)) - 1]})
    run_id = runner.start({"class_id": "L01XA"})["run_id"]
    out = runner.advance(run_id)
    return out, asked


def test_a_choice_from_the_list_the_same_step_extracted_is_kept():
    out, asked = _run("carboplatin")

    assert out["blocked"] == [], out["blocked"]
    assert out["extracted"]["comparator"] == "carboplatin"
    assert len(asked) == 1, "a correct choice is not asked again"


def test_a_choice_off_the_list_the_same_step_extracted_is_still_refused():
    out, asked = _run("aspirin", "aspirin")

    assert "aspirin" in asked[1]["problem"] and "class_members" in asked[1]["problem"]
    assert "comparator" not in out["extracted"]
    assert {"step": "choose", "fact": "comparator"} in out["unresolved"]
