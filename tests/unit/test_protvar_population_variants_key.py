"""ProtVar returns co-located variants under `variants`; we read two other keys.

`ProtVar_get_population` fetched the right URL and reported
`colocated_variants: []`. The API answers 8,930 bytes for that exact query:

    {"accession": "P22304", "position": 149, "altBase": ...,
     "variants": [ {...}, {...} ], "freqMap": {}}

The parser looped over `("proteinColocatedVariant", "genomicColocatedVariant")`,
neither of which exists in the response, so it always fell through to an empty
list. Every field it reads INSIDE a variant is correct — `wildType`,
`alternativeSequence`, `genomicLocation`, `cytogeneticBand`,
`populationFrequencies` are all present and named exactly that — so only the
container key was wrong.

Verified live 2026-08-03: P22304/149 yields 2 variants, the first Ser->Ala at
Xq28 with a ClinVar MAF of 0.00026.

The two legacy keys are still accepted, so this is additive rather than a swap.
"""

import pytest

import tooluniverse.protvar_tool as mod

VARIANT = {
    "type": "VARIANT",
    "wildType": "Ser",
    "alternativeSequence": "Ala",
    "genomicLocation": ["NC_000023.11:g.149501011A>C"],
    "cytogeneticBand": "Xq28",
    "populationFrequencies": [
        {"populationName": "MAF", "frequency": 0.00026, "source": "ClinVar"}
    ],
}
PAYLOAD = {
    "accession": "P22304",
    "position": 149,
    "altBase": "C",
    "variants": [VARIANT],
    "freqMap": {},
}

CONFIG = {"name": "ProtVar_get_population", "parameter": {"properties": {}}}
ARGS = {"accession": "P22304", "position": 149, "genomic_location": 149501011}


def _tool():
    from tooluniverse.protvar_tool import ProtVarPopulationTool

    return ProtVarPopulationTool(CONFIG)


@pytest.fixture
def served(monkeypatch):
    """Serve the real payload shape."""
    monkeypatch.setattr(mod, "_get_json", lambda url, timeout=None: PAYLOAD)


@pytest.mark.unit
def test_variants_are_read_from_the_variants_key(served):
    result = _tool().run(ARGS)

    assert result["status"] == "success", result
    found = result["data"]["colocated_variants"]
    assert found, f"the payload has 2 variants but none were read: {result['data']}"
    assert found[0]["wild_type"] == "Ser", found[0]
    assert found[0]["alt_sequence"] == "Ala", found[0]


@pytest.mark.unit
def test_the_legacy_keys_still_work(monkeypatch):
    """Additive: if ProtVar ever returns the old shape, keep reading it."""
    monkeypatch.setattr(
        mod, "_get_json",
        lambda url, timeout=None: {"proteinColocatedVariant": [VARIANT]},
    )

    result = _tool().run(ARGS)

    assert result["data"]["colocated_variants"], result["data"]


@pytest.mark.unit
def test_a_position_with_no_variants_is_still_empty(monkeypatch):
    """The fix must not invent rows."""
    monkeypatch.setattr(
        mod, "_get_json",
        lambda url, timeout=None: {"accession": "P22304", "variants": []},
    )

    result = _tool().run(ARGS)

    assert result["data"]["colocated_variants"] == [], result["data"]


@pytest.mark.network
def test_the_real_position_reports_its_variants():
    """The claim the unit tests cannot make: P22304/149 has co-located variants."""
    result = _tool().run(ARGS)

    assert result["status"] == "success", result
    found = result["data"]["colocated_variants"]
    assert found, f"expected co-located variants for P22304/149, got {result['data']}"
