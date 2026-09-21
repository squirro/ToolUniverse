"""The embedding stores must not write to the process working directory.

All five embedding tools ship `"data_dir": "./data/embeddings"` in their
`storage_config`, and the constructor does `Path(that).mkdir(...)`. Under the
served image -- non-root uid 10001, working directory owned by root -- every one
of them fails before it does any work:

    Failed to initialize tool for validation: [Errno 13] Permission denied: 'data'

This is the fifth instance of one defect: a relative path resolved against a
working directory that is writable in a developer checkout and not in the
container. `download_file`, `download_binary_file`, `ToolGraphComposer` and
`ToolGraphGenerationPipeline` were the other four, and they share the fix.

The class default is already correct (`get_user_cache_dir()/embeddings`); it is
the shipped config that overrides it with a relative path, so the resolution has
to happen where the config is read.
"""

import os

import pytest

from tooluniverse.database_setup.embedding_database import EmbeddingDatabase
from tooluniverse.database_setup.embedding_sync import EmbeddingSync
from tooluniverse.utils import get_user_cache_dir

SHIPPED = {"storage_config": {"data_dir": "./data/embeddings",
                              "faiss_index_type": "IndexFlatIP"}}


def _config(configs):
    return {"name": "embedding_test", "type": "EmbeddingDatabase",
            "parameter": {"properties": {}}, "configs": configs}


@pytest.mark.parametrize("cls", [EmbeddingDatabase, EmbeddingSync])
@pytest.mark.unit
def test_the_shipped_relative_data_dir_lands_in_the_cache_dir(cls, monkeypatch, tmp_path):
    monkeypatch.setenv("TOOLUNIVERSE_TMPDIR", str(tmp_path))
    monkeypatch.chdir("/")                     # as unwritable as the container's

    tool = cls(_config(SHIPPED))

    assert str(tool.data_dir).startswith(str(tmp_path)), tool.data_dir
    assert tool.data_dir.is_dir()


@pytest.mark.parametrize("cls", [EmbeddingDatabase, EmbeddingSync])
@pytest.mark.unit
def test_an_absolute_data_dir_is_honoured(cls, monkeypatch, tmp_path):
    monkeypatch.setenv("TOOLUNIVERSE_TMPDIR", "/nonexistent-cache")
    wanted = tmp_path / "chosen"

    tool = cls(_config({"storage_config": {"data_dir": str(wanted)}}))

    assert tool.data_dir == wanted


@pytest.mark.parametrize("cls", [EmbeddingDatabase, EmbeddingSync])
@pytest.mark.unit
def test_no_configured_dir_still_defaults_to_the_cache_dir(cls, monkeypatch, tmp_path):
    """The pre-existing default was already right; it must stay right."""
    monkeypatch.setenv("TOOLUNIVERSE_TMPDIR", str(tmp_path))
    monkeypatch.chdir("/")

    tool = cls(_config({}))

    assert tool.data_dir == tmp_path / "embeddings"
