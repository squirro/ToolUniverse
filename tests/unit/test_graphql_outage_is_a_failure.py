"""An OpenTargets outage must read as a failure, not as a disease with no targets.

Four different failures — a 5xx, GraphQL errors, a body with no data key and a body that
is not JSON — all collapsed to "No data returned from API", which nothing recognises as
an upstream failure. A server that is down was reported to the agent as an answer, and
the id resolver blamed the agent's own input for it.

A source that genuinely holds nothing must still read as an empty answer, because the
brand-name fallback depends on it.
"""

import pytest
import requests

import tooluniverse.graphql_tool as mod
from tooluniverse.graphql_tool import execute_query
from tooluniverse.skill_runner import is_upstream_failure

pytestmark = pytest.mark.unit

ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"


class _Response:
    def __init__(self, ok, payload, status_code=200, decodes=True):
        self.ok = ok
        self.status_code = status_code
        self.text = "upstream is unavailable"
        self._payload = payload
        self._decodes = decodes

    def json(self):
        if not self._decodes:
            raise requests.exceptions.JSONDecodeError("no json", "", 0)
        return self._payload


@pytest.mark.parametrize("response", [
    _Response(ok=False, payload={}, status_code=503),
    _Response(ok=False, payload={}, status_code=500),
    _Response(ok=True, payload={"errors": [{"message": "Cannot query field"}]}),
    _Response(ok=True, payload={}, decodes=False),
])
def test_a_source_failure_is_reported_as_an_upstream_failure(monkeypatch, response):
    monkeypatch.setattr(mod.requests, "post", lambda *a, **k: response)

    assert is_upstream_failure(execute_query(ENDPOINT, "{ x }")), "failure not recognised"


def test_a_transport_error_is_reported_rather_than_raised(monkeypatch):
    def post(*a, **k):
        raise requests.exceptions.ConnectTimeout("timed out")

    monkeypatch.setattr(mod.requests, "post", post)

    assert is_upstream_failure(execute_query(ENDPOINT, "{ x }"))


def test_a_source_that_holds_nothing_is_still_an_empty_answer(monkeypatch):
    """The brand-name fallback reads this, so it must not become a failure."""
    monkeypatch.setattr(mod.requests, "post",
                        lambda *a, **k: _Response(ok=True, payload={"nothing": {}}))

    assert execute_query(ENDPOINT, "{ x }") is None


def test_an_outage_does_not_tell_the_agent_to_fix_its_own_input(monkeypatch):
    monkeypatch.setattr(mod.requests, "post",
                        lambda *a, **k: _Response(ok=False, payload={}, status_code=503))

    assert mod._ot_resolve_id(ENDPOINT, "EGFR", "target") is None
