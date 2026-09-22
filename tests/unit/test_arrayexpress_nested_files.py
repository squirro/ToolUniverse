"""BioStudies wraps `files` in a list of lists, and we only unwrapped subsections.

`arrayexpress_get_experiment_files` fetched the right study and reported zero
files for E-GEOD-26319, which has plenty. The payload nests them as

    section.subsections[].files == [[{"path": "...", "size": 843671}, ...]]

a LIST of lists. `_extract_files_from_section` walked each entry and kept it only
`if isinstance(file_obj, dict)` -- and each entry is a list, so every file was
skipped in silence.

The tell is that the same function already handles this quirk one field over,
with a comment: "Note: BioStudies subsections can be a list of lists". The shape
was known; it was applied to `subsections` and missed on `files`.

Verified live 2026-08-03: E-GEOD-26319 carries both processed-data files
(GSM646313_sample_table.txt, 843671 bytes) and MAGE-TAB files
(E-GEOD-26319.idf.txt).
"""

import pytest

from tooluniverse.arrayexpress_tool import ArrayExpressRESTTool

CONFIG = {
    "name": "arrayexpress_get_experiment_files",
    "parameter": {"properties": {"experiment_id": {"type": "string"}}},
    "fields": {},
}


def _tool():
    return ArrayExpressRESTTool(CONFIG)


@pytest.mark.unit
def test_files_wrapped_in_a_list_of_lists_are_found():
    """The real BioStudies shape, trimmed to the two files that matter."""
    section = {
        "accno": "processed-data",
        "type": "Processed Data",
        "files": [[
            {"path": "GSM646313_sample_table.txt", "size": 843671},
            {"path": "GSM646314_sample_table.txt", "size": 843112},
        ]],
    }

    files = _tool()._extract_files_from_section(section)

    names = [f["name"] for f in files]
    assert names == ["GSM646313_sample_table.txt", "GSM646314_sample_table.txt"], names
    assert files[0]["size"] == 843671, files[0]


@pytest.mark.unit
def test_a_flat_list_of_files_still_works():
    """Both shapes appear in the wild; fixing one must not break the other."""
    section = {"files": [{"path": "E-GEOD-26319.idf.txt", "size": 3440}]}

    files = _tool()._extract_files_from_section(section)

    assert [f["name"] for f in files] == ["E-GEOD-26319.idf.txt"], files


@pytest.mark.unit
def test_files_nested_under_subsections_are_reached():
    """The real payload puts them a level down, inside a list of lists too."""
    study = {
        "accno": "E-GEOD-26319",
        "subsections": [[
            {"accno": "processed-data",
             "files": [[{"path": "a.txt", "size": 1}]]},
            {"accno": "mt-E-GEOD-26319",
             "files": [[{"path": "b.idf.txt", "size": 2}]]},
        ]],
    }

    files = _tool()._extract_files_from_section(study)

    assert sorted(f["name"] for f in files) == ["a.txt", "b.idf.txt"], files


@pytest.mark.unit
def test_a_section_with_no_files_yields_nothing():
    assert _tool()._extract_files_from_section({"accno": "x", "type": "Study"}) == []


@pytest.mark.network
def test_the_real_study_reports_its_files():
    """The claim the unit tests cannot make: this experiment has files."""
    result = _tool().run({"experiment_id": "E-GEOD-26319"})

    assert result["status"] == "success", result
    assert result["count"] > 0, f"reported {result['count']} files: {result}"
    names = [f["name"] for f in result["data"]]
    assert any(n.endswith(".txt") for n in names), names
