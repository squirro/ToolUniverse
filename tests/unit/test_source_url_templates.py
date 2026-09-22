"""A tool that POSTs still owes the reader an openable link (DSR-671).

DSR-667 cites a call by reading the intercepted request URL, which says nothing for a POST:
all 56 OpenTargets tools POST to one GraphQL endpoint, so the captured URL is byte-identical
whatever was asked, and citing it renders a footnote that looks checked and lands nowhere
(DSR-631). The answer is to stop deriving the link from the transport: a template names the
record the answer describes and is rendered from the call's own arguments. Rendering is pure
-- template plus arguments in, string or nothing out -- which is what makes these tests
network-free.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.tools_sr import source_url, source_url_templates

DATA = Path(source_url.__file__).resolve().parents[1] / "data"
OT = {"type": "OpenTarget"}


@pytest.mark.parametrize("template,arguments,expected", [
    ("https://platform.opentargets.org/target/{ensemblId}", {"ensemblId": "ENSG00000157764"},
     "https://platform.opentargets.org/target/ENSG00000157764"),
    # `/target/None` is a link a researcher opens once and never trusts again.
    ("https://platform.opentargets.org/target/{ensemblId}", {"efoId": "EFO_0000311"}, None),
    ("https://x/{a}", {"a": None}, None),
    ("https://x/{a}", {"a": ""}, None),
    ("https://x/{a}", {"a": "   "}, None),
    # Search terms carry spaces, and an identifier may not be one we have seen.
    ("https://platform.opentargets.org/search?q={queryString}", {"queryString": "BRAF V600E"},
     "https://platform.opentargets.org/search?q=BRAF%20V600E"),
    # The pages are per-entity; a call for several has no single record, so it cites the first.
    ("https://x/{ids}", {"ids": ["GO:0006915", "GO:0008219"]}, "https://x/GO%3A0006915"),
    ("https://x/{ids}", {"ids": []}, None),
])
def test_rendering_is_pure_and_refuses_to_half_render(template, arguments, expected):
    assert source_url_templates.render(template, arguments) == expected


@pytest.mark.parametrize("tool,arguments,config,expected", [
    # DSR-631 step 2: the API URL reproduces the query, but the record page is what reads as
    # credible in a footnote. One representative call per record-bearing GET family.
    ("tool", {"pdb_id": "1TUP"}, {"type": "RCSBTool"}, "https://www.rcsb.org/structure/1TUP"),
    ("tool", {"pdb_id": "1TUP"}, {"type": "RCSBDataTool"}, "https://www.rcsb.org/structure/1TUP"),
    ("tool", {"accession": "P30874"}, {"type": "UniProtRESTTool"},
     "https://www.uniprot.org/uniprotkb/P30874"),
    ("tool", {"cid": "2244"}, {"type": "PubChemRESTTool"},
     "https://pubchem.ncbi.nlm.nih.gov/compound/2244"),
    ("tool", {"aid": "1000"}, {"type": "PubChemRESTTool"},
     "https://pubchem.ncbi.nlm.nih.gov/bioassay/1000"),
    ("tool", {"cid": "2244", "compound_name": "aspirin"}, {"type": "PubChemToxTool"},
     "https://pubchem.ncbi.nlm.nih.gov/compound/2244"),
    ("tool", {"aid": "1000"}, {"type": "PubChemBioAssayTool"},
     "https://pubchem.ncbi.nlm.nih.gov/bioassay/1000"),
    ("tool", {"stId": "R-HSA-1640170"}, {"type": "ReactomeRESTTool"},
     "https://reactome.org/content/detail/R-HSA-1640170"),
    # RCSBGraphQLTool and gnomAD POST, so a template is their ONLY route to a citation;
    # a multi-id call cites its first entry.
    ("RCSBGraphQL_get_structure_summary", {"pdb_ids": ["1TUP", "4HHB"]},
     {"type": "RCSBGraphQLTool"}, "https://www.rcsb.org/structure/1TUP"),
    # gnomAD's dataset lives in `default_variables`, not the call, so the page is cited
    # without it and gnomAD's own default dataset applies.
    ("gnomad_get_variant", {"variant_id": "19-44908822-C-T"}, {"type": "gnomADGraphQLQueryTool"},
     "https://gnomad.broadinstitute.org/variant/19-44908822-C-T"),
    # The free-text search has no record page until it resolves, so it abstains.
    ("gnomad_search_variants", {"query": "rs7412"}, {"type": "gnomADGraphQLQueryTool"}, None),
    # The tool is the authority on where its answer can be read.
    ("OpenTargets_get_publications_by_target_ensemblID", {"entityId": "ENSG00000157764"},
     {**OT, "source_url_template": "https://elsewhere/{entityId}"},
     "https://elsewhere/ENSG00000157764"),
    ("ChEMBL_search_targets", {"query": "BRAF"}, {"type": "ChEMBLTool"}, None),
    # Citation sits on the hot path for every tool result; it must never be what fails.
    ("whatever", {"a": "b"}, None, None),
    (None, None, None, None),
])
def test_a_declared_template_names_the_record_page(tool, arguments, config, expected):
    assert source_url_templates.declared_url(tool, arguments, config) == expected


@pytest.mark.parametrize("tool,arguments,tail", [
    # A call carrying both a target and a disease describes the evidence for that pair.
    ("OpenTargets_target_disease_evidence",
     {"ensemblId": "ENSG00000157764", "efoId": "MONDO_0005105"},
     "/evidence/ENSG00000157764/MONDO_0005105"),
    # The less specific template is used when the specific one cannot render.
    ("OpenTargets_get_diseases_phenotypes_by_target_ensembl", {"ensemblId": "ENSG00000157764"},
     "/target/ENSG00000157764"),
    # `entityId` is an Ensembl, EFO or ChEMBL id depending only on which tool was called,
    # so the arguments alone cannot say which page it belongs to.
    ("OpenTargets_get_publications_by_target_ensemblID", {"entityId": "ID"}, "/target/ID"),
    ("OpenTargets_get_publications_by_disease_efoId", {"entityId": "ID"}, "/disease/ID"),
    ("OpenTargets_get_publications_by_drug_chemblId", {"entityId": "ID"}, "/drug/ID"),
])
def test_the_most_specific_renderable_family_template_wins(tool, arguments, tail):
    url = source_url_templates.declared_url(tool, arguments, OT)
    assert url is not None and url.endswith(tail), (tool, url)


def test_every_gnomad_tool_that_names_a_record_renders_a_link():
    """Gene, transcript, region and variant pages, each keyed on what the call was given."""
    cases = {
        "gnomad_get_gene_constraints": ({"gene_symbol": "BRCA1"}, "/gene/BRCA1"),
        "gnomad_get_gene": ({"gene_symbol": "BRCA1"}, "/gene/BRCA1"),
        "gnomad_get_transcript": ({"transcript_id": "ENST00000357654"},
                                  "/transcript/ENST00000357654"),
        "gnomad_get_region": ({"chrom": "17", "start": 43044295, "stop": 43125483},
                              "/region/17-43044295-43125483"),
        # The SV query names gnomad_sv_r4 in its body; the site needs it in the URL too.
        "gnomad_get_sv_detail": ({"variant_id": "DEL_CHR17_1234"},
                                 "/variant/DEL_CHR17_1234?dataset=gnomad_sv_r4"),
    }
    types = {t["name"]: t["type"]
             for t in json.loads((DATA / "gnomad_tools.json").read_text())}
    for tool, (arguments, tail) in cases.items():
        url = source_url_templates.declared_url(tool, arguments, {"type": types[tool]})
        assert url is not None and url.endswith(tail), (tool, url)


def test_every_opentargets_tool_but_the_go_lookup_renders_a_link():
    """55 of 56. The exception has no entity page keyed on what it is given, and abstains
    rather than inventing one -- which is the behaviour this ticket asks for."""
    tools = json.loads((DATA / "opentarget_tools.json").read_text())
    without = [tool["name"] for tool in tools
               if source_url_templates.declared_url(
                   tool["name"],
                   {name: "X" for name in ((tool.get("parameter") or {}).get("properties") or {})},
                   tool) is None]

    assert without == [], without
    assert len(tools) >= 56, len(tools)


def test_each_opentargets_tool_produces_a_link_distinct_to_its_own_query():
    """The defect being fixed: one endpoint, one captured URL, every question alike."""
    tool = "OpenTargets_get_diseases_phenotypes_by_target_ensembl"
    a = source_url_templates.declared_url(tool, {"ensemblId": "ENSG00000157764"}, OT)
    b = source_url_templates.declared_url(tool, {"ensemblId": "ENSG00000141510"}, OT)

    assert a != b


# --- and the stamper prefers a template over the intercepted URL ---


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
        arguments={"ensemblId": "ENSG00000157764"}, config=OT)

    assert stamped["source_url"].endswith("/target/ENSG00000157764")


def test_without_a_template_the_intercepted_url_is_still_used():
    stamped = source_url.stamp({"data": []}, [_record("https://api.example.org/lookup?symbol=BRAF")],
                               tool_name="Something_else", arguments={"symbol": "BRAF"},
                               config={"type": "Other"})

    assert stamped["source_url"] == "https://api.example.org/lookup?symbol=BRAF"


def test_a_tool_that_already_cites_itself_is_left_alone():
    stamped = source_url.stamp(
        {"source_url": "https://curated.example/record/1"}, [],
        tool_name="OpenTargets_get_diseases_phenotypes_by_target_ensembl",
        arguments={"ensemblId": "ENSG00000157764"}, config=OT)

    assert stamped["source_url"] == "https://curated.example/record/1"
