"""The chemical-probes tool asks only for fields the live Open Targets schema has.

Open Targets dropped `probeMinerScore` from `ChemicalProbe`; a query that still names it
is refused whole with HTTP 400, so the tool returned no probes for any target.
"""

import json
import re
from pathlib import Path

import pytest

import tooluniverse.graphql_tool as mod
from tooluniverse.graphql_tool import OpentargetTool

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "opentargets"
# The live schema's answer for the type, and the tool's query answered live for EGFR.
FIELDS = {f["name"] for f in json.loads(
    (FIXTURES / "chemical_probe_fields_2026-09-24.json").read_text())["data"]["__type"]["fields"]}
EGFR_TEXT = (FIXTURES / "egfr_chemical_probes_2026-09-24.json").read_text()

CONFIGS = json.loads((Path(mod.__file__).parent / "data" / "opentarget_tools.json").read_text())
CONFIG = next(t for t in CONFIGS if t["name"] == "OpenTargets_get_chemical_probes_by_target_ensemblID")


def _asked(query):
    """The scalar fields the query selects on a chemical probe."""
    body = re.search(r"chemicalProbes\s*{(.*)}\s*}\s*}", query, re.S).group(1)
    body = re.sub(r"{[^{}]*}", "", body)                # drop the nested selections
    return set(re.findall(r"\w+", body))


class _Answer:
    def __init__(self, status, text):
        self.status_code, self.text, self.ok = status, text, status < 400

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def source(monkeypatch):
    """The live source's rule: a field the type lacks refuses the whole query."""
    def post(url, json=None, timeout=None):
        unknown = sorted(_asked(json["query"]) - FIELDS)
        if unknown:
            return _Answer(400, '{"errors":[{"message":"Cannot query field '
                           f"'{unknown[0]}' on type 'ChemicalProbe'.\"}}]}}")
        return _Answer(200, EGFR_TEXT)

    monkeypatch.setattr(mod.requests, "post", post)


def test_the_query_asks_only_for_fields_the_live_schema_has():
    assert _asked(CONFIG["query_schema"]) <= FIELDS


def test_the_tool_returns_the_probes_the_source_holds_for_a_target_that_has_some(source):
    out = OpentargetTool(CONFIG).run({"ensemblId": "ENSG00000146648"})
    assert out.get("status") != "error", out.get("error")

    served = json.loads(EGFR_TEXT)["data"]["target"]["chemicalProbes"]
    probes = out["data"]["target"]["chemicalProbes"]
    assert [p["id"] for p in probes] == [p["id"] for p in served] and len(probes) == 12
    assert {"id", "isHighQuality", "probesDrugsScore"} <= set(probes[0])
