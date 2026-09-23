"""Europe PMC answered its own failures with statements about the literature.

Six shapes, each turning an infrastructure problem into a claim about the evidence, which
is the class the Skill Process design exists to remove.

* The error item carries `open_access: False` and `citations: 0`. A search that never
  reached the source says the paper is not open access and has no citations.
* The envelope reports `metadata.count` of the item list, which on a failure holds the one
  error item, so the reader is told one article came back beside `data: []`.
* The fallback chain reports `trace[-1]`, so a retryable 503 followed by a 403 is presented
  with the 403 and reads as not worth retrying.
* The lite request carries the journal name. When it fails the code falls through to
  `rec["source"]`, which is a **database code** -- `MED`, `PMC`, `PPR` -- printed where a
  journal title belongs.
* A full text that could not be fetched is skipped with `continue`, so the article
  contributes no snippet and the run concludes the paper does not mention the term it was
  searched for. That is the headline defect.
* Three caps of three narrow the answer and none of them is stated.

The article records here are the shape recorded in `tests/tools/test_europe_pmc_auto_snippets.py`,
not one invented for the test.
"""

import pytest

import tooluniverse.europe_pmc_tool as mod
from tooluniverse.europe_pmc_tool import EuropePMCTool

pytestmark = pytest.mark.unit


class _Resp:
    def __init__(self, *, status_code=200, text="", url="", json_data=None, reason="",
                 headers=None):
        self.status_code = status_code
        self.text = text
        self.url = url or "https://example.test"
        self.reason = reason
        self.headers = headers or {}
        self._json_data = json_data

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON data")
        return self._json_data


def _record(article_id="12345", **over):
    """One core record, as Europe PMC returns it."""
    rec = {"id": article_id, "source": "MED", "pmid": article_id,
           "pmcid": f"PMC{article_id}", "title": "Study on antibiotic resistance",
           "abstractText": "We studied resistance evolution.",
           "authorList": {"author": [{"fullName": "Smith J"}]},
           "pubYear": "2023", "doi": "10.1234/test", "isOpenAccess": "Y",
           "citedByCount": 10}
    rec.update(over)
    return rec


def _search_page(records, hit_count=1):
    return {"hitCount": hit_count, "resultList": {"result": records},
            "nextCursorMark": None}


def _tool():
    return EuropePMCTool({"name": "EuropePMC_search_articles"})


# ------------------------------------------------------- a failure is not a fact about a paper

def test_a_search_that_never_reached_the_source_states_no_open_access_status(monkeypatch):
    monkeypatch.setattr(mod, "request_with_retry",
                        lambda *a, **k: _Resp(status_code=503, reason="Service Unavailable"))

    out = _tool().run({"query": "cisplatin", "limit": 5})

    assert out["status"] == "error"
    assert "open_access" not in str(out.get("data")), out
    assert out.get("retryable") is True


def test_the_error_item_itself_claims_nothing_about_the_paper():
    item = EuropePMCTool._error_item("Europe PMC API error 503", retryable=True)

    assert "open_access" not in item, item
    assert "citations" not in item, item


def test_a_failure_envelope_counts_the_articles_it_returned(monkeypatch):
    """`count: 1` beside `data: []` told the reader one article came back."""
    monkeypatch.setattr(mod, "request_with_retry",
                        lambda *a, **k: _Resp(status_code=503, reason="Service Unavailable"))

    out = _tool().run({"query": "cisplatin", "limit": 5})

    assert out["data"] == []
    assert out["metadata"]["count"] == 0, out["metadata"]


# ------------------------------------------------------------------- the chain's own verdict

def test_a_chain_that_began_with_a_retryable_failure_is_still_retryable(monkeypatch):
    """503 on Europe PMC then 403 on the NCBI mirror: the 503 decides, not the 403."""
    answers = iter([_Resp(status_code=503), _Resp(status_code=404),
                    _Resp(status_code=404), _Resp(status_code=403)])
    monkeypatch.setattr(mod, "request_with_retry", lambda *a, **k: next(answers, _Resp(status_code=403)))

    fetch = mod._fetch_fulltext_with_trace(
        None, europe_fulltext_xml_url="https://europepmc.org/x/fullTextXML",
        pmcid="PMC12345", timeout=1)

    assert fetch["ok"] is False
    assert fetch["retryable"] is True, fetch["trace"]


def test_a_chain_of_plain_refusals_is_not_retryable(monkeypatch):
    """Every attempt a 403: nothing here is worth asking again."""
    monkeypatch.setattr(mod, "request_with_retry", lambda *a, **k: _Resp(status_code=403))

    fetch = mod._fetch_fulltext_with_trace(
        None, europe_fulltext_xml_url="https://europepmc.org/x/fullTextXML",
        pmcid="PMC12345", timeout=1)

    assert fetch["ok"] is False
    assert fetch["retryable"] is False, fetch["trace"]


# ------------------------------------------------------ a database code is not a journal name

