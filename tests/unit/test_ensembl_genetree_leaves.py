"""Ensembl gene-tree leaves carry `taxonomy`, not `species`, so none were collected.

`EnsemblCompara_get_gene_tree` fetched BRCA1's tree successfully -- 391 KB, 206
leaves -- and reported `{"tree_id": null, "newick": null, "members": [],
"total_members": 0}`. Three mismatches against the real payload:

* `_collect_members` recognised a leaf by `"id" in node and "species" in node`.
  Leaves have `id`, `sequence`, `taxonomy`, `confidence`, `branch_length` and no
  `species` key at all, so the condition never held and every one of the 206 was
  skipped.
* the species name lives at `taxonomy.scientific_name`;
* `tree_id` was read from `tree.id`, but the tree id is at the TOP level
  (`ENSGT00440000034289`) while `tree.id` does not exist -- `tree` holds
  `taxonomy`, `branch_length`, `events`, `confidence`, `children`.

Verified live 2026-08-03. `newick` stays null by design: asking for JSON returns a
nested structure rather than a Newick string, and the tool does not request the
`nh` format.

Shapes below are trimmed from the real response, including a genuine leaf
(Salvator merianae, the Argentine black and white tegu) to keep the nesting
honest.
"""

import pytest

from tooluniverse.ensembl_compara_tool import EnsemblComparaTool

CONFIG = {
    "name": "EnsemblCompara_get_gene_tree",
    "parameter": {"properties": {}},
    "fields": {"endpoint": "gene_tree"},
}

LEAF = {
    "id": {"source": "EnsEMBL", "accession": "ENSSMRG00000007896"},
    "taxonomy": {"scientific_name": "Salvator merianae",
                 "common_name": "Argentine black and white tegu", "id": 96440},
    "sequence": {"name": "BRCA1-201",
                 "id": [{"accession": "ENSSMRP00000009940", "source": "EnsEMBL"}]},
    "confidence": {}, "branch_length": 0.1,
}
HUMAN_LEAF = {
    "id": {"source": "EnsEMBL", "accession": "ENSG00000012048"},
    "taxonomy": {"scientific_name": "Homo sapiens", "id": 9606},
    "sequence": {"name": "BRCA1-201"},
}
TREE = {
    "type": "gene tree", "rooted": 1, "id": "ENSGT00440000034289",
    "tree": {
        "taxonomy": {"scientific_name": "Amniota"}, "branch_length": 0,
        "events": {"type": "speciation"}, "confidence": {},
        "children": [LEAF, {"taxonomy": {}, "children": [HUMAN_LEAF]}],
    },
}


@pytest.mark.unit
def test_leaves_are_collected_from_taxonomy_not_a_species_key():
    members = []
    EnsemblComparaTool(CONFIG)._collect_members(TREE["tree"], members)

    assert len(members) == 2, f"expected both leaves, got {members}"
    species = {m["species"] for m in members}
    assert species == {"Salvator merianae", "Homo sapiens"}, species
    ids = {m["gene_id"] for m in members}
    assert ids == {"ENSSMRG00000007896", "ENSG00000012048"}, ids


@pytest.mark.unit
def test_internal_nodes_are_not_counted_as_members():
    """Only leaves are members; an ancestor with children is not a gene."""
    members = []
    EnsemblComparaTool(CONFIG)._collect_members(
        {"taxonomy": {"scientific_name": "Amniota"}, "children": []}, members
    )

    assert members == [], members


@pytest.mark.unit
def test_the_tree_id_is_read_from_the_top_level(monkeypatch):
    """`tree.id` does not exist; the id sits beside `tree`."""
    import tooluniverse.ensembl_compara_tool as mod

    class _Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return TREE

    monkeypatch.setattr(mod.requests, "get",
                        lambda *a, **k: _Response())

    result = EnsemblComparaTool(CONFIG).run({"gene": "BRCA1", "species": "human"})

    assert result["status"] == "success", result
    assert result["data"]["tree_id"] == "ENSGT00440000034289", result["data"]
    assert result["data"]["total_members"] == 2, result["data"]


@pytest.mark.network
def test_the_real_brca1_tree_has_members():
    """The claim the unit tests cannot make: this tree is large and we read it."""
    result = EnsemblComparaTool(CONFIG).run({"gene": "BRCA1", "species": "human"})

    assert result["status"] == "success", result
    data = result["data"]
    assert data["tree_id"], data
    assert data["total_members"] > 50, f"only {data['total_members']} members"
    species = {m["species"] for m in data["members"]}
    assert any("Homo" in s for s in species) or len(species) > 10, species
