"""run_skill / continue_skill: the agent's view of a Skill Run (ADR-0016).

The agent never sees Temporal. It sees two tools whose return value is one of three
shapes (finished with the bundle, waiting with a question, running with a progress
line) and it keeps calling until the first, so a tick lands on every step boundary.
These tests drive the pure client over a scripted handle, so no server and no clock.
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
    finished = progress("r1", _status("a", [], finished=True), handover={"skill": "demo"})
    assert finished["status"] == "finished" and finished["handover"] == {"skill": "demo"}
    # The reply the agent acts on has to say what comes next, in the reply itself.
    assert "submit_report(run_id=\"r1\"" in finished["next"] and "before you answer" in finished["next"]
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
async def test_waiting_returns_the_handover_when_the_run_finishes():
    handle = ScriptedHandle([_status("a", []), _status(None, ["a"], finished=True)],
                            result={"skill": "demo", "facts": {}})

    out = await wait_for_progress(handle, window=10, poll=0)

    assert out["status"] == "finished" and out["handover"]["skill"] == "demo"


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

    out = await start(client, FakeStore(PROCESS), "demo",
                      {"drug_name": "x", "requested_aes": None})

    inp, run_id, queue = client.started[0]
    assert inp.process == PROCESS and inp.definition_hash == "h" * 64
    assert inp.definition_iri.endswith("/skills/demo") and run_id.startswith("skill-demo-")
    assert queue == "skills"
    assert out["status"] == "running" and out["step_id"] == "b"


@pytest.mark.asyncio
async def test_a_published_process_with_an_undeclared_table_does_not_start():
    """The definition in GraphDB does not pass through the YAML loader; the rule still holds."""
    leaky = {**PROCESS, "steps": PROCESS["steps"] + [
        {"id": "literature", "calls": [], "collect": {"papers": {"path": "data.articles"}}}]}
    client = FakeClient(ScriptedHandle([_status("a", [])]))

    out = await start(client, FakeStore(leaky), "demo", {"drug_name": "x"})

    assert out["status"] == "error" and "papers" in out["error"]
    assert client.started == []


def test_the_agent_fetches_rows_of_a_finished_run_by_its_run_id(tmp_path):
    from tooluniverse.skill_run_client import fetch_run_data
    from tooluniverse.skill_working_record import WorkingRecord

    WorkingRecord(tmp_path, "skill-demo-1").put_table(
        "papers", [{"pmid": "1", "title": "A"}, {"pmid": "2", "title": "B"}])

    out = fetch_run_data("skill-demo-1", "papers", columns=["pmid"], limit=1, offset=1,
                         directory=tmp_path)

    assert out["status"] == "ok" and out["rows"] == [{"pmid": "2"}]


def test_a_fetch_for_a_run_that_does_not_exist_says_so_and_leaves_nothing_behind(tmp_path):
    from tooluniverse.skill_run_client import fetch_run_data

    out = fetch_run_data("skill-demo-404", "papers", directory=tmp_path)

    assert out["status"] == "unknown_run"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_an_optional_input_left_undecided_stops_the_run_and_is_named():
    """Absent is not an answer: the question may name what this input is for."""
    client = FakeClient(ScriptedHandle([_status("a", [])]))

    out = await start(client, FakeStore(PROCESS), "demo", {"drug_name": "x"})

    assert out["status"] == "confirm_inputs"
    assert out["undecided_inputs"] == ["requested_aes"]
    assert client.started == []


@pytest.mark.asyncio
async def test_an_optional_input_declined_with_null_starts_the_run_without_it():
    client = FakeClient(ScriptedHandle([_status("a", []), _status("b", ["a"], remaining=1)]))

    out = await start(client, FakeStore(PROCESS), "demo",
                      {"drug_name": "x", "requested_aes": None})

    assert out["status"] == "running"
    assert client.started[0][0].inputs == {"drug_name": "x"}


@pytest.mark.asyncio
async def test_an_optional_input_that_is_bound_reaches_the_run():
    client = FakeClient(ScriptedHandle([_status("a", []), _status("b", ["a"], remaining=1)]))

    await start(client, FakeStore(PROCESS), "demo",
                {"drug_name": "x", "requested_aes": ["ototoxicity"]})

    assert client.started[0][0].inputs == {"drug_name": "x", "requested_aes": ["ototoxicity"]}


def test_the_agent_asks_for_the_rows_most_relevant_to_its_own_words(tmp_path):
    from tooluniverse.skill_run_client import fetch_run_data
    from tooluniverse.skill_working_record import WorkingRecord

    WorkingRecord(tmp_path, "skill-demo-1").put_table("papers", [
        {"pmid": "1", "abstract": "A herbal formula was studied in mice."},
        {"pmid": "2", "abstract": "Magnesium lowered acute kidney injury after cisplatin."}])

    out = fetch_run_data("skill-demo-1", "papers", columns=["pmid"], limit=1,
                         rank_by="cisplatin kidney injury magnesium", directory=tmp_path)

    assert out["rows"][0]["pmid"] == "2" and out["matched"] == 1


@pytest.mark.asyncio
async def test_an_input_name_the_process_does_not_declare_is_refused_with_the_declared_ones():
    """An invented input name is refused with the declared ones, not silently ignored."""
    client = FakeClient(ScriptedHandle([_status("a", [])]))

    out = await start(client, FakeStore(PROCESS), "demo",
                      {"drug_name": "x", "requested_aes": None, "focus_adverse_events": ["y"]})

    assert out["status"] == "schema_mismatch"
    assert out["unknown_inputs"] == ["focus_adverse_events"]
    assert out["required_inputs"] == ["drug_name"] and out["optional_inputs"] == ["requested_aes"]
    assert client.started == []


# --- the draft report is read before the user sees it ------------------------------

HANDOVER = {"skill": "demo", "facts": {"prr_table": [
    {"term": "ototoxicity", "prr": 54.766,
     "url": "https://api.fda.gov/drug/event.json?search=ototoxicity&api_key=REDACTED"}]}}


class FinishedClient(FakeClient):
    def get_workflow_handle(self, run_id):
        return self.handle


def _records(tmp_path):
    from tooluniverse.skill_working_record import WorkingRecord
    record = WorkingRecord(tmp_path, "skill-demo-1")
    record.put_table("papers", [{"pmid": "31234567", "abstract": "Hearing loss in 57%.",
                                 "url": "https://pubmed.ncbi.nlm.nih.gov/31234567/"}])
    record.fetch("papers", columns=["pmid", "abstract", "url"], limit=1)
    return tmp_path


@pytest.mark.asyncio
async def test_a_draft_that_states_only_what_the_agent_received_is_accepted(tmp_path):
    from tooluniverse.skill_run_client import submit_report

    draft = ("PRR 54.77 for ototoxicity [1]; hearing loss in 57% [2].\n"
             "[1]: https://api.fda.gov/drug/event.json?search=ototoxicity\n"
             "[2]: https://pubmed.ncbi.nlm.nih.gov/31234567/")
    client = FinishedClient(ScriptedHandle([_status("z", ["z"], finished=True)], result=HANDOVER))

    out = await submit_report(client, "skill-demo-1", draft, directory=_records(tmp_path))

    assert out == {"status": "accepted", "run_id": "skill-demo-1", "failures": []}


@pytest.mark.asyncio
async def test_a_draft_with_an_unvouched_number_is_sent_back_once_then_goes_out_with_the_failure_stated(tmp_path):
    from tooluniverse.skill_run_client import submit_report

    draft = "PRR 54.77 for ototoxicity, against a Canadian PRR of about 53.44."
    client = FinishedClient(ScriptedHandle([_status("z", ["z"], finished=True)], result=HANDOVER))
    directory = _records(tmp_path)

    first = await submit_report(client, "skill-demo-1", draft, directory=directory)
    second = await submit_report(client, "skill-demo-1", draft, directory=directory)

    assert first["status"] == "revise" and first["failures"][0]["text"] == "53.44"
    assert "53.44" in first["hint"]
    assert second["status"] == "accepted_with_failures"
    assert second["failures"][0]["text"] == "53.44"
    assert "53.44" in second["append_to_report"]
