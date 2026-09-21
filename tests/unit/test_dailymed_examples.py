"""A DailyMed parse tool's own example must be a label that has the section.

Four of these were recorded as silent empty successes -- HTTP 200, zero rows,
no explanation -- and none of them was broken. The shipped example pointed at
`030d9bca-a934-6ef9-e063-6394a90a8277`, an OTC monograph label whose sections
are ACTIVE INGREDIENT, PURPOSE, INDICATIONS & USAGE and WARNINGS. Adverse
reactions, contraindications, drug interactions and clinical pharmacology are
prescription-label sections, so an OTC label cannot contain them and the tools
were correctly returning nothing.

The example is now a prescription label (atorvastatin, Teva) carrying all six
sections the family parses. Measured on the switch: four tools went from empty
to 915-20,366 characters of real content.

Marked `network` because the claim is about what upstream holds; the default
suite deselects it. Run with:

    pytest tests/unit/test_dailymed_examples.py -o addopts="" -m network
"""

import glob
import json
import os

import pytest

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "data")
PARSERS = [
    "DailyMed_parse_adverse_reactions",
    "DailyMed_parse_clinical_pharmacology",
    "DailyMed_parse_contraindications",
    "DailyMed_parse_dosing",
    "DailyMed_parse_drug_interactions",
]
OTC_LABEL = "030d9bca-a934-6ef9-e063-6394a90a8277"


def _tools():
    out = {}
    for path in glob.glob(os.path.join(DATA, "*.json")):
        try:
            defs = json.load(open(path))
        except Exception:
            continue
        if isinstance(defs, list):
            for tool in defs:
                if isinstance(tool, dict) and tool.get("name"):
                    out.setdefault(tool["name"], tool)
    return out


TOOLS = _tools()


@pytest.mark.unit
@pytest.mark.parametrize("name", PARSERS)
def test_the_example_is_not_the_otc_label_that_has_no_such_section(name):
    """Cheap, offline guard against the exact regression, by id."""
    examples = json.dumps(TOOLS[name].get("test_examples") or [])
    assert OTC_LABEL not in examples, (
        f"{name}'s example is the OTC monograph label, which has no "
        f"prescription sections; the tool will answer empty and look broken"
    )


@pytest.mark.network
@pytest.mark.parametrize("name", PARSERS)
def test_the_declared_example_actually_returns_content(name):
    """The claim the offline test cannot make: the section is really there."""
    from tooluniverse.execute_function import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools()
    example = (TOOLS[name].get("test_examples") or [{}])[0]

    result = tu.run({"name": name, "arguments": example})

    assert result, f"{name} returned nothing for its own example"
    payload = json.dumps(result, default=str)
    assert len(payload) > 300, f"{name} returned an all-but-empty payload: {payload[:200]}"
