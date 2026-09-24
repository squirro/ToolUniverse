"""Open Targets no longer serves target enabling packages: the tool says so plainly.

The live Target type has no `tep` field and no other type holds the packages (schema read
2026-09-24), so the query is refused whole. A raw 400 reads as an outage to retry.
"""

import json
import re
from pathlib import Path

import pytest

import tooluniverse.graphql_tool as mod
from tooluniverse.graphql_tool import OpentargetTool

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "opentargets"
# The live schema's answer for the Target type.
TARGET_FIELDS = {f["name"] for f in json.loads(
    (FIXTURES / "target_fields_2026-09-24.json").read_text())["data"]["__type"]["fields"]}

CONFIGS = json.loads((Path(mod.__file__).parent / "data" / "opentarget_tools.json").read_text())
CONFIG = next(t for t in CONFIGS if t["name"] == "OpenTargets_get_target_enabling_packages_by_ensemblID")


@pytest.fixture
def source(monkeypatch):
    """The live source's rule: a field the Target type lacks refuses the whole query."""
    sent = []

    class Answer:
        status_code, ok = 400, False
        text = '{"errors":[{"message":"Cannot query field \'tep\' on type \'Target\'."}]}'

        def json(self):
            return json.loads(self.text)

    def post(url, json=None, timeout=None):
        sent.append(json)
        return Answer()

    monkeypatch.setattr(mod.requests, "post", post)
    return sent


def test_the_live_target_type_has_no_enabling_packages():
    assert "tep" not in TARGET_FIELDS
    assert re.search(r"\btep\s*{", CONFIG["query_schema"])


def test_the_tool_says_the_source_no_longer_serves_them_without_asking_it(source):
    out = OpentargetTool(CONFIG).run({"ensemblId": "ENSG00000141510"})

    assert out["status"] == "error"
    assert "no longer serves target enabling packages" in out["error"]
    assert "2026-09-24" in out["error"]
    assert out["retryable"] is False
    assert source == [], "a query the schema refuses is not sent"


def test_the_description_steers_the_agent_away():
    assert "no longer serves target enabling packages" in CONFIG["description"]
