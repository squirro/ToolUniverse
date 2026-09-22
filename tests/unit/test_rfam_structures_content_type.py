"""Rfam's /structures route reads `content-type` as a query param, not a header.

`_get_structure_mapping` asked for JSON with an `Accept: application/json`
header, the way `_get_family` does. `/family/{id}` honours either form, but
`/family/{id}/structures` honours ONLY the query parameter and answers **HTTP
500** with an HTML error page to the header form:

    /family/RF00002/structures            Accept header  -> 500, text/html
    /family/RF00002/structures?content-type=application/json -> 200, 149 KB of mapping
    /family/RF00002                       either form    -> 200, JSON

That asymmetry is why two near-identical methods in the same module behaved
differently, and why a 500 made this look like a withdrawn endpoint. Verified
live 2026-08-03: the route returns the PDB mapping the tool exists to fetch
({"mapping": [{"pdb_id": "6y6x", "chain": "L8", ...}]}).
"""

import pytest

import tooluniverse.rfam_tool as mod
from tooluniverse.rfam_tool import RfamTool

CONFIG = {"name": "Rfam_get_structure_mapping", "parameter": {"properties": {}}}


class _Response:
    status_code = 200
    headers = {"content-type": "application/json"}
    text = "{}"

    def json(self):
        return {"mapping": [{"pdb_id": "6y6x", "chain": "L8"}]}


@pytest.fixture
def captured(monkeypatch):
    """Record what Rfam would actually receive."""
    seen = {}

    def _fake_get(url, headers=None, params=None, timeout=None, **kwargs):
        seen["url"] = url
        seen["headers"] = headers or {}
        seen["params"] = params or {}
        return _Response()

    monkeypatch.setattr(mod.requests, "get", _fake_get)
    return seen


@pytest.mark.unit
def test_json_is_requested_by_query_param(captured):
    """The Accept header alone gets a 500 from this route."""
    RfamTool(CONFIG).run(
        {"operation": "get_structure_mapping", "family_id": "RF00002", "format": "json"}
    )

    assert captured["params"].get("content-type") == "application/json", (
        f"params were {captured['params']!r}; /structures ignores the Accept "
        "header and 500s without the content-type query parameter"
    )


@pytest.mark.unit
def test_the_xml_format_is_asked_for_the_same_way(captured):
    RfamTool(CONFIG).run(
        {"operation": "get_structure_mapping", "family_id": "RF00002", "format": "xml"}
    )

    assert captured["params"].get("content-type") == "text/xml", captured["params"]


@pytest.mark.network
def test_the_real_route_returns_the_pdb_mapping():
    """The claim the unit tests cannot make: this query returns the mapping."""
    result = RfamTool(CONFIG).run(
        {"operation": "get_structure_mapping", "family_id": "RF00002", "format": "json"}
    )

    assert result["status"] == "success", result
    assert result["data"]["mapping"], "expected PDB mapping rows for RF00002"
    assert result["data"]["mapping"][0]["pdb_id"], result["data"]["mapping"][0]


@pytest.mark.network
def test_the_sibling_family_route_still_works():
    """`/family/{id}` was never affected; the fix must not disturb it."""
    result = RfamTool({"name": "Rfam_get_family", "parameter": {"properties": {}}}).run(
        {"operation": "get_family", "family_id": "RF00002", "format": "json"}
    )

    assert result["status"] == "success", result
    assert result["data"]["rfam"]["acc"] == "RF00002", result["data"]
