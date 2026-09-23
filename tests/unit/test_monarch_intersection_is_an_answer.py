"""The joint-phenotype intersection answered with a bare list and lost candidates quietly.

`MonarchDiseasesForMultiplePhenoTool` takes one disease list per phenotype and intersects
them. Six things went wrong at once, and the rare-disease process uses it for **both** of
its differential steps.

It asked each phenotype for 500 rows whatever the caller wanted and threw away the
response's own `total`, so a common phenotype -- annotated on thousands of diseases -- came
back cut, and every disease past the cut silently left the intersection. It read the items
under one key name, so a 200 whose list key is renamed emptied that phenotype's set and
therefore the whole intersection. It cut the result out of a Python `set`, so which
candidates survived the caller's limit was arbitrary and the true diagnosis could be the
one dropped. It answered a bare list, carrying no status, no total and no note, so nothing
downstream could tell an answer from a failure. And an empty phenotype list raised
`IndexError` on `all_diseases[0]`.

In the other direction, `execute_RESTful_query` stamps every error envelope with
`error_details.type = "UpstreamServiceError"`, and `is_upstream_failure` matches on that
type string, so a Monarch **404** -- the source answering that nothing matches -- was
reported as the source having failed.
"""

from unittest.mock import patch

import pytest

import tooluniverse.restful_tool as mod
from tooluniverse.restful_tool import MonarchDiseasesForMultiplePhenoTool
from tooluniverse.skill_runner import is_upstream_failure

pytestmark = pytest.mark.unit

CONFIG = {
    "name": "get_joint_associated_diseases_by_HPO_ID_list",
    "type": "MonarchDiseasesForMultiplePheno",
    "tool_url": "/association",
    "parameter": {"type": "object", "properties": {}},
    "query_schema": {"category": ["biolink:DiseaseToPhenotypicFeatureAssociation"],
                     "object": None, "compact": True,
                     "object_category": ["biolink:PhenotypicFeature"],
                     "limit": 500, "offset": 0},
}


def _tool():
    return MonarchDiseasesForMultiplePhenoTool(CONFIG)


def _items(labels, total=None):
    return {"items": [{"subject_label": name} for name in labels],
            "total": len(labels) if total is None else total}


def _monarch(answers):
    """Answer each phenotype by its HPO id, in the order the tool asks."""
    def _execute(endpoint_url=None, variables=None, **kw):
        return answers[variables["object"]]
    return _execute


# ------------------------------------------------------------------ the shapes it returns

def test_an_empty_phenotype_list_is_refused_with_a_message():
    with patch.object(mod, "execute_RESTful_query", side_effect=AssertionError("no call")):
        result = _tool().run({"HPO_ID_list": [], "limit": 20})

    assert result["status"] == "error"
    assert "HPO_ID_list" in result["error"]


def test_the_intersection_carries_a_status_and_a_total():
    answers = {"HP:1": _items(["Alpha", "Beta", "Gamma"]),
               "HP:2": _items(["Beta", "Gamma", "Delta"])}

    with patch.object(mod, "execute_RESTful_query", side_effect=_monarch(answers)):
        result = _tool().run({"HPO_ID_list": ["HP:1", "HP:2"], "limit": 20})

    assert result["status"] == "success", result
    assert result["data"]["total"] == 2
    assert sorted(result["data"]["diseases"]) == ["Beta", "Gamma"]


def test_a_response_whose_item_list_is_renamed_is_an_error_not_an_empty_set():
    """A 200 with `results` where `items` was expected emptied the whole intersection."""
    answers = {"HP:1": {"results": [{"subject_label": "Alpha"}], "total": 1},
               "HP:2": _items(["Alpha"])}

    with patch.object(mod, "execute_RESTful_query", side_effect=_monarch(answers)):
        result = _tool().run({"HPO_ID_list": ["HP:1", "HP:2"], "limit": 20})

    assert result["status"] == "error", result
    assert "items" in result["error"]


