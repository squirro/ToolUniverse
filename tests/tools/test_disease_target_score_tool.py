"""Regression tests for DiseaseTargetScoreTool.

Guards the fix for the unguarded ``response_data["data"]["disease"]`` access
(graphql_tool.py). ``execute_query`` runs ``remove_none_and_empty_values``,
so an invalid efoId (commonly a disease *name* passed instead of an
EFO/MONDO id) comes back as ``{"data": {}}``. The old code indexed
``["disease"]`` directly and raised ``KeyError: 'disease'`` -> surfaced to
the agent as ``"Unexpected error: 'disease'"``.
"""

import json
import os
from unittest.mock import patch

from tooluniverse import graphql_tool
from tooluniverse.graphql_tool import DiseaseTargetScoreTool


def _cfg():
    path = os.path.join(
        os.path.dirname(graphql_tool.__file__),
        "data",
        "disease_target_score_tools.json",
    )
    tools = json.load(open(path))
    return next(t for t in tools if t["name"] == "cancer_biomarkers_disease_target_score")


def test_not_found_efoid_returns_clean_error_not_keyerror():
    """Invalid efoId -> execute_query yields data={} -> must NOT raise KeyError."""
    tool = DiseaseTargetScoreTool(_cfg())
    with patch.object(graphql_tool, "execute_query", return_value={"data": {}}):
        result = tool.run({"efoId": "prostate cancer"})  # name, not an id
    assert result["status"] == "error"
    assert "efoId" in result["error"]
    # Actionable: points the caller at name->id resolution.
    assert "EFO" in result["error"] or "MONDO" in result["error"]


def test_missing_efoid_required():
    tool = DiseaseTargetScoreTool(_cfg())
    result = tool.run({})
    assert result["status"] == "error"
    assert result["error"] == "efoId is required"


def test_valid_efoid_returns_scores():
    tool = DiseaseTargetScoreTool(_cfg())
    page = {
        "data": {
            "disease": {
                "id": "MONDO_0008315",
                "name": "prostate cancer",
                "associatedTargets": {
                    "count": 1,
                    "rows": [
                        {
                            "target": {"approvedSymbol": "AR", "id": "ENSG00000169083"},
                            "datasourceScores": [
                                {"id": "cancer_biomarkers", "score": 0.87}
                            ],
                        }
                    ],
                },
            }
        }
    }
    with patch.object(graphql_tool, "execute_query", return_value=page):
        result = tool.run({"efoId": "MONDO_0008315"})
    assert result["status"] == "success"
    scores = result["data"]["target_scores"]
    assert scores and scores[0]["target_symbol"] == "AR"
    assert scores[0]["datasource"] == "cancer_biomarkers"
