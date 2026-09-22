"""A tool's schema must let a model construct a valid call before it makes one.

Every tool below demands, at runtime, a parameter its schema never marks required. Each was
observed failing over SMCP in the audit baseline (`.scratch/tool-audit/audit_mcp_complete
.jsonl`, verdict `error_schema_mismatch`). The runtime messages are excellent, but they
arrive *after* a failed call, so a model reading the schema guesses, fails, and burns a turn.

Two shapes, two fixes: a parameter the tool always needs belongs in `required`; "at least
one of X, Y or Z" cannot be expressed by a flat `required` list at all, so that contract has
to live in the description -- the only other surface the model reads before calling.
"""

import glob
import json
import os
import re

import pytest

DATA = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "data"
)

# (tool, parameter the runtime demands unconditionally)
ALWAYS_REQUIRED = [
    ("BRENDA_get_enzyme_info", "ec_number"),
    ("BRENDA_get_inhibitors", "ec_number"),
    ("BRENDA_get_kcat", "ec_number"),
    ("BRENDA_get_km", "ec_number"),
    ("CancerPrognosis_get_gene_expression", "cancer"),
    ("CancerPrognosis_get_study_summary", "cancer"),
    ("CancerPrognosis_get_survival_data", "cancer"),
    ("CancerPrognosis_search_studies", "keyword"),
    ("ChEMBL_get_drug_mechanisms", "drug_chembl_id"),
    ("ELM_get_instances", "uniprot_id"),
    ("Orphanet_get_classification", "orpha_code"),
    ("Orphanet_get_disease", "orpha_code"),
    ("Orphanet_get_icd_mapping", "orpha_code"),
    ("gwas_get_snps_for_gene", "gene_symbol"),
    ("iPTMnet_search", "search_term"),
]

# (tool, the alternatives the runtime says at least one of is needed)
ONE_OF = [
    ("BVBRC_search_amr", ("antibiotic", "genome_id", "resistant_phenotype")),
    ("BVBRC_search_surveillance",
     ("subtype", "geographic_group", "host_group", "collection_country")),
    ("LOVD_search_variants", ("variant_dbid", "dna_notation")),
    ("OmniPath_get_enzyme_substrate", ("enzymes", "substrates")),
    ("OmniPath_get_ligand_receptor_interactions",
     ("partners", "sources", "targets")),
    ("OmniPath_get_signaling_interactions", ("partners", "sources", "targets")),
    ("OmniPath_get_tf_target_interactions", ("tf_gene", "target_gene")),
    ("OpenFDA_get_approval_history", ("drug_name", "application_number")),
    ("OpenFDA_get_approved_products", ("drug_name", "application_number")),
    ("OpenFDA_search_drug_approvals",
     ("drug_name", "sponsor", "application_number")),
    ("PharmacoDB_get_biomarker_assoc", ("compound_name", "compound_id")),
    ("PharmacoDB_get_cell_line", ("cell_name", "cell_id")),
    ("PharmacoDB_get_compound", ("compound_name", "compound_id")),
    ("PharmacoDB_get_experiments", ("compound_name", "cell_line_name")),
    ("ProtacDB_search_protacs", ("target", "e3_ligase")),
    ("SIDER_get_drug_indications", ("sider_drug_id", "drug_name")),
    ("SIDER_get_drug_side_effects", ("sider_drug_id", "drug_name")),
    ("SIDER_get_drugs_for_side_effect", ("meddra_code", "side_effect_name")),
    ("SYNERGxDB_search_combos",
     ("drug_id_1", "drug_id_2", "drug_name_1", "drug_name_2", "dataset")),
    ("SynBioHub_get_part", ("part_uri", "display_id")),
    # Conditional on the mode rather than on a sibling parameter.
    ("MolecularFormula_analyze", ("formula",)),
    # Both refuse a term-only call: snippets need a document to read, and the
    # audit probe's {"terms": [...]} was rejected as "Provide either ...".
    ("ArXiv_get_pdf_snippets", ("arxiv_id", "pdf_url")),
    ("SemanticScholar_get_pdf_snippets", ("paper_id", "open_access_pdf_url")),
]

# Words that signal a conditional requirement to a reader.
CONDITIONAL_MARKERS = (
    "at least one", "either", "one of", "required for", "required when",
    "provide one", "must supply",
)


def _load_tools():
    tools = {}
    for path in glob.glob(os.path.join(DATA, "**", "*.json"), recursive=True):
        try:
            defs = json.load(open(path))
        except Exception:
            continue
        if isinstance(defs, list):
            for tool in defs:
                if isinstance(tool, dict) and tool.get("name"):
                    tools.setdefault(tool["name"], tool)
    return tools


TOOLS = _load_tools()


def _tool(name):
    assert name in TOOLS, f"{name} not found in {DATA}"
    return TOOLS[name]


@pytest.mark.unit
@pytest.mark.parametrize("name,param", ALWAYS_REQUIRED)
def test_unconditionally_demanded_parameter_is_declared_required(name, param):
    """The case the schema CAN express exactly, so there is no excuse for leaving the
    model to discover it by failing."""
    required = (_tool(name).get("parameter") or {}).get("required") or []
    assert param in required, (
        f"{name} rejects any call without {param!r}, but its schema requires "
        f"{required} -- a model reading the schema cannot know to send it"
    )


