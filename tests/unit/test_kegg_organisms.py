"""kegg_list_organisms must read the endpoint KEGG still serves, and parse it.

`/list/organism` was retired and now answers 400 with an empty body; the
organism roster lives at `/list/genome`. The two halves of this belong in one
change, because fixing only the endpoint trades a loud failure for a silent
one: `/list/genome` returns two tab-separated fields where the old endpoint
returned four, and the parser drops any line with fewer than three, so the tool
would answer HTTP 200 with zero organisms -- the `ok_empty` class this audit
exists to surface.

Format verified live 2026-08-02: 11,934 lines, every one exactly
`T01001\thsa; Homo sapiens (human)`.
"""

import pytest

from tooluniverse.kegg_tool import KEGGListOrganisms

GENOME_LIST = (
    "T01001\thsa; Homo sapiens (human)\n"
    "T01005\tptr; Pan troglodytes (chimpanzee)\n"
    "T02283\tpps; Pan paniscus (bonobo)"
)


def _tool():
    return KEGGListOrganisms({"name": "kegg_list_organisms", "parameter": {}})


@pytest.mark.unit
def test_organism_roster_is_read_from_the_endpoint_kegg_still_serves():
    """`/list/organism` answers 400; the roster moved to `/list/genome`."""
    assert _tool().endpoint == "/list/genome"


@pytest.mark.unit
def test_genome_rows_parse_into_organism_code_and_name(monkeypatch):
    """Two fields, not four: the code and name share one `code; name` column."""
    tool = _tool()
    monkeypatch.setattr(
        tool, "_make_request", lambda *a, **k: {"status": "success", "data": GENOME_LIST}
    )

    organisms = tool.run({})["data"]

    assert len(organisms) == 3
    assert organisms[0]["organism_code"] == "hsa"
    assert organisms[0]["organism_name"] == "Homo sapiens (human)"


@pytest.mark.unit
def test_a_row_without_an_organism_code_is_kept_under_its_genome_id(monkeypatch):
    """Every live row carries `code; name`, but a parser that silently drops
    what it cannot split is how a roster empties itself without saying so."""
    tool = _tool()
    monkeypatch.setattr(
        tool,
        "_make_request",
        lambda *a, **k: {"status": "success", "data": "T40001\tSome unnamed genome"},
    )

    organisms = tool.run({})["data"]

    assert len(organisms) == 1
    assert organisms[0]["genome_id"] == "T40001"
    assert organisms[0]["organism_name"] == "Some unnamed genome"
