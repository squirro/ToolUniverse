"""Regression tests for ChEMBL target resolution by gene symbol / UniProt accession.

Background (DSR-627). A live agent asked for chemical starting points against CCKBR and
made 13 consecutive failing `ChEMBL_search_targets` calls before the turn died with a
user-visible error. Root cause: the tool exposed only `pref_name__contains`, and ChEMBL's
`pref_name` for that target is "Gastrin/cholecystokinin type B receptor" -- it never
contains the gene symbol. The query returned zero rows rather than an error, so the agent
could not diagnose it and simply retried with more synonyms.

These tests pin the two query fields that *do* resolve a gene symbol, so the schema cannot
silently regress to a name-only search again.

The schema tests are offline and always run. The network tests hit the public ChEMBL REST
API and are marked so they can be deselected: `pytest -m "not network"` (the default).
"""

import json
from pathlib import Path

import pytest

CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data/target.json"

# CCKBR -- the target that triggered the original failure.
CCKBR_SYMBOL = "CCKBR"
CCKBR_UNIPROT = "P32239"
CCKBR_CHEMBL_ID = "CHEMBL298"

DATA_FILE = (
    Path(__file__).resolve().parents[2]  # tests/unit/<file> -> repo root
    / "src"
    / "tooluniverse"
    / "data"
    / "chembl_tools.json"
)


def _search_targets_schema() -> dict:
    payload = json.loads(DATA_FILE.read_text())
    tools = payload if isinstance(payload, list) else payload.get("tools", [])
    for tool in tools:
        if tool.get("name") == "ChEMBL_search_targets":
            return tool
    raise AssertionError("ChEMBL_search_targets missing from chembl_tools.json")


# --------------------------------------------------------------------------- schema


def test_gene_symbol_and_uniprot_params_are_exposed():
    """The two fields that can resolve a gene symbol must exist in the schema."""
    props = _search_targets_schema()["parameter"]["properties"]
    assert "target_synonym__icontains" in props, (
        "gene-symbol lookup field missing -- a symbol like CCKBR becomes unresolvable"
    )
    assert "target_components__accession" in props, (
        "UniProt accession lookup field missing"
    )


def test_pref_name_documents_that_it_does_not_match_gene_symbols():
    """The zero-result behaviour is silent, so it has to be documented in the schema.

    This is what stops an agent retrying a query that can never succeed.
    """
    props = _search_targets_schema()["parameter"]["properties"]
    text = props["pref_name__contains"]["description"].lower()
    assert "gene symbol" in text
    assert "not" in text


def test_tool_description_states_the_resolution_order():
    description = _search_targets_schema()["description"].lower()
    assert "target_synonym__icontains" in description
    assert "target_components__accession" in description


def test_wrapper_signature_forwards_the_new_params():
    """The typed wrapper must forward the new fields, not silently drop them."""
    from tooluniverse.tools.ChEMBL_search_targets import ChEMBL_search_targets

    import inspect

    params = inspect.signature(ChEMBL_search_targets).parameters
    assert "target_synonym__icontains" in params
    assert "target_components__accession" in params


# ----------------------------------------------------------------------------- live


@pytest.mark.network
def test_gene_symbol_resolves_to_the_right_chembl_target():
    """CCKBR -> CHEMBL298 via the synonym field. This is the exact case that failed."""
    import requests

    resp = requests.get(
        CHEMBL_API,
        params={"target_synonym__icontains": CCKBR_SYMBOL, "limit": 20},
        timeout=30,
    )
    resp.raise_for_status()
    ids = {t["target_chembl_id"] for t in resp.json().get("targets", [])}
    assert CCKBR_CHEMBL_ID in ids, f"expected {CCKBR_CHEMBL_ID}, got {sorted(ids)}"


@pytest.mark.network
def test_uniprot_accession_resolves_to_the_right_chembl_target():
    import requests

    resp = requests.get(
        CHEMBL_API,
        params={"target_components__accession": CCKBR_UNIPROT, "limit": 20},
        timeout=30,
    )
    resp.raise_for_status()
    ids = {t["target_chembl_id"] for t in resp.json().get("targets", [])}
    assert CCKBR_CHEMBL_ID in ids, f"expected {CCKBR_CHEMBL_ID}, got {sorted(ids)}"


@pytest.mark.network
def test_pref_name_search_still_returns_nothing_for_a_gene_symbol():
    """Pins the upstream behaviour the fix works around.

    If this ever starts returning rows, ChEMBL changed its data model and the guidance in
    the tool description should be revisited.
    """
    import requests

    resp = requests.get(
        CHEMBL_API,
        params={"pref_name__contains": CCKBR_SYMBOL, "limit": 20},
        timeout=30,
    )
    resp.raise_for_status()
    assert resp.json().get("targets") == [], (
        "ChEMBL now matches gene symbols in pref_name -- revisit the tool description"
    )
