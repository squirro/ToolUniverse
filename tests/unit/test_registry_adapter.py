"""Unit tests for the grounded, cache-first registry adapter (ADR-0006 / DSR-507).

Pure module — the live SMCP introspection is injected as `probe`, so every test
runs offline with a call-counting stub.
"""

import pytest

from tooluniverse.skill_conversion.registry_adapter import (
    RegistryAdapter,
    ToolFact,
    default_unavailable,
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


def test_nonexistent_tool_is_not_available():
    """Invariant: available ⟹ exists. A probe miss yields exists=False AND available=False."""
    probe = CountingProbe({})  # unknown tools probe as {"exists": False, "signature": None}
    adapter = RegistryAdapter(cluster="sr-dev", probe=probe, cache={})

    fact = adapter.resolve("Ghost_tool")

    assert fact.exists is False
    assert fact.available is False


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
    """make_smcp_probe adapts a get_tool_info caller into the Probe contract.

    get_tool_info is a BATCH meta-tool: a found single-name request returns
    {"total_found": 1, "tools": [{"name","parameter"}]}; a NOT-FOUND name is not an
    error — it echoes a stub tool with that name but total_found=0. Existence keys on
    total_found + exact-name match, NOT on name presence (DSR-508, real sr-dev shape)."""
    def call(tool_name):
        catalog = {
            "ClinVar_search_variants": {
                "total_found": 1,
                "tools": [{"name": "ClinVar_search_variants",
                           "parameter": {"gene": {"type": "string"}}}],
            }
        }
        # the real not-found shape: total_found=0 with a name-echoing stub tool
        return catalog.get(tool_name, {"total_found": 0, "tools": [{"name": tool_name}]})

    probe = make_smcp_probe(call)

    assert probe("ClinVar_search_variants") == {
        "exists": True,
        "signature": {"gene": {"type": "string"}},
    }
    # the not-found stub echoes the name but total_found=0 → must be exists False
    assert probe("No_Such_Tool") == {"exists": False, "signature": None}


# ---------------------------------------------------------------------------
# Fix 1 — alias-resolution fallback for shortened tool names (DSR-509)
# ---------------------------------------------------------------------------

class CountingCall:
    """Stub for the raw get_tool_info caller injected into make_smcp_probe.

    Returns the batch shape {"total_found": N, "tools": [...]} keyed per tool name.
    Unknown names echo the SMCP not-found stub: total_found=0, tools=[{name: <echoed>}].
    """

    def __init__(self, catalog=None):
        # catalog: {tool_name: {"total_found": N, "tools": [...]}}
        self._catalog = catalog or {}
        self.calls = []

    def __call__(self, tool_name: str) -> dict:
        self.calls.append(tool_name)
        return self._catalog.get(
            tool_name,
            {"total_found": 0, "tools": [{"name": tool_name}]},
        )


def test_long_name_miss_then_shortened_hit():
    """A long full name that misses on exact probe HITS on the shortened name.

    The probe must:
    - issue the first call with the full name (which returns total_found=0 / stub)
    - detect the name is long enough to be shortened
    - issue a second call with the shortened name (which returns a real match)
    - return exists=True with the short tool's signature
    """
    full = "OpenTargets_get_associated_targets_by_disease_efoId"   # 51 chars
    short = "OpenTargets_get_asso_targ_by_dise_efoI"               # 38 chars
    expected_sig = {"efoId": {"type": "string"}}

    call_stub = CountingCall(
        catalog={
            short: {
                "total_found": 1,
                "tools": [{"name": short, "parameter": expected_sig}],
            }
        }
    )

    probe = make_smcp_probe(call_stub)
    result = probe(full)

    assert result == {"exists": True, "signature": expected_sig}
    assert call_stub.calls == [full, short], (
        "probe must issue exact call first, then shortened call on miss"
    )


def test_short_name_miss_no_second_call():
    """A short name (≤45 chars) that misses does NOT trigger a second call.

    shorten_tool_name is a no-op for names within the limit, so
    short == full and no extra call should be made.
    """
    short_name = "ClinVar_search_variants"   # 23 chars — already within 45

    call_stub = CountingCall()  # empty catalog → every name misses

    probe = make_smcp_probe(call_stub)
    result = probe(short_name)

    assert result == {"exists": False, "signature": None}
    assert call_stub.calls == [short_name], (
        "exactly one call on a short-name miss — no alias fallback"
    )


def test_exact_name_hit_only_one_call():
    """An exact-name HIT on the first try returns exists=True with one call only."""
    tool = "ClinVar_search_variants"
    sig = {"gene": {"type": "string"}}

    call_stub = CountingCall(
        catalog={
            tool: {
                "total_found": 1,
                "tools": [{"name": tool, "parameter": sig}],
            }
        }
    )

    probe = make_smcp_probe(call_stub)
    result = probe(tool)

    assert result == {"exists": True, "signature": sig}
    assert call_stub.calls == [tool], (
        "exact hit must not trigger a second alias-resolution call"
    )


# ---------------------------------------------------------------------------
# Fix 2 — ADMETAI registered-but-broken seed (DSR-509)
# ---------------------------------------------------------------------------

def test_admetai_seeded_unavailable():
    """ADMETAI tools are seeded unavailable: registered but broken (missing package)."""
    assert default_unavailable("ADMETAI_predict_BBB_penetrance") is True


def test_omim_disgenet_still_seeded_unavailable():
    """Regression: OMIM/DisGeNET unavailability seeds survive the ADMETAI addition."""
    assert default_unavailable("OMIM_search") is True
    assert default_unavailable("DisGeNET_search_gene") is True


def test_admetai_resolve_short_circuits_no_probe():
    """RegistryAdapter.resolve for ADMETAI must short-circuit to available=False with no probe call."""
    probe = CountingProbe({
        "ADMETAI_predict_BBB_penetrance": {"exists": True, "signature": {"smiles": "string"}},
    })
    adapter = RegistryAdapter(cluster="sr-dev", probe=probe, cache={})

    fact = adapter.resolve("ADMETAI_predict_BBB_penetrance")

    assert fact.available is False
    assert probe.calls == [], "seeded-unavailable tools must NOT be probed"
