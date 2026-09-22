"""run_skill / continue_skill — the agent's view of a Skill Run (ADR-0016, DSR-712).

The agent never sees Temporal. It sees two tools whose return value is one of
three shapes — finished with the bundle, waiting with a question, running with a
progress line — and it keeps calling until the first. Every return is a tick the
user can see; the user decided a tick lands on every step boundary. These tests
drive the pure client over a scripted handle, so no server and no clock.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_run_client import (  # noqa: E402
    missing_inputs,
    progress,
    wait_for_progress,
)

pytestmark = pytest.mark.unit

PROCESS = {"skill": "demo", "inputs": ["drug_name"], "optional_inputs": ["requested_aes"],
           "steps": [{"id": "a", "calls": []}]}


def _status(step_id, done, waiting=None, finished=False, remaining=0):
    return {"finished": finished, "step_id": step_id, "step_label": f"Phase {step_id}",
            "done": done, "remaining": remaining, "waiting_for": waiting}


class ScriptedHandle:
    """Answers `query` from a script, one status per poll; records signals."""

    def __init__(self, statuses, result=None):
        self.statuses, self.result_value, self.signals = list(statuses), result, []
        self.id = "skill-demo-1"

    async def query(self, _name):
        return self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]

    async def signal(self, _name, payload):
        self.signals.append(payload)

    async def result(self):
        return self.result_value


def test_missing_required_inputs_are_named_and_optional_ones_are_not():
    assert missing_inputs(PROCESS, {}) == ["drug_name"]
    assert missing_inputs(PROCESS, {"drug_name": "x"}) == []
    assert missing_inputs(PROCESS, {"requested_aes": ["MDS"]}) == ["drug_name"]


def test_the_three_shapes():
    assert progress("r1", _status("a", [], finished=True), bundle={"skill": "demo"}) == {
        "status": "finished", "run_id": "r1", "bundle": {"skill": "demo"}}
    question = {"kind": "judge", "step": "a", "wants": ["k"], "context": {}}
    assert progress("r1", _status("a", [], waiting=question)) == {
        "status": "waiting", "run_id": "r1", "question": question,
        "step_id": "a", "step_label": "Phase a", "done": 0}
    assert progress("r1", _status("b", ["a"], remaining=3)) == {
        "status": "running", "run_id": "r1", "step_id": "b", "step_label": "Phase b",
        "done": 1, "remaining": 3}


@pytest.mark.asyncio
async def test_waiting_returns_on_the_next_step_boundary():
    """Entered while step a runs; returns as soon as the run is on step b."""
    handle = ScriptedHandle([_status("a", []), _status("a", []), _status("b", ["a"], remaining=2)])

    out = await wait_for_progress(handle, window=10, poll=0)

    assert out["status"] == "running" and out["step_id"] == "b" and out["done"] == 1


@pytest.mark.asyncio
async def test_waiting_returns_at_once_when_the_run_asks_a_question():
    question = {"kind": "repair", "step": "a", "wants": ["drug_name"], "context": {}}
    handle = ScriptedHandle([_status("a", [], waiting=question)])

    out = await wait_for_progress(handle, window=10, poll=0)

    assert out["status"] == "waiting" and out["question"] == question


@pytest.mark.asyncio
async def test_waiting_returns_the_bundle_when_the_run_finishes():
    handle = ScriptedHandle([_status("a", []), _status(None, ["a"], finished=True)],
                            result={"skill": "demo", "facts": {}})

    out = await wait_for_progress(handle, window=10, poll=0)

    assert out["status"] == "finished" and out["bundle"]["skill"] == "demo"


@pytest.mark.asyncio
async def test_waiting_gives_up_after_the_window_with_a_running_tick():
    """A long step: the agent still gets a tick, and calls again."""
    handle = ScriptedHandle([_status("a", [], remaining=9)])

    out = await wait_for_progress(handle, window=0.05, poll=0.01)

    assert out["status"] == "running" and out["step_id"] == "a"


from tooluniverse.skill_process_store import SkillProcessNotFound  # noqa: E402
from tooluniverse.skill_run_client import start  # noqa: E402


class FakeStore:
    def __init__(self, process=None):
        self.process = process

    def load(self, skill):
        if self.process is None:
            raise SkillProcessNotFound(f"no Skill Process published for {skill!r}")
        return self.process, {"definition_hash": "h" * 64, "git_commit": "abc"}


class FakeClient:
    def __init__(self, handle):
        self.handle, self.started = handle, []

    async def start_workflow(self, _run, inp, *, id, task_queue):
        self.started.append((inp, id, task_queue))
        return self.handle


@pytest.mark.asyncio
async def test_a_missing_required_input_is_reported_before_any_run_starts():
    client = FakeClient(ScriptedHandle([_status("a", [])]))

    out = await start(client, FakeStore(PROCESS), "demo", {"requested_aes": ["MDS"]})

    assert out["status"] == "schema_mismatch" and out["missing_inputs"] == ["drug_name"]
    assert client.started == []


@pytest.mark.asyncio
async def test_a_skill_without_a_published_process_is_an_error_not_a_fallback():
    client = FakeClient(ScriptedHandle([_status("a", [])]))

    out = await start(client, FakeStore(None), "no-such", {"drug_name": "x"})

    assert out["status"] == "error" and "no-such" in out["error"]
    assert client.started == []


@pytest.mark.asyncio
async def test_start_carries_the_definition_and_its_hash_into_the_run():
    handle = ScriptedHandle([_status("a", []), _status("b", ["a"], remaining=1)])
    client = FakeClient(handle)

    out = await start(client, FakeStore(PROCESS), "demo", {"drug_name": "x"})

    inp, run_id, queue = client.started[0]
    assert inp.process == PROCESS and inp.definition_hash == "h" * 64
    assert inp.definition_iri.endswith("/skills/demo") and run_id.startswith("skill-demo-")
    assert queue == "skills"
    assert out["status"] == "running" and out["step_id"] == "b"
