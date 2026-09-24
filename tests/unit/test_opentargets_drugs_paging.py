"""The drugs-for-target tool pages its list and says how much of it the source holds.

Open Targets answers the whole list in one response: `drugAndClinicalCandidates` takes no
paging argument. Whole, a well-studied target's list is larger than one agent response
carries, so the tool hands it out in pages, each with the source's own total.
"""

import json
from pathlib import Path

import pytest

import tooluniverse.graphql_tool as mod
from tooluniverse.graphql_tool import OpentargetTool

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "opentargets"
# The tool's own query, answered live for EGFR (ENSG00000146648).
EGFR = json.loads((FIXTURES / "egfr_drug_candidates_2026-09-24.json").read_text())
SOURCE_ROWS = EGFR["data"]["target"]["drugAndClinicalCandidates"]["rows"]
SOURCE_TOTAL = EGFR["data"]["target"]["drugAndClinicalCandidates"]["count"]

CONFIGS = json.loads((Path(mod.__file__).parent / "data" / "opentarget_tools.json").read_text())
CONFIG = next(t for t in CONFIGS if t["name"] == "OpenTargets_get_associated_drugs_by_target_ensemblID")


@pytest.fixture
def sent(monkeypatch):
    seen = []

    def execute_query(endpoint_url, query, variables=None):
        seen.append(dict(variables or {}))
        return mod.remove_none_and_empty_values(json.loads(json.dumps(EGFR)))

    monkeypatch.setattr(mod, "execute_query", execute_query)
    return seen


def _rows(out):
    return out["data"]["target"]["drugAndClinicalCandidates"]["rows"]


def test_the_recorded_list_is_longer_than_one_page():
    assert SOURCE_TOTAL == len(SOURCE_ROWS) == 82
    assert CONFIG["parameter"]["properties"]["page_size"]["default"] < SOURCE_TOTAL


def test_a_page_holds_part_of_the_list_and_states_the_sources_total(sent):
    out = OpentargetTool(CONFIG).run({"ensemblId": "ENSG00000146648", "page": 1, "page_size": 25})

    assert [r["drug"]["id"] for r in _rows(out)] == [r["drug"]["id"] for r in SOURCE_ROWS[:25]]
    assert out["data"]["target"]["drugAndClinicalCandidates"]["count"] == 82, "the source's count is kept"
    meta = out["metadata"]
    assert (meta["total"], meta["page"], meta["page_size"], meta["returned"]) == (82, 1, 25, 25)
    assert meta["has_more"] is True and meta["next_page"] == 2
    assert "82" in meta["note"]


def test_the_pages_together_are_the_sources_list_in_its_order(sent):
    tool = OpentargetTool(CONFIG)
    pages = [tool.run({"ensemblId": "ENSG00000146648", "page": p, "page_size": 25}) for p in (1, 2, 3, 4)]

    assert [r["drug"]["id"] for page in pages for r in _rows(page)] == [
        r["drug"]["id"] for r in SOURCE_ROWS]
    last = pages[-1]["metadata"]
    assert (last["returned"], last["has_more"], last["next_page"]) == (7, False, None)


def test_paging_is_the_tools_own_and_never_sent_to_the_source(sent):
    OpentargetTool(CONFIG).run({"ensemblId": "ENSG00000146648", "page": 2, "page_size": 10})

    assert sent == [{"ensemblId": "ENSG00000146648"}]


def test_without_paging_arguments_the_first_page_comes_with_the_total(sent):
    out = OpentargetTool(CONFIG).run({"ensemblId": "ENSG00000146648"})

    default = CONFIG["parameter"]["properties"]["page_size"]["default"]
    assert len(_rows(out)) == default
    assert (out["metadata"]["total"], out["metadata"]["has_more"]) == (82, True)


def test_a_page_wide_enough_holds_the_whole_list(sent):
    out = OpentargetTool(CONFIG).run({"ensemblId": "ENSG00000146648", "page_size": 1000})

    assert len(_rows(out)) == 82
    assert (out["metadata"]["returned"], out["metadata"]["has_more"]) == (82, False)


def test_the_return_schema_declares_the_total_and_the_fields_the_query_asks_for():
    schema = CONFIG["return_schema"]["properties"]
    assert {"total", "page", "page_size", "returned", "has_more", "next_page"} <= set(
        schema["metadata"]["properties"])
    row = (schema["data"]["properties"]["target"]["properties"]["drugAndClinicalCandidates"]
           ["properties"]["rows"]["items"]["properties"])
    assert set(row) == {"drug", "maxClinicalStage", "diseases"}
    assert set(row["drug"]["properties"]) == {"id", "name", "maximumClinicalStage"}
