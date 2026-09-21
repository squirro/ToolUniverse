"""Bgee's API needs the trailing slash, and answers 403 without it.

`BGEE_BASE_URL` was `https://www.bgee.org/api` -- no slash -- and the site
serves a Cloudflare "Just a moment..." interstitial to that path as **HTTP
403**, rather than redirecting to the slash form. A 403 reads as "blocked, or
we need a credential", which is how all three Bgee tools sat in the audit as an
access problem while the service was fine and free:

    /api?page=species&display_type=json   -> 403, text/html "Just a moment..."
    /api/?page=species&display_type=json  -> 200, {"code": 200, "status": "SUCCESS"}

The module docstring's "No authentication required. Free public access." was
true the whole time. Verified live 2026-08-03 with the *default*
python-requests User-Agent: spoofing a browser changes nothing, the slash is
the entire fault.
"""

import pytest

import tooluniverse.bgee_tool as mod
from tooluniverse.bgee_tool import BgeeTool


def _config(endpoint):
    return {
        "name": f"Bgee_{endpoint}",
        "parameter": {"properties": {}},
        "fields": {"endpoint": endpoint},
    }


class _Response:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "code": 200,
            "status": "SUCCESS",
            "data": {"species": [], "result": {"geneMatches": []}, "calls": []},
        }


@pytest.fixture
def captured(monkeypatch):
    """Record the URL Bgee would actually receive."""
    seen = {}

    def _fake_get(url, params=None, timeout=None, **kwargs):
        seen["url"] = url
        seen["params"] = params
        return _Response()

    monkeypatch.setattr(mod.requests, "get", _fake_get)
    return seen


@pytest.mark.unit
@pytest.mark.parametrize(
    "endpoint,arguments",
    [
        ("species_list", {}),
        ("gene_search", {"query": "TP53"}),
        (
            "gene_expression",
            {"gene_id": "ENSG00000141510", "species_id": "9606"},
        ),
    ],
)
def test_every_endpoint_requests_the_slash_form(captured, endpoint, arguments):
    """Without the trailing slash Cloudflare answers 403 instead of redirecting."""
    BgeeTool(_config(endpoint)).run(arguments)

    assert captured["url"].endswith("/api/"), (
        f"{endpoint} requested {captured['url']!r}; the slashless form draws a "
        "Cloudflare interstitial as HTTP 403"
    )


@pytest.mark.unit
def test_the_constant_itself_carries_the_slash():
    """Pinned so a future edit cannot quietly drop it again."""
    assert mod.BGEE_BASE_URL.endswith("/"), mod.BGEE_BASE_URL


@pytest.mark.network
@pytest.mark.parametrize(
    "endpoint,arguments",
    [
        ("species_list", {}),
        ("gene_search", {"query": "TP53"}),
        (
            "gene_expression",
            {"gene_id": "ENSG00000141510", "species_id": "9606"},
        ),
    ],
)
def test_the_real_service_answers_the_query_we_build(endpoint, arguments):
    """The claim the unit tests cannot make: Bgee returns data, unauthenticated."""
    result = BgeeTool(_config(endpoint)).run(arguments)

    assert result["status"] == "success", result
