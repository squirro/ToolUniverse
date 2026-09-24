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
    """fda.gov answers `response`; the ClinPGx fallback is unreachable."""
    import requests

    def get(url, *a, **k):
        if "clinpgx" in url:
            raise requests.exceptions.ConnectionError("unreachable in this test")
        return response

    monkeypatch.setattr(mod.requests, "get", get)
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


# --- when fda.gov refuses, ClinPGx answers, labelled as ClinPGx ------------------------
#
# ClinPGx annotates FDA labels and marks those on FDA's biomarker list. Those rows are
# ClinPGx's reading of a label, not FDA's table: the answer must say so wherever it is
# read, and a drug ClinPGx lists nothing for leaves the FDA table unread, not empty.

import json
from pathlib import Path

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import absorb

RECORDED_CLINPGX = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "clinpgx"
     / "fda_biomarker_label_annotations_2026-09-24.json").read_text())
CLINPGX_HOST = "api.clinpgx.org"


class _JSONResponse(_Response):
    def json(self):
        return json.loads(self.text)


def _clinpgx(url, params):
    """ClinPGx as recorded: an exact, case-sensitive name match, 404 for no match."""
    recorded = RECORDED_CLINPGX.get((params or {}).get("relatedChemicals.name"),
                                    RECORDED_CLINPGX["aspirin"])
    return _JSONResponse(recorded["http_status"], json.dumps(recorded["body"]), url=url)


def _run_blocked(monkeypatch, fda_response, arguments, clinpgx=_clinpgx):
    seen = []

    def get(url, params=None, **kwargs):
        seen.append(url)
        return clinpgx(url, params) if CLINPGX_HOST in url else fda_response

    monkeypatch.setattr(mod.requests, "get", get)
    return FDAPharmacogenomicBiomarkersTool({"name": "x"}).run(arguments), seen


def test_a_refused_fda_table_is_answered_from_clinpgx_and_says_so(monkeypatch):
    result, _ = _run_blocked(monkeypatch, _Response(404, "Not found\n", url=APOLOGY_URL),
                             {"drug_name": "abacavir"})

    assert result["status"] == "success", result
    assert result["source"] == "ClinPGx"
    assert result["fallback_from"] == "fda.gov"
    assert "refuses automated" in result["fda_table"]
    assert "not the FDA table" in result["note"]
    (row,) = result["results"]
    assert row["source"] == "ClinPGx"
    assert row["url"] == "https://www.clinpgx.org/labelAnnotation/PA166104833"
    assert row["Biomarker"] == "HLA-B"
    assert row["PGxLevel"] == "Testing Required"
    # The FDA table's own columns would pass the row off as a row of that table.
    assert "LabelingSection" not in row and "TherapeuticArea" not in row


def test_every_clinpgx_row_carries_its_own_link(monkeypatch):
    result, _ = _run_blocked(monkeypatch, _Response(403, AKAMAI_403), {"drug_name": "warfarin"})

    assert result["count"] == 2
    assert [r["Biomarker"] for r in result["results"]] == ["CYP2C9, VKORC1", "PROC, PROS1"]
    assert all(r["url"].startswith("https://www.clinpgx.org/labelAnnotation/PA")
               for r in result["results"])


def test_the_drug_name_is_found_whatever_its_case(monkeypatch):
    """ClinPGx matches names exactly and holds them in lower case; "Abacavir" answers 404."""
    result, _ = _run_blocked(monkeypatch, _Response(403, AKAMAI_403), {"drug_name": "Abacavir"})

    assert result["count"] == 1, result


def test_the_biomarker_filter_and_the_limit_apply_to_clinpgx_rows(monkeypatch):
    result, _ = _run_blocked(monkeypatch, _Response(403, AKAMAI_403),
                             {"drug_name": "warfarin", "biomarker": "vkorc1"})
    assert [r["Biomarker"] for r in result["results"]] == ["CYP2C9, VKORC1"]

    result, _ = _run_blocked(monkeypatch, _Response(403, AKAMAI_403),
                             {"drug_name": "warfarin", "limit": 1})
    assert (result["count"], result["shown"]) == (2, 1)


def test_an_answering_fda_table_is_used_and_clinpgx_is_not_asked(monkeypatch):
    result, seen = _run_blocked(monkeypatch, _Response(200, TABLE), {"drug_name": "abacavir"})

    assert result["source"] == "FDA"
    assert "fallback_from" not in result
    assert not any(CLINPGX_HOST in url for url in seen), seen


def test_clinpgx_failing_too_fails_with_both_reasons(monkeypatch):
    def down(url, params):
        return _JSONResponse(503, '{"status": "error"}', url=url)

    result, _ = _run_blocked(monkeypatch, _Response(403, AKAMAI_403),
                             {"drug_name": "abacavir"}, clinpgx=down)

    assert is_upstream_failure(result), result
    assert "refuses automated" in result["error"]
    assert "ClinPGx" in result["error"] and "503" in result["error"]


def test_clinpgx_listing_nothing_leaves_the_fda_table_unread_not_empty(monkeypatch):
    result, _ = _run_blocked(monkeypatch, _Response(403, AKAMAI_403), {"drug_name": "aspirin"})

    assert is_upstream_failure(result), result
    assert "count" not in result
    assert "refuses automated" in result["error"]
    assert "not read" in result["error"]


@pytest.mark.parametrize("skill, step", [("clinical-data-integration", "pharmacogenomics"),
                                         ("adverse-event-detection", "interactions")])
def test_the_step_records_which_source_answered(monkeypatch, skill, step):
    spec = next(s for s in load_graph(skill)["steps"] if s["id"] == step)
    fallback, _ = _run_blocked(monkeypatch, _Response(403, AKAMAI_403), {"drug_name": "abacavir"})
    fda, _ = _run_blocked(monkeypatch, _Response(200, TABLE), {"drug_name": "abacavir"})
    cpic = {"status": "success", "data": [], "metadata": {"source": "CPIC"}}

    assert absorb(spec, [cpic, fallback], {})["facts"]["pgx_biomarker_source"] == "ClinPGx"
    assert absorb(spec, [cpic, fda], {})["facts"]["pgx_biomarker_source"] == "FDA"
    assert "ClinPGx" in spec["notes"] and "pgx_biomarker_source" in spec["notes"]
