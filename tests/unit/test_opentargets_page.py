"""Open Targets serves association rows in pages; the disease-to-targets tool must be able to ask.

The response carries the full count, but the tool returned the source's default page and had
no parameter to ask for more, so the count was there and nothing could use it.
"""

import json
from pathlib import Path

import pytest

import tooluniverse.graphql_tool as mod
from tooluniverse.graphql_tool import OpentargetTool

pytestmark = pytest.mark.unit

CONFIGS = json.loads((Path(mod.__file__).parent / "data" / "opentarget_tools.json").read_text())
CONFIG = next(t for t in CONFIGS if t["name"] == "OpenTargets_get_associated_targets_by_disease_efoId")


@pytest.fixture
def sent(monkeypatch):
    seen = {}

    def execute_query(endpoint_url, query, variables=None):
        seen["query"], seen["variables"] = query, dict(variables or {})
        return {"data": {"disease": {"id": variables["efoId"], "associatedTargets": {
            "count": 13367, "rows": [{"target": {"id": "ENSG1", "approvedSymbol": "APOE"}, "score": 0.9}]}}}}

    monkeypatch.setattr(mod, "execute_query", execute_query)
    return seen


def test_size_and_index_travel_in_the_querys_page_argument(sent):
    out = OpentargetTool(CONFIG).run({"efoId": "MONDO_0004975", "size": 500, "index": 2})

    assert "page: {index: $index, size: $size}" in sent["query"].replace("  ", " ")
    assert sent["variables"] == {"efoId": "MONDO_0004975", "size": 500, "index": 2}
    assert out["data"]["disease"]["associatedTargets"]["count"] == 13367, "the caller sees how much exists"


def test_without_the_parameters_the_sources_default_page_is_asked_for():
    """Open Targets pages 25 rows by default; the tool's defaults must not change that."""
    seen = {}

    def execute_query(endpoint_url, query, variables=None):
        seen.update(variables or {})
        return {"data": {}}

    import tooluniverse.graphql_tool as g
    original = g.execute_query
    g.execute_query = execute_query
    try:
        OpentargetTool(CONFIG).run({"efoId": "MONDO_0004975"})
    finally:
        g.execute_query = original

    assert seen == {"efoId": "MONDO_0004975", "size": 25, "index": 0}


def test_the_schema_declares_the_two_parameters_with_the_sources_defaults():
    properties = CONFIG["parameter"]["properties"]

    assert properties["size"]["default"] == 25 and properties["index"]["default"] == 0
    assert "13" not in properties["size"]["description"], "no measured number leaks into the schema"


DISEASES = next(t for t in CONFIGS if t["name"] == "OpenTargets_get_diseases_phenotypes_by_target_ensembl")


def test_the_diseases_by_target_tool_pages_too_and_carries_the_association_score():
    """The tool answered one default page with per-source scores and no overall score, so a
    process could neither reach the disease it was asked about nor grade it."""
    seen = {}

    def execute_query(endpoint_url, query, variables=None):
        seen["query"], seen["variables"] = query, dict(variables or {})
        return {"data": {"target": {"associatedDiseases": {"count": 461, "rows": []}}}}

    import tooluniverse.graphql_tool as g
    original = g.execute_query
    g.execute_query = execute_query
    try:
        OpentargetTool(DISEASES).run({"ensemblId": "ENSG00000110195", "size": 500})
    finally:
        g.execute_query = original

    assert "associatedDiseases(page: {index: $index, size: $size})" in seen["query"].replace("  ", " ")
    assert seen["variables"] == {"ensemblId": "ENSG00000110195", "size": 500, "index": 0}
    rows_block = seen["query"].split("rows {", 1)[1]
    assert "score" in rows_block.split("datasourceScores")[0], "the overall association score is asked for"
    assert DISEASES["parameter"]["properties"]["size"]["default"] == 25


def test_every_field_the_associations_step_collects_is_declared_in_the_return_schema():
    """The drug-target process collects each row's overall `score` and bands it; a field the
    schema does not declare is one the description promises and the contract does not."""
    import yaml
    graph = yaml.safe_load((Path(mod.__file__).parent / "data" / "skill_graphs"
                            / "drug-target-validation.yaml").read_text())
    step = next(s for s in graph["steps"] if s["id"] == "associations")
    collected = step["collect"]["disease_rows"]
    schema = DISEASES["return_schema"]
    for part in collected["path"].split("."):
        schema = schema["properties"][part]
    row = schema["items"]

    for field in collected["fields"]:
        node = row
        for part in field.split(" as ")[0].split("."):
            assert part in node.get("properties", {}), (field, sorted(node.get("properties", {})))
            node = node["properties"][part]
    assert row["properties"]["score"]["type"] == "number"


def test_the_already_paged_similar_entity_tools_keep_their_default_size():
    """`GraphQLTool.run` fills `size` for any tool that declares it; those tools got 5 and must still."""
    similar = next(t for t in CONFIGS if t["name"] == "OpenTargets_get_similar_entities_by_disease_efoId")
    seen = {}

    def execute_query(endpoint_url, query, variables=None):
        seen.update(variables or {})
        return {"data": {}}

    import tooluniverse.graphql_tool as g
    original = g.execute_query
    g.execute_query = execute_query
    try:
        OpentargetTool(similar).run({"efoId": "MONDO_0004975"})
    finally:
        g.execute_query = original

    assert seen["size"] == similar["parameter"]["properties"]["size"].get("default", 5)
