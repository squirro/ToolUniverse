"""A source that could not be reached must not read as a source that held nothing.

Both tools here answered a caught exception with an empty result and a number. The number
is the damage: `search_ctgov` returned `[], 0` and `gxa_fetch_analytics` returned `[], ""`,
and in each case the caller carried on as though the source had answered.

`exec_ct_search` expands one term into several and merges the trials from each. A term whose
search failed contributed nothing, and nothing said so, so a filtered list arrived looking
like a short one. `exec_differential_expression` fetches every matching study in parallel and
takes the median across them. A study whose fetch failed was simply absent from the median,
and the row still said `status: ok` with an `n_studies` counting only what survived -- a
confident wrong number, which is worse than an empty table.

The all-failed case in `exec_differential_expression` was already honest (DSR-629,
`studies_found_fetch_failed`). The partial case was not, and partial is the common one.
"""

import json

import pytest

from tooluniverse.tools_sr import clinical_trials as ct
from tooluniverse.tools_sr import differential as de

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- ClinicalTrials

def _study(nct_id="NCT00000001", title="A trial of something"):
    """The one shape `search_ctgov` reads; every other module is optional to it."""
    return {"protocolSection": {"identificationModule": {"nctId": nct_id,
                                                         "briefTitle": title}}}


class _Answer:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _ctgov(monkeypatch, unreachable=()):
    """Stand in for ClinicalTrials.gov, raising for the terms named in `unreachable`.

    `_expand_intervention` is pinned to the term itself so the query carries it verbatim
    and the fake can decide per term; the real one reaches PubChem and OLS.
    """
    monkeypatch.setattr(ct, "_expand_intervention", lambda term, timeout=15: term)

    def _get(url, params=None, timeout=None):
        term = (params or {}).get("query.intr", "")
        if term in unreachable:
            raise OSError("ClinicalTrials.gov unreachable")
        return _Answer({"studies": [_study(f"NCT-{term}")], "totalCount": 7})

    monkeypatch.setattr("requests.get", _get)


def test_an_unreachable_ctgov_is_not_answered_with_a_count(monkeypatch):
    """`[], 0` said the source holds nothing. It said nothing about the source at all."""
    _ctgov(monkeypatch, unreachable={"cisplatin"})

    with pytest.raises(Exception) as raised:
        ct.search_ctgov("cisplatin")

    assert "unreachable" in str(raised.value)


def test_a_term_whose_search_failed_is_named_in_the_table(monkeypatch):
    _ctgov(monkeypatch, unreachable={"carboplatin"})

    rows = ct.exec_ct_search({"intervention": "cisplatin, carboplatin"}, None, None, None)

    failed = [r for r in rows if r.get("search_status") == "source_unreachable"]
    assert [r["_input_query"] for r in failed] == ["carboplatin"], rows


def test_a_failed_term_reports_its_total_as_unknown_not_as_zero(monkeypatch):
    _ctgov(monkeypatch, unreachable={"carboplatin"})

    rows = ct.exec_ct_search({"intervention": "carboplatin"}, None, None, None)

    assert [r["total_matching"] for r in rows] == ["unknown"], rows


def test_the_terms_that_answered_still_bring_their_trials(monkeypatch):
    """A partial outage must narrow the answer, not replace it."""
    _ctgov(monkeypatch, unreachable={"carboplatin"})

    rows = ct.exec_ct_search({"intervention": "cisplatin, carboplatin"}, None, None, None)

    assert [r["nct_id"] for r in rows if r.get("nct_id")] == ["NCT-cisplatin"]
    assert [r["total_matching"] for r in rows if r.get("nct_id")] == ["7"]


def test_a_failed_term_keeps_the_columns_the_table_pipeline_reads(monkeypatch):
    _ctgov(monkeypatch, unreachable={"carboplatin"})

    rows = ct.exec_ct_search({"intervention": "cisplatin, carboplatin"}, None, None, None)

    populated, failed = rows[0], rows[1]
    assert set(failed) == set(populated), "the failure row is the same table, not another one"


# ------------------------------------------------------------------------ Expression Atlas

_CATALOG = [
    {"experimentAccession": "E-GOOD", "experimentType": "RNASEQ_MRNA_DIFFERENTIAL",
     "species": "Homo sapiens",
     "experimentDescription": "neuroendocrine carcinoma versus adjacent normal tissue"},
    {"experimentAccession": "E-DEAD", "experimentType": "RNASEQ_MRNA_DIFFERENTIAL",
     "species": "Homo sapiens",
     "experimentDescription": "neuroendocrine carcinoma patient samples versus normal"},
]

_ANALYTICS = (
    "Gene ID\tGene Name\t'carcinoma vs normal'.p-value\t'carcinoma vs normal'.log2foldchange\n"
    "ENSG00000110148\tCCKBR\t0.001\t2.5\n"
)


class _Body:
    def __init__(self, text):
        self._text = text

    def read(self):
        return self._text.encode()


def _gxa(monkeypatch, unreachable=()):
    """Stand in for the Expression Atlas analytics files, by accession."""
    monkeypatch.setattr(de, "_get_experiments_catalog", lambda **kw: _CATALOG)

    def _urlopen(request, timeout=None):
        if any(acc in request.full_url for acc in unreachable):
            raise OSError("Expression Atlas unreachable")
        return _Body(_ANALYTICS)

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)


def _row(monkeypatch, unreachable=()):
    _gxa(monkeypatch, unreachable=unreachable)
    return de.exec_differential_expression(
        {"indication": "neuroendocrine carcinoma", "gene": "CCKBR"}, None, None, None)[0]


def test_an_unreachable_atlas_is_not_answered_with_an_empty_table(monkeypatch):
    """`[], ""` was indistinguishable from an analytics file holding no rows."""
    _gxa(monkeypatch, unreachable={"E-DEAD"})

    with pytest.raises(Exception) as raised:
        de.gxa_fetch_analytics("E-DEAD")

    assert "unreachable" in str(raised.value)


def test_a_study_that_could_not_be_read_is_not_counted_as_a_study_that_agreed(monkeypatch):
    """Two studies matched, one answered. `status: ok` claimed both were considered."""
    assert _row(monkeypatch, unreachable={"E-DEAD"})["status"] != "ok"


def test_the_study_that_could_not_be_read_is_named(monkeypatch):
    row = _row(monkeypatch, unreachable={"E-DEAD"})

    assert "E-DEAD" in json.loads(row["diagnostics"])["unreadable"]


def test_a_partial_read_says_the_median_stands_on_fewer_studies_than_matched(monkeypatch):
    row = _row(monkeypatch, unreachable={"E-DEAD"})

    assert row["n_studies"] == 1
    assert "not evidence" in row["status_detail"].lower()


def test_the_studies_that_did_answer_are_still_aggregated(monkeypatch):
    """A partial outage must narrow the answer, not replace it."""
    row = _row(monkeypatch, unreachable={"E-DEAD"})

    assert row["median_log2fc"] == 2.5
    assert row["direction"] == "up"


def test_a_complete_read_is_still_plainly_ok(monkeypatch):
    row = _row(monkeypatch)

    assert row["status"] == "ok"
    assert row["n_studies"] == 2
