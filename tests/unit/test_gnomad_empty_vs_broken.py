"""gnomAD: a variant it does not hold is not a failure (DSR-694).

Five failures in the 2026-08-21 skill sweep, of two different kinds, both reported
identically as errors:

* `gnomad_search_variants` handed free text — "BRCA1 c.5266dupC",
  "PTEN 10-87933148-G-A", "NM_007294.4:c.5266dup" — and gnomAD answered HTTP 500
  "Unrecognized query". The tool's description already says to search by rsID; the
  agent guessed anyway, which is the same soft-pressure plateau we measured on the
  citation rule. So the contract is enforced at the tool instead: a query that
  cannot work is refused with the accepted forms named, and never sent upstream.

* `gnomad_get_variant("10-87933148-G-A")` came back 200 with "Variant not found",
  and `gnomad_search_variants("rs104893877")` came back 200 with null data. Both
  are gnomAD answering honestly. Reporting them as errors tells the agent the
  service broke, which is false and invites a pointless retry.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _tool(config=None):
    from tooluniverse.gnomad_tool import gnomADGraphQLQueryTool

    return gnomADGraphQLQueryTool(config or {
        "name": "gnomad_search_variants",
        "type": "gnomADGraphQLQueryTool",
        "fields": {"query_schema": "query($query: String!) { variant_search { variant_id } }",
                   "variable_map": {"query": "query"}},
    })


def _graphql(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.url = "https://gnomad.broadinstitute.org/api"
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


class TestEmptyIsNotBroken(unittest.TestCase):
    def test_a_variant_gnomad_does_not_hold_is_an_empty_result(self):
        with patch("tooluniverse.gnomad_tool.requests.Session.post") as post:
            post.return_value = _graphql({"data": {"variant": None}})
            out = _tool().run({"query": "rs104893877"})
        assert out["status"] != "error", out
        assert out.get("data") in (None, {}, {"variant": None}) or out.get("empty")

    def test_variant_not_found_is_an_empty_result_not_a_failure(self):
        """gnomAD reports this as a GraphQL error at HTTP 200. It is an answer."""
        with patch("tooluniverse.gnomad_tool.requests.Session.post") as post:
            post.return_value = _graphql(
                {"errors": [{"message": "Variant not found"}], "data": None})
            out = _tool().run({"query": "10-87933148-G-A"})
        assert out["status"] != "error", out

    def test_a_real_graphql_error_is_still_an_error(self):
        with patch("tooluniverse.gnomad_tool.requests.Session.post") as post:
            post.return_value = _graphql(
                {"errors": [{"message": "Cannot query field 'nonsense'"}],
                 "data": None})
            out = _tool().run({"query": "rs7412"})
        assert out["status"] == "error", out


class TestUnusableQueriesAreRefusedLocally(unittest.TestCase):
    def test_free_text_is_refused_before_the_request_is_sent(self):
        """The 500 we saw is gnomAD rejecting garbage. Do not send it."""
        with patch("tooluniverse.gnomad_tool.requests.Session.post") as post:
            out = _tool().run({"query": "BRCA1 c.5266dupC"})
        assert out["status"] == "error", out
        assert not post.called, "an unusable query must not reach gnomAD"

    def test_the_refusal_names_the_forms_that_do_work(self):
        with patch("tooluniverse.gnomad_tool.requests.Session.post"):
            out = _tool().run({"query": "NM_007294.4:c.5266dup"})
        message = out["error"].lower()
        assert "rs" in message and "-" in message, out

    def test_an_rsid_is_accepted(self):
        with patch("tooluniverse.gnomad_tool.requests.Session.post") as post:
            post.return_value = _graphql({"data": {"variant_search": [{"variant_id": "x"}]}})
            out = _tool().run({"query": "rs7412"})
        assert out["status"] == "success", out
        assert post.called

    def test_a_variant_id_is_accepted(self):
        with patch("tooluniverse.gnomad_tool.requests.Session.post") as post:
            post.return_value = _graphql({"data": {"variant_search": [{"variant_id": "x"}]}})
            out = _tool().run({"query": "19-44908822-C-T"})
        assert out["status"] == "success", out
        assert post.called

    def test_a_tool_that_does_not_take_a_query_is_left_alone(self):
        """Only the free-text search surface is guarded — gene-constraint lookups
        and the rest must keep working exactly as before."""
        tool = _tool({"name": "gnomad_get_gene_constraints",
                      "type": "gnomADGraphQLQueryTool",
                      "fields": {"query_schema": "query { gene { symbol } }",
                                 "variable_map": {"gene_symbol": "geneSymbol"}}})
        with patch("tooluniverse.gnomad_tool.requests.Session.post") as post:
            post.return_value = _graphql({"data": {"gene": {"symbol": "BRCA1"}}})
            out = tool.run({"gene_symbol": "BRCA1"})
        assert out["status"] == "success", out


class TestShippedDefaults(unittest.TestCase):
    def test_variant_tools_default_to_the_dataset_that_holds_exomes(self):
        """Measured 2026-09-03: 10-87933148-G-A is 'Variant not found' on
        gnomad_r3 (genomes only) and present on gnomad_r4 (exomes + genomes).
        Half of the sweep's gnomAD failures were this default, not the API."""
        import json
        from pathlib import Path
        from tooluniverse import gnomad_tool

        data_dir = Path(gnomad_tool.__file__).parent / "data"
        defaults = {}
        for path in data_dir.glob("*gnomad*.json"):
            for tool in json.loads(path.read_text()):
                if tool["name"] in ("gnomad_search_variants", "gnomad_get_variant"):
                    defaults[tool["name"]] = tool["fields"]["default_variables"]["dataset"]
        assert defaults == {"gnomad_search_variants": "gnomad_r4",
                            "gnomad_get_variant": "gnomad_r4"}, defaults
