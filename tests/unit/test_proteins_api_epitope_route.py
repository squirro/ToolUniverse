"""The Proteins API epitope route exists; we were asking for the wrong path.

`proteins_api_get_epitopes` requested `/proteins/{accession}/epitopes`, which
404s, then fell back to scraping epitope mentions out of the main protein entry's
comments and features -- finding none for P04637 and reporting success with zero
rows. Its own description said so outright: "the separate epitopes endpoint is
not available".

It is available, under a different path and in the singular:

    /proteins/api/proteins/P04637/epitopes -> 404
    /proteins/api/epitope/P04637           -> 200, 56 KB, 62 EPITOPE features
                                              with IEDB cross-references

Verified live 2026-08-03. This is what a silent zero-row looks like once the
wrapper has *documented* its own bug as an upstream limitation: nothing errors,
the note explains the emptiness plausibly, and the tool reads as healthy.

Two surfaces had to change, because `_build_url` prefers the config's endpoint
template and only falls back to the per-tool branch in code -- fixing either
alone leaves the other wrong for the next caller. The extractor needed nothing:
it already keeps features whose type contains "epitope".
"""

import json
import pathlib

import pytest

from tooluniverse.proteins_api_tool import ProteinsAPIRESTTool

CONFIG_FILE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src" / "tooluniverse" / "data" / "proteins_api_tools.json"
)


def _shipped_config(name):
    entries = [t for t in json.loads(CONFIG_FILE.read_text())
               if t.get("name") == name]
    assert len(entries) == 1, f"expected one {name}, found {len(entries)}"
    return entries[0]


@pytest.mark.unit
def test_the_shipped_config_points_at_the_singular_epitope_route():
    """This is the surface that actually runs: the template wins over the code."""
    endpoint = _shipped_config("proteins_api_get_epitopes")["fields"]["endpoint"]

    assert endpoint.endswith("/epitope/{accession}"), (
        f"config endpoint is {endpoint!r}; /proteins/{{accession}}/epitopes "
        "answers 404 and sends the tool into a fallback that finds nothing"
    )


@pytest.mark.unit
def test_the_url_built_from_that_config_is_the_working_one():
    url = ProteinsAPIRESTTool(_shipped_config("proteins_api_get_epitopes"))._build_url(
        {"accession": "P04637"}
    )

    assert url == "https://www.ebi.ac.uk/proteins/api/epitope/P04637", url


@pytest.mark.unit
def test_the_code_fallback_agrees_with_the_config():
    """Reached when a caller supplies no endpoint template, so it must not
    disagree -- a fixed config plus a stale fallback is the same bug waiting."""
    cfg = dict(_shipped_config("proteins_api_get_epitopes"))
    cfg["fields"] = {}

    url = ProteinsAPIRESTTool(cfg)._build_url({"accession": "P04637"})

    assert url.endswith("/epitope/P04637"), url


@pytest.mark.unit
def test_the_description_no_longer_claims_the_endpoint_is_missing():
    """The false claim is why nobody re-checked this for a whole campaign."""
    description = _shipped_config("proteins_api_get_epitopes")["description"]

    assert "not available" not in description.lower(), description


@pytest.mark.network
def test_the_real_route_returns_epitope_features():
    """The claim the unit tests cannot make: P04637 has epitopes, and we get them.

    Asserted on the outcome rather than a container shape. On the correct route
    the API's own payload comes back whole -- accession, sequence and the feature
    list -- instead of the filtered list the old fallback assembled, so pinning
    "data is a list of features" would have pinned the bug's shape.
    """
    result = ProteinsAPIRESTTool(_shipped_config("proteins_api_get_epitopes")).run(
        {"accession": "P04637"}
    )

    assert result["status"] == "success", result
    payload = result["data"]
    features = payload.get("features") if isinstance(payload, dict) else payload
    assert features, f"expected EPITOPE features for P04637, got {payload!r}"

    kinds = {str(f.get("type", "")).upper() for f in features if isinstance(f, dict)}
    assert "EPITOPE" in kinds, kinds
    # The point of the fix: this is a real number, not zero.
    epitopes = [f for f in features
                if str(f.get("type", "")).upper() == "EPITOPE"]
    assert len(epitopes) > 10, f"only {len(epitopes)} epitopes; expected dozens"
