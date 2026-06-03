"""Unit tests for converter-prompt assembly (DSR-508)."""
import pytest

from tooluniverse.skill_conversion.prompt import (
    TRANSFORM_CHECKLIST,
    build_converter_prompt,
    render_grounded_facts,
)
from tooluniverse.skill_conversion.registry_adapter import ToolFact
from tooluniverse.skill_conversion.substitution import Substitution

pytestmark = pytest.mark.unit


def test_render_grounded_facts_lists_available_and_substitutions():
    available = [
        ToolFact(name="OpenTargets_get_asso_targ_by_dise_efoI", exists=True,
                 signature={"efoId": "string"}, available=True, quirk="use underscore form"),
    ]
    subs = [Substitution("DisGeNET_search_gene",
                         ("OpenTargets_get_asso_targ_by_dise_efoI",),
                         "DisGeNET dead; use OpenTargets.", escalate=False)]
    block = render_grounded_facts(available, subs)
    assert "OpenTargets_get_asso_targ_by_dise_efoI" in block
    assert "underscore" in block             # quirk surfaced
    assert "DisGeNET_search_gene" in block    # substitution origin surfaced
    assert "SUBSTITUTE" in block.upper()


def test_build_converter_prompt_contains_all_four_parts():
    prompt = build_converter_prompt(
        target_skill_md="# Target Research SKILL",
        golden_source="# Disease SKILL source",
        golden_persona="# Disease persona converted",
        grounded_facts_block="GROUNDED FACTS HERE",
    )
    assert "# Disease SKILL source" in prompt       # golden few-shot (source)
    assert "# Disease persona converted" in prompt  # golden few-shot (converted)
    assert "GROUNDED FACTS HERE" in prompt          # grounded facts
    assert "# Target Research SKILL" in prompt      # target to convert
    assert TRANSFORM_CHECKLIST.splitlines()[0] in prompt  # the checklist
