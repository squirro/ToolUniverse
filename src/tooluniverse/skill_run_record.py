"""The permanent Run Record: a PROV-O skeleton of one Skill Run.

Temporal keeps the working record only for a while; this is what lasts. The skeleton is
pure Python so the sandboxed workflow can build it, and the RDF is made inside the
activity that writes it. It holds which definition ran, each step's outcome, every call
with its arguments and every question with its answer, but no payload; its nodes are
minted IRIs, never blank, so derived facts can point at them.
"""
from __future__ import annotations

import json

from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

from .skill_process_store import RUNS_BASE

PROV = Namespace("http://www.w3.org/ns/prov#")
SRR = Namespace("https://data.swissrockets.com/skill/run-ext#")

OUTCOMES = ("done", "repaired", "blocked", "unresolved", "skipped")


def outcome_of(step_id: str, run: dict) -> str:
    """One word per step. Blocked beats unresolved beats repaired beats done."""
    if any(b["step"] == step_id for b in run["blocked"]):
        return "blocked"
    if any(u["step"] == step_id for u in run["unresolved"]):
        return "unresolved"
    if step_id in run["done"]:
        if any(q["step"] == step_id and q["kind"] == "repair" for q in run["questions"]):
            return "repaired"
        return "done"
    return "skipped"


def skeleton(process: dict, run: dict, *, run_id: str,
             definition_iri: str, definition_hash: str, started: str | None = None,
             inputs: dict | None = None) -> dict:
    """What the record holds, as plain data. Pure.

    `started` and `inputs` let a Saved Analysis list its runs (SA-12); older callers omit them.
    """
    steps = []
    for spec in process["steps"]:
        sid = spec["id"]
        steps.append({
            "id": sid,
            "outcome": outcome_of(sid, run),
            "calls": [{"tool": c["tool"], "arguments": c["arguments"]}
                      for c in run["calls_made"].get(sid, [])],
            "questions": [{"kind": q["kind"], "wants": q["wants"], "answer": q["answer"]}
                          for q in run["questions"] if q["step"] == sid],
        })
    extra = {k: v for k, v in (("started", started), ("inputs", inputs)) if v is not None}
    return {"run_id": run_id, "skill": process["skill"],
            "definition_iri": definition_iri, "definition_hash": definition_hash,
            "steps": steps, **extra}


def _lit(value) -> Literal:
    return Literal(json.dumps(value, sort_keys=True, default=str))


def to_prov(skel: dict) -> str:
    """The skeleton as PROV-O Turtle. Every node is an IRI minted from the run id."""
    g = Graph()
    g.bind("prov", PROV)
    g.bind("srr", SRR)
    run = URIRef(RUNS_BASE + skel["run_id"])
    g.add((run, RDF.type, PROV.Activity))
    g.add((run, RDFS.label, Literal(f"Skill Run {skel['run_id']}")))
    g.add((run, PROV.used, URIRef(skel["definition_iri"])))
    g.add((run, SRR.skill, Literal(skel["skill"])))
    g.add((run, SRR.definitionHash, Literal(skel["definition_hash"])))
    if skel.get("started"):
        g.add((run, SRR.started, Literal(skel["started"], datatype=XSD.dateTime)))
    if "inputs" in skel:
        g.add((run, SRR.inputs, _lit(skel["inputs"])))
    for order, step in enumerate(skel["steps"]):
        s = URIRef(f"{run}/step/{step['id']}")
        g.add((s, RDF.type, PROV.Activity))
        g.add((s, PROV.wasInformedBy, run))
        g.add((s, SRR.stepId, Literal(step["id"])))
        g.add((s, SRR.order, Literal(order)))
        g.add((s, SRR.outcome, Literal(step["outcome"])))
        for n, call in enumerate(step["calls"]):
            c = URIRef(f"{s}/call/{n}")
            g.add((c, RDF.type, PROV.Activity))
            g.add((c, PROV.wasInformedBy, s))
            g.add((c, SRR.tool, Literal(call["tool"])))
            g.add((c, SRR.arguments, _lit(call["arguments"])))
        for n, q in enumerate(step["questions"]):
            e = URIRef(f"{s}/question/{n}")
            g.add((e, RDF.type, PROV.Entity))
            g.add((e, PROV.wasGeneratedBy, s))
            g.add((e, SRR.kind, Literal(q["kind"])))
            g.add((e, SRR.wants, _lit(q["wants"])))
            g.add((e, SRR.answer, _lit(q["answer"])))
    return g.serialize(format="turtle")
