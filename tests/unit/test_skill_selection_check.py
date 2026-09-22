"""The code tool selects rows; a check verifies the selection (rule 6 of ADR-0018).

"Which completed phase 3 trials examined hearing protection?" -- a ranking by words finds the
subject, but PHASE3 and COMPLETED are values of a closed list, not words to rank by. The fetch
tool gets no filter: the agent selects in its code tool, from rows it fetched, and the server
verifies the answer against the whole table -- every row from the table, every row meeting
the condition, no qualifying row dropped -- and names the row that breaks it.
"""

import tempfile

import pytest

from tooluniverse.skill_runner import SkillRunner, check_facts
from tooluniverse.skill_working_record import WorkingRecord

pytestmark = pytest.mark.unit

TRIALS = ([{"nct_id": f"NCT{n:04d}", "title": f"Trial {n}", "phase": "PHASE3", "status": "COMPLETED"}
           for n in range(3)]
          + [{"nct_id": "NCT0100", "title": "Phase 3, still running", "phase": "PHASE3", "status": "RECRUITING"}]
          + [{"nct_id": f"NCT02{n:02d}", "title": f"Early {n}", "phase": "PHASE2", "status": "COMPLETED"}
             for n in range(5)])
WANTED = [r for r in TRIALS if r["phase"] == "PHASE3" and r["status"] == "COMPLETED"]
RULE = {"selected_from": {"table": "trial_rows", "where": {"phase": "PHASE3", "status": "COMPLETED"}}}


# --- the description tells the reader what values a column takes, and how often -------------

def test_the_description_lists_the_values_and_counts_of_columns_with_few_distinct_values():
    record = WorkingRecord(tempfile.mkdtemp(prefix="working-records-"), "run-1")
    record.put_table("trial_rows", TRIALS)

    described = record.describe("trial_rows")

    assert described["values"] == {"phase": {"PHASE3": 4, "PHASE2": 5},
                                   "status": {"COMPLETED": 8, "RECRUITING": 1}}
    assert "nct_id" not in described["values"] and "title" not in described["values"]


REGISTRY = [                       # the registry's own recorded shape: phase is a LIST
    {"nct_id": "NCT00064077", "phase": ["PHASE3"], "status": "COMPLETED"},
    {"nct_id": "NCT00002", "phase": ["PHASE2", "PHASE3"], "status": "COMPLETED"},
    {"nct_id": "NCT00003", "phase": ["PHASE2"], "status": "COMPLETED"},
    {"nct_id": "NCT00004", "phase": ["PHASE3"], "status": "RECRUITING"},
    {"nct_id": "NCT00005", "phase": [], "status": "COMPLETED"},
]


def test_a_list_valued_column_is_described_by_its_elements_and_selected_by_membership():
    """A list-valued column compared to a bare string refuses every exact row."""
    record = WorkingRecord(tempfile.mkdtemp(prefix="working-records-"), "run-2")
    record.put_table("trial_rows", REGISTRY)

    assert record.describe("trial_rows")["values"]["phase"] == {"PHASE3": 3, "PHASE2": 2}
    wanted = [REGISTRY[0], REGISTRY[1]]
    rule = {"selected_from": {"table": "trial_rows", "where": {"phase": "PHASE3", "status": "COMPLETED"}}}
    assert check_facts({"selected": [rule]}, {"selected": wanted}, {}, tables=lambda n: REGISTRY) == []
    (failure,) = check_facts({"selected": [rule]}, {"selected": wanted[:1]}, {}, tables=lambda n: REGISTRY)
    assert "dropped" in failure["reason"] and "NCT00002" in failure["reason"]


# --- the check, over the whole table ---------------------------------------------------------

def _rows(name):
    return {"trial_rows": TRIALS}[name]


def test_a_correct_selection_passes():
    assert check_facts({"selected": [RULE]}, {"selected": WANTED}, {}, tables=_rows) == []


def test_a_row_that_does_not_meet_the_condition_fails_and_is_named():
    wrong = WANTED + [TRIALS[3]]                       # PHASE3 but RECRUITING

    (failure,) = check_facts({"selected": [RULE]}, {"selected": wrong}, {}, tables=_rows)

    assert failure["check"] == "selected_from"
    assert "status" in failure["reason"] and "NCT0100" in failure["reason"]


def test_a_dropped_row_that_meets_the_condition_fails_and_is_named():
    (failure,) = check_facts({"selected": [RULE]}, {"selected": WANTED[1:]}, {}, tables=_rows)

    assert "dropped" in failure["reason"] and "NCT0000" in failure["reason"]


