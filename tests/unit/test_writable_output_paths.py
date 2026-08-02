"""Tools that write files must resolve relative paths somewhere writable.

The deployed SMCP image runs as a non-root uid whose working directory is owned
by root, so any tool defaulting to a relative output path fails there while
working perfectly in a developer checkout. Four tools did, each with its own
copy of the mistake:

    ToolGraphComposer            Permission denied: './tool_composition_graph.json'
    ToolGraphGenerationPipeline  Permission denied: './tool_relationship_graph.json'
    download_file                Permission denied: '/app/tu_src/downloads'
    download_binary_file         Permission denied: './downloads'

The policy is shared -- relative resolves under a writable base, absolute is the
caller's decision and is honoured exactly -- but the *base* is a per-domain
choice, so it is passed in: downloads are ephemeral and belong in the temp
directory, while a generated graph is a reusable artefact and belongs in the
ToolUniverse cache directory next to the composer's own cache file.
"""

import os

import pytest

from tooluniverse.utils import get_user_cache_dir, resolve_writable_path


@pytest.mark.unit
def test_a_relative_path_resolves_under_the_given_base(monkeypatch):
    monkeypatch.chdir("/")

    assert resolve_writable_path("./out/graph.json", "/base") == "/base/out/graph.json"


@pytest.mark.unit
def test_a_bare_filename_resolves_under_the_given_base():
    assert resolve_writable_path("graph.json", "/base") == "/base/graph.json"


@pytest.mark.unit
def test_an_absolute_path_is_honoured_exactly():
    """A caller naming a real location has made a decision worth keeping."""
    assert resolve_writable_path("/var/data/graph.json", "/base") == "/var/data/graph.json"


@pytest.mark.unit
def test_user_and_variable_references_are_expanded_before_the_test_for_absolute(monkeypatch):
    monkeypatch.setenv("HOME", "/home/app")

    assert resolve_writable_path("~/graph.json", "/base") == "/home/app/graph.json"


@pytest.mark.unit
def test_the_cache_dir_honours_the_deployment_override(monkeypatch, tmp_path):
    """The image relocates writable state; the base has to follow it."""
    monkeypatch.setenv("TOOLUNIVERSE_TMPDIR", str(tmp_path))

    assert get_user_cache_dir() == str(tmp_path)
