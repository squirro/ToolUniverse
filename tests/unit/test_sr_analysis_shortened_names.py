"""An SR analysis tool must answer to the name it is served under.

`ClinicalTrials_search_by_intervention_and_condition` is 51 characters. MCP
shortens anything past the cap, so the tool is advertised -- and its config is
built -- as `ClinicalTrials_sear_by_inte_and_cond`. The dispatch map is keyed on
the full name, so the lookup missed and the tool rejected a call made under its
own advertised name:

    {"error": "SR analysis tool 'ClinicalTrials_sear_by_inte_and_cond' not
     supported", "available_tools": [... the full names ...]}

The error even lists the full name it wants, one line below the short one it was
given, which is what makes it read like a missing tool rather than a name that
did not survive the transport.

Matching on the shortened form rather than adding an alias keeps this working
for any future name over the cap.
"""

import pytest

from tooluniverse.sr_analysis_tool import SRAnalysisTool
from tooluniverse.tool_name_utils import shorten_tool_name

FULL = "ClinicalTrials_search_by_intervention_and_condition"


def _tool(name):
    return SRAnalysisTool({"name": name, "parameter": {"properties": {}}})


@pytest.mark.unit
def test_the_name_really_is_shortened_past_the_cap():
    """Pin the premise, so the rule below reads as its consequence."""
    assert len(FULL) > 45
    assert shorten_tool_name(FULL, 45) != FULL


@pytest.mark.unit
def test_the_shortened_name_dispatches(monkeypatch):
    """The call arrives under the advertised name, and must be routed."""
    seen = {}

    def _fake_exec(arguments, input_table, output_table, db_path):
        seen["called"] = True
        return []

    import tooluniverse.sr_analysis_tool as mod
    monkeypatch.setitem(mod._DISPATCH, FULL, _fake_exec)

    result = _tool(shorten_tool_name(FULL, 45)).run(
        {"intervention": "terbium-161", "condition": "prostate cancer"}
    )

    assert seen.get("called"), f"not dispatched: {result}"


@pytest.mark.unit
def test_a_genuinely_unknown_name_is_still_rejected():
    """Resolving short names must not turn every typo into a silent match."""
    result = _tool("No_Such_SR_Tool_At_All").run({})

    assert "not supported" in str(result.get("error", ""))
