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

# A realistic master-router shape: the STEP-2 frontmatter clause enumerates ONLY the
# data-file analysis skills ("this exact list (never invent): … Use for …"), while the
# BODY routing table also names servable research skills (disease/drug/target-research).
# The parser must scope to the STEP-2 clause and NOT sweep the body's research skills in.
ROUTER = """---
name: tooluniverse
description: "ToolUniverse plugin router. STEP 2 routing — pick a sub-skill name from
this exact list (never invent): tooluniverse-rnaseq-deseq2 (RNA-seq DE),
tooluniverse-crispr-screen-analysis (MAGeCK), tooluniverse-proteomics-analysis (mass spec).
Use for CSV/Excel/VCF and any analysis question."
paths: "*.csv,*.vcf"
---
# Routing Table
### 2. Research & Profiling
| "research", "disease" | Skill(skill="tooluniverse-disease-research") |
| "research", "target"  | Skill(skill="tooluniverse-target-research") |
| "research", "drug"    | Skill(skill="tooluniverse-drug-research") |
"""


def test_step2_list_is_parsed_excluding_body_research_skills_and_router_itself():
    analysis = parse_router_analysis_skills(ROUTER)
    # the three STEP-2 analysis skills are in
    assert "tooluniverse-rnaseq-deseq2" in analysis
    assert "tooluniverse-crispr-screen-analysis" in analysis
    assert "tooluniverse-proteomics-analysis" in analysis
    # the router itself is not a sub-skill
    assert "tooluniverse" not in analysis
    # CRITICAL regression: research skills named only in the BODY routing table are
    # NOT analysis — the parser must scope to the STEP-2 clause, not the whole doc.
    assert "tooluniverse-target-research" not in analysis
    assert "tooluniverse-disease-research" not in analysis
    assert "tooluniverse-drug-research" not in analysis


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
