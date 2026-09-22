"""A source that answers "nothing here" has not failed (DSR-695).

Four of the twelve single-failure tools in the 2026-08-21 skill sweep were the source
answering honestly, reported as an error: PubChem 404s an unknown name with
``PUGREST.NotFound``; openFDA 404s a search with no matches with ``NOT_FOUND`` (and the
Orange Book tool sent a bare application number, "202379", which can never match because
openFDA stores "NDA202379"); NICE answers ``resultCount: 0`` with ``failed: false``; GIN
serves a page saying "0 results found". The opposite mistake is guarded too -- each source
has a different answer when it is broken, and that answer must stay an error.

Response shapes recorded 2026-09-21.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _response(status=200, payload=None, text=""):
    resp = MagicMock()
    resp.status_code = status
    if payload is None:
        resp.json.side_effect = ValueError("not JSON")
        resp.text = text
    else:
        resp.json.return_value = payload
        resp.text = json.dumps(payload)
    resp.content = resp.text.encode()
    return resp


def _http_error(resp):
    import requests

    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        f"{resp.status_code} Client Error", response=resp)
    return resp


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("tooluniverse.unified_guideline_tools.time.sleep", lambda *_: None):
        yield


# --- PubChem ---------------------------------------------------------------

PUBCHEM_NOT_FOUND = {"Fault": {"Code": "PUGREST.NotFound", "Message": "No CID found",
                               "Details": ["No CID found that matches the given name"]}}
PUBCHEM_BUSY = {"Fault": {"Code": "PUGREST.ServerBusy",
                          "Message": "Too many requests or server too busy"}}


def _pubchem():
    from tooluniverse.pubchem_tool import PubChemRESTTool

    return PubChemRESTTool({
        "name": "PubChem_get_CID_by_compound_name",
        "type": "PubChemRESTTool",
        "parameter": {"type": "object", "properties": {"name": {"type": "string"}},
                      "required": []},
        "fields": {"endpoint": "/compound/name/{name}/cids/JSON"},
    })


@pytest.mark.parametrize("response,status", [
    (_response(404, PUBCHEM_NOT_FOUND), "success"),           # the source answered
    (_response(503, PUBCHEM_BUSY), "error"),
    (_response(404, text="<html>Not Found</html>"), "error"),  # a 404 that is not NotFound
])
def test_pubchem_tells_an_unknown_name_from_a_broken_server(response, status):
    with patch("tooluniverse.pubchem_tool.requests.get") as get:
        get.return_value = response
        out = _pubchem().run({"name": "DOTA-Tyr3-octreotate"})

    assert out["status"] == status, out
    assert status == "error" or not out.get("data"), out


# --- FDA Orange Book -------------------------------------------------------

OPENFDA_NO_MATCH = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}
OPENFDA_ONE_DRUG = {
    "meta": {"results": {"total": 1}},
    "results": [{
        "application_number": "NDA202379",
        "sponsor_name": "JANSSEN BIOTECH",
        "products": [{"brand_name": "ZYTIGA", "active_ingredients": []}],
    }],
}


def _orange_book():
    from tooluniverse.fda_orange_book_tool import FDAOrangeBookTool

    return FDAOrangeBookTool({
        "name": "FDA_OrangeBook_get_exclusivity",
        "type": "FDAOrangeBookTool",
        "parameter": {"type": "object", "required": [],
                      "properties": {"operation": {"const": "get_exclusivity"}}},
    })


@pytest.mark.parametrize("response,status", [
    (_http_error(_response(404, OPENFDA_NO_MATCH)), "success"),
    (_http_error(_response(404, text="<pre>Cannot GET /drug/drugsfda.json</pre>")), "error"),
])
def test_openfda_tells_no_matches_from_a_broken_endpoint(response, status):
    with patch("tooluniverse.fda_orange_book_tool.openfda_get") as get:
        get.return_value = response
        out = _orange_book().run({"brand_name": "NOSUCHBRAND"})

    assert out["status"] == status, out
    assert status == "error" or out["data"]["drugs"] == [], out


def test_a_bare_application_number_is_searched_with_its_prefixes():
    with patch("tooluniverse.fda_orange_book_tool.openfda_get") as get:
        get.return_value = _response(200, OPENFDA_ONE_DRUG)
        out = _orange_book().run({"application_number": "202379"})

    search = get.call_args[0][1]["search"]
    for prefixed in ("NDA202379", "ANDA202379", "BLA202379"):
        assert prefixed in search, search
    assert out["status"] == "success", out
    assert out["data"]["drugs"][0]["application_number"] == "NDA202379"


def test_a_prefixed_application_number_is_sent_as_given():
    with patch("tooluniverse.fda_orange_book_tool.openfda_get") as get:
        get.return_value = _response(200, OPENFDA_ONE_DRUG)
        _orange_book().run({"application_number": "NDA202379"})

    assert get.call_args[0][1]["search"] == 'application_number:"NDA202379"'


# --- NICE ------------------------------------------------------------------

NICE_ZERO = {"failed": False, "errorMessage": None, "resultCount": 0, "documents": []}
NICE_FAILED = {"failed": True, "errorMessage": "Search unavailable",
               "resultCount": 0, "documents": []}


def _nice(results):
    from tooluniverse.unified_guideline_tools import NICEWebScrapingTool

    page_props = {} if results is None else {"results": results}
    html = ('<html><body><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": page_props}}) + "</script></body></html>")
    tool = NICEWebScrapingTool({"name": "NICE_Clinical_Guidelines_Search"})
    tool.session = MagicMock()
    tool.session.get.return_value = _response(200, text=html)
    return tool


@pytest.mark.parametrize("results,empty", [
    (NICE_ZERO, True),        # resultCount 0 with failed:false is the source answering
    (NICE_FAILED, False),
    (None, False),            # a page without the results object is broken
])
def test_nice_tells_zero_results_from_a_broken_search(results, empty):
    out = _nice(results).run({"query": "diabetes"})

    if empty:
        assert out == [], out
    else:
        assert isinstance(out, dict) and out.get("error"), out


# --- GIN -------------------------------------------------------------------

GIN_ZERO = ('<html><body><div class="pager-header"><span>0 results found for '
            '<span class="search-keyword">"no such guideline"</span></span> </div>'
            "</body></html>")
GIN_ONE = ('<html><body><div class="pager-header"><span>1 results found for '
           '<span class="search-keyword">"asthma children"</span></span> </div>'
           '<article class="node node--view-mode-listing"><h3><a href="/promoting-asthma">'
           "Promoting Asthma Control in Children</a></h3></article></body></html>")
GIN_NO_LISTING = "<html><body><div class='content-listing-results'></div></body></html>"


def _gin(html):
    from tooluniverse.unified_guideline_tools import GINGuidelinesTool

    tool = GINGuidelinesTool({"name": "GIN_Guidelines_Search"})
    tool.session = MagicMock()
    tool.session.get.return_value = _response(200, text=html)
    return tool


@pytest.mark.parametrize("html,titles", [
    (GIN_ZERO, []),
    (GIN_ONE, ["Promoting Asthma Control in Children"]),
])
def test_gin_returns_the_guidelines_its_page_lists(html, titles):
    out = _gin(html).run({"query": "asthma children"})

    assert isinstance(out, list) and [g["title"] for g in out] == titles, out


def test_a_page_without_a_result_count_is_an_error():
    """GIN sometimes serves the search page with no listing at all."""
    out = _gin(GIN_NO_LISTING).run({"query": "diabetes"})

    assert isinstance(out, dict) and out.get("status") == "error", out
