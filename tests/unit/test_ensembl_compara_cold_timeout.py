"""Ensembl computes homology on the cold path, and it takes longer than 30s.

The default timeout was 30s. Ensembl's /homology endpoints answer a query they
have not seen in 41-85s, then serve the identical query from cache in 0.2s:

    BRCA1 orthologues, cold  -> 200 in 41.1s   (measured in-container)
    the same query, warm     -> 200 in  0.2s   (x5 consecutive)
    TP53 paralogues, cold    -> 200 in 39.4s
    BRCA1 orthologues, cold  -> 200 in 84.5s   (measured from the host)

So every FIRST query for a gene failed and every repeat succeeded, which is the
worst possible shape: the audit recorded these tools as working because earlier
sweeps had warmed exactly the examples it re-probed, while a real agent asking a
novel question always pays the cold path. Verified 2026-08-03; the wrapper's own
request shape (format=condensed) is not the cause -- it is fast once warm and
slow once cold, like every other form of the query.

90s is the floor these tests defend, chosen to clear the slowest cold response
observed (84.5s) rather than the fastest.
"""

import pytest

import tooluniverse.ensembl_compara_tool as mod
from tooluniverse.ensembl_compara_tool import EnsemblComparaTool

# The slowest cold response measured, in seconds. A default at or below this
# turns Ensembl's cold path into a tool failure.
SLOWEST_COLD_RESPONSE = 84.5


def _config(endpoint, **extra):
    cfg = {
        "name": f"EnsemblCompara_get_{endpoint}",
        "parameter": {"properties": {}},
        "fields": {"endpoint": endpoint},
    }
    cfg.update(extra)
    return cfg


@pytest.mark.unit
@pytest.mark.parametrize("endpoint", ["orthologues", "paralogues", "gene_tree"])
def test_the_default_timeout_clears_the_cold_path(endpoint):
    """A 30s default made the first query for any gene fail."""
    tool = EnsemblComparaTool(_config(endpoint))

    assert tool.timeout > SLOWEST_COLD_RESPONSE, (
        f"default timeout is {tool.timeout}s, but a cold Ensembl homology query "
        f"has been measured at {SLOWEST_COLD_RESPONSE}s"
    )


@pytest.mark.unit
def test_an_explicit_timeout_still_wins():
    """The default is a floor for the cold path, not a policy override."""
    assert EnsemblComparaTool(_config("orthologues", timeout=5)).timeout == 5


@pytest.mark.unit
def test_the_configured_timeout_reaches_the_request(monkeypatch):
    """A default nothing passes to requests.get would fix nothing."""
    seen = {}

    class _Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": []}

    def _fake_get(url, params=None, headers=None, timeout=None, **kwargs):
        seen["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(mod.requests, "get", _fake_get)

    tool = EnsemblComparaTool(_config("orthologues"))
    tool.run({"gene": "BRCA1", "target_species": "mouse"})

    assert seen["timeout"] == tool.timeout, seen
    assert seen["timeout"] > SLOWEST_COLD_RESPONSE, seen
