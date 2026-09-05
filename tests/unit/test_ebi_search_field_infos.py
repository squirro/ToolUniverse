"""EBI Search returns `domains[0].fieldInfos`; we looked for `fields`.

`ebi_get_domain_fields` fetched the right URL and returned `data: [], count: 0`.
The `fields` extraction path checked `data["fields"]` and
`data["domain"]["fields"]`, and the real payload is

    {"domains": [{"id": "ensembl_gene", "name": ..., "indexInfos": [...],
                  "fieldInfos": [{...}, ...]}]}

— `domains` plural, a LIST, and `fieldInfos` rather than `fields`. Verified live
2026-08-03: `ensembl_gene` carries 109 field descriptors.

Two separate faults had to be cleared for this tool to answer, which is why the
fixture alone was not enough:

* the audit's example asked the `ensembl` CONTAINER domain, which has no fields
  by construction — only `subdomains`. That is fixed by a fixture pointing at the
  leaf (`.scratch/tool-audit/fixtures/ebi_get_domain_fields.json`);
* and this extraction path, which would have returned nothing for any domain.
"""

import pytest

from tooluniverse.ebi_search_tool import EBISearchRESTTool

CONFIG = {
    "name": "ebi_get_domain_fields",
    "parameter": {"properties": {"domain": {"type": "string"}}},
    "fields": {"extract_path": "fields"},
}

# The real shape, trimmed to two descriptors.
PAYLOAD = {
    "domains": [{
        "id": "ensembl_gene",
        "name": "Ensembl Gene",
        "indexInfos": [{"name": "number of entries", "value": "2068"}],
        "fieldInfos": [
            {"id": "id", "name": "id", "description": "Gene identifier",
             "options": [{"name": "searchable", "value": "true"}]},
            {"id": "name", "name": "name", "description": "Gene name",
             "options": [{"name": "retrievable", "value": "true"}]},
        ],
    }]
}


@pytest.mark.unit
def test_field_descriptors_are_read_from_domains_field_infos():
    fields = EBISearchRESTTool(CONFIG)._extract_data(PAYLOAD, "fields")

    assert isinstance(fields, list), fields
    assert [f["id"] for f in fields] == ["id", "name"], fields


@pytest.mark.unit
def test_the_older_shapes_still_work():
    """Both documented fallbacks must keep working; this is additive."""
    tool = EBISearchRESTTool(CONFIG)

    assert tool._extract_data({"fields": [{"id": "a"}]}, "fields") == [{"id": "a"}]
    assert tool._extract_data(
        {"domain": {"fields": [{"id": "b"}]}}, "fields"
    ) == [{"id": "b"}]


@pytest.mark.unit
def test_a_container_domain_yields_nothing_rather_than_erroring():
    """`ensembl` really has no fields, and that must stay an empty answer."""
    container = {"domains": [{"id": "ensembl", "subdomains": [{"id": "ensembl_gene"}]}]}

    assert EBISearchRESTTool(CONFIG)._extract_data(container, "fields") == []


@pytest.mark.network
def test_the_real_leaf_domain_reports_its_fields():
    """The claim the unit tests cannot make: ensembl_gene has many fields."""
    result = EBISearchRESTTool(CONFIG).run({"domain": "ensembl_gene"})

    assert result["status"] == "success", result
    assert result["data"], f"expected field descriptors, got {result}"
    assert len(result["data"]) > 50, f"only {len(result['data'])} fields"
