"""ComposeTool dependency loading must not destroy the tool registry.

A ComposeTool that finds a dependency missing auto-loads it. The loading call
used to be `load_tools(tool_type=[category])`, which takes load_tools' full
reload branch -- clearing `all_tools` and `all_tool_dict` and refilling them
from that one category. Every other tool disappeared.

Served over SMCP this is severe: the registry is process-wide, so one agent
invoking one ComposeTool removed all ~2,261 tools for every client of that
container -- including the compact-mode meta-tools -- until it was restarted.
The server kept answering HTTP 200 throughout, so nothing looked wrong.

See DSR-634.
"""

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.compose_tool import ComposeTool


COMPOSE_CONFIG = {
    "type": "ComposeTool",
    "name": "RegistrySafetyProbe",
    "description": "Test fixture; never executed, only its dependency loader is.",
    "parameter": {"type": "object", "properties": {}},
    "auto_load_dependencies": True,
}


@pytest.fixture
def loaded_tu():
    """A ToolUniverse with two categories loaded.

    Two are enough to expose the defect and keep the test quick: auto-loading a
    dependency from one must not evict the other. Category names are
    case-sensitive ("ChEMBL", not "chembl") -- get one wrong and the fixture
    silently loads nothing from it, which makes the assertions pass vacuously.

    Function-scoped on purpose: the defect mutates the registry, so a shared
    instance would leave later tests asserting against already-wrecked state.
    """
    tu = ToolUniverse()
    tu.load_tools(categories=["uniprot", "ChEMBL"])
    assert any(n.startswith("ChEMBL_") for n in tu.all_tool_dict)
    assert any(n.startswith("UniProt_") for n in tu.all_tool_dict)
    return tu


@pytest.mark.unit
def test_loading_a_missing_dependency_keeps_every_other_tool(loaded_tu):
    """The registry may only grow when a dependency is auto-loaded."""
    before = dict(loaded_tu.all_tool_dict)
    assert len(before) > 1, "fixture did not load a usable registry"

    # Pick a real tool to stand in for a missing dependency. What matters is
    # that it maps to a category, which is what triggers the auto-load path.
    dependency = next(
        name for name in before if name.startswith("UniProt_")
    )

    compose = ComposeTool(COMPOSE_CONFIG, tooluniverse=loaded_tu)
    compose._load_missing_dependencies({dependency})

    after = loaded_tu.all_tool_dict
    lost = set(before) - set(after)
    assert not lost, (
        f"auto-loading '{dependency}' dropped {len(lost)} of {len(before)} tools "
        f"from the registry, e.g. {sorted(lost)[:5]}"
    )


@pytest.mark.unit
def test_dependency_load_does_not_strand_tools_from_other_categories(loaded_tu):
    """Tools outside the dependency's category must survive the load.

    Stated separately from the count check because a same-size registry made of
    entirely different tools would still break every in-flight caller.
    """
    chembl_before = {n for n in loaded_tu.all_tool_dict if n.startswith("ChEMBL_")}
    assert chembl_before, "fixture did not load the second category"

    dependency = next(
        name for name in loaded_tu.all_tool_dict if name.startswith("UniProt_")
    )
    compose = ComposeTool(COMPOSE_CONFIG, tooluniverse=loaded_tu)
    compose._load_missing_dependencies({dependency})

    chembl_after = {n for n in loaded_tu.all_tool_dict if n.startswith("ChEMBL_")}
    assert chembl_before <= chembl_after, (
        "loading a uniprot dependency removed ChEMBL tools: "
        f"{sorted(chembl_before - chembl_after)[:5]}"
    )
