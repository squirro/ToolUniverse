"""drug-target-validation as a Skill Process: the skill's grading tables are the server's
arithmetic, its judgements are options out of closed lists, and the question's disease is
read onto the source's ids in a judged, checked mapping.

The process is driven whole against recorded responses; the agent's judgements are answered
by a stub that reads them from the question, as the agent would.
"""
import json
from pathlib import Path

import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner

pytestmark = pytest.mark.unit

RECORDED = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "dtv"
                       / "folr1_ovarian_2026-09-22.json").read_text())

# The options a careful reader of the recorded data would choose, and what the skill's
# tables give for them: 5 + 10 + 5, 4 + 7 + 0, 15, 3 + 5.
CHOSEN = {
    "structural_class": "alphafold_confident", "chemical_class": "drug_like_below_100nM",
    "target_class": "validated_druggable_family",
    "expression_class": "low_in_critical_tissues", "ko_class": "viable_mild_phenotype",
    "adverse_class": "boxed_warning_or_withdrawal",
    "clinical_class": "approved_same_disease",
    "functional_class": "biochemical_assay", "model_class": "patient_derived_xenograft",
    "gwas_loci": 0, "rare_variant": "no", "somatic_mutation": "no",
}


def _agent(question, first_answers):
    wants, context = question["wants"], question["context"]
    if "disease_choice" in wants:
        (row,) = [r for r in context["disease_candidates"] if r["name"] == context["disease"]]
        return {"disease_choice": [{"of": context["disease"], "term": row["id"],
                                    "reason": "the candidate whose name is the disease itself",
                                    "concept": ["ovary", "cancer"]}]}
    if "web_queries" in wants:
        return {"web_queries": [f"{s} drug target" for s in context["web_subjects"]]}
    if "web_rows" in wants:
        return {"web_rows": []}
    answer = {}
    for name in wants:
        if name in first_answers:
            answer[name] = first_answers.pop(name)     # a wrong option, once
        elif name in CHOSEN:
            answer[name] = CHOSEN[name]
        else:
            answer[name] = f"reason for {name}"
    return answer


def _drive(records, disease="ovarian cancer", first_answers=None, responses=None):
    calls, asked = [], []
    first_answers = dict(first_answers or {})
    served = {**RECORDED, **(responses or {})}

    def execute(tool, arguments):
        calls.append((tool, arguments))
        return served[tool]

    def agent(question):
        asked.append(question)
        return _agent(question, first_answers)

    runner = SkillRunner(load_graph("drug-target-validation"), execute=execute, ask=agent,
                         records=records)
    inputs = {"target": "FOLR1", **({"disease": disease} if disease else {})}
    run_id = runner.start(inputs)["run_id"]
    for _ in range(200):
        if runner.advance(run_id)["finished"]:
            break
    else:
        raise AssertionError("the run did not finish")
    return runner.handover(run_id), calls, asked


def test_the_score_is_the_servers_arithmetic_over_recorded_data_and_judged_options(tmp_path):
    handed, calls, asked = _drive(tmp_path)
    facts = handed["facts"]

    assert (facts["symbol"], facts["ensembl_id"], facts["uniprot_id"], facts["tdl"]) == (
        "FOLR1", "ENSG00000110195", "P15328", "Tclin")
    assert facts["function"].startswith("Binds to folate")
    # the disease named in the question, read onto the source's id, then looked up in the
    # source's own association table: score 0.534 falls in the 0.5 band
    (row,) = facts["disease_choice"]
    assert (row["of"], row["term"]) == ("ovarian cancer", "MONDO_0008170")
    assert facts["efo_id"] == "MONDO_0008170"
    assert [a for t, a in calls if t == "OpenTargets_get_evidence_by_datasource"][0]["efoId"] == "MONDO_0008170"
    assert round(facts["disease_score"], 3) == 0.534 and facts["pathway_points"] == 7
    assert facts["literature_total"] == 150 and facts["literature_points"] == 10
    assert facts["pli_points"] == 0 and facts["genetic_points"] == 0
    assert facts["disease_association"] == 17
    assert (facts["druggability_total"], facts["safety_total"], facts["clinical_points"],
            facts["validation_total"]) == (20, 11, 15, 8)
    assert facts["total"] == 71 and facts["tier"] == "Tier 2 -- CONDITIONAL GO"


def test_the_wide_tables_are_evidence_and_the_loop_runs_over_the_sources_drug_names(tmp_path):
    handed, calls, asked = _drive(tmp_path)
    facts = handed["facts"]

    described = {t["table"] for t in handed["tables"]}
    for evidence in ("literature_rows", "trial_rows", "gwas_rows"):
        assert evidence not in facts and evidence in described
    # Every row the source served arrives; the width comes from the recording, not from
    # a number written here. A cap is caught by the wide-table test below.
    served = (RECORDED["OpenTargets_get_diseases_phenotypes_by_target_ensembl"]
              ["data"]["target"]["associatedDiseases"]["rows"])
    assert len(facts["disease_rows"]) == len(served), "the whole association list, one page"
    looped = [a["drug_name"] for t, a in calls if t == "FDA_get_boxed_warning_info_by_drug_name"]
    assert looped == [r["name"] for r in facts["drug_rows"]] and looped[0] == "VINTAFOLIDE"
    # the clinical judgement ("approved for THIS disease?") reads the drug's indications
    assert "ovarian cancer" in facts["drug_rows"][0]["indications"]
    assert [r["drug"] for r in facts["boxed_rows"]] == looped
    assert all(r["boxed_warning"].startswith("WARNING") for r in facts["boxed_rows"])
    # ChEMBL timed out when recorded: a recorded failure, not a silent gap, and the
    # drugs from Open Targets still arrive
    assert any(f["tool"] == "ChEMBL_search_targets" for f in handed["failures"])
    assert handed["blocked"] == [] and "stalled" not in handed