def _core_and_lite(monkeypatch, *, lite_status=200, lite_json=None):
    def _get(session, method, url, **kw):
        result_type = (kw.get("params") or {}).get("resultType")
        if result_type == "lite":
            return _Resp(status_code=lite_status, json_data=lite_json)
        return _Resp(json_data=_search_page([_record()]))
    monkeypatch.setattr(mod, "request_with_retry", _get)


def test_a_lite_failure_does_not_put_the_database_code_in_the_journal(monkeypatch):
    """`MED` is Europe PMC's name for its own index, not the journal the paper is in."""
    _core_and_lite(monkeypatch, lite_status=503)

    (article,) = _tool().run({"query": "cisplatin", "limit": 1})["data"]

    assert article["journal"] != "MED", article
    assert article["data_quality"]["has_journal"] is False


def test_a_lite_answer_still_gives_the_journal(monkeypatch):
    _core_and_lite(monkeypatch, lite_status=200, lite_json=_search_page(
        [{"id": "12345", "journalTitle": "Journal of Resistance"}]))

    (article,) = _tool().run({"query": "cisplatin", "limit": 1})["data"]

    assert article["journal"] == "Journal of Resistance"


# -------------------------------------------------- a paper that could not be read said nothing

def test_a_full_text_that_could_not_be_read_is_not_a_paper_without_the_term(monkeypatch):
    """The article contributed no snippet, and nothing said the fetch had failed."""
    def _get(session, method, url, **kw):
        params = kw.get("params") or {}
        if params.get("resultType") == "lite":
            return _Resp(json_data=_search_page([{"id": "12345",
                                                  "journalTitle": "Journal of Resistance"}]))
        if params.get("resultType") == "core":
            return _Resp(json_data=_search_page([_record()]))
        return _Resp(status_code=503)      # every full-text attempt fails
    monkeypatch.setattr(mod, "request_with_retry", _get)

    (article,) = _tool().run({"query": "cisplatin", "limit": 1,
                              "extract_terms_from_fulltext": ["resistance"]})["data"]

    assert article.get("fulltext_snippets_error"), article
    assert not article.get("fulltext_snippets")


def test_the_caps_that_narrow_the_answer_are_stated(monkeypatch):
    """Three caps of three: articles processed, snippets per term, abstracts enriched."""
    def _get(session, method, url, **kw):
        params = kw.get("params") or {}
        if params.get("resultType") == "lite":
            return _Resp(json_data=_search_page([]))
        if params.get("resultType") == "core":
            return _Resp(json_data=_search_page(
                [_record(str(i)) for i in range(5)], hit_count=5))
        return _Resp(status_code=403)
    monkeypatch.setattr(mod, "request_with_retry", _get)

    out = _tool().run({"query": "cisplatin", "limit": 5,
                       "extract_terms_from_fulltext": ["resistance"]})

    assert "limits" in out["metadata"], out["metadata"]
    assert out["metadata"]["limits"]["fulltext_articles_scanned"] == 3


# ------------------------------------------- the structured tool: the two criteria I first missed
#
# Both live in `EuropePMCStructuredFullTextTool`, not in `EuropePMCTool._search`, which is why a
# first reading of the search path found neither.

from tooluniverse.europe_pmc_tool import EuropePMCStructuredFullTextTool  # noqa: E402

_ARTICLE = """<article>
  <front><article-meta><title-group><article-title>A study</article-title></title-group>
  <abstract>{abstract}</abstract></article-meta></front>
  <body><sec><title>Methods</title><p>We did things.</p></sec></body>
</article>"""


def _structured():
    return EuropePMCStructuredFullTextTool({"name": "EuropePMC_get_structured_fulltext"})


def test_a_pmid_lookup_that_failed_does_not_state_the_article_is_not_open_access(monkeypatch):
    """`_resolve_pmid_to_pmcid` swallows everything, so a dead network read as a closed paper."""
    def _boom(*a, **k):
        raise OSError("Europe PMC unreachable")
    monkeypatch.setattr(mod, "request_with_retry", _boom)

    out = _structured().run({"pmid": "32226684"})

    assert out["status"] == "error"
    assert "open-access" not in out["error"], out["error"]
    assert "unreachable" in out["error"] or "could not be reached" in out["error"], out["error"]


def test_a_pmid_the_source_genuinely_does_not_know_still_says_so(monkeypatch):
    """The real not-found answer must survive: only the outage stops claiming a status."""
    monkeypatch.setattr(mod, "request_with_retry",
                        lambda *a, **k: _Resp(json_data={"resultList": {"result": []}}))

    out = _structured().run({"pmid": "32226684"})

    assert out["status"] == "error"
    assert "PubMed Central" in out["error"]


def test_an_abstract_element_holding_no_text_is_not_a_parsed_abstract():
    """`<abstract></abstract>` yields "" — an abstract key with nothing in it reads as read."""
    parsed = _structured()._parse_article_xml(_ARTICLE.format(abstract=""))

    assert parsed["abstract"] is None
    assert parsed["has_abstract"] is False


def test_an_abstract_with_text_is_reported_as_read():
    parsed = _structured()._parse_article_xml(
        _ARTICLE.format(abstract="<p>We studied resistance.</p>"))

    assert "resistance" in parsed["abstract"]
    assert parsed["has_abstract"] is True
