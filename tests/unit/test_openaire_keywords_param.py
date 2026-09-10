"""OpenAIRE has no `query` parameter, and the 400 was being swallowed.

`OpenAIRE_search_publications` sent `query=...`, which the legacy search API
rejects outright, and then returned the failure INSIDE a success envelope:

    {"status": "success",
     "data": {"status": "error", "error": "Network/API error calling OpenAIRE",
              "reason": "400 Client Error: Bad Request for url: ..."}}

so the audit read it as `ok_empty` and nothing ever surfaced as broken. Measured
against `https://api.openaire.eu/search/publications` on 2026-08-03:

    query=machine+learning    -> 400
    keywords=machine+learning -> 200, 1,161,515 results
    title=machine+learning    -> 200,   496,236 results

`keywords` is the general-purpose field and the one a "search publications" tool
wants; `title` would silently narrow every search to title matches only.

The outer `"status": "success"` around an inner error is left alone here: it is
one tool's habit rather than a pattern, and the audit's classifier deliberately
judges emptiness on the payload, so hiding this behind a classifier rule would
have masked the parameter bug instead of fixing it.
"""

import pytest

import tooluniverse.openaire_tool as mod
from tooluniverse.openaire_tool import OpenAIRETool

CONFIG = {"name": "OpenAIRE_search_publications", "parameter": {"properties": {}}}


@pytest.fixture
def captured(monkeypatch):
    """Record the request OpenAIRE would actually receive."""
    seen = {}

    class _Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"response": {"header": {"total": {"$": 0}}, "results": None}}

    def _fake_get(url, params=None, timeout=None, **kwargs):
        seen["url"] = url
        seen["params"] = params or {}
        return _Response()

    monkeypatch.setattr(mod.requests, "get", _fake_get)
    return seen


@pytest.mark.unit
def test_the_search_term_is_sent_as_keywords(captured):
    OpenAIRETool(CONFIG).run({"query": "machine learning"})

    assert "query" not in captured["params"], (
        "OpenAIRE answers 400 to `query`; the failure was then wrapped in a "
        "success envelope and read as an empty result"
    )
    assert captured["params"].get("keywords") == "machine learning", captured["params"]


@pytest.mark.unit
def test_it_is_keywords_and_not_title(captured):
    """`title` also returns 200, and would narrow every search silently."""
    OpenAIRETool(CONFIG).run({"query": "GLP-1 receptor agonist"})

    assert "title" not in captured["params"], captured["params"]


@pytest.mark.network
def test_the_real_search_returns_publications():
    """The claim the unit tests cannot make: this query returns results."""
    result = OpenAIRETool(CONFIG).run({"query": "machine learning",
                                            "max_results": 2})

    assert result["status"] == "success", result
    payload = result["data"]
    assert payload.get("status") != "error", payload
    assert payload.get("total_results", 0) > 0, payload
    assert payload.get("results"), payload
