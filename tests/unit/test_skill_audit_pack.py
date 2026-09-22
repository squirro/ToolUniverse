"""The pack the blinded judges score: no arm marker, every cited abstract whole.

A persona that opens each answer with a plan block naming its tools gives the arm away,
and resolving citations by PMID alone leaves PMC-linked reports with no abstract in the
pack, so their numbers score "not verified".
"""

import json
import re
import sys
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))

from skill_audit.pack import (  # noqa: E402
    Citation,
    build_pack,
    check_pack,
    citations,
    render,
    resolve,
    strip_plan,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
WEB_REPORT = json.loads((FIXTURES / "web_report_cisplatin_2026-09-19.json").read_text())["answer"]
RECORDED = json.loads((FIXTURES / "citations" / "resolve_probe_2026-09-21.json").read_text())
QUESTION = ("Pull together an end-to-end safety picture for cisplatin and look especially at "
            "nephrotoxicity and ototoxicity.")


def _recorded_fetch(url: str) -> str:
    """The three services as they answered, keyed by what the URL asks for."""
    if "idconv" in url and "PMC11673797" in url:
        return json.dumps(RECORDED["idconv/PMC11673797"])
    if "efetch" in url and "id=39765905" in url:
        return RECORDED["efetch/39765905"]
    if "europepmc" in url and "10.3390" in url:
        return json.dumps(RECORDED["europepmc/DOI:10.3390/antiox13121578"])
    raise AssertionError(f"unexpected request: {url}")


# --- blinding: the plan block goes, nothing else moves ---------------------------------

def test_the_plan_block_is_removed_and_the_rest_of_the_report_is_unchanged():
    stripped, plan = strip_plan(WEB_REPORT)

    lines = WEB_REPORT.splitlines()
    block_end = next(n for n, line in enumerate(lines) if n and not line.startswith(">") and line.strip())
    assert plan.startswith("> ## Research Plan") and plan.splitlines() == [l for l in lines[:block_end] if l]
    assert stripped == "\n".join(lines[block_end:])
    assert "Research Plan" not in stripped and "Step A" not in stripped


def test_a_report_without_a_plan_block_is_returned_as_it_is():
    text = "## Cisplatin safety\n\n> a quoted finding, not a plan\n\nText."

    assert strip_plan(text) == (text, None)


# --- citations: each kind of link resolves to the abstract, complete ----------------------

def test_the_three_kinds_of_link_are_found_in_a_report():
    text = ("see https://pubmed.ncbi.nlm.nih.gov/39765905/ and "
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC11673797/ and https://doi.org/10.3390/antiox13121578).")

    assert citations(text) == [Citation("pmid", "39765905"), Citation("pmc", "PMC11673797"),
                               Citation("doi", "10.3390/antiox13121578")]


@pytest.mark.parametrize("citation", [
    Citation("pmid", "39765905"),
    Citation("pmc", "PMC11673797"),
    Citation("doi", "10.3390/antiox13121578"),
])
def test_each_kind_of_link_resolves_to_the_same_abstract_from_recorded_responses(citation):
    found = resolve(citation, fetch=_recorded_fetch)

    assert found["pmid"] == "39765905"
    assert found["title"].startswith("Cisplatin-Induced Hearing Loss")
    assert found["abstract"].startswith("Cisplatin is an established component")
    assert found["url"] == "https://pubmed.ncbi.nlm.nih.gov/39765905/"


def test_a_long_abstract_is_in_the_pack_complete():
    abstract = ("Finding. " * 375).strip()             # well past any cut
    xml = ("<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID Version=\"1\">1</PMID><Article>"
           f"<ArticleTitle>Long</ArticleTitle><Abstract><AbstractText>{abstract}</AbstractText>"
           "</Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>")
    pack = build_pack(QUESTION, {"A": "A number.[^1^]\n\n[^1^]: https://pubmed.ncbi.nlm.nih.gov/1/"},
                      fetch=lambda url: xml)

    assert abstract in render(pack)
    assert check_pack(pack, QUESTION) == []


# --- the pack is examined before the judges get it ------------------------------------------

def _pack(fetch=_recorded_fetch, **reports):
    return build_pack(QUESTION, reports or {"A": "Text.[^1^]\n\n[^1^]: https://pubmed.ncbi.nlm.nih.gov/39765905/"},
                      fetch=fetch)


def test_the_check_fails_on_the_wrong_question_in_the_header():
    pack = _pack()

    problems = check_pack(pack, "What is the safety picture for Lutathera?")

    assert any("question" in p for p in problems)


def test_the_check_fails_on_a_word_that_identifies_an_arm():
    pack = _pack(A="The run_skill hand-over gave PRR 54.766.[^1^]\n\n[^1^]: https://pubmed.ncbi.nlm.nih.gov/39765905/",
                 B="> ## Research Plan\n> tools\n\nPRR 54.766.")

    problems = check_pack(pack, QUESTION)

    assert any("run_skill" in p and "A" in p for p in problems)
    assert not any("Research Plan" in p for p in problems), "the plan block was stripped at build time"


def test_the_check_fails_when_an_abstract_was_cut():
    pack = _pack()
    pack["reports"][0]["citations"][0]["abstract"] = pack["reports"][0]["citations"][0]["abstract"][:120] + "…"

    assert any("cut" in p or "complete" in p for p in check_pack(pack, QUESTION))


def test_the_pack_keeps_the_original_report_beside_the_blinded_one():
    pack = _pack(A=WEB_REPORT)

    assert pack["reports"][0]["original"] == WEB_REPORT
    assert "Research Plan" not in pack["reports"][0]["text"]
    assert re.search(r"PMC11673797", pack["reports"][0]["original"])
