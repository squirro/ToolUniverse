"""Tool_Finder must say what is missing, not name an attribute.

The served image installs plain `.`, not `.[embedding]`, on purpose: the
embedding finder pulls sentence-transformers plus a ~1.5 B model that OOMs the
host. `ToolFinderEmbedding.__init__` handles that by catching the ImportError
and setting `_dependencies_available = False` -- but the attribute assignment it
skips on the way (`self.tooluniverse`, set only inside
`load_tool_desc_embedding`) leaves the object half-built, and the audit saw:

    'ToolFinderEmbedding' object has no attribute 'tooluniverse'

which sends a reader looking for a registry bug rather than a missing extra.
There is already a good message behind `_dependencies_available`; the object
just has to survive long enough to reach it.

Two independent guarantees, because either alone still fails in the image:
the constructor keeps the registry it was handed, and a call without the extra
reports the package.
"""

import pytest

from tooluniverse.tool_finder_embedding import ToolFinderEmbedding

CONFIG = {
    "name": "Tool_Finder",
    "type": "ToolFinderEmbedding",
    "parameter": {"properties": {}},
    "configs": {"tool_finder_model": "not-a-real-model"},
}


class _Registry:
    all_tools = []
    all_tool_dict = {}

    def get_tool_specification_by_names(self, names):
        return [{"name": n} for n in names]

    def prepare_tool_prompts(self, specs):
        return specs

    def refresh_tool_name_desc(self, *a, **k):
        return [], []


@pytest.fixture
def without_extra(monkeypatch):
    """Reproduce the image: the embedding stack is not installed."""
    def _boom(*a, **k):
        raise ImportError("No module named 'sentence_transformers'")

    monkeypatch.setattr(ToolFinderEmbedding, "load_rag_model", _boom, raising=False)


@pytest.mark.unit
def test_the_registry_survives_a_missing_embedding_extra(without_extra):
    """__init__ is handed the registry; dropping it is what produced the
    AttributeError three layers away."""
    with pytest.warns(UserWarning):
        finder = ToolFinderEmbedding(CONFIG, _Registry())

    assert getattr(finder, "tooluniverse", None) is not None


@pytest.mark.unit
def test_a_call_without_the_extra_names_the_package(without_extra):
    """The failure a user sees must be actionable, not an attribute name."""
    with pytest.warns(UserWarning):
        finder = ToolFinderEmbedding(CONFIG, _Registry())

    with pytest.raises(ImportError) as caught:
        finder.find_tools(message="gene expression analysis", picked_tool_names=[])

    assert "embedding" in str(caught.value)
