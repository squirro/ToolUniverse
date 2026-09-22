"""Every FAERS analytics operation resolves the drug through the same field chain.

Only `calculate_disproportionality` resolved a brand name through the chain; the other
operations hard-coded `patient.drug.openfda.generic_name`, which matches no brand name, so
the reaction counts arrived and every other operation answered 404. One drug name, one field
for every operation.
"""
import json
import pathlib
import types

import pytest

import tooluniverse.faers_analytics_tool as mod
from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

pytestmark = pytest.mark.unit

CONFIGS = {t["name"]: t for t in json.loads(
    (pathlib.Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
     / "faers_analytics_tools.json").read_text())}

# openFDA answers 404 for generic_name and a count for brand_name.
KNOWN = {"patient.drug.openfda.brand_name": 5551}

CASES = [
    ("FAERS_stratify_by_demographics", {"drug_name": "LUTATHERA", "stratify_by": "sex"}),
    ("FAERS_filter_serious_events", {"drug_name": "LUTATHERA", "seriousness_type": "hospitalization"}),
    ("FAERS_analyze_temporal_trends", {"drug_name": "LUTATHERA"}),
    ("FAERS_rollup_meddra_hierarchy", {"drug_name": "LUTATHERA"}),
]


@pytest.fixture
def openfda(monkeypatch):
    """openFDA as it answers: a count for the resolved field, 404 for generic_name."""
    urls = []

    def fake_get(url, timeout=None, **_):
        urls.append(url)
        if "generic_name" in url:
            resp = types.SimpleNamespace(status_code=404)
            def boom():
                raise mod.requests.HTTPError("404 Client Error: Not Found for url: " + url)
            resp.raise_for_status = boom
            return resp
        return types.SimpleNamespace(
            status_code=200, raise_for_status=lambda: None,
            json=lambda: {"results": [{"term": "1", "count": 3000}, {"term": "2", "count": 2551}]})

    monkeypatch.setattr(mod.requests, "get", fake_get)
    monkeypatch.setattr(FAERSAnalyticsTool, "_field_total",
                        lambda self, field, term: KNOWN.get(field), raising=False)
    return urls


@pytest.mark.parametrize("tool_name,arguments", CASES)
def test_a_brand_name_is_queried_through_the_resolved_field(tool_name, arguments, openfda):
    result = FAERSAnalyticsTool(CONFIGS[tool_name]).run(arguments)

    assert result.get("status") != "error", result
    queried = [u for u in openfda if "count=" in u]
    assert queried, "no count query was made"
    assert all("patient.drug.openfda.brand_name" in u for u in queried), queried
    assert not any("generic_name" in u for u in queried), queried


def test_the_envelope_says_which_field_the_numbers_describe(openfda):
    result = FAERSAnalyticsTool(CONFIGS["FAERS_filter_serious_events"]).run(
        {"drug_name": "LUTATHERA", "seriousness_type": "death"})

    assert result["data"]["case_definition"]["resolved_field"] == "patient.drug.openfda.brand_name", result["data"]
