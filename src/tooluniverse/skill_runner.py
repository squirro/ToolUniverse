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

import json
import re
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


def _derive(spec: dict, facts: dict) -> bool | None:
    """A gateway condition computed from data, not asserted by the model.

    None means UNKNOWN: the source fact never arrived, so there is nothing to
    decide on. Live on enzalutamide the `signals` extraction missed, the rule
    derived over an empty list, and the branch was skipped as though the data had
    said "no strong signal" — a silent wrong answer. A genuine empty result is
    still False; only an ABSENT fact is unknown.
    """
    if spec["from"] not in facts:
        return None
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
                              "blocked": [], "skipped": [], "results": {}}
        return {"run_id": run_id, "step": self._peek(run_id)}

    def state(self, run_id: str) -> dict:
        return self._runs[run_id]

    def _peek(self, run_id: str) -> dict | None:
        run = self._runs[run_id]
        return next_step(self.graph, done=run["done"] + run["skipped"],
                         facts=run["facts"])

    MAX_PAYLOAD = 12_000

    def bundle(self, run_id: str) -> dict:
        """Everything the report needs, handed over ONCE at the end.

        The runner extracts only what the next step requires; the rest — label
        text, the trial list, the papers — is what the report is made of, so the
        run keeps it. Capping each payload keeps the bundle sendable: the point of
        running server-side is that raw results never travel through the
        transcript on the way, so they arrive once, trimmed, at the end.
        """
        run = self._runs[run_id]
        trimmed = {}
        for step_id, results in run["results"].items():
            kept = []
            for payload in results:
                text = json.dumps(payload, default=str)
                kept.append(payload if len(text) <= self.MAX_PAYLOAD
                            else {"truncated": True,
                                  "preview": text[:self.MAX_PAYLOAD]})
            trimmed[step_id] = kept
        return {
            "skill": self.graph["skill"],
            "facts": run["facts"],
            "results": trimmed,
            "steps_done": run["done"],
            "failures": run["failures"],
            "blocked": run["blocked"],
        }

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
            rule = rule if isinstance(rule, dict) else {"path": rule}
            for payload in results:
                found = _dig(payload, rule["path"])
                if found is None:
                    continue
                if rule.get("regex") and isinstance(found, str):
                    # Some values only exist inside a returned string: DailyMed
                    # puts the BRAND at the head of its SPL title, and FAERS
                    # indexes this drug family by brand (LUTATHERA returns 100
                    # reaction terms where the generic name returns 3).
                    match = re.search(rule["regex"], found)
                    if not match:
                        continue
                    found = match.group(1) if match.groups() else match.group(0)
                if rule.get("limit") and isinstance(found, list):
                    found = found[: rule["limit"]]
                extracted[name] = found
                break
            if name not in extracted and rule.get("default_from"):
                fallback = run["facts"].get(rule["default_from"])
                if fallback is not None:
                    extracted[name] = fallback
        # `collect` gathers a value from EVERY call, which is what a loop step
        # needs: FAERS answers one metrics object per reaction, and the gateway
        # has to see them all. `extract` takes the first match, `collect` the lot.
        for name, path in (spec.get("collect") or {}).items():
            gathered = [found for payload in results
                        if (found := _dig(payload, path)) is not None]
            if gathered:
                extracted[name] = gathered
        # `combine` merges facts the question supplied with facts the data
        # produced. The reactions a user names ("especially myelodysplastic
        # syndrome and renal impairment") exist only in the question and are
        # rarely frequent enough to survive a top-N cut — for Lutathera neither
        # is in the top twelve — so requested terms lead and the cap trims the
        # frequency-ranked tail, never the ask.
        for name, rule in (spec.get("combine") or {}).items():
            merged: list = []
            for source in rule.get("union", []):
                value = run["facts"].get(source) or extracted.get(source) or []
                for item in (value if isinstance(value, list) else [value]):
                    if item not in merged:
                        merged.append(item)
            if rule.get("limit"):
                merged = merged[: rule["limit"]]
            extracted[name] = merged
        run["facts"].update(extracted)

        for name, rule in (spec.get("derive") or {}).items():
            decided = _derive(rule, run["facts"])
            extracted[name] = decided
            if decided is None:
                # Do NOT put an unknown in facts: `when` reads falsy and would
                # skip the branch silently. Say so instead.
                run["blocked"].append({
                    "step": step["id"],
                    "reason": (f"cannot decide {name}: {rule['from']} was never "
                               "extracted, so the branch was not taken"),
                })
            else:
                run["facts"][name] = decided

        run["results"][step["id"]] = results
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


def normalised_executor(dispatch: Callable[[dict], Any]) -> Callable[[str, dict], Any]:
    """Wrap ToolUniverse's dispatch so the runner sees what the AGENT sees.

    `execute_tool` is not a second implementation — its class calls
    `run_one_function` and then normalises: JSON-decode a string return, and wrap
    any non-dict as {"result": ...}. Calling `run_one_function` directly skips
    that, so the runner saw a bare list where every saved trace shows
    {"result": [...]}, and an extraction path written from a trace missed.

    One door. Extraction paths written against a trace work in the runner, and
    vice versa.
    """
    def execute(tool: str, arguments: dict) -> Any:
        result = dispatch({"name": tool, "arguments": arguments})
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, ValueError):
                return {"result": result}
        return result if isinstance(result, dict) else {"result": result}
    return execute


def compose(graph: dict, facts: dict) -> dict:
    """Expose the graph's own templating, so callers need not reimplement it."""
    return _fill(graph, facts)
