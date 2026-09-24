"""clinical-data-integration driven through its repair: the question's isotope notation
finds no label, the agent names the drug as DailyMed files it, and the run goes on.

The two identity lookups are recorded, for the name that misses and the name that hits;
every other tool answers an empty success, and the agent's judgements are empty.
"""
import json
from pathlib import Path

import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner

pytestmark = pytest.mark.unit

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "skill_processes" / "clinical_data_integration"
MISSING = "177Lu-dotatate"
FILED = "lutetium Lu 177 dotatate"
SETID = "72d1a024-00b7-418a-b36e-b2cb48f2ab55"


def _recorded(tool, arguments):
    path = RECORDED / f"{tool}_2026-09-24.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text())[json.dumps(arguments, sort_keys=True)]


def _drive(suggestions):
    calls, asked = [], []

    def execute(tool, arguments):
        calls.append((tool, arguments))
        recorded = _recorded(tool, arguments)
        return recorded if recorded is not None else {"status": "success", "data": {}}

    def agent(question):
        asked.append(question)
        if question["kind"] == "repair":
            return {"drug_name": list(suggestions)}
        return {name: [] for name in question["wants"]}

    runner = SkillRunner(load_graph("clinical-data-integration"), execute=execute, ask=agent)
    run_id = runner.start({"drug_name": MISSING})["run_id"]
    for _ in range(100):
        if runner.advance(run_id)["finished"]:
            break
    else:
        raise AssertionError("the run did not finish")
    return runner.handover(run_id), calls, asked


def test_the_first_lookup_misses_the_repair_names_the_drug_and_the_run_goes_on():
    handed, calls, asked = _drive([FILED])

    (repair,) = [q for q in asked if q["kind"] == "repair"]
    assert (repair["step"], repair["argument"], repair["value"]) == ("identity", "drug_name", MISSING)
    looked_up = [a["drug_name"] for tool, a in calls if tool == "DailyMed_search_spls"]
    assert looked_up == [MISSING, FILED]
    # the label handle comes from the repaired lookup, and the next step uses it
    assert handed["facts"]["setid"] == SETID
    assert handed["facts"]["faers_name"] == "LUTATHERA"
    assert [a["setid"] for tool, a in calls if tool == "DailyMed_parse_adverse_reactions"] == [SETID]
    # later steps are composed with the name that resolved, not the one that missed
    assert [a["drug_name"] for tool, a in calls if tool == "FDA_get_boxed_warning_info_by_drug_name"] == [FILED]
    # the miss the repair started from is kept, and says what repaired it
    first = [f for f in handed["failures"] if f["tool"] == "DailyMed_search_spls"]
    assert first and first[0]["arguments"]["drug_name"] == MISSING and first[0]["repaired_by"] == FILED
    assert "identity" in handed["steps_done"]
    assert not [b for b in handed["blocked"] if b["step"] == "identity"]


def test_a_repair_that_finds_nothing_is_blocked_and_says_so():
    handed, calls, asked = _drive([MISSING])

    assert "setid" not in handed["facts"]
    (blocked,) = [b for b in handed["blocked"] if b["step"] == "identity"]
    assert MISSING in blocked["reason"]
