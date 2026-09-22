"""A malformed argument killed the whole turn instead of degrading to an error.

DSR-627 ask 2. An agent that had already failed a dozen ChEMBL calls started
flailing at the argument shape, and the turn died with a user-visible
"An error has occurred while processing your request".

~20 adversarial MCP calls showed TU never lets an exception reach the transport:
there are five nested catch-alls, and an *executed-and-failed* tool always comes
back `isError: false` with a proper envelope -- which is why the agent degrades
gracefully for ordinary failures. Three calls behave differently:

    execute_tool{tool_name:"X", arguments:[1,2,3]}  -> isError:true, pydantic string
    execute_tool{}                                  -> isError:true, "Missing required argument"
    tools/call on an unregistered name              -> isError:true, "Unknown tool"

FastMCP's own client SDK raises on `isError` by default, so if Squirro's client
shares that default, `isError: true` IS the turn-killer.

The first two never reach TU code at all: FastMCP validates against the tool's
JSON schema first, and `execute_tool` declared `arguments` as object-or-string
with `tool_name` required. A list fails that constraint, and pydantic's message
goes back as `isError: true` before the handler runs.

The handler, meanwhile, was ALREADY written to handle every one of these cases
and return a clean `{"status": "error", "error_type": "ValidationError"}`
envelope. So the containment fix is to stop the schema from rejecting the call
first, and let the handler answer -- which turns a dead session into a tool
observation the model can read and correct.

This does not weaken validation: it moves it from a layer that raises to a layer
that explains.
"""

import glob
import json
import pathlib

import pytest

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


@pytest.mark.unit
def test_a_wrongly_typed_arguments_value_reaches_the_handler():
    """`arguments` must not be constrained to object|string at the schema layer.

    A list is genuinely malformed -- the point is that the HANDLER should say so,
    because a schema rejection becomes isError:true and kills the turn.
    """
    params = _execute_tool_schema()["parameter"]["properties"]["arguments"]

    assert "oneOf" not in params, (
        "a oneOf constraint rejects a list before TU can explain it: " f"{params}"
    )


@pytest.mark.unit
def test_a_missing_tool_name_reaches_the_handler():
    """`execute_tool{}` must be answerable, not a validation error."""
    schema = _execute_tool_schema()["parameter"]

    assert "tool_name" not in schema.get("required", []), (
        "tool_name in `required` makes execute_tool{} a schema rejection "
        "(isError:true) rather than the handler's readable envelope"
    )


@pytest.mark.unit
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

    return ExecuteToolTool(
        {"name": "execute_tool", "type": "ExecuteTool"}, tooluniverse=_StubUniverse()
    )


@pytest.mark.unit
def test_the_handler_explains_a_list_instead_of_raising():
    result = _tool().run({"tool_name": "ChEMBL_search_targets", "arguments": [1, 2, 3]})

    assert result["status"] == "error"
    assert result["error_type"] == "ValidationError"
    assert "list" in result["error"]


@pytest.mark.unit
def test_the_handler_explains_a_missing_tool_name_instead_of_raising():
    result = _tool().run({})

    assert result["status"] == "error"
    assert result["error_type"] == "ValidationError"
    assert "tool_name" in result["error"]


# --- find_tools had the same shape: a legitimate call answering nothing useful ---


@pytest.mark.unit
@pytest.mark.parametrize(
    "method,advanced",
    [
        ("auto", False),   # the reported case: falls through to an implicit None
        ("auto", True),
        ("keyword", False),
        ("llm", False),    # Tool_Finder_LLM is excluded from the image
        ("embedding", False),
        ("nonsense", True),
    ],
)
def test_a_search_tool_is_always_selected(method, advanced):
    """`_select_search_tool` returned None for auto+advanced=False.

    The `auto` branch had no `else`, so the function fell off the end and the
    caller reported "Missing or empty function name" -- a legitimate-looking call
    that answers nothing and invites exactly the retry loop DSR-627 is about.
    `use_advanced_search` is an exposed parameter, so a model can trip it.
    """
    from tooluniverse.smcp import SMCP

    chosen = SMCP._select_search_tool(_SearchStub(), method, advanced)

    assert chosen, f"no tool selected for search_method={method!r}, advanced={advanced}"


class _SearchStub:
    """Only `_select_search_tool`'s view of the universe: the loaded tool names."""

    class _TU:
        @staticmethod
        def return_all_loaded_tools():
            return [{"name": "Tool_Finder_Keyword"}]

    tooluniverse = _TU()


# --- an unconstrained property must actually be unconstrained (DSR-627 follow-up) ---
# Removing the oneOf was meant to stop the schema layer rejecting a malformed call. It did
# the opposite: _resolve_param_type read a missing `type` as "string", so `arguments`
# accepted only a string and rejected the dict form its own description documents. Every
# tool is reached through execute_tool, so a local sweep had 2,186 of 2,194 tools failing
# with one identical pydantic error.


@pytest.mark.unit
def test_a_property_with_no_declared_type_accepts_any_type():
    """JSON Schema: an absent `type` permits any type. The resolver must agree."""
    from typing import Any

    from tooluniverse.smcp import SMCP

    python_type, _ = SMCP._resolve_param_type({"description": "anything at all"})

    assert python_type is Any, python_type


@pytest.mark.unit
def test_the_execute_tool_arguments_property_is_not_narrowed_to_a_string():
    """The regression itself, pinned against the shipped schema rather than a fixture."""
    from tooluniverse.smcp import SMCP

    arguments = _execute_tool_schema()["parameter"]["properties"]["arguments"]

    python_type, _ = SMCP._resolve_param_type(arguments)

    assert python_type is not str, (
        "arguments resolved to str, so a dict is rejected before the handler sees it; "
        f"schema was {arguments}"
    )


@pytest.mark.unit
def test_a_declared_type_is_still_honoured():
    """The relaxation must not leak into properties that do declare a type."""
    from tooluniverse.smcp import SMCP

    assert SMCP._resolve_param_type({"type": "string"})[0] is str
    assert SMCP._resolve_param_type({"type": "object"})[0] is dict
