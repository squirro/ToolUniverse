"""Skills as a process graph — the plan lives in data, not in the model's head.

A served skill body is a standing operating procedure written as prose: nine
phases, each naming its tools, with gateways expressed in capital letters ("pick
the first applicable, then STOP"). The agent is handed all of it at once and asked
to remember it while doing the work. Measured on sr-dev on 2026-08-21 with three
probes per skill, four of the first eight skills returned a different verdict
across three identical runs, and a citation rule delivered on every single turn was
ignored on 29 of 76 answers. Soft pressure has plateaued.

This module holds the same procedure as a graph. `next_step` is pure and stateless:
give it the graph, the step ids already done, and the facts gathered so far, and it
returns the ONE step to run now — with the exact tool calls and their arguments
already filled in. The agent stops planning and starts executing, which is the
only class of technique that binds rather than persuades (the others being tool
masking and schema-constrained arguments).

Deliberately not a workflow engine. There is no server-side state: the caller
passes back what it has done, exactly as an MCP tool call must. If this earns its
keep on one skill, running the same graph under a durable engine is the next step,
not a prerequisite.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

# Package data, not deploy/: the image installs `src` and nothing else, so a graph
# under deploy/ would silently not exist in the container. Overridable for local
# iteration and, later, for a projection compiled out of GraphDB.
GRAPHS_DIR = Path(
    os.environ.get("TU_SKILL_GRAPHS_DIR")
    or Path(__file__).resolve().parent / "data" / "skill_graphs"
)

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class SkillGraphError(RuntimeError):
    """No graph for that skill, or the graph cannot be run with these facts."""


def load_graph(skill: str, graphs_dir: str | Path | None = None) -> dict:
    """Load the process graph for one skill."""
    directory = Path(graphs_dir) if graphs_dir else GRAPHS_DIR
    path = directory / f"{skill}.yaml"
    if not path.is_file():
        available = sorted(p.stem for p in directory.glob("*.yaml")) \
            if directory.is_dir() else []
        raise SkillGraphError(
            f"no process graph for {skill!r}; available: {available}")
    graph = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or not graph.get("steps"):
        raise SkillGraphError(f"graph for {skill!r} has no steps")
    return graph


def _fill(value: Any, facts: dict) -> Any:
    """Substitute {placeholders} from facts, naming any that are missing."""
    if isinstance(value, dict):
        return {k: _fill(v, facts) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill(v, facts) for v in value]
    if not isinstance(value, str):
        return value
    missing = [name for name in _PLACEHOLDER.findall(value) if name not in facts]
    if missing:
        raise SkillGraphError(
            f"cannot build the call: missing {', '.join(sorted(set(missing)))}")
    # A lone placeholder keeps its type; embedded ones are string-substituted.
    whole = _PLACEHOLDER.fullmatch(value)
    if whole:
        return facts[whole.group(1)]
    return _PLACEHOLDER.sub(lambda m: str(facts[m.group(1)]), value)


def _is_runnable(step: dict, done: set[str], facts: dict) -> bool:
    if step["id"] in done:
        return False
    if any(dep not in done for dep in step.get("requires", [])):
        return False
    condition = step.get("when")
    if condition and not facts.get(condition):
        # A gateway: the step is only on this path if the fact is present and true.
        return False
    loop = step.get("for_each")
    # An empty list means there is nothing to iterate: move on rather than demand
    # a call that cannot be made.
    return not (loop and loop in facts and not facts[loop])


def _expand_calls(step: dict, facts: dict) -> list[dict]:
    """The calls to make now — one per item when the step loops over a list."""
    calls = step.get("calls", [])
    loop = step.get("for_each")
    if not loop:
        return [{"tool": c["tool"], "arguments": _fill(c.get("arguments", {}), facts)}
                for c in calls]
    if loop not in facts:
        raise SkillGraphError(
            f"cannot build the call: missing {loop} (the list this step iterates)")
    variable = step.get("as", "item")
    expanded = []
    for item in facts[loop]:
        scoped = {**facts, variable: item}
        expanded.extend(
            {"tool": c["tool"], "arguments": _fill(c.get("arguments", {}), scoped)}
            for c in calls
        )
    return expanded


def next_step(graph: dict, done: list[str], facts: dict) -> dict | None:
    """The one step to run now, or None when the procedure is finished.

    Steps are offered in declaration order, so the graph reads top to bottom like
    the body it replaces. A step whose gateway condition is absent is skipped, and
    skipping it must never stall the procedure.
    """
    done_set = set(done or [])
    facts = facts or {}
    for step in graph["steps"]:
        if not _is_runnable(step, done_set, facts):
            continue
        return {
            "id": step["id"],
            "label": step.get("label", step["id"]),
            "calls": _expand_calls(step, facts),
            "produces": step.get("produces", []),
            "notes": step.get("notes"),
            "remaining": sum(
                1 for s in graph["steps"]
                if s["id"] not in done_set and s["id"] != step["id"]
                and (not s.get("when") or facts.get(s.get("when")))
            ),
        }
    return None
