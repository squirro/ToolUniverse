"""A dataset that failed to load must say why it failed.

`DatasetTool._load_dataset` catches every exception, prints it to stdout, and
leaves an empty frame behind; every later call then answers

    {"status": "error", "error": "Dataset not loaded or is empty"}

which names no cause a caller could act on. It cost this audit a wrong
diagnosis: `drugbank_full_search` was read as fallout from the DSR-635 drugbank
exclusions, when the actual reason is that the served image installs no parquet
engine -- neither pyarrow nor fastparquet -- so `pd.read_parquet` raises
ImportError on the one drugbank dataset that is a .parquet. The other three are
CSVs and work.

The print went to a container log nobody reads. The message is the only surface
the caller sees, so the cause belongs in it.
"""

import pandas as pd
import pytest

from tooluniverse.dataset_tool import DatasetTool

CONFIG = {
    "name": "test_dataset_tool",
    "type": "DatasetTool",
    "query_schema": {"search_fields": ["name"], "limit": 10},
    "parameter": {"properties": {"query": {"type": "string"}}},
}


def _tool(**overrides):
    return DatasetTool({**CONFIG, **overrides})


@pytest.mark.unit
def test_a_missing_parquet_engine_is_named_in_the_error(monkeypatch, tmp_path):
    """The classifier can only book `needs_package` if the message says so."""
    path = tmp_path / "drugbank_raw.parquet"
    path.write_bytes(b"not really a parquet")

    def _no_engine(*a, **k):
        raise ImportError(
            "Unable to find a usable engine; tried using: 'pyarrow', "
            "'fastparquet'. A suitable version of pyarrow or fastparquet is "
            "required for parquet support."
        )

    monkeypatch.setattr(pd, "read_parquet", _no_engine)

    result = _tool(local_dataset_path=str(path)).run({"query": "aspirin"})

    assert result["status"] == "error"
    assert "pyarrow" in result["error"]


@pytest.mark.unit
def test_a_dataset_file_that_is_not_there_says_so(tmp_path):
    result = _tool(local_dataset_path=str(tmp_path / "absent.csv")).run({"query": "x"})

    assert result["status"] == "error"
    assert "absent.csv" in result["error"]


@pytest.mark.unit
def test_an_unreadable_format_is_reported_rather_than_silently_empty(tmp_path):
    """No branch matches, so the frame stays None; that is a config error and
    reporting it as "empty" sends the reader looking at the data instead."""
    path = tmp_path / "drugbank.rdf"
    path.write_text("<rdf/>")

    result = _tool(local_dataset_path=str(path)).run({"query": "x"})

    assert result["status"] == "error"
    assert ".rdf" in result["error"] or "format" in result["error"].lower()


@pytest.mark.unit
def test_a_dataset_that_loaded_is_searchable(tmp_path):
    """The failure path must not have swallowed the working one."""
    path = tmp_path / "drugs.csv"
    path.write_text("name,drugbank_id\naspirin,DB00945\n")

    result = _tool(local_dataset_path=str(path)).run({"query": "aspirin"})

    assert result.get("status") != "error", result
