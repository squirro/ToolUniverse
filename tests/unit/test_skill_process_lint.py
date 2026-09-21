"""A Skill Process names no entity (rule 10): what the lint refuses, and what it lets through.

Converting agents test on one question and write the fix in that question's words. The
three shipped processes did exactly that, unseen through five judged experiments.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_process_lint import violations  # noqa: E402

pytestmark = pytest.mark.unit


def _process(*steps, **top):
    return {"skill": "demo", "inputs": ["drug_name"], "steps": list(steps), **top}


def test_free_text_in_a_call_argument_is_refused_and_located():
    """The defect as it shipped: one test question's words, sent for every drug."""
    process = _process({"id": "web_context", "delegate": [
        {"tool": "exa_web_search",
         "arguments": {"query": "{drug_name} myelodysplastic syndrome renal impairment safety"}}]})

    (found,) = violations(process)

    assert found.kind == "free_text_argument"
    assert (found.step, found.field) == ("web_context", "delegate[0].arguments.query")
    assert "myelodysplastic" in found.text


@pytest.mark.parametrize("value", [
    "{drug_name}",                       # a placeholder
    "{inn} AND {reaction}",              # placeholders joined by the source's operator
    "sex",                               # the source's own constant
    "get_approval_history",
    "symbol,name,entrezgene,ensembl.gene,summary",
    "<the disease CURIE from the search>",   # an instruction to the agent, not a query
])
def test_placeholders_operators_and_the_sources_constants_pass(value):
    process = _process({"id": "lookup", "calls": [
        {"tool": "some_tool", "arguments": {"argument": value, "size": 10, "flag": True}}]})

    assert [v for v in violations(process) if v.kind == "free_text_argument"] == []


def test_the_instructions_of_a_delegated_computation_are_prose_not_a_query():
    process = _process({"id": "compute", "delegate": [
        {"tool": "OpenAI_Code_Interpreter",
         "arguments": {"task": "Sort the rows by prr, largest first. Keep term and url as received.",
                       "rows": "{prr_rows}"}}]})

    assert violations(process) == []


def test_an_entity_of_the_skills_benchmark_questions_is_refused_wherever_the_agent_reads_prose():
    """The rare-disease template named the disease families that answer both of its cases."""
    process = _process(
        {"id": "differential", "calls": [],
         "notes": "Coarse facies plus hepatosplenomegaly returns the storage disorders."},
        {"id": "compute", "delegate": [{"tool": "OpenAI_Code_Interpreter", "arguments": {
            "task": "Set aside every term that names Hurler syndrome."}}]},
        report="Name the gene pair that separates them (IDUA for Hurler against IDS).")

    found = violations(process, entities=["Hurler", "hepatosplenomegaly", "cisplatin"])

    assert [(v.kind, v.step, v.field, v.text) for v in found] == [
        ("named_entity", "(process)", "report", "Hurler"),
        ("named_entity", "differential", "notes", "hepatosplenomegaly"),
        ("named_entity", "compute", "delegate[0].arguments.task", "Hurler"),
    ]


def test_a_rule_stated_without_a_benchmark_entity_passes():
    process = _process(
        {"id": "differential", "calls": [],
         "notes": "When the top two candidates share a disease family, name the gene pair."},
        report="State the inheritance and age of onset that separate the candidates.")

    assert violations(process, entities=["Hurler", "hepatosplenomegaly"]) == []


def test_a_gene_symbol_is_matched_as_written_so_the_plural_of_id_is_not_a_gene():
    process = _process({"id": "resolve", "calls": [], "label": "Resolve the disease IDs",
                        "notes": "Carry the ids into every later step. ids is not a gene."},
                       report="Separate the two by their gene (the IDS row).")

    found = violations(process, entities=["IDS", "Hurler"])

    assert [(v.field, v.text) for v in found] == [("report", "IDS")]


MAXIMA = {"search_clinical_trials": {"pageSize": 1000}, "PubMed_search_articles": {"limit": 1000}}


def _call(tool, **arguments):
    return {"tool": tool, "arguments": {"query_term": "{drug_name}", **arguments}}


def test_a_limit_nobody_wrote_is_the_sources_default_and_is_refused():
    """Ten trials of 866: `pageSize` was never set, so no written value could have been caught."""
    process = _process({"id": "trials", "calls": [_call("search_clinical_trials")]})

    (found,) = violations(process, maxima=MAXIMA)

    assert (found.kind, found.step, found.field) == (
        "source_default", "trials", "calls[0].arguments.pageSize")


def test_a_hand_written_limit_below_the_sources_maximum_needs_a_reason():
    narrow = {"id": "literature", "calls": [_call("PubMed_search_articles", limit=10)]}
    reasoned = {**narrow, "narrowed": "the ten most relevant are read; the total is recorded"}

    (found,) = violations(_process(narrow), maxima=MAXIMA)

    assert (found.kind, found.text) == ("narrowed_without_reason", "limit=10, the source allows 1000")
    assert violations(_process(reasoned), maxima=MAXIMA) == []


def test_a_call_at_the_sources_maximum_passes():
    process = _process({"id": "trials", "calls": [_call("search_clinical_trials", pageSize=1000)]})

    assert violations(process, maxima=MAXIMA) == []


# --- the line in the sand, over the processes that ship -------------------------

def test_the_shipped_processes_break_the_rules_exactly_where_the_known_list_says():
    """Exact, in both directions: a new violation fails, and so does a fixed one still listed --
    the list can only shrink, and it shrinks in the commit that fixes the process."""
    from tooluniverse.skill_graph import GRAPHS_DIR, load_graph
    from tooluniverse.skill_process_lint import benchmark_entities, known_violations, source_maxima

    found = {
        path.stem: sorted(v.message for v in violations(
            load_graph(path.stem), entities=benchmark_entities(path.stem),
            maxima=source_maxima()))
        for path in sorted(GRAPHS_DIR.glob("*.yaml"))}

    assert {skill: messages for skill, messages in found.items() if messages} == known_violations()


def test_a_row_that_packs_several_lists_is_refused_because_they_fall_out_of_step():
    """198 DOIs against 200 PMIDs: `collect` drops a missing value, and every later pair is wrong."""
    packed = _process({"id": "literature", "calls": [], "collect": {"literature_rows": {
        "path": "", "fields": ["$item as reaction", "data[].pmid as pmids", "data[].doi_url as dois"]}}},
        tables={"literature_rows": "evidence"})
    one_list = _process({"id": "phenotypes", "calls": [], "collect": {"disease_phenotypes": {
        "path": "data", "fields": ["$item as orphacode", "phenotypes[].hpo_id as hpo_ids"]}}},
        tables={"disease_phenotypes": "fact"})

    (found,) = violations(packed)

    assert (found.kind, found.step, found.field) == (
        "parallel_lists", "literature", "collect.literature_rows")
    assert violations(one_list) == []
