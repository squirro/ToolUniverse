"""Unit tests for the get_skill body loader (ADR-0005 / DSR-505).

Pure module — no fastmcp/squirro import required.
"""

import pytest

from tooluniverse.skill_serving import (
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

def test_loads_known_body(skills_dir):
    body = load_skill_body(skills_dir, "disease-research")
    assert "Disease SOP body" in body


def test_md_suffix_is_accepted(skills_dir):
    assert load_skill_body(skills_dir, "disease-research.md").startswith("# Role")


def test_unknown_name_lists_available(skills_dir):
    with pytest.raises(SkillNotFound) as exc:
        load_skill_body(skills_dir, "nonexistent")
    msg = str(exc.value)
    # The error must help the agent self-correct by naming what IS served.
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
    """available_skills returns the served body stems, sorted."""
    assert available_skills(skills_dir) == ["disease-research", "drug-research"]


def test_available_skills_missing_dir_is_empty(tmp_path):
    """A missing skills_dir yields an empty list, not an error."""
    assert available_skills(tmp_path / "nope") == []


# --- the serving-surface citation contract (DSR-631) ----------------------
# The renderer promotes only LINK-bearing footnotes, and a loaded body is BINDING —
# so the citation contract must ride on the serving surface itself, appended by the
# loader to EVERY body, superseding whatever an individual body says.

def test_every_served_body_carries_the_citation_contract(skills_dir):
    from tooluniverse.skill_serving import CITATION_CONTRACT

    body = load_skill_body(skills_dir, "disease-research")

    assert body.endswith(CITATION_CONTRACT)
    assert "source_url" in CITATION_CONTRACT
    assert "supersede" in CITATION_CONTRACT.lower()


def test_the_original_body_text_is_preserved_ahead_of_the_contract(skills_dir):
    body = load_skill_body(skills_dir, "drug-research")

    assert body.startswith("# Role\nDrug SOP body")


def test_an_unknown_name_still_raises_not_found(skills_dir):
    with pytest.raises(SkillNotFound):
        load_skill_body(skills_dir, "no-such-skill")


def test_the_contract_teaches_the_execute_tool_call_form(skills_dir):
    """A live turn died passing another tool's parameters straight into execute_tool
    (9 pydantic 'unexpected keyword argument' errors, no retry). The trailer is read
    exactly when a loaded skill starts calling tools, so the two-parameter form and
    the recovery hint ride there."""
    from tooluniverse.skill_serving import CITATION_CONTRACT

    assert "execute_tool(tool_name=" in CITATION_CONTRACT
    assert "unexpected keyword argument" in CITATION_CONTRACT
