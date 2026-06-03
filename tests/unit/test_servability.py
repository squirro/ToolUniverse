"""Unit tests for the servability classifier (ADR-0007 / DSR-508).

Pure module — the authoritative analysis-skill set is parsed from the master
router's STEP-2 routing list; per-skill paths:/RULE-ZERO are corroboration.
"""
import pytest

from tooluniverse.skill_conversion.servability import (
    Servability,
    classify,
    parse_router_analysis_skills,
)

pytestmark = pytest.mark.unit

# A trimmed master-router description: its STEP-2 list enumerates analysis skills.
ROUTER = """---
name: tooluniverse
description: "ToolUniverse plugin router. STEP 2 routing — pick a sub-skill name from
this exact list (never invent): tooluniverse-rnaseq-deseq2 (RNA-seq DE),
tooluniverse-crispr-screen-analysis (MAGeCK), tooluniverse-proteomics-analysis (mass spec)."
paths: "*.csv,*.vcf"
---
body
"""


def test_router_list_is_parsed_minus_router_itself():
    analysis = parse_router_analysis_skills(ROUTER)
    assert "tooluniverse-rnaseq-deseq2" in analysis
    assert "tooluniverse-crispr-screen-analysis" in analysis
    assert "tooluniverse-proteomics-analysis" in analysis
    assert "tooluniverse" not in analysis  # the router itself is not a sub-skill


def test_analysis_skill_in_router_list_is_not_servable():
    analysis = parse_router_analysis_skills(ROUTER)
    s = classify("tooluniverse-crispr-screen-analysis", "# any body", analysis)
    assert s.servable is False
    assert "router" in s.reason.lower()


def test_research_skill_absent_from_list_is_servable():
    analysis = parse_router_analysis_skills(ROUTER)
    s = classify("tooluniverse-target-research", "# Target research\nno file inputs", analysis)
    assert s.servable is True


def test_paths_frontmatter_corroborates_analysis_even_if_absent_from_list():
    skill_md = "---\nname: tooluniverse-mystery\npaths: \"*.h5ad\"\n---\nbody"
    s = classify("tooluniverse-mystery", skill_md, frozenset())
    assert s.servable is False
    assert "paths" in s.reason.lower()


def test_rule_zero_body_corroborates_analysis():
    skill_md = "---\nname: tooluniverse-mystery2\n---\n## RULE ZERO\nread executed.ipynb"
    s = classify("tooluniverse-mystery2", skill_md, frozenset())
    assert s.servable is False
    assert "rule zero" in s.reason.lower()
