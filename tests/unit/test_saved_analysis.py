"""A Saved Analysis is written by a user's save and replayed on new Inputs (ADR-0019).

It has the shape of a Skill Process and runs on the same interpreter, but its only copy is
a named graph under `analyses/<prompt id>` in the `skill-processes` repository, written by
SMCP when the Studio plugin forwards a confirmed save. These tests sit at the same HTTP
boundary as the process-store tests, with a mocked GraphDB.
"""

import sys
from pathlib import Path

import pytest
from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.saved_analysis import (  # noqa: E402
    problems,
    SavedAnalysisRefused,
    analysis_skill,
    save,
)
from tooluniverse.skill_graph_bbo import provenance, to_bbo  # noqa: E402
from tooluniverse.skill_process_store import Store, named_graph  # noqa: E402

pytestmark = pytest.mark.unit

ENDPOINT = "http://graphdb.test:7200"
PROMPT_ID = "K_IZog8LROOP2gPODyN2uQ"

# One recorded ToolUniverse call with one Input: the tracer's whole shape.
DEFINITION = {
    "inputs": ["target"],
    "steps": [{
        "id": "turn1_call1",
        "label": "Turn 1: trials for the target",
        "calls": [{"tool": "ClinicalTrials_search_studies",
                   "arguments": {"condition": "prostate cancer", "intervention": "{target}"}}],
    }],
}


def _store():
    return Store(endpoint=ENDPOINT, repository="skill-processes", auth=("u", "p"))


def _put(requests_mock):
    return requests_mock.put(
        f"{ENDPOINT}/repositories/skill-processes/rdf-graphs/service", status_code=204)


def test_a_saved_analysis_lives_under_the_analyses_prefix_keyed_by_the_prompt_id():
    assert analysis_skill(PROMPT_ID) == f"analyses/{PROMPT_ID}"
    assert named_graph(analysis_skill(PROMPT_ID)) == \
        f"https://data.swissrockets.com/skills/analyses/{PROMPT_ID}"


@pytest.mark.parametrize("bad", ["", "../x", "a b", "x" * 200, "a/b", "<x>"])
def test_a_prompt_id_that_is_not_a_squirro_id_is_refused(bad):
    with pytest.raises(SavedAnalysisRefused):
        analysis_skill(bad)


def test_save_writes_the_definition_with_its_author_and_prompt_id(requests_mock):
    put = _put(requests_mock)

    iri = save(_store(), PROMPT_ID, DEFINITION, author="user-42")

    assert iri == named_graph(f"analyses/{PROMPT_ID}")
    g = Graph().parse(data=put.last_request.text, format="turtle")
    assert provenance(g)["author"] == "user-42"
    assert provenance(g)["prompt_id"] == PROMPT_ID


def test_what_save_writes_reads_back_as_the_same_definition(requests_mock):
    put = _put(requests_mock)
    save(_store(), PROMPT_ID, DEFINITION, author="user-42")
    requests_mock.post(f"{ENDPOINT}/repositories/skill-processes",
                       text=put.last_request.text, headers={"Content-Type": "text/turtle"})

    loaded, prov = _store().load(analysis_skill(PROMPT_ID))

    assert loaded == {**DEFINITION, "skill": f"analyses/{PROMPT_ID}"}
    assert prov["author"] == "user-42"


def test_the_skill_id_comes_from_the_prompt_id_never_from_the_body(requests_mock):
    put = _put(requests_mock)

    iri = save(_store(), PROMPT_ID, {**DEFINITION, "skill": "adverse-event-detection"},
               author="user-42")

    assert iri == named_graph(f"analyses/{PROMPT_ID}")
    # requests_mock's `.qs` lowercases values; the prompt id is case-sensitive.
    from urllib.parse import parse_qs, urlparse
    assert parse_qs(urlparse(put.last_request.url).query) == {"graph": [iri]}


