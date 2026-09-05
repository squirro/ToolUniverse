"""A Skill Process on Temporal: one interpreter workflow, the process as its input.

ADR-0016. The in-memory `SkillRunner` proved the trust properties — the server
orders, calls, extracts and branches; the model binds inputs, answers named
questions, writes the report. Temporal adds the Run Record: every call, argument,
question and answer in the event history, and the run survives the process that
started it.

The split is Temporal's own. Everything that touches the world is an activity:
one `execute_tool` per call, bound to the registry the SMCP process already
loaded. Everything that decides is the pure step logic in `skill_runner` — the
same functions the in-memory driver uses — awaited here instead of called.

The model is reached through a query and a signal, never a callback: when a step
needs a Repair or a Judgement fact the workflow publishes the question in
`status()` and waits for `answer()`. The agent sees the question as the return
value of `run_skill` / `continue_skill` and answers with the next call. A
question nobody answers closes the step as blocked after ORACLE_WAIT, so the run
still finishes and states the gap.

Nothing here reads a file, the clock or a random source: the process dict is in
the workflow-started event, which is also what makes a run readable after the
skill it ran has changed.
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
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

with workflow.unsafe.imports_passed_through():
    from .skill_graph import SkillGraphError, fill
    from .skill_ceilings import ceiling_for, source_of
from .skill_run_record import skeleton, to_prov
from .skill_runner import (
        MAX_PAYLOAD,
        absorb,
        apply,
        asked,
        bundle_of,
        judged,
        new_run,
        next_runnable,
        question_for,
        resolved,
        substitute,
    )

TASK_QUEUE = "skills"

# The sandbox re-imports the workflow's module per run, and importing this module
# imports the `tooluniverse` package — the whole registry. Pass the package through:
# the step logic it needs is pure by contract, and the registry is never touched
# from workflow code.
WORKFLOW_RUNNER = SandboxedWorkflowRunner(
    restrictions=SandboxRestrictions.default.with_passthrough_modules("tooluniverse"))
CALL_TIMEOUT = timedelta(seconds=120)       # the Ensembl cold-path ceiling
ORACLE_WAIT = timedelta(hours=1)            # then the step is blocked, not the run
PAYLOAD_CAP = 1_000_000                     # Temporal's per-payload limit is 2 MB
MAX_REPAIRS = 2


@dataclass
class ToolCall:
    tool: str
    arguments: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    payload: Any = None
    truncated: bool = False


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


@activity.defn(name="execute_tool")
def execute_tool(call: ToolCall) -> ToolResult:
    if _executor is None:
        raise RuntimeError("no executor bound: call bind_executor() at worker start")
    payload = _executor(call.tool, call.arguments)
    text = json.dumps(payload, default=str)
    if len(text) > PAYLOAD_CAP:
        return ToolResult(payload={"truncated": True, "preview": text[:PAYLOAD_CAP]},
                          truncated=True)
    return ToolResult(payload=payload)


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
        self._run = new_run(inp.inputs)
        run, process = self._run, self._process
        while True:
            step = next_runnable(process, run)
            if step is None:
                break
            self._current = step
            spec = next(s for s in process["steps"] if s["id"] == step["id"])
            made = list(step["calls"])
            results, failures = await self._calls(step["calls"])
            repair = spec.get("repair")
            if repair and not resolved(spec, repair, results):
                results, failures = await self._repair(spec, step, repair, results,
                                                       failures, made)
            outcome = absorb(spec, results, run["facts"])
            delegated = spec.get("delegate") or []
            if delegated:
                # Web search and code live on the agent: the run pauses with the
                # calls composed, the agent makes them, the answer is on record.
                wanted = spec.get("produces") or []
                try:
                    calls = [{"tool": c["tool"], "arguments": fill(c.get("arguments", {}), run["facts"])}
                             for c in delegated]
                except SkillGraphError as exc:
                    run["blocked"].append({"step": step["id"], "reason": str(exc)})
                    outcome = judged(outcome, wanted, None)
                else:
                    made.extend(calls)
                    answer = await self._ask(question_for(
                        step["id"], "delegate", wanted, dict(run["facts"]), calls=calls,
                        notes=spec.get("notes")))
                    outcome = judged(outcome, wanted, answer)
            wants = spec.get("judge") or []
            if wants:
                answer = await self._ask(question_for(
                    step["id"], "judge", wants, {**run["facts"], **outcome["facts"]},
                    notes=spec.get("notes")))
                outcome = judged(outcome, wants, answer)
            apply(run, step["id"], results, failures, outcome, calls=made)
        self._current = None
        bundle = bundle_of(process, run, MAX_PAYLOAD)
        bundle["record"] = await self._record(inp)
        self._finished = True
        return bundle

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

    async def _calls(self, calls: list[dict]) -> tuple[list, list]:
        """Run a step's calls concurrently and gather them in declared order.

        A loop's iterations are the same call with one value substituted, so they
        are independent and run at once; a per-source semaphore keeps a rate
        limit from turning fan-out into a ban. One failure is one item missing,
        named by its arguments, never the whole step.
        """
        gates: dict[str, asyncio.Semaphore] = {}

        async def one(call: dict):
            source = source_of(call["tool"])
            gate = gates.setdefault(source, asyncio.Semaphore(ceiling_for(call["tool"])))
            async with gate:
                out: ToolResult = await workflow.execute_activity(
                    execute_tool, ToolCall(call["tool"], call["arguments"]),
                    start_to_close_timeout=CALL_TIMEOUT,
                    retry_policy=RetryPolicy(maximum_attempts=1))
                return out.payload

        settled = await asyncio.gather(*(one(c) for c in calls), return_exceptions=True)
        results, failures = [], []
        for call, outcome in zip(calls, settled):
            if isinstance(outcome, BaseException):
                # A broken tool must not end the procedure. The failure is in the
                # history as the failed activity; the bundle names it and its item.
                cause = getattr(outcome, "cause", None) or outcome
                failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                 "error": f"{type(cause).__name__}: {cause}"})
            else:
                results.append(outcome)
        return results, failures

    async def _repair(self, spec, step, repair, results, failures, made):
        argument = repair["argument"]
        original = step["calls"][0]["arguments"].get(argument)
        answer = await self._ask(question_for(
            step["id"], "repair", [argument], dict(self._run["facts"]),
            tool=step["calls"][0]["tool"], argument=argument, value=original,
            problem=f"returned nothing for {original!r}"))
        suggestions = (answer or {}).get(argument) or []
        for candidate in suggestions[:MAX_REPAIRS]:
            retry_calls = substitute(step["calls"], argument, candidate)
            made.extend(retry_calls)
            retried, retry_failures = await self._calls(retry_calls)
            if resolved(spec, repair, retried):
                self._run["facts"][argument] = candidate
                return retried, retry_failures
            results, failures = retried, retry_failures
        if answer is not None:
            self._run["blocked"].append({
                "step": step["id"],
                "reason": (f"{argument}={original!r} could not be resolved after "
                           f"{MAX_REPAIRS} suggested alternatives"),
            })
        return results, failures
