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

TRIALS = ([{"nct_id": f"NCT{n:04d}", "title": f"Trial {n}", "phase": "PHASE3",
            "status": "COMPLETED"} for n in range(3)]
          + [{"nct_id": "NCT0100", "title": "Phase 3, still running", "phase": "PHASE3",
              "status": "RECRUITING"}]
          + [{"nct_id": f"NCT02{n:02d}", "title": f"Early {n}", "phase": "PHASE2",
              "status": "COMPLETED"} for n in range(5)])
WANTED = [r for r in TRIALS if r["phase"] == "PHASE3" and r["status"] == "COMPLETED"]
WHERE = {"phase": "PHASE3", "status": "COMPLETED"}
RULE = {"selected_from": {"table": "trial_rows", "where": WHERE}}
# Identifiers, not rows: a key cannot be retyped into another row's prose.
KEYED = {"selected_from": {"table": "trial_rows", "key": "nct_id", "where": WHERE}}
INVENTED = {"nct_id": "NCT9999", "title": "Made up", "phase": "PHASE3", "status": "COMPLETED"}


def _check(rule, selected, rows=TRIALS):
    return check_facts({"selected": [rule]}, {"selected": selected}, {},
                       tables=lambda name: {"trial_rows": rows}[name])


def _record(name, rows):
    record = WorkingRecord(tempfile.mkdtemp(prefix="working-records-"), name)
    record.put_table("trial_rows", rows)
    return record


# --- the description tells the reader what values a column takes, and how often -------------

def test_the_description_lists_the_values_and_counts_of_columns_with_few_distinct_values():
    described = _record("run-1", TRIALS).describe("trial_rows")

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
    assert _record("run-2", REGISTRY).describe("trial_rows")["values"]["phase"] == {
        "PHASE3": 3, "PHASE2": 2}

    wanted = REGISTRY[:2]
    assert _check(RULE, wanted, REGISTRY) == []
    (failure,) = _check(RULE, wanted[:1], REGISTRY)
    assert "dropped" in failure["reason"] and "NCT00002" in failure["reason"]


# --- the check, over the whole table ---------------------------------------------------------

def test_a_correct_selection_passes():
    assert _check(RULE, WANTED) == []


@pytest.mark.parametrize("rule,selected,named", [
    (RULE, WANTED + [TRIALS[3]], ["status", "NCT0100"]),       # PHASE3 but RECRUITING
    (RULE, WANTED[1:], ["dropped", "NCT0000"]),
    (RULE, WANTED + [INVENTED], ["not in trial_rows", "NCT9999"]),
    (KEYED, ["NCT0000", "NCT9999"], ["not in trial_rows", "NCT9999"]),
    (KEYED, [r["nct_id"] for r in WANTED] + ["NCT0100"], ["does not meet", "NCT0100"]),
    (KEYED, ["NCT0001", "NCT0002"], ["dropped", "NCT0000"]),
])
def test_a_selection_that_breaks_the_rule_fails_and_names_the_row(rule, selected, named):
    (failure,) = _check(rule, selected)

    assert failure["check"] == "selected_from"
    assert all(part in failure["reason"] for part in named), failure["reason"]


def test_a_selection_answered_as_keys_is_materialised_into_the_tables_own_rows():
    from tooluniverse.skill_runner import materialised

    keys = [r["nct_id"] for r in WANTED]

    assert _check(KEYED, keys) == []
    assert materialised({"selected": [KEYED]}, {"selected": keys}, {},
                        tables=lambda name: {"trial_rows": TRIALS}[name]) == {"selected": WANTED}


# --- in a run: the table is evidence, the agent answers from its code tool, the server checks --

PROCESS = {
    "skill": "selection", "inputs": ["drug_name"],
    "tables": {"trial_rows": "evidence"},
    "steps": [
        {"id": "trials",
         "calls": [{"tool": "search_clinical_trials", "arguments": {"q": "{drug_name}"}}],
         "collect": {"trial_rows": {"path": "data.studies", "flatten": True,
                                    "fields": ["nct_id", "title", "phase", "status"]}}},
        {"id": "select", "requires": ["trials"],
         "delegate": [{"tool": "OpenAI_Code_Interpreter",
                       "arguments": {"task": "keep the rows where phase is PHASE3 and "
                                             "status is COMPLETED",
                                     "table": "trial_rows"}}],
         "produces": ["selected"], "check": {"selected": [RULE]}},
    ],
}


def _drive(answers, process=PROCESS):
    replies, asked = iter(answers), []
    runner = SkillRunner(process, execute=lambda tool, a: {"data": {"studies": TRIALS}},
                         ask=lambda q: asked.append(q) or {"selected": next(replies)},
                         records=tempfile.mkdtemp(prefix="working-records-"))
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass
    return runner.handover(run_id), asked


def test_in_a_run_the_keys_the_agent_answers_become_the_tables_rows_in_the_facts():
    keyed = {**PROCESS, "steps": [PROCESS["steps"][0],
                                  {**PROCESS["steps"][1], "check": {"selected": [KEYED]}}]}

    handed, _ = _drive([[r["nct_id"] for r in WANTED]], keyed)

    assert handed["facts"]["selected"] == WANTED


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