@pytest.mark.parametrize("definition", [
    {"inputs": ["target"], "steps": []},
    {"inputs": [], "steps": [{"id": "s", "calls": [], "when": "never_bound"}]},
    {"inputs": [], "steps": [{"id": "s", "calls": [], "collect": {"rows": {"path": "x"}}}]},
])
def test_a_definition_that_cannot_run_is_refused_and_nothing_is_written(requests_mock,
                                                                       definition):
    put = _put(requests_mock)

    with pytest.raises(SavedAnalysisRefused):
        save(_store(), PROMPT_ID, definition, author="user-42")

    assert not put.called


def test_a_skill_process_published_without_provenance_extras_reads_as_before():
    prov = provenance(Graph().parse(data=to_bbo({"skill": "x", "inputs": [], "steps": [
        {"id": "s", "calls": []}]}, git_commit="abc"), format="turtle"))

    assert prov["git_commit"] == "abc"
    assert prov["author"] is None and prov["prompt_id"] is None


# -- the SMCP save route and the replay tool --------------------------------------------

from tooluniverse.saved_analysis import handle_save, replay  # noqa: E402

TOKEN = "s3cret-token"
BODY = {"prompt_id": PROMPT_ID, "author": "user-42", "definition": DEFINITION}


@pytest.mark.parametrize("given", [None, "", "wrong", TOKEN + "x"])
def test_a_save_without_the_shared_token_is_refused_and_nothing_is_written(requests_mock,
                                                                         given):
    put = _put(requests_mock)

    status, out = handle_save(BODY, given, TOKEN, _store())

    assert status == 401 and "token" in out["error"]
    assert not put.called


@pytest.mark.parametrize("body", [
    {**BODY, "author": ""},
    {k: v for k, v in BODY.items() if k != "definition"},
    {**BODY, "prompt_id": "../x"},
    "not an object",
])
def test_a_malformed_save_is_refused_with_a_reason(requests_mock, body):
    put = _put(requests_mock)

    status, out = handle_save(body, TOKEN, TOKEN, _store())

    assert status in (400, 422) and out["error"]
    assert not put.called


def test_a_save_with_the_token_is_written_and_answers_with_the_graph(requests_mock):
    _put(requests_mock)

    status, out = handle_save(BODY, TOKEN, TOKEN, _store())

    assert status == 200 and out == {"iri": named_graph(f"analyses/{PROMPT_ID}"),
                                     "prompt_id": PROMPT_ID}


class _Store:
    def __init__(self, process):
        self.process, self.asked = process, []

    def load(self, skill):
        self.asked.append(skill)
        return self.process, {"definition_hash": "h" * 64}


class _Handle:
    id = "run"

    async def query(self, _name):
        return {"finished": False, "step_id": "turn1_call1", "step_label": "Turn 1",
                "done": [], "remaining": 1, "waiting_for": None}


class _Client:
    def __init__(self):
        self.started = []

    async def start_workflow(self, _run, inp, *, id, task_queue):
        self.started.append(inp)
        return _Handle()


@pytest.mark.asyncio
async def test_replay_runs_the_prompts_saved_analysis_with_the_given_inputs():
    client, store = _Client(), _Store({**DEFINITION, "skill": f"analyses/{PROMPT_ID}"})

    out = await replay(client, store, PROMPT_ID, {"target": "AR-V7"})

    assert store.asked == [f"analyses/{PROMPT_ID}"]
    assert client.started[0].inputs == {"target": "AR-V7"}
    assert out["status"] == "running"


@pytest.mark.asyncio
async def test_replay_with_an_unknown_input_starts_nothing_and_names_the_expected_ones():
    client = _Client()
    store = _Store({**DEFINITION, "skill": f"analyses/{PROMPT_ID}"})

    out = await replay(client, store, PROMPT_ID, {"gene": "AR-V7"})

    assert out["status"] == "schema_mismatch" and out["required_inputs"] == ["target"]
    assert client.started == []


@pytest.mark.asyncio
async def test_replay_of_a_bad_prompt_id_is_an_error_and_reads_nothing():
    client, store = _Client(), _Store(None)

    out = await replay(client, store, "../adverse-event-detection", {})

    assert out["status"] == "error" and store.asked == [] and client.started == []


