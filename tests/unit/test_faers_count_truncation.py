"""FAERS count queries discarded 29% of the reaction distribution, silently.

`FAERSAnalyticsTool` builds its `count=` URLs by hand and sends neither a `limit`
nor an `api_key`. openFDA defaults a count request to the top **100** terms, so
every reaction table, stratification and serious-event summary this tool has ever
produced was the top 100 and said nothing about the rest.

Measured against openFDA 2026-08-04, `medicinalproduct:"LUTATHERA"` counting
`patient.reaction.reactionmeddrapt.exact`:

    no limit (what the code sends)   -> HTTP 200, 100 terms, summed count  9,038
    &limit=1000 with an api_key      -> HTTP 200, 1000 terms, summed count 12,720
    &limit=1000 without an api_key   -> HTTP 403 API_KEY_MISSING
    &limit=1001 with an api_key      -> HTTP 400 "Limit cannot exceed 1000 ..."

Three things follow, and the middle one is why this is not a one-line fix.

**1. The loss is 29%.** 9,038 of 12,720 reaction mentions, and it is drawn from the
tail, so it is exactly the rare-event end that a pharmacovigilance reader cares about.

**2. The limit cannot be raised without the key.** openFDA allows `limit>100` only
for authenticated callers, so sending `limit=1000` unconditionally would turn a
working-but-truncated tool into a 403 wherever `FDA_API_KEY` is unset. The key is
read by `openfda_tool.py` and `openfda_adv_tool.py`; this module never read it.

**3. 1000 does not exhaust the tail either.** At `limit=1000` the trailing terms
still have `count == 1`, so terms remain beyond the cap. A full page is evidence of
truncation, not of completeness, and the envelope has to say so — reporting a capped
distribution as if it were the whole one is the same class of defect as the silent
zero this tool was already fixed for.
"""

import json
import pathlib

import pytest

from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

COUNT_FIELD = "patient.reaction.reactionmeddrapt.exact"


def _shipped_config():
    import glob

    for path in glob.glob(
        str(
            pathlib.Path(__file__).resolve().parents[2]
            / "src" / "tooluniverse" / "data" / "**" / "*.json"
        ),
        recursive=True,
    ):
        try:
            entries = json.loads(open(path).read())
        except Exception:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if (
                isinstance(entry, dict)
                and entry.get("name") == "FAERS_calculate_disproportionality"
            ):
                return entry
    raise AssertionError("FAERS_calculate_disproportionality not found in data/")


CONFIG = _shipped_config()


def _tool():
    return FAERSAnalyticsTool(CONFIG)


@pytest.mark.unit
def test_a_key_buys_the_thousand_term_page(monkeypatch):
    monkeypatch.setenv("FDA_API_KEY", "TESTKEY")

    url = _tool()._count_url('drug:"X"', COUNT_FIELD)

    assert "&limit=1000" in url
    assert "&api_key=TESTKEY" in url


@pytest.mark.unit
def test_without_a_key_the_limit_is_left_off(monkeypatch):
    """openFDA 403s on limit>100 unauthenticated — asking for 1000 breaks the call."""
    monkeypatch.delenv("FDA_API_KEY", raising=False)

    url = _tool()._count_url('drug:"X"', COUNT_FIELD)

    assert "limit=" not in url
    assert "api_key=" not in url


@pytest.mark.unit
def test_a_full_page_is_reported_as_truncated():
    """1000 terms means more were dropped, not that the distribution ended."""
    results = [{"term": f"EVENT_{i}", "count": 1} for i in range(1000)]

    note = _tool()._truncation_note(results)

    assert note is not None
    assert "1000" in note


@pytest.mark.unit
def test_a_short_page_is_complete():
    results = [{"term": "NAUSEA", "count": 12}, {"term": "RASH", "count": 3}]

    assert _tool()._truncation_note(results) is None


@pytest.mark.unit
def test_the_pt_total_counts_terms_not_the_display_slice(monkeypatch):
    """`total_unique_PTs` was len() of a 50-item slice, so it always said 50.

    The rollup shows the top 50 preferred terms but counted the slice rather than
    the response, reporting a display cap as a data total — the same mistake as
    reporting a truncated distribution as the whole one, one layer down.
    """
    monkeypatch.delenv("FDA_API_KEY", raising=False)
    payload = {"results": [{"term": f"PT_{i}", "count": 200 - i} for i in range(120)]}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return payload

    import tooluniverse.faers_analytics_tool as mod

    monkeypatch.setattr(mod.requests, "get", lambda *a, **k: _Resp())

    out = _tool()._rollup_meddra_hierarchy({"drug_name": "aspirin"})
    hierarchy = out["data"]["meddra_hierarchy"]

    assert len(hierarchy["PT_level"]) == 50, "still shows the top 50"
    assert hierarchy["total_unique_PTs"] == 120, hierarchy["total_unique_PTs"]
