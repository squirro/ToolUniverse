"""run_skill / continue_skill: the agent's side of a Skill Run (ADR-0016).

The agent never sees Temporal. It calls `run_skill(skill, inputs)`, then
`continue_skill(run_id, answer)` until the return says finished. Each return is
one of three shapes:

    {"status": "finished", "run_id", "handover"}                 -> write the report
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


def undecided_inputs(process: dict, inputs: dict) -> list[str]:
    """Optional names the agent neither bound nor declined with an explicit null."""
    return [name for name in process.get("optional_inputs", []) if name not in inputs]


def missing_inputs(process: dict, inputs: dict) -> list[str]:
    """Required names the agent did not bind — reported before any run starts."""
    return [name for name in process.get("inputs", []) if inputs.get(name) in (None, "")]


def run_id_for(skill: str) -> str:
    return f"skill-{skill}-{uuid.uuid4().hex[:8]}"


def progress(run_id: str, status: dict, handover: dict | None = None) -> dict:
    """One of the three shapes, from a `status()` answer."""
    if status.get("finished"):
        return {"status": "finished", "run_id": run_id, "handover": handover,
                "next": (f"Write the report from `handover` as its `report` and `write_the_report` "
                         f"say, then call submit_report(run_id=\"{run_id}\", draft=<the whole "
                         "report>) before you answer the user. Answer only with what it accepts.")}
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
            return progress(handle.id, status, handover=await handle.result())
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
    from .skill_graph import undeclared_tables
    from .skill_process_store import SkillProcessNotFound
    from .skill_workflow import TASK_QUEUE, SkillRunInput, SkillWorkflow

    try:
        process, prov = store.load(skill)
    except SkillProcessNotFound as exc:
        return {"status": "error", "error": str(exc)}
    if undeclared := undeclared_tables(process):
        return {"status": "error",
                "error": f"the published process for {skill!r} collects {undeclared} without "
                         "declaring them under `tables:`; it cannot run until it is republished"}
    declared = set(process.get("inputs", [])) | set(process.get("optional_inputs", []))
    unknown = [name for name in (inputs or {}) if name not in declared]
    if unknown:
        return {"status": "schema_mismatch", "unknown_inputs": unknown,
                "required_inputs": process.get("inputs", []),
                "optional_inputs": process.get("optional_inputs", []),
                "hint": "these are not inputs of this skill; use the declared names only, "
                        "then call run_skill again"}
    missing = missing_inputs(process, inputs or {})
    if missing:
        return {"status": "schema_mismatch", "missing_inputs": missing,
                "required_inputs": process.get("inputs", []),
                "optional_inputs": process.get("optional_inputs", []),
                "hint": "bind these from the question, then call run_skill again"}
    undecided = undecided_inputs(process, inputs or {})
    if undecided:
        return {"status": "confirm_inputs", "undecided_inputs": undecided,
                "hint": "read the question again: bind each of these if the question names "
                        "it, or pass it as null to decline it, then call run_skill again"}
    from .skill_process_store import named_graph

    handle = await client.start_workflow(
        SkillWorkflow.run,
        SkillRunInput(skill=skill, process=process,
                      inputs={k: v for k, v in (inputs or {}).items() if v is not None},
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


def fetch_run_data(run_id: str, table: str, columns: list[str] | None = None,
                   limit: int | None = None, offset: int = 0, rank_by: str | None = None,
                   *, directory=None) -> dict:
    """Rows of one table of a run's Working Record, as the agent asks for them."""
    from .skill_working_record import WorkingRecord, records_dir

    record = WorkingRecord.existing(directory or records_dir(), run_id)
    if record is None:
        return {"status": "unknown_run", "run_id": run_id,
                "hint": "use the run_id that run_skill returned; a record lives as long as "
                        "the server that made it"}
    return record.fetch(table, columns, limit, offset, rank_by)


REPORT_ATTEMPTS = 2


async def submit_report(client: Any, run_id: str, draft: str, *, directory=None) -> dict:
    """Read the draft against what the agent received; ask once more, then let it go.

    Received = the hand-over (facts, tables) and every row served by fetch_run_data. A draft
    that states nothing else is accepted. Otherwise the agent is asked once to revise, with
    each failure named; a second draft goes out with the remaining failures appended.
    """
    from .skill_report_check import check_report
    from .skill_working_record import WorkingRecord, records_dir
    from .skill_workflow import SkillWorkflow

    handover = await client.get_workflow_handle(run_id).result()
    record = WorkingRecord.existing(directory or records_dir(), run_id)
    received = {"handover": handover, "fetched": record.served() if record else {}}
    failures = check_report(draft, received)
    if not failures:
        return {"status": "accepted", "run_id": run_id, "failures": []}
    attempt = record.count("report_submitted") if record else REPORT_ATTEMPTS
    named = "; ".join(f"{f['kind']} {f['text']!r} in: {f['context']}" for f in failures)
    if attempt < REPORT_ATTEMPTS:
        return {"status": "revise", "run_id": run_id, "failures": failures,
                "hint": ("these statements are not in the facts you were handed or the rows you "
                         "fetched: take each from its row and cite that row, fetch the row that "
                         "holds it, or remove it; then submit again -- " + named)}
    return {"status": "accepted_with_failures", "run_id": run_id, "failures": failures,
            "append_to_report": ("Not verified against the run's data: " + named)}
