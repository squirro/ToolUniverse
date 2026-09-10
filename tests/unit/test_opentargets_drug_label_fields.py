"""OpenTargets' drug label fields became objects; the vendored queries did not.

`synonyms` and `tradeNames` on the `Drug` type are now
`[DrugLabelAndSource!]!` -- each entry carries a `label` and the `source` that
supplied it -- where they used to be plain string lists. A GraphQL query that
selects an object field without a sub-selection is invalid, so the server
rejects the whole query and the wrapper reports the least useful thing it could:

    {"status": "error", "error": "No data returned from API"}

Three tools, one drift. `OpenTargets_get_drug_description_by_chemblId` kept
working throughout, which is what made this look like a per-tool fault rather
than a schema change.

This is the recurring OpenTargets failure mode: the vendored `query_schema`
falls behind the live schema, and the symptom never names the field. The live
test below is the guard, and it covers every OpenTarget query rather than only
the three that broke this time.
"""

import json
import re

import pytest

DATA = "src/tooluniverse/data/opentarget_tools.json"
LABEL_FIELDS = ("synonyms", "tradeNames")


def _tools():
    import os
    here = os.path.dirname(__file__)
    path = os.path.join(here, "..", "..", *DATA.split("/"))
    return [t for t in json.load(open(path)) if t.get("query_schema")]


@pytest.mark.unit
def test_no_query_selects_a_drug_label_field_as_a_scalar():
    """`synonyms` needs `{ label source }`; without it the query is invalid."""
    offenders = []
    for tool in _tools():
        query = tool["query_schema"]
        for field in LABEL_FIELDS:
            # the field name NOT followed by an opening brace
            if re.search(rf"\b{field}\b\s*(?!\{{)", query) and not re.search(
                rf"\b{field}\b\s*\{{", query
            ):
                offenders.append(f"{tool['name']} selects {field} as a scalar")
    assert not offenders, (
        "these queries are invalid against the live schema, and the wrapper "
        "will report only 'No data returned from API': " + "; ".join(offenders)
    )


@pytest.mark.network
def test_every_vendored_query_still_validates_against_the_live_schema():
    """The general guard: drift is caught by name, not as an empty result."""
    import urllib.request

    URL = "https://api.platform.opentargets.org/api/v4/graphql"
    broken = []
    for tool in _tools():
        payload = json.dumps({"query": tool["query_schema"], "variables": {}}).encode()
        request = urllib.request.Request(
            URL, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read())
        except Exception as exc:  # HTTPError carries the GraphQL errors too
            try:
                body = json.loads(exc.read())
            except Exception:
                continue                      # transport trouble is not drift
        for error in body.get("errors", []):
            text = error.get("message", "")
            # Missing variables are expected here; a bad FIELD is the defect.
            if "must have a sub selection" in text or "Cannot query field" in text:
                broken.append(f"{tool['name']}: {text[:90]}")
    assert not broken, "vendored queries no longer match the schema:\n" + "\n".join(broken)
