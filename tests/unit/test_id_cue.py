"""The description must name the ID namespace the tool actually requires (DSR-662).

155 served tools require an identifier in a specific namespace, say so in the *parameter*
description, and never say it in the *tool* description -- which is the only surface the
model reads at every call. ``HPA_get_cancer_prognostics_by_gene`` advertises "prognostic
value of a gene" while requiring ``ensembl_id``, which is exactly why two skill bodies call
it with a bare gene symbol and get nothing.

Derived at registry load, never authored, so nothing goes stale and tools upstream writes
next year inherit the behaviour. No file under the data directory is touched (ADR-0014).

The namespace is read out of the parameter description's own grammar -- the words before
"ID"/"accession"/"CURIE" -- rather than matched against a list of known databases. A list
would be wrong the moment upstream adds one.
"""

import pytest

from tooluniverse.tools_sr import id_cue

HPA = {
    "name": "HPA_get_cancer_prognostics_by_gene",
    "description": (
        "Retrieve prognostic value of a gene across various cancer types, indicating "
        "if its expression level correlates with patient survival outcomes."
    ),
    "parameter": {
        "properties": {
            "ensembl_id": {
                "description": (
                    "Ensembl Gene ID of the gene to check, e.g., 'ENSG00000141510' "
                    "for TP53, 'ENSG00000012048' for BRCA1."
                )
            }
        },
        "required": ["ensembl_id"],
    },
}


# --- reading the namespace out of the parameter's own words ---


@pytest.mark.parametrize(
    "description,expected",
    [
        ("Ensembl Gene ID of the gene to check, e.g. 'ENSG00000141510'.", "Ensembl"),
        ("UniProt accession for the protein.", "UniProt"),
        ("The ChEMBL ID of the molecule.", "ChEMBL"),
        ("A MONDO CURIE identifying the disease.", "MONDO"),
        ("PubChem CID for the compound.", "PubChem"),
    ],
)
def test_the_namespace_comes_from_the_parameters_own_grammar(description, expected):
    assert expected in id_cue.namespaces(description)


def test_a_parameter_that_pins_no_namespace_yields_nothing():
    assert id_cue.namespaces("The maximum number of rows to return.") == []
    assert id_cue.namespaces("Free-text search query.") == []


def test_a_parameter_naming_two_namespaces_yields_both():
    found = id_cue.namespaces("An Ensembl gene ID or a UniProt accession.")

    assert "Ensembl" in found and "UniProt" in found


def test_an_imperative_sentence_is_not_read_as_a_namespace():
    """BioModels_get_model: 'Find IDs using biomodels_search' is guidance, not a namespace."""
    found = id_cue.namespaces(
        "BioModels identifier (e.g., 'BIOMD0000000469'). Find IDs using biomodels_search."
    )

    assert found == ["BioModels"], found


def test_a_parenthetical_gloss_does_not_displace_the_namespace():
    """disease_target_score: 'The EFO (Experimental Factor Ontology) ID' means EFO."""
    found = id_cue.namespaces(
        "The EFO (Experimental Factor Ontology) ID of the disease, e.g., 'EFO_0000339'"
    )

    assert found == ["EFO"], found


@pytest.mark.parametrize("namespace", ["EFO", "UniProt", "NCBI", "Ensembl", "PDB"])
def test_the_cue_reads_grammatically_whatever_the_namespace_starts_with(namespace):
    """No indefinite article precedes the namespace.

    "a UniProt" and "an NCBI" are both correct by sound and both wrong by first letter,
    and no cheap rule gets every case; the phrasing avoids the question instead.
    """
    tool = {
        "name": "X_get",
        "description": "Get a thing.",
        "parameter": {
            "properties": {"x": {"description": f"The {namespace} ID of the thing."}},
            "required": ["x"],
        },
    }

    cue = id_cue.derive_cue(tool)

    assert f"the {namespace} namespace" in cue, cue
    assert f"a {namespace}" not in cue and f"an {namespace}" not in cue, cue


