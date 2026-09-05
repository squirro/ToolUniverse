"""LOVD gates its search routes behind a cookie, and says so in HTML with a 200.

`/variants/{gene}` with search parameters answers a "Checking your browser..."
page -- **HTTP 200, text/html** -- to a client holding no cookie. The wrapper
then called `.json()` on that page and surfaced

    LOVD API request failed: Expecting value: line 1 column 1 (char 0)

which names the JSON parser and says nothing about the bot check, so the tool
read as an upstream/parsing fault for as long as it was measured:

    no cookie                          -> 200, text/html, "Checking your browser..."
    cookies={"lovd_cookie_check":"OK"} -> 200, application/json, the variant

Verified live 2026-08-03. Two things were ruled out along the way: the literal
`/` in the parameter name `search_Variant/DBID` is *not* the fault (percent-
encoded and literal forms fail identically), and neither is the User-Agent.
`/genes/{gene}` was never affected, which is why only the search tool failed.
"""

import pytest
import requests

import tooluniverse.lovd_tool as mod
from tooluniverse.lovd_tool import LOVDTool

BOT_CHECK_PAGE = (
    '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">\n'
    "<html><head><title>Checking your browser...</title></head><body></body></html>"
)


def _config(operation):
    return {
        "name": f"LOVD_{operation}",
        "parameter": {"properties": {}},
        "fields": {"operation": operation},
    }


class _Response:
    """Stands in for what LOVD returns, JSON or otherwise."""

    def __init__(self, payload, *, is_json=True, status_code=200):
        self._payload = payload
        self._is_json = is_json
        self.status_code = status_code
        self.headers = {
            "content-type": "application/json" if is_json else "text/html; charset=UTF-8"
        }
        self.text = "" if is_json else payload

    def raise_for_status(self):
        pass

    def json(self):
        if not self._is_json:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload


@pytest.fixture
def captured(monkeypatch):
    """Record what LOVD would actually receive."""
    seen = {}

    def _fake_get(url, params=None, cookies=None, timeout=None, **kwargs):
        seen["url"] = url
        seen["params"] = params
        seen["cookies"] = cookies
        return _Response([{"Variant/DBID": "TP53_010464"}])

    monkeypatch.setattr(mod.requests, "get", _fake_get)
    return seen


@pytest.mark.unit
def test_the_search_request_carries_the_cookie(captured):
    """Without it LOVD serves its bot-check page instead of the variant."""
    LOVDTool(_config("search_variants")).run(
        {"gene_symbol": "TP53", "variant_dbid": "TP53_010464"}
    )

    assert captured["cookies"], "no cookie sent; LOVD answers with an HTML bot check"
    assert captured["cookies"].get("lovd_cookie_check") == "OK", captured["cookies"]


@pytest.mark.unit
def test_the_bot_check_page_is_reported_as_itself(monkeypatch):
    """A JSON-parser error hid this defect; the message must name the real cause."""

    def _serve_bot_check(url, params=None, cookies=None, timeout=None, **kwargs):
        return _Response(BOT_CHECK_PAGE, is_json=False)

    monkeypatch.setattr(mod.requests, "get", _serve_bot_check)

    result = LOVDTool(_config("search_variants")).run(
        {"gene_symbol": "TP53", "variant_dbid": "TP53_010464"}
    )

    assert result["status"] == "error", result
    assert "Expecting value" not in result["error"], (
        "the JSON parser is not the problem and must not be what we report"
    )
    assert "html" in result["error"].lower() or "browser" in result["error"].lower(), (
        result["error"]
    )


@pytest.mark.network
def test_the_real_service_returns_the_documented_variant():
    """The claim the unit tests cannot make: this query returns the variant."""
    result = LOVDTool(_config("search_variants")).run(
        {"gene_symbol": "TP53", "variant_dbid": "TP53_010464"}
    )

    assert result["status"] == "success", result
    assert result["data"], "expected one variant row for TP53_010464"
    assert result["data"][0]["Variant/DBID"] == "TP53_010464", result["data"][0]


@pytest.mark.network
def test_the_unaffected_gene_route_still_works():
    """`/genes/{gene}` never needed the cookie; the fix must not disturb it."""
    result = LOVDTool(_config("get_gene")).run({"gene_symbol": "TP53"})

    assert result["status"] == "success", result
    assert result["data"]["symbol"] == "TP53", result["data"]
