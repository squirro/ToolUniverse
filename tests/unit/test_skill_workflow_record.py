"""Tool results go around Temporal's history; the facts go through it (ADR-0017).

These tests run the real activities against a bound executor and a Working Record in a
temporary directory, under Temporal's time-skipping environment. No server, no network.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_workflow import (  # noqa: E402
    WORKFLOW_RUNNER,
    SkillRunInput,
    SkillWorkflow,
    absorb_step,
    bind_executor,
    bind_records,
    execute_tool,
    keep_answered_evidence,
)
from tooluniverse.skill_working_record import WorkingRecord  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

QUEUE = "skills-record-test"

PROCESS = {
    "skill": "demo",
    "inputs": ["drug_name"],
    "tables": {"prr_rows": "fact", "papers": "evidence"},
    "steps": [
        {"id": "signals",
         "calls": [{"tool": "disproportionality", "arguments": {"drug": "{drug_name}"}}],
         "collect": {"prr_rows": {"path": "data.rows", "flatten": True,
                                  "fields": ["term", "prr", "url"]}}},
        {"id": "literature", "requires": ["signals"],
         "calls": [{"tool": "search_papers", "arguments": {"query": "{drug_name}"}}],
         "collect": {"papers": {"path": "data.articles", "flatten": True,
                                "fields": ["pmid", "title", "abstract", "url"]}}},
    ],
}

PRR_ROWS = [{"term": "DEAFNESS", "prr": 17.7, "url": "https://example.org/deafness"}]
PAPERS = [{"pmid": str(n), "title": f"Paper {n}", "abstract": "finding " * 320,
           "url": f"https://pubmed.ncbi.nlm.nih.gov/{n}/"} for n in range(1000)]
RESPONSES = {"disproportionality": {"data": {"rows": PRR_ROWS}},
             "search_papers": {"data": {"articles": PAPERS}}}


@activity.defn(name="record_run")
def _record_run(skel: dict) -> str:
    return "urn:test:record"


async def test_a_result_larger_than_temporal_allows_goes_through_and_stays_out_of_the_history(tmp_path):
    assert len(json.dumps(RESPONSES["search_papers"])) > 2_000_000
    bind_executor(lambda tool, arguments: RESPONSES[tool])
    bind_records(tmp_path)

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue=QUEUE, workflows=[SkillWorkflow],
                          activities=[execute_tool, absorb_step, keep_answered_evidence, _record_run],
                          activity_executor=ThreadPoolExecutor(4),
                          workflow_runner=WORKFLOW_RUNNER):
            handle = await env.client.start_workflow(
                SkillWorkflow.run,
                SkillRunInput(skill="demo", process=PROCESS, inputs={"drug_name": "cisplatin"}),
                id="run-big", task_queue=QUEUE)
            handover = await handle.result()
            history = await handle.fetch_history()

    assert handover["facts"]["prr_rows"] == PRR_ROWS
    described = {t["table"]: t["rows"] for t in handover["tables"]}
    assert described == {"papers": 1000, "results.signals": 1, "results.literature": 1000}
    assert "results" not in handover
    assert "truncated" not in json.dumps(handover)
    assert len(history.to_json()) < 200_000
    assert WorkingRecord(tmp_path, "run-big").fetch("papers", limit=1)["total_rows"] == 1000