# ------------------------------------------------------------------ what it does not lose

def test_the_order_is_stable_and_follows_the_first_phenotype():
    """Cutting an unordered set to a limit drops arbitrary candidates, run to run."""
    answers = {"HP:1": _items(["Alpha", "Beta", "Gamma", "Delta"]),
               "HP:2": _items(["Delta", "Gamma", "Beta", "Alpha"])}

    with patch.object(mod, "execute_RESTful_query", side_effect=_monarch(answers)):
        runs = [_tool().run({"HPO_ID_list": ["HP:1", "HP:2"], "limit": 20})["data"]["diseases"]
                for _ in range(5)]

    assert runs[0] == ["Alpha", "Beta", "Gamma", "Delta"], runs[0]
    assert all(r == runs[0] for r in runs), runs


def test_a_cut_to_the_callers_limit_states_the_full_total():
    answers = {"HP:1": _items(["Alpha", "Beta", "Gamma"]),
               "HP:2": _items(["Alpha", "Beta", "Gamma"])}

    with patch.object(mod, "execute_RESTful_query", side_effect=_monarch(answers)):
        result = _tool().run({"HPO_ID_list": ["HP:1", "HP:2"], "limit": 2})

    assert result["data"]["diseases"] == ["Alpha", "Beta"]
    assert result["data"]["total"] == 3
    assert "note" in result["data"], result["data"]


def test_a_phenotype_whose_list_the_source_cut_is_named():
    """A common phenotype is annotated on thousands of diseases; the page is not the set."""
    answers = {"HP:1": _items(["Alpha", "Beta"], total=4000),
               "HP:2": _items(["Alpha", "Beta"])}

    with patch.object(mod, "execute_RESTful_query", side_effect=_monarch(answers)):
        result = _tool().run({"HPO_ID_list": ["HP:1", "HP:2"], "limit": 20})

    cut = result["data"]["truncated_phenotypes"]
    assert [c["phenotype"] for c in cut] == ["HP:1"], cut
    assert cut[0]["source_total"] == 4000


def test_a_caller_asking_for_more_than_the_page_gets_a_bigger_page():
    asked = []

    def _execute(endpoint_url=None, variables=None, **kw):
        asked.append(variables["limit"])
        return _items(["Alpha"])

    with patch.object(mod, "execute_RESTful_query", side_effect=_execute):
        _tool().run({"HPO_ID_list": ["HP:1"], "limit": 2000})

    assert asked == [2000], asked


def test_a_failed_phenotype_still_fails_the_whole_call():
    """One list missing makes the intersection meaningless; that behaviour stays."""
    answers = {"HP:1": {"status": "error", "error": "Monarch answered HTTP 503",
                        "error_details": {"type": "UpstreamServiceError", "retriable": True}},
               "HP:2": _items(["Alpha"])}

    with patch.object(mod, "execute_RESTful_query", side_effect=_monarch(answers)):
        result = _tool().run({"HPO_ID_list": ["HP:1", "HP:2"], "limit": 20})

    assert result["status"] == "error"
    assert is_upstream_failure(result)


# ------------------------------------------------------- an answer of "nothing" is an answer

class _Response:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_a_monarch_not_found_is_not_reported_as_the_source_failing():
    """404 is Monarch answering that nothing matches. The report must not say it failed."""
    with patch.object(mod, "request_with_retry",
                      side_effect=lambda *a, **k: _Response(404, text="not found")):
        envelope = mod.execute_RESTful_query("https://api.monarchinitiative.org/x")

    assert envelope["status"] == "error"
    assert not is_upstream_failure(envelope), envelope


def test_a_monarch_outage_is_still_reported_as_the_source_failing():
    with patch.object(mod, "request_with_retry",
                      side_effect=lambda *a, **k: _Response(503, text="unavailable")):
        envelope = mod.execute_RESTful_query("https://api.monarchinitiative.org/x")

    assert is_upstream_failure(envelope), envelope