# -- Derived values at replay (SA-03): the converter's shapes run on NEW outputs ---------

from tooluniverse.skill_runner import SkillRunner  # noqa: E402

# As the delivery repo's converter proposes them for "search AR-V7 trials, then each one's
# details" (three recorded calls for three trials) and "map the gene, then its structure".
LOOP = {"skill": "analyses/x", "inputs": ["intervention"], "steps": [
    {"id": "t1_c1", "label": "Turn 1: search", "produces": ["nct_id_list"],
     "extract": {"nct_id_list": "studies[].nct_id"},
     "calls": [{"tool": "search", "arguments": {"intervention": "{intervention}"}}]},
    {"id": "t1_c2", "label": "Turn 1: get_study", "requires": ["t1_c1"],
     "for_each": "nct_id_list", "as": "nct_id",
     "calls": [{"tool": "get_study", "arguments": {"nct_id": "{nct_id}", "sections": "summary"}}]},
]}
ONLY = {"skill": "analyses/y", "inputs": ["gene_names"], "steps": [
    {"id": "t1_c1", "label": "Turn 1: map", "produces": ["qualifier"],
     "extract": {"qualifier": "results.0.to"},
     "calls": [{"tool": "map", "arguments": {"gene_names": "{gene_names}"}}]},
    {"id": "t1_c2", "label": "Turn 1: structure", "requires": ["t1_c1"],
     "calls": [{"tool": "structure", "arguments": {"qualifier": "{qualifier}"}}]},
]}


def _replay(graph, inputs, outputs):
    calls = []
    runner = SkillRunner(graph, execute=lambda t, a: calls.append((t, a)) or outputs.get(t, {}))
    run_id = runner.start(inputs)["run_id"]
    for _ in range(10):
        if runner.advance(run_id) is None or runner.state(run_id).get("finished"):
            break
    return calls


def test_a_loop_makes_one_call_for_every_item_of_the_new_output():
    new = {"search": {"studies": [{"nct_id": f"NCT0{n}"} for n in range(1, 5)]}}

    calls = _replay(LOOP, {"intervention": "KRAS"}, new)

    assert calls[0] == ("search", {"intervention": "KRAS"})
    assert [a for t, a in calls if t == "get_study"] == [
        {"nct_id": f"NCT0{n}", "sections": "summary"} for n in range(1, 5)]


def test_the_only_value_is_taken_from_the_new_output_not_the_recorded_one():
    calls = _replay(ONLY, {"gene_names": "KRAS"}, {"map": {"results": [{"to": "P01116"}]}})

    assert ("structure", {"qualifier": "P01116"}) in calls


def test_both_shapes_pass_the_save_checks():
    assert problems(LOOP) == [] and problems(ONLY) == []


# -- Choice at replay (SA-05, ADR-0020): the user picks from the NEW candidates ----------

from rdflib import Graph as _Graph  # noqa: E402

from tooluniverse.skill_graph_bbo import from_bbo  # noqa: E402
from tooluniverse.skill_run_client import progress  # noqa: E402

# As the converter proposes "map the gene, then the structure of the FIRST accession" (1 of 3).
CHOICE = {"skill": "analyses/z", "inputs": ["gene_names"], "steps": [
    {"id": "t1_c1", "label": "Turn 1: map", "produces": ["qualifier_candidates"],
     "extract": {"qualifier_candidates": "results[].to"},
     "calls": [{"tool": "map", "arguments": {"gene_names": "{gene_names}"}}]},
    {"id": "t1_c2_pick", "label": "Turn 1: pick qualifier", "requires": ["t1_c1"], "calls": [],
     "judge": ["qualifier_pick"], "produces": ["qualifier_pick"],
     "check": {"qualifier_pick": {"only_in": "qualifier_candidates"}},
     "choose": {"qualifier_pick": {"from": "qualifier_candidates", "recorded": ["Q92826"]}}},
    {"id": "t1_c2", "label": "Turn 1: structure", "requires": ["t1_c2_pick"],
     "for_each": "qualifier_pick", "as": "qualifier",
     "calls": [{"tool": "structure", "arguments": {"qualifier": "{qualifier}"}}]},
]}


