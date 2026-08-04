"""One drug name, two defensible populations, and only one of them was reported.

`_resolve_drug_field` walks a field chain and stops at the FIRST field that knows
the drug. Every count then describes that field alone -- the NARROW population.
The UNION of all spellings is a different, equally defensible cohort, and the two
do not always agree.

Measured on openFDA (DSR-628), LUTATHERA:

    myelodysplastic syndrome   narrow 29 cases, ROR  7.2
                               union  50 cases, ROR 12.0
    renal impairment           narrow/union both        ROR 2.22

So the sensitivity is signal-specific: it cannot be assumed away, and picking one
population silently means a reader comparing our ROR against a published one has
no way to know which cohort either number describes.

Rather than choose, report both: the narrow definition stays PRIMARY so published
numbers do not move underneath anyone, and the union rides along as a sensitivity
analysis -- which is what a pharmacovigilance reader would run by hand anyway.
The cost is two extra count calls, not four: only the drug-side counts change,
and c and d derive from them.
"""

import pytest

from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

GENERIC = "patient.drug.openfda.generic_name"
BRAND = "patient.drug.openfda.brand_name"
PRODUCT = "patient.drug.medicinalproduct.exact"


@pytest.mark.unit
def test_the_narrow_population_is_a_single_field():
    queries = FAERSAnalyticsTool.population_queries(
        [(BRAND, "Lutathera"), (PRODUCT, "LUTATHERA")]
    )

    assert queries["narrow"] == f'{BRAND}:"Lutathera"'


@pytest.mark.unit
def test_the_union_population_ors_every_field_that_knew_the_drug():
    """The matched TERM travels with its field -- .exact needs the uppercase form."""
    queries = FAERSAnalyticsTool.population_queries(
        [(BRAND, "Lutathera"), (PRODUCT, "LUTATHERA")]
    )

    assert queries["union"] == f'{BRAND}:"Lutathera"+OR+{PRODUCT}:"LUTATHERA"'


@pytest.mark.unit
def test_one_matching_field_means_the_two_populations_are_identical():
    """No second spelling, so there is nothing to compare -- do not imply there is."""
    queries = FAERSAnalyticsTool.population_queries([(GENERIC, "Aspirin")])

    assert queries["narrow"] == queries["union"]


@pytest.mark.unit
def test_an_exact_field_is_also_probed_uppercased():
    """`.exact` is case-STRICT and FAERS stores product names uppercase.

    Measured live 2026-08-04:
        medicinalproduct.exact:"Lutathera" -> HTTP 404
        medicinalproduct.exact:"LUTATHERA" -> 5,682 reports
        openfda.brand_name:"Lutathera"     -> 5,683 (case-insensitive)

    Passing the caller's casing to every field made the union miss the second
    population entirely and report "no sensitivity to report" -- a confident
    wrong answer, which is worse than the ambiguity it was meant to remove.
    """
    assert FAERSAnalyticsTool.candidate_terms(PRODUCT, "Lutathera") == [
        "Lutathera", "LUTATHERA",
    ]


@pytest.mark.unit
def test_a_case_insensitive_field_is_probed_once():
    """brand_name matches either casing, so a second probe would just cost a call."""
    assert FAERSAnalyticsTool.candidate_terms(BRAND, "Lutathera") == ["Lutathera"]


@pytest.mark.unit
def test_an_already_uppercase_term_is_not_probed_twice():
    assert FAERSAnalyticsTool.candidate_terms(PRODUCT, "LUTATHERA") == ["LUTATHERA"]


# --- synonyms come from openFDA itself, not from co-occurrence ---
# Counting names across a whole REPORT conflates synonyms with co-medications:
# LUTATHERA's reports name LUTETIUM LU 177 DOTATATE 5,683 times (the same product)
# and OCTREOTIDE 314 times (a different drug the patient also took). Telling those
# apart by a co-occurrence threshold is a clinical judgement call.
#
# The openfda block on the matched DRUG ENTRY sidesteps it: it is the NDC-derived
# name set for that one product, so a co-medication cannot appear in it at all.

LUTATHERA_OPENFDA = {
    "brand_name": ["LUTATHERA"],
    "generic_name": ["LUTETIUM LU 177 DOTATATE"],
    "substance_name": ["LUTETIUM OXODOTREOTIDE LU-177"],
}


@pytest.mark.unit
def test_synonyms_are_read_from_the_drug_entrys_own_name_set():
    names = FAERSAnalyticsTool.synonyms_from_openfda(LUTATHERA_OPENFDA)

    assert names == [
        "LUTATHERA", "LUTETIUM LU 177 DOTATATE", "LUTETIUM OXODOTREOTIDE LU-177",
    ]


@pytest.mark.unit
def test_a_missing_openfda_block_yields_no_synonyms():
    """Many FAERS entries carry no openfda block at all -- that is not an error."""
    assert FAERSAnalyticsTool.synonyms_from_openfda({}) == []
    assert FAERSAnalyticsTool.synonyms_from_openfda(None) == []


@pytest.mark.unit
def test_synonyms_are_deduplicated_case_insensitively():
    names = FAERSAnalyticsTool.synonyms_from_openfda(
        {"brand_name": ["Lutathera", "LUTATHERA"], "generic_name": ["lutathera"]}
    )

    assert names == ["LUTATHERA"]


@pytest.mark.unit
def test_a_material_divergence_is_called_out():
    """LUTATHERA/MDS: 7.2 vs 12.0 is the case a reader must not miss."""
    note = FAERSAnalyticsTool.divergence_note(
        {"ROR": 7.2, "cases": 29}, {"ROR": 12.0, "cases": 50}
    )

    assert note is not None
    assert "7.2" in note and "12.0" in note


@pytest.mark.unit
def test_a_stable_signal_is_not_flagged():
    """Renal impairment is 2.22 either way -- flagging it would be noise."""
    assert FAERSAnalyticsTool.divergence_note(
        {"ROR": 2.22, "cases": 40}, {"ROR": 2.22, "cases": 44}
    ) is None


@pytest.mark.unit
def test_crossing_the_no_signal_line_is_always_material():
    """A signal that appears under one population and vanishes under the other."""
    note = FAERSAnalyticsTool.divergence_note(
        {"ROR": 1.4, "cases": 12}, {"ROR": 0.9, "cases": 15}
    )

    assert note is not None
    assert "1.0" in note or "direction" in note.lower()
