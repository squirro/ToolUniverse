"""Unit tests for the get_skill body loader (ADR-0005 / DSR-505). Pure module."""

import re

import pytest

from tooluniverse.skill_serving import (
    CITATION_CONTRACT,
    SkillNotFound,
    available_skills,
    load_skill_body,
    normalize_skill_name,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def skills_dir(tmp_path):
    (tmp_path / "disease-research.md").write_text("# Role\nDisease SOP body\n")
    (tmp_path / "drug-research.md").write_text("# Role\nDrug SOP body\n")
    return tmp_path


# --- normalize_skill_name -------------------------------------------------

@pytest.mark.parametrize(
    "given,expected",
    [
        ("disease-research", "disease-research"),
        ("disease-research.md", "disease-research"),
        ("  disease-research  ", "disease-research"),
        ("Disease-Research", "disease-research"),
        ("drug_research", "drug_research"),
    ],
)
def test_normalize_accepts_and_canonicalizes(given, expected):
    assert normalize_skill_name(given) == expected


@pytest.mark.parametrize("bad", ["", "   ", "../secrets", "a/b", "foo.txt", "-lead"])
def test_normalize_rejects_invalid(bad):
    with pytest.raises(SkillNotFound):
        normalize_skill_name(bad)


# --- load_skill_body ------------------------------------------------------

@pytest.mark.parametrize("name", ["disease-research", "disease-research.md"])
def test_loads_a_known_body_with_or_without_the_suffix(skills_dir, name):
    body = load_skill_body(skills_dir, name)
    assert body.startswith("# Role") and "Disease SOP body" in body


def test_unknown_name_lists_available(skills_dir):
    # The error must help the agent self-correct by naming what IS served.
    with pytest.raises(SkillNotFound) as exc:
        load_skill_body(skills_dir, "nonexistent")
    msg = str(exc.value)
    assert "disease-research" in msg and "drug-research" in msg


def test_missing_skills_dir_raises(tmp_path):
    with pytest.raises(SkillNotFound):
        load_skill_body(tmp_path / "does-not-exist", "disease-research")


@pytest.mark.parametrize("attack", ["../disease-research", "a/b", "foo bar"])
def test_traversal_and_garbage_rejected(skills_dir, attack):
    # name comes from the LLM; it must fail closed, never escape the served dir.
    with pytest.raises(SkillNotFound):
        load_skill_body(skills_dir, attack)


# --- available_skills -----------------------------------------------------

def test_available_skills_sorted_stems(skills_dir):
    assert available_skills(skills_dir) == ["disease-research", "drug-research"]


def test_available_skills_missing_dir_is_empty(tmp_path):
    """A missing skills_dir yields an empty list, not an error."""
    assert available_skills(tmp_path / "nope") == []


# --- the serving-surface citation contract (DSR-631) ----------------------
# The renderer promotes only LINK-bearing footnotes, and a loaded body is BINDING —
# so the citation contract rides on the serving surface itself, appended by the
# loader to EVERY body, superseding whatever an individual body says.

def test_the_contract_is_appended_to_every_body_and_the_body_survives(skills_dir):
    assert load_skill_body(skills_dir, "disease-research").endswith(CITATION_CONTRACT)
    assert load_skill_body(skills_dir, "drug-research").startswith("# Role\nDrug SOP body")


# What the contract must say, each rule traced to failures in the 2026-08-21 coverage
# baseline (DSR-690):
#  - execute_tool: a live turn died passing another tool's parameters straight in
#  - tool names: three calls named tools that exist nowhere, so the agent guessed
#  - identifiers: 12 lookup misses were invented formats (`sst2_human`, PDB 7t11)
#  - footnotes: 29 of 76 answers emitted links the renderer drops (no url scheme)
#  - type mismatches: both directions occur, so send the agent to the declared schema
@pytest.mark.parametrize("literal", [
    "source_url", "execute_tool(tool_name=", "unexpected keyword argument",
    "grep_tools", "https://", "get_tool_info",
])
def test_the_contract_names_the_thing_exactly(literal):
    assert literal in CITATION_CONTRACT, CITATION_CONTRACT


@pytest.mark.parametrize("pattern,flags", [
    (r"supersede", re.IGNORECASE),
    (r"never (guess|invent)[^.]*tool\s+name", re.IGNORECASE),
    (r"identifier", re.IGNORECASE),
    (r"resolve[^.]*(before|first)|do not (guess|invent)[^.]*identifier", re.IGNORECASE),
    (r"before you emit|check every footnote|output gate", re.IGNORECASE),
    (r"is not of type", 0),
])
def test_the_contract_states_the_rule(pattern, flags):
    assert re.search(pattern, CITATION_CONTRACT, flags), CITATION_CONTRACT


def test_the_contract_does_not_prescribe_a_parameter_shape():
    """ReactomeAnalysis_pathway_enrichment was rejected with "['MEN1', ...] is not of
    type 'string'" BECAUSE an earlier contract said list parameters are arrays."""
    assert not re.search(r"as a JSON array|list-typed parameter as", CITATION_CONTRACT), \
        CITATION_CONTRACT
