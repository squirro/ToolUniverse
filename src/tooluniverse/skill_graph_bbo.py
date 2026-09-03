"""Render a skill's process graph as BBO — the notation the Novartis PoC uses.

BBO is an OWL rendering of BPMN. The Novartis HR processes
(`data/kg/*_process.ttl`) use `Process`, `ServiceTask`, `UserTask`,
`StartEvent`, `EndEvent`, `ExclusiveGateway`, `NormalSequenceFlow`,
`ConditionalSequenceFlow` with a `ConditionExpression`, and `has_resource` onto a
`SoftwareResource` or `HumanResource`. Our YAML graphs are a compact subset of
precisely that, so the structural half of the conversion is mechanical.

It belongs in a generator rather than in hand-written Turtle. `repair` is one
block a person can read and four nodes a graph must draw — a ServiceTask, a
gateway asking whether the value resolved, a task that asks the agent, and a flow
back into the task it repairs. Nobody should edit four nodes to change "try
twice" into "try three times".

BBO describes control flow and says nothing about data plumbing. Four things in
our graphs therefore have no BBO term and ride in an SR extension namespace:
extraction paths, gathering across a loop's calls, a gateway condition derived
from returned values, and typed process inputs. Novartis needed the same and
answered it with `ontology_extensions.ttl`.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import XSD

BBO = Namespace("https://www.irit.fr/recherches/MELODI/ontologies/BBO#")
SRP = Namespace("https://data.swissrockets.com/skill/process-ext#")
SR = Namespace("https://data.swissrockets.com/skill/process/")
RES = Namespace("https://data.swissrockets.com/skill/resource/")


def _node(skill: str, local: str) -> URIRef:
    return SR[f"{skill}/{local}"]


def definition_hash(graph: dict) -> str:
    """The hash of the definition itself, not of any one serialisation of it."""
    return hashlib.sha256(
        json.dumps(graph, sort_keys=True, default=str).encode()).hexdigest()


def to_bbo(graph: dict, git_commit: str | None = None) -> str:
    """Serialise one process graph as BBO Turtle."""
    skill = graph["skill"]
    g = Graph()
    for prefix, ns in (("bbo", BBO), ("srp", SRP), ("srproc", SR), ("srres", RES)):
        g.bind(prefix, ns)

    process = _node(skill, "Process")
    g.add((process, RDF.type, BBO.Process))
    g.add((process, RDFS.label, Literal(skill)))
    # Provenance: a Skill Run carries these, so a record can be matched to the
    # repo revision it executed after the skill has changed.
    g.add((process, SRP.definitionHash, Literal(definition_hash(graph))))
    if git_commit:
        g.add((process, SRP.gitCommit, Literal(git_commit)))

    # Typed process inputs — what the AGENT must bind from the question. The one
    # boundary that stays with the model, so it is declared rather than implied.
    for order, name in enumerate(graph.get("inputs", [])):
        _declare_input(g, process, skill, name, optional=False, order=order)
    for order, name in enumerate(graph.get("optional_inputs", [])):
        _declare_input(g, process, skill, name, optional=True, order=order)

    steps = graph["steps"]
    start = _node(skill, "Start")
    end = _node(skill, "End")
    g.add((start, RDF.type, BBO.StartEvent))
    g.add((end, RDF.type, BBO.EndEvent))
    for element in (start, end):
        g.add((process, BBO.has_flowElements, element))

    for order, step in enumerate(steps):
        _task(g, process, skill, step, order)

    _flows(g, process, skill, steps, start, end)
    return g.serialize(format="turtle")


def _declare_input(g: Graph, process: URIRef, skill: str, name: str,
                   optional: bool, order: int) -> None:
    node = _node(skill, f"input/{name}")
    g.add((node, RDF.type, SRP.ProcessInput))
    g.add((node, RDFS.label, Literal(name)))
    g.add((node, SRP.order, Literal(order, datatype=XSD.integer)))
    g.add((process, SRP.hasInput, node))
    if optional:
        g.add((node, SRP.optional, Literal(True, datatype=XSD.boolean)))


def _task(g: Graph, process: URIRef, skill: str, step: dict, order: int) -> None:
    task = _node(skill, step["id"])
    g.add((task, RDF.type, BBO.ServiceTask))
    g.add((task, RDFS.label, Literal(step.get("label", step["id"]))))
    g.add((task, SRP.order, Literal(order, datatype=XSD.integer)))
    g.add((process, BBO.has_flowElements, task))
    if step.get("notes"):
        g.add((task, RDFS.comment, Literal(step["notes"])))
    # The lossless channel: the reader rebuilds the step from these, while the
    # readable literals below serve people and SPARQL.
    for key, prop in _JSON_SPECS.items():
        if key in step:
            g.add((task, prop, Literal(json.dumps(step[key], sort_keys=True))))

    # Every tool is a resource the task points at — the same hook Novartis uses
    # for its knowledge graph, and where Biolink I/O types would hang (DSR-688).
    for call in step.get("calls", []):
        resource = RES[call["tool"]]
        g.add((resource, RDF.type, BBO.SoftwareResource))
        g.add((resource, RDFS.label, Literal(call["tool"])))
        g.add((task, BBO.has_resource, resource))
        if call.get("arguments"):
            g.add((task, SRP.callArguments,
                   Literal(json.dumps({call["tool"]: call["arguments"]},
                                      sort_keys=True))))

    # --- the four things BBO has no term for ---
    for name, rule in (step.get("extract") or {}).items():
        g.add((task, SRP.extracts, Literal(f"{name} = {_rule(rule)}")))
    for name, rule in (step.get("collect") or {}).items():
        path = rule["path"] if isinstance(rule, dict) else rule
        match = f" matching {rule['match']}" if isinstance(rule, dict) and rule.get("match") else ""
        g.add((task, SRP.collects, Literal(f"{name} = {path}{match} (every call)")))
    for name, rule in (step.get("derive") or {}).items():
        g.add((task, SRP.derives,
               Literal(f"{name} = {rule.get('mode', 'any')} {rule['from']}"
                       f"{'.' + rule['field'] if rule.get('field') else ''} "
                       f"{rule.get('op', '==')} {rule.get('value')}")))
    if step.get("for_each"):
        g.add((task, SRP.iterates, Literal(step["for_each"])))
        g.add((task, SRP.iterationVariable, Literal(step.get("as", "item"))))
    for name in (step.get("combine") or {}):
        g.add((task, SRP.combines, Literal(name)))


# YAML key -> the srp: property that carries it verbatim, as JSON.
_JSON_SPECS = {
    "calls": SRP.callsSpec,
    "extract": SRP.extractSpec,
    "collect": SRP.collectSpec,
    "combine": SRP.combineSpec,
    "derive": SRP.deriveSpec,
    "produces": SRP.produces,
    "judge": SRP.judges,
}


def _rule(rule: Any) -> str:
    if not isinstance(rule, dict):
        return str(rule)
    parts = [rule["path"]]
    for key in ("regex", "limit", "default_from"):
        if rule.get(key) is not None:
            parts.append(f"{key}={rule[key]}")
    return " ".join(str(p) for p in parts)


def _flow(g: Graph, process: URIRef, source: URIRef, target: URIRef,
          uri: URIRef, conditional: str | None = None) -> None:
    g.add((uri, RDF.type,
           BBO.ConditionalSequenceFlow if conditional else BBO.NormalSequenceFlow))
    g.add((uri, BBO.has_sourceRef, source))
    g.add((uri, BBO.has_targetRef, target))
    g.add((source, BBO.has_outgoing, uri))
    g.add((target, BBO.has_incoming, uri))
    g.add((process, BBO.has_flowElements, uri))
    if conditional:
        expression = URIRef(str(uri) + "/condition")
        g.add((expression, RDF.type, BBO.ConditionExpression))
        g.add((expression, RDFS.label, Literal(conditional)))
        g.add((uri, BBO.has_conditionExpression, expression))


def _flows(g: Graph, process: URIRef, skill: str, steps: list[dict],
           start: URIRef, end: URIRef) -> None:
    ids = [s["id"] for s in steps]
    for step in steps:
        task = _node(skill, step["id"])
        sources = step.get("requires") or []

        if not sources:
            _flow(g, process, start, task, _node(skill, f"flow/start-{step['id']}"))
        for dep in sources:
            _gated_flow(g, process, skill, step, _node(skill, dep), task)

        # A step nothing depends on ends the process.
        if not any(step["id"] in (other.get("requires") or []) for other in steps):
            _flow(g, process, task, end, _node(skill, f"flow/{step['id']}-end"))

        if step.get("repair"):
            _repair(g, process, skill, step, task)
    assert ids  # every step reachable is checked by the graph's own guard tests


def _gated_flow(g: Graph, process: URIRef, skill: str, step: dict,
                source: URIRef, task: URIRef) -> None:
    """A `when:` becomes a real gateway, not an attribute the reader must notice."""
    condition = step.get("when")
    if not condition:
        _flow(g, process, source, task,
              _node(skill, f"flow/{source.split('/')[-1]}-{step['id']}"))
        return
    gateway = _node(skill, f"gateway/{step['id']}")
    g.add((gateway, RDF.type, BBO.ExclusiveGateway))
    g.add((gateway, RDFS.label, Literal(f"{condition}?")))
    g.add((process, BBO.has_flowElements, gateway))
    _flow(g, process, source, gateway,
          _node(skill, f"flow/{source.split('/')[-1]}-gw-{step['id']}"))
    _flow(g, process, gateway, task,
          _node(skill, f"flow/gw-{step['id']}-yes"), conditional=condition)


def _repair(g: Graph, process: URIRef, skill: str, step: dict,
            task: URIRef) -> None:
    """Ask-and-retry as four nodes: gateway, ask task, agent resource, loop back.

    The agent supplies world knowledge the data does not hold — that "Lu-177" and
    "lu 177" name one isotope. Novartis writes a human in this position as a
    UserTask with a HumanResource; this is the same task with an agent resource.
    """
    repair = step["repair"]
    gateway = _node(skill, f"gateway/{step['id']}-resolved")
    ask = _node(skill, f"{step['id']}-ask-agent")
    agent = RES["ConversationalAgent"]

    g.add((gateway, RDF.type, BBO.ExclusiveGateway))
    g.add((gateway, RDFS.label, Literal(f"{repair['when_missing']} resolved?")))
    g.add((process, BBO.has_flowElements, gateway))

    g.add((ask, RDF.type, BBO.UserTask))
    g.add((ask, RDFS.label,
           Literal(f"Ask the agent for another {repair['argument']}")))
    g.add((ask, BBO.has_resource, agent))
    g.add((agent, RDF.type, BBO.HumanResource))
    g.add((agent, RDFS.label, Literal("Conversational agent (world knowledge)")))
    g.add((ask, SRP.repairsArgument, Literal(repair["argument"])))
    g.add((ask, SRP.whenMissing, Literal(repair["when_missing"])))
    g.add((ask, SRP.maxAttempts, Literal(2, datatype=XSD.integer)))
    g.add((process, BBO.has_flowElements, ask))

    _flow(g, process, task, gateway, _node(skill, f"flow/{step['id']}-check"))
    _flow(g, process, gateway, ask, _node(skill, f"flow/{step['id']}-repair"),
          conditional=f"{repair['when_missing']} missing")
    _flow(g, process, ask, task, _node(skill, f"flow/{step['id']}-retry"))


# --- the inverse: a process dict from the graph (DSR-709) -----------------------

def _local(node: URIRef, skill: str) -> str:
    return str(node)[len(str(SR[skill])) + 1:]


def provenance(g: Graph) -> dict:
    """What the published copy says about its origin."""
    process = next(g.subjects(RDF.type, BBO.Process))
    return {
        "definition_hash": str(g.value(process, SRP.definitionHash) or ""),
        "git_commit": str(g.value(process, SRP.gitCommit) or "") or None,
    }


def from_bbo(g: Graph) -> dict:
    """Rebuild the process dict the generator was given.

    Control flow comes back from the BBO elements — order, flows, gateways, the
    repair cluster — and the data plumbing from the JSON literals. Only keys the
    original had are produced, so `from_bbo(parse(to_bbo(p))) == p`.
    """
    process = next(g.subjects(RDF.type, BBO.Process))
    skill = str(g.value(process, RDFS.label))
    out: dict = {"skill": skill}

    inputs = sorted(g.objects(process, SRP.hasInput),
                    key=lambda n: int(g.value(n, SRP.order) or 0))
    required = [str(g.value(n, RDFS.label)) for n in inputs
                if not g.value(n, SRP.optional)]
    optional = [str(g.value(n, RDFS.label)) for n in inputs if g.value(n, SRP.optional)]
    if required:
        out["inputs"] = required
    if optional:
        out["optional_inputs"] = optional

    tasks = sorted(g.subjects(RDF.type, BBO.ServiceTask),
                   key=lambda n: int(g.value(n, SRP.order) or 0))
    order_of = {t: i for i, t in enumerate(tasks)}
    out["steps"] = [_step(g, skill, task, order_of) for task in tasks]
    return out


def _step(g: Graph, skill: str, task: URIRef, order_of: dict) -> dict:
    step: dict = {"id": _local(task, skill)}
    label = str(g.value(task, RDFS.label) or "")
    if label and label != step["id"]:
        step["label"] = label

    # Dependencies and the gate: a flow in from a task, or from the step's own
    # gateway, whose flows in name the real sources and whose conditional flow
    # names the fact.
    sources, condition = [], None
    for flow in g.subjects(BBO.has_targetRef, task):
        source = g.value(flow, BBO.has_sourceRef)
        if (source, RDF.type, BBO.ServiceTask) in g:
            sources.append(source)
        elif (source, RDF.type, BBO.ExclusiveGateway) in g and \
                _local(source, skill) == f"gateway/{step['id']}":
            expression = g.value(flow, BBO.has_conditionExpression)
            condition = str(g.value(expression, RDFS.label)) if expression else None
            for inner in g.subjects(BBO.has_targetRef, source):
                sources.append(g.value(inner, BBO.has_sourceRef))
    if sources:
        step["requires"] = [_local(s, skill) for s in
                            sorted(sources, key=lambda s: order_of[s])]
    if condition:
        step["when"] = condition

    if (value := g.value(task, SRP.iterates)) is not None:
        step["for_each"] = str(value)
        step["as"] = str(g.value(task, SRP.iterationVariable) or "item")

    for key, prop in _JSON_SPECS.items():
        if (value := g.value(task, prop)) is not None:
            step[key] = json.loads(str(value))

    ask = _node(skill, f"{step['id']}-ask-agent")
    if (argument := g.value(ask, SRP.repairsArgument)) is not None:
        step["repair"] = {"argument": str(argument),
                          "when_missing": str(g.value(ask, SRP.whenMissing))}

    if (notes := g.value(task, RDFS.comment)) is not None:
        step["notes"] = str(notes)
    return step
