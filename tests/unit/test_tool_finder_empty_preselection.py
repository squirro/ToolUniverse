"""An empty preselection must mean "search", not "return nothing".

`find_tools` branches on `if picked_tool_names is None:` to decide whether to
run a search. An empty LIST is not None, so passing `picked_tool_names: []` --
the natural way to say "I have no preselection", and the value shipped in all
three finders' own `test_examples` -- skips the search entirely and returns
zero tools with no error.

That is the worst possible place for a silent empty result: this is the
discovery path. Under `--compact-mode` the agent sees five meta-tools and
reaches the other ~2,100 through `find_tools`, so a finder that answers `[]`
makes the entire registry look empty. All three finders booked as `ok_empty` or
`error` in the audit for exactly this reason.

Measured against the live registry: `{"description": "gene expression
analysis", "limit": 3}` returns 3 tools, and adding `"picked_tool_names": []`
returns 0.
"""

import pytest

from tooluniverse.tool_finder_keyword import ToolFinderKeyword


class _Registry:
    """Just enough ToolUniverse for find_tools to run."""

    def __init__(self):
        self.asked_for = None

    def get_tool_specification_by_names(self, names):
        self.asked_for = list(names)
        return [{"name": n} for n in names]

    def prepare_tool_prompts(self, specs):
        return specs

    def refresh_tool_name_desc(self, *a, **k):
        return [], []


def _finder(monkeypatch, search_returns=("Alpha_tool", "Beta_tool")):
    tool = ToolFinderKeyword.__new__(ToolFinderKeyword)   # skip index building
    tool.tooluniverse = _Registry()
    tool.exclude_tools = []
    searched = []

    def _search(payload):
        searched.append(payload)
        import json as _json
        return _json.dumps({"tools": [{"name": n} for n in search_returns]})

    monkeypatch.setattr(tool, "_run_json_search", _search, raising=False)
    return tool, searched


@pytest.mark.unit
def test_an_empty_preselection_still_searches(monkeypatch):
    """The regression: [] is not None, so the search was being skipped."""
    tool, searched = _finder(monkeypatch)

    tool.find_tools(message="gene expression analysis", picked_tool_names=[], rag_num=3)

    assert searched, "no search ran: an empty list was treated as a preselection"
    assert tool.tooluniverse.asked_for == ["Alpha_tool", "Beta_tool"]


@pytest.mark.unit
def test_omitting_the_preselection_searches_as_before(monkeypatch):
    """The path that already worked must keep working."""
    tool, searched = _finder(monkeypatch)

    tool.find_tools(message="gene expression analysis", rag_num=3)

    assert searched
    assert tool.tooluniverse.asked_for == ["Alpha_tool", "Beta_tool"]


@pytest.mark.unit
def test_a_real_preselection_is_honoured_without_searching(monkeypatch):
    """A caller naming tools has already chosen; do not second-guess it."""
    tool, searched = _finder(monkeypatch)

    tool.find_tools(picked_tool_names=["ChEMBL_search_targets"], rag_num=3)

    assert not searched, "a real preselection must not trigger a search"
    assert tool.tooluniverse.asked_for == ["ChEMBL_search_targets"]
