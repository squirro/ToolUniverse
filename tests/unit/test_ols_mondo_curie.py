"""The OLS EFO tools accept MONDO ids, because EFO imports MONDO.

`_obo_id_to_efo_iri` converted only the `EFO:` prefix and returned everything
else unchanged, so `MONDO:0005015` was double-URL-encoded as a literal CURIE and
never resolved to a term. The tools looked EFO-only; they are not.

EFO imports MONDO's disease hierarchy, and OLS4 serves those classes under the
`efo` ontology — with MORE children than MONDO alone, since EFO adds its own
subclasses. Measured 2026-08-03 against ols4/api/ontologies/{onto}/terms/{iri}:

    efo   + MONDO_0005015 (diabetes mellitus) -> 11 children
    mondo + MONDO_0005015                     ->  8 children
    efo   + MONDO_0005011 (Crohn disease)     ->  5 children
    efo   + MONDO_0004992 (cancer)            -> 34 children

This also retires the audit's stale example: `EFO:0000400`'s own label in OLS is
`obsolete_diabetes mellitus`, and an obsolete term legitimately has no children,
which is why `ols_get_efo_term_children` measured as a silent zero-row while
working correctly.

The prefix rule is not symmetric, and that is the point: EFO's own terms live at
`http://www.ebi.ac.uk/efo/EFO_x`, while everything it imports uses the OBO PURL
`http://purl.obolibrary.org/obo/{PREFIX}_{local}` -- the same convention the
sibling `ols_tool._expand_short_term_id` already follows.
"""

import pytest

from tooluniverse.efo_tool import OLSRESTTool


@pytest.mark.unit
@pytest.mark.parametrize(
    "curie,expected",
    [
        # EFO's own namespace is NOT an OBO PURL.
        ("EFO:0000400", "http://www.ebi.ac.uk/efo/EFO_0000400"),
        ("efo:0000400", "http://www.ebi.ac.uk/efo/EFO_0000400"),
        # Everything EFO imports resolves through the OBO PURL.
        ("MONDO:0005015", "http://purl.obolibrary.org/obo/MONDO_0005015"),
        ("HP:0001903", "http://purl.obolibrary.org/obo/HP_0001903"),
        ("GO:0006338", "http://purl.obolibrary.org/obo/GO_0006338"),
        ("CHEBI:15377", "http://purl.obolibrary.org/obo/CHEBI_15377"),
    ],
)
def test_a_curie_becomes_the_right_iri_for_its_namespace(curie, expected):
    assert OLSRESTTool._obo_id_to_efo_iri(curie) == expected


@pytest.mark.unit
def test_a_full_iri_is_left_alone():
    """Callers that already resolved the term must not have it mangled."""
    iri = "http://purl.obolibrary.org/obo/MONDO_0005011"

    assert OLSRESTTool._obo_id_to_efo_iri(iri) == iri


@pytest.mark.unit
def test_something_that_is_not_a_curie_is_left_alone():
    assert OLSRESTTool._obo_id_to_efo_iri("diabetes mellitus") == "diabetes mellitus"


@pytest.mark.network
def test_the_efo_children_route_answers_for_a_mondo_id():
    """The claim the unit tests cannot make: EFO serves MONDO's hierarchy."""
    cfg = {
        "name": "ols_get_efo_term_children",
        "parameter": {"properties": {}},
        "fields": {"kind": "children", "ontology_id": "efo"},
    }

    result = OLSRESTTool(cfg).run({"obo_id": "MONDO:0005015", "size": 5})

    assert result["status"] == "success", result
    children = result["data"]["children"]
    assert children, f"expected children of diabetes mellitus, got {result['data']}"
    labels = " ".join(str(c.get("label", "")) for c in children).lower()
    assert "diabetes" in labels, labels


@pytest.mark.network
def test_the_obsolete_efo_example_really_does_have_no_children():
    """Pins WHY the example was replaced, so nobody restores it as a 'fix'."""
    cfg = {
        "name": "ols_get_efo_term",
        "parameter": {"properties": {}},
        "fields": {"kind": "term", "ontology_id": "efo"},
    }

    result = OLSRESTTool(cfg).run({"obo_id": "EFO:0000400"})

    assert result["status"] == "success", result
    assert "obsolete" in str(result["data"]).lower(), result["data"]
