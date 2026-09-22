"""The FAERS reaction list is fetched as wide as the source allows, and says when it is cut.

Sending `count=` with no `limit` takes openFDA's default page, so a word the question asks
about can be lost to a page size nobody wrote. The width follows the key, because openFDA
needs an api_key for `limit>100`.
"""

import json
import pathlib

import pytest

import tooluniverse.openfda_adv_tool as mod
from tooluniverse.openfda_adv_tool import FDADrugAdverseEventTool

pytestmark = pytest.mark.unit


def _shipped_config():
    root = pathlib.Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
    for entry in json.loads((root / "fda_drug_adverse_event_tools.json").read_text()):
        if entry.get("name") == "FAERS_count_reactions_by_drug_event":
            return entry
    raise AssertionError("FAERS_count_reactions_by_drug_event not found")


class _Response:
    status_code = 200

    def __init__(self, results):
        self._results = results

    def raise_for_status(self):
        pass

    def json(self):
        return {"results": self._results}


@pytest.fixture
def sent(monkeypatch):
    seen = {}

    def get(url, *args, **kwargs):
        seen["url"] = url
        return _Response(seen.get("results", [{"term": "NAUSEA", "count": 3}]))

    monkeypatch.setattr(mod.requests, "get", get)
    return seen


def test_with_a_key_the_thousand_term_page_is_asked_for(monkeypatch, sent):
    monkeypatch.setenv("FDA_API_KEY", "TESTKEY")

    FDADrugAdverseEventTool(_shipped_config()).run({"medicinalproduct": "cisplatin"})

    assert "&limit=1000" in sent["url"]


def test_without_a_key_the_limit_is_left_off(monkeypatch, sent):
    """openFDA answers 403 to limit>100 without a key; asking would break the call."""
    monkeypatch.delenv("FDA_API_KEY", raising=False)

    FDADrugAdverseEventTool(_shipped_config()).run({"medicinalproduct": "cisplatin"})

    assert "limit=" not in sent["url"]


def test_a_full_page_says_that_more_terms_exist(monkeypatch, sent):
    monkeypatch.setenv("FDA_API_KEY", "TESTKEY")
    sent["results"] = [{"term": f"EVENT_{n}", "count": 1} for n in range(1000)]

    out = FDADrugAdverseEventTool(_shipped_config()).run({"medicinalproduct": "cisplatin"})

    assert len(out["result"]) == 1000
    assert "1000" in out["note"] and "more" in out["note"]


def test_a_short_page_is_the_whole_list(monkeypatch, sent):
    monkeypatch.setenv("FDA_API_KEY", "TESTKEY")

    out = FDADrugAdverseEventTool(_shipped_config()).run({"medicinalproduct": "cisplatin"})

    assert out["result"] == [{"term": "NAUSEA", "count": 3}]
    assert "note" not in out
