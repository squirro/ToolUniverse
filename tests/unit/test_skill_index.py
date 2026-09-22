"""Unit tests for the find_skill catalog search (ADR-0009). Pure module."""

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
    toks = tokenize(
        "Cancer Classification agent for a biotech holding. Given a tumor, you produce a report."
    )
    assert "cancer" in toks and "classification" in toks and "tumor" in toks
    for boilerplate in ("agent", "biotech", "holding", "given", "produce", "report", "for", "a"):
        assert boilerplate not in toks


@pytest.mark.parametrize("body,expected", [
    # the contiguous lines under '# Role', up to a blank line
    ("<!--hdr-->\n# Role\nLine one of role.\nLine two of role.\n\n# LOOK UP\nother\n",
     "Line one of role. Line two of role."),
    ("# Other\nno role here\n", ""),
])
def test_role_description_is_the_role_paragraph_or_empty(body, expected):
    assert role_description(body) == expected


@pytest.mark.parametrize("body,expected", [
    ("<!--\nPorted from X.\nTriggers: tumour, Neoplasm, malignancy\n-->\n# Role\nr\n",
     ["tumour", "neoplasm", "malignancy"]),
    ("<!--\nPorted from X.\n-->\n# Role\nr\n", []),
])
def test_header_triggers_are_lowercased_or_empty(body, expected):
    assert header_triggers(body) == expected


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

@pytest.mark.parametrize("query,limit,expected", [
    # a natural domain query beats the shared boilerplate
    ("classify this tumor sample", 3, "cancer-classification"),
    ("regulatory variant", 3, "regulatory-variant-analysis"),
    # 'neoplasm' appears only in cancer-classification's Triggers, never its Role text
    ("neoplasm staging", 3, "cancer-classification"),
    ("drug", 1, "drug-research"),
])
def test_search_routes_a_query_to_the_right_skill(skills_dir, query, limit, expected):
    hits = search(build_index(skills_dir), query, limit=limit)
    assert hits and len(hits) <= limit
    assert hits[0].name == expected


@pytest.mark.parametrize("query", [
    "agent biotech holding report",   # only shared template words: do not pick confidently
    "   the and of   ",               # whitespace/stopwords only
])
def test_search_returns_nothing_it_cannot_justify(skills_dir, query):
    assert search(build_index(skills_dir), query, limit=3) == []


def test_search_no_docs_returns_empty():
    assert search([], "anything", limit=3) == []


def test_search_deterministic_tie_break_by_name():
    docs = [
        SkillDoc("b-skill", ("kinase", "kinase"), "d"),
        SkillDoc("a-skill", ("kinase", "kinase"), "d"),
    ]
    assert [h.name for h in search(docs, "kinase", limit=2)] == ["a-skill", "b-skill"]


# --- every served skill needs routing triggers (DSR-630 follow-up) -------------
# Measured on sr-dev: a find_skill query for an emerging viral clade returned five
# *genomics* skills and NOT infectious-disease. _doc_tokens weights Triggers x3, but 64
# of 76 bodies carried none, leaving them ranked on shared template phrasing.

from pathlib import Path as _Path

_DEPLOY = _Path(__file__).resolve().parents[2] / "deploy"
_DISPATCHERS = {"router", "router-spike", "doriano", "smcp-only"}


def _served_bodies():
    for p in sorted(_DEPLOY.glob("persona-*.md")):
        name = p.stem[len("persona-"):]
        if name in _DISPATCHERS or name.startswith("prod"):
            continue
        yield name, p.read_text()


def _served_skills_dir(tmp={}):
    """The served set as the image stages it: persona-<name>.md -> <name>.md."""
    import tempfile
    if "dir" not in tmp:
        d = _Path(tempfile.mkdtemp())
        for name, body in _served_bodies():
            (d / f"{name}.md").write_text(body)
        tmp["dir"] = d
    return tmp["dir"]


def test_every_served_skill_declares_triggers():
    missing = [name for name, body in _served_bodies() if not header_triggers(body)]
    assert missing == [], f"skills with no Triggers line (unroutable by find_skill): {missing}"


def test_an_outbreak_brief_ranks_the_infectious_disease_skill():
    """The live failing query, scored against the real corpus."""
    hits = search(build_index(_served_skills_dir()),
                  "current situation brief of an emerging viral clade including "
                  "genomics, spread dynamics, and countermeasures", limit=5)
    names = [h.name for h in hits]
    assert "infectious-disease" in names, names
