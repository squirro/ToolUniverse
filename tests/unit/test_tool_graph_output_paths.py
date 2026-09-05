"""The two tool-graph writers must not default to the working directory.

Both computed their graph correctly and then failed on the write, as the
non-root uid the SMCP image runs under:

    ToolGraphComposer            Permission denied: './tool_composition_graph.json'
    ToolGraphGenerationPipeline  Failed to write output: [Errno 13] Permission
                                 denied: './tool_relationship_graph.json'

The second is the sharper loss -- its result payload carried the finished graph
alongside the error, so the work was done and then thrown away.

A generated graph is a reusable artefact, and the composer already keeps its
cache there, so the base is the ToolUniverse cache directory.
"""

import json
import os

import pytest

from tooluniverse.compose_scripts.tool_graph_composer import _save_graph
from tooluniverse.compose_scripts.tool_graph_generation import compose

ONE_TOOL = [{"type": "SampleTool", "name": "ExampleTool", "description": "example"}]


@pytest.mark.unit
def test_the_composer_saves_a_relative_path_under_the_cache_dir(monkeypatch, tmp_path):
    """The base is deliberately one that does not exist yet: a fresh container
    has never written a cache directory, and resolving into a missing one just
    moves the failure."""
    base = tmp_path / "cache"
    monkeypatch.setenv("TOOLUNIVERSE_TMPDIR", str(base))
    monkeypatch.chdir("/")

    files = _save_graph({"nodes": [], "edges": []}, "./tool_composition_graph")

    assert files["json"] == str(base / "tool_composition_graph.json")
    assert os.path.exists(files["json"])


@pytest.mark.unit
def test_the_generation_pipeline_writes_its_graph_under_the_cache_dir(monkeypatch, tmp_path):
    """One tool config means no pairs to evaluate, so this reaches the write
    without an LLM -- the same shape the audit probe sent."""
    base = tmp_path / "cache"
    monkeypatch.setenv("TOOLUNIVERSE_TMPDIR", str(base))
    monkeypatch.chdir("/")

    result = compose({"tool_configs": ONE_TOOL}, tooluniverse=None, call_tool=None)

    assert result["status"] == "success", result
    assert result["output_file"] == str(base / "tool_relationship_graph.json")
    assert json.loads((base / "tool_relationship_graph.json").read_text())["nodes"]


@pytest.mark.unit
def test_an_absolute_output_path_is_still_honoured(monkeypatch, tmp_path):
    """Resolving relative paths must not take the choice away from a caller
    that made one."""
    monkeypatch.setenv("TOOLUNIVERSE_TMPDIR", "/nonexistent-cache")
    wanted = tmp_path / "chosen" / "graph.json"
    os.makedirs(wanted.parent)

    result = compose(
        {"tool_configs": ONE_TOOL, "output_path": str(wanted)},
        tooluniverse=None,
        call_tool=None,
    )

    assert result["output_file"] == str(wanted)
    assert wanted.exists()
