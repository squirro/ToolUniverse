"""ClinGen actionability: two dead endpoints, a wrong filter key, and a bare except.

`ClinGen_search_actionability` returned `{"Adult": [], "Pediatric": []}` with
`status: success` for BRCA1, a gene ClinGen definitely curates. Three faults
stacked, and the third is what hid the first two:

1. Both endpoints are gone. `actionability.clinicalgenome.org/ac/Adult/api/summ`
   and `/ac/Pediatric/api/summ` answer **404**; the data now lives at
   `search.clinicalgenome.org/api/actionability` (300 curated genes).
2. The filter looked for `gene` / `Gene`. The records key on **`symbol`**, so the
   filter matched 0 rows even when the fetch worked.
3. Each failing context was caught by a bare `except Exception: pass`, so two
   404s became an empty result reported as success.

The live record already carries the split, so one request replaces two:

    {"symbol": "BRCA1", "hgnc_id": "HGNC:1100",
     "diseases": [{"label": "BRCA1-related cancer predisposition",
                   "curie": "MONDO:..."}, ...],
     "adults": [...], "pediatrics": [...]}

Verified live 2026-08-03: 300 rows, exactly one matching BRCA1 on `symbol`, with
three associated diseases. Note the `?gene=` query parameter is ignored by the
API — it returns the whole list — so filtering stays client-side deliberately.
"""

import pytest

import tooluniverse.clingen_tool as mod
from tooluniverse.clingen_tool import ClinGenTool

CONFIG = {
    "name": "ClinGen_search_actionability",
    "parameter": {"properties": {"gene": {"type": "string"}}},
    "fields": {"operation": "search_actionability"},
}

# One row of the real payload, trimmed.
ROWS = [
    {"symbol": "ABCD1", "hgnc_id": "HGNC:61",
     "diseases": [{"label": "adrenoleukodystrophy", "curie": "MONDO:0018544"}],
     "adults": [None], "pediatrics": [{"score": 3}]},
    {"symbol": "BRCA1", "hgnc_id": "HGNC:1100",
     "diseases": [{"label": "BRCA1-related cancer predisposition",
                   "curie": "MONDO:0016419"}],
     "adults": [{"score": 12}], "pediatrics": [None]},
]


@pytest.fixture
def served(monkeypatch):
    """Serve the live payload shape, and record what was requested."""
    seen = {}

    class _Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"total": len(ROWS), "rows": ROWS, "nassert": 0, "npanels": 2}

    def _fake_get(url, headers=None, timeout=None, **kwargs):
        seen.setdefault("urls", []).append(url)
        return _Response()

    monkeypatch.setattr(mod.requests, "get", _fake_get)
    return seen


@pytest.mark.unit
def test_it_queries_the_search_api_not_the_dead_actionability_host(served):
    ClinGenTool(CONFIG).run({"gene": "BRCA1"})

    urls = served["urls"]
    assert urls, "no request was made"
    for url in urls:
        assert "actionability.clinicalgenome.org" not in url, (
            f"{url} is the retired host and answers 404"
        )
    assert any("search.clinicalgenome.org/api/actionability" in u for u in urls), urls


@pytest.mark.unit
def test_the_gene_is_matched_on_symbol(served):
    """`gene`/`Gene` matched nothing; the field is `symbol`."""
    result = ClinGenTool(CONFIG).run({"gene": "BRCA1"})

    assert result["status"] == "success", result
    found = result["data"]["Adult"] + result["data"]["Pediatric"]
    assert found, f"BRCA1 is curated by ClinGen but nothing matched: {result}"
    assert all(str(r.get("symbol", "")).upper() == "BRCA1" for r in found), found


@pytest.mark.unit
def test_a_gene_that_is_not_curated_is_still_empty(served):
    """The fix must not make everything match."""
    result = ClinGenTool(CONFIG).run({"gene": "NOTAGENE"})

    assert result["status"] == "success", result
    assert result["adult_count"] == 0 and result["pediatric_count"] == 0, result


@pytest.mark.unit
def test_a_dead_upstream_is_reported_rather_than_swallowed(monkeypatch):
    """A bare `except: pass` is what turned two 404s into a clean empty answer."""
    import requests as _rq

    def _fake_get(url, headers=None, timeout=None, **kwargs):
        raise _rq.RequestException("404 Client Error: Not Found")

    monkeypatch.setattr(mod.requests, "get", _fake_get)

    result = ClinGenTool(CONFIG).run({"gene": "BRCA1"})

    assert result["status"] == "error", (
        "an unreachable upstream must not be reported as an empty success"
    )


@pytest.mark.network
def test_the_real_api_curates_brca1():
    """The claim the unit tests cannot make: BRCA1 is in ClinGen actionability."""
    result = ClinGenTool(CONFIG).run({"gene": "BRCA1"})

    assert result["status"] == "success", result
    found = result["data"]["Adult"] + result["data"]["Pediatric"]
    assert found, f"expected BRCA1 curations, got {result}"
    diseases = str(found[0].get("diseases", "")).lower()
    assert "brca1" in diseases or "breast" in diseases, found[0]
