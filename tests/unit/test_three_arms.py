"""The four-arm driver was written for one question and one skill. Rung 2
measures a second process, so the arm prompts must name whichever skill is
under test — and only in the two arms that load a skill."""

import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))

from skill_audit.three_arms import ARM_NAMES, arms_for  # noqa: E402


def test_the_arm_prompts_name_the_skill_under_test():
    arms = arms_for("rare-disease-diagnosis")
    assert tuple(arms) == ARM_NAMES
    assert 'get_skill(name="rare-disease-diagnosis", plain=true)' in arms["prose"]
    assert arms["modelled"] == "Use the rare-disease-diagnosis skill. "


def test_the_bare_and_web_arms_never_hear_the_skill_name():
    arms = arms_for("rare-disease-diagnosis")
    assert "rare-disease" not in arms["bare"]
    assert arms["web"] == ""


def test_the_default_skill_is_the_rung_one_process():
    assert "clinical-data-integration" in arms_for("clinical-data-integration")["prose"]
