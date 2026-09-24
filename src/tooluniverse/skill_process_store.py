"""Skill Processes in GraphDB: publish the reviewed YAML, read it back at run start.

The YAML in the repo is authoritative; GraphDB holds the published copy, one named
graph per skill in a dedicated repository, so a process is queryable and `run_skill`
reads it from the same store that holds the Run Record. A publish replaces the graph;
a load is one CONSTRUCT. There is no fallback to packaged YAML: a store that does not
answer is an error, not a silently different definition.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from rdflib import Graph

from .skill_graph_bbo import definition_hash, from_bbo, provenance, to_bbo

SKILLS_BASE = "https://data.swissrockets.com/skills/"
DEFAULT_REPOSITORY = "skill-processes"
TIMEOUT = 30

# A plain GraphDB repository; nothing the atlas needs (no Lucene connector).
_REPOSITORY_CONFIG = """\
@prefix rep: <http://www.openrdf.org/config/repository#> .
@prefix sr: <http://www.openrdf.org/config/repository/sail#> .
@prefix sail: <http://www.openrdf.org/config/sail#> .
@prefix graphdb: <http://www.ontotext.com/config/graphdb#> .

[] a rep:Repository ;
    rep:repositoryID "{repository}" ;
    rdfs:label "Skill Processes (ADR-0016)" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:Sail" ;
            graphdb:ruleset "empty" ;
            graphdb:enable-context-index "true" ;
        ]
    ] .
"""


class SkillProcessNotFound(LookupError):
    """No published process for that skill in the store."""


class SkillProcessMismatch(RuntimeError):
    """The process rebuilt from the store is not the definition its hash names."""


def named_graph(skill: str) -> str:
    return SKILLS_BASE + skill


RUNS_BASE = SKILLS_BASE + "runs/"


def run_graph(run_id: str) -> str:
    return RUNS_BASE + run_id


@dataclass
class Store:
    endpoint: str
    repository: str = DEFAULT_REPOSITORY
    auth: tuple[str, str] | None = None

    @classmethod
    def from_env(cls) -> Store:
        endpoint = os.environ.get("GRAPHDB_ENDPOINT")
        if not endpoint:
            raise RuntimeError("GRAPHDB_ENDPOINT is not set")
        user, password = os.environ.get("GRAPHDB_USERNAME"), os.environ.get("GRAPHDB_PASSWORD")
        return cls(endpoint=endpoint.rstrip("/"),
                   repository=os.environ.get("GRAPHDB_SKILLS_REPO") or DEFAULT_REPOSITORY,
                   auth=(user, password) if user else None)

    # -- publish -------------------------------------------------------------------

    def publish(self, process: dict, git_commit: str | None = None) -> str:
        """Replace the skill's named graph with this process. Returns the graph IRI."""
        iri = named_graph(process["skill"])
        turtle = to_bbo(process, git_commit=git_commit)
        # A copy the reader cannot rebuild whole would be refused at every run start.
        rebuilt(Graph().parse(data=turtle, format="turtle"), process["skill"])
        response = requests.put(
            f"{self.endpoint}/repositories/{self.repository}/rdf-graphs/service",
            params={"graph": iri},
            data=turtle.encode(),
            headers={"Content-Type": "text/turtle; charset=utf-8"},
            auth=self.auth, timeout=TIMEOUT)
        response.raise_for_status()
        return iri

    def record(self, turtle: str, run_id: str) -> str:
        """Replace the run's named graph with its Run Record. Returns the graph IRI."""
        iri = run_graph(run_id)
        response = requests.put(
            f"{self.endpoint}/repositories/{self.repository}/rdf-graphs/service",
            params={"graph": iri},
            data=turtle.encode(),
            headers={"Content-Type": "text/turtle; charset=utf-8"},
            auth=self.auth, timeout=TIMEOUT)
        response.raise_for_status()
        return iri

    def ensure_repository(self) -> None:
        probe = requests.get(f"{self.endpoint}/rest/repositories/{self.repository}",
                             auth=self.auth, timeout=TIMEOUT)
        if probe.status_code == 200:
            return
        if probe.status_code != 404:
            probe.raise_for_status()
        created = requests.post(
            f"{self.endpoint}/rest/repositories",
            files={"config": ("config.ttl",
                              _REPOSITORY_CONFIG.format(repository=self.repository),
                              "text/turtle")},
            auth=self.auth, timeout=TIMEOUT)
        created.raise_for_status()

    # -- load ----------------------------------------------------------------------

    def load(self, skill: str) -> tuple[dict, dict]:
        """The process dict and its provenance, from the skill's named graph."""
        iri = named_graph(skill)
        response = requests.post(
            f"{self.endpoint}/repositories/{self.repository}",
            data={"query": f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{iri}> {{ ?s ?p ?o }} }}"},
            headers={"Accept": "text/turtle"},
            auth=self.auth, timeout=TIMEOUT)
        response.raise_for_status()
        # Turtle is UTF-8 by definition; do not let requests guess from the header.
        g = Graph().parse(data=response.content, format="turtle")
        if len(g) == 0:
            raise SkillProcessNotFound(
                f"no Skill Process published for {skill!r} in {self.repository} at {self.endpoint}")
        return rebuilt(g, skill)


def rebuilt(g: Graph, skill: str) -> tuple[dict, dict]:
    """The process read back from its graph, and its provenance.

    The hash is recomputed on what was rebuilt, so a step key the reader does not carry
    is a refusal, not a smaller process running under the full definition's hash.
    """
    process, prov = from_bbo(g), provenance(g)
    actual = definition_hash(process)
    if actual != prov["definition_hash"]:
        raise SkillProcessMismatch(
            f"the published process for {skill!r} does not rebuild to the definition it was "
            f"published from (published hash {prov['definition_hash'][:12] or 'none'}, "
            f"rebuilt {actual[:12]}): the store and this server disagree on the process's "
            "keys, so it cannot run until it is republished from this server's version")
    return process, prov
