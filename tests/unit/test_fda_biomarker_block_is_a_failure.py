"""fda.gov refusing us must read as a failed source, not as a drug with no biomarkers.

Recorded 2026-09-24 from sr-dev. From the host, Akamai answers 403 "Access Denied".
From inside the container, `requests` is redirected to an "abuse-detection-apology"
page that itself answers 404, so the error read "404 Not Found" -- which a run takes
for "nothing there", an answer. A 200 page with no biomarker table is the same refusal
in a third shape: it parsed to zero rows and was reported as a success.
"""

import pytest

import tooluniverse.fda_pharmacogenomic_biomarkers_tool as mod
from tooluniverse.fda_pharmacogenomic_biomarkers_tool import (
    FDAPharmacogenomicBiomarkersTool,
)
from tooluniverse.skill_runner import is_upstream_failure

pytestmark = pytest.mark.unit

AKAMAI_403 = """<HTML><HEAD>
<TITLE>Access Denied</TITLE>
</HEAD><BODY>
<H1>Access Denied</H1>

You don't have permission to access "http&#58;&#47;&#47;www&#46;fda&#46;gov&#47;drugs&#47;science&#45;and&#45;research&#45;drugs&#47;table&#45;pharmacogenomic&#45;biomarkers&#45;drug&#45;labeling" on this server.<P>
Reference&#32;&#35;18&#46;6ee22517&#46;1790270155&#46;1715098b
<P>https&#58;&#47;&#47;errors&#46;edgesuite&#46;net&#47;18&#46;6ee22517&#46;1790270155&#46;1715098b</P>
</BODY>
</HTML>
"""

APOLOGY_URL = "https://www.fda.gov/apology_objects/abuse-detection-apology.html"

TABLE = """<html><body><table>
<thead><tr><th>Drug</th><th>Therapeutic Area*</th><th>Biomarker†</th>
<th>Labeling Sections</th></tr></thead>
<tbody><tr><td>Abacavir</td><td>Infectious Diseases</td><td>HLA-B</td>
<td>Boxed Warning</td></tr></tbody></table></body></html>"""


class _Response:
    def __init__(self, status_code, text, url=FDAPharmacogenomicBiomarkersTool.FDA_URL):
        self.status_code = status_code
        self.text = text
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.exceptions.HTTPError(
                f"{self.status_code} Client Error: for url: {self.url}", response=self
            )


def _run(monkeypatch, response, arguments=None):
    monkeypatch.setattr(mod.requests, "get", lambda *a, **k: response)
    return FDAPharmacogenomicBiomarkersTool({"name": "x"}).run(arguments or {"drug_name": "abacavir"})


def test_an_akamai_403_is_a_failed_source(monkeypatch):
    result = _run(monkeypatch, _Response(403, AKAMAI_403))

    assert is_upstream_failure(result), result
    assert result["upstream_status"] == 403
    assert "refuses automated" in result["error"]


def test_the_apology_redirect_is_a_failed_source_not_a_missing_page(monkeypatch):
    result = _run(monkeypatch, _Response(404, "Not found\n", url=APOLOGY_URL))

    assert is_upstream_failure(result), result
    assert "refuses automated" in result["error"]


def test_a_page_without_the_table_is_a_failure_not_zero_rows(monkeypatch):
    result = _run(monkeypatch, _Response(200, "<html><body>Please wait</body></html>"))

    assert is_upstream_failure(result), result


def test_a_drug_the_table_does_not_list_is_still_an_answer(monkeypatch):
    result = _run(monkeypatch, _Response(200, TABLE), {"drug_name": "aspirin"})

    assert result["status"] == "success"
    assert result["count"] == 0


def test_a_listed_drug_is_found(monkeypatch):
    result = _run(monkeypatch, _Response(200, TABLE))

    assert result["status"] == "success"
    assert result["results"][0]["Biomarker"] == "HLA-B"
