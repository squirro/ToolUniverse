"""A relative download path must land somewhere the process can actually write.

Both download tools resolve a relative `output_path` against the process
working directory. That is fine for a developer running from a home checkout
and wrong everywhere this is deployed: the SMCP image runs as a non-root uid
whose working directory is owned by root, so the tools' own declared example
(`./downloads/output.txt`) fails with

    Failed to create directory: [Errno 13] Permission denied: './downloads'
    Failed to create directory: [Errno 13] Permission denied: '/app/tu_src/downloads'

Observed for both tools in the audit baseline. The model cannot know the
container's layout, so a relative path has to resolve somewhere writable rather
than be rejected.
"""

import os
import tempfile

import pytest

from tooluniverse.file_download_tool import BinaryDownloadTool, FileDownloadTool


def _text_tool():
    return FileDownloadTool({"name": "download_file", "parameter": {}})


def _binary_tool():
    return BinaryDownloadTool({"name": "download_binary_file", "parameter": {}})


@pytest.mark.unit
@pytest.mark.parametrize("tool", [_text_tool(), _binary_tool()])
def test_a_relative_path_resolves_somewhere_writable_not_the_cwd(tool, monkeypatch):
    """`./downloads/output.txt` must not become `<cwd>/downloads/output.txt`."""
    monkeypatch.chdir("/")          # a directory this process cannot write to

    resolved = tool._normalize_path("./downloads/output.txt")

    assert resolved.startswith(tempfile.gettempdir())
    assert resolved.endswith(os.path.join("downloads", "output.txt"))


@pytest.mark.unit
@pytest.mark.parametrize("tool", [_text_tool(), _binary_tool()])
def test_an_absolute_path_is_honoured_exactly(tool):
    """The caller naming a real location is the caller's decision to keep."""
    assert tool._normalize_path("/var/data/report.pdf") == "/var/data/report.pdf"


@pytest.mark.unit
@pytest.mark.parametrize("tool", [_text_tool(), _binary_tool()])
def test_a_bare_filename_resolves_under_the_writable_base(tool, monkeypatch):
    """A filename with no directory part is the commonest relative form."""
    monkeypatch.chdir("/")

    resolved = tool._normalize_path("report.pdf")

    assert resolved == os.path.join(tempfile.gettempdir(), "report.pdf")


@pytest.mark.unit
def test_the_binary_tool_creates_its_directory_under_the_writable_base(monkeypatch):
    """The failure was in makedirs, so the resolved path must reach it."""
    monkeypatch.chdir("/")
    created = []
    monkeypatch.setattr(
        "tooluniverse.file_download_tool.os.makedirs",
        lambda path, **kw: created.append(path),
    )

    def _boom(*a, **k):
        raise RuntimeError("stop after the directory is prepared")

    monkeypatch.setattr("tooluniverse.file_download_tool.requests.get", _boom)

    _binary_tool().run(
        {"url": "https://example.org/x.bin", "output_path": "./downloads/x.bin"}
    )

    assert created, "the directory was never prepared"
    assert created[0].startswith(tempfile.gettempdir())
