"""The Skill Process interpreter on Temporal (ADR-0016, DSR-710).

One workflow type runs every process; the process travels inside the run as input.
Every tool call is an activity; the model's two holes — repair and judgement — are a
`status` query the caller polls and an `answer` signal it sends. These tests drive the
workflow the way the agent will, through a client, under Temporal's time-skipping
environment with a stub activity registered under the real activity's name — so the
one-hour ceiling costs nothing to test and no server is needed.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_runner import SkillRunner  # noqa: E402
from tooluniverse.skill_workflow import (  # noqa: E402
    WORKFLOW_RUNNER,
    SkillRunInput,
    SkillWorkflow,
    ToolCall,
    ToolResult,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

QUEUE = "skills-test"

GRAPH = {
    "skill": "demo",
    "inputs": ["drug_name"],
    "steps": [
        {"id": "resolve",
         "calls": [{"tool": "resolve_drug", "arguments": {"name": "{drug_name}"}}],
         "extract": {"chembl_id": "data.id"}},
        {"id": "signals", "requires": ["resolve"],
         "calls": [{"tool": "disproportionality",
                    "arguments": {"chembl_id": "{chembl_id}"}}],
         "extract": {"rows": "data.rows"},
         "derive": {"strong_signal": {"from": "rows", "field": "prr",
                                      "op": ">=", "value": 5, "mode": "any"}}},
        {"id": "stratify", "requires": ["signals"], "when": "strong_signal",
         "calls": [{"tool": "stratify", "arguments": {"chembl_id": "{chembl_id}"}}]},
        {"id": "report", "requires": ["signals"], "calls": []},
    ],
}

OK = {
    "resolve_drug": {"data": {"id": "CHEMBL88"}},
    "disproportionality": {"data": {"rows": [{"prr": 17.7}, {"prr": 1.2}]}},
    "stratify": {"data": {"sex": "F"}},
}


def _stub(responses):
    """A stub under the real activity's name: tool -> payload, or an Exception."""
    calls = []

    @activity.defn(name="execute_tool")
    def execute_tool(call: ToolCall) -> ToolResult:
        calls.append((call.tool, call.arguments))
        value = responses[call.tool]
        if callable(value):
            value = value(call)
        if isinstance(value, Exception):
            raise ApplicationError(str(value), non_retryable=True)
        return ToolResult(payload=value)

    return execute_tool, calls


async def _run(env, responses, process, inputs, run_id="run-1", before_result=None):
    stub, calls = _stub(responses)
    async with Worker(env.client, task_queue=QUEUE, workflows=[SkillWorkflow],
                      activities=[stub], activity_executor=ThreadPoolExecutor(4),
                      workflow_runner=WORKFLOW_RUNNER):
        handle = await env.client.start_workflow(
            SkillWorkflow.run,
            SkillRunInput(skill=process["skill"], process=process, inputs=inputs),
            id=run_id, task_queue=QUEUE)
        if before_result:
            await before_result(handle, env)
        return await handle.result(), calls