def test_an_example_accession_is_not_mistaken_for_a_namespace():
    """'P04637' is a value, not a database."""
    assert id_cue.namespaces("Such as the P04637 ID.") == []


# --- the derived cue ---


def test_a_tool_hiding_its_namespace_gains_a_cue_naming_it():
    cue = id_cue.derive_cue(HPA)

    assert cue is not None
    assert "Ensembl" in cue


def test_the_cue_carries_an_example_identifier_when_the_parameter_gives_one():
    """A shape the model can copy beats a namespace it has to guess the format of."""
    assert "ENSG00000141510" in id_cue.derive_cue(HPA)


def test_a_description_that_already_names_the_namespace_gains_nothing():
    already = dict(HPA, description="Prognostics by Ensembl gene ID across cancers.")

    assert id_cue.derive_cue(already) is None


def test_a_tool_with_no_required_parameters_is_unchanged():
    tool = {
        "name": "X_search",
        "description": "Search things.",
        "parameter": {
            "properties": {"query": {"description": "A ChEMBL ID, optionally."}},
            "required": [],
        },
    }

    assert id_cue.derive_cue(tool) is None


def test_only_required_parameters_drive_the_cue():
    """An optional namespaced filter is not what the model gets wrong at call time."""
    tool = {
        "name": "X_get",
        "description": "Get things.",
        "parameter": {
            "properties": {
                "name": {"description": "A plain name."},
                "chembl_id": {"description": "Optional ChEMBL ID filter."},
            },
            "required": ["name"],
        },
    }

    assert id_cue.derive_cue(tool) is None


def test_two_namespaces_produce_one_well_formed_cue():
    tool = {
        "name": "X_map",
        "description": "Map an identifier.",
        "parameter": {
            "properties": {
                "identifier": {"description": "An Ensembl gene ID or UniProt accession."}
            },
            "required": ["identifier"],
        },
    }

    cue = id_cue.derive_cue(tool)

    assert "Ensembl" in cue and "UniProt" in cue
    assert cue.count("Requires") == 1, f"malformed multi-namespace cue: {cue}"


# --- applying it ---


def test_apply_appends_the_cue_to_the_served_description():
    applied = id_cue.apply(HPA)

    assert applied["description"].startswith(HPA["description"])
    assert "Ensembl" in applied["description"]


def test_apply_does_not_mutate_the_definition_it_was_given():
    """The definitions come from files under data/; nothing there may be modified."""
    original = HPA["description"]

    id_cue.apply(HPA)

    assert HPA["description"] == original


def test_apply_is_idempotent():
    once = id_cue.apply(HPA)
    twice = id_cue.apply(once)

    assert once["description"] == twice["description"]


def test_apply_leaves_a_tool_with_nothing_to_add_exactly_as_it_was():
    tool = {"name": "X", "description": "Plain.", "parameter": {"properties": {}}}

    assert id_cue.apply(tool) == tool


# --- it has to actually happen at registry load ---
# A derivation nothing calls changes no description the model ever reads.


class _Registry:
    def __init__(self):
        self.all_tool_dict = {}

    def load_tools(self, *args, **kwargs):
        self.all_tool_dict = {"HPA_get_cancer_prognostics_by_gene": dict(HPA)}
        return len(self.all_tool_dict)


def test_loading_the_registry_rewrites_the_served_descriptions():
    id_cue.install(_Registry)
    registry = _Registry()

    registry.load_tools()

    served = registry.all_tool_dict["HPA_get_cancer_prognostics_by_gene"]["description"]
    assert "Ensembl" in served, served


def test_the_loaders_return_value_is_preserved():
    """Callers read the tool count back from load_tools."""
    id_cue.install(_Registry)

    assert _Registry().load_tools() == 1


def test_installing_the_loader_hook_twice_does_not_double_wrap():
    id_cue.install(_Registry)
    once = _Registry.load_tools

    id_cue.install(_Registry)

    assert _Registry.load_tools is once
