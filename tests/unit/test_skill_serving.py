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
