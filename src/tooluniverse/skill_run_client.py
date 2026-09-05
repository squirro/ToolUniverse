"""run_skill / continue_skill: the agent's side of a Skill Run (ADR-0016).

The agent never sees Temporal. It calls `run_skill(skill, inputs)`, then
`continue_skill(run_id, answer)` until the return says finished. Each return is
one of three shapes:

    {"status": "finished", "run_id", "bundle"}                 -> write the report
    {"status": "waiting",  "run_id", "question", ...}          -> answer it
    {"status": "running",  "run_id", "step_id", "step_label", "done", "remaining"}

and each is a progress line the user can see. Waiting returns as soon as the run
crosses a step boundary (the user's choice: one tick per step), or asks a
question, or finishes, or the window elapses — the window keeps a tool call
under whatever timeout the MCP client has, which we cannot see.

Pure over a handle that offers `query`, `signal`, `result`; SMCP passes the real
workflow handle, tests pass a script.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

POLL_WINDOW = 40.0          # seconds a single tool call may wait
POLL_INTERVAL = 1.0


def missing_inputs(process: dict, inputs: dict) -> list[str]:
    """Required names the agent did not bind — reported before any run starts."""
    return [name for name in process.get("inputs", []) if inputs.get(name) in (None, "")]


def run_id_for(skill: str) -> str:
    return f"skill-{skill}-{uuid.uuid4().hex[:8]}"


def progress(run_id: str, status: dict, bundle: dict | None = None) -> dict:
    """One of the three shapes, from a `status()` answer."""
    if status.get("finished"):
        return {"status": "finished", "run_id": run_id, "bundle": bundle}
    base = {"run_id": run_id, "step_id": status.get("step_id"),
            "step_label": status.get("step_label"), "done": len(status.get("done") or [])}
    if status.get("waiting_for"):
        return {"status": "waiting", "question": status["waiting_for"], **base}
    return {"status": "running", "remaining": status.get("remaining", 0), **base}


async def wait_for_progress(handle: Any, *, window: float = POLL_WINDOW,
                            poll: float = POLL_INTERVAL) -> dict:
    """Poll `status` until something the agent should hear about, or the window ends."""
    from .skill_workflow import SkillWorkflow

    deadline = time.monotonic() + window
    entered = None
    while True:
        status = await handle.query(SkillWorkflow.status)
        if status.get("finished"):
            return progress(handle.id, status, bundle=await handle.result())
        if status.get("waiting_for"):
            return progress(handle.id, status)
        here = (status.get("step_id"), len(status.get("done") or []))
        if entered is None:
            entered = here
        elif here != entered:
            return progress(handle.id, status)          # a step boundary was crossed
        if time.monotonic() >= deadline:
            return progress(handle.id, status)
        await asyncio.sleep(poll)


async def start(client: Any, store: Any, skill: str, inputs: dict, *,
                task_queue: str | None = None) -> dict:
    """Load the process, validate the inputs, start the run, wait for the first tick."""
    from .skill_process_store import SkillProcessNotFound
    from .skill_workflow import TASK_QUEUE, SkillRunInput, SkillWorkflow

    try:
        process, prov = store.load(skill)
    except SkillProcessNotFound as exc:
        return {"status": "error", "error": str(exc)}
    missing = missing_inputs(process, inputs or {})
    if missing:
        return {"status": "schema_mismatch", "missing_inputs": missing,
                "required_inputs": process.get("inputs", []),
                "optional_inputs": process.get("optional_inputs", []),
                "hint": "bind these from the question, then call run_skill again"}
    from .skill_process_store import named_graph

    handle = await client.start_workflow(
        SkillWorkflow.run,
        SkillRunInput(skill=skill, process=process, inputs=dict(inputs or {}),
                      definition_iri=named_graph(skill),
                      definition_hash=prov.get("definition_hash", "")),
        id=run_id_for(skill), task_queue=task_queue or TASK_QUEUE)
    return await wait_for_progress(handle)


async def resume(client: Any, run_id: str, answer: dict | None = None) -> dict:
    """Send the answer if there is one, then wait for the next tick."""
    from .skill_workflow import SkillWorkflow

    handle = client.get_workflow_handle(run_id)
    if answer:
        await handle.signal(SkillWorkflow.answer, dict(answer))
    return await wait_for_progress(handle)
