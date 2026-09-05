"""The shared tool registry must survive a partial load.

ToolUniverse holds one registry per process, and SMCP serves every MCP client
from that one object. So a call that empties it does not affect only its own
caller -- it removes every tool, for every client, until the container is
restarted. DSR-634 is that failure, observed in production through a ComposeTool.
"""
import pytest

from tooluniverse import ToolUniverse


@pytest.mark.unit
def test_a_category_load_keeps_the_tools_already_loaded():
    """Loading one category must add to the registry, not replace it.

    load_tools() with no selection is a documented full reload and may clear.
    Naming a category is a request for that category to be present, which is
    not a request for everything else to be destroyed.
    """
    tu = ToolUniverse()
    tu.load_tools(categories=["uniprot"])
    first = set(tu.all_tool_dict)
    assert first, "fixture is meaningless if the first load found nothing"

    tu.load_tools(categories=["output_summarization"])
    after = set(tu.all_tool_dict)

    lost = first - after
    assert not lost, (
        f"loading 'output_summarization' evicted {len(lost)} uniprot tools "
        f"from the shared registry, e.g. {sorted(lost)[:3]}"
    )


@pytest.mark.unit
def test_an_explicit_full_reload_still_clears():
    """The anti-duplicate behaviour of a bare load_tools() is preserved."""
    tu = ToolUniverse()
    tu.load_tools(categories=["uniprot"])
    tu.load_tools()
    names = list(tu.all_tool_dict)
    assert len(names) == len(set(names)), "a full reload duplicated tool names"