def _in_memory(responses, process, inputs):
    runner = SkillRunner(process, execute=lambda tool, a: responses[tool])
    run_id = runner.start(inputs)["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass
    return runner.bundle(run_id)


async def test_the_workflow_returns_the_bundle_the_in_memory_runner_returns():
    """Parity is the claim: same process, same stubs, same evidence."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, calls = await _run(env, OK, GRAPH, {"drug_name": "cisplatin"})

    assert bundle == _in_memory(OK, GRAPH, {"drug_name": "cisplatin"})
    assert [tool for tool, _ in calls] == ["resolve_drug", "disproportionality", "stratify"]
    assert bundle["facts"]["strong_signal"] is True
    assert bundle["steps_done"] == ["resolve", "signals", "stratify", "report"]


async def _wait_for_question(handle, tries=200):
    """Poll `status` the way run_skill will, until the run is waiting on the model."""
    import asyncio
    for _ in range(tries):
        state = await handle.query(SkillWorkflow.status)
        if state["waiting_for"] or state["finished"]:
            return state
        await asyncio.sleep(0.05)
    raise AssertionError("the run never asked")


async def test_a_failing_tool_is_a_recorded_failure_and_the_run_goes_on():
    broken = dict(OK, stratify=RuntimeError("bot-blocked"))
    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, _ = await _run(env, broken, GRAPH, {"drug_name": "cisplatin"}, "run-fail")

    assert bundle["steps_done"] == ["resolve", "signals", "stratify", "report"]
    assert [f["tool"] for f in bundle["failures"]] == ["stratify"]
    assert "bot-blocked" in bundle["failures"][0]["error"]
    assert bundle["results"]["stratify"] == []


async def test_a_step_that_cannot_be_built_is_blocked_not_fatal():
    """resolve returns no id, so signals cannot be composed; report still runs."""
    no_id = dict(OK, resolve_drug={"data": {}})
    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, calls = await _run(env, no_id, GRAPH, {"drug_name": "x"}, "run-blocked")

    assert [tool for tool, _ in calls] == ["resolve_drug"]
    # signals cannot be composed; report needs no fact, so it still runs, and
    # stratify's gate never opens. Same rule as the in-memory runner.
    assert bundle["steps_done"] == ["resolve", "report"]
    assert bundle["unresolved"] == [{"step": "resolve", "fact": "chembl_id"}]
    assert [b["step"] for b in bundle["blocked"]] == ["signals"]
    assert "missing chembl_id" in bundle["blocked"][0]["reason"]


REPAIRED = {
    "skill": "repaired", "inputs": ["drug_name"],
    "steps": [
        {"id": "identity",
         "calls": [{"tool": "DailyMed_search_spls", "arguments": {"drug_name": "{drug_name}"}}],
         "repair": {"argument": "drug_name", "when_missing": "setid"},
         "extract": {"setid": "data.0.setid"}},
        {"id": "label", "requires": ["identity"],
         "calls": [{"tool": "DailyMed_parse", "arguments": {"setid": "{setid}"}}]},
    ],
}


async def test_a_repair_is_asked_for_by_signal_and_the_second_suggestion_resolves_it():
    seen = []

    def dailymed(call):
        seen.append(call.arguments["drug_name"])
        found = call.arguments["drug_name"] == "Lutathera"
        return {"data": [{"setid": "72d1"}] if found else []}

    responses = {"DailyMed_search_spls": dailymed, "DailyMed_parse": {"data": "label"}}

    async def answer_the_repair(handle, env):
        state = await _wait_for_question(handle)
        question = state["waiting_for"]
        assert question["kind"] == "repair" and question["wants"] == ["drug_name"]
        assert question["value"] == "lutetium Lu-177 dotatate"
        await handle.signal(SkillWorkflow.answer,
                            {"drug_name": ["lutetium lu 177 dotatate", "Lutathera"]})

    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, _ = await _run(env, responses, REPAIRED,
                               {"drug_name": "lutetium Lu-177 dotatate"}, "run-repair",
                               before_result=answer_the_repair)

    assert seen == ["lutetium Lu-177 dotatate", "lutetium lu 177 dotatate", "Lutathera"]
    assert bundle["calls"] == {"identity": ["DailyMed_search_spls"] * 3,
                               "label": ["DailyMed_parse"]}, "retries are on the record"
    assert bundle["facts"]["drug_name"] == "Lutathera"
    assert bundle["facts"]["setid"] == "72d1"
    assert bundle["steps_done"] == ["identity", "label"]
    assert bundle["blocked"] == []



JUDGED = {
    "skill": "judged", "inputs": ["symptoms"],
    "steps": [
        {"id": "hypothesis", "calls": [], "produces": ["keyword"], "judge": ["keyword"]},
        {"id": "search", "requires": ["hypothesis"],
         "calls": [{"tool": "orphanet", "arguments": {"query": "{keyword}"}}]},
    ],
}


async def test_a_judgement_is_asked_for_by_signal_and_carried_into_the_next_call():
    async def judge(handle, env):
        state = await _wait_for_question(handle)
        question = state["waiting_for"]
        assert question == {"kind": "judge", "step": "hypothesis", "wants": ["keyword"],
                            "context": {"symptoms": ["hepatosplenomegaly"]}}
        assert state["step_id"] == "hypothesis" and state["done"] == []
        await handle.signal(SkillWorkflow.answer, {"keyword": "storage disorder"})

    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, calls = await _run(env, {"orphanet": {"data": []}}, JUDGED,
                                   {"symptoms": ["hepatosplenomegaly"]}, "run-judge",
                                   before_result=judge)

    assert calls == [("orphanet", {"query": "storage disorder"})]
    assert bundle["facts"]["keyword"] == "storage disorder"
    assert bundle["unresolved"] == [] and bundle["blocked"] == []


async def test_a_question_nobody_answers_closes_the_step_as_blocked_after_the_ceiling():
    """Time-skipped: the hour passes at once. The run still finishes and says why."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, calls = await _run(env, {"orphanet": {"data": []}}, JUDGED,
                                   {"symptoms": ["x"]}, "run-unanswered")

    assert bundle["blocked"][0] == {"step": "hypothesis",
                                    "reason": "no answer to judge for ['keyword']"}
    assert bundle["unresolved"] == [{"step": "hypothesis", "fact": "keyword"}]
    assert calls == [], "search needs the keyword, so it is blocked too"
    assert [b["step"] for b in bundle["blocked"]] == ["hypothesis", "search"]


