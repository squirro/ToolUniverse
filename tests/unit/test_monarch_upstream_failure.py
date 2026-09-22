"""A failure of an upstream service must not look like an answer (DSR-771).

Recorded 2026-09-18 in rare-disease-diagnosis: Monarch answered a server error, the REST
wrapper turned it into `False`, the tool indexed it, and the wrapper's TypeError became a
`status: error` result the run counted as an answer -- zero failed calls, two facts never
produced, seven steps blocked with a reason that named only the missing list.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import tooluniverse.restful_tool as mod
from tooluniverse.restful_tool import MonarchDiseasesForMultiplePhenoTool
from tooluniverse.skill_runner import SkillRunner, is_upstream_failure

pytestmark = pytest.mark.unit

CONFIG = next(t for t in json.loads((Path(mod.__file__).parent / "data" / "monarch_tools.json").read_text())
              if t["name"] == "get_joint_associated_diseases_by_HPO_ID_list")


def _response(status, payload=None, text=""):
    resp = MagicMock()
    resp.status_code, resp.text, resp.headers = status, text, {}
    if payload is None:
        resp.json.side_effect = ValueError("not JSON")
    else:
        resp.json.return_value = payload
    return resp


@pytest.fixture
def session(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr(mod, "_SESSION", fake)
    monkeypatch.setattr(mod, "BACKOFF_SECONDS", 0)
    return fake


# --- the tool ------------------------------------------------------------------------------

def test_a_server_error_is_retried_and_then_reported_with_the_upstream_status(session):
    session.request.return_value = _response(502, text="<html>Bad Gateway</html>")

    out = MonarchDiseasesForMultiplePhenoTool(CONFIG).run({"HPO_ID_list": ["HP:0001263", "HP:0001250"]})

    assert out["status"] == "error" and out["upstream_status"] == 502
    assert "502" in out["error"] and out["retryable"] is True
    assert session.request.call_count == 3, "three attempts for the first id, then the call fails whole"


def test_a_good_answer_still_gives_the_intersection_of_disease_names(session):
    session.request.side_effect = [
        _response(200, {"items": [{"subject_label": "Hurler"}, {"subject_label": "Other"}]}),
        _response(200, {"items": [{"subject_label": "Hurler"}]}),
    ]

    assert MonarchDiseasesForMultiplePhenoTool(CONFIG).run({"HPO_ID_list": ["HP:1", "HP:2"]}) == ["Hurler"]


def test_a_body_that_is_not_json_is_an_error_with_the_status_not_false(session):
    session.request.return_value = _response(200, text="<html>maintenance</html>")

    out = mod.execute_RESTful_query("https://api.monarchinitiative.org/v3/api/association", {"q": "x"})

    assert out["status"] == "error" and out["upstream_status"] == 200 and "JSON" in out["error"]


# --- the run -------------------------------------------------------------------------------

PROCESS = {
    "skill": "demo", "inputs": ["hpo_ids"],
    "steps": [
        {"id": "differential", "calls": [{"tool": "monarch", "arguments": {"ids": "{hpo_ids}"}}],
         "extract": {"candidates": {"path": "result"}}, "produces": ["candidates"]},
        {"id": "resolve", "requires": ["differential"], "for_each": "candidates", "as": "name",
         "calls": [{"tool": "orphanet", "arguments": {"query": "{name}"}}]},
    ],
}
UPSTREAM = {"status": "error", "error": "Monarch answered HTTP 502 (Bad Gateway)", "upstream_status": 502,
            "retryable": True, "error_details": {"type": "ToolServerError", "retriable": True}}
NOT_FOUND = {"status": "error", "error": {"code": "NOT_FOUND", "message": "No matches found"}}


def _drive(answer):
    runner = SkillRunner(PROCESS, execute=lambda tool, a: answer if tool == "monarch" else {"data": {}})
    run_id = runner.start({"hpo_ids": ["HP:0001263"]})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass
    return runner.handover(run_id)


def test_an_upstream_failure_is_a_failed_call_and_the_blocked_step_names_it():
    handed = _drive(UPSTREAM)

    (failure,) = handed["failures"]
    assert failure["tool"] == "monarch" and failure["step"] == "differential" and "502" in failure["error"]
    assert handed["unresolved"] == [{"step": "differential", "fact": "candidates"}]
    (blocked,) = handed["blocked"]
    assert blocked["step"] == "resolve"
    assert "missing candidates" in blocked["reason"] and "monarch" in blocked["reason"] and "502" in blocked["reason"]


def test_a_source_that_answers_nothing_here_is_still_not_a_failure():
    handed = _drive(NOT_FOUND)

    assert handed["failures"] == []
    assert handed["unresolved"] == [{"step": "differential", "fact": "candidates"}]


def test_what_counts_as_an_upstream_failure():
    assert is_upstream_failure(UPSTREAM)
    assert is_upstream_failure({"status": "error", "error": "x", "error_details": {"type": "ToolServerError"}})
    assert is_upstream_failure({"status": "error", "error": "x", "upstream_status": 503})
    # ChEMBL's envelope as recorded: no type, no code, the timeout only in the text
    assert is_upstream_failure({
        "status": "error", "url": "https://www.ebi.ac.uk/chembl/api/data/target.json",
        "error": "ChEMBL API request failed: HTTPSConnectionPool(host='www.ebi.ac.uk', port=443): Read timed out. (read timeout=30)",
        "detail": "ReadTimeout(ReadTimeoutError(\"...Read timed out.\"))"})
    # a tool the deployment does not serve: the call was never made, so it is a failed call
    assert is_upstream_failure({"status": "error", "error": "Tool 'Pharos_get_target' not found even after loading tools",
                                "error_details": {"type": "ToolUnavailableError", "retriable": False}})
    assert not is_upstream_failure(NOT_FOUND)
    assert not is_upstream_failure({"status": "success", "data": []})
    assert not is_upstream_failure(["a", "list"])
