"""adverse-event-detection with a named reaction: the question's word is read onto the
source's terms in a judged, checked, placed step, and the loop runs over the reading.

The process is driven whole. FAERS answers its recorded term counts for cisplatin; the
agent's judgements are answered by a stub that reads them from the question, as the agent
would.
"""
import json
from pathlib import Path

import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
RECORDED_COUNTS = json.loads((FIXTURES / "openfda" / "faers_count_reactions_2026-09-24.json").read_text())
# The recorded list's top twenty reactions once the process sets its noise terms aside.
TOP_TWENTY = ["NAUSEA", "NEUTROPENIA", "FEBRILE NEUTROPENIA", "VOMITING", "ANAEMIA",
              "THROMBOCYTOPENIA", "DIARRHOEA", "PYREXIA", "MYELOSUPPRESSION", "FATIGUE",
              "DEHYDRATION", "PNEUMONIA", "SEPSIS", "ASTHENIA", "DYSPNOEA", "PANCYTOPENIA",
              "MUCOSAL INFLAMMATION", "ACUTE KIDNEY INJURY", "DECREASED APPETITE",
              "PLATELET COUNT DECREASED"]
PRR = {"ACUTE KIDNEY INJURY": 17.7, "NEPHROPATHY TOXIC": 9.4, "NEUTROPENIA": 2.5}

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "skill_processes" / "adverse_event_detection"


def _recorded(tool, arguments):
    """The response recorded for this exact call, or None when the tool was not recorded."""
    path = RECORDED / f"{tool}_2026-09-24.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text())[json.dumps(arguments, sort_keys=True)]


def _recorded_lookup(term):
    recorded = json.loads((FIXTURES / "ols" / "placing_probe_2026-09-21.json").read_text())
    return recorded.get(term, {})


def _agent(question, comparator="carboplatin"):
    wants, context = question["wants"], question["context"]
    if "comparator" in wants:
        return {"comparator": comparator}
    if "requested_meddra" in wants:
        (word,) = context["requested_aes"]
        listed = [row["term"] for row in context["faers_term_rows"]]
        return {"requested_meddra": [
            {"of": word, "term": t, "reason": "the injury the word names", "concept": ["kidney", "renal"]}
            for t in listed if "KIDNEY" in t or "NEPHRO" in t]}
    return {name: "stub" for name in wants}


def _drive(requested_aes=None, comparators=("carboplatin",)):
    calls, asked = [], []
    comparators = list(comparators)

    def execute(tool, arguments):
        calls.append((tool, arguments))
        recorded = _recorded(tool, arguments)
        if recorded is not None:
            return recorded
        if tool == "OpenTargets_get_drug_chembId_by_generic_name":
            # the shape the tool audit recorded (aspirin -> CHEMBL25 first, then its salts)
            return {"status": "success", "data": {"search": {"hits": [
                {"id": "CHEMBL11359", "name": "CISPLATIN", "description": "Small molecule drug"},
                {"id": "CHEMBL2", "name": "A NEIGHBOUR", "description": "..."}]}}}
        if tool == "FAERS_count_reactions_by_drug_event":
            return RECORDED_COUNTS[arguments["medicinalproduct"]]
        if tool == "FAERS_calculate_disproportionality":
            prr = PRR.get(arguments["adverse_event"], 1.5)
            return {"data": {"metrics": {"PRR": {"value": prr}}}, "source_url": "u"}
        return {"status": "success", "data": {}}

    def agent(question):
        asked.append(question)
        if "comparator" in question["wants"]:
            return _agent(question, comparators.pop(0) if len(comparators) > 1 else comparators[0])
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
    handed, calls, asked = _drive(requested_aes=["nephrotoxicity"])

    looped = [a["adverse_event"] for tool, a in calls if tool == "FAERS_calculate_disproportionality"]
    # The mapped terms lead, one of them from far below the top twenty; the word never
    # reaches FAERS, and the cap trims the frequency tail instead.
    assert looped[:2] == ["ACUTE KIDNEY INJURY", "NEPHROPATHY TOXIC"] and "nephrotoxicity" not in looped
    assert looped[2:] == [t for t in TOP_TWENTY if t != "ACUTE KIDNEY INJURY"][:18]
    assert [(r["of"], r["term"], r["placing"]) for r in handed["facts"]["requested_meddra"]] == [
        ("nephrotoxicity", "ACUTE KIDNEY INJURY", "placed"),
        ("nephrotoxicity", "NEPHROPATHY TOXIC", "unknown")]   # no ontology holds the term
    assert handed["mappings"] == ["requested_meddra"]
    (mapping_question,) = [q for q in asked if "requested_meddra" in q["wants"]]
    assert "reason" in mapping_question["notes"]
    assert len(mapping_question["choices"]["requested_meddra"]) == 100, "the whole recorded list"


