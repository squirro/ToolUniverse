"""The Temporal worker that runs inside the SMCP process (ADR-0016).

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
from tooluniverse.skill_working_record import WorkingRecord  # noqa: E402
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
async def test_the_activity_reaches_the_registry_through_the_agents_door(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILL_WORKING_RECORDS", str(tmp_path))
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
    assert WorkingRecord(tmp_path, "run-door").results("lookup") == [{"hits": [{"symbol": "GBA"}]}]


MAPPED = {
    "skill": "mapped", "inputs": ["drug_name"], "optional_inputs": ["requested_aes"],
    "tables": {"faers_term_rows": "fact", "requested_meddra": "fact"},
    "steps": [
        {"id": "faers_counts",
         "calls": [{"tool": "FAERS_count_reactions_by_drug_event",
                    "arguments": {"medicinalproduct": "{drug_name}"}}],
         "collect": {"faers_term_rows": {"path": "result", "flatten": True, "fields": ["term"]}}},
        {"id": "requested_terms", "requires": ["faers_counts"], "when": "requested_aes",
         "judge": ["requested_meddra"],
         "mapping": {"requested_meddra": {"of": "requested_aes",
                                          "onto": {"rows": "faers_term_rows", "field": "term"}}},
         "produces": ["requested_meddra"]},
    ],
}


class FaersStub(StubToolUniverse):
    def run_one_function(self, function_call):
        return json.dumps({"result": [{"term": "DEAFNESS"}, {"term": "NAUSEA"}]})


@pytest.mark.asyncio
async def test_the_worker_places_a_judged_mapping_with_the_ontology_lookup(tmp_path, monkeypatch):
    """The served worker must carry the placing activity, bound to the live lookup by default."""
    from tooluniverse import skill_ontology_placing

    recorded = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ols"
                           / "placing_probe_2026-09-21.json").read_text())
    monkeypatch.setenv("SKILL_WORKING_RECORDS", str(tmp_path))
    monkeypatch.setattr(skill_ontology_placing, "lookup", lambda term: recorded.get(term, {}))

    async def answer_when_asked(handle):
        for _ in range(200):
            state = await handle.query(SkillWorkflow.status)
            if state["waiting_for"]:
                await handle.signal(SkillWorkflow.answer, {"requested_meddra": [
                    {"of": "ototoxicity", "term": "DEAFNESS", "reason": "the ototoxic injury",
                     "concept": ["ear", "hearing"]}]})
                return
            await asyncio.sleep(0.05)
        raise AssertionError("the run never asked")

    async with await WorkflowEnvironment.start_time_skipping() as env:
        worker = skill_worker.build_worker(env.client, FaersStub(), task_queue="skills-test")
        async with worker:
            handle = await env.client.start_workflow(
                SkillWorkflow.run,
                SkillRunInput(skill="mapped", process=MAPPED,
                              inputs={"drug_name": "x", "requested_aes": ["ototoxicity"]}),
                id="run-placed", task_queue="skills-test")
            await answer_when_asked(handle)
            handed = await handle.result()

    (row,) = handed["facts"]["requested_meddra"]
    assert (row["term"], row["placing"], row["ontology"]) == ("DEAFNESS", "placed", "hp")
    assert handed["mappings"] == ["requested_meddra"]


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
