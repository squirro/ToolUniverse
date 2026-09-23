"""Four FAERS paths stated a number that was not true, each inside a success envelope.

All four grow from one mismatch. `_count_url` sends no `limit` without an `FDA_API_KEY`,
because openFDA rejects a limit above 100 from an unauthenticated caller, so the page that
actually applies is 100. `_truncation_note` compared the row count against `COUNT_PAGE_MAX`,
which is 1000. Without a key the note could never fire, and every count path reported a
page as though it were the distribution.

The temporal trend is the worst of it. openFDA orders a `count=` by frequency, so a capped
date count is the hundred **most reported** dates, not the first hundred. Sorting those by
year and comparing the ends produced Increasing, Decreasing or Stable over something that
is not a time series at all.

Beside those, the serious-events total was read from a response whose status was never
checked, so a 404, a 429 or a 500 with a JSON body parsed cleanly to a total of zero and
was printed next to a populated reaction list; and the sensitivity arm read a dropped HTTP
failure in the synonym lookup as a fact about the drug, reporting that only one openFDA
field knows it.
"""

import pytest
import requests

import tooluniverse.faers_analytics_tool as mod
from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

pytestmark = pytest.mark.unit

COUNT_FIELD = "patient.reaction.reactionmeddrapt.exact"

# What openFDA gives an unauthenticated count request. The tool asks for no limit,
# so this is the ceiling every count path below actually ran under.
UNAUTHENTICATED_PAGE = 100


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code), response=self)

    def json(self):
        return self._payload


def _openfda(monkeypatch, on_count, on_total=None, key=None):
    """Answer a count URL and a `limit=1` total URL differently, as openFDA does."""
    if key:
        monkeypatch.setenv("FDA_API_KEY", key)
    else:
        monkeypatch.delenv("FDA_API_KEY", raising=False)
    total = on_total if on_total is not None else _Resp(
        {"meta": {"results": {"total": 4200}}})

    def _get(url, *args, **kwargs):
        answer = on_count if "count=" in url else total
        return answer(url) if callable(answer) else answer

    monkeypatch.setattr(mod.requests, "get", _get)


def _tool():
    return FAERSAnalyticsTool({"name": "FAERS_calculate_disproportionality",
                               "description": "", "parameter": {}})


def _full_page(rows):
    return _Resp({"results": rows})


# ------------------------------------------------------- the ceiling that actually applied

def test_a_full_unauthenticated_page_is_reported_as_truncated(monkeypatch):
    """100 terms is the whole page openFDA gives without a key, so more were dropped."""
    monkeypatch.delenv("FDA_API_KEY", raising=False)
    results = [{"term": f"EVENT_{i}", "count": 1} for i in range(UNAUTHENTICATED_PAGE)]

    assert _tool()._truncation_note(results) is not None


def test_a_page_short_of_the_unauthenticated_ceiling_is_complete(monkeypatch):
    monkeypatch.delenv("FDA_API_KEY", raising=False)
    results = [{"term": f"EVENT_{i}", "count": 1} for i in range(UNAUTHENTICATED_PAGE - 1)]

    assert _tool()._truncation_note(results) is None


def test_a_key_raises_the_ceiling_so_a_hundred_terms_is_the_whole_answer(monkeypatch):
    """With a key the page is 1000, so 100 terms means the distribution ended."""
    monkeypatch.setenv("FDA_API_KEY", "TESTKEY")
    results = [{"term": f"EVENT_{i}", "count": 1} for i in range(UNAUTHENTICATED_PAGE)]

    assert _tool()._truncation_note(results) is None


# ------------------------------------------------------------------------ the temporal trend

def test_a_capped_date_count_is_not_reported_as_a_trend(monkeypatch):
    """The rows are the most frequently reported dates. Their ends are not a trend."""
    rows = [{"time": f"{2004 + i % 20}0101", "count": 500 - i}
            for i in range(UNAUTHENTICATED_PAGE)]
    _openfda(monkeypatch, _full_page(rows))

    out = _tool()._analyze_temporal_trends({"drug_name": "aspirin"})

    assert out["trend_analysis"]["trend"] not in ("Increasing", "Decreasing", "Stable"), out


def test_a_capped_date_count_says_the_rows_are_a_frequency_sample(monkeypatch):
    rows = [{"time": f"{2004 + i % 20}0101", "count": 500 - i}
            for i in range(UNAUTHENTICATED_PAGE)]
    _openfda(monkeypatch, _full_page(rows))

    out = _tool()._analyze_temporal_trends({"drug_name": "aspirin"})

    assert "most" in out["trend_analysis"]["trend"].lower(), out["trend_analysis"]


