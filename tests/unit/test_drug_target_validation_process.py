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


def _drive(records, disease="ovarian cancer", first_answers=None):
    calls, asked = [], []
    first_answers = dict(first_answers or {})

    def execute(tool, arguments):
        calls.append((tool, arguments))
        return RECORDED[tool]

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
    # Every row the source served arrives, whatever its width. The count is read from
    # the recording rather than written here, and the recording is kept above any
    # plausible page size so a cap would fail this.
    served = (RECORDED["OpenTargets_get_diseases_phenotypes_by_target_ensembl"]
              ["data"]["target"]["associatedDiseases"]["rows"])
    assert len(served) > 100, "the recording must exceed a plausible cap to catch one"
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
