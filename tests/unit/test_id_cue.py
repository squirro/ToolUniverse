"""The description must name the ID namespace the tool actually requires (DSR-662).

155 served tools require an identifier in a specific namespace, say so in the *parameter*
description, and never in the *tool* description -- the only surface the model reads at
every call. ``HPA_get_cancer_prognostics_by_gene`` advertises "prognostic value of a gene"
while requiring ``ensembl_id``, which is why two skill bodies call it with a bare gene
symbol and get nothing. Derived at registry load, never authored, and no file under the
data directory is touched (ADR-0014). The namespace is read out of the parameter
description's own grammar -- the words before "ID"/"accession"/"CURIE" -- rather than
matched against a list of known databases, which would be wrong the moment upstream adds
one.
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


def _tool(properties, required, description="Get a thing.", name="X_get"):
    return {"name": name, "description": description,
            "parameter": {"properties": properties, "required": required}}


# --- reading the namespace out of the parameter's own words ---


@pytest.mark.parametrize("description,expected", [
    ("Ensembl Gene ID of the gene to check, e.g. 'ENSG00000141510'.", ["Ensembl"]),
    ("UniProt accession for the protein.", ["UniProt"]),
    ("The ChEMBL ID of the molecule.", ["ChEMBL"]),
    ("A MONDO CURIE identifying the disease.", ["MONDO"]),
    ("PubChem CID for the compound.", ["PubChem"]),
    ("The maximum number of rows to return.", []),
    ("Free-text search query.", []),
    ("An Ensembl gene ID or a UniProt accession.", ["Ensembl", "UniProt"]),
    # BioModels_get_model: 'Find IDs using biomodels_search' is guidance, not a namespace.
    ("BioModels identifier (e.g., 'BIOMD0000000469'). Find IDs using biomodels_search.",
     ["BioModels"]),
    # disease_target_score: 'The EFO (Experimental Factor Ontology) ID' means EFO.
    ("The EFO (Experimental Factor Ontology) ID of the disease, e.g., 'EFO_0000339'", ["EFO"]),
    # 'P04637' is a value, not a database.
    ("Such as the P04637 ID.", []),
])
def test_the_namespace_comes_from_the_parameters_own_grammar(description, expected):
    assert sorted(id_cue.namespaces(description)) == sorted(expected)


@pytest.mark.parametrize("namespace", ["EFO", "UniProt", "NCBI", "Ensembl", "PDB"])
def test_the_cue_reads_grammatically_whatever_the_namespace_starts_with(namespace):
    """"a UniProt" and "an NCBI" are both correct by sound and both wrong by first letter,
    and no cheap rule gets every case; the phrasing avoids the question instead."""
    cue = id_cue.derive_cue(_tool({"x": {"description": f"The {namespace} ID of the thing."}},
                                  ["x"]))

    assert f"the {namespace} namespace" in cue, cue
    assert f"a {namespace}" not in cue and f"an {namespace}" not in cue, cue


# --- the derived cue ---


def test_a_tool_hiding_its_namespace_gains_a_cue_naming_it_with_an_example():
    """A shape the model can copy beats a namespace it has to guess the format of."""
    cue = id_cue.derive_cue(HPA)

    assert cue is not None and "Ensembl" in cue
    assert "ENSG00000141510" in cue


@pytest.mark.parametrize("tool", [
    # A description that already names the namespace gains nothing.
    dict(HPA, description="Prognostics by Ensembl gene ID across cancers."),
    # No required parameter at all.
    _tool({"query": {"description": "A ChEMBL ID, optionally."}}, [], name="X_search"),
    # An optional namespaced filter is not what the model gets wrong at call time.
    _tool({"name": {"description": "A plain name."},
           "chembl_id": {"description": "Optional ChEMBL ID filter."}}, ["name"]),
])
def test_a_tool_that_hides_nothing_required_gains_no_cue(tool):
    assert id_cue.derive_cue(tool) is None


def test_two_namespaces_produce_one_well_formed_cue():
    cue = id_cue.derive_cue(_tool(
        {"identifier": {"description": "An Ensembl gene ID or UniProt accession."}},
        ["identifier"], description="Map an identifier.", name="X_map"))

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

    assert once["description"] == id_cue.apply(once)["description"]


def test_apply_leaves_a_tool_with_nothing_to_add_exactly_as_it_was():
    tool = {"name": "X", "description": "Plain.", "parameter": {"properties": {}}}

    assert id_cue.apply(tool) == tool


# --- it has to actually happen at registry load: a derivation nothing calls changes
# --- no description the model ever reads.


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
