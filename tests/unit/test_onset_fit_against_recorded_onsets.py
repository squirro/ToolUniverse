"""Onset fit compares the patient's age with the age range of each Orphanet onset class.

The onset classes are the ones Orphanet returned in two recorded live runs of the
rare-disease process. The rule is the shipped process's own compute rule.
"""
import json
from pathlib import Path

import pytest

from tooluniverse import skill_runner as sr
from tooluniverse.skill_graph import load_graph

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "skill_processes"
RECORDINGS = [FIXTURES / "rare_disease" / "Orphanet_get_natural_history_2026-09-24.json",
              FIXTURES / "rare_disease_coarse_facies" / "Orphanet_get_natural_history_2026-09-24.json"]


def _recorded_onsets():
    rows = {}
    for path in RECORDINGS:
        for key, response in json.loads(path.read_text()).items():
            if key != "_note":
                rows[str(json.loads(key)["orphacode"])] = response["data"]
    return rows


ONSETS = _recorded_onsets()
RULE = next(s for s in load_graph("rare-disease-diagnosis")["steps"]
            if s["id"] == "rank_differential")["compute"]["ranked_rows"]


def _fit(age, codes):
    facts = {"age_years": age,
             "overlap_rows": [{"orpha_code": c, "preferred_term": ONSETS[c].get("preferred_term"),
                               "overlap_pct": 50} for c in codes],
             "disease_inheritance": [ONSETS[c] for c in codes]}
    return {r["orpha_code"]: r["onset_fit"] for r in sr._rank_differential(RULE, facts)}


def test_an_adult_fits_adult_onset_and_is_later_than_childhood_onset():
    fit = _fit(60, ["454714", "101110", "351", "93399", "580", "93473"])
    assert fit == {
        "454714": "fits: Adult (19 to 65 years)",         # Plasma cell leukemia, Adult + Elderly
        "101110": "fits: Adult (19 to 65 years)",         # Spinocerebellar ataxia type 20
        "351": "fits: All ages (any age)",                # Galactosialidosis
        "93399": "earlier than patient: Adolescent (12 to 18 years)",
        "580": "earlier than patient: Childhood (2 to 11 years)",
        "93473": "earlier than patient: Infancy (28 days to 23 months)",
    }


def test_an_elderly_patient_matches_the_elderly_class():
    assert _fit(70, ["454714"]) == {"454714": "fits: Elderly (over 65 years)"}


def test_a_child_fits_childhood_onset_and_adult_onset_is_later():
    fit = _fit(4, ["580", "796", "101110", "454714", "93473", "351"])
    assert fit == {
        "580": "fits: Childhood (2 to 11 years)",
        "796": "fits: Childhood (2 to 11 years)",        # Sandhoff: Adolescent, Adult, Childhood, Infancy
        "101110": "later than patient: Adult (19 to 65 years)",
        "454714": "later than patient: Adult (19 to 65 years)",
        "93473": "earlier than patient: Infancy (28 days to 23 months)",
        "351": "fits: All ages (any age)",
    }


def test_an_infant_aged_in_fractions_of_a_year_matches_infancy_or_neonatal():
    assert _fit(0.5, ["93473", "580"]) == {
        "93473": "fits: Infancy (28 days to 23 months)",
        "580": "later than patient: Childhood (2 to 11 years)"}
    assert _fit(0.02, ["93473", "709"]) == {
        "93473": "fits: Neonatal (birth to 4 weeks)",
        "709": "fits: Neonatal (birth to 4 weeks)"}       # Peters plus: Antenatal, Neonatal


def test_a_disease_with_no_onset_data_is_not_assessed():
    assert ONSETS["363294"]["average_age_of_onset"] == []
    assert _fit(4, ["363294"]) == {"363294": "not assessed (no onset data)"}


def test_an_onset_class_the_table_does_not_know_is_not_assessed_never_fits():
    facts = {"age_years": 4,
             "overlap_rows": [{"orpha_code": "1", "overlap_pct": 50}],
             "disease_inheritance": [{"orpha_code": "1", "average_age_of_onset": ["Toddler"]}]}
    [row] = sr._rank_differential(RULE, facts)
    assert row["onset_fit"] == "not assessed (unknown onset class: Toddler)"


def test_a_known_match_wins_over_an_unknown_class_but_an_unknown_blocks_earlier_or_later():
    facts = {"age_years": 60,
             "overlap_rows": [{"orpha_code": "1", "overlap_pct": 50},
                              {"orpha_code": "2", "overlap_pct": 50}],
             "disease_inheritance": [{"orpha_code": "1", "average_age_of_onset": ["Adult", "Toddler"]},
                                     {"orpha_code": "2", "average_age_of_onset": ["Childhood", "Toddler"]}]}
    fit = {r["orpha_code"]: r["onset_fit"] for r in sr._rank_differential(RULE, facts)}
    assert fit == {"1": "fits: Adult (19 to 65 years)",
                   "2": "not assessed (unknown onset class: Toddler)"}


def test_an_age_that_is_not_a_number_of_years_is_not_assessed():
    for age in ("four", True, -1):
        assert set(_fit(age, ["580"]).values()) == {
            f"not assessed (patient age {age!r} is not a number of years)"}
    assert _fit("4", ["580"]) == {"580": "fits: Childhood (2 to 11 years)"}


def test_only_an_onset_still_ahead_of_the_patient_ranks_lower():
    facts = {"age_years": 4,
             "overlap_rows": [{"orpha_code": c, "preferred_term": c, "overlap_pct": 50}
                              for c in ("101110", "93473", "363294", "580")],
             "disease_inheritance": [ONSETS[c] for c in ("101110", "93473", "363294", "580")]}
    ranked = sr._rank_differential(RULE, facts)
    # fits, earlier and not assessed tie on onset, so the name decides; Adult comes last
    assert [r["orpha_code"] for r in ranked] == ["363294", "580", "93473", "101110"]
    assert [r["onset_class"] for r in ranked] == [None, "Childhood", "Infancy", "Adult"]
