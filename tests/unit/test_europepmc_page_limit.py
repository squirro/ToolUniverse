"""Europe PMC serves at most 1,000 results per request; a larger `limit` must page, not vanish.

An oversized page size answers HTTP 200 with an error body and no result list, which the tool
read as "success, no articles", so asking for the source's width gave "no literature found",
stated as a fact.
"""

import json
from pathlib import Path

import pytest

import tooluniverse.europe_pmc_tool as mod
from tooluniverse.europe_pmc_tool import EuropePMCTool

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "europepmc"
PAGE = json.loads((FIXTURES / "search_cancer_pageSize1000_2026-09-21.json").read_text())
TOO_WIDE = json.loads((FIXTURES / "search_cancer_pageSize2000_2026-09-21.json").read_text())
CONFIG = next(t for t in json.loads((Path(mod.__file__).parent / "data" / "europe_pmc_tools.json").read_text())
              if t["name"] == "EuropePMC_search_articles")


class _Response:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.reason = payload, status, "OK"

    def json(self):
        return self._payload


def _pages(monkeypatch, answers):
    """Europe PMC as recorded: each request gets the next answer; the requests are kept."""
    sent = []
    queue = list(answers)

    def request_with_retry(session, method, url, *, params, **kwargs):
        sent.append(dict(params))
        return _Response(queue.pop(0) if queue else {"resultList": {"result": []}})

    monkeypatch.setattr(mod, "request_with_retry", request_with_retry)
    return sent


def test_a_limit_above_the_sources_page_pages_with_the_cursor_and_never_asks_for_more_than_1000(monkeypatch):
    last = {**PAGE, "nextCursorMark": None}
    sent = _pages(monkeypatch, [PAGE, PAGE, last, last])      # core + lite per page, two pages

    out = EuropePMCTool(CONFIG).run({"query": "cancer", "limit": 2000})

    assert out["status"] == "success"
    assert len(out["data"]) == 6, "three recorded articles per page, two pages"
    assert {p["pageSize"] for p in sent} == {1000}
    assert [p.get("cursorMark", "*") for p in sent if p["resultType"] == "core"] == ["*", PAGE["nextCursorMark"]]
    assert out["metadata"]["total"] == PAGE["hitCount"] == 5601522


def test_a_page_size_error_in_a_200_body_is_reported_as_an_error_not_an_empty_success(monkeypatch):
    _pages(monkeypatch, [TOO_WIDE, TOO_WIDE])

    out = EuropePMCTool(CONFIG).run({"query": "cancer", "limit": 500})

    assert out["status"] == "error"
    assert "Valid size is between 1 and 1000" in out["error"]
    assert out.get("data") in (None, [])


def test_a_limit_within_one_page_makes_one_request_of_that_size(monkeypatch):
    sent = _pages(monkeypatch, [PAGE, PAGE])

    out = EuropePMCTool(CONFIG).run({"query": "cancer", "limit": 3})

    assert [p["pageSize"] for p in sent] == [3, 3]
    assert len(out["data"]) == 3 and out["metadata"]["total"] == 5601522


def test_the_schema_states_the_true_maximum_per_request():
    assert "1000" in CONFIG["parameter"]["properties"]["limit"]["description"]
