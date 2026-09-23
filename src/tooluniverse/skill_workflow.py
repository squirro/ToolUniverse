"""One Temporal workflow that interprets a Skill Process given as its input.

Everything that touches the world is an activity; everything that decides is the
pure step logic in `skill_runner`, awaited here. The model is reached through a
query and a signal: a step that needs an answer publishes the question in
`status()` and waits for `answer()`.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

with workflow.unsafe.imports_passed_through():
    from .skill_graph import SkillGraphError, delegated_calls
    from .skill_ceilings import ceiling_for, source_of
from .skill_run_record import skeleton, to_prov
from .skill_runner import (
    absorb_recorded,
    apply,
    asked,
    checked,
    check_facts,
    handover_of,
    is_upstream_failure,
    judged,
    keep_evidence,
    mapping_choices,
    mapping_problem,
    materialised,
    new_run,
    next_runnable,
    placed_mapping,
    question_for,
    recomputed,
    substitute,
    tables_checked,
    upstream_failure_text,
)

from .skill_working_record import WorkingRecord

TASK_QUEUE = "skills"

# Importing this module imports the whole `tooluniverse` package; pass it through the sandbox.
WORKFLOW_RUNNER = SandboxedWorkflowRunner(
    restrictions=SandboxRestrictions.default.with_passthrough_modules("tooluniverse"))
CALL_TIMEOUT = timedelta(seconds=120)       # the slowest source's cold path
ORACLE_WAIT = timedelta(hours=1)            # then the step is blocked, not the run
MAX_REPAIRS = 2


@dataclass
class ToolCall:
    tool: str
    arguments: dict = field(default_factory=dict)
    run_id: str = ""
    step: str = ""
    call_n: int = 0
    attempt: int = 0


@dataclass
class ToolResult:
    """Where the result is, never the result: it stays in the Working Record."""
    step: str = ""
    call_n: int = 0
    size: int = 0


@dataclass
class StepToAbsorb:
    run_id: str
    spec: dict
    calls: list
    facts: dict
    tables: dict = field(default_factory=dict)


@dataclass
class SkillRunInput:
    skill: str
    process: dict
    inputs: dict = field(default_factory=dict)
    definition_iri: str = ""
    definition_hash: str = ""


# --- the activity: one door, the same one the agent's execute_tool uses ---------

_executor: Callable[[str, dict], Any] | None = None


def bind_executor(execute: Callable[[str, dict], Any]) -> None:
    """Point the activity at the loaded registry (SMCP's `normalised_executor`)."""
    global _executor
    _executor = execute


_records: str | None = None


def bind_records(directory) -> None:
    """Point the activities at the directory that holds the Working Records."""
    global _records
    _records = str(directory)


def _record_of(run_id: str) -> WorkingRecord:
    if _records is None:
        raise RuntimeError("no records directory bound: call bind_records() at worker start")
    return WorkingRecord(_records, run_id)


@activity.defn(name="execute_tool")
def execute_tool(call: ToolCall) -> ToolResult:
    if _executor is None:
        raise RuntimeError("no executor bound: call bind_executor() at worker start")
    payload = _executor(call.tool, call.arguments)
    _record_of(call.run_id).put_result(call.step, call.call_n, call.tool, call.arguments,
                                       payload, attempt=call.attempt)
    if is_upstream_failure(payload):
        # The tool already retried within its limits, so the activity is not retried.
        raise ApplicationError(upstream_failure_text(payload)[len("UpstreamFailure: "):],
                               type="UpstreamFailure", non_retryable=True)
    return ToolResult(step=call.step, call_n=call.call_n,
                      size=len(json.dumps(payload, default=str)))


@activity.defn(name="absorb_step")
def absorb_step(step: StepToAbsorb) -> dict:
    """Extract and collect where the results are; hand back the facts, not the results."""
    return absorb_recorded(_record_of(step.run_id), step.tables, step.spec, step.calls,
                           step.facts)


@dataclass
class AnswerToCheck:
    run_id: str
    rules: dict
    produced: dict
    facts: dict


@activity.defn(name="check_answer")
def check_answer(answer: AnswerToCheck) -> dict:
    """Run the checks that read an Evidence table beside the record.
    Returns the failures and the rows for selected keys, never the table."""
    tables = _record_of(answer.run_id).rows
    return {"failures": check_facts(answer.rules, answer.produced, answer.facts, tables=tables),
            "rows_by_key": materialised(answer.rules, answer.produced, answer.facts, tables=tables)}


@dataclass
class AnsweredToKeep:
    run_id: str
    tables: dict
    outcome: dict


@activity.defn(name="keep_answered_evidence")
def keep_answered_evidence(answered: AnsweredToKeep) -> dict:
    """An evidence table the agent answered goes to the record, described,
    instead of travelling whole in the facts."""
    outcome = {**answered.outcome, "facts": dict(answered.outcome["facts"])}
    described = keep_evidence(_record_of(answered.run_id), answered.tables, outcome)
    return {"outcome": outcome, "evidence": described}


@dataclass
class MappingToPlace:
    spec: dict
    outcome: dict


_lookup: Callable[[str], dict] | None = None


def bind_lookup(lookup: Callable[[str], dict] | None) -> None:
    """Point the placing activity at an ontology lookup; unbound, every placing is unknown."""
    global _lookup
    _lookup = lookup


PLACING_TIMEOUT = timedelta(seconds=300)    # several ontology requests per term


@activity.defn(name="place_mapping")
def place_mapping(mapping: MappingToPlace) -> dict:
    """Each mapped term gets its placing from the ontology service; evidence, never a gate."""
    return placed_mapping(mapping.spec, mapping.outcome, _lookup)


RECORD_TIMEOUT = timedelta(seconds=30)

_recorder: Any = None


def bind_recorder(store: Any) -> None:
    """Point the record activity at the store that holds the definitions."""
    global _recorder
    _recorder = store


@activity.defn(name="record_run")
def record_run(skel: dict) -> str:
    if _recorder is None:
        raise RuntimeError("no store bound: call bind_recorder() at worker start")
    return _recorder.record(to_prov(skel), skel["run_id"])


# --- the workflow: the in-memory driver, awaited ---------------------------------

@workflow.defn(name="SkillWorkflow")
class SkillWorkflow:
    def __init__(self) -> None:
        self._run: dict = new_run({})
        self._process: dict = {}
        self._current: dict | None = None
        self._question: dict | None = None
        self._answer: dict | None = None
        self._finished = False

    @workflow.run
    async def run(self, inp: SkillRunInput) -> dict:
        self._process = inp.process
        self._run = new_run({**(inp.process.get("constants") or {}), **inp.inputs})
        run, process = self._run, self._process
        while True:
            step = next_runnable(process, run)
            if step is None:
                break
            self._current = step
            spec = next(s for s in process["steps"] if s["id"] == step["id"])
            made = list(step["calls"])
            failures = await self._calls(step["calls"])
            outcome = await self._absorb(spec, step["calls"], run["facts"])
            if spec.get("repair") and not outcome["resolved"]:
                outcome, failures = await self._repair(spec, step, spec["repair"], outcome,
                                                       failures, made)
            run.setdefault("evidence", []).extend(outcome.pop("evidence"))
            outcome.pop("resolved")
            delegated = spec.get("delegate") or []
            if delegated:
                # Web search and code live on the agent: it makes the composed calls.
                wanted = spec.get("produces") or []
                try:
                    calls = delegated_calls(spec, run["facts"])
                except SkillGraphError as exc:
                    run["blocked"].append({"step": step["id"], "reason": str(exc)})
                    outcome = judged(outcome, wanted, None)
                else:
                    made.extend(calls)
                    outcome = await self._answered(spec, step, wanted, outcome, question_for(
                        step["id"], "delegate", wanted, dict(run["facts"]), calls=calls,
                        notes=spec.get("notes")))
            # Only names the step could not resolve itself go to the model.
            wants = [n for n in (spec.get("judge") or []) if n not in outcome["facts"]]
            if wants:
                outcome = await self._answered(spec, step, wants, outcome, question_for(
                    step["id"], "judge", wants, {**run["facts"], **outcome["facts"]},
                    notes=spec.get("notes"),
                    choices=mapping_choices(spec, {**run["facts"], **outcome["facts"]})))
            tables = self._process.get("tables") or {}
            if any(tables.get(name) == "evidence" for name in outcome["facts"]):
                kept = await workflow.execute_activity(
                    keep_answered_evidence,
                    AnsweredToKeep(workflow.info().workflow_id, tables, outcome),
                    start_to_close_timeout=CALL_TIMEOUT,
                    retry_policy=RetryPolicy(maximum_attempts=3))
                outcome = kept["outcome"]
                run.setdefault("evidence", []).extend(kept["evidence"])
            apply(run, step["id"], failures, outcome, calls=made)
        self._current = None
        handover = handover_of(process, run)
        handover["run_id"] = workflow.info().workflow_id
        handover["record"] = await self._record(inp)
        self._finished = True
        return handover

    # -- the model's two holes: a question the caller reads, an answer it sends --

    @workflow.query
    def status(self) -> dict:
        step = self._current
        return {
            "finished": self._finished,
            "step_id": step["id"] if step else None,
            "step_label": step.get("label") if step else None,
            "done": list(self._run["done"]),
            "remaining": step["remaining"] if step else 0,
            "waiting_for": self._question,
        }

    @workflow.signal
    def answer(self, facts: dict) -> None:
        self._answer = dict(facts or {})

    async def _record(self, inp: SkillRunInput) -> dict:
        """Write the permanent Run Record once. A failed write is a warning, never a failed run."""
        skel = skeleton(self._process, self._run, run_id=workflow.info().workflow_id,
                        definition_iri=inp.definition_iri, definition_hash=inp.definition_hash)
        try:
            iri = await workflow.execute_activity(
                record_run, skel,
                start_to_close_timeout=RECORD_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3))
        except Exception as exc:                          # noqa: BLE001 — soft by design
            cause = getattr(exc, "cause", None) or exc
            return {"status": "failed", "error": f"{type(cause).__name__}: {cause}",
                    "skeleton": skel}
        return {"status": "written", "iri": iri, "skeleton": skel}

    async def _answered(self, spec: dict, step: dict, wants: list[str], outcome: dict,
                        question: dict) -> dict:
        """Ask, fold the answer in, check it; a failing check is asked once more."""
        answer = await self._ask(question)
        outcome = judged(outcome, wants, answer)
        beside = await self._checked_beside_record(spec, wants, outcome)
        outcome, problem = checked(spec, step["id"], wants, outcome, self._run["facts"],
                                   answered=answer is not None,
                                   failures=beside["failures"] if beside else None,
                                   rows_by_key=beside["rows_by_key"] if beside else None)
        problem = problem or mapping_problem(spec, outcome, self._run["facts"])
        if problem:
            answer = await self._ask({**question, "problem": problem})
            outcome = judged(outcome, wants, answer)
            beside = await self._checked_beside_record(spec, wants, outcome)
            outcome, _ = checked(spec, step["id"], wants, outcome, self._run["facts"],
                                 answered=False,
                                 failures=beside["failures"] if beside else None,
                                 rows_by_key=beside["rows_by_key"] if beside else None)
            if mapping_problem(spec, outcome, self._run["facts"]):
                for name in spec.get("mapping") or {}:
                    outcome["facts"].pop(name, None)
                    outcome["unresolved"].append(name)
        if spec.get("mapping"):
            outcome = await workflow.execute_activity(
                place_mapping, MappingToPlace(spec, outcome),
                start_to_close_timeout=PLACING_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=2))
        return recomputed(spec, outcome, self._run["facts"])

    async def _checked_beside_record(self, spec: dict, wants: list[str], outcome: dict) -> list | None:
        """The step's checks, run beside the record when one reads an Evidence table;
        None when none does."""
        rules = spec.get("check") or {}
        if not tables_checked(rules):
            return None
        produced = {n: outcome["facts"][n] for n in wants if n in outcome["facts"]}
        return await workflow.execute_activity(
            check_answer,
            AnswerToCheck(workflow.info().workflow_id, rules, produced, self._run["facts"]),
            start_to_close_timeout=CALL_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3))

    async def _ask(self, question: dict) -> dict | None:
        self._question, self._answer = question, None
        try:
            await workflow.wait_condition(lambda: self._answer is not None,
                                          timeout=ORACLE_WAIT)
        except asyncio.TimeoutError:
            self._run["blocked"].append({
                "step": question["step"],
                "reason": f"no answer to {question['kind']} for {question['wants']}",
            })
            asked(self._run, question, None)
            return None
        finally:
            self._question = None
        asked(self._run, question, self._answer)
        return self._answer

    # -- the work: every call an activity, all at once, capped per source ---------

    async def _absorb(self, spec: dict, calls: list[dict], facts: dict) -> dict:
        return await workflow.execute_activity(
            absorb_step,
            StepToAbsorb(workflow.info().workflow_id, spec, calls, facts,
                         self._process.get("tables") or {}),
            start_to_close_timeout=CALL_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3))

    async def _calls(self, calls: list[dict], attempt: int = 0) -> list:
        """Run a step's calls at once and gather them in declared order; a per-source
        semaphore keeps a rate limit from banning the fan-out. One failure is one missing item."""
        gates: dict[str, asyncio.Semaphore] = {}

        run_id = workflow.info().workflow_id
        step_id = (self._current or {}).get("id", "")

        async def one(call_n: int, call: dict):
            source = source_of(call["tool"])
            gate = gates.setdefault(source, asyncio.Semaphore(ceiling_for(call["tool"])))
            async with gate:
                return await workflow.execute_activity(
                    execute_tool,
                    ToolCall(call["tool"], call["arguments"], run_id, step_id, call_n, attempt),
                    start_to_close_timeout=CALL_TIMEOUT,
                    retry_policy=RetryPolicy(maximum_attempts=1))

        settled = await asyncio.gather(*(one(n, c) for n, c in enumerate(calls)),
                                       return_exceptions=True)
        failures = []
        for call, outcome in zip(calls, settled):
            if isinstance(outcome, BaseException):
                # A broken tool must not end the procedure; the bundle names the missing item.
                cause = getattr(outcome, "cause", None) or outcome
                # A typed application error carries the name the activity gave it.
                kind = getattr(cause, "type", None) or type(cause).__name__
                text = str(cause)
                failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                 "error": text if text.startswith(f"{kind}: ") else f"{kind}: {text}"})
        return failures

    async def _repair(self, spec, step, repair, outcome, failures, made):
        argument = repair["argument"]
        original = step["calls"][0]["arguments"].get(argument)
        problem = f"returned nothing for {original!r}"
        answer = await self._ask(question_for(
            step["id"], "repair", [argument], dict(self._run["facts"]),
            tool=step["calls"][0]["tool"], argument=argument, value=original,
            problem=problem))
        suggestions = (answer or {}).get(argument) or []
        # A repair always starts from a call that returned nothing usable, even when
        # that was not an error; a successful repair must still be able to say so.
        pre_repair = failures or [{"tool": step["calls"][0]["tool"],
                                   "arguments": step["calls"][0]["arguments"],
                                   "error": problem}]
        for attempt, candidate in enumerate(suggestions[:MAX_REPAIRS], start=1):
            retry_calls = substitute(step["calls"], argument, candidate)
            made.extend(retry_calls)
            failures = await self._calls(retry_calls, attempt=attempt)
            outcome = await self._absorb(spec, retry_calls,
                                         {**self._run["facts"], argument: candidate})
            if outcome["resolved"]:
                self._run["facts"][argument] = candidate
                kept = [{**f, "repaired_by": candidate} for f in pre_repair]
                return outcome, kept + failures
        if answer is not None:
            self._run["blocked"].append({
                "step": step["id"],
                "reason": (f"{argument}={original!r} could not be resolved after "
                           f"{MAX_REPAIRS} suggested alternatives"),
            })
        return outcome, failures
