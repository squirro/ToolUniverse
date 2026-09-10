"""ensembl_get_homology hits the same slow endpoint EnsemblCompara_* does.

Fixed alongside the EnsemblCompara default (see
test_ensembl_compara_cold_timeout.py): Ensembl computes homology for a query it
has not served before, and /homology answers in 29-85s cold against a 30s
default:

    /homology/symbol/human/TP53   (this tool's shape) -> 200 in 28.9s, 372 KB
    /homology/symbol/human/BRCA1  (condensed)         -> 200 in 41.1s cold
    the same BRCA1 query                              -> 200 in 84.5s from the host

28.9s against a 30s ceiling is a coin flip, which is why this tool alternated
between ok_data and a timeout across sweeps.

Unlike EnsemblComparaTool -- whose three tools ALL query homology, so its module
default moved -- EnsemblRESTTool serves many fast Ensembl endpoints. Raising its
default would make every one of them wait 120s before reporting a genuinely dead
endpoint, so the timeout goes on this tool's own config entry, using the
mechanism the class already documents ("Allow per-tool timeout override via JSON
config") and the convention its neighbours already follow (ensembl_get_genetree
and ensembl_vep_region both carry an explicit timeout).
"""

import json
from pathlib import Path

import pytest

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "ensembl_tools.json"
)

# The slowest cold /homology response measured, in seconds.
SLOWEST_COLD_RESPONSE = 84.5


def _entries():
    return json.loads(CONFIG.read_text())


def _entry(name):
    matches = [t for t in _entries() if t.get("name") == name]
    # json.load keeps only the LAST duplicate key, so a second block for the same
    # tool would silently shadow the first; assert there is exactly one.
    assert len(matches) == 1, f"expected exactly one {name} entry, found {len(matches)}"
    return matches[0]


@pytest.mark.unit
def test_the_homology_tool_declares_a_timeout_past_the_cold_path():
    timeout = _entry("ensembl_get_homology").get("timeout")

    assert timeout is not None, (
        "no timeout on ensembl_get_homology, so it inherits the class default of "
        "30s -- below the 28.9s-85s cold path of /homology"
    )
    assert timeout > SLOWEST_COLD_RESPONSE, (
        f"timeout is {timeout}s; a cold /homology query has been measured at "
        f"{SLOWEST_COLD_RESPONSE}s"
    )


@pytest.mark.unit
def test_the_fast_endpoints_keep_the_lean_default():
    """The point of a per-tool timeout is NOT to slow everything else down."""
    slow = [
        t["name"]
        for t in _entries()
        if isinstance(t.get("timeout"), int) and t["timeout"] > SLOWEST_COLD_RESPONSE
    ]

    assert slow == ["ensembl_get_homology"], (
        f"only the measured-slow endpoint should carry a >{SLOWEST_COLD_RESPONSE}s "
        f"timeout, but these do: {slow}"
    )


@pytest.mark.unit
def test_the_config_still_parses_and_is_unduplicated():
    """A hand-edited JSON payload is easy to corrupt; prove it survived."""
    entries = _entries()
    names = [t.get("name") for t in entries if t.get("name")]

    assert len(names) == len(set(names)), "duplicate tool names in ensembl_tools.json"
    # 21 as measured, not as a guess: a hand edit that drops an entry or opens a
    # second block for the same tool changes this, and json.load would otherwise
    # keep only the last duplicate silently.
    assert len(entries) == 21, f"{len(entries)} entries, expected 21"
