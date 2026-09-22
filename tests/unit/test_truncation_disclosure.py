"""A capped result must never be presented as a complete one (DSR-660).

Two paired guards. One reads the source for functions that take the first N of a
collection without mentioning a total or a truncation. One reads the registry for tools
that accept a limit but declare no companion total, so they could not disclose a cap even
if they wanted to. The reference is FAERS, whose invariant is the one worth remembering:
a full page is evidence of truncation, not of completeness. Both counts are frozen rather
than fixed, because the population is upstream code that re-syncs from mims-harvard:main.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.tools_sr import truncation

ROOT = Path(truncation.__file__).resolve().parents[1]
DATA = ROOT / "data"
BASELINE = json.loads((ROOT / "tools_sr" / "truncation_baseline.json").read_text())


def _registry(tmp_path, entry):
    (tmp_path / "some_tools.json").write_text(json.dumps([entry]))
    return truncation.tools_without_a_total(tmp_path)


# --- the ratchets ---


def test_undisclosed_caps_have_not_increased():
    findings = truncation.undisclosed_slices(ROOT)

    assert len(findings) <= BASELINE["undisclosed_slicing_functions"], (
        f"{len(findings)} undisclosed caps, baseline "
        f"{BASELINE['undisclosed_slicing_functions']}:\n"
        + "\n".join(f.message for f in findings[-10:])
    )


def test_tools_accepting_a_limit_without_a_total_have_not_increased():
    findings = truncation.tools_without_a_total(DATA)

    assert len(findings) <= BASELINE["tools_accepting_a_limit_without_a_total"], (
        f"{len(findings)} against baseline "
        f"{BASELINE['tools_accepting_a_limit_without_a_total']}:\n"
        + "\n".join(f.message for f in findings[-10:])
    )


# --- proof the source guard can fail ---


def test_a_newly_added_undisclosed_cap_is_found(tmp_path):
    (tmp_path / "new_tool.py").write_text(
        "def search(rows, limit):\n"
        "    return rows[:limit]\n"
    )

    findings = truncation.undisclosed_slices(tmp_path)

    assert len(findings) == 1, [f.message for f in findings]
    assert findings[0].function == "search"


def test_a_cap_that_discloses_is_not_reported(tmp_path):
    """Modelled on the FAERS note: say the list was cut and give the whole size."""
    (tmp_path / "good_tool.py").write_text(
        "def search(rows, limit):\n"
        "    page = rows[:limit]\n"
        "    return {'rows': page, 'total_count': len(rows),\n"
        "            'truncated': len(rows) > limit}\n"
    )

    assert truncation.undisclosed_slices(tmp_path) == []


def test_the_faers_reference_implementation_passes():
    """Named in the ticket as the implementation to verify against."""
    faers = [f for f in truncation.undisclosed_slices(ROOT) if "faers" in str(f.path)]

    assert faers == [], [f.message for f in faers]


# --- proof the registry guard can fail ---


def test_a_tool_accepting_a_limit_with_no_total_is_reported(tmp_path):
    findings = _registry(tmp_path, {
        "name": "Thing_search",
        "type": "RESTTool",
        "parameter": {"properties": {"query": {}, "limit": {}}},
        "return_schema": {"properties": {"rows": {}}},
    })

    assert len(findings) == 1
    assert findings[0].name == "Thing_search"
    assert findings[0].limits == ["limit"]


@pytest.mark.parametrize("entry", [
    # declares a total alongside the limit
    {"name": "Thing_search", "type": "RESTTool",
     "parameter": {"properties": {"query": {}, "limit": {}}},
     "return_schema": {"properties": {"rows": {}, "total_count": {}}}},
    # takes no limit at all, so it has nothing to disclose
    {"name": "Thing_get", "type": "RESTTool",
     "parameter": {"properties": {"identifier": {}}},
     "return_schema": {"properties": {"row": {}}}},
])
def test_a_tool_with_nothing_to_disclose_is_not_reported(tmp_path, entry):
    assert _registry(tmp_path, entry) == []


# --- the vocabulary is observed, not invented ---


def test_every_disclosure_term_actually_occurs_in_the_corpus():
    """A term nobody writes is a term the guard invented, and inventing them is how a
    rule starts reporting compliant code."""
    text = "\n".join(path.read_text(errors="ignore").lower() for path in ROOT.rglob("*.py"))
    for term in truncation.DISCLOSURE_TERMS:
        assert term in text, term


def test_remaining_is_deliberately_absent_from_the_vocabulary():
    """It reads like the obvious word and occurs in zero slicing functions here."""
    assert "remaining" not in truncation.DISCLOSURE_TERMS


# --- the reports name their offenders ---


def test_each_slice_finding_names_the_file_line_and_function():
    findings = truncation.undisclosed_slices(ROOT)

    assert findings
    sample = findings[0]
    assert str(sample.path).endswith(".py")
    assert sample.line > 0
    assert sample.function
    assert "caps a result" in sample.message


def test_each_tool_finding_names_the_tool_its_file_and_the_limit():
    findings = truncation.tools_without_a_total(DATA)

    assert findings
    sample = findings[0]
    assert sample.name and sample.source.endswith(".json") and sample.limits
    assert sample.name in sample.message