def test_an_option_off_the_closed_list_is_refused_and_asked_again_with_the_list(tmp_path):
    handed, calls, asked = _drive(tmp_path, first_answers={"ko_class": "mostly fine"})

    ko_questions = [q for q in asked if "ko_class" in q["wants"]]
    assert len(ko_questions) == 2
    assert "mostly fine" in ko_questions[1]["problem"] and "ko_options" in ko_questions[1]["problem"]
    assert ko_questions[0]["context"]["ko_options"][0] == "viable_no_severe_phenotype"
    assert handed["facts"]["ko_class"] == "viable_mild_phenotype" and handed["facts"]["ko_points"] == 7


def test_without_a_disease_the_disease_bound_steps_are_skipped_and_no_total_is_claimed(tmp_path):
    handed, calls, asked = _drive(tmp_path, disease=None)

    skipped = {s["step"] for s in handed["steps_skipped"]}
    assert {"disease_candidates", "disease_choice", "pair", "literature"} <= skipped
    assert [q for q in asked if "disease_choice" in q["wants"]] == []
    assert "total" not in handed["facts"] and "tier" not in handed["facts"]
    unresolved = {u["fact"] for u in handed["unresolved"]}
    assert {"total", "disease_association"} <= unresolved
    assert handed["facts"]["druggability_total"] == 20, "the dimensions that need no disease are scored"
    assert "stalled" not in handed


# --- a wide table is not capped on its way to the evidence store -----------------
#
# The shape is the recorded one; the width is made here, so the guard costs no fixture
# and can sit above any page size a future change might introduce.

def test_a_wide_association_table_arrives_whole(tmp_path):
    import copy

    wide = copy.deepcopy(RECORDED["OpenTargets_get_diseases_phenotypes_by_target_ensembl"])
    table = wide["data"]["target"]["associatedDiseases"]
    template = table["rows"][0]
    table["rows"] = [
        {**copy.deepcopy(template),
         "disease": {**template["disease"], "id": f"MONDO_{n:07d}", "name": f"disease {n}"}}
        for n in range(300)
    ]
    table["count"] = 300

    handed, _, _ = _drive(
        tmp_path,
        responses={"OpenTargets_get_diseases_phenotypes_by_target_ensembl": wide})

    assert len(handed["facts"]["disease_rows"]) == 300, "a cap trimmed the source's table"


def test_the_trials_search_carries_the_questions_disease_beside_the_target(tmp_path):
    handed, calls, asked = _drive(tmp_path, disease="ovarian cancer")

    (sent,) = [args for tool, args in calls if tool == "search_clinical_trials"]
    assert sent == {"query_term": "FOLR1", "condition": "ovarian cancer", "pageSize": 1000}


def test_without_a_disease_the_trials_search_runs_on_the_target_alone(tmp_path):
    handed, calls, asked = _drive(tmp_path, disease=None)

    (sent,) = [args for tool, args in calls if tool == "search_clinical_trials"]
    assert sent == {"query_term": "FOLR1", "pageSize": 1000}, "no placeholder, no null"


def test_the_known_drugs_are_asked_for_whole_not_as_the_tools_first_page(tmp_path):
    """The drugs tool pages its list; the clinical judgement reads every drug."""
    handed, calls, asked = _drive(tmp_path)

    (sent,) = [args for tool, args in calls
               if tool == "OpenTargets_get_associated_drugs_by_target_ensemblID"]
    assert sent == {"ensemblId": "ENSG00000110195", "page_size": 1000}


def test_a_run_holding_one_page_of_the_drugs_owes_the_sources_total(tmp_path):
    """Served one page of 25 of EGFR's 82, the report must say the source holds 82."""
    from tooluniverse.skill_report_check import check_report

    egfr = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "opentargets"
                       / "egfr_drug_candidates_2026-09-24.json").read_text())
    holder = egfr["data"]["target"]["drugAndClinicalCandidates"]
    one_page = {"status": "success",
                "data": {"target": {**egfr["data"]["target"],
                                    "drugAndClinicalCandidates": {**holder, "rows": holder["rows"][:25]}}},
                "metadata": {"total": 82, "returned": 25, "has_more": True, "next_page": 2}}
    handed, calls, asked = _drive(
        tmp_path, responses={"OpenTargets_get_associated_drugs_by_target_ensemblID": one_page})

    (table,) = [t for t in handed["tables"] if t["table"] == "results.modulators"]
    assert table["source_total"] == 82
    assert len(handed["facts"]["drug_rows"]) == 25
    owed = [f for f in check_report("The target has known drugs.", {"handover": handed})
            if f["kind"] == "narrowing_not_stated"]
    assert any("results.modulators" in f["text"] and "82" in f["text"] for f in owed)