def _choose(new_candidates, answers):
    calls, questions, answers = [], [], list(answers)
    runner = SkillRunner(
        CHOICE,
        execute=lambda t, a: calls.append((t, a)) or (
            {"results": [{"to": c} for c in new_candidates]} if t == "map" else {}),
        ask=lambda q: questions.append(q) or (answers.pop(0) if answers else None))
    run_id = runner.start({"gene_names": "KRAS"})["run_id"]
    for _ in range(10):
        if runner.advance(run_id) is None or runner.state(run_id).get("finished"):
            break
    return calls, questions


def test_a_choice_asks_the_user_with_the_new_candidates_and_the_old_pick_preselected():
    _, questions = _choose(["P01116", "Q92826", "E5FF39"], [{"qualifier_pick": ["P01116"]}])

    (q,) = questions
    assert q["kind"] == "choose" and q["wants"] == ["qualifier_pick"]
    assert q["choices"] == {"qualifier_pick": ["P01116", "Q92826", "E5FF39"]}
    assert q["preselected"] == {"qualifier_pick": ["Q92826"]}


def test_a_recorded_pick_the_new_output_lacks_is_not_preselected():
    _, questions = _choose(["P01116", "E5FF39"], [{"qualifier_pick": ["P01116"]}])

    assert questions[0]["preselected"] == {"qualifier_pick": []}


def test_the_users_pick_drives_the_calls_that_use_it():
    calls, _ = _choose(["P01116", "Q92826", "E5FF39"], [{"qualifier_pick": ["P01116", "E5FF39"]}])

    assert [a["qualifier"] for t, a in calls if t == "structure"] == ["P01116", "E5FF39"]


def test_a_single_picked_value_counts_as_a_list_of_one():
    calls, _ = _choose(["P01116", "Q92826"], [{"qualifier_pick": "P01116"}])

    assert [a["qualifier"] for t, a in calls if t == "structure"] == ["P01116"]


def test_a_pick_from_outside_the_candidates_is_asked_again_then_left_unresolved():
    calls, questions = _choose(["P01116", "Q92826"],
                               [{"qualifier_pick": ["HOXB13"]}, {"qualifier_pick": ["X"]}])

    assert len(questions) == 2 and "HOXB13" in questions[1]["problem"]
    assert not [c for c in calls if c[0] == "structure"]


def test_a_choice_survives_the_graphdb_round_trip():
    assert from_bbo(_Graph().parse(data=to_bbo(CHOICE), format="turtle")) == CHOICE
    assert problems(CHOICE) == []


def test_the_waiting_reply_sends_a_choice_to_the_user_not_to_the_model():
    out = progress("r1", {"step_id": "t1_c2_pick", "done": ["t1_c1"], "waiting_for": {
        "kind": "choose", "wants": ["qualifier_pick"], "choices": {"qualifier_pick": ["A"]},
        "preselected": {"qualifier_pick": []}}})

    assert out["status"] == "waiting"
    assert "user" in out["next"] and "do not choose" in out["next"].lower()


def test_a_call_whose_tool_is_not_a_tool_name_is_refused_before_anything_is_written(
        requests_mock):
    put = _put(requests_mock)
    bad = {"steps": [{"id": "s", "calls": [{"tool": "Identity & Classification",
                                            "arguments": {}}]}]}

    status, out = handle_save({**BODY, "definition": bad}, TOKEN, TOKEN, _store())

    assert status == 422 and "tool names" in out["error"] and not put.called


def test_a_definition_that_would_not_read_back_whole_is_refused_as_the_callers_to_fix(
        requests_mock):
    put = _put(requests_mock)

    status, out = handle_save({**BODY, "definition": {**DEFINITION, "inputs": []}},
                              TOKEN, TOKEN, _store())

    assert status == 422 and "rebuild" in out["error"] and not put.called
