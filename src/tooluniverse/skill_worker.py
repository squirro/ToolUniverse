"""The Temporal worker for Skill Runs, started inside the SMCP process (ADR-0016).

It lives here and not in its own container for one reason: the registry. SMCP
loads ~2,278 tools once, applies the exclusion list, and installs the central
repairs — transport status, the citation stamp, the id cue — on that instance. A
worker in another container would carry a second copy of all of it, or none. So
the activity is bound to SMCP's own instance through the same normalisation the
agent's `execute_tool` uses: one door.

The worker runs in a daemon thread with its own event loop, beside FastMCP's.
It starts only when TEMPORAL_ADDRESS is set; otherwise SMCP is exactly as
before and `run_skill` is simply not served.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from temporalio.client import Client
from temporalio.worker import Worker

from .skill_process_store import Store
from .skill_runner import normalised_executor
from .skill_workflow import (
    TASK_QUEUE,
    WORKFLOW_RUNNER,
    SkillWorkflow,
    bind_executor,
    bind_recorder,
    execute_tool,
    record_run,
)

log = logging.getLogger(__name__)

NAMESPACE = "skills"
CONNECT_RETRY_SECONDS = 5
MAX_ACTIVITIES = 15          # matches the server's --max-workers


def configured() -> str | None:
    return os.environ.get("TEMPORAL_ADDRESS") or None


def build_worker(client: Client, tooluniverse: Any, *, task_queue: str = TASK_QUEUE) -> Worker:
    """A worker whose activity calls tools through the agent's door."""
    bind_executor(normalised_executor(tooluniverse.run_one_function))
    try:
        bind_recorder(Store.from_env())
    except RuntimeError:
        # No GRAPHDB_ENDPOINT: run_skill cannot load a definition either, so the
        # worker is only reached in tests; the record activity then fails soft.
        log.warning("skill worker: GRAPHDB_ENDPOINT unset; Run Records will not be written")
    return Worker(
        client,
        task_queue=task_queue,
        workflows=[SkillWorkflow],
        activities=[execute_tool, record_run],
        activity_executor=ThreadPoolExecutor(MAX_ACTIVITIES),
        workflow_runner=WORKFLOW_RUNNER,
    )


async def connect_with_retry(
    address: str,
    namespace: str,
    *,
    connect: Callable[..., Awaitable[Any]] = Client.connect,
    retry_seconds: float = CONNECT_RETRY_SECONDS,
) -> Any:
    """Keep trying: compose starts Temporal and SMCP together, in no fixed order."""
    while True:
        try:
            return await connect(address, namespace=namespace)
        except Exception as exc:            # noqa: BLE001 — any transport error
            log.warning("skill worker: Temporal at %s not reachable (%s); retrying",
                        address, exc)
            await asyncio.sleep(retry_seconds)


async def serve(address: str, namespace: str, tooluniverse: Any) -> None:
    client = await connect_with_retry(address, namespace)
    worker = build_worker(client, tooluniverse)
    log.info("skill worker polling %s namespace=%s queue=%s", address, namespace, TASK_QUEUE)
    await worker.run()


def start_in_thread(tooluniverse: Any, address: str | None = None,
                    namespace: str | None = None) -> threading.Thread | None:
    """Start the worker beside the server, or do nothing when Temporal is not configured."""
    address = address or configured()
    if not address:
        return None
    namespace = namespace or os.environ.get("TEMPORAL_NAMESPACE") or NAMESPACE
    thread = threading.Thread(
        target=lambda: asyncio.run(serve(address, namespace, tooluniverse)),
        name="skill-worker", daemon=True)
    thread.start()
    return thread
