"""A tool that POSTs still owes the reader an openable link (DSR-671).

DSR-667 cites the call that produced an answer by reading the intercepted request URL.
That works for a GET, whose parameters are in the URL, and says nothing for a POST, whose
parameters are in the body: all 56 OpenTargets tools POST to one GraphQL endpoint, so the
captured URL is byte-identical whatever was asked. Citing it would render a footnote that
looks checked and lands nowhere -- worse than no citation (DSR-631), which is why the
interceptor skips POSTs and why this family had no citation at all.

The answer is to stop deriving the link from the transport. A template names the record the
answer describes and is rendered from the call's own arguments, so each tool produces a
distinct link. Rendering is pure -- template plus arguments in, string or nothing out --
which is what makes these tests network-free.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.tools_sr import source_url, source_url_templates

DATA = Path(source_url.__file__).resolve().parents[1] / "data"


# --- rendering is pure, and refuses to half-render ---


def test_a_template_renders_from_the_call_arguments():
    url = source_url_templates.render(
        "https://platform.opentargets.org/target/{ensemblId}",
        {"ensemblId": "ENSG00000157764"},
    )

    assert url == "https://platform.opentargets.org/target/ENSG00000157764"


def test_a_missing_argument_yields_no_url_rather_than_a_broken_one():
    """``/target/None`` is a link a researcher opens once and never trusts again."""
    assert source_url_templates.render(
        "https://platform.opentargets.org/target/{ensemblId}", {"efoId": "EFO_0000311"}
    ) is None


@pytest.mark.parametrize("value", [None, "", "   "])
def test_a_blank_argument_yields_no_url(value):
    assert source_url_templates.render("https://x/{a}", {"a": value}) is None


def test_a_value_is_percent_encoded():
    """Search terms carry spaces, and an identifier may not be one we have seen."""
    url = source_url_templates.render(
        "https://platform.opentargets.org/search?q={queryString}",
        {"queryString": "BRAF V600E"},
    )

    assert url == "https://platform.opentargets.org/search?q=BRAF%20V600E"


def test_a_list_argument_cites_its_first_entry():
    """The pages are per-entity; a call for several has no single record to point at."""
    url = source_url_templates.render("https://x/{ids}", {"ids": ["GO:0006915", "GO:0008219"]})

    assert url == "https://x/GO%3A0006915"


def test_an_empty_list_yields_no_url():
    assert source_url_templates.render("https://x/{ids}", {"ids": []}) is None


# --- which template applies, and in what order ---


def test_the_most_specific_family_template_wins():
    """A call carrying both a target and a disease describes the evidence for that pair,
    not the target alone."""
    url = source_url_templates.declared_url(
        "OpenTargets_target_disease_evidence",
        {"ensemblId": "ENSG00000157764", "efoId": "MONDO_0005105"},
        {"type": "OpenTarget"},
    )

    assert url.endswith("/evidence/ENSG00000157764/MONDO_0005105")


def test_a_less_specific_template_is_used_when_the_specific_one_cannot_render():
    url = source_url_templates.declared_url(
        "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
        {"ensemblId": "ENSG00000157764"},
        {"type": "OpenTarget"},
    )

    assert url.endswith("/target/ENSG00000157764")


def test_record_bearing_get_families_cite_the_human_page_not_the_api():
    """DSR-631 step 2: the API URL reproduces the query, but the record page is what
    reads as credible in a footnote. One representative call per family."""
    cases = [
        ({"type": "RCSBTool"}, {"pdb_id": "1TUP"},
         "https://www.rcsb.org/structure/1TUP"),
        ({"type": "RCSBDataTool"}, {"pdb_id": "1TUP"},
         "https://www.rcsb.org/structure/1TUP"),
        ({"type": "UniProtRESTTool"}, {"accession": "P30874"},
         "https://www.uniprot.org/uniprotkb/P30874"),
        ({"type": "PubChemRESTTool"}, {"cid": "2244"},
         "https://pubchem.ncbi.nlm.nih.gov/compound/2244"),
        ({"type": "PubChemRESTTool"}, {"aid": "1000"},
         "https://pubchem.ncbi.nlm.nih.gov/bioassay/1000"),
        ({"type": "PubChemToxTool"}, {"cid": "2244", "compound_name": "aspirin"},
         "https://pubchem.ncbi.nlm.nih.gov/compound/2244"),
        ({"type": "PubChemBioAssayTool"}, {"aid": "1000"},
         "https://pubchem.ncbi.nlm.nih.gov/bioassay/1000"),
        ({"type": "ReactomeRESTTool"}, {"stId": "R-HSA-1640170"},
         "https://reactome.org/content/detail/R-HSA-1640170"),
    ]
    for config, arguments, expected in cases:
        url = source_url_templates.declared_url("tool", arguments, config)
        assert url == expected, (config, arguments, url)


def test_the_rcsb_graphql_family_cites_a_structure_page_from_its_id_list():
    """RCSBGraphQLTool POSTs, so — like OpenTargets — a template is its ONLY route to a
    citation: the interceptor never cites a POST. A multi-id call cites its first entry."""
    url = source_url_templates.declared_url(
        "RCSBGraphQL_get_structure_summary",
        {"pdb_ids": ["1TUP", "4HHB"]},
        {"type": "RCSBGraphQLTool"},
    )

    assert url == "https://www.rcsb.org/structure/1TUP"


def test_a_tool_declaring_its_own_template_overrides_this_module():
    """The tool is the authority on where its answer can be read."""
    url = source_url_templates.declared_url(
        "OpenTargets_get_publications_by_target_ensemblID",
        {"entityId": "ENSG00000157764"},
        {"type": "OpenTarget", "source_url_template": "https://elsewhere/{entityId}"},
    )

    assert url == "https://elsewhere/ENSG00000157764"


def test_an_entity_id_gets_the_page_its_tool_name_implies():
    """`entityId` is an Ensembl, EFO or ChEMBL id depending only on which tool was called,
    so the arguments alone cannot say which page it belongs to."""
    pairs = {
        "OpenTargets_get_publications_by_target_ensemblID": "/target/ID",
        "OpenTargets_get_publications_by_disease_efoId": "/disease/ID",
        "OpenTargets_get_publications_by_drug_chemblId": "/drug/ID",
    }
    for tool, tail in pairs.items():
        url = source_url_templates.declared_url(tool, {"entityId": "ID"},
                                                {"type": "OpenTarget"})
        assert url.endswith(tail), (tool, url)


def test_a_tool_outside_the_family_gets_no_template():
    assert source_url_templates.declared_url(
        "ChEMBL_search_targets", {"query": "BRAF"}, {"type": "ChEMBLTool"}
    ) is None


def test_a_missing_config_does_not_raise():
    """Citation sits on the hot path for every tool result; it must never be what fails."""
    assert source_url_templates.declared_url("whatever", {"a": "b"}, None) is None
    assert source_url_templates.declared_url(None, None, None) is None


# --- the family is actually covered, and the coverage is measured, not assumed ---


def test_every_opentargets_tool_but_the_go_lookup_renders_a_link():
    """55 of 56. The exception has no entity page keyed on what it is given, and abstains
    rather than inventing one -- which is the behaviour this ticket asks for."""
    tools = json.loads((DATA / "opentarget_tools.json").read_text())
    without = []
    for tool in tools:
        declared = (tool.get("parameter") or {}).get("properties") or {}
        arguments = {name: "X" for name in declared}
        if source_url_templates.declared_url(tool["name"], arguments, tool) is None:
            without.append(tool["name"])

    assert without == [], without
    assert len(tools) >= 56, len(tools)


def test_each_opentargets_tool_produces_a_link_distinct_to_its_own_query():
    """The defect being fixed: one endpoint, one captured URL, every question alike."""
    a = source_url_templates.declared_url(
        "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
        {"ensemblId": "ENSG00000157764"}, {"type": "OpenTarget"})
    b = source_url_templates.declared_url(
        "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
        {"ensemblId": "ENSG00000141510"}, {"type": "OpenTarget"})

    assert a != b


# --- and the stamper prefers it over the intercepted URL ---


def _record(url, method="GET"):
    from tooluniverse.tools_sr import http_record

    return http_record.CallRecord(url=url, status_code=200, reached=True, error=None,
                                  method=method)


def test_a_declared_template_outranks_the_intercepted_url():
    """Interception can only report the endpoint; the template names the record."""
    records = [_record("https://api.platform.opentargets.org/api/v4/graphql", method="POST"),
               _record("https://api.example.org/lookup?symbol=BRAF")]

    stamped = source_url.stamp(
        {"data": []}, records,
        tool_name="OpenTargets_get_diseases_phenotypes_by_target_ensembl",
        arguments={"ensemblId": "ENSG00000157764"},
        config={"type": "OpenTarget"},
    )

    assert stamped["source_url"].endswith("/target/ENSG00000157764")


def test_without_a_template_the_intercepted_url_is_still_used():
    records = [_record("https://api.example.org/lookup?symbol=BRAF")]

    stamped = source_url.stamp({"data": []}, records, tool_name="Something_else",
                               arguments={"symbol": "BRAF"}, config={"type": "Other"})

    assert stamped["source_url"] == "https://api.example.org/lookup?symbol=BRAF"


def test_a_tool_that_already_cites_itself_is_left_alone():
    stamped = source_url.stamp(
        {"source_url": "https://curated.example/record/1"}, [],
        tool_name="OpenTargets_get_diseases_phenotypes_by_target_ensembl",
        arguments={"ensemblId": "ENSG00000157764"}, config={"type": "OpenTarget"},
    )

    assert stamped["source_url"] == "https://curated.example/record/1"
