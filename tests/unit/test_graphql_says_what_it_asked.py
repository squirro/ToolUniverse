"""A retry with different arguments answers a different question, and said so nowhere.

`OpentargetTool` answers an unsuccessful drug query by asking again with the arguments
quietly changed: the drug name is cut at its first hyphen and every remaining hyphen
becomes a space, so `ZD-1839` is asked as `ZD` and `5-FU` as `5`. Whatever that second
question returns comes back as a success about the drug the caller named. `ZD` is a
prefix, not a drug.

The retry also fired on a source that had *failed*, not merely answered with nothing, so
an OpenTargets outage was followed by a second, differently-worded query whose rows were
then attributed to the caller's drug.

`OpentargetToolDrugNameMatch` swaps the brand name for openFDA's generic name and records
that only with `print()` to the server's standard output, which is not the agent's channel.

Separately, `execute_query` runs `remove_none_and_empty_values`, which **deletes any key
whose value is an empty list**. `DiseaseTargetScoreTool` then reads `associatedTargets`
rows and `datasourceScores` with bracket access, so a target carrying no datasource scores
raises `KeyError`. That surfaces as a server error, which `is_upstream_failure` reads as
retriable, so the runner retries a call that cannot ever succeed. The file already handles
exactly this for the `disease` key, and says why in its own comment.

The payloads below are put through the real cleaner rather than written out in their
stripped form, so the shape under test is the one the module actually produces.
"""

from unittest.mock import patch

import pytest

import tooluniverse.graphql_tool as gqt
from tooluniverse.graphql_tool import (DiseaseTargetScoreTool, OpentargetTool,
                                       remove_none_and_empty_values)
from tooluniverse.http_utils import upstream_error

pytestmark = pytest.mark.unit


def _drug_tool():
    return OpentargetTool({
        "name": "drug_query", "type": "OpenTarget",
        "query_schema": "query($drugName: String!) { drug(name: $drugName) { id } }",
        "parameter": {"type": "object", "properties": {}},
    })


def _score_tool():
    return DiseaseTargetScoreTool({
        "name": "disease_target_score", "type": "DiseaseTargetScoreTool",
        "query_schema": "query { disease { id } }",
        "parameter": {"type": "object", "properties": {}},
        "datasource_id": "chembl",
    })


# ------------------------------------------------------------------ the silent second question

def test_a_retry_that_changed_the_drug_name_states_the_name_it_used():
    """`ZD-1839` asked as `ZD` is a different question and the answer must say so."""
    asked = []

    def _execute(endpoint_url=None, query=None, variables=None, **kw):
        asked.append(variables.get("drugName"))
        return None if variables.get("drugName") == "ZD-1839" else {"data": {"drug": {"id": "X"}}}

    with patch.object(gqt, "execute_query", side_effect=_execute):
        result = _drug_tool().run({"drugName": "ZD-1839"})

    assert asked == ["ZD-1839", "ZD"], asked
    assert result["status"] == "success"
    assert "ZD" in str(result.get("metadata")), result


def test_a_source_that_failed_is_not_asked_a_different_question():
    """An outage is not a drug name that needs shortening."""
    asked = []

    def _execute(endpoint_url=None, query=None, variables=None, **kw):
        asked.append(variables.get("drugName"))
        return upstream_error("OpenTargets answered HTTP 503", 503, retryable=True)

    with patch.object(gqt, "execute_query", side_effect=_execute):
        result = _drug_tool().run({"drugName": "ZD-1839"})

    assert asked == ["ZD-1839"], asked
    assert result["status"] == "error"


def test_a_drug_the_source_knows_is_never_re_asked():
    asked = []

    def _execute(endpoint_url=None, query=None, variables=None, **kw):
        asked.append(variables.get("drugName"))
        return {"data": {"drug": {"id": "CHEMBL939"}}}

    with patch.object(gqt, "execute_query", side_effect=_execute):
        result = _drug_tool().run({"drugName": "5-FU"})

    assert asked == ["5-FU"], asked
    assert result["status"] == "success"
    assert "metadata" not in result or "retried_with" not in result["metadata"]


# ------------------------------------------------------------- the emptied keys the cleaner made

def _page(rows, count=None):
    """One associatedTargets page, put through the cleaner the module really runs."""
    return remove_none_and_empty_values({"data": {"disease": {
        "id": "EFO_0000339", "name": "test disease",
        "associatedTargets": {"count": len(rows) if count is None else count, "rows": rows},
    }}})


def test_the_cleaner_really_deletes_an_emptied_key():
    """The premise of the two tests below, stated rather than assumed."""
    cleaned = _page([{"target": {"approvedSymbol": "TP53", "id": "ENSG1"},
                      "datasourceScores": []}])

    row = cleaned["data"]["disease"]["associatedTargets"]["rows"][0]
    assert "datasourceScores" not in row, row


def test_a_target_with_no_datasource_scores_is_a_stated_absence():
    rows = [{"target": {"approvedSymbol": "TP53", "id": "ENSG1"}, "datasourceScores": []},
            {"target": {"approvedSymbol": "EGFR", "id": "ENSG2"},
             "datasourceScores": [{"id": "chembl", "score": 0.5}]}]

    with patch.object(gqt, "execute_query", side_effect=lambda *a, **k: _page(rows)):
        result = _score_tool().run({"efoId": "EFO_0000339", "datasourceId": "chembl"})

    assert result["status"] == "success", result
    assert [s["target_symbol"] for s in result["data"]["target_scores"]] == ["EGFR"]


def test_a_page_whose_rows_were_emptied_is_a_stated_absence():
    with patch.object(gqt, "execute_query", side_effect=lambda *a, **k: _page([], count=0)):
        result = _score_tool().run({"efoId": "EFO_0000339", "datasourceId": "chembl"})

    assert result["status"] == "success", result
    assert result["data"]["target_scores"] == []
    assert result["data"]["total_targets_with_scores"] == 0


def test_a_target_row_missing_its_target_block_is_skipped_not_a_key_error():
    rows = [{"datasourceScores": [{"id": "chembl", "score": 0.5}]},
            {"target": {"approvedSymbol": "EGFR", "id": "ENSG2"},
             "datasourceScores": [{"id": "chembl", "score": 0.5}]}]

    with patch.object(gqt, "execute_query", side_effect=lambda *a, **k: _page(rows)):
        result = _score_tool().run({"efoId": "EFO_0000339", "datasourceId": "chembl"})

    assert result["status"] == "success", result
    assert [s["target_symbol"] for s in result["data"]["target_scores"]] == ["EGFR"]
