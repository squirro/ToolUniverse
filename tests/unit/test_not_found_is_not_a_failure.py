"""A source that answers "nothing here" has not failed (DSR-695).

Four of the twelve single-failure tools in the 2026-08-21 skill sweep were the
source answering honestly, reported as an error:

* PubChem answers an unknown name with HTTP 404 and ``PUGREST.NotFound``.
* openFDA answers a search with no matches with HTTP 404 and ``NOT_FOUND``. The
  Orange Book tool also sent a bare application number ("202379"), which can
  never match: openFDA stores "NDA202379".
* NICE answers with ``resultCount: 0`` and ``failed: false``.
* GIN answers with a page that says "0 results found".

The opposite mistake is guarded too. Each source has a different answer when it
is broken, and that answer must stay an error: a PubChem fault that is not
NotFound, an openFDA 404 that is not JSON, a NICE page without its results
object, a GIN page without its result count.

Response shapes recorded 2026-09-21.
"""

import json
import unittest
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


# --- PubChem ---------------------------------------------------------------

PUBCHEM_NOT_FOUND = {
    "Fault": {
        "Code": "PUGREST.NotFound",
        "Message": "No CID found",
        "Details": ["No CID found that matches the given name"],
    }
}
PUBCHEM_BUSY = {
    "Fault": {
        "Code": "PUGREST.ServerBusy",
        "Message": "Too many requests or server too busy",
    }
}


def _pubchem():
    from tooluniverse.pubchem_tool import PubChemRESTTool

    return PubChemRESTTool({
        "name": "PubChem_get_CID_by_compound_name",
        "type": "PubChemRESTTool",
        "parameter": {"type": "object",
                      "properties": {"name": {"type": "string"}},
                      "required": []},
        "fields": {"endpoint": "/compound/name/{name}/cids/JSON"},
    })


class TestPubChem(unittest.TestCase):
    def test_a_name_pubchem_does_not_hold_is_an_empty_result(self):
        with patch("tooluniverse.pubchem_tool.requests.get") as get:
            get.return_value = _response(404, PUBCHEM_NOT_FOUND)
            out = _pubchem().run({"name": "DOTA-Tyr3-octreotate"})
        assert out["status"] == "success", out
        assert not out.get("data"), out

    def test_a_busy_server_is_still_an_error(self):
        with patch("tooluniverse.pubchem_tool.requests.get") as get:
            get.return_value = _response(503, PUBCHEM_BUSY)
            out = _pubchem().run({"name": "aspirin"})
        assert out["status"] == "error", out

    def test_a_404_that_is_not_pubchems_not_found_is_still_an_error(self):
        with patch("tooluniverse.pubchem_tool.requests.get") as get:
            get.return_value = _response(404, text="<html>Not Found</html>")
            out = _pubchem().run({"name": "aspirin"})
        assert out["status"] == "error", out


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


def _http_error(resp):
    import requests

    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        f"{resp.status_code} Client Error", response=resp)
    return resp


class TestOrangeBook(unittest.TestCase):
    def test_no_matching_application_is_an_empty_result(self):
        with patch("tooluniverse.fda_orange_book_tool.openfda_get") as get:
            get.return_value = _http_error(_response(404, OPENFDA_NO_MATCH))
            out = _orange_book().run({"brand_name": "NOSUCHBRAND"})
        assert out["status"] == "success", out
        assert out["data"]["drugs"] == [], out

    def test_a_404_that_is_not_openfdas_no_match_is_still_an_error(self):
        with patch("tooluniverse.fda_orange_book_tool.openfda_get") as get:
            get.return_value = _http_error(
                _response(404, text="<pre>Cannot GET /drug/drugsfda.json</pre>"))
            out = _orange_book().run({"brand_name": "ZYTIGA"})
        assert out["status"] == "error", out

    def test_a_bare_application_number_is_searched_with_its_prefixes(self):
        with patch("tooluniverse.fda_orange_book_tool.openfda_get") as get:
            get.return_value = _response(200, OPENFDA_ONE_DRUG)
            out = _orange_book().run({"application_number": "202379"})
        search = get.call_args[0][1]["search"]
        for prefixed in ("NDA202379", "ANDA202379", "BLA202379"):
            assert prefixed in search, search
        assert out["status"] == "success", out
        assert out["data"]["drugs"][0]["application_number"] == "NDA202379"

    def test_a_prefixed_application_number_is_sent_as_given(self):
        with patch("tooluniverse.fda_orange_book_tool.openfda_get") as get:
            get.return_value = _response(200, OPENFDA_ONE_DRUG)
            _orange_book().run({"application_number": "NDA202379"})
        assert get.call_args[0][1]["search"] == 'application_number:"NDA202379"'


# --- NICE ------------------------------------------------------------------

def _nice_page(results):
    page_props = {} if results is None else {"results": results}
    data = {"props": {"pageProps": page_props}}
    return ('<html><body><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(data) + "</script></body></html>")


NICE_ZERO = {"failed": False, "errorMessage": None, "resultCount": 0, "documents": []}
NICE_FAILED = {"failed": True, "errorMessage": "Search unavailable",
               "resultCount": 0, "documents": []}


def _nice(html):
    from tooluniverse.unified_guideline_tools import NICEWebScrapingTool

    tool = NICEWebScrapingTool({"name": "NICE_Clinical_Guidelines_Search"})
    tool.session = MagicMock()
    tool.session.get.return_value = _response(200, text=html)
    return tool


@patch("tooluniverse.unified_guideline_tools.time.sleep", lambda *_: None)
class TestNICE(unittest.TestCase):
    def test_zero_results_is_an_empty_list(self):
        out = _nice(_nice_page(NICE_ZERO)).run({"query": "no such guideline"})
        assert out == [], out

    def test_a_search_nice_reports_as_failed_is_still_an_error(self):
        out = _nice(_nice_page(NICE_FAILED)).run({"query": "diabetes"})
        assert isinstance(out, dict) and out.get("error"), out

    def test_a_page_without_the_results_object_is_still_an_error(self):
        out = _nice(_nice_page(None)).run({"query": "diabetes"})
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


@patch("tooluniverse.unified_guideline_tools.time.sleep", lambda *_: None)
class TestGIN(unittest.TestCase):
    def test_zero_results_is_an_empty_list(self):
        out = _gin(GIN_ZERO).run({"query": "no such guideline"})
        assert out == [], out

    def test_results_are_still_returned(self):
        out = _gin(GIN_ONE).run({"query": "asthma children"})
        assert [g["title"] for g in out] == ["Promoting Asthma Control in Children"]

    def test_a_page_without_a_result_count_is_an_error(self):
        """GIN sometimes serves the search page with no listing at all."""
        out = _gin(GIN_NO_LISTING).run({"query": "diabetes"})
        assert isinstance(out, dict) and out.get("status") == "error", out
