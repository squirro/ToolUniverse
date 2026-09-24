"""Two Europe PMC searches on one cached instance each report their own total (DSR-791).

ToolUniverse keeps one instance per tool, and a Skill Process step runs its calls together on
a thread pool. The hit count was kept on the instance and read back after the search, so a
second search could overwrite the first one's count before the first one read it. The report
quotes that count as the source total.
"""

import threading

import pytest

import tooluniverse.europe_pmc_tool as mod
from tooluniverse.europe_pmc_tool import EuropePMCTool

pytestmark = pytest.mark.unit


def _page(query, hit_count, cursor):
    return {"hitCount": hit_count, "nextCursorMark": cursor,
            "resultList": {"result": [{"id": query, "source": "MED", "title": query}]}}


class _Response:
    status_code, reason = 200, "OK"

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_a_search_finishing_in_between_does_not_change_the_other_searchs_total(monkeypatch):
    a_counted, b_finished = threading.Event(), threading.Event()

    def request_with_retry(session, method, url, *, params, **kwargs):
        if params["query"] == "alpha":
            if params.get("cursorMark", "*") == "*":
                if params["resultType"] == "lite":
                    a_counted.set()          # alpha has its count; beta may start now
                return _Response(_page("alpha", 111, "next"))
            b_finished.wait(timeout=10)      # alpha's second page waits for beta to finish
            return _Response({"hitCount": 111, "resultList": {"result": []}})
        return _Response(_page("beta", 222, None))

    monkeypatch.setattr(mod, "request_with_retry", request_with_retry)
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})
    out = {}

    def search(query):
        out[query] = tool.run({"query": query, "limit": 2})
        if query == "beta":
            b_finished.set()

    alpha = threading.Thread(target=search, args=("alpha",))
    alpha.start()
    assert a_counted.wait(timeout=10)
    search("beta")
    alpha.join(timeout=10)

    assert out["beta"]["metadata"]["total"] == 222
    assert out["alpha"]["metadata"]["total"] == 111