async def test_the_history_holds_the_process_the_answer_and_replays_deterministically():
    """The Run Record: the definition in the started event, the model's answer as a
    signal event, and a history the interpreter replays without a determinism error."""
    from temporalio.worker import Replayer

    async def judge(handle, env):
        await _wait_for_question(handle)
        await handle.signal(SkillWorkflow.answer, {"keyword": "storage disorder"})

    stub, _ = _stub({"orphanet": {"data": []}})
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue=QUEUE, workflows=[SkillWorkflow],
                          activities=[stub], activity_executor=ThreadPoolExecutor(2),
                          workflow_runner=WORKFLOW_RUNNER):
            handle = await env.client.start_workflow(
                SkillWorkflow.run,
                SkillRunInput(skill="judged", process=JUDGED, inputs={"symptoms": ["x"]},
                              definition_iri="https://data.swissrockets.com/skills/judged",
                              definition_hash="abc123"),
                id="run-history", task_queue=QUEUE)
            await judge(handle, env)
            await handle.result()
            history = await handle.fetch_history()

    events = history.events
    started = events[0].workflow_execution_started_event_attributes
    first_input = started.input.payloads[0].data.decode()
    assert '"process"' in first_input and '"hypothesis"' in first_input
    assert "abc123" in first_input
    signals = [e.workflow_execution_signaled_event_attributes for e in events
               if e.HasField("workflow_execution_signaled_event_attributes")]
    assert [s.signal_name for s in signals] == ["answer"]
    assert "storage disorder" in signals[0].input.payloads[0].data.decode()

    await Replayer(workflows=[SkillWorkflow],
                   workflow_runner=WORKFLOW_RUNNER).replay_workflow(history)


from tooluniverse.skill_graph import GRAPHS_DIR, load_graph  # noqa: E402


@pytest.mark.parametrize("skill", sorted(p.stem for p in GRAPHS_DIR.glob("*.yaml")))
async def test_every_shipped_process_finishes_on_temporal_with_a_signalling_oracle(skill):
    import asyncio

    process = load_graph(skill)
    tools = {c["tool"] for s in process["steps"] for c in s.get("calls", [])}

    async def answer_everything(handle, env):
        for _ in range(400):
            state = await handle.query(SkillWorkflow.status)
            if state["finished"]:
                return
            if state["waiting_for"]:
                wants = state["waiting_for"]["wants"]
                await handle.signal(SkillWorkflow.answer, {n: ["stub"] for n in wants})
            await asyncio.sleep(0.02)

    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, _ = await _run(env, {t: {} for t in tools}, process,
                               {n: ["stub"] for n in process.get("inputs", [])},
                               f"run-{skill}", before_result=answer_everything)

    assert bundle["skill"] == skill
    assert not any("no answer" in b["reason"] for b in bundle["blocked"]), bundle["blocked"]


DELEGATED = {
    "skill": "delegated", "inputs": ["drug_name"], "report": "Say what the web adds.",
    "steps": [
        {"id": "label", "calls": [{"tool": "label_tool", "arguments": {"q": "{drug_name}"}}],
         "notes": "The label is ground truth."},
        {"id": "web_context", "requires": ["label"],
         "delegate": [{"tool": "exa_web_search", "arguments": {"query": "{drug_name} safety"}}],
         "produces": ["web_context"]},
    ],
}


async def test_a_delegated_step_pauses_with_the_calls_and_the_answer_lands_in_the_bundle():
    async def do_the_search(handle, env):
        state = await _wait_for_question(handle)
        q = state["waiting_for"]
        assert q["kind"] == "delegate" and q["wants"] == ["web_context"]
        assert q["calls"] == [{"tool": "exa_web_search", "arguments": {"query": "Lutathera safety"}}]
        await handle.signal(SkillWorkflow.answer, {"web_context": [{"title": "hit", "url": "https://x"}]})

    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, calls = await _run(env, {"label_tool": {"data": "label"}}, DELEGATED,
                                   {"drug_name": "Lutathera"}, "run-delegate",
                                   before_result=do_the_search)

    assert calls == [("label_tool", {"q": "Lutathera"})], "the server made only its own call"
    assert bundle["facts"]["web_context"] == [{"title": "hit", "url": "https://x"}]
    assert bundle["calls"] == {"label": ["label_tool"], "web_context": ["exa_web_search"]}
    assert bundle["notes"] == {"label": "The label is ground truth."}
    assert bundle["report"] == "Say what the web adds."


