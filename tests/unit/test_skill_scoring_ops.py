"""A skill's grading prose becomes the server's arithmetic (rule 6, DSR-789).

drug-target-validation scores a target 0-100 from bands ("more than 100 publications: 10; 50-100:
7 ..."), from closed-list judgements ("mouse knockout viable, no severe phenotype: 10 ... lethal:
0") and from a sum with tiers. The prose body asked the model to apply these; a process declares
them, the server applies them, and a judged option that is not on the list is refused.
"""

import pytest

from tooluniverse.skill_runner import SkillRunner, absorb

pytestmark = pytest.mark.unit


def test_band_turns_a_number_into_points_by_the_first_threshold_it_reaches():
    spec = {"id": "score", "calls": [], "compute": {
        "literature_points": {"op": "band", "from": "literature_total",
                              "bands": [[100, 10], [50, 7], [10, 5], [1, 3], [0, 0]]}}}

    assert absorb(spec, [], {"literature_total": 240})["facts"]["literature_points"] == 10
    assert absorb(spec, [], {"literature_total": 50})["facts"]["literature_points"] == 7
    assert absorb(spec, [], {"literature_total": 0})["facts"]["literature_points"] == 0
    assert "literature_points" in absorb(spec, [], {})["unresolved"], "no number, no points: unresolved"


def test_band_reads_a_float_and_a_path_into_a_fact():
    spec = {"id": "score", "calls": [], "compute": {
        "pathway_points": {"op": "band", "from": "association.score",
                           "bands": [[0.8, 10], [0.5, 7], [0.2, 4], [0, 1]]}}}

    assert absorb(spec, [], {"association": {"score": 0.63}})["facts"]["pathway_points"] == 7


def test_map_turns_a_judged_option_into_points_and_refuses_an_option_off_the_list():
    spec = {"id": "score", "calls": [], "compute": {
        "ko_points": {"op": "map", "from": "ko_phenotype",
                      "table": {"viable_no_phenotype": 10, "viable_mild": 7, "concerning": 3, "lethal": 0,
                                "no_data": 5}}}}

    assert absorb(spec, [], {"ko_phenotype": "viable_mild"})["facts"]["ko_points"] == 7
    out = absorb(spec, [], {"ko_phenotype": "mostly fine"})
    assert "ko_points" not in out["facts"]
    assert any("mostly fine" in b["reason"] and "viable_mild" in b["reason"] for b in out["blocked"])


def test_sum_adds_the_named_points_and_band_gives_the_tier():
    spec = {"id": "score", "calls": [], "compute": {
        "total": {"op": "sum", "of": ["a", "b", "c"]},
        "tier": {"op": "band", "from": "total", "bands": [[80, "Tier 1"], [60, "Tier 2"], [40, "Tier 3"], [0, "Tier 4"]]}}}

    out = absorb(spec, [], {"a": 28, "b": 24, "c": 14})
    assert out["facts"]["total"] == 66 and out["facts"]["tier"] == "Tier 2"
    assert "total" in absorb(spec, [], {"a": 28, "b": 24})["unresolved"], "a missing part is not a zero"


def test_lookup_takes_one_rows_value_from_a_fact_table_by_the_key_another_fact_names():
    """The pair's Open Targets score: the row of `disease_rows` whose id is the mapped disease."""
    rows = [{"disease_id": "MONDO_0013110", "score": 0.95}, {"disease_id": "MONDO_0008170", "score": 0.63}]
    spec = {"id": "score", "calls": [], "compute": {
        "disease_score": {"op": "lookup", "rows": "disease_rows", "key": "disease_id", "equals": "efo_id",
                          "field": "score"}}}

    assert absorb(spec, [], {"disease_rows": rows, "efo_id": "MONDO_0008170"})["facts"]["disease_score"] == 0.63
    missing = absorb(spec, [], {"disease_rows": rows, "efo_id": "MONDO_9999999"})
    assert "disease_score" not in missing["facts"]
    assert any("MONDO_9999999" in b["reason"] for b in missing["blocked"]), "an absent row is said, not zero"
    assert "disease_score" in absorb(spec, [], {"disease_rows": rows})["unresolved"], "no key yet: unresolved"