def test_without_a_requested_reaction_the_reading_is_skipped_and_the_top_terms_run():
    handed, calls, asked = _drive()

    assert [q for q in asked if "requested_meddra" in q["wants"]] == []
    # requested_aes is never supplied, so the gate was never decided, not closed on evidence.
    assert {"step": "requested_terms", "gate": "requested_aes",
            "decided": False} in handed["steps_skipped"]
    looped = [a["adverse_event"] for tool, a in calls if tool == "FAERS_calculate_disproportionality"]
    assert looped == TOP_TWENTY
    assert "OFF LABEL USE" not in looped and "DEATH" not in looped, "noise set aside before the cap"
    assert "stalled" not in handed and handed["blocked"] == []


def test_the_facts_the_process_feeds_forward_are_the_servers_not_the_agents():
    """A fact said to be "fed back by the agent" is never asked for, so `chembl_id`,
    `top_aes` and the grading are extracted and computed instead."""
    handed, calls, asked = _drive()

    assert [q["wants"] for q in asked] == [["comparator"]], "only the comparator is the agent's"
    assert handed["facts"]["chembl_id"] == "CHEMBL11359"
    assert [a for tool, a in calls if tool == "OpenTargets_get_drug_indications_by_chemblId"] == [
        {"chemblId": "CHEMBL11359"}]
    graded = handed["facts"]["graded_rows"]
    assert [r["term"] for r in graded][:2] == ["ACUTE KIDNEY INJURY", "NEUTROPENIA"]
    assert [r["term"] for r in graded if r["flagged"]] == ["ACUTE KIDNEY INJURY"]
    assert len(graded) == len(TOP_TWENTY)
    assert handed["facts"]["strong_aes"] == ["ACUTE KIDNEY INJURY"] and handed["facts"]["strong_signal"] is True
    assert [a["adverse_event"] for tool, a in calls if tool == "FAERS_stratify_by_demographics"] == [
        "ACUTE KIDNEY INJURY"]


# --- the comparative step: the agent names a member of the drug's own class ----------

def test_the_comparative_step_runs_against_a_class_member_the_agent_chose():
    handed, calls, asked = _drive()

    (question,) = [q for q in asked if q["wants"] == ["comparator"]]
    # the choice is put to the agent with the class the source gives, whole
    assert question["context"]["class_name"] == "Platinum compounds"
    assert "carboplatin" in question["context"]["class_members"]
    assert [a for tool, a in calls if tool == "FAERS_compare_drugs"] == [
        {"drug1": "cisplatin", "drug2": "carboplatin", "adverse_event": "ACUTE KIDNEY INJURY"}]
    assert "comparative" in handed["steps_done"]
    assert "comparative" not in {s["step"] for s in handed["steps_skipped"]}


def test_a_comparator_outside_the_class_is_asked_again_with_the_class():
    handed, calls, asked = _drive(comparators=("aspirin", "oxaliplatin"))

    first, second = [q for q in asked if q["wants"] == ["comparator"]]
    assert "aspirin" in second["problem"] and "class_members" in second["problem"]
    assert [a["drug2"] for tool, a in calls if tool == "FAERS_compare_drugs"] == ["oxaliplatin"]
