"""An openFDA outage must read as a failure, never as a drug with no adverse events.

The count tool answered a transport error with a one-row list whose only key was
`error`. Post-processing turned that into a zero count, and the run recorded an empty
reaction list with no failure, so the report stated the drug had no adverse events.
"""

import json
import pathlib

import pytest
import requests

import tooluniverse.openfda_adv_tool as mod
from tooluniverse.openfda_adv_tool import FDADrugAdverseEventTool
from tooluniverse.skill_runner import is_upstream_failure

pytestmark = pytest.mark.unit


def _shipped_config():
    root = pathlib.Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
    for entry in json.loads((root / "fda_drug_adverse_event_tools.json").read_text()):
        if entry.get("name") == "FAERS_count_reactions_by_drug_event":
            return entry
    raise AssertionError("FAERS_count_reactions_by_drug_event not found")


class _Response:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = "upstream is unavailable"

    def raise_for_status(self):
        raise requests.exceptions.HTTPError(f"{self.status_code} Server Error", response=self)

    def json(self):
        return {}


@pytest.mark.parametrize("raiser", [
    lambda *a, **k: (_ for _ in ()).throw(requests.exceptions.ConnectTimeout("timed out")),
    lambda *a, **k: _Response(503),
])
def test_a_transport_failure_is_reported_as_an_upstream_failure(monkeypatch, raiser):
    monkeypatch.setattr(mod.requests, "get", raiser)

    answer = FDADrugAdverseEventTool(_shipped_config()).run({"medicinalproduct": "cisplatin"})

    assert is_upstream_failure(answer), answer


def test_a_transport_failure_does_not_become_a_zero_count(monkeypatch):
    monkeypatch.setattr(
        mod.requests, "get",
        lambda *a, **k: (_ for _ in ()).throw(requests.exceptions.ConnectTimeout("timed out")))

    answer = FDADrugAdverseEventTool(_shipped_config()).run({"medicinalproduct": "cisplatin"})

    assert "result" not in answer, "a failed call must not present rows"
    assert json.dumps(answer).count('"count": 0') == 0
