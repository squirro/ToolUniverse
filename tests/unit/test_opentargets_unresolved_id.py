"""An OpenTargets id that does not resolve must say so, not report success.

Eleven `OpenTargets_*_by_disease_efoId` tools answer

    {"status": "success", "data": {}}

for an id the platform cannot resolve. The agent reads "success, no results" and
concludes the disease genuinely has no associated targets, no synonyms, no
publications -- a confident wrong answer it has no way to question.

The upstream shape is `{"data": {"disease": null}}`; `remove_none_and_empty_values`
strips the null, leaving `{"data": {}}`. `execute_query` even documents the
intent --

    # disease not found = {"data": {}}. Callers distinguish empty results
    # from errors via status envelope.

-- but no caller ever did: `GraphQLTool.run` returns `status: success` whatever
comes back. This pins the missing half of that contract.

Observed live: EFO_0000384 (the value in these tools' own `test_examples`)
returns `disease: null`, while MONDO_0004975 returns 13,367 associated targets.
"""

import pytest

import tooluniverse.graphql_tool as graphql_tool
from tooluniverse.graphql_tool import OpentargetTool

DISEASE_QUERY = (
    "query q($efoId: String!) { disease(efoId: $efoId) { id name } }"
)


def _disease_tool():
    return OpentargetTool(
        {
            "name": "OpenTargets_get_disease_description_by_efoId",
            "type": "OpenTarget",
            "query_schema": DISEASE_QUERY,
            "parameter": {
                "type": "object",
                "properties": {"efoId": {"type": "string"}},
                "required": ["efoId"],
            },
        }
    )


@pytest.mark.unit
def test_unresolved_disease_id_is_an_error_not_an_empty_success(monkeypatch):
    """`{"data": {}}` from a disease query means the id did not resolve."""
    monkeypatch.setattr(graphql_tool, "execute_query", lambda *a, **k: {"data": {}})

    result = _disease_tool().run({"efoId": "EFO_0000384"})

    assert result["status"] == "error", (
        f"an unresolvable id was reported as success: {result}"
    )
    assert "EFO_0000384" in result["error"], (
        "the error must name the id that failed so the agent can correct it"
    )
    assert "MONDO" in result["error"], (
        "the error must point at the likely fix; OpenTargets keys many diseases "
        "by MONDO and plain EFO ids no longer resolve"
    )


@pytest.mark.unit
def test_a_resolved_disease_is_still_a_success(monkeypatch):
    """The guard must not swallow real results."""
    monkeypatch.setattr(
        graphql_tool,
        "execute_query",
        lambda *a, **k: {"data": {"disease": {"id": "MONDO_0004975",
                                             "name": "Alzheimer disease"}}},
    )

    result = _disease_tool().run({"efoId": "MONDO_0004975"})

    assert result["status"] == "success"
    assert result["data"]["disease"]["name"] == "Alzheimer disease"


@pytest.mark.unit
def test_non_disease_queries_are_left_alone(monkeypatch):
    """A target query returning empty is not the disease-resolution failure."""
    monkeypatch.setattr(graphql_tool, "execute_query", lambda *a, **k: {"data": {}})

    tool = OpentargetTool(
        {
            "name": "OpenTargets_target_info",
            "type": "OpenTarget",
            "query_schema": "query q($ensemblId: String!) "
                            "{ target(ensemblId: $ensemblId) { id } }",
            "parameter": {
                "type": "object",
                "properties": {"ensemblId": {"type": "string"}},
                "required": ["ensemblId"],
            },
        }
    )
    result = tool.run({"ensemblId": "ENSG00000141510"})

    assert result["status"] == "success"
