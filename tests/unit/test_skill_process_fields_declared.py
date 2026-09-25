"""Every value a shipped process reads is declared in its tool's return schema.

A process reads results by path (`collect` and `extract`, optionally with `fields`). A path
the schema does not declare is a promise the contract does not make: when the payload lacks
it the step quietly gathers nothing, and when the payload has it the schema is wrong for
every other reader. Paths resolve as the runner resolves them (`_dig`): dotted keys, a digit
indexes a list, `key[]` maps over a list.

What the runner sees is not always the tool's bare return. The walk models what reaches it:
a non-dict return arrives as {"result": ...} (normalised_executor), and the central layer
stamps `source_url` and the transport keys on every dict result. A step with several calls
reads each value from whichever call's payload carries it, so a rule needs one of its step's
tools to declare it, not all of them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import tooluniverse

pytestmark = pytest.mark.unit

DATA = Path(tooluniverse.__file__).parent / "data"
PROCESSES = sorted((DATA / "skill_graphs").glob("*.yaml"))

# Stamped on every dict result by tools_sr.source_url and tools_sr.transport_status.
CENTRAL = {"source_url": {"type": "string"},
           "transport_status": {"type": "string"},
           "transport_note": {"type": "string"}}


def _tools() -> dict[str, dict]:
    tools: dict[str, dict] = {}
    for path in sorted(DATA.glob("*.json")):
        try:
            defs = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue  # a broken definition file is the wiring test's finding, not this one's
        if isinstance(defs, list):
            for tool in defs:
                if isinstance(tool, dict) and "name" in tool:
                    tools.setdefault(tool["name"], tool)
    return tools


def _types(schema: dict) -> set:
    t = schema.get("type")
    return set(t) if isinstance(t, list) else {t} if t else set()


def _variants(schema) -> list[dict]:
    """A schema and each of its anyOf / oneOf branches, siblings carried into each branch."""
    if not isinstance(schema, dict):
        return []
    branches = schema.get("anyOf") or schema.get("oneOf")
    if not branches:
        return [schema]
    base = {k: v for k, v in schema.items() if k not in ("anyOf", "oneOf")}
    out = [base] if base.get("properties") or base.get("items") else []
    for branch in branches:
        out.extend(_variants({**base, **branch} if isinstance(branch, dict) else branch))
    return out


def _delivered(schema: dict) -> list[dict]:
    """The shapes the runner receives for this return schema."""
    shapes = []
    for variant in _variants(schema):
        types = _types(variant)
        if types and "object" not in types:
            shapes.append({"type": "object", "properties": {"result": variant, **CENTRAL}})
        else:
            shapes.append({**variant, "properties": {**CENTRAL, **(variant.get("properties") or {})}})
    return shapes


def _step(schema: dict, key: str) -> list[dict]:
    out = []
    for variant in _variants(schema):
        if key.isdigit():
            if "items" in variant:
                out.append(variant["items"])
        elif key in (variant.get("properties") or {}):
            out.append(variant["properties"][key])
        elif isinstance(variant.get("additionalProperties"), dict):
            out.append(variant["additionalProperties"])
    return out


def _resolve(schemas: list[dict], path: str) -> list[dict]:
    """The schemas at `path`, walking as _dig walks; empty when nothing declares it."""
    current = schemas
    for part in path.split("."):
        mapped = part.endswith("[]")
        key = part[:-2] if mapped else part
        if key:
            current = [s for schema in current for s in _step(schema, key)]
        if mapped:
            current = [v["items"] for schema in current for v in _variants(schema) if "items" in v]
        if not current:
            return []
    return current


def _records(schemas: list[dict]) -> list[dict]:
    """What `fields` are read from: the items of a list, or the object itself."""
    out = []
    for schema in schemas:
        for variant in _variants(schema):
            out.append(variant["items"] if "items" in variant else variant)
    return out


def _rules(graph: dict):
    for step in graph.get("steps", []):
        tools = list(dict.fromkeys(c["tool"] for c in step.get("calls") or [] if c.get("tool")))
        if not tools:
            continue
        for kind in ("collect", "extract"):
            for fact, rule in (step.get(kind) or {}).items():
                rule = rule if isinstance(rule, dict) else {"path": rule}
                if isinstance(rule.get("path"), str):
                    yield step["id"], f"{kind}.{fact}", tools, rule


def undeclared(graph: dict, tools: dict[str, dict]) -> list[str]:
    """Each rule no tool of its step declares, naming the path or fields that fail."""
    findings = []
    for step_id, name, step_tools, rule in _rules(graph):
        fields = [f.partition(" as ")[0].strip() for f in rule.get("fields") or []]
        fields = [f for f in fields if not f.startswith("$")]
        reasons = []
        for tool_name in step_tools:
            schema = (tools.get(tool_name) or {}).get("return_schema")
            if not schema:
                reasons.append(f"{tool_name} has no return_schema")
                continue
            found = _resolve(_delivered(schema), rule["path"])
            if not found:
                reasons.append(f"{tool_name} does not declare `{rule['path']}`")
                continue
            records = _records(found)
            missing = [f for f in fields if not _resolve(records, f)]
            if not missing:
                reasons = []
                break
            reasons.append(f"{tool_name} does not declare {', '.join(f'`{m}`' for m in missing)}")
        if reasons:
            findings.append(f"{step_id}/{name}: " + "; ".join(reasons))
    return findings


@pytest.mark.parametrize("process", PROCESSES, ids=lambda p: p.stem)
def test_every_value_a_process_reads_is_declared_by_its_tool(process):
    findings = undeclared(yaml.safe_load(process.read_text()), _tools())
    assert not findings, "\n".join(findings)


# --- proof the walk can fail, and does not fail on what the runner really sees ---

_TOOLS = {
    "rows": {"return_schema": {"type": "object", "properties": {"data": {
        "type": "array", "items": {"type": "object", "properties": {"id": {}, "name": {}}}}}}},
    "bare_list": {"return_schema": {"type": "array", "items": {"type": "string"}}},
    "other": {"return_schema": {"type": "object", "properties": {"tdl": {}}}},
}


def _graph(*steps):
    return {"steps": list(steps)}


def test_an_undeclared_field_is_named():
    graph = _graph({"id": "s", "calls": [{"tool": "rows"}],
                    "collect": {"r": {"path": "data", "fields": ["id", "rsId as rs"]}}})
    assert undeclared(graph, _TOOLS) == ["s/collect.r: rows does not declare `rsId`"]


def test_an_undeclared_path_is_named():
    graph = _graph({"id": "s", "calls": [{"tool": "rows"}], "extract": {"x": "data.hits.0.symbol"}})
    assert undeclared(graph, _TOOLS) == ["s/extract.x: rows does not declare `data.hits.0.symbol`"]


def test_mapped_and_indexed_paths_resolve_as_the_runner_digs():
    graph = _graph({"id": "s", "calls": [{"tool": "rows"}],
                    "extract": {"a": "data[].name", "b": "data.0.id"}})
    assert undeclared(graph, _TOOLS) == []


def test_a_bare_list_is_read_under_result_and_a_stamped_source_url_is_there():
    graph = _graph({"id": "s", "calls": [{"tool": "bare_list"}],
                    "extract": {"a": "result.0"},
                    "collect": {"b": {"path": "", "fields": ["source_url"]}}})
    assert undeclared(graph, _TOOLS) == []


def test_one_tool_of_a_step_declaring_a_value_is_enough_and_none_is_not():
    both = {"id": "s", "calls": [{"tool": "rows"}, {"tool": "other"}]}
    assert undeclared(_graph({**both, "extract": {"t": "tdl"}}), _TOOLS) == []
    assert undeclared(_graph({**both, "extract": {"v": "version"}}), _TOOLS) == [
        "s/extract.v: rows does not declare `version`; other does not declare `version`"]