def test_a_complete_date_count_still_gets_its_trend(monkeypatch):
    """The fix must not silence a date count that did fit in one page."""
    rows = [{"time": "20200101", "count": 10}, {"time": "20240101", "count": 90}]
    _openfda(monkeypatch, _full_page(rows))

    out = _tool()._analyze_temporal_trends({"drug_name": "aspirin"})

    assert out["trend_analysis"]["trend"] == "Increasing", out["trend_analysis"]


# ------------------------------------------------------------------- the serious-events total

def _serious_total(monkeypatch, status):
    """Only the serious-events total fails; the drug probe and the count both answer.

    The total URL is the one carrying the seriousness clause, so it is the only
    request this stubs out -- a fake that killed every `limit=1` URL would take the
    drug-field probe down first and prove nothing about the path under test.
    """
    monkeypatch.delenv("FDA_API_KEY", raising=False)

    def _get(url, *args, **kwargs):
        if "serious:1" in url and "count=" not in url:
            return _Resp({"error": {"code": "FAILED"}}, status=status)
        if "count=" in url:
            return _Resp({"results": [{"term": "NAUSEA", "count": 12}]})
        return _Resp({"meta": {"results": {"total": 4200}}})

    monkeypatch.setattr(mod.requests, "get", _get)


def test_a_failed_total_request_is_not_read_as_a_total_of_zero(monkeypatch):
    """A 500 with a JSON body parses cleanly; `meta` is simply absent."""
    _serious_total(monkeypatch, 500)

    out = _tool()._filter_serious_events({"drug_name": "aspirin"})

    assert out.get("status") != "success", out


def test_a_search_that_matched_nothing_is_still_a_real_zero(monkeypatch):
    """openFDA answers 404 to a search matching nothing. That zero is true."""
    _serious_total(monkeypatch, 404)

    out = _tool()._filter_serious_events({"drug_name": "aspirin"})

    assert out["status"] == "success", out
    assert out["data"]["total_serious_events"] == 0


# --------------------------------------------------- what the capped page does to the numbers

def test_capped_demographic_percentages_say_what_they_are_a_percentage_of(monkeypatch):
    rows = [{"term": f"C{i}", "count": 10} for i in range(UNAUTHENTICATED_PAGE)]
    _openfda(monkeypatch, _full_page(rows))

    out = _tool()._stratify_by_demographics(
        {"drug_name": "aspirin", "stratify_by": "country"})

    assert "truncation_warning" in out, out
    assert "page" in out["total_reports_note"].lower(), out.get("total_reports_note")


def test_a_capped_preferred_term_count_is_carried_as_truncated(monkeypatch):
    rows = [{"term": f"PT_{i}", "count": 200 - i} for i in range(UNAUTHENTICATED_PAGE)]
    _openfda(monkeypatch, _full_page(rows))

    out = _tool()._rollup_meddra_hierarchy({"drug_name": "aspirin"})

    assert "truncation_warning" in out["data"], out["data"]


def test_a_capped_serious_event_filter_is_carried_as_truncated(monkeypatch):
    rows = [{"term": f"PT_{i}", "count": 200 - i} for i in range(UNAUTHENTICATED_PAGE)]
    _openfda(monkeypatch, _full_page(rows))

    out = _tool()._filter_serious_events({"drug_name": "aspirin"})

    assert "truncation_warning" in out["data"], out["data"]


# ------------------------------------------------------------------ the failed synonym lookup

def _name_set_lookup_dies(monkeypatch):
    """Only openFDA's name-set lookup fails. Every field probe still answers.

    `_openfda_block` rebuilds the very URL `_field_total` has just probed with, so the
    two cannot be told apart by URL -- but the name-set lookup is always the second
    request, because the block resolves the field before asking for the names. Killing
    that one request alone leaves the arm on exactly the branch the defect produces:
    one field matched, so it reports that only one field knows the drug.

    Only the first drug field matches, as for a drug whose other names openFDA would
    have supplied had the lookup answered.
    """
    monkeypatch.delenv("FDA_API_KEY", raising=False)
    calls = []

    def _get(url, *args, **kwargs):
        calls.append(url)
        if len(calls) == 2:
            raise requests.ConnectionError("openFDA unreachable")
        if FAERSAnalyticsTool.DRUG_NAME_FIELDS[0] in url:
            return _Resp({"meta": {"results": {"total": 4200}}})
        return _Resp({"error": {"code": "NOT_FOUND"}}, status=404)

    monkeypatch.setattr(mod.requests, "get", _get)


def test_a_dropped_synonym_lookup_is_not_a_statement_about_the_drug(monkeypatch):
    """One field matching is a fact. A lookup that never ran is not that fact."""
    _name_set_lookup_dies(monkeypatch)

    out = _tool()._population_sensitivity("aspirin", "NAUSEA", "generic_name", 2.0, 10, 100)

    assert out["computed"] is False
    assert "only one openfda field" not in out["reason"].lower(), out["reason"]
    assert "look" in out["reason"].lower(), out["reason"]
