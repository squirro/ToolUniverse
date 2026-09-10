"""Emit a skill's process graph as BBO, the notation the Novartis PoC used.

Novartis models its HR processes in BBO — `Process`, `ServiceTask`, `UserTask`,
`ExclusiveGateway`, `NormalSequenceFlow`, `ConditionalSequenceFlow` with a
`ConditionExpression`, and `has_resource` onto a `SoftwareResource` or
`HumanResource`. Our YAML is a compact subset of exactly that, so the structural
half of the conversion is mechanical and belongs in a generator, not in hand-
written Turtle: `repair` is one block to read and four nodes to draw, and nobody
should edit four nodes to change "try twice" to "try three times".

BBO describes control flow and says nothing about data plumbing, so four things
have no BBO term and take an SR extension namespace — extraction paths, gathering
across a loop, derived gateway conditions, and typed process inputs. Novartis hit
the same wall and answered it with `data/kg/ontology_extensions.ttl`.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_graph_bbo import BBO, SRP, to_bbo

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


@pytest.fixture(scope="module")
def turtle():
    return to_bbo(GRAPH)


@pytest.fixture(scope="module")
def parsed(turtle):
    rdflib = pytest.importorskip("rdflib")
    g = rdflib.Graph()
    g.parse(data=turtle, format="turtle")
    return g


# --- it must be real RDF, not a string that looks like it -------------------

def test_the_output_parses_as_turtle(parsed):
    assert len(parsed) > 0


def test_there_is_exactly_one_process(parsed):
    import rdflib
    procs = list(parsed.subjects(rdflib.RDF.type, BBO.Process))
    assert len(procs) == 1


# --- the control flow BBO already describes ---------------------------------

def test_every_step_becomes_a_service_task(parsed):
    import rdflib
    tasks = list(parsed.subjects(rdflib.RDF.type, BBO.ServiceTask))
    assert len(tasks) == 3


def test_the_process_starts_and_ends_with_events(parsed):
    import rdflib
    assert list(parsed.subjects(rdflib.RDF.type, BBO.StartEvent))
    assert list(parsed.subjects(rdflib.RDF.type, BBO.EndEvent))


def test_a_when_condition_becomes_a_gateway_with_a_conditional_flow(parsed):
    """Two gateways is correct here: one for `when: strong`, one for the repair
    check — the repair loop is a gateway in its own right."""
    import rdflib
    labels = {str(o) for s in parsed.subjects(rdflib.RDF.type, BBO.ExclusiveGateway)
              for o in parsed.objects(s, rdflib.RDFS.label)}
    assert "strong?" in labels, labels
    conditions = {str(o) for s in parsed.subjects(rdflib.RDF.type,
                                                  BBO.ConditionExpression)
                  for o in parsed.objects(s, rdflib.RDFS.label)}
    assert "strong" in conditions, conditions


def test_each_tool_is_a_software_resource_the_task_points_at(parsed):
    import rdflib
    resources = {str(r) for r in parsed.subjects(rdflib.RDF.type, BBO.SoftwareResource)}
    assert any("FAERS_x" in r for r in resources), resources
    assert list(parsed.subject_objects(BBO.has_resource))


def test_flows_carry_source_and_target(parsed):
    assert list(parsed.subject_objects(BBO.has_sourceRef))
    assert list(parsed.subject_objects(BBO.has_targetRef))


# --- repair: a UserTask whose resource is the agent, looping back ------------

def test_repair_becomes_a_task_that_asks_and_returns(parsed):
    import rdflib
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
    rdflib = pytest.importorskip("rdflib")
    g = rdflib.Graph()
    g.parse(data=to_bbo(load_graph(skill)), format="turtle")
    assert len(list(g.subjects(rdflib.RDF.type, BBO.ServiceTask))) >= 8


# --- the reader is the inverse of the generator (DSR-709) ---------------------
# The proof that BBO plus the srp: extension expresses every construct a shipped
# process uses: what goes out as Turtle comes back as the same dict. Readable
# literals stay for people and SPARQL; a JSON literal per construct is the
# lossless channel the reader uses.

from rdflib import Graph  # noqa: E402

from tooluniverse.skill_graph import GRAPHS_DIR  # noqa: E402
from tooluniverse.skill_graph_bbo import from_bbo, provenance  # noqa: E402


@pytest.mark.parametrize("skill", sorted(p.stem for p in GRAPHS_DIR.glob("*.yaml")))
def test_every_shipped_process_round_trips_through_bbo(skill):
    process = load_graph(skill)

    turtle = to_bbo(process)
    back = from_bbo(Graph().parse(data=turtle, format="turtle"))

    assert back == process


def test_the_published_process_carries_its_commit_and_content_hash():
    turtle = to_bbo(GRAPH, git_commit="abc1234")
    g = Graph().parse(data=turtle, format="turtle")

    prov = provenance(g)

    assert prov["git_commit"] == "abc1234"
    assert len(prov["definition_hash"]) == 64
    # the hash is of the definition, not of the Turtle: same dict, same hash
    assert prov["definition_hash"] == provenance(
        Graph().parse(data=to_bbo(GRAPH, git_commit="other"), format="turtle"))["definition_hash"]
