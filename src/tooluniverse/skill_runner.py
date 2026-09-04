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
in-memory dict. The step logic — `absorb`, `resolved`, `substitute`, `apply`,
`trim` — is module-level and pure, so a durable host (Temporal, ADR-0016) can
await the calls itself and hand the results to the same functions; this class is
the synchronous driver over them.
"""
from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from typing import Any

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



MAX_PAYLOAD = 12_000   # per payload in the bundle; raw results never ride the transcript


def new_run(inputs: dict) -> dict:
    """Fresh run state: the whole of it is (done, facts) plus what went wrong."""
    return {"facts": dict(inputs), "done": [], "failures": [], "blocked": [],
            "skipped": [], "results": {}, "calls": {}, "unresolved": [], "excluded": {}}


def apply(run: dict, step_id: str, results: list, failures: list, outcome: dict,
          calls: list[dict] | None = None) -> None:
    """Record a finished step on the run. Pure over its arguments; mutates `run`."""
    run["results"][step_id] = results
    # The tools this step ran, retries included: the agent's own trace never
    # shows them, so the bundle carries the record itself.
    run["calls"][step_id] = [c["tool"] for c in (calls or [])]
    run["done"].append(step_id)
    run["failures"].extend(failures)
    run["facts"].update(outcome["facts"])
    run["blocked"].extend(outcome["blocked"])
    if outcome.get("excluded"):
        run["excluded"][step_id] = outcome["excluded"]
    run["unresolved"].extend({"step": step_id, "fact": name}
                             for name in outcome["unresolved"])


def trim(results: list, cap: int) -> list:
    """Cap each payload so the bundle stays sendable; say where the cut was."""
    kept = []
    for payload in results:
        text = json.dumps(payload, default=str)
        kept.append(payload if len(text) <= cap
                    else {"truncated": True, "preview": text[:cap]})
    return kept


def next_runnable(graph: dict, run: dict) -> dict | None:
    """The step to run now, marking any step that cannot be built as blocked.

    Loops, because skipping one blocked step can reveal another. A step we
    cannot build is BLOCKED, not fatal: live, a missed FAERS extraction killed a
    ten-step run at step four, and the other four sources did not depend on it.
    """
    while True:
        try:
            return next_step(graph, done=run["done"] + run["skipped"],
                             facts=run["facts"])
        except SkillGraphError as exc:
            blocked = getattr(exc, "step", None) or next(
                (s["id"] for s in graph["steps"]
                 if s["id"] not in run["done"] and s["id"] not in run["skipped"]
                 and all(d in run["done"] for d in s.get("requires", []))),
                None)
            if blocked is None:
                return None
            run["skipped"].append(blocked)
            run["blocked"].append({"step": blocked, "reason": str(exc)})


def bundle_of(graph: dict, run: dict, cap: int) -> dict:
    """Everything the report needs, handed over ONCE at the end.

    The run kept every result — label text, the trial list, the papers — because
    that is what the report is made of. Capping each payload keeps it sendable.
    """
    return {
        "skill": graph["skill"],
        "facts": run["facts"],
        "results": {step_id: trim(results, cap)
                    for step_id, results in run["results"].items()},
        "steps_done": run["done"],
        "calls": run.get("calls", {}),
        # The author's judgement, with the data: what each step means and how the
        # report must read the evidence. Blind-judged 2026-09-03, the reports that
        # lacked this printed FAERS coding noise as signals.
        "notes": {s["id"]: s["notes"] for s in graph["steps"]
                  if s.get("notes") and s["id"] in run["done"]},
        "report": graph.get("report"),
        "excluded": run.get("excluded", {}),
        "failures": run["failures"],
        "blocked": run["blocked"],
        "unresolved": run["unresolved"],
    }


def resolved(spec: dict, repair: dict, results: list) -> bool:
    """Did the value this step exists to produce actually arrive?"""
    wanted = repair["when_missing"]
    rule = (spec.get("extract") or {}).get(wanted)
    path = rule["path"] if isinstance(rule, dict) else rule
    return any(_dig(payload, path) is not None for payload in results)


def substitute(calls: list[dict], argument: str, candidate: Any) -> list[dict]:
    """The same calls with one argument swapped, wherever a call carries it."""
    out = []
    for call in calls:
        arguments = dict(call["arguments"])
        if argument in arguments:
            arguments[argument] = candidate
        out.append({**call, "arguments": arguments})
    return out


def question_for(step_id: str, kind: str, wants: list[str], context: dict, **detail) -> dict:
    """The one question shape the model is asked mid-run: repair, judgement or delegation.

    The step's notes ride along when it has any — they say what shape the answer
    should take, and an agent that never saw them answered a web search with bare
    URLs where the author had asked for title, url and snippet.
    """
    return {"kind": kind, "step": step_id, "wants": list(wants), "context": context,
            **{k: v for k, v in detail.items() if v is not None}}


def judged(outcome: dict, wants: list[str], answer: dict | None) -> dict:
    """Fold the model's answer to a judgement into a step outcome.

    Only the names the step declared are taken; a declared name the model did
    not answer is unresolved, like an extraction that never arrived.
    """
    answer = answer or {}
    facts = {**outcome["facts"],
             **{name: answer[name] for name in wants if name in answer}}
    unresolved = outcome["unresolved"] + [n for n in wants if n not in answer]
    return {**outcome, "facts": facts, "unresolved": unresolved}


def absorb(spec: dict, results: list, facts: dict) -> dict:
    """What a step's results yield: facts, what never arrived, what cannot be decided.

    Pure. `extract` takes the first match, `collect` the lot, `combine` merges
    with facts the question supplied, `derive` decides a gateway from data. A
    derive over a source that never arrived is UNKNOWN and lands in `blocked`,
    never in facts — `when` reads a missing key as falsy and would skip the
    branch silently.
    """
    extracted: dict[str, Any] = {}
    excluded: dict[str, list] = {}
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
            if rule.get("exclude") and isinstance(found, list):
                # The author knows which returned values are noise — FAERS coding
                # terms such as ILL-DEFINED DISORDER — and says so in the process,
                # before any cap, so the cap trims real terms only.
                dropped = [v for v in found if v in rule["exclude"]]
                if dropped:
                    excluded[name] = dropped
                    found = [v for v in found if v not in rule["exclude"]]
            if rule.get("limit") and isinstance(found, list):
                found = found[: rule["limit"]]
            extracted[name] = found
            break
        if name not in extracted and rule.get("default_from"):
            fallback = facts.get(rule["default_from"])
            if fallback is not None:
                extracted[name] = fallback
    # `collect` gathers a value from EVERY call, which is what a loop step
    # needs: FAERS answers one metrics object per reaction, and the gateway
    # has to see them all.
    for name, rule in (spec.get("collect") or {}).items():
        rule = rule if isinstance(rule, dict) else {"path": rule}
        gathered = []
        for payload in results:
            found = _dig(payload, rule["path"])
            if found is None:
                continue
            if rule.get("match"):
                # The first item that matches, per call: an HPO lookup answers
                # UPHENO:, MP:, then HP:, and only the HP id is a human phenotype.
                items = found if isinstance(found, list) else [found]
                found = next((i for i in items
                              if isinstance(i, str) and re.search(rule["match"], i)),
                             None)
                if found is None:
                    continue
            if rule.get("flatten") and isinstance(found, list):
                # One list per call folded into one list: Orphanet answers a
                # gene list per disease, and the gene panel loops over genes.
                gathered.extend(found)
            else:
                gathered.append(found)
        if rule.get("unique"):
            gathered = list(dict.fromkeys(gathered))
        if gathered:
            extracted[name] = gathered
    # `combine` merges facts the question supplied with facts the data
    # produced. Requested terms lead and the cap trims the frequency-ranked
    # tail, never the ask.
    for name, rule in (spec.get("combine") or {}).items():
        merged: list = []
        for source in rule.get("union", []):
            value = facts.get(source) or extracted.get(source) or []
            for item in (value if isinstance(value, list) else [value]):
                if item not in merged:
                    merged.append(item)
        if rule.get("limit"):
            merged = merged[: rule["limit"]]
        extracted[name] = merged

    blocked, undecided = [], []
    known = {**facts, **extracted}
    for name, rule in (spec.get("derive") or {}).items():
        decided = _derive(rule, known)
        if decided is None:
            undecided.append(name)
            blocked.append({
                "step": spec["id"],
                "reason": (f"cannot decide {name}: {rule['from']} was never "
                           "extracted, so the branch was not taken"),
            })
        else:
            extracted[name] = decided

    # A value the step SAYS it produces and did not is recorded, always.
    unresolved = [name for name in (spec.get("extract") or {})
                  if name not in extracted]
    return {"facts": extracted, "unresolved": unresolved, "blocked": blocked,
            "undecided": undecided, "excluded": excluded}


class SkillRunner:
    """Server-side execution of one skill graph, one run at a time."""

    MAX_REPAIRS = 2

    def __init__(self, graph: dict, execute: Callable[[str, dict], Any],
                 ask: Callable[[dict], list[str]] | None = None):
        self.graph = graph
        self.execute = execute
        # `ask` puts the model back in the loop as an ORACLE, never as the
        # scheduler: the server decides a lookup failed, frames the question,
        # validates the answer by re-querying, and stops after MAX_REPAIRS.
        # It exists because the agent knows things the data does not — that
        # "Lu-177" and "lu 177" are one isotope — and DailyMed returns nothing
        # for the form the agent correctly binds from the question.
        self.ask = ask
        self._runs: dict[str, dict] = {}

    def start(self, inputs: dict, run_id: str | None = None) -> dict:
        # A host that already names its runs (Temporal) passes the id in; the
        # in-memory host is the only one that mints its own.
        run_id = run_id or uuid.uuid4().hex
        self._runs[run_id] = new_run(inputs)
        return {"run_id": run_id, "step": self._peek(run_id)}

    def state(self, run_id: str) -> dict:
        return self._runs[run_id]

    def _peek(self, run_id: str) -> dict | None:
        run = self._runs[run_id]
        return next_step(self.graph, done=run["done"] + run["skipped"],
                         facts=run["facts"])

    MAX_PAYLOAD = MAX_PAYLOAD

    def _repair(self, spec, step, repair, results, failures, run, made):
        """Ask for a better argument value and retry, at most MAX_REPAIRS times."""
        if resolved(spec, repair, results):
            return results, failures
        argument = repair["argument"]
        original = step["calls"][0]["arguments"].get(argument)
        answer = self.ask(question_for(
            step["id"], "repair", [argument], dict(run["facts"]),
            tool=step["calls"][0]["tool"], argument=argument, value=original,
            problem=f"returned nothing for {original!r}",
        ))
        # One answer shape for every question: the wanted name mapped to its
        # value — here a list of alternatives. A bare list is still taken.
        suggestions = answer.get(argument) if isinstance(answer, dict) else answer
        for candidate in (suggestions or [])[: self.MAX_REPAIRS]:
            retried, retry_failures = [], []
            retry_calls = substitute(step["calls"], argument, candidate)
            made.extend(retry_calls)
            for call in retry_calls:
                try:
                    retried.append(self.execute(call["tool"], call["arguments"]))
                except Exception as exc:                   # noqa: BLE001
                    retry_failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                           "error": f"{type(exc).__name__}: {exc}"})
            if resolved(spec, repair, retried):
                run["facts"][argument] = candidate
                return retried, retry_failures
            results, failures = retried, retry_failures
        run["blocked"].append({
            "step": step["id"],
            "reason": (f"{argument}={original!r} could not be resolved after "
                       f"{self.MAX_REPAIRS} suggested alternatives"),
        })
        return results, failures

    def bundle(self, run_id: str) -> dict:
        return bundle_of(self.graph, self._runs[run_id], self.MAX_PAYLOAD)

    def _peek_safe(self, run_id: str):
        return next_runnable(self.graph, self._runs[run_id])

    def advance(self, run_id: str) -> dict:
        """Run the current step's calls, extract what follows, and move on."""
        run = self._runs[run_id]
        step = self._peek_safe(run_id)
        if step is None:
            return {"finished": True, "next_step": None, "extracted": {},
                    "failures": run["failures"], "blocked": run["blocked"],
                    "unresolved": run["unresolved"]}

        spec = next(s for s in self.graph["steps"] if s["id"] == step["id"])
        results, failures, made = [], [], list(step["calls"])
        for call in step["calls"]:
            try:
                results.append(self.execute(call["tool"], call["arguments"]))
            except Exception as exc:                       # noqa: BLE001
                # A broken tool must not end the procedure: one bot-blocked FDA
                # endpoint ended a whole run under the model-driven loop.
                failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                 "error": f"{type(exc).__name__}: {exc}"})

        repair = spec.get("repair")
        if repair and self.ask:
            results, failures = self._repair(
                spec, step, repair, results, failures, run, made)

        outcome = absorb(spec, results, run["facts"])
        delegated = spec.get("delegate") or []
        if delegated:
            # Web search and code live on the agent, not in the registry. The run
            # asks the agent to make these calls with its own tools and hands
            # back the named facts — same pause as a judgement, results on record.
            wanted = spec.get("produces") or []
            try:
                calls = [{"tool": c["tool"], "arguments": _fill(c.get("arguments", {}), run["facts"])}
                         for c in delegated]
            except SkillGraphError as exc:
                run["blocked"].append({"step": step["id"], "reason": str(exc)})
                outcome = judged(outcome, wanted, None)
            else:
                made.extend(calls)
                answer = self.ask(question_for(step["id"], "delegate", wanted, dict(run["facts"]),
                                               calls=calls, notes=spec.get("notes"))) if self.ask else None
                outcome = judged(outcome, wanted, answer)
        wants = spec.get("judge") or []
        if wants:
            # A judgement fact is asked for by name, after the step's own calls,
            # with everything known so far — never inferred from what an
            # extraction happened to miss.
            answer = self.ask(question_for(
                step["id"], "judge", wants, {**run["facts"], **outcome["facts"]},
                notes=spec.get("notes"),
            )) if self.ask else None
            outcome = judged(outcome, wants, answer)
        apply(run, step["id"], results, failures, outcome, calls=made)
        # The caller sees an unknown as an explicit None; facts never hold one.
        extracted = {**outcome["facts"], **{n: None for n in outcome["undecided"]}}
        missed = [{"step": step["id"], "fact": name} for name in outcome["unresolved"]]
        following = self._peek_safe(run_id)
        return {
            "step_id": step["id"],
            "blocked": run["blocked"],
            "unresolved": missed,
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
