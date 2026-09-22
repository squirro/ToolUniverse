"""One drug name, two defensible populations, and only one of them was reported.

`_resolve_drug_field` stops at the FIRST field that knows the drug, so every count
describes that field alone -- the NARROW population. The UNION of all spellings is a
different, equally defensible cohort, and the two do not always agree: measured on
openFDA (DSR-628), LUTATHERA/myelodysplastic syndrome is 29 cases ROR 7.2 narrow and
50 cases ROR 12.0 union, while renal impairment is 2.22 either way. So the narrow
definition stays PRIMARY and the union rides along as a sensitivity analysis.
"""

import pytest

from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

GENERIC = "patient.drug.openfda.generic_name"
BRAND = "patient.drug.openfda.brand_name"
PRODUCT = "patient.drug.medicinalproduct.exact"

pytestmark = pytest.mark.unit

LUTATHERA_OPENFDA = {
    "brand_name": ["LUTATHERA"],
    "generic_name": ["LUTETIUM LU 177 DOTATATE"],
    "substance_name": ["LUTETIUM OXODOTREOTIDE LU-177"],
}


# --- the two populations ---

def test_the_narrow_population_is_one_field_and_the_union_ors_them_all():
    """The matched TERM travels with its field -- .exact needs the uppercase form."""
    queries = FAERSAnalyticsTool.population_queries(
        [(BRAND, "Lutathera"), (PRODUCT, "LUTATHERA")]
    )

    assert queries["narrow"] == f'{BRAND}:"Lutathera"'
    assert queries["union"] == f'{BRAND}:"Lutathera"+OR+{PRODUCT}:"LUTATHERA"'


def test_one_matching_field_means_the_two_populations_are_identical():
    """No second spelling, so there is nothing to compare -- do not imply there is."""
    queries = FAERSAnalyticsTool.population_queries([(GENERIC, "Aspirin")])

    assert queries["narrow"] == queries["union"]


# --- which spellings are probed ---
# `.exact` is case-STRICT and FAERS stores product names uppercase. Measured live
# 2026-08-04: medicinalproduct.exact:"Lutathera" -> 404, "LUTATHERA" -> 5,682 reports,
# openfda.brand_name:"Lutathera" -> 5,683 (case-insensitive). Passing the caller's
# casing to every field made the union miss the second population entirely.

@pytest.mark.parametrize("field,term,expected", [
    (PRODUCT, "Lutathera", ["Lutathera", "LUTATHERA"]),
    (BRAND, "Lutathera", ["Lutathera"]),         # case-insensitive: a second probe is waste
    (PRODUCT, "LUTATHERA", ["LUTATHERA"]),       # already uppercase
])
def test_candidate_terms_probe_each_field_the_way_it_matches(field, term, expected):
    assert FAERSAnalyticsTool.candidate_terms(field, term) == expected


# --- synonyms come from openFDA itself, not from co-occurrence ---
# Counting names across a whole REPORT conflates synonyms with co-medications.
# The openfda block on the matched DRUG ENTRY is the NDC-derived name set for that one
# product, so a co-medication cannot appear in it at all.

@pytest.mark.parametrize("block,expected", [
    (LUTATHERA_OPENFDA,
     ["LUTATHERA", "LUTETIUM LU 177 DOTATATE", "LUTETIUM OXODOTREOTIDE LU-177"]),
    ({}, []),           # many FAERS entries carry no openfda block; not an error
    (None, []),
    ({"brand_name": ["Lutathera", "LUTATHERA"], "generic_name": ["lutathera"]},
     ["LUTATHERA"]),    # deduplicated case-insensitively
])
def test_synonyms_are_read_from_the_drug_entrys_own_name_set(block, expected):
    assert FAERSAnalyticsTool.synonyms_from_openfda(block) == expected


def test_expansion_anchors_on_the_query_term_and_adds_the_other_spellings():
    """The caller's own term stays FIRST -- it defines the narrow/primary cohort -- and
    "LUTATHERA" from the openfda block is not repeated as a second casing of it."""
    assert FAERSAnalyticsTool.expand_terms("Lutathera", LUTATHERA_OPENFDA) == [
        "Lutathera", "LUTETIUM LU 177 DOTATATE", "LUTETIUM OXODOTREOTIDE LU-177",
    ]


def test_no_openfda_block_means_no_expansion():
    assert FAERSAnalyticsTool.expand_terms("Aspirin", None) == ["Aspirin"]


# --- when the divergence is worth telling the reader about ---

@pytest.mark.parametrize("narrow,union,must_contain", [
    # LUTATHERA/MDS: 7.2 vs 12.0 is the case a reader must not miss
    ({"ROR": 7.2, "cases": 29}, {"ROR": 12.0, "cases": 50}, ["7.2", "12.0"]),
    # measured live: the ROR ratio is 1.44, under a 1.5 gate, yet the union holds 48%
    # more cases -- case count is the more interpretable driver
    ({"ROR": 7.564, "cases": 31}, {"ROR": 10.866, "cases": 46}, ["46", "31"]),
])
def test_a_material_divergence_is_called_out(narrow, union, must_contain):
    note = FAERSAnalyticsTool.divergence_note(narrow, union)

    assert note is not None
    for text in must_contain:
        assert text in note, note


def test_crossing_the_no_signal_line_is_always_material():
    """A signal that appears under one population and vanishes under the other."""
    note = FAERSAnalyticsTool.divergence_note(
        {"ROR": 1.4, "cases": 12}, {"ROR": 0.9, "cases": 15}
    )

    assert note is not None
    assert "1.0" in note or "direction" in note.lower()


def test_a_stable_signal_is_not_flagged():
    """Renal impairment is 2.22 either way -- flagging it would be noise."""
    assert FAERSAnalyticsTool.divergence_note(
        {"ROR": 2.22, "cases": 40}, {"ROR": 2.22, "cases": 44}
    ) is None
