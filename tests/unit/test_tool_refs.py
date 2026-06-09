"""Unit tests for tool-ref extraction (DSR-508)."""
import pytest

from tooluniverse.skill_conversion.tool_refs import extract_tool_refs

pytestmark = pytest.mark.unit

SKILL_MD = """
Call `OpenTargets_get_asso_targ_by_dise_efoI`(efoId) then
`ClinVar_search_variants`(gene, condition). Lowercase tools exist too:
`gwas_get_variants_for_trait` and `civic_search_evidence_items`. Repeats like
`ClinVar_search_variants` should de-dup. Plain words and `inline_code` noise.
"""


def test_extracts_backtick_quoted_underscore_identifiers_in_order():
    refs = extract_tool_refs(SKILL_MD)
    assert refs[0] == "OpenTargets_get_asso_targ_by_dise_efoI"
    assert "ClinVar_search_variants" in refs
    assert "gwas_get_variants_for_trait" in refs
    assert "civic_search_evidence_items" in refs


def test_dedups_preserving_first_seen_order():
    refs = extract_tool_refs(SKILL_MD)
    assert refs.count("ClinVar_search_variants") == 1
