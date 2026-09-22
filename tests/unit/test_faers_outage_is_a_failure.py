"""A FAERS analytics outage must carry the typed details a run reads as a failure.

`status: "error"` alone is not enough: the run tells a failed source from a source with
nothing to say by the upstream status and the typed error details. Without them a 5xx or
a read timeout was indistinguishable from a real answer of zero.
"""

import json
import pathlib

import pytest
import requests

import tooluniverse.faers_analytics_tool as mod
from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool
from tooluniverse.skill_runner import is_upstream_failure

pytestmark = pytest.mark.unit


def _shipped_config():
    root = pathlib.Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
    for path in root.glob("*.json"):
        try:
            entries = json.loads(path.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("type") == "FAERSAnalyticsTool":
                return entry
    raise AssertionError("no FAERSAnalyticsTool config found")


class _Response:
    status_code = 503
    text = "upstream is unavailable"

    def raise_for_status(self):
        raise requests.exceptions.HTTPError("503 Server Error", response=self)

    def json(self):
        return {}


@pytest.mark.parametrize("operation,arguments", [
    ("calculate_disproportionality", {"drug_name": "Lutathera", "adverse_event": "nausea"}),
    ("stratify_by_demographics", {"drug_name": "Lutathera", "stratify_by": "sex"}),
    ("filter_serious_events", {"drug_name": "Lutathera", "seriousness_type": "death"}),
])
@pytest.mark.parametrize("failure", ["timeout", "server_error"])
def test_an_outage_is_reported_as_an_upstream_failure(monkeypatch, operation, arguments, failure):
    def get(*a, **k):
        if failure == "timeout":
            raise requests.exceptions.ReadTimeout("read timed out")
        return _Response()

    monkeypatch.setattr(mod.requests, "get", get)

    answer = FAERSAnalyticsTool(_shipped_config()).run({"operation": operation, **arguments})

    assert is_upstream_failure(answer), answer
