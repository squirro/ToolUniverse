"""Runner logic that must hold without a live cluster: resume, ordering, diff.

The network path is not tested here — it is `SquirroChatClient`, which has its
own tests. What matters at this seam is that a 76-skill sweep can be interrupted
and resumed, that the report puts the worst skills where a human will read them,
and that two runs can be compared so an upstream merge cannot silently break a
skill the way it used to silently break a tool.
"""

import json
import sys
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))

from skill_audit.sweep import (
    diff_runs,
    render_report,
    rescore_trace,
    rows_to_run,
    trim_actions,
)

CORPUS = [
    {"skill": "disease-research", "tier": 2, "question": "q1"},
    {"skill": "toxicology", "tier": 1, "question": "q2"},
    {"skill": "infectious-disease", "tier": 2, "question": "q3"},
]

pytestmark = pytest.mark.unit


def _result(skill, verdict, codes=(), warns=0):
    return {"skill": skill, "verdict": verdict,
            "findings": [{"code": c, "severity": "fail", "message": "",
                          "evidence": {}} for c in codes],
            "n_warn": warns, "calls": [], "answer_len": 10}


# --- resume ----------------------------------------------------------------

def test_a_sweep_resumes_by_skipping_the_skills_already_done():
    todo = rows_to_run(CORPUS, done={"toxicology"})
    assert [r["skill"] for r in todo] == ["disease-research", "infectious-disease"]


def test_a_skill_whose_only_result_was_a_retry_is_run_again():
    """A provider refusal is not an answer, so resume must not treat it as done."""
    todo = rows_to_run(CORPUS, done={"toxicology"}, retryable={"toxicology"})
    assert "toxicology" in [r["skill"] for r in todo]


def test_the_report_shows_one_row_per_skill_when_a_skill_was_re_run():
    """Resume appends, so the same skill can appear twice in results.jsonl —
    the report must show its latest verdict, not both."""
    report = render_report([_result("a", "fail", codes=["no_skill_loaded"]),
                            _result("a", "pass")])
    assert report.count("| a ") == 1
    assert "no_skill_loaded" not in report


def test_only_filters_to_named_skills():
    todo = rows_to_run(CORPUS, done=set(), only=["toxicology"])
    assert [r["skill"] for r in todo] == ["toxicology"]


def test_tier_filters_to_one_tier():
    todo = rows_to_run(CORPUS, done=set(), tier=1)
    assert [r["skill"] for r in todo] == ["toxicology"]


# --- report ----------------------------------------------------------------

def test_the_report_lists_failures_before_warnings_before_passes():
    report = render_report([
        _result("a", "pass"),
        _result("b", "warn", warns=2),
        _result("c", "fail", codes=["no_skill_loaded"]),
    ])
    assert report.index("| c ") < report.index("| b ") < report.index("| a ")


def test_the_report_ranks_warned_skills_by_how_many_warnings_they_carry():
    report = render_report([
        _result("light", "warn", warns=1),
        _result("heavy", "warn", warns=4),
    ])
    assert report.index("| heavy ") < report.index("| light ")


def test_the_report_names_the_failure_codes_so_the_summary_is_actionable():
    report = render_report([_result("c", "fail", codes=["skill_without_tools"])])
    assert "skill_without_tools" in report


# --- diff ------------------------------------------------------------------

def test_a_skill_that_passed_before_and_fails_now_is_a_regression():
    old = [_result("a", "pass"), _result("b", "fail", codes=["x"])]
    new = [_result("a", "fail", codes=["no_skill_loaded"]),
           _result("b", "fail", codes=["x"])]
    delta = diff_runs(old, new)
    assert delta["regressed"] == ["a"]
    assert delta["fixed"] == []


def test_a_skill_that_failed_before_and_passes_now_is_a_fix():
    delta = diff_runs([_result("a", "fail", codes=["x"])], [_result("a", "pass")])
    assert delta["fixed"] == ["a"]


def test_a_run_loads_from_a_directory_or_from_a_bare_results_file(tmp_path):
    """The recorded baseline is committed as one .jsonl; a fresh run is a
    directory. diff has to compare the two, so it must read either."""
    from skill_audit.sweep import load_run
    row = json.dumps(_result("a", "pass"))
    bare = tmp_path / "baseline.jsonl"
    bare.write_text(row + "\n")
    as_dir = tmp_path / "run"
    as_dir.mkdir()
    (as_dir / "results.jsonl").write_text(row + "\n")
    assert load_run(bare) == load_run(as_dir)


def test_a_skill_missing_from_the_new_run_is_reported_not_ignored():
    delta = diff_runs([_result("a", "pass")], [])
    assert delta["absent"] == ["a"]


# --- the trace must survive the run, so a scorer fix costs no cluster time ---

def test_the_saved_trace_keeps_what_the_oracle_reads():
    """Tool name, status and output text — everything score() looks at."""
    actions = [{"tool_name": "execute_tool", "status": "finished",
                "content": {"parameters": {"tool_name": "UniProt_search"},
                            "output": '{"results": []}'}}]
    kept = trim_actions(actions)
    assert kept[0]["tool_name"] == "execute_tool"
    assert kept[0]["content"]["parameters"]["tool_name"] == "UniProt_search"
    assert kept[0]["content"]["output"] == '{"results": []}'


def test_a_huge_tool_output_is_truncated_so_the_trace_file_stays_readable():
    actions = [{"tool_name": "execute_tool", "status": "finished",
                "content": {"parameters": {}, "output": "x" * 50_000}}]
    kept = trim_actions(actions)
    assert len(kept[0]["content"]["output"]) < 10_000


def test_rescoring_a_saved_trace_reproduces_a_verdict_without_the_cluster(tmp_path):
    trace = {"skill": "toxicology", "actions": [], "answer": "", "error": None}
    (tmp_path / "toxicology.json").write_text(json.dumps(trace))
    result = rescore_trace(tmp_path / "toxicology.json", body=None)
    assert result["skill"] == "toxicology"
    assert result["verdict"] == "fail"
    assert "no_skill_loaded" in [f["code"] for f in result["findings"]]
