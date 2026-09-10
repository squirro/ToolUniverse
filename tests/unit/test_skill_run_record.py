"""The permanent Run Record (ADR-0016, DSR-725): a skeleton, never a payload.

Temporal keeps the working record for thirty days. What lasts is a few dozen
triples per run in GraphDB: which definition ran, each step's outcome, every
call with its arguments, every question with its answer — and nothing a tool
returned. Derived facts (Rung 3) will point at these IRIs.
"""

import json
import sys
from pathlib import Path

import pytest
from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_runner import SkillRunner, new_run  # noqa: E402
from tooluniverse.skill_run_record import outcome_of, skeleton, to_prov  # noqa: E402

pytestmark = pytest.mark.unit

PROV = Namespace("http://www.w3.org/ns/prov#")
SRR = Namespace("https://data.swissrockets.com/skill/run-ext#")
RUNS = "https://data.swissrockets.com/skills/runs/"

PROCESS = {
    "skill": "demo", "inputs": ["drug_name"],
    "steps": [
        {"id": "identity",
         "calls": [{"tool": "DailyMed_search_spls", "arguments": {"drug_name": "{drug_name}"}}],
         "extract": {"setid": "data.0.setid"},
         "repair": {"argument": "drug_name", "when_missing": "setid"}},
        {"id": "label", "requires": ["identity"],
         "calls": [{"tool": "DailyMed_get_label", "arguments": {"setid": "{setid}"}}],
         "produces": ["boxed_warning"], "judge": ["boxed_warning"]},
        {"id": "variant", "requires": ["identity"], "when": "variant_id",
         "calls": [{"tool": "gnomad_get_variant", "arguments": {"variant_id": "{variant_id}"}}]},
        {"id": "report", "requires": ["label"], "calls": []},
    ],
}

SECRET_PAYLOAD = "THE-LABEL-TEXT-THAT-MUST-NOT-LEAK"


def _finished_run():
    """A run through the in-memory runner: one repair, one judgement, one closed gate."""
    responses = {"DailyMed_search_spls": lambda a: {"data": []} if a["drug_name"] == "Lu-177"
                 else {"data": [{"setid": "abc-123"}]},
                 "DailyMed_get_label": lambda a: {"data": {"text": SECRET_PAYLOAD}}}
    answers = {"repair": {"drug_name": ["lu 177"]}, "judge": {"boxed_warning": "none"}}
    runner = SkillRunner(PROCESS, execute=lambda tool, a: responses[tool](a),
                         ask=lambda q: answers[q["kind"]])
    run_id = runner.start({"drug_name": "Lu-177"}, run_id="run-abc")["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass
    return runner.state(run_id)


def _skel():
    return skeleton(PROCESS, _finished_run(), run_id="run-abc",
                    definition_iri="https://data.swissrockets.com/skills/demo",
                    definition_hash="deadbeef")


def test_every_step_is_present_with_its_outcome():
    skel = _skel()
    assert skel["run_id"] == "run-abc" and skel["definition_hash"] == "deadbeef"
    assert [(s["id"], s["outcome"]) for s in skel["steps"]] == [
        ("identity", "repaired"), ("label", "done"), ("variant", "skipped"), ("report", "done")]


def test_every_call_carries_its_arguments_including_the_retry():
    identity = next(s for s in _skel()["steps"] if s["id"] == "identity")
    assert [c["arguments"]["drug_name"] for c in identity["calls"]] == ["Lu-177", "lu 177"]
    assert all(c["tool"] == "DailyMed_search_spls" for c in identity["calls"])


def test_every_question_is_present_with_its_answer_and_no_context():
    skel = _skel()
    questions = [(s["id"], q["kind"], q["answer"]) for s in skel["steps"] for q in s["questions"]]
    assert questions == [("identity", "repair", {"drug_name": ["lu 177"]}),
                         ("label", "judge", {"boxed_warning": "none"})]
    assert "context" not in json.dumps(skel)


def test_no_payload_reaches_the_record():
    assert SECRET_PAYLOAD not in json.dumps(_skel())
    assert "results" not in json.dumps(_skel())


def test_a_blocked_and_an_unresolved_step_get_those_outcomes():
    run = new_run({})
    run["done"] = ["a", "b"]
    run["skipped"] = ["c"]
    run["blocked"] = [{"step": "c", "reason": "cannot build the call: missing x"}]
    run["unresolved"] = [{"step": "b", "fact": "genes"}]
    assert outcome_of("a", run) == "done"
    assert outcome_of("b", run) == "unresolved"
    assert outcome_of("c", run) == "blocked"
    assert outcome_of("never-offered", run) == "skipped"


# --- the RDF: IRIs only, PROV-O, nothing but the skeleton ------------------------

def _graph():
    return Graph().parse(data=to_prov(_skel()), format="turtle")


def test_the_record_parses_and_has_no_blank_nodes():
    g = _graph()
    assert len(g) > 0
    assert not any(isinstance(n, BNode) for t in g for n in t)


def test_the_run_is_an_activity_that_used_the_definition_at_its_hash():
    g = _graph()
    run = URIRef(RUNS + "run-abc")
    assert (run, RDF.type, PROV.Activity) in g
    assert (run, PROV.used, URIRef("https://data.swissrockets.com/skills/demo")) in g
    assert (run, SRR.definitionHash, Literal("deadbeef")) in g
    assert (run, SRR.skill, Literal("demo")) in g


def test_each_step_is_an_activity_informed_by_the_run_with_its_outcome():
    g = _graph()
    run = URIRef(RUNS + "run-abc")
    identity = URIRef(RUNS + "run-abc/step/identity")
    assert (identity, RDF.type, PROV.Activity) in g
    assert (identity, PROV.wasInformedBy, run) in g
    assert (identity, SRR.outcome, Literal("repaired")) in g
    assert (URIRef(RUNS + "run-abc/step/variant"), SRR.outcome, Literal("skipped")) in g


def test_each_call_is_an_activity_under_its_step_with_its_arguments_as_json():
    g = _graph()
    identity = URIRef(RUNS + "run-abc/step/identity")
    retry = URIRef(RUNS + "run-abc/step/identity/call/1")
    assert (retry, PROV.wasInformedBy, identity) in g
    assert (retry, SRR.tool, Literal("DailyMed_search_spls")) in g
    assert (retry, SRR.arguments, Literal(json.dumps({"drug_name": "lu 177"}, sort_keys=True))) in g


def test_each_question_is_an_entity_generated_by_its_step_with_the_answer():
    g = _graph()
    q = URIRef(RUNS + "run-abc/step/identity/question/0")
    assert (q, RDF.type, PROV.Entity) in g
    assert (q, PROV.wasGeneratedBy, URIRef(RUNS + "run-abc/step/identity")) in g
    assert (q, SRR.kind, Literal("repair")) in g
    assert (q, SRR.answer, Literal(json.dumps({"drug_name": ["lu 177"]}, sort_keys=True))) in g


def test_no_payload_reaches_the_graph_either():
    assert SECRET_PAYLOAD not in to_prov(_skel())
