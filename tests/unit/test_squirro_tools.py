"""Direct calls to Squirro tools in a Replay (SA-06a, ADR-0021 amended).

A call named `squirro:<project>:<agent>:<tool_id>` is made through genai's /tools/execute with
the options of the agent the analysis was saved from, read at run time. These tests sit at the
HTTP boundary with a mocked cluster.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.squirro_tools import (  # noqa: E402
    SquirroToolError,
    SquirroTools,
    call_name,
    routed,
)

pytestmark = pytest.mark.unit

CLUSTER = "https://sr-dev.squirro.test"
TOOL = "genai_plugin.clinicaltrials_search_tool.clinicaltrials_search_tool.clinicaltrials_search"
NAME = call_name("proj1", "agentA", TOOL)
AGENT = {"toolkit": {"tools": [
    {"tool_id": TOOL, "custom_name": "Clinical_Trials_Search", "options": {"max_studies": 50}},
]}}


def _cluster(requests_mock, execute=None):
    token = requests_mock.post(f"{CLUSTER}/api/user/oauth2/token",
                               json={"access_token": "AT", "expires_in": 3600})
    agent = requests_mock.get(f"{CLUSTER}/service/genai/v0/projects/proj1/agents/agentA",
                              json=AGENT)
    run = requests_mock.post(f"{CLUSTER}/service/genai/v0/tools/execute",
                             json=execute or {"success": True, "result": '{"studies": []}',
                                              "error": None})
    return token, agent, run


def _tools():
    return SquirroTools(cluster=CLUSTER, refresh_token="RT")


def test_the_call_name_carries_the_agent_it_was_saved_from():
    assert NAME == f"squirro:proj1:agentA:{TOOL}"


def test_a_direct_call_runs_the_tool_with_the_agents_options(requests_mock):
    token, _, run = _cluster(requests_mock)

    out = _tools().execute(NAME, {"action": "search", "intervention": "AR-V7"})

    assert out == '{"studies": []}'
    assert run.last_request.json() == {
        "tool_id": TOOL, "tool_options": {"max_studies": 50},
        "inputs": {"action": "search", "intervention": "AR-V7"}}
    assert run.last_request.headers["Authorization"] == "Bearer AT"
    assert token.last_request.text == "grant_type=refresh_token&refresh_token=RT"


def test_the_token_and_the_agent_are_read_once_for_many_calls(requests_mock):
    token, agent, run = _cluster(requests_mock)
    tools = _tools()

    for n in range(3):
        tools.execute(NAME, {"nct_id": f"NCT0{n}"})

    assert token.call_count == 1 and agent.call_count == 1 and run.call_count == 3


def test_a_tool_that_fails_raises_its_own_error(requests_mock):
    _cluster(requests_mock, execute={"success": False, "result": None,
                                     "error": "2 validation errors: epo_ops_key Field required"})

    with pytest.raises(SquirroToolError, match="epo_ops_key"):
        _tools().execute(NAME, {})


def test_a_tool_the_agent_no_longer_has_is_an_error_that_says_so(requests_mock):
    _cluster(requests_mock)

    with pytest.raises(SquirroToolError, match="no longer has"):
        _tools().execute(call_name("proj1", "agentA", "genai_plugin.gone.gone.gone"), {})


@pytest.mark.parametrize("bad", ["squirro:only-two:parts", "squirro::agentA:tool", "UniProt_search"])
def test_a_name_that_is_not_a_direct_call_is_refused(bad):
    with pytest.raises(SquirroToolError):
        _tools().execute(bad, {})


def test_routed_sends_direct_calls_to_squirro_and_the_rest_to_toolunivers(requests_mock):
    _cluster(requests_mock)
    seen = []
    dispatch = routed(lambda call: seen.append(call) or {"ok": True}, _tools())

    assert dispatch({"name": NAME, "arguments": {"x": 1}}) == '{"studies": []}'
    assert dispatch({"name": "UniProt_search", "arguments": {"query": "KRAS"}}) == {"ok": True}
    assert seen == [{"name": "UniProt_search", "arguments": {"query": "KRAS"}}]


def test_without_a_token_direct_calls_fail_with_a_reason_and_toolunivers_still_works():
    dispatch = routed(lambda call: "tu", None)

    assert dispatch({"name": "UniProt_search", "arguments": {}}) == "tu"
    with pytest.raises(SquirroToolError, match="SQUIRRO_REPLAY_TOKEN"):
        dispatch({"name": NAME, "arguments": {}})


def test_every_request_asks_for_json_since_the_token_endpoint_defaults_to_xml(requests_mock):
    token, agent, run = _cluster(requests_mock)

    _tools().execute(NAME, {})

    for route in (token, agent, run):
        assert route.last_request.headers["Accept"] == "application/json"