def test_first_takes_the_one_value_a_mapping_produced_and_sum_caps_an_additive_score():
    """A judged mapping yields `<name>_terms`, a list; the calls that follow need the one id.
    The genetic sub-score adds four parts (6 + 2 + 2 + 2) but the skill caps it at 10."""
    spec = {"id": "s", "calls": [], "compute": {
        "efo_id": {"op": "first", "of": "efo_choice_terms"},
        "genetic_points": {"op": "sum", "of": ["a", "b", "c", "d"], "cap": 10}}}

    out = absorb(spec, [], {"efo_choice_terms": ["MONDO_0008170", "MONDO_0004992"], "a": 6, "b": 2, "c": 2, "d": 2})
    assert out["facts"]["efo_id"] == "MONDO_0008170" and out["facts"]["genetic_points"] == 10
    assert "efo_id" in absorb(spec, [], {"efo_choice_terms": []})["unresolved"], "an empty list yields nothing"


def test_lookup_accepts_a_list_key_and_uses_its_first_value():
    rows = [{"disease_id": "MONDO_0008170", "score": 0.53}]
    spec = {"id": "s", "calls": [], "compute": {
        "disease_score": {"op": "lookup", "rows": "disease_rows", "key": "disease_id",
                          "equals": "efo_choice_terms", "field": "score"}}}

    assert absorb(spec, [], {"disease_rows": rows, "efo_choice_terms": ["MONDO_0008170"]})["facts"]["disease_score"] == 0.53


def test_a_compute_over_the_steps_own_judged_fact_resolves_once_the_judgement_is_in():
    """The judge is asked after the step's calls, and the arithmetic over the option chosen
    belongs to the same step: `ko_class` is judged, `ko_points` is its table applied. A
    mapping's `_terms` list likewise feeds a `first` in the step that judged it."""
    process = {
        "skill": "scored", "inputs": ["target"],
        "steps": [
            {"id": "ko", "calls": [], "judge": ["ko_class"],
             "compute": {"ko_points": {"op": "map", "from": "ko_class", "table": {"lethal": 0, "viable": 10}}},
             "produces": ["ko_class", "ko_points"]},
        ],
    }
    runner = SkillRunner(process, execute=lambda t, a: {}, ask=lambda q: {"ko_class": "viable"})
    run_id = runner.start({"target": "FOLR1"})["run_id"]
    out = runner.advance(run_id)

    assert out["extracted"]["ko_points"] == 10
    assert out["unresolved"] == [] and out["blocked"] == []
    assert runner.handover(run_id)["facts"]["ko_points"] == 10


def test_a_judged_option_the_table_lacks_is_a_named_block_not_a_silent_gap():
    process = {
        "skill": "scored", "inputs": ["target"],
        "steps": [
            {"id": "ko", "calls": [], "judge": ["ko_class"],
             "compute": {"ko_points": {"op": "map", "from": "ko_class", "table": {"lethal": 0, "viable": 10}}},
             "produces": ["ko_class", "ko_points"]},
        ],
    }
    runner = SkillRunner(process, execute=lambda t, a: {}, ask=lambda q: {"ko_class": "mostly fine"})
    run_id = runner.start({"target": "FOLR1"})["run_id"]
    out = runner.advance(run_id)

    assert "ko_points" not in out["extracted"]
    assert any("mostly fine" in b["reason"] for b in out["blocked"])
    assert [u["fact"] for u in out["unresolved"]] == ["ko_points"]


def test_a_process_declares_its_closed_lists_as_constants_the_checks_can_read():
    process = {
        "skill": "scored", "inputs": ["target"],
        "constants": {"ko_options": ["viable_no_phenotype", "viable_mild", "concerning", "lethal", "no_data"]},
        "steps": [
            {"id": "ko", "calls": [], "judge": ["ko_phenotype"], "produces": ["ko_phenotype"],
             "check": {"ko_phenotype": [{"only_in": "ko_options"}]}},
        ],
    }
    answers = iter([{"ko_phenotype": "mostly fine"}, {"ko_phenotype": "viable_mild"}])
    asked = []
    runner = SkillRunner(process, execute=lambda t, a: {},
                         ask=lambda q: asked.append(q) or next(answers))
    run_id = runner.start({"target": "FOLR1"})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass

    assert "mostly fine" in asked[1]["problem"] and "ko_options" in asked[1]["problem"]
    assert runner.handover(run_id)["facts"]["ko_phenotype"] == "viable_mild"
    assert asked[0]["context"]["ko_options"][0] == "viable_no_phenotype", "the list is in the question"
