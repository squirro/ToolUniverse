"""Emit a skill's process graph as BBO, a standard business process ontology.

Our YAML is a compact subset of BBO's control-flow terms. BBO says nothing about data
plumbing, so four things take an SR extension namespace: extraction paths, gathering
across a loop, derived gateway conditions, and typed process inputs.
"""

import sys
from pathlib import Path

import pytest
import rdflib
from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_graph import GRAPHS_DIR, load_graph  # noqa: E402
from tooluniverse.skill_graph_bbo import BBO, SRP, from_bbo, provenance, to_bbo  # noqa: E402

pytestmark = pytest.mark.unit

GRAPH = {
    "skill": "demo", "inputs": ["drug_name"], "optional_inputs": ["requested_aes"],
    "steps": [
        {"id": "resolve", "label": "Resolve",
         "calls": [{"tool": "OpenTargets_x", "arguments": {"n": "{drug_name}"}}],
         "extract": {"chembl_id": "data.id"},
         "repair": {"argument": "drug_name", "when_missing": "chembl_id"}},
        {"id": "signals", "requires": ["resolve"], "for_each": "aes", "as": "ae",
         "calls": [{"tool": "FAERS_x", "arguments": {"ae": "{ae}"}}],
         "collect": {"prrs": "data.prr"},
         "derive": {"strong": {"from": "prrs", "op": ">=", "value": 5,
                               "mode": "any"}}},
        {"id": "stratify", "requires": ["signals"], "when": "strong",
         "calls": [{"tool": "FAERS_y", "arguments": {}}]},
    ],
}


def _round_trip(process):
    return from_bbo(Graph().parse(data=to_bbo(process), format="turtle"))


@pytest.fixture(scope="module")
def parsed():
    return Graph().parse(data=to_bbo(GRAPH), format="turtle")


# --- it must be real RDF, not a string that looks like it -------------------

def test_the_output_parses_as_turtle(parsed):
    assert len(parsed) > 0


def test_there_is_exactly_one_process(parsed):
    assert len(list(parsed.subjects(rdflib.RDF.type, BBO.Process))) == 1


# --- the control flow BBO already describes ---------------------------------

def test_every_step_becomes_a_service_task(parsed):
    assert len(list(parsed.subjects(rdflib.RDF.type, BBO.ServiceTask))) == 3


def test_the_process_starts_and_ends_with_events(parsed):
    assert list(parsed.subjects(rdflib.RDF.type, BBO.StartEvent))
    assert list(parsed.subjects(rdflib.RDF.type, BBO.EndEvent))


def test_a_when_condition_becomes_a_gateway_with_a_conditional_flow(parsed):
    """Two gateways is correct here: one for `when: strong`, one for the repair check."""
    labels = {str(o) for s in parsed.subjects(rdflib.RDF.type, BBO.ExclusiveGateway)
              for o in parsed.objects(s, rdflib.RDFS.label)}
    assert "strong?" in labels, labels
    conditions = {str(o) for s in parsed.subjects(rdflib.RDF.type,
                                                  BBO.ConditionExpression)
                  for o in parsed.objects(s, rdflib.RDFS.label)}
    assert "strong" in conditions, conditions


def test_each_tool_is_a_software_resource_the_task_points_at(parsed):
    resources = {str(r) for r in parsed.subjects(rdflib.RDF.type, BBO.SoftwareResource)}
    assert any("FAERS_x" in r for r in resources), resources
    assert list(parsed.subject_objects(BBO.has_resource))


def test_flows_carry_source_and_target(parsed):
    assert list(parsed.subject_objects(BBO.has_sourceRef))
    assert list(parsed.subject_objects(BBO.has_targetRef))


# --- repair: a UserTask whose resource is the agent, looping back ------------

def test_repair_becomes_a_task_that_asks_and_returns(parsed):
    asks = list(parsed.subjects(rdflib.RDF.type, BBO.UserTask))
    assert len(asks) == 1, asks
    # and it flows BACK into the task it repairs
    targets = {str(t) for t in parsed.objects(None, BBO.has_targetRef)}
    assert any(t.endswith("resolve") for t in targets), targets