@pytest.mark.unit
@pytest.mark.parametrize("name,alternatives", ONE_OF)
def test_conditional_requirement_is_stated_in_the_description(name, alternatives):
    """Asserted against the description only: the parameter NAMES appear in `properties`
    by definition, so checking there would pass without any fix."""
    description = (_tool(name).get("description") or "").lower()

    missing = [a for a in alternatives if a.lower() not in description]
    assert not missing, (
        f"{name} requires at least one of {list(alternatives)} at runtime, but "
        f"its description never mentions {missing}"
    )
    assert any(m in description for m in CONDITIONAL_MARKERS), (
        f"{name}'s description names the parameters but does not say one of "
        f"them is required; add an explicit 'at least one of ...' statement"
    )


# A description that names a filter the schema does not declare sends the model to
# construct a call it has no way to validate. Same defect as the two above, arriving from
# the opposite direction: the prose is ahead of the contract.
FILTER_TOKEN = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)*__[a-z]+)\b")


def _undeclared_filters(tool) -> list[str]:
    """Filters the prose names that the schema does not declare."""
    schema = tool.get("parameter") or {}
    properties = schema.get("properties") or {}
    prose = (tool.get("description") or "") + " ".join(
        (p or {}).get("description", "") for p in properties.values()
    )
    return sorted(set(FILTER_TOKEN.findall(prose)) - set(properties))


@pytest.mark.unit
def test_no_description_names_a_filter_its_schema_does_not_declare():
    """Django-style `field__operator` filters read as instructions, not prose.

    ChEMBL_search_activities told the model to prefer `target_chembl_id__exact` while
    declaring `target_chembl_id`. Both work upstream, so the tool was never broken; the
    model was pointed at a name it cannot find in its own schema. Checked in one pass
    rather than per tool: 2,400 parametrised cases to name one offender is a lot of test.
    """
    offenders = {
        name: undeclared
        for name, tool in sorted(TOOLS.items())
        if tool.get("parameter") and (undeclared := _undeclared_filters(tool))
    }
    assert not offenders, (
        "descriptions naming a filter the schema does not declare: "
        + "; ".join(f"{n} -> {f}" for n, f in offenders.items())
    )


# --- the same rule, widened past filter tokens (DSR-665) ---
# The narrow rule above is kept as a regression gate; this widens it to parameter names
# generally. Widening naively is unusable: 62 hits, most naming something real that simply
# is not an input to this tool. Four subtractions -- return-schema fields, registry tool
# names, the base of a declared filter, and a token whose sentence names another tool --
# take that to 4, all waived by name. The corpus has no true positive of this class today;
# the rule ships blocking at zero, and its whole value is in what it stops arriving.

from tooluniverse.tools_sr import description_contract  # noqa: E402


def _thing(description, properties=("query",), **extra):
    return {
        "name": "Thing_search",
        "description": description,
        "parameter": {"properties": {p: {} for p in properties}},
        **extra,
    }


_OTHER_GET_GENE = {"name": "Other_get_gene", "parameter": {"properties": {"x": {}}}}


@pytest.mark.unit
def test_no_description_names_a_parameter_its_schema_does_not_declare():
    findings = description_contract.undeclared_parameters(TOOLS)

    assert not findings, "; ".join(f.message for f in findings)


@pytest.mark.unit
@pytest.mark.parametrize(
    "tools,expected",
    [
        # Proof the widened rule can fail. Green over a corpus it was tuned on means little.
        ({"Thing_search": _thing("Search things. Pass `organism_name` to restrict it.")},
         [("Thing_search", "organism_name")]),
        # A single backticked word is usually prose -- allowing them all adds `only`, `null`
        # and `df`. The registry decides: a one-word token counts only if some tool
        # declares a parameter by that name.
        ({"Other_search": {"name": "Other_search",
                           "parameter": {"properties": {"organism": {}}}},
          "Thing_search": _thing("Search things. Pass `organism` to restrict it.")},
         [("Thing_search", "organism")]),
        ({"Thing_search": _thing(
            "Returns `null` when nothing matches; use `only` one filter.")}, []),
        # Describing what comes back is not an instruction to pass it.
        ({"Thing_search": _thing("Search things. The response carries `total_count`.",
                                 return_schema={"properties": {"total_count": {}}})}, []),
        # `pref_name` beside a declared `pref_name__contains` is the field being explained.
        ({"Thing_search": _thing("Note that `pref_name` coverage is incomplete.",
                                 properties=("pref_name__contains",))}, []),
        # A hand-off names its destination.
        ({"Other_get_gene": _OTHER_GET_GENE,
          "Thing_search": _thing("Use `Other_get_gene` to find a gene's `canonical_id`.")},
         []),
        # A description that merely borrows a name leaves the model nowhere to send it.
        ({"Other_get_gene": _OTHER_GET_GENE,
          "Thing_search": _thing("Resolve the gene first, then pass its `canonical_id`.")},
         [("Thing_search", "canonical_id")]),
    ],
)
def test_a_description_may_only_name_parameters_its_schema_declares(tools, expected):
    findings = description_contract.undeclared_parameters(tools)

    assert [(f.tool, f.token) for f in findings] == expected


@pytest.mark.unit
def test_every_waiver_states_a_reason():
    for tool, tokens in description_contract.WAIVED.items():
        for token, reason in tokens.items():
            assert reason.strip() and len(reason) > 20, (tool, token, reason)


@pytest.mark.unit
def test_no_waiver_has_gone_stale():
    """A waiver for a token the prose no longer mentions is dead weight that would quietly
    cover a real finding if that token ever came back."""
    for tool_name, tokens in description_contract.WAIVED.items():
        tool = TOOLS.get(tool_name)
        assert tool is not None, tool_name
        prose = description_contract._prose(tool)
        for token in tokens:
            assert f"`{token}`" in prose, (tool_name, token)
