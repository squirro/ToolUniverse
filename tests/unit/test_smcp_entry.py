"""The served process must actually have interception installed (DSR-666).

The annotation logic is worth nothing if nothing switches it on. The console script the
image runs -- ``tooluniverse-smcp`` -> ``smcp_server:run_smcp_server`` -- is an upstream
file, so rather than edit it the image points at an SR-owned entry that installs
interception first and then delegates, unchanged, to the upstream server.

Ordering is the property under test: installing *after* the server starts serving would
leave a window in which results go out unannotated.
"""

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.tools_sr import smcp_entry


@pytest.fixture(autouse=True)
def unwrapped():
    original_run = ToolUniverse.run_one_function
    original_load = ToolUniverse.load_tools
    yield
    ToolUniverse.run_one_function = original_run
    ToolUniverse.load_tools = original_load


def test_installing_wraps_the_real_tooluniverse():
    smcp_entry.install_interception()

    assert getattr(ToolUniverse.run_one_function, "_sr_transport_status", False)


def test_the_id_namespace_cue_is_installed_too():
    """DSR-662 rewrites descriptions at load, so it must be on before tools load."""
    smcp_entry.install_interception()

    assert getattr(ToolUniverse.load_tools, "_sr_id_cue", False)


def test_installing_twice_does_not_double_wrap():
    smcp_entry.install_interception()
    once = ToolUniverse.run_one_function

    smcp_entry.install_interception()

    assert ToolUniverse.run_one_function is once


def test_interception_is_installed_before_the_server_is_handed_control(monkeypatch):
    """A server that starts first would serve unannotated results until install lands."""
    installed_when_called = {}

    def fake_run_smcp_server():
        installed_when_called["value"] = getattr(
            ToolUniverse.run_one_function, "_sr_transport_status", False
        )

    monkeypatch.setattr(smcp_entry, "_run_upstream_server", fake_run_smcp_server)

    smcp_entry.main()

    assert installed_when_called["value"] is True


def test_an_annotated_invocation_still_returns_the_upstream_result():
    """Interception is additive; the unknown-tool error must survive it intact."""
    smcp_entry.install_interception()
    tu = ToolUniverse()
    tu.all_tool_dict = {"placeholder": {"name": "placeholder"}}

    result = tu.run_one_function({"name": "definitely_not_a_tool", "arguments": {}})

    assert result["status"] == "error"
