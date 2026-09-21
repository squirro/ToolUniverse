"""Unit tests for the find_skill catalog search (ADR-0009).

Pure module — no fastmcp/squirro import required.
"""

import pytest

from tooluniverse.skill_index import (
    SkillDoc,
    build_index,
    header_triggers,
    role_description,
    search,
    tokenize,
)

pytestmark = pytest.mark.unit


def _body(role: str, header: str = "") -> str:
    hdr = f"<!--\n{header}\n-->\n\n" if header else ""
    return f"{hdr}# Role\n{role}\n\n# LOOK UP, DON'T GUESS\nstuff\n"


@pytest.fixture
def skills_dir(tmp_path):
    """Three skills sharing the Role boilerplate, differing only in domain."""
    (tmp_path / "cancer-classification.md").write_text(
        _body(
            "Cancer Classification agent for a biotech holding. Given a free-text tumor "
            "description or an OncoTree code, you produce a classification report by querying "
            "authoritative databases through ToolUniverse.",
            header="Triggers: tumour, neoplasm, malignancy, OncoTree",
        )
    )
    (tmp_path / "regulatory-variant-analysis.md").write_text(
        _body(
            "Regulatory Variant Analysis agent for a biotech team. Given a non-coding regulatory "
            "variant (rsID or region), you produce a regulatory interpretation report by querying "
            "RegulomeDB, ENCODE, and eQTL databases through ToolUniverse."
        )
    )
    (tmp_path / "drug-research.md").write_text(
        _body(
            "Drug Research agent for a biotech holding. Given a drug, you produce a profile of "
            "chemistry, targets, indications, and safety by querying databases through ToolUniverse."
        )
    )
    return tmp_path


def test_tokenize_keeps_domain_words_drops_template_boilerplate():
    """Distinctive domain words survive; shared skill-template phrasing is stripped."""
    toks = tokenize(
        "Cancer Classification agent for a biotech holding. Given a tumor, you produce a report."
    )
    assert "cancer" in toks and "classification" in toks and "tumor" in toks
    for boilerplate in ("agent", "biotech", "holding", "given", "produce", "report", "for", "a"):
        assert boilerplate not in toks


def test_role_description_extracts_the_role_paragraph():
    """The contiguous lines under '# Role' (up to a blank line) become the description."""
    body = "<!--hdr-->\n# Role\nLine one of role.\nLine two of role.\n\n# LOOK UP\nother\n"
    assert role_description(body) == "Line one of role. Line two of role."


def test_role_description_absent_returns_empty():
    """A body without a '# Role' heading yields an empty description."""
    assert role_description("# Other\nno role here\n") == ""


def test_header_triggers_parsed_from_leading_comment():
    """A 'Triggers:' line in the HTML-comment header yields lowercased trigger phrases."""
    body = "<!--\nPorted from X.\nTriggers: tumour, Neoplasm, malignancy\n-->\n# Role\nr\n"
    assert header_triggers(body) == ["tumour", "neoplasm", "malignancy"]


def test_header_triggers_absent_returns_empty():
    """No 'Triggers:' line yields an empty list."""
    assert header_triggers("<!--\nPorted from X.\n-->\n# Role\nr\n") == []


def test_build_index_covers_all_skills(skills_dir):
    """Every *.md in the directory becomes a SkillDoc with non-empty tokens."""
    idx = build_index(skills_dir)
    assert {d.name for d in idx} == {
        "cancer-classification",
        "regulatory-variant-analysis",
        "drug-research",
    }
    assert all(isinstance(d, SkillDoc) and d.tokens for d in idx)


def test_build_index_missing_dir_returns_empty(tmp_path):
    """A non-existent directory yields an empty index, not an error."""
    assert build_index(tmp_path / "nope") == []


# --- search: the routing behaviour that matters --------------------------

def test_search_routes_domain_query_to_right_skill(skills_dir):
    """A natural domain query ranks the matching skill first despite shared boilerplate."""
    hits = search(build_index(skills_dir), "classify this tumor sample", limit=3)
    assert hits[0].name == "cancer-classification"


def test_search_name_tokens_win(skills_dir):
    """A query echoing a skill's name routes to it."""
    assert search(build_index(skills_dir), "regulatory variant", limit=3)[0].name == (
        "regulatory-variant-analysis"
    )


def test_search_triggers_improve_synonym_recall(skills_dir):
    """'neoplasm' appears only in cancer-classification's Triggers, never its Role text."""
    hits = search(build_index(skills_dir), "neoplasm staging", limit=3)
    assert hits and hits[0].name == "cancer-classification"


def test_search_pure_boilerplate_query_does_not_rank(skills_dir):
    """A query of only shared template words must not confidently pick a skill."""
    assert search(build_index(skills_dir), "agent biotech holding report", limit=3) == []


def test_search_respects_limit_and_drops_zero_overlap(skills_dir):
    """limit caps results; only overlapping skills are returned."""
    hits = search(build_index(skills_dir), "drug", limit=1)
    assert len(hits) == 1 and hits[0].name == "drug-research"


def test_search_empty_query_returns_empty(skills_dir):
    """A whitespace/stopword-only query yields no hits."""
    assert search(build_index(skills_dir), "   the and of   ", limit=3) == []


def test_search_no_docs_returns_empty():
    """An empty index yields no hits."""
    assert search([], "anything", limit=3) == []


def test_search_deterministic_tie_break_by_name():
    """Equal-scoring skills are ordered by name."""
    docs = [
        SkillDoc("b-skill", ("kinase", "kinase"), "d"),
        SkillDoc("a-skill", ("kinase", "kinase"), "d"),
    ]
    assert [h.name for h in search(docs, "kinase", limit=2)] == ["a-skill", "b-skill"]


# --- every served skill needs routing triggers (DSR-630 follow-up) -------------
# Measured on sr-dev: find_skill("...emerging viral clade including genomics, spread
# dynamics, and countermeasures") returned five *genomics* skills and NOT
# infectious-disease. _doc_tokens weights Triggers x3 as the deliberate routing signal,
# but 64 of 76 bodies carried none, leaving them ranked on shared template phrasing.

import re as _re
from pathlib import Path as _Path

_DEPLOY = _Path(__file__).resolve().parents[2] / "deploy"
_DISPATCHERS = {"router", "router-spike", "doriano", "smcp-only"}


def _served_bodies():
    for p in sorted(_DEPLOY.glob("persona-*.md")):
        name = p.stem[len("persona-"):]
        if name in _DISPATCHERS or name.startswith("prod"):
            continue
        yield name, p.read_text()


def test_every_served_skill_declares_triggers():
    from tooluniverse.skill_index import header_triggers

    missing = [name for name, body in _served_bodies() if not header_triggers(body)]
    assert missing == [], f"skills with no Triggers line (unroutable by find_skill): {missing}"


def test_an_outbreak_brief_ranks_the_infectious_disease_skill():
    """The live failing query, scored against the real corpus."""
    from tooluniverse.skill_index import build_index, search

    docs = build_index(_DEPLOY_SKILLS_DIR())
    hits = search(docs, "current situation brief of an emerging viral clade including "
                        "genomics, spread dynamics, and countermeasures", limit=5)
    names = [h.name for h in hits]
    assert "infectious-disease" in names, names


def _DEPLOY_SKILLS_DIR(tmp={}):
    """The served set as the image stages it: persona-<name>.md -> <name>.md."""
    import tempfile, shutil
    if "dir" not in tmp:
        d = _Path(tempfile.mkdtemp())
        for name, body in _served_bodies():
            (d / f"{name}.md").write_text(body)
        tmp["dir"] = d
    return tmp["dir"]
