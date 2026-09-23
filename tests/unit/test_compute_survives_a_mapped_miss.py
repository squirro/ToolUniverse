"""A mapped path keeps its misses in place, and four compute rules read them as records.

`_dig` leaves one entry per record for a mapped path, `None` where a record lacked the
field, so that two paths over the same records stay index-aligned. A rule that walks such a
list with `row.get(...)` raises `AttributeError: 'NoneType' object has no attribute 'get'`.

`_rows_of` exists for this and says so in its own docstring. Three rules were converted to
it and four were not — `_rank_differential`, `_hierarchy`, `_overlap`, `_fewest` — and all
four are used by `rare-disease-diagnosis.yaml`, the one shipped process carrying mapped
paths: `data.items[].id`, `phenotypes[].hpo_id`, `prevalences[].class`, `data.genes[].Symbol`.
One source record without the field is enough.

`_computed` catches only `SkillPathError`, so the crash kills the run; on the durable driver
the activity retries three times and fails the workflow. A failure is meant to be visible,
not fatal and not silent, and an `AttributeError` is none of those to a researcher.

The last test is the one that matters. This file exists because a guard was added and four
call sites were never converted, and nothing detected that. The sweep drives **every** op in
`_COMPUTE_OPS` over a poisoned list, and a new op is a failure until it is covered — so the
next rule cannot repeat this quietly.
"""

import pytest

from tooluniverse import skill_runner as sr

pytestmark = pytest.mark.unit


def _disease(code="ORPHA:1", ids=("HP:0001", "HP:0002")):
    return {"orpha_code": code, "preferred_term": "A disease", "hpo_ids": list(ids)}


# --- one per unconverted rule -----------------------------------------------------------

def test_rank_differential_survives_a_miss_in_every_list_it_reads():
    rule = {"op": "rank_differential", "overlap": "overlap_rows",
            "inheritance": "disease_inheritance", "epidemiology": "disease_prevalence",
            "patient_age_years": "age_years", "early_onset": ["Childhood"],
            "late_onset": ["Adult"], "must_carry": "discriminating_hpo_ids",
            "rows_ids": "disease_phenotypes", "hierarchy": "hpo_hierarchy"}
    facts = {
        "overlap_rows": [None, {"orpha_code": "ORPHA:1", "preferred_term": "A disease",
                                "overlap_pct": 50}],
        "disease_inheritance": [None, {"orpha_code": "ORPHA:1",
                                       "average_age_of_onset": ["Childhood"]}],
        "disease_prevalence": [None, {"orpha_code": "ORPHA:1", "classes": ["1-9 / 100 000"]}],
        "age_years": 7,
        "discriminating_hpo_ids": ["HP:0001"],
        "disease_phenotypes": [None, _disease()],
        "hpo_hierarchy": [None, {"hpo_id": "HP:0001", "parents": [], "children": []}],
    }

    ranked = sr._rank_differential(rule, facts)

    assert [r["orpha_code"] for r in ranked] == ["ORPHA:1"]
    assert ranked[0]["rank"] == 1


def test_hierarchy_survives_a_miss_in_the_rows_it_indexes():
    rule = {"hierarchy": "hpo_hierarchy"}
    facts = {"hpo_hierarchy": [None, {"hpo_id": "HP:0001", "parents": ["HP:0000"]}]}

    index = sr._hierarchy(rule, facts)

    assert list(index) == ["HP:0001"]


def test_overlap_survives_a_miss_in_its_rows_and_in_its_gene_rows():
    rule = {"op": "overlap", "rows": "disease_phenotypes", "row_ids": "hpo_ids",
            "against": "hpo_ids", "gene_rows": "orphanet_gene_rows",
            "hierarchy": "hpo_hierarchy",
            "grades": [{"grade": "T1", "min_pct": 80, "needs_gene": True},
                       {"grade": "T4", "min_pct": 0}]}
    facts = {"disease_phenotypes": [None, _disease()],
             "hpo_ids": ["HP:0001", "HP:0002"],
             "orphanet_gene_rows": [None, {"orpha_code": "ORPHA:1", "genes": ["GENE1"]}],
             "hpo_hierarchy": [None, {"hpo_id": "HP:0001"}]}

    rows = sr._overlap(rule, facts)

    assert [r["orpha_code"] for r in rows] == ["ORPHA:1"]
    assert rows[0]["overlap_pct"] == 100
    assert rows[0]["grade"] == "T1", "the gene row survived the miss beside it"


