"""Twelve openFDA tools made every request anonymously (DSR-649).

Six modules in the image call `api.fda.gov`. `openfda_tool.py` and
`openfda_adv_tool.py` read `FDA_API_KEY`; `fda_label_tool.py`,
`fda_orange_book_tool.py` and `openfda_approval_tool.py` did not, so the 12 tools
they back shared openFDA's **anonymous 1,000 requests/day per IP** instead of the
**120,000/day** the key already in `deploy/.env` buys.

Sized by measurement rather than assumption, 2026-08-04:

* **Not a correctness fix.** Unlike the FAERS count endpoints (DSR-628), these
  search endpoints serve `limit>100` to anonymous callers perfectly well --
  `drug/label.json?limit=1000` returns all 719 aspirin labels with no key and no
  403. The key/limit coupling is specific to `count=` queries.
* **The truncation that does exist is benign.** These modules cap at
  `min(limit, 100)`, so a broad query like `openfda.generic_name:"aspirin"` (719
  labels) is cut. But that drops near-duplicate product labels off a list, not
  the tail of a distribution a statistic is computed from -- the thing that made
  the FAERS case a wrong answer rather than a short one.

So the value here is quota headroom, and the risk is that exhausting the
anonymous bucket surfaces as HTTP 429 -- indistinguishable, to the agent, from
"this tool is broken".
"""

import pytest

MODULES = [
    ("tooluniverse.fda_label_tool", "FDA_LABEL_URL"),
    ("tooluniverse.openfda_approval_tool", "FDA_DRUGSFDA_URL"),
    ("tooluniverse.fda_orange_book_tool", "FDA_BASE_URL"),
]


def _captured_params(monkeypatch, module_name, call):
    """Run `call` with requests.get stubbed, returning the params it was sent."""
    import importlib

    mod = importlib.import_module(module_name)
    seen = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"meta": {"results": {"total": 0}}, "results": []}

    def _fake_get(url, params=None, timeout=None, **kw):
        seen["params"] = params or {}
        return _Resp()

    monkeypatch.setattr(mod.requests, "get", _fake_get)
    call(mod)
    return seen.get("params", {})


@pytest.mark.unit
@pytest.mark.parametrize("module_name,_url", MODULES)
def test_the_key_is_sent_when_configured(monkeypatch, module_name, _url):
    monkeypatch.setenv("FDA_API_KEY", "TESTKEY")

    params = _captured_params(
        monkeypatch, module_name, lambda m: m.openfda_get("https://api.fda.gov/x.json",
                                                          {"search": "q", "limit": 5})
    )

    assert params.get("api_key") == "TESTKEY", params


@pytest.mark.unit
@pytest.mark.parametrize("module_name,_url", MODULES)
def test_no_key_means_no_api_key_param(monkeypatch, module_name, _url):
    """An absent key must not become the literal string "None" in the query."""
    monkeypatch.delenv("FDA_API_KEY", raising=False)

    params = _captured_params(
        monkeypatch, module_name, lambda m: m.openfda_get("https://api.fda.gov/x.json",
                                                          {"search": "q", "limit": 5})
    )

    assert "api_key" not in params, params


@pytest.mark.unit
@pytest.mark.parametrize("module_name,_url", MODULES)
def test_the_callers_own_params_survive(monkeypatch, module_name, _url):
    monkeypatch.setenv("FDA_API_KEY", "TESTKEY")

    params = _captured_params(
        monkeypatch, module_name, lambda m: m.openfda_get("https://api.fda.gov/x.json",
                                                          {"search": "aspirin", "limit": 7})
    )

    assert params["search"] == "aspirin"
    assert params["limit"] == 7
