"""The Temporal worker that runs inside the SMCP process (ADR-0016, DSR-711).

One door: the activity must reach the registry through the same instance and the
same normalisation the agent's `execute_tool` uses, so a run sees exactly what the
agent sees — the exclusions, the stamped citations, the transport status. These
tests bind the worker to a stub "ToolUniverse" and drive a real workflow through it
under the time-skipping environment.
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from temporalio.testing import WorkflowEnvironment

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse import skill_worker  # noqa: E402
from tooluniverse.skill_workflow import SkillRunInput, SkillWorkflow  # noqa: E402

pytestmark = pytest.mark.unit

PROCESS = {
    "skill": "one-call", "inputs": ["gene"],
    "steps": [{"id": "lookup",
               "calls": [{"tool": "MyGene_query_genes", "arguments": {"query": "{gene}"}}],
               "extract": {"symbol": "hits.0.symbol"}}],
}


class StubToolUniverse:
    """Answers like the loaded registry does: `run_one_function` takes a function-call
    dict and may return a JSON *string*, which the agent's door decodes."""

    def __init__(self):
        self.calls = []

    def run_one_function(self, function_call):
        self.calls.append(function_call)
        return json.dumps({"hits": [{"symbol": "GBA"}]})


def test_without_a_temporal_address_no_worker_starts(monkeypatch):
    monkeypatch.delenv("TEMPORAL_ADDRESS", raising=False)
    assert skill_worker.start_in_thread(StubToolUniverse()) is None


@pytest.mark.asyncio
async def test_the_activity_reaches_the_registry_through_the_agents_door():
    registry = StubToolUniverse()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        worker = skill_worker.build_worker(env.client, registry, task_queue="skills-test")
        async with worker:
            bundle = await env.client.execute_workflow(
                SkillWorkflow.run,
                SkillRunInput(skill="one-call", process=PROCESS, inputs={"gene": "GBA"}),
                id="run-door", task_queue="skills-test")

    assert registry.calls == [{"name": "MyGene_query_genes", "arguments": {"query": "GBA"}}]
    assert bundle["facts"]["symbol"] == "GBA", "the JSON string was decoded, as for the agent"
    assert bundle["results"]["lookup"] == [{"hits": [{"symbol": "GBA"}]}]


@pytest.mark.asyncio
async def test_connecting_retries_until_the_server_is_there():
    """Compose brings SMCP and Temporal up together; the worker must not die if
    Temporal is a few seconds behind."""
    attempts = []

    async def connect(address, namespace):
        attempts.append((address, namespace))
        if len(attempts) < 3:
            raise RuntimeError("connection refused")
        return "client"

    client = await skill_worker.connect_with_retry(
        "temporal:7233", "skills", connect=connect, retry_seconds=0)

    assert client == "client"
    assert attempts == [("temporal:7233", "skills")] * 3
