"""GDC_get_cnv_data advertised a gene filter and silently ignored it.

The schema declares `gene_symbol` — "Optional: Gene symbol to focus analysis" —
and `GDCCNVTool.run` never referenced it. The filter it built used only
`project_id` and `data_type`, so asking for PTEN in TCGA-PRAD returned **3,005
unfiltered file records** (`.seg.txt`, `gene_level_copy_number.tsv`) with nothing
to indicate the gene had been dropped. A caller cannot tell a focused answer from
an unfocused one.

It could not have worked against `/files` in any case: a copy-number file covers
the whole genome, so there is no per-gene file to select. The gene filter belongs
to a different endpoint.

`/cnv_occurrences` does support it. Measured against GDC 2026-08-03:

    filters = cnv.consequence.gene.symbol=PTEN AND cases.project.project_id=TCGA-PRAD
    -> total 159   (Loss 151, Gain 8)

which is the deletion half of the cohort-alteration question DSR-629 asks for —
`cBioPortal` reports the same locus as 95 deep + 64 shallow deletions of 492, and
GDC's "Loss" merges those two buckets (95+64 = 159).

So the fix routes a gene-qualified request to `/cnv_occurrences` and leaves the
un-qualified file listing exactly as it was.
"""

import json

import pytest

import tooluniverse.gdc_tool as mod
from tooluniverse.gdc_tool import GDCCNVTool

CONFIG = {"name": "GDC_get_cnv_data", "parameter": {"properties": {}}}


@pytest.fixture
def captured(monkeypatch):
    """Record the URL GDC would actually receive (the tool uses urllib, not requests)."""
    seen = {}

    def _fake_http_get(url, headers=None, timeout=None, **kw):
        seen["url"] = url
        return {"hits": [], "pagination": {"total": 0}}

    monkeypatch.setattr(mod, "_http_get", _fake_http_get)
    return seen


def _filter_fields(seen):
    """Every `field` named anywhere in the outgoing filter tree."""
    from urllib.parse import parse_qs, urlparse

    raw = parse_qs(urlparse(seen["url"]).query).get("filters", [""])[0]
    found = []

    def walk(node):
        if isinstance(node, dict):
            content = node.get("content")
            if isinstance(content, dict) and "field" in content:
                found.append(content["field"])
            walk(content)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(json.loads(raw) if raw else {})
    return found


@pytest.mark.unit
def test_a_gene_symbol_actually_reaches_the_query(captured):
    """It was accepted and dropped; 3,005 unfiltered files came back."""
    GDCCNVTool(CONFIG).run({"project_id": "TCGA-PRAD", "gene_symbol": "PTEN"})

    fields = _filter_fields(captured)
    assert any("gene.symbol" in f for f in fields), (
        f"gene_symbol never reached the filter; fields were {fields}"
    )
    assert any("project_id" in f for f in fields), fields


@pytest.mark.unit
def test_a_gene_qualified_request_uses_the_endpoint_that_supports_it(captured):
    """/files cannot filter by gene — a CNV file covers the whole genome."""
    GDCCNVTool(CONFIG).run({"project_id": "TCGA-PRAD", "gene_symbol": "PTEN"})

    assert "cnv_occurrences" in captured["url"], captured["url"]


@pytest.mark.unit
def test_without_a_gene_the_file_listing_is_unchanged(captured):
    """The existing behaviour must survive: no gene, same /files query."""
    GDCCNVTool(CONFIG).run({"project_id": "TCGA-PRAD"})

    assert "/files" in captured["url"], captured["url"]
    fields = _filter_fields(captured)
    assert not any("gene.symbol" in f for f in fields), fields


@pytest.mark.unit
def test_project_id_is_still_required(captured):
    result = GDCCNVTool(CONFIG).run({"gene_symbol": "PTEN"})

    assert result["status"] == "error", result


@pytest.mark.network
def test_the_real_cohort_returns_the_deletion_split():
    """The claim the unit tests cannot make: PTEN is deleted in TCGA prostate."""
    result = GDCCNVTool(CONFIG).run({"project_id": "TCGA-PRAD",
                                     "gene_symbol": "PTEN", "size": 400})

    assert result["status"] == "success", result
    assert result.get("total", 0) > 100, result
    changes = result.get("cnv_change_counts") or {}
    assert changes.get("Loss", 0) > 100, changes
