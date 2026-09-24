"""drug-target-validation's identity step counts a MyGene hit as the target only when it
names the query: the hit's symbol is the query, or the query is one of the aliases MyGene
lists for the hit, compared without regard to case.

MyGene answers a near miss with a wrong first hit, not with nothing ("FR-alpha" gives
FOLR2, "FOLR-1" gives FOLR3). Such a hit goes to the repair, and the repaired symbol is
what the run describes. The MyGene responses are recorded live, unedited.
"""
import json
from pathlib import Path

import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "dtv"
MYGENE = json.loads((FIXTURES / "mygene_folr1_queries_2026-09-24.json").read_text())
OTHERS = json.loads((FIXTURES / "folr1_ovarian_2026-09-22.json").read_text())


def _identity(target, suggestions=("FOLR1",)):
    """Run the identity step alone; the agent suggests `suggestions` when asked to repair."""
    queried, asked = [], []

    def execute(tool, arguments):
        if tool == "MyGene_query_genes":
            queried.append(arguments["query"])
            assert "alias" in arguments["fields"].split(","), "the step must ask for aliases"
            return MYGENE["responses"][arguments["query"]]
        return OTHERS[tool]

    def agent(question):
        asked.append(question)
        return {"target": list(suggestions)} if question["kind"] == "repair" else {}

    runner = SkillRunner(load_graph("drug-target-validation"), execute=execute, ask=agent)
    run_id = runner.start({"target": target})["run_id"]
    out = runner.advance(run_id)
    assert out["step_id"] == "identity"
    return out, queried, [q for q in asked if q["kind"] == "repair"], runner.handover(run_id)


@pytest.mark.parametrize("query,wrong", [("FR-alpha", "FOLR2"), ("FOLR-1", "FOLR3")])
def test_a_first_hit_that_does_not_name_the_query_goes_to_the_repair(query, wrong):
    out, queried, repairs, handed = _identity(query)

    (repair,) = repairs
    assert repair["value"] == query, "the question names what was looked up"
    assert wrong in repair["problem"], repair["problem"]
    assert queried == [query, "FOLR1"], "the retry looks up the suggested symbol"
    assert (out["extracted"]["symbol"], out["extracted"]["ensembl_id"]) == ("FOLR1", "ENSG00000110195")
    assert handed["facts"]["target"] == "FOLR1"


@pytest.mark.parametrize("query", ["FOLR1", "FRalpha", "fralpha"])
def test_a_hit_named_by_its_symbol_or_a_listed_alias_in_any_case_is_resolved(query):
    out, queried, repairs, _ = _identity(query)

    assert repairs == [] and queried == [query]
    assert out["extracted"]["symbol"] == "FOLR1"


def test_a_wrong_hit_the_repair_cannot_fix_is_blocked_not_a_failed_run():
    out, queried, repairs, _ = _identity("FR-alpha", suggestions=("FOLR-1",))

    assert len(repairs) == 1 and queried == ["FR-alpha", "FOLR-1"]
    assert any("could not be resolved" in b["reason"] for b in out["blocked"])
    assert "symbol" not in out["extracted"] and "ensembl_id" not in out["extracted"], (
        "the wrong gene's identifiers are not kept")
    assert {"step": "identity", "fact": "ensembl_id"} in out["unresolved"]
    assert out["next_step"] is not None, "the run goes on"
