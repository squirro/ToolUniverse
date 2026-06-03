"""Unit tests for the grounded, cache-first registry adapter (ADR-0006 / DSR-507).

Pure module — the live SMCP introspection is injected as `probe`, so every test
runs offline with a call-counting stub.
"""

import pytest

from tooluniverse.skill_conversion.registry_adapter import (
    RegistryAdapter,
    ToolFact,
    make_smcp_probe,
)

pytestmark = pytest.mark.unit


class CountingProbe:
    """A stub registry probe that records every tool it was asked to introspect."""

    def __init__(self, facts=None):
        # facts: {tool_name: {"exists": bool, "signature": dict|None}}
        self._facts = facts or {}
        self.calls = []

    def __call__(self, tool_name):
        self.calls.append(tool_name)
        return self._facts.get(tool_name, {"exists": False, "signature": None})


def test_cache_miss_probes_once_and_returns_toolfact():
    """A cache miss does exactly one live probe and returns a populated ToolFact."""
    probe = CountingProbe({"ClinVar_search_variants": {"exists": True,
                                                        "signature": {"gene": "string"}}})
    adapter = RegistryAdapter(cluster="sr-dev", probe=probe, cache={})

    fact = adapter.resolve("ClinVar_search_variants")

    assert isinstance(fact, ToolFact)
    assert fact.name == "ClinVar_search_variants"
    assert fact.exists is True
    assert fact.signature == {"gene": "string"}
    assert fact.available is True       # no unavailability seed → available
    assert fact.quirk is None           # no quirk seed for this tool
    assert probe.calls == ["ClinVar_search_variants"]  # probed exactly once


def test_cache_hit_skips_probe_and_miss_writes_back():
    """First resolve probes + writes back; the second is served from cache, no probe."""
    probe = CountingProbe({"ClinVar_search_variants": {"exists": True,
                                                       "signature": {"gene": "string"}}})
    adapter = RegistryAdapter(cluster="sr-dev", probe=probe, cache={})

    first = adapter.resolve("ClinVar_search_variants")
    second = adapter.resolve("ClinVar_search_variants")

    assert second == first
    assert probe.calls == ["ClinVar_search_variants"]  # probed only once, total


def test_cache_is_per_cluster():
    """The same tool resolved on two clusters does not collide: two probes, two entries."""
    probe = CountingProbe({"ClinVar_search_variants": {"exists": True, "signature": None}})
    shared_cache: dict = {}
    sr_dev = RegistryAdapter(cluster="sr-dev", probe=probe, cache=shared_cache)
    sempart = RegistryAdapter(cluster="sempart", probe=probe, cache=shared_cache)

    sr_dev.resolve("ClinVar_search_variants")
    sempart.resolve("ClinVar_search_variants")

    assert probe.calls == ["ClinVar_search_variants", "ClinVar_search_variants"]
    assert ("sr-dev", "ClinVar_search_variants") in shared_cache
    assert ("sempart", "ClinVar_search_variants") in shared_cache


def test_opentargets_efoid_quirk_is_seeded():
    """An OpenTargets efoId tool gets the underscore-not-colon quirk, on top of its probe."""
    probe = CountingProbe({"OpenTargets_get_asso_targ_by_dise_efoI":
                           {"exists": True, "signature": {"efoId": "string"}}})
    adapter = RegistryAdapter(cluster="sr-dev", probe=probe, cache={})

    fact = adapter.resolve("OpenTargets_get_asso_targ_by_dise_efoI")

    assert fact.exists is True
    assert fact.signature == {"efoId": "string"}
    assert fact.quirk is not None
    assert "underscore" in fact.quirk.lower()


def test_omim_and_disgenet_seeded_unavailable():
    """Key-gated tools (OMIM, DisGeNET) are seeded unavailable on this cluster."""
    probe = CountingProbe({
        "OMIM_search": {"exists": True, "signature": None},
        "DisGeNET_search_gene": {"exists": True, "signature": None},
    })
    adapter = RegistryAdapter(cluster="sr-dev", probe=probe, cache={})

    assert adapter.resolve("OMIM_search").available is False
    assert adapter.resolve("DisGeNET_search_gene").available is False
    # Short-circuit policy: a seeded-unavailable tool is NOT probed (the seed wins,
    # saving a live call on a tool the converter will drop/substitute anyway).
    assert probe.calls == []


def test_make_smcp_probe_maps_get_tool_info():
    """make_smcp_probe adapts a get_tool_info caller into the Probe contract."""
    def call(tool_name):
        catalog = {
            "ClinVar_search_variants": {
                "name": "ClinVar_search_variants",
                "parameter_schema": {"gene": {"type": "string"}},
            }
        }
        return catalog.get(tool_name, {"error": f"Tool '{tool_name}' not found."})

    probe = make_smcp_probe(call)

    assert probe("ClinVar_search_variants") == {
        "exists": True,
        "signature": {"gene": {"type": "string"}},
    }
    assert probe("No_Such_Tool") == {"exists": False, "signature": None}
