"""Pharos is served, and its answers mean what the tool says they mean.

The image excluded all four Pharos tools after two readings of 502. Probed again from
sr-dev on 2026-09-24 they answer; what remains is a slow cold query. The Pharos gateway
gives up at about 60 s with a 504 while the backend finishes and caches the result, so a
single retry answers in about a second.
"""

import sys
from pathlib import Path

import pytest
import requests

import tooluniverse.pharos_tool as mod
from tooluniverse.pharos_tool import PharosTool

pytestmark = pytest.mark.unit

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))

import persona_lint  # noqa: E402

PHAROS_TOOLS = {
    "Pharos_get_target", "Pharos_search_targets",
    "Pharos_get_tdl_summary", "Pharos_get_disease_targets",
}


def test_the_image_serves_every_pharos_tool():
    excluded = persona_lint.excluded_tool_names((DEPLOY / "Dockerfile").read_text())
    assert PHAROS_TOOLS & excluded == set()


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Server Error")

    def json(self):
        return self._payload


TARGETS = {"data": {"targets": {"count": 11, "targets": [{"sym": "SSTR2"}]}}}


def _tool(operation):
    return PharosTool({"name": "x", "fields": {"operation": operation}})


def _record(monkeypatch, responses):
    sent = []

    def post(url, json=None, **kwargs):
        sent.append(json)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(mod.requests, "post", post)
    return sent


@pytest.mark.parametrize("first", [
    _Response(504),
    requests.exceptions.ReadTimeout("read timed out"),
])
def test_a_cold_query_the_gateway_gave_up_on_is_asked_once_more(monkeypatch, first):
    sent = _record(monkeypatch, [first, _Response(200, TARGETS)])

    result = _tool("search_targets").run({"query": "somatostatin receptor"})

    assert result["status"] == "success", result
    assert len(sent) == 2


def test_a_second_gateway_timeout_is_reported_as_a_failure(monkeypatch):
    sent = _record(monkeypatch, [_Response(504), _Response(504)])

    result = _tool("search_targets").run({"query": "somatostatin receptor"})

    assert result["status"] == "error"
    assert "504" in result["error"]
    assert len(sent) == 2


def test_a_query_error_is_not_retried(monkeypatch):
    sent = _record(monkeypatch, [_Response(400)])

    result = _tool("get_target").run({"gene": "EGFR"})

    assert result["status"] == "error"
    assert len(sent) == 1


@pytest.mark.parametrize("operation,arguments", [
    ("search_targets", {"query": "somatostatin receptor", "top": 3}),
    ("get_disease_targets", {"disease": "breast cancer", "top": 3}),
])
def test_top_limits_the_rows_returned(monkeypatch, operation, arguments):
    # Pharos ignores `top` on the outer targets() field and always answers 10 rows.
    sent = _record(monkeypatch, [_Response(200, TARGETS)])

    _tool(operation).run(arguments)

    query = " ".join(sent[0]["query"].split())
    assert "targets(top: $top)" in query
    assert sent[0]["variables"]["top"] == 3


@pytest.mark.parametrize("operation,arguments", [
    ("search_targets", {"query": "somatostatin receptor", "tdl": "Tdark"}),
    ("get_disease_targets", {"disease": "breast cancer", "tdl": "Tdark"}),
])
def test_tdl_filters_by_development_level(monkeypatch, operation, arguments):
    sent = _record(monkeypatch, [_Response(200, TARGETS)])

    _tool(operation).run(arguments)

    assert sent[0]["variables"]["facets"] == [
        {"facet": "Target Development Level", "values": ["Tdark"]}
    ]
    assert "facets: $facets" in " ".join(sent[0]["query"].split())