# --- fan-out: concurrent under a per-source ceiling, results in declared order ----
#
# Of 366 s inside Temporal on the Lutathera question, 345 s were fourteen FAERS
# calls made one after another (ADR-0016). A loop's iterations are independent by
# construction — the same call with one value substituted — so they run at once,
# capped per source, and are gathered back in the order they were declared.

import threading
import time

LOOP = {
    "skill": "loop",
    "inputs": ["terms"],
    "steps": [
        {"id": "prr", "for_each": "terms", "as": "term",
         "calls": [{"tool": "ChEMBL_lookup", "arguments": {"term": "{term}"}}],
         "collect": {"seen": {"path": "data.term"}}},
        {"id": "report", "requires": ["prr"], "calls": []},
    ],
}


def _counting(delay_for):
    """A stub that records how many calls are in flight at once."""
    state = {"in_flight": 0, "peak": 0, "lock": threading.Lock()}

    def respond(call):
        with state["lock"]:
            state["in_flight"] += 1
            state["peak"] = max(state["peak"], state["in_flight"])
        time.sleep(delay_for(call.arguments["term"]))
        with state["lock"]:
            state["in_flight"] -= 1
        return {"data": {"term": call.arguments["term"]}}

    return respond, state


async def test_loop_iterations_run_at_once_but_never_more_than_the_source_ceiling():
    respond, state = _counting(lambda term: 0.3)
    terms = ["a", "b", "c", "d", "e", "f"]
    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, calls = await _run(env, {"ChEMBL_lookup": respond}, LOOP, {"terms": terms})

    assert state["peak"] == 2                      # ChEMBL's ceiling; 4 worker threads available
    assert bundle["facts"]["seen"] == terms        # declared order, not completion order
    assert len(calls) == 6


async def test_results_keep_declared_order_when_a_later_call_finishes_first():
    respond, _ = _counting(lambda term: {"a": 0.4, "b": 0.05}.get(term, 0.05))
    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, _ = await _run(env, {"ChEMBL_lookup": respond}, LOOP, {"terms": ["a", "b"]})

    assert bundle["facts"]["seen"] == ["a", "b"]


async def test_one_failed_iteration_leaves_the_others_and_names_its_item():
    def respond(call):
        if call.arguments["term"] == "b":
            raise ApplicationError("429 Too Many Requests", non_retryable=True)
        return {"data": {"term": call.arguments["term"]}}

    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, _ = await _run(env, {"ChEMBL_lookup": respond}, LOOP, {"terms": ["a", "b", "c"]})

    assert bundle["facts"]["seen"] == ["a", "c"]
    assert bundle["steps_done"] == ["prr", "report"]
    assert len(bundle["failures"]) == 1
    assert bundle["failures"][0]["tool"] == "ChEMBL_lookup"
    assert bundle["failures"][0]["arguments"] == {"term": "b"}
    assert "429" in bundle["failures"][0]["error"]


async def test_the_fan_out_changes_nothing_the_in_memory_runner_returns():
    """Parity is still the claim: the same process, the same stubs, the same bundle."""
    responses = {"ChEMBL_lookup": lambda call: {"data": {"term": call.arguments["term"]}}}
    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, _ = await _run(env, responses, LOOP, {"terms": ["x", "y", "z"]})

    sync = SkillRunner(LOOP, execute=lambda tool, a: {"data": {"term": a["term"]}})
    run_id = sync.start({"terms": ["x", "y", "z"]})["run_id"]
    while not sync.advance(run_id)["finished"]:
        pass
    assert bundle == sync.bundle(run_id)


async def test_a_delegated_step_is_handed_to_the_agent_whole_never_fanned_out():
    process = {"skill": "d", "inputs": ["names"], "steps": [
        {"id": "web",
         "delegate": [{"tool": "exa_web_search", "arguments": {"query": "{names}"}}],
         "produces": ["hits"]}]}

    async def answer_when_asked(handle, env):
        while True:
            status = await handle.query(SkillWorkflow.status)
            if status["waiting_for"]:
                break
            await env.sleep(1)
        assert status["waiting_for"]["kind"] == "delegate"
        await handle.signal(SkillWorkflow.answer, {"hits": ["ok"]})

    async with await WorkflowEnvironment.start_time_skipping() as env:
        bundle, calls = await _run(env, {}, process, {"names": ["p", "q"]},
                                   before_result=answer_when_asked)

    assert calls == []                      # no execute_tool activity ran
    assert bundle["facts"]["hits"] == ["ok"]
