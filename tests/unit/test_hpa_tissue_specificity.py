""""No tissue-specific expression" is a finding, not an absence of data.

HPA populates `RNA tissue specific nTPM` only for genes that are *enriched* in
particular tissues. For a ubiquitously-expressed gene the field is null — which
is a real biological answer, not a gap. The tool reported it as

    "No RNA tissue expression data available for this gene"

which reads as "HPA knows nothing about this gene" and sends the caller looking
for another source. The audit probed TP53, about as ubiquitous as a gene gets,
and booked the tool as broken.

It is not broken: ALB (liver), INS (pancreas) and SSTR2 — Torpedo's target —
all return data through the same path. Only the message and the declared
example needed fixing.
"""

import json

import pytest

from tooluniverse.hpa_tool import HPAGetRnaExpressionByTissueTool

CONFIG = {"name": "HPA_get_rna_expression_in_specific_tissues",
          "parameter": {"properties": {}}}


def _tool(payload, monkeypatch):
    tool = HPAGetRnaExpressionByTissueTool(CONFIG)
    monkeypatch.setattr(tool, "_make_api_request", lambda *a, **k: payload)
    return tool


@pytest.mark.unit
def test_a_ubiquitous_gene_is_told_apart_from_a_missing_one(monkeypatch):
    """The gene was found; it simply has no tissue-enriched expression."""
    tool = _tool({"Gene": "TP53", "RNA tissue specific nTPM": None}, monkeypatch)

    result = tool.run({"ensembl_id": "ENSG00000141510", "tissue_names": ["liver"]})

    message = json.dumps(result).lower()
    assert "specific" in message or "enrich" in message, result
    assert "no rna tissue expression data available" not in message, (
        "reads as 'HPA has nothing for this gene', which is false — it means the "
        "gene is not tissue-enriched"
    )


@pytest.mark.unit
def test_a_tissue_enriched_gene_still_returns_its_values(monkeypatch):
    """The working path must survive the message change."""
    tool = _tool(
        {"Gene": "ALB", "RNA tissue specific nTPM": {"liver": 12345.6}}, monkeypatch
    )

    result = tool.run({"ensembl_id": "ENSG00000163631", "tissue_names": ["liver"]})

    assert result["status"] == "success", result


@pytest.mark.network
def test_the_declared_example_returns_data():
    """The example must exercise the tool: a tissue-enriched gene, not TP53."""
    import os

    data = os.path.join(os.path.dirname(__file__), "..", "..",
                        "src", "tooluniverse", "data", "hpa_tools.json")
    spec = next(t for t in json.load(open(data)) if t.get("name") == CONFIG["name"])
    example = (spec.get("test_examples") or [None])[0]
    assert example, "the tool declares no example"

    # the real definition, not a stub: `fields.endpoint` is what makes the call
    result = HPAGetRnaExpressionByTissueTool(spec).run(example)
    assert result.get("status") == "success", result