def test_fewest_survives_a_miss_among_the_rows_it_counts():
    rule = {"op": "fewest", "rows": "term_counts", "id": "hpo_id", "count": "diseases",
            "take": 2}
    facts = {"term_counts": [None,
                             {"hpo_id": "HP:0001", "diseases": ["a"]},
                             {"hpo_id": "HP:0002", "diseases": ["a", "b"]},
                             {"hpo_id": "HP:0003", "diseases": ["a", "b", "c"]}]}

    assert sr._fewest(rule, facts) == ["HP:0001", "HP:0002"]


# --- the sweep: no op may read a mapped miss as a record ---------------------------------
#
# One case per op in `_COMPUTE_OPS`. Every list a case hands over leads with a bare `None`,
# which is what a mapped path leaves where a record had no value.

POISON = [None]


def _case(rule, facts):
    return rule, facts


MISS_CASES = {
    "rank_differential": _case(
        {"op": "rank_differential", "overlap": "rows", "inheritance": "inh",
         "epidemiology": "epi", "must_carry": "must", "rows_ids": "ids",
         "hierarchy": "hier"},
        {"rows": POISON + [{"orpha_code": "ORPHA:1", "overlap_pct": 10}],
         "inh": POISON, "epi": POISON, "must": ["HP:0001"], "ids": POISON,
         "hier": POISON}),
    "overlap": _case(
        {"op": "overlap", "rows": "rows", "row_ids": "hpo_ids", "against": "case",
         "gene_rows": "genes", "hierarchy": "hier", "grades": [{"grade": "T4", "min_pct": 0}]},
        {"rows": POISON + [_disease()], "case": ["HP:0001"], "genes": POISON,
         "hier": POISON}),
    "fewest": _case(
        {"op": "fewest", "rows": "rows", "id": "hpo_id", "count": "diseases", "take": 1},
        {"rows": POISON + [{"hpo_id": "HP:0001", "diseases": ["a"]}]}),
    "hierarchy": _case(
        {"op": "hierarchy", "rows": "rows"},
        {"rows": POISON + [{"hpo_id": "HP:0001", "direction": "parents", "ids": ["HP:0000"]}]}),
    "flag": _case(
        {"op": "flag", "rows": "rows", "field": "score", "threshold": 1},
        {"rows": POISON + [{"score": 2}]}),
    "pluck": _case(
        {"op": "pluck", "rows": "rows", "field": "hpo_id"},
        {"rows": POISON + [{"hpo_id": "HP:0001"}]}),
    # These four read a single value rather than a rows fact, so the poison they can meet
    # is a miss in the value itself, not a None among records.
    "band": _case(
        {"op": "band", "from": "value", "bands": [[0, 1]]},
        {"value": None}),
    "map": _case(
        {"op": "map", "from": "value", "table": {"a": 1}},
        {"value": None}),
    "sum": _case(
        {"op": "sum", "of": ["a", "b"]},
        {"a": 1, "b": None}),
    "first": _case(
        {"op": "first", "of": "a"},
        {"a": POISON}),
    "lookup": _case(
        {"op": "lookup", "rows": "rows", "equals": "wanted", "key": "hpo_id",
         "field": "label"},
        {"rows": POISON + [{"hpo_id": "HP:0001", "label": "a term"}],
         "wanted": "HP:0001"}),
}


def test_every_compute_op_is_driven_over_a_mapped_miss():
    """A new op is a failure here until its own case is written.

    This is the criterion the ticket rests on: the guard existed and four call sites were
    never converted because nothing asked. Now something asks, of every op.
    """
    assert set(MISS_CASES) == set(sr._COMPUTE_OPS), {
        "ops with no case": sorted(set(sr._COMPUTE_OPS) - set(MISS_CASES)),
        "cases for no op": sorted(set(MISS_CASES) - set(sr._COMPUTE_OPS)),
    }


@pytest.mark.parametrize("op", sorted(MISS_CASES))
def test_no_compute_op_reads_a_mapped_miss_as_a_record(op):
    rule, facts = MISS_CASES[op]

    sr._compute(rule, facts)     # a stated outcome or None; never an AttributeError