def test_a_row_that_is_not_in_the_table_fails():
    invented = WANTED + [{"nct_id": "NCT9999", "title": "Made up", "phase": "PHASE3", "status": "COMPLETED"}]

    (failure,) = check_facts({"selected": [RULE]}, {"selected": invented}, {}, tables=_rows)

    assert "not in trial_rows" in failure["reason"] and "NCT9999" in failure["reason"]


# --- identifiers, not rows: the agent names the rows by key, the server takes them from the table ---
#
# A key cannot be retyped into another row's prose, so only the drop remains to check.

KEYED = {"selected_from": {"table": "trial_rows", "key": "nct_id",
                           "where": {"phase": "PHASE3", "status": "COMPLETED"}}}


def test_a_selection_answered_as_keys_is_materialised_into_the_tables_own_rows():
    from tooluniverse.skill_runner import materialised

    keys = [r["nct_id"] for r in WANTED]

    assert check_facts({"selected": [KEYED]}, {"selected": keys}, {}, tables=_rows) == []
    assert materialised({"selected": [KEYED]}, {"selected": keys}, {}, tables=_rows) == {"selected": WANTED}


def test_a_key_that_is_not_in_the_table_fails_and_is_named():
    (failure,) = check_facts({"selected": [KEYED]}, {"selected": ["NCT0000", "NCT9999"]}, {}, tables=_rows)

    assert "NCT9999" in failure["reason"] and "not in trial_rows" in failure["reason"]


def test_a_key_whose_row_does_not_meet_the_condition_fails_and_is_named():
    keys = [r["nct_id"] for r in WANTED] + ["NCT0100"]

    (failure,) = check_facts({"selected": [KEYED]}, {"selected": keys}, {}, tables=_rows)

    assert "NCT0100" in failure["reason"] and "does not meet" in failure["reason"]


def test_a_dropped_key_still_fails():
    (failure,) = check_facts({"selected": [KEYED]}, {"selected": ["NCT0001", "NCT0002"]}, {}, tables=_rows)

    assert "dropped" in failure["reason"] and "NCT0000" in failure["reason"]


def test_in_a_run_the_keys_the_agent_answers_become_the_tables_rows_in_the_facts():
    keyed_process = {**PROCESS, "steps": [PROCESS["steps"][0],
                                          {**PROCESS["steps"][1], "check": {"selected": [KEYED]}}]}
    runner = SkillRunner(keyed_process, execute=lambda tool, a: {"data": {"studies": TRIALS}},
                         ask=lambda q: {"selected": [r["nct_id"] for r in WANTED]},
                         records=tempfile.mkdtemp(prefix="working-records-"))
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass

    assert runner.handover(run_id)["facts"]["selected"] == WANTED


# --- in a run: the table is evidence, the agent answers from its code tool, the server checks --

PROCESS = {
    "skill": "selection", "inputs": ["drug_name"],
    "tables": {"trial_rows": "evidence"},
    "steps": [
        {"id": "trials", "calls": [{"tool": "search_clinical_trials", "arguments": {"q": "{drug_name}"}}],
         "collect": {"trial_rows": {"path": "data.studies", "flatten": True,
                                    "fields": ["nct_id", "title", "phase", "status"]}}},
        {"id": "select", "requires": ["trials"],
         "delegate": [{"tool": "OpenAI_Code_Interpreter",
                       "arguments": {"task": "keep the rows where phase is PHASE3 and status is COMPLETED",
                                     "table": "trial_rows"}}],
         "produces": ["selected"], "check": {"selected": [RULE]}},
    ],
}


def _drive(answers):
    replies = iter(answers)
    asked = []
    runner = SkillRunner(PROCESS, execute=lambda tool, a: {"data": {"studies": TRIALS}},
                         ask=lambda q: asked.append(q) or {"selected": next(replies)},
                         records=tempfile.mkdtemp(prefix="working-records-"))
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass
    return runner.handover(run_id), asked


def test_a_correct_selection_becomes_a_fact_and_the_table_stays_evidence():
    handed, asked = _drive([WANTED])

    assert handed["facts"]["selected"] == WANTED
    assert "trial_rows" not in handed["facts"]
    assert [t["table"] for t in handed["tables"] if t["table"] == "trial_rows"] == ["trial_rows"]
    assert len(asked) == 1 and asked[0]["calls"][0]["arguments"]["table"] == "trial_rows"


def test_a_wrong_selection_is_asked_again_with_the_row_named_then_left_unresolved():
    handed, asked = _drive([WANTED[1:], WANTED[1:]])

    assert "NCT0000" in asked[1]["problem"] and "dropped" in asked[1]["problem"]
    assert "selected" not in handed["facts"]
    assert handed["unresolved"] == [{"step": "select", "fact": "selected"}]
