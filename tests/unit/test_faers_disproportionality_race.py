"""FAERS disproportionality: the resolved drug field must not ride on `self`.

Observed live (DSR-693): the tool returned a NEGATIVE contingency cell and then
refused to compute — `a=31, b=-31` and `a=52, b=-52`, always exactly `-a`, which
means the drug-only count came back 0 while the drug+event count did not. That is
arithmetically impossible for one drug in one population.

It reproduces only under concurrency. `_calculate_disproportionality` resolved the
drug's field once and stashed it on the instance, and `_get_faers_count` read it
back off the instance later. ToolUniverse hands out ONE cached instance per tool
name (`_get_tool_instance(..., cache=True)`), so a second disproportionality call
for a different drug overwrites that field between the `a` query and the `b`
query. The first call then counts its drug under the second drug's field, matches
nothing, and gets 0.

The fix is to pass the field explicitly. These tests hold that line without any
network: they assert the field reaches the query, and that instance state cannot
change it.
"""

import re
import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

BRAND = "patient.drug.openfda.brand_name"
GENERIC = "patient.drug.openfda.generic_name"


def _make_tool():
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    return FAERSAnalyticsTool({"name": "x", "description": "x", "parameter": {}})


def _response(total):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"meta": {"results": {"total": total}}}
    resp.raise_for_status.return_value = None
    return resp


class TestResolvedFieldIsExplicit(unittest.TestCase):
    def test_the_count_query_uses_the_field_it_was_given(self):
        tool = _make_tool()
        with patch("tooluniverse.faers_analytics_tool.requests.get") as get:
            get.return_value = _response(5683)
            tool._get_faers_count("lutetium lu-177 dotatate", None, field=BRAND)
        url = get.call_args[0][0]
        assert BRAND in url, url

    def test_instance_state_cannot_override_the_field_it_was_given(self):
        """The race in one assertion: another call has just stashed a different
        field on the shared instance, and this call must ignore it."""
        tool = _make_tool()
        tool._resolved_drug_field = BRAND          # a concurrent call's leftovers
        with patch("tooluniverse.faers_analytics_tool.requests.get") as get:
            get.return_value = _response(5683)
            tool._get_faers_count("lutetium lu-177 dotatate", None, field=GENERIC)
        url = get.call_args[0][0]
        assert GENERIC in url, url
        assert BRAND not in url, url

    def test_both_drug_queries_of_one_calculation_use_the_same_field(self):
        """`a` and `b` must describe the same population, or `b` goes negative."""
        tool = _make_tool()
        with patch("tooluniverse.faers_analytics_tool.requests.get") as get:
            get.return_value = _response(100)
            with patch.object(tool, "_resolve_drug_field",
                              return_value=(BRAND, 100)):
                tool._calculate_disproportionality(
                    {"drug_name": "d", "adverse_event": "e"})
        drug_urls = [c[0][0] for c in get.call_args_list
                     if re.search(r"patient\.drug", c[0][0])]
        assert drug_urls, "no drug query was issued"
        assert all(BRAND in u for u in drug_urls), drug_urls


class TestImpossibleCountsAreNamed(unittest.TestCase):
    def test_a_drug_total_below_the_joint_count_is_reported_as_inconsistent(self):
        """Belt and braces: if the counts ever disagree again, the envelope must
        say the two queries disagreed — never emit a negative cell."""
        tool = _make_tool()
        totals = iter([52, 0, 1000, 20_000_000])   # a, drug-only, event-only, total
        with patch("tooluniverse.faers_analytics_tool.requests.get") as get:
            get.side_effect = lambda *a, **k: _response(next(totals))
            with patch.object(tool, "_resolve_drug_field",
                              return_value=(GENERIC, 52)):
                out = tool._calculate_disproportionality(
                    {"drug_name": "d", "adverse_event": "e"})
        assert out["status"] == "error"
        assert "inconsistent" in out["error"].lower(), out["error"]
        assert not any(v < 0 for v in out.get("contingency_table", {}).values()), out
