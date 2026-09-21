"""adverse-event-detection with a named reaction: the question's word is read onto the
source's terms in a judged, checked, placed step, and the loop runs over the reading.

The process is driven whole, with stubs in the recorded shapes; the agent's judgements
are answered by a stub that reads them from the question, as the agent would.
"""
import json
from pathlib import Path

import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner

pytestmark = pytest.mark.unit

TERMS = ["NAUSEA", "DEAFNESS", "FALL"]


def _recorded_lookup(term):
    recorded = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ols"
                           / "placing_probe_2026-09-21.json").read_text())
    return recorded.get(term, {})


def _agent(question):
    wants, context = question["wants"], question["context"]
    if "requested_meddra" in wants:
        (word,) = context["requested_aes"]
        listed = [row["term"] for row in context["faers_term_rows"]]
        return {"requested_meddra": [
            {"of": word, "term": t, "reason": "the injury the word names", "concept": ["ear", "hearing"]}
            for t in listed if "DEAF" in t]}
    return {name: "stub" for name in wants}


def _drive(requested_aes=None):
    calls, asked = [], []

    def execute(tool, arguments):
        calls.append((tool, arguments))
        if tool == "OpenTargets_get_drug_chembId_by_generic_name":
            # the shape the tool audit recorded (aspirin -> CHEMBL25 first, then its salts)
            return {"status": "success", "data": {"search": {"hits": [
                {"id": "CHEMBL11359", "name": "CISPLATIN", "description": "Small molecule drug"},
                {"id": "CHEMBL2", "name": "A NEIGHBOUR", "description": "..."}]}}}
        if tool == "FAERS_count_reactions_by_drug_event":
            return {"result": [{"term": t, "count": 10} for t in TERMS]}
        if tool == "FAERS_calculate_disproportionality":
            prr = {"NAUSEA": 1.5, "DEAFNESS": 17.7, "FALL": 2.5}[arguments["adverse_event"]]
            return {"data": {"metrics": {"PRR": {"value": prr}}}, "source_url": "u"}
        return {"status": "success", "data": {}}

    def agent(question):
        asked.append(question)
        return _agent(question)

    runner = SkillRunner(load_graph("adverse-event-detection"), execute=execute, ask=agent,
                         lookup=_recorded_lookup)
    inputs = {"drug_name": "cisplatin", **({"requested_aes": requested_aes} if requested_aes else {})}
    run_id = runner.start(inputs)["run_id"]
    for _ in range(100):
        if runner.advance(run_id)["finished"]:
            break
    else:
        raise AssertionError("the run did not finish")
    return runner.handover(run_id), calls, asked


def test_a_requested_reaction_is_read_onto_faers_terms_and_leads_the_loop():
    handed, calls, asked = _drive(requested_aes=["ototoxicity"])

    looped = [a["adverse_event"] for tool, a in calls if tool == "FAERS_calculate_disproportionality"]
    assert looped[0] == "DEAFNESS" and "ototoxicity" not in looped
    (row,) = handed["facts"]["requested_meddra"]
    assert (row["of"], row["term"], row["placing"]) == ("ototoxicity", "DEAFNESS", "placed")
    assert handed["mappings"] == ["requested_meddra"]
    (mapping_question,) = [q for q in asked if "requested_meddra" in q["wants"]]
    assert "reason" in mapping_question["notes"]


def test_without_a_requested_reaction_the_reading_is_skipped_and_the_top_terms_run():
    handed, calls, asked = _drive()

    assert [q for q in asked if "requested_meddra" in q["wants"]] == []
    assert {"step": "requested_terms", "gate": "requested_aes"} in handed["steps_skipped"]
    looped = [a["adverse_event"] for tool, a in calls if tool == "FAERS_calculate_disproportionality"]
    assert looped == TERMS
    assert "stalled" not in handed and handed["blocked"] == []


def test_the_facts_the_process_feeds_forward_are_the_servers_not_the_agents():
    """As shipped, `chembl_id`, `top_aes` and the grading were "fed back by the agent" — and
    never asked for, so the run had none of them. They are extracted and computed now."""
    handed, calls, asked = _drive()

    assert asked == []
    assert handed["facts"]["chembl_id"] == "CHEMBL11359"
    assert [a for tool, a in calls if tool == "OpenTargets_get_drug_indications_by_chemblId"] == [
        {"chemblId": "CHEMBL11359"}]
    assert [(r["term"], r["flagged"]) for r in handed["facts"]["graded_rows"]] == [
        ("DEAFNESS", True), ("FALL", False), ("NAUSEA", False)]
    assert handed["facts"]["strong_aes"] == ["DEAFNESS"] and handed["facts"]["strong_signal"] is True
    assert [a["adverse_event"] for tool, a in calls if tool == "FAERS_stratify_by_demographics"] == ["DEAFNESS"]
