"""A malformed argument killed the whole turn instead of degrading to an error (DSR-627).

~20 adversarial MCP calls showed TU never lets an exception reach the transport: an
executed-and-failed tool always comes back `isError: false` with a proper envelope. Three
calls behaved differently -- `arguments` as a list, `execute_tool{}`, and an unregistered
name -- and FastMCP's own client SDK raises on `isError` by default, so `isError: true` IS
the turn-killer. The first two never reached TU code at all: FastMCP validates against the
JSON schema first, and `execute_tool` declared `arguments` as object-or-string with
`tool_name` required. The handler was ALREADY written to answer every one of these with a
clean `{"status": "error", "error_type": "ValidationError"}` envelope, so the containment
fix is to stop the schema rejecting the call first and let the handler explain. This does
not weaken validation: it moves it from a layer that raises to a layer that explains.
"""

import glob
import json
import pathlib

import pytest

from tooluniverse.smcp import SMCP

pytestmark = pytest.mark.unit

DATA = pathlib.Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _execute_tool_schema():
    for path in glob.glob(str(DATA / "*.json")):
        try:
            entries = json.load(open(path))
        except Exception:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("name") == "execute_tool":
                return entry
    raise AssertionError("execute_tool not found in data/")


def test_a_wrongly_typed_arguments_value_reaches_the_handler():
    """A list is genuinely malformed -- the point is that the HANDLER should say so,
    because a schema rejection becomes isError:true and kills the turn."""
    params = _execute_tool_schema()["parameter"]["properties"]["arguments"]

    assert "oneOf" not in params, (
        f"a oneOf constraint rejects a list before TU can explain it: {params}")


def test_a_missing_tool_name_reaches_the_handler():
    """`execute_tool{}` must be answerable, not a validation error."""
    schema = _execute_tool_schema()["parameter"]

    assert "tool_name" not in schema.get("required", []), (
        "tool_name in `required` makes execute_tool{} a schema rejection "
        "(isError:true) rather than the handler's readable envelope")


def test_the_description_still_states_what_arguments_should_be():
    """Relaxing the schema must not lose the guidance -- the model reads this."""
    params = _execute_tool_schema()["parameter"]["properties"]

    assert "object" in params["arguments"]["description"].lower()
    assert "required" in params["tool_name"]["description"].lower()


# --- the handler's own answers, pinned so the schema change stays safe ---


class _StubUniverse:
    """Stands in for ToolUniverse so validation is reached without loading tools."""

    def return_all_loaded_tools(self):
        return []


def _tool():
    from tooluniverse.tool_discovery_tools import ExecuteToolTool

    return ExecuteToolTool({"name": "execute_tool", "type": "ExecuteTool"},
                           tooluniverse=_StubUniverse())


@pytest.mark.parametrize("arguments,named", [
    ({"tool_name": "ChEMBL_search_targets", "arguments": [1, 2, 3]}, "list"),
    ({}, "tool_name"),
])
def test_the_handler_explains_instead_of_raising(arguments, named):
    result = _tool().run(arguments)

    assert result["status"] == "error"
    assert result["error_type"] == "ValidationError"
    assert named in result["error"]


# --- find_tools had the same shape: a legitimate call answering nothing useful ---


class _SearchStub:
    """Only `_select_search_tool`'s view of the universe: the loaded tool names."""

    class _TU:
        @staticmethod
        def return_all_loaded_tools():
            return [{"name": "Tool_Finder_Keyword"}]

    tooluniverse = _TU()


@pytest.mark.parametrize("method,advanced", [
    ("auto", False),   # the reported case: falls through to an implicit None
    ("auto", True),
    ("keyword", False),
    ("llm", False),    # Tool_Finder_LLM is excluded from the image
    ("embedding", False),
    ("nonsense", True),
])
def test_a_search_tool_is_always_selected(method, advanced):
    """The `auto` branch had no `else`, so `_select_search_tool` fell off the end and the
    caller reported "Missing or empty function name" -- a legitimate-looking call that
    answers nothing. `use_advanced_search` is exposed, so a model can trip it."""
    chosen = SMCP._select_search_tool(_SearchStub(), method, advanced)

    assert chosen, f"no tool selected for search_method={method!r}, advanced={advanced}"


# --- an unconstrained property must actually be unconstrained (DSR-627 follow-up) ---
# Removing the oneOf was meant to stop the schema layer rejecting a malformed call. It did
# the opposite: _resolve_param_type read a missing `type` as "string", so `arguments`
# accepted only a string and rejected the dict form its own description documents. Every
# tool is reached through execute_tool, so a local sweep had 2,186 of 2,194 tools failing
# with one identical pydantic error.


def test_a_property_with_no_declared_type_accepts_any_type():
    """JSON Schema: an absent `type` permits any type. The resolver must agree."""
    from typing import Any

    python_type, _ = SMCP._resolve_param_type({"description": "anything at all"})

    assert python_type is Any, python_type


def test_the_execute_tool_arguments_property_is_not_narrowed_to_a_string():
    """The regression itself, pinned against the shipped schema rather than a fixture."""
    arguments = _execute_tool_schema()["parameter"]["properties"]["arguments"]

    python_type, _ = SMCP._resolve_param_type(arguments)

    assert python_type is not str, (
        "arguments resolved to str, so a dict is rejected before the handler sees it; "
        f"schema was {arguments}")


def test_a_declared_type_is_still_honoured():
    """The relaxation must not leak into properties that do declare a type."""
    assert SMCP._resolve_param_type({"type": "string"})[0] is str
    assert SMCP._resolve_param_type({"type": "object"})[0] is dict
