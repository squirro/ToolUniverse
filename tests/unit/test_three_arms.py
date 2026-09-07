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


def test_the_four_arm_score_reports_uncited_numbers_from_the_full_bundle(tmp_path):
    """The four-arm driver scores PRR values; it now also counts the numbers the
    bundle cannot vouch for, reading a .bundle.json sidecar when the trace's own
    bundle was capped."""
    import json
    from skill_audit.three_arms import score
    actions = [{"tool_name": "run_skill", "content": {"parameters": {}, "output": '{"status": "running"}'}},
               {"tool_name": "continue_skill", "content": {"parameters": {},
                "output": '{"status": "finished", "run_id": "r1", "bundle": {"facts": {"prrs": [3.9]}}, "calls": {"x": ["t"]}}'}}]
    sidecar = tmp_path / "modelled-r1.bundle.json"
    sidecar.write_text(json.dumps({"facts": {"prrs": [3.9, 21.4]}, "calls": {"x": ["t"]}}))

    row = score(actions, "PRR 3.9 and PRR 21.4, and a ROR of 10.861.", bundle_path=sidecar)

    assert row["uncited_numbers"] == ["10.861"]           # 21.4 is in the sidecar, not the trace
    assert row["uncited_count"] == 1


def test_without_a_sidecar_the_trace_bundle_is_used():
    from skill_audit.three_arms import score
    actions = [{"tool_name": "continue_skill", "content": {"parameters": {},
                "output": '{"status": "finished", "run_id": "r1", "bundle": {"facts": {"prrs": [3.9]}}, "calls": {}}'}}]

    row = score(actions, "PRR 3.9 and PRR 21.4.")

    assert row["uncited_numbers"] == ["21.4"]
