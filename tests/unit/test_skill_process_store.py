"""Skill Processes live in GraphDB; the run reads its definition from there (DSR-709).

The YAML in the repo is authoritative and reviewed; GraphDB holds the published
copy — one named graph per skill in the `skill-processes` repository — and
`run_skill` reads it at run start. These tests sit at the HTTP boundary with a
mocked GraphDB: what publish sends, what load asks, and what a missing graph
becomes. Nothing here needs a live store.
"""

import sys
from pathlib import Path

import pytest
import requests
from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_graph import load_graph  # noqa: E402
from tooluniverse.skill_graph_bbo import to_bbo  # noqa: E402
from tooluniverse.skill_process_store import (  # noqa: E402
    SkillProcessNotFound,
    Store,
    named_graph,
)

pytestmark = pytest.mark.unit

ENDPOINT = "http://graphdb.test:7200"


def _store():
    return Store(endpoint=ENDPOINT, repository="skill-processes", auth=("u", "p"))


def test_the_named_graph_is_one_per_skill_under_the_skills_base():
    assert named_graph("clinical-data-integration") == \
        "https://data.swissrockets.com/skills/clinical-data-integration"


def test_publish_puts_the_turtle_into_the_skills_named_graph(requests_mock):
    put = requests_mock.put(
        f"{ENDPOINT}/repositories/skill-processes/rdf-graphs/service", status_code=204)
    process = load_graph("adverse-event-detection")

    iri = _store().publish(process, git_commit="abc1234")

    assert iri == named_graph("adverse-event-detection")
    assert put.called_once
    req = put.last_request
    assert req.qs == {"graph": [iri]}
    assert req.headers["Content-Type"].startswith("text/turtle")
    assert "abc1234" in req.text and "adverse-event-detection" in req.text
    assert req.headers["Authorization"].startswith("Basic ")


def test_load_constructs_the_named_graph_and_returns_the_process(requests_mock):
    process = load_graph("rare-disease-diagnosis")
    requests_mock.post(f"{ENDPOINT}/repositories/skill-processes",
                       text=to_bbo(process, git_commit="abc1234"),
                       headers={"Content-Type": "text/turtle"})

    loaded, prov = _store().load("rare-disease-diagnosis")

    assert loaded == process
    assert prov["git_commit"] == "abc1234" and len(prov["definition_hash"]) == 64
    from urllib.parse import parse_qs
    query = parse_qs(requests_mock.last_request.text)["query"][0]
    assert query.startswith("CONSTRUCT") and f"<{named_graph('rare-disease-diagnosis')}>" in query


def test_a_skill_with_no_published_process_is_a_named_error(requests_mock):
    requests_mock.post(f"{ENDPOINT}/repositories/skill-processes",
                       text=Graph().serialize(format="turtle"),
                       headers={"Content-Type": "text/turtle"})

    with pytest.raises(SkillProcessNotFound) as exc:
        _store().load("no-such-skill")

    assert "no-such-skill" in str(exc.value)


def test_a_store_that_does_not_answer_raises_rather_than_falling_back(requests_mock):
    """No packaged-YAML fallback: a failed query is an error the tool returns."""
    requests_mock.post(f"{ENDPOINT}/repositories/skill-processes",
                       exc=requests.ConnectionError("refused"))

    with pytest.raises(requests.ConnectionError):
        _store().load("adverse-event-detection")


def test_ensure_repository_creates_it_only_when_missing(requests_mock):
    requests_mock.get(f"{ENDPOINT}/rest/repositories/skill-processes", status_code=404)
    post = requests_mock.post(f"{ENDPOINT}/rest/repositories", status_code=201)

    _store().ensure_repository()

    assert post.called_once
    assert "skill-processes" in post.last_request.text

    requests_mock.get(f"{ENDPOINT}/rest/repositories/skill-processes", status_code=200,
                      json={"id": "skill-processes"})
    _store().ensure_repository()
    assert post.call_count == 1
