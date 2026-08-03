"""BindingDB names the parameter `pdb`, and takes its ids comma-separated.

`getLigandsByPDBs` was being called with `pdbs=1TUP;2XYZ` -- plural, semicolons
-- and BindingDB answers **HTTP 500** to that, not a 400 or an empty result.
A 500 reads as "the service is broken", which is how this sat in the audit as an
upstream failure while the service was fine:

    pdbs=1TUP&cutoff=10000&response=application/json   -> 500
    pdb=1TUP&cutoff=10000&response=application/json    -> 200, real affinities
    pdb=1Q0L,3ANM&cutoff=100&response=application/json -> 200, real affinities

Verified live 2026-08-03. The cutoff value is irrelevant to the failure; only
the parameter name is.
"""

import pytest

import tooluniverse.bindingdb_tool as mod
from tooluniverse.bindingdb_tool import BindingDBTool

CONFIG = {"name": "BindingDB_get_ligands_by_pdb", "parameter": {"properties": {}}}


@pytest.fixture
def captured(monkeypatch):
    """Record the query BindingDB would actually receive."""
    seen = {}

    def _fake_get(endpoint, params, timeout=None):
        seen["endpoint"] = endpoint
        seen["params"] = params
        return {"getLindsByPDBsResponse": {"affinities": []}}

    monkeypatch.setattr(mod, "_http_get", _fake_get)
    return seen


@pytest.mark.unit
def test_the_parameter_is_pdb_not_pdbs(captured):
    BindingDBTool(CONFIG)._get_ligands_by_pdbs({"pdb_ids": "1TUP"})

    assert "pdb" in captured["params"], captured["params"]
    assert "pdbs" not in captured["params"], "BindingDB answers 500 to `pdbs`"


@pytest.mark.unit
def test_several_ids_are_comma_separated(captured):
    """Semicolons are what produced the 500."""
    BindingDBTool(CONFIG)._get_ligands_by_pdbs({"pdb_ids": "1Q0L,3ANM"})

    assert captured["params"]["pdb"] == "1Q0L,3ANM"
    assert ";" not in captured["params"]["pdb"]


@pytest.mark.unit
def test_a_list_of_ids_is_accepted_too(captured):
    BindingDBTool(CONFIG)._get_ligands_by_pdbs({"pdb_ids": ["1Q0L", "3ANM"]})

    assert captured["params"]["pdb"] == "1Q0L,3ANM"


@pytest.mark.network
def test_the_real_service_answers_the_query_we_build():
    """The claim the unit tests cannot make: this query returns affinities."""
    result = BindingDBTool(CONFIG)._get_ligands_by_pdbs({"pdb_ids": "1Q0L,3ANM"})

    assert result["status"] == "success", result
    assert result["data"]["affinities"], "expected affinity rows for 1Q0L/3ANM"
