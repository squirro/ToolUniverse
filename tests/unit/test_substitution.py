"""Unit tests for unavailable-tool substitution (DSR-512)."""
import pytest

from tooluniverse.skill_conversion.registry_adapter import RegistryAdapter, ToolFact
from tooluniverse.skill_conversion.substitution import (
    Substitution,
    is_substitutable,
    substitute,
)

pytestmark = pytest.mark.unit


def _adapter(available_names):
    def probe(name):
        return {"exists": name in available_names,
                "signature": None}
    return RegistryAdapter(cluster="sr-dev", probe=probe, cache={})


def test_disgenet_substitutes_to_grounded_opentargets():
    fact = ToolFact(name="DisGeNET_search_gene", exists=False,
                    signature=None, available=False, quirk=None)
    adapter = _adapter({"OpenTargets_get_asso_targ_by_dise_efoI"})
    sub = substitute(fact, adapter)
    assert isinstance(sub, Substitution)
    assert "OpenTargets_get_asso_targ_by_dise_efoI" in sub.alternatives
    assert sub.escalate is False


def test_substitute_escalates_when_alternative_also_dead():
    fact = ToolFact(name="DisGeNET_search_gene", exists=False,
                    signature=None, available=False, quirk=None)
    adapter = _adapter(set())  # nothing available → no grounded alternative
    sub = substitute(fact, adapter)
    assert sub.alternatives == ()
    assert sub.escalate is True


def test_is_substitutable_only_for_seeded_families():
    assert is_substitutable("OMIM_search")
    assert is_substitutable("DisGeNET_search_gene")
    assert not is_substitutable("ClinVar_search_variants")


def test_disgenet_disease_direction_substitutes_to_opentargets():
    fact = ToolFact(name="DisGeNET_search_gene", exists=False,
                    signature=None, available=False, quirk=None)
    adapter = _adapter({"OpenTargets_get_asso_targ_by_dise_efoI"})
    sub = substitute(fact, adapter, direction="disease")
    assert "OpenTargets_get_asso_targ_by_dise_efoI" in sub.alternatives
    assert sub.escalate is False


def test_disgenet_target_direction_does_not_use_disease_to_target_tool():
    """A target-centric skill must NOT get the disease->target substitute (no efoId in hand)."""
    fact = ToolFact(name="DisGeNET_search_gene", exists=False,
                    signature=None, available=False, quirk=None)
    adapter = _adapter({"OpenTargets_get_asso_targ_by_dise_efoI"})
    sub = substitute(fact, adapter, direction="target")
    assert "OpenTargets_get_asso_targ_by_dise_efoI" not in sub.alternatives
