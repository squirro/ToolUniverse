"""run_skill / continue_skill: the agent's view of a Skill Run (ADR-0016).

The agent never sees Temporal. It sees two tools whose return value is one of three shapes
(finished with the bundle, waiting with a question, running with a progress line) and it
keeps calling until the first. These tests drive the pure client over a scripted handle.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_process_store import SkillProcessNotFound  # noqa: E402
from tooluniverse.skill_run_client import (  # noqa: E402
    fetch_run_data,
    missing_inputs,
    progress,
    start,
    submit_report,
    wait_for_progress,
)
from tooluniverse.skill_working_record import WorkingRecord  # noqa: E402

pytestmark = pytest.mark.unit

PROCESS = {"skill": "demo", "inputs": ["drug_name"], "optional_inputs": ["requested_aes"],
           "steps": [{"id": "a", "calls": []}]}
LEAKY = {**PROCESS, "steps": PROCESS["steps"] + [
    {"id": "literature", "calls": [], "collect": {"papers": {"path": "data.articles"}}}]}
SHUT = {**PROCESS, "steps": PROCESS["steps"] + [
    {"id": "comparative", "requires": ["a"], "when": "comparator", "calls": []}]}
QUESTION = {"kind": "judge", "step": "a", "wants": ["k"], "context": {}}


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
    assert progress("r1", _status("a", [], waiting=QUESTION)) == {
        "status": "waiting", "run_id": "r1", "question": QUESTION,
        "step_id": "a", "step_label": "Phase a", "done": 0}
    assert progress("r1", _status("b", ["a"], remaining=3)) == {
        "status": "running", "run_id": "r1", "step_id": "b", "step_label": "Phase b",
        "done": 1, "remaining": 3}


@pytest.mark.asyncio
@pytest.mark.parametrize("statuses, result, window, poll, expected", [
    # entered while step a runs; returns as soon as the run is on step b
    ([_status("a", []), _status("a", []), _status("b", ["a"], remaining=2)], None, 10, 0,
     {"status": "running", "step_id": "b", "done": 1}),
    ([_status("a", [], waiting=QUESTION)], None, 10, 0,
     {"status": "waiting", "question": QUESTION}),
    ([_status("a", []), _status(None, ["a"], finished=True)], {"skill": "demo", "facts": {}}, 10, 0,
     {"status": "finished", "handover": {"skill": "demo", "facts": {}}}),
    # a long step: the agent still gets a tick, and calls again
    ([_status("a", [], remaining=9)], None, 0.05, 0.01,
     {"status": "running", "step_id": "a"}),
], ids=["boundary", "question", "finished", "window"])
async def test_waiting_returns_on_the_boundary_the_question_the_finish_or_the_window(
        statuses, result, window, poll, expected):
    out = await wait_for_progress(ScriptedHandle(statuses, result), window=window, poll=poll)

    assert {k: out[k] for k in expected} == expected


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
@pytest.mark.parametrize("process, skill, inputs, expected, needle", [
    (PROCESS, "demo", {"requested_aes": ["MDS"]},
     {"status": "schema_mismatch", "missing_inputs": ["drug_name"]}, None),
    # a skill without a published process is an error, not a fallback
    (None, "no-such", {"drug_name": "x"}, {"status": "error"}, "no-such"),
    # the definition in GraphDB does not pass through the YAML loader; the rule still holds
    (LEAKY, "demo", {"drug_name": "x"}, {"status": "error"}, "papers"),
    # nor does a gate that nothing can open
    (SHUT, "demo", {"drug_name": "x"}, {"status": "error"}, "comparator"),
    # absent is not an answer: the question may name what the optional input is for
    (PROCESS, "demo", {"drug_name": "x"},
     {"status": "confirm_inputs", "undecided_inputs": ["requested_aes"]}, None),
    # an invented input name is refused with the declared ones, not silently ignored
    (PROCESS, "demo", {"drug_name": "x", "requested_aes": None, "focus_adverse_events": ["y"]},
     {"status": "schema_mismatch", "unknown_inputs": ["focus_adverse_events"],
      "required_inputs": ["drug_name"], "optional_inputs": ["requested_aes"]}, None),
], ids=["missing", "no-process", "undeclared-table", "unbound-gate", "undecided", "unknown-input"])
async def test_a_run_that_cannot_start_says_why_and_starts_nothing(
        process, skill, inputs, expected, needle):
    client = FakeClient(ScriptedHandle([_status("a", [])]))

    out = await start(client, FakeStore(process), skill, inputs)

    assert {k: out[k] for k in expected} == expected
    assert needle is None or needle in out["error"]
    assert client.started == []


@pytest.mark.asyncio
async def test_start_carries_the_definition_and_its_hash_into_the_run():
    client = FakeClient(ScriptedHandle([_status("a", []), _status("b", ["a"], remaining=1)]))

    out = await start(client, FakeStore(PROCESS), "demo",
                      {"drug_name": "x", "requested_aes": None})

    inp, run_id, queue = client.started[0]
    assert inp.process == PROCESS and inp.definition_hash == "h" * 64
    assert inp.definition_iri.endswith("/skills/demo") and run_id.startswith("skill-demo-")
    assert queue == "skills"
    assert out["status"] == "running" and out["step_id"] == "b"


@pytest.mark.asyncio
@pytest.mark.parametrize("requested_aes, reaching", [
    (None, {"drug_name": "x"}),                                        # declined with null
    (["ototoxicity"], {"drug_name": "x", "requested_aes": ["ototoxicity"]}),
])
async def test_an_optional_input_reaches_the_run_only_when_it_is_bound(requested_aes, reaching):
    client = FakeClient(ScriptedHandle([_status("a", []), _status("b", ["a"], remaining=1)]))

    out = await start(client, FakeStore(PROCESS), "demo",
                      {"drug_name": "x", "requested_aes": requested_aes})

    assert out["status"] == "running"
    assert client.started[0][0].inputs == reaching


def test_the_agent_fetches_rows_of_a_finished_run_by_its_run_id(tmp_path):
    WorkingRecord(tmp_path, "skill-demo-1").put_table(
        "papers", [{"pmid": "1", "title": "A"}, {"pmid": "2", "title": "B"}])

    out = fetch_run_data("skill-demo-1", "papers", columns=["pmid"], limit=1, offset=1,
                         directory=tmp_path)

    assert out["status"] == "ok" and out["rows"] == [{"pmid": "2"}]


def test_a_fetch_for_a_run_that_does_not_exist_says_so_and_leaves_nothing_behind(tmp_path):
    out = fetch_run_data("skill-demo-404", "papers", directory=tmp_path)

    assert out["status"] == "unknown_run"
    assert list(tmp_path.iterdir()) == []


def test_the_agent_asks_for_the_rows_most_relevant_to_its_own_words(tmp_path):
    WorkingRecord(tmp_path, "skill-demo-1").put_table("papers", [
        {"pmid": "1", "abstract": "A herbal formula was studied in mice."},
        {"pmid": "2", "abstract": "Magnesium lowered acute kidney injury after cisplatin."}])

    out = fetch_run_data("skill-demo-1", "papers", columns=["pmid"], limit=1,
                         rank_by="cisplatin kidney injury magnesium", directory=tmp_path)

    assert out["rows"][0]["pmid"] == "2" and out["matched"] == 1


# --- the draft report is read before the user sees it ------------------------------

HANDOVER = {"skill": "demo", "facts": {"prr_table": [
    {"term": "ototoxicity", "prr": 54.766,
     "url": "https://api.fda.gov/drug/event.json?search=ototoxicity&api_key=REDACTED"}]}}


class FinishedClient(FakeClient):
    def get_workflow_handle(self, run_id):
        return self.handle


def _records(tmp_path):
    record = WorkingRecord(tmp_path, "skill-demo-1")
    record.put_table("papers", [{"pmid": "31234567", "abstract": "Hearing loss in 57%.",
                                 "url": "https://pubmed.ncbi.nlm.nih.gov/31234567/"}])
    record.fetch("papers", columns=["pmid", "abstract", "url"], limit=1)
    return tmp_path


@pytest.mark.asyncio
async def test_a_draft_that_states_only_what_the_agent_received_is_accepted(tmp_path):
    draft = ("PRR 54.77 for ototoxicity [1]; hearing loss in 57% [2].\n"
             "[1]: https://api.fda.gov/drug/event.json?search=ototoxicity\n"
             "[2]: https://pubmed.ncbi.nlm.nih.gov/31234567/")
    client = FinishedClient(ScriptedHandle([_status("z", ["z"], finished=True)], result=HANDOVER))

    out = await submit_report(client, "skill-demo-1", draft, directory=_records(tmp_path))

    assert out == {"status": "accepted", "run_id": "skill-demo-1", "failures": []}


@pytest.mark.asyncio
async def test_a_draft_with_an_unvouched_number_is_sent_back_once_then_goes_out_with_the_failure_stated(tmp_path):
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


@pytest.mark.asyncio
async def test_a_published_process_the_store_cannot_give_back_whole_is_an_error_the_agent_sees(
        requests_mock, monkeypatch):
    """The run executes what the store returns; a key the reader drops must not run."""
    from tooluniverse import skill_graph_bbo
    from tooluniverse.skill_graph import load_graph
    from tooluniverse.skill_process_store import Store

    endpoint = "http://graphdb.test:7200"
    requests_mock.post(f"{endpoint}/repositories/skill-processes",
                       text=skill_graph_bbo.to_bbo(load_graph("adverse-event-detection")),
                       headers={"Content-Type": "text/turtle"})
    specs = {k: v for k, v in skill_graph_bbo._JSON_SPECS.items() if k != "compute"}
    monkeypatch.setattr(skill_graph_bbo, "_JSON_SPECS", specs)
    client = FakeClient(ScriptedHandle([_status("a", [])]))

    out = await start(client, Store(endpoint=endpoint), "adverse-event-detection",
                      {"drug_name": "cisplatin", "requested_aes": None})

    assert client.started == []
    assert out["status"] == "error"
    assert "republish" in out["error"]


# --- the served body promises a server run only when the host can take one now -----

@pytest.mark.asyncio
async def test_the_served_body_promises_a_server_run_only_while_the_host_answers():
    from tooluniverse.skill_run_client import served_directive

    async def up():
        return None

    async def down():
        return "ConnectError: connection refused"

    skill = "clinical-data-integration"
    assert "THE SERVER RUNS" in await served_directive(skill, up)
    unreachable = await served_directive(skill, down)
    assert "THE SERVER RUNS" not in unreachable and "next_skill_step(" in unreachable
    assert "THE SERVER RUNS" not in await served_directive(skill, None)   # no host configured


class _Health:
    def __init__(self, healthy):
        self.healthy = healthy

    async def check_health(self, *, timeout=None):
        if isinstance(self.healthy, Exception):
            raise self.healthy
        return self.healthy


class _Client:
    def __init__(self, healthy):
        self.service_client = _Health(healthy)


@pytest.mark.asyncio
async def test_the_host_probe_names_why_the_host_cannot_take_a_run():
    import asyncio

    from tooluniverse.skill_run_client import host_unreachable

    async def healthy():
        return _Client(True)

    async def refused():
        raise ConnectionRefusedError("temporal:7233")

    async def failing_health():
        return _Client(RuntimeError("not serving"))

    async def hangs():
        await asyncio.sleep(10)

    assert await host_unreachable(healthy, timeout=0.5) is None
    assert "temporal:7233" in await host_unreachable(refused, timeout=0.5)
    assert "not serving" in await host_unreachable(failing_health, timeout=0.5)
    assert "Timeout" in await host_unreachable(hangs, timeout=0.1)
