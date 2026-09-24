"""DepMap_get_gene_dependencies answered with no numbers.

It looked the symbol up in the gene catalogue and returned the catalogue row and a note
about what gene-effect scores mean, never the scores. PCNA, essential in every line,
got the same number-free answer as FOLR1, so "no numbers" read as "no dependency".

The numbers are in the Cell Model Passports API: `/genes/{id}/datasets/crispr_ko`
(one row per screened line, Sanger and Broad) and `/genes/{id}/essentiality_profiles`
(the common-essential flag). The fixtures are those two responses, recorded live on
2026-09-24 with `page[size]=2000`, unedited: PCNA (common-essential), FOLR1 (the gene
of the failing run) and A12M1 (not in the CRISPR library, zero rows).
"""

import json
from pathlib import Path

import pytest

import tooluniverse.depmap_tool as mod
from tooluniverse.depmap_tool import DepMapTool

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "depmap"
DATE = "2026-09-24"
GENES = {
    "PCNA": ("SIDG24143", "HGNC:8729"),
    "FOLR1": ("SIDG09258", "HGNC:3791"),
    "A12M1": ("SIDG00013", None),
}
CONFIG = {"name": "DepMap_get_gene_dependencies",
          "fields": {"operation": "get_gene_dependencies"}}


def _recorded(symbol, endpoint):
    gid = GENES[symbol][0]
    return (FIXTURES / f"{symbol.lower()}_{gid}_{endpoint}_{DATE}.json").read_text()


class _Response:
    status_code = 200

    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def served(monkeypatch):
    """Serve the recorded payloads by URL; the catalogue lookup is tested elsewhere."""
    requested = []
    by_id = {gid: sym for sym, (gid, _) in GENES.items()}

    def _fake_get(url, params=None, timeout=None, **kwargs):
        requested.append((url, dict(params or {})))
        for gid, sym in by_id.items():
            if url.endswith(f"/genes/{gid}/datasets/crispr_ko"):
                return _Response(_recorded(sym, "crispr_ko"))
            if url.endswith(f"/genes/{gid}/essentiality_profiles"):
                return _Response(_recorded(sym, "essentiality_profiles"))
        raise AssertionError(f"unexpected request {url} {params}")

    def _fake_search(self, arguments):
        sym = arguments["query"]
        gid, hgnc = GENES[sym]
        return {"status": "success", "data": {"genes": [
            {"gene_id": gid, "symbol": sym, "hgnc_id": hgnc, "exact_match": True}]}}

    monkeypatch.setattr(mod.requests, "get", _fake_get)
    monkeypatch.setattr(DepMapTool, "_search_genes", _fake_search)
    return requested


@pytest.mark.unit
def test_a_common_essential_gene_comes_back_with_numbers(served):
    result = DepMapTool(CONFIG).run({"gene_symbol": "PCNA"})

    assert result["status"] == "success", result
    data = result["data"]
    assert data["screens_total"] == 1269, data
    assert data["screens_held"] == 1269, data
    assert data["common_essential"] is True, data
    assert data["dependent_screens"] > 1250, data
    assert data["median_bf_scaled"] < -15, data
    assert data["median_fc_clean_qn"] < -2, data
    by_source = {s["source"]: s for s in data["by_source"]}
    assert set(by_source) == {"Sanger", "Broad"}, data["by_source"]
    assert by_source["Sanger"]["screens"] == 512
    assert by_source["Broad"]["screens"] == 757
    most = data["most_dependent"]
    assert most and most[0]["bf_scaled"] <= most[-1]["bf_scaled"], most
    assert most[0]["model_id"].startswith("SIDM"), most[0]


@pytest.mark.unit
def test_a_non_dependent_gene_says_so_with_numbers(served):
    """FOLR1 is not a dependency, and the answer now carries the numbers that show it."""
    result = DepMapTool(CONFIG).run({"gene_symbol": "FOLR1"})

    assert result["status"] == "success", result
    data = result["data"]
    assert data["screens_total"] == 1269, data
    assert data["common_essential"] is False, data
    assert data["dependent_screens"] <= 2, data
    assert data["median_bf_scaled"] > 3, data


@pytest.mark.unit
def test_the_answer_names_its_source_so_it_can_be_cited(served):
    data = DepMapTool(CONFIG).run({"gene_symbol": "PCNA"})["data"]

    assert data["gene_id"] == "SIDG24143"
    assert data["source_url"].endswith("/genes/SIDG24143/datasets/crispr_ko"), data
    assert "negative" in data["note"], data["note"]


@pytest.mark.unit
def test_the_capped_list_of_lines_says_it_is_capped(served):
    data = DepMapTool(CONFIG).run({"gene_symbol": "PCNA"})["data"]

    assert len(data["most_dependent"]) < data["screens_held"]
    assert data["most_dependent_truncated"] is True, data


@pytest.mark.unit
def test_a_model_id_narrows_the_rows_to_that_line(served):
    rows = json.loads(_recorded("PCNA", "crispr_ko"))["data"]
    model = rows[0]["relationships"]["model"]["data"]["id"]
    expected = [r for r in rows if r["relationships"]["model"]["data"]["id"] == model]

    data = DepMapTool(CONFIG).run({"gene_symbol": "PCNA", "model_id": model})["data"]

    assert data["model_id"] == model
    assert data["screens_held"] == len(expected), data
    assert {s["model_id"] for s in data["most_dependent"]} == {model}


@pytest.mark.unit
def test_a_gene_with_no_screen_rows_is_an_error_not_an_empty_success(served):
    """A12M1 is in the catalogue but not in the CRISPR library: DepMap has zero rows."""
    result = DepMapTool(CONFIG).run({"gene_symbol": "A12M1"})

    assert result["status"] == "error", result
    assert "no CRISPR" in result["error"], result
    assert "A12M1" in result["error"]


@pytest.mark.unit
def test_a_gene_not_in_the_catalogue_is_an_error_not_an_empty_success(monkeypatch):
    def _nothing(self, arguments):
        return {"status": "success", "data": {"genes": [], "count": 0}}

    monkeypatch.setattr(DepMapTool, "_search_genes", _nothing)

    result = DepMapTool(CONFIG).run({"gene_symbol": "NOTAREALGENE"})

    assert result["status"] == "error", result
    assert "NOTAREALGENE" in result["error"]


@pytest.mark.unit
def test_an_unreachable_source_is_marked_retryable(monkeypatch):
    """So the process runner records a failed call, not a gene with no dependency."""
    def _found(self, arguments):
        return {"status": "success", "data": {"genes": [
            {"gene_id": "SIDG24143", "symbol": "PCNA", "exact_match": True}]}}

    def _down(url, params=None, timeout=None, **kwargs):
        raise mod.requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr(DepMapTool, "_search_genes", _found)
    monkeypatch.setattr(mod.requests, "get", _down)

    result = DepMapTool(CONFIG).run({"gene_symbol": "PCNA"})

    assert result["status"] == "error", result
    assert result.get("retryable") is True, result


@pytest.mark.network
def test_the_live_api_returns_numbers_for_pcna():
    result = DepMapTool(CONFIG).run({"gene_symbol": "PCNA"})

    assert result["status"] == "success", result
    assert result["data"]["median_bf_scaled"] < -10, result["data"]
