"""Run a skill's process graph SERVER-SIDE — the Novartis navigator, ported.

The Novartis PoC did not make an LLM obedient; it kept the LLM out of the control
loop. A Python `ProcessNavigator` walked the BBO graph, `SessionState` held the
state, `_gw_*` predicates chose each branch from state the code had computed, and
`_action_*` functions performed the work. Nothing was asked to choose, so nothing
drifted.

Our first port moved the PLAN out of the model and left the RUNTIME with it: the
model had to decide to start, carry `done` and `facts` between calls, report the
values gateways branch on, and choose to make each call. Measured on sr-dev, it
executed that loop faithfully when it entered it (nine steps, in order, four calls
where four were offered) but failed to enter it on two runs of three, and
abandoned it after seven of nine steps on another.

This module closes that gap. It holds the run state, executes each step's calls
itself, extracts the values the next step needs, and evaluates gateways from the
REAL results. The model's remaining jobs are choosing the skill and writing the
report.

`execute` is injected — SMCP passes the in-process ToolUniverse (ExecuteTool is
already constructed with `tooluniverse=self`), and tests pass a stub. State is an
in-memory dict: durability across restarts is what a workflow engine would add,
and is deliberately not in this spike.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable

from .skill_graph import SkillGraphError, _fill, next_step

_OPS: dict[str, Callable[[Any, Any], bool]] = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _dig(payload: Any, path: str) -> Any:
    """Follow a dotted path into a result, returning None rather than raising.

    Deliberately not JSONPath: a boring, declarative accessor is what keeps the
    extraction reviewable, and a miss surfaces as a named missing fact at the next
    step rather than a crash.

    One form beyond dots: a segment ending ``[]`` maps over a list, so
    ``result[].term`` turns FAERS's [{term, count}, ...] into the term strings the
    next step must pass back VERBATIM — MedDRA is case- and spelling-strict, and
    the prose body spends five lines asking the model not to retype them.
    """
    current: Any = payload
    mapping = False
    for part in path.split("."):
        mapped = part.endswith("[]")
        key = part[:-2] if mapped else part
        if key:
            current = _step_in(current, key, mapping)
            if current is None:
                return None
        if mapped:
            if mapping:
                return None                    # nested mapping is out of scope
            if not isinstance(current, list):
                return None
            mapping = True
    return current


def _step_in(current: Any, key: str, mapping: bool) -> Any:
    """Take one path segment, over a single value or over every mapped item."""
    if mapping:
        if not isinstance(current, list):
            return None
        out = [_step_in(item, key, False) for item in current]
        return [value for value in out if value is not None]
    if isinstance(current, dict):
        return current.get(key)
    if isinstance(current, list) and key.isdigit():
        return current[int(key)] if int(key) < len(current) else None
    return None


def _derive(spec: dict, facts: dict) -> bool:
    """A gateway condition computed from data, not asserted by the model."""
    rows = facts.get(spec["from"]) or []
    field, op, value = spec.get("field"), spec.get("op", "=="), spec.get("value")
    compare = _OPS[op]
    hits = []
    for row in rows:
        seen = row.get(field) if isinstance(row, dict) else row
        if seen is None:
            continue
        try:
            hits.append(compare(seen, value))
        except TypeError:
            continue
    return all(hits) if spec.get("mode") == "all" else any(hits)


class SkillRunner:
    """Server-side execution of one skill graph, one run at a time."""

    def __init__(self, graph: dict, execute: Callable[[str, dict], Any]):
        self.graph = graph
        self.execute = execute
        self._runs: dict[str, dict] = {}

    def start(self, inputs: dict) -> dict:
        run_id = uuid.uuid4().hex
        self._runs[run_id] = {"facts": dict(inputs), "done": [], "failures": [],
                              "blocked": [], "skipped": []}
        return {"run_id": run_id, "step": self._peek(run_id)}

    def state(self, run_id: str) -> dict:
        return self._runs[run_id]

    def _peek(self, run_id: str) -> dict | None:
        run = self._runs[run_id]
        return next_step(self.graph, done=run["done"] + run["skipped"],
                         facts=run["facts"])

    def _peek_safe(self, run_id: str):
        """Peek, and mark any step we cannot build as blocked rather than raising.

        Loops, because skipping one blocked step can reveal another.
        """
        run = self._runs[run_id]
        while True:
            try:
                return self._peek(run_id)
            except SkillGraphError as exc:
                blocked = next(
                    (s["id"] for s in self.graph["steps"]
                     if s["id"] not in run["done"] and s["id"] not in run["skipped"]
                     and all(d in run["done"] for d in s.get("requires", []))),
                    None)
                if blocked is None:
                    return None
                run["skipped"].append(blocked)
                run["blocked"].append({"step": blocked, "reason": str(exc)})

    def advance(self, run_id: str) -> dict:
        """Run the current step's calls, extract what follows, and move on."""
        run = self._runs[run_id]
        # A step we cannot build is BLOCKED, not fatal. Live, a missed FAERS
        # extraction killed a ten-step run at step four — and the other four
        # sources did not depend on it.
        step = self._peek_safe(run_id)
        if step is None:
            return {"finished": True, "next_step": None, "extracted": {},
                    "failures": run["failures"], "blocked": run["blocked"]}

        spec = next(s for s in self.graph["steps"] if s["id"] == step["id"])
        results, failures = [], []
        for call in step["calls"]:
            try:
                results.append(self.execute(call["tool"], call["arguments"]))
            except Exception as exc:                       # noqa: BLE001
                # A broken tool must not end the procedure: one bot-blocked FDA
                # endpoint ended a whole run under the model-driven loop.
                failures.append({"tool": call["tool"],
                                 "error": f"{type(exc).__name__}: {exc}"})

        extracted: dict[str, Any] = {}
        for name, rule in (spec.get("extract") or {}).items():
            path = rule["path"] if isinstance(rule, dict) else rule
            limit = rule.get("limit") if isinstance(rule, dict) else None
            for payload in results:
                found = _dig(payload, path)
                if found is not None:
                    if limit and isinstance(found, list):
                        found = found[:limit]
                    extracted[name] = found
                    break
        run["facts"].update(extracted)

        for name, rule in (spec.get("derive") or {}).items():
            extracted[name] = _derive(rule, run["facts"])
            run["facts"][name] = extracted[name]

        run["done"].append(step["id"])
        run["failures"].extend(failures)
        following = self._peek_safe(run_id)
        return {
            "step_id": step["id"],
            "blocked": run["blocked"],
            "extracted": extracted,
            "failures": failures,
            "next_step": following,
            "finished": following is None,
        }


def compose(graph: dict, facts: dict) -> dict:
    """Expose the graph's own templating, so callers need not reimplement it."""
    return _fill(graph, facts)
