"""Unit tests for the get_skill body loader (ADR-0005 / DSR-505).

Pure module — no fastmcp/squirro import required.
"""

import re

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


# --- rules added from the 2026-08-21 coverage baseline (DSR-690) -------------

def test_the_contract_forbids_inventing_a_tool_name():
    """Three calls in the sweep named tools that exist nowhere: PharmGKB_get_drug_label,
    ensembl_lookup_region, ClinGen_search_dosage_sensitivity_region. None of those
    strings appears in any served body — persona_lint is right that the corpus has no
    dead calls, so the agent guessed plausible names instead of discovering real ones."""
    from tooluniverse.skill_serving import CITATION_CONTRACT

    assert re.search(r"never (guess|invent)[^.]*tool\s+name", CITATION_CONTRACT,
                     re.IGNORECASE), CITATION_CONTRACT
    assert "grep_tools" in CITATION_CONTRACT


def test_the_contract_requires_identifiers_to_be_resolved_not_guessed():
    """12 lookup misses were invented identifier formats: `sst2_human` where GPCRdb
    wanted sstr2_human or a UniProt accession, PDB 7t11 for a question that named
    7T10, protein_name where AlphaFold wants a qualifier."""
    from tooluniverse.skill_serving import CITATION_CONTRACT

    assert re.search(r"identifier", CITATION_CONTRACT, re.IGNORECASE)
    assert re.search(r"resolve[^.]*(before|first)|do not (guess|invent)[^.]*identifier",
                     CITATION_CONTRACT, re.IGNORECASE), CITATION_CONTRACT


def test_the_contract_requires_a_url_scheme_on_every_footnote():
    """29 of 76 answers emitted footnotes the renderer drops — `](clinicaltrials.gov)`
    with no scheme, and `](squirro_source#...)`. Only http/https/mailto/xmpp render, so
    the rule has to name the scheme rather than say 'a link'."""
    from tooluniverse.skill_serving import CITATION_CONTRACT

    assert "https://" in CITATION_CONTRACT
    assert re.search(r"before you emit|check every footnote|output gate",
                     CITATION_CONTRACT, re.IGNORECASE), CITATION_CONTRACT


def test_the_contract_sends_a_type_mismatch_back_to_the_schema():
    """Both directions occur and neither can be assumed. UniProt_search was rejected
    with "'accession,gene_names,go_id' is not of type 'array'" (comma-joined a list),
    while ReactomeAnalysis_pathway_enrichment was rejected with "['MEN1', 'DAXX', ...]
    is not of type 'string'. Expected string, got list" — the second was CAUSED by an
    earlier version of this contract telling the agent that list parameters are arrays.
    So the rule must send it to the declared schema, never prescribe a shape."""
    from tooluniverse.skill_serving import CITATION_CONTRACT

    assert "get_tool_info" in CITATION_CONTRACT, CITATION_CONTRACT
    assert re.search(r"is not of type", CITATION_CONTRACT), CITATION_CONTRACT
    # It must NOT tell the agent that a list parameter is always an array.
    assert not re.search(r"as a JSON array|list-typed parameter as", CITATION_CONTRACT), \
        CITATION_CONTRACT
