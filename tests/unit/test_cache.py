"""Unit tests for the file-backed adapter cache (DSR-508)."""
import pytest

from tooluniverse.skill_conversion.cache import JsonFileCache
from tooluniverse.skill_conversion.registry_adapter import RegistryAdapter, ToolFact

pytestmark = pytest.mark.unit


def test_set_persists_across_instances_on_same_path(tmp_path):
    path = tmp_path / "facts.json"
    cache = JsonFileCache(path)
    fact = ToolFact(name="ClinVar_search_variants", exists=True,
                    signature={"gene": "string"}, available=True, quirk=None)
    cache[("sr-dev", "ClinVar_search_variants")] = fact

    reopened = JsonFileCache(path)
    assert reopened[("sr-dev", "ClinVar_search_variants")] == fact
    assert ("sr-dev", "ClinVar_search_variants") in reopened
    assert len(reopened) == 1


def test_adapter_uses_filecache_and_saturates_across_runs(tmp_path):
    """A second adapter on the same cache file serves a hit without re-probing."""
    path = tmp_path / "facts.json"
    facts = {"ClinVar_search_variants": {"exists": True, "signature": None}}

    def probe(name):
        probe.calls.append(name)
        return facts.get(name, {"exists": False, "signature": None})
    probe.calls = []

    first = RegistryAdapter(cluster="sr-dev", probe=probe, cache=JsonFileCache(path))
    first.resolve("ClinVar_search_variants")
    assert probe.calls == ["ClinVar_search_variants"]

    second = RegistryAdapter(cluster="sr-dev", probe=probe, cache=JsonFileCache(path))
    second.resolve("ClinVar_search_variants")
    assert probe.calls == ["ClinVar_search_variants"]  # no second probe — served from disk