# --- the four things BBO has no term for ------------------------------------

def test_data_plumbing_is_carried_in_the_extension_namespace(parsed):
    for prop in (SRP.extracts, SRP.collects, SRP.derives, SRP.iterates):
        assert list(parsed.subject_objects(prop)), prop


def test_process_inputs_are_declared_and_marked_optional(parsed):
    inputs = {str(o) for o in parsed.objects(None, SRP.hasInput)}
    assert any("drug_name" in i for i in inputs), inputs
    assert list(parsed.subject_objects(SRP.optional))


# --- the shipped graphs convert -----------------------------------------------

@pytest.mark.parametrize("skill", ["adverse-event-detection",
                                   "clinical-data-integration",
                                   "rare-disease-diagnosis"])
def test_every_shipped_graph_converts_and_parses(skill):
    g = Graph().parse(data=to_bbo(load_graph(skill)), format="turtle")
    assert len(list(g.subjects(rdflib.RDF.type, BBO.ServiceTask))) >= 8


# --- the reader is the inverse of the generator -------------------------------
# What goes out as Turtle comes back as the same dict. Readable literals stay for
# people and SPARQL; a JSON literal per construct is the lossless channel.

@pytest.mark.parametrize("skill", sorted(p.stem for p in GRAPHS_DIR.glob("*.yaml")))
def test_every_shipped_process_round_trips_through_bbo(skill):
    process = load_graph(skill)

    assert _round_trip(process) == process


def test_the_published_process_carries_its_commit_and_content_hash():
    prov = provenance(Graph().parse(data=to_bbo(GRAPH, git_commit="abc1234"), format="turtle"))

    assert prov["git_commit"] == "abc1234"
    assert len(prov["definition_hash"]) == 64
    # the hash is of the definition, not of the Turtle: same dict, same hash
    assert prov["definition_hash"] == provenance(
        Graph().parse(data=to_bbo(GRAPH, git_commit="other"), format="turtle"))["definition_hash"]


# A declaration lost on the way to GraphDB would run a different process from the YAML.
@pytest.mark.parametrize("process, read", [
    ({**GRAPH, "tables": {"prr_rows": "fact", "papers": "evidence"}},
     lambda p: p["tables"]),
    # a closed list a judgement is checked against must reach the store whole and in order
    ({**GRAPH, "constants": {"ko_options": ["viable_no_phenotype", "viable_mild", "lethal"],
                             "critical_tissues": ["Heart", "Liver", "Kidney"]}},
     lambda p: p["constants"]),
    ({"skill": "d", "inputs": ["drug_name"], "steps": [
        {"id": "literature",
         "calls": [{"tool": "PubMed_search_articles", "arguments": {"query": "{drug_name}"}}],
         "narrowed": "the ten most relevant are read; the total is recorded"}]},
     lambda p: p["steps"][0]["narrowed"]),
    ({"skill": "d", "inputs": ["drug_name"], "steps": [
        {"id": "trials", "total": "total_count",
         "calls": [{"tool": "search_clinical_trials", "arguments": {"query_term": "{drug_name}"}}]}]},
     lambda p: p["steps"][0]["total"]),
    ({"skill": "d", "inputs": ["drug_name"], "optional_inputs": ["requested_aes"], "steps": [
        {"id": "requested_terms", "calls": [], "judge": ["requested_meddra"],
         "mapping": {"requested_meddra": {"of": "requested_aes",
                                          "onto": {"rows": "faers_term_rows", "field": "term"}}},
         "produces": ["requested_meddra"]}]},
     lambda p: p["steps"][0]["mapping"]),
], ids=["tables", "constants", "narrowed", "total", "mapping"])
def test_a_declaration_survives_the_round_trip(process, read):
    assert read(_round_trip(process)) == read(process)
