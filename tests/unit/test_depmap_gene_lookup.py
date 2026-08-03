"""DepMap searched 500 of 45,751 genes and called the rest "not in the catalog".

`DepMap_search_genes` reported

    {"query": "EGFR", "genes": [], "count": 0,
     "note": "Gene 'EGFR' not found in DepMap gene catalog"}

for a gene that is certainly in it. The method paged `sort=symbol` from page 1 to
page 5 at 100 per page and filtered client-side, so it only ever saw the first
500 symbols alphabetically — everything up to about "ABCD3". Any gene past that
was declared absent, which is a false statement about 98.9% of the catalog and
worse than an error, because it reads as an authoritative negative.

The Sanger API genuinely has no symbol filter — `filter[symbol]`,
`filter[symbol][eq]`, `filter[hgnc_symbol]`, `q` and `symbol` are all accepted
and silently ignored, returning an unfiltered default page (verified
2026-08-03) — so client-side matching is right. What was wrong is scanning
linearly from the start.

It does sort reliably, and `meta.count` reports 45,751 across 458 pages:

    page   1 -> A12M1     .. ABCD3
    page 150 -> KLHL25    .. KPNA3-IT1
    page 458 -> ZSCAN12P1 .. ZZZ3

so a binary search over the page space finds any symbol in ~9 requests instead
of 458.
"""

import pytest

import tooluniverse.depmap_tool as mod
from tooluniverse.depmap_tool import DepMapTool

CONFIG = {
    "name": "DepMap_search_genes",
    "parameter": {"properties": {"query": {"type": "string"}}},
    "fields": {"operation": "search_genes"},
}

# A stand-in catalogue, sorted, larger than the old 5-page window.
# 2,000 leading symbols, so EGFR sits at page 21 of 21 -- comfortably outside the
# old 5-page (500-symbol) window, the way it does in the real 458-page catalogue.
CATALOG = sorted(
    [f"A{i:04d}" for i in range(2000)] + ["EGFR", "EGFR-AS1", "TP53", "ZZZ3"]
)
PAGE_SIZE = 100


class _Response:
    status_code = 200

    def __init__(self, symbols, total):
        self._symbols = symbols
        self._total = total

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "data": [
                {"id": s, "attributes": {"symbol": s, "hgnc_id": f"HGNC:{i}"}}
                for i, s in enumerate(self._symbols)
            ],
            "meta": {"count": self._total},
        }


@pytest.fixture
def served(monkeypatch):
    """Serve CATALOG with the API's real sorted-pagination semantics."""
    calls = {"n": 0}

    def _fake_get(url, params=None, timeout=None, **kwargs):
        calls["n"] += 1
        params = params or {}
        size = int(params.get("page[size]", PAGE_SIZE))
        number = int(params.get("page[number]", 1))
        start = (number - 1) * size
        return _Response(CATALOG[start:start + size], len(CATALOG))

    monkeypatch.setattr(mod.requests, "get", _fake_get)
    return calls


@pytest.mark.unit
def test_a_gene_late_in_the_alphabet_is_found(served):
    """EGFR sits past the old 500-symbol window."""
    result = DepMapTool(CONFIG).run({"query": "EGFR"})

    assert result["status"] == "success", result
    symbols = [g.get("symbol") for g in result["data"]["genes"]]
    assert "EGFR" in symbols, (
        f"EGFR is in the catalogue at position {CATALOG.index('EGFR')} but was "
        f"not found: {result['data']}"
    )


@pytest.mark.unit
def test_the_last_gene_in_the_catalogue_is_found(served):
    result = DepMapTool(CONFIG).run({"query": "ZZZ3"})

    symbols = [g.get("symbol") for g in result["data"]["genes"]]
    assert "ZZZ3" in symbols, result["data"]


@pytest.mark.unit
def test_it_does_not_read_the_whole_catalogue_to_do_it(served):
    """A linear scan would work and be unusable; this must stay logarithmic."""
    DepMapTool(CONFIG).run({"query": "ZZZ3"})

    pages = len(CATALOG) // PAGE_SIZE + 1
    assert served["n"] < pages, (
        f"made {served['n']} requests for a {pages}-page catalogue; that is a scan"
    )


@pytest.mark.unit
def test_a_gene_that_really_is_absent_is_still_reported_absent(served):
    """The fix must not invent matches."""
    result = DepMapTool(CONFIG).run({"query": "NOTAREALGENE"})

    assert result["status"] == "success", result
    assert result["data"]["count"] == 0, result["data"]


@pytest.mark.network
def test_the_real_catalogue_contains_egfr():
    """The claim the unit tests cannot make: EGFR is in DepMap."""
    result = DepMapTool(CONFIG).run({"query": "EGFR"})

    assert result["status"] == "success", result
    symbols = [g.get("symbol") for g in result["data"]["genes"]]
    assert "EGFR" in symbols, result["data"]
