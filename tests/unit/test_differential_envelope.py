"""differential_expression reported a transport failure as a biological negative.

`exec_differential_expression` had two early exits returning **byte-identical** rows --
same empty `median_log2fc`, same `n_studies: 0`, same empty `experiments` -- for (A) no GxA
experiment surviving the description filter and (B) experiments matching but every
analytics fetch failing. B is a network outage; A is a real, if narrow, answer. A third
case, the gene simply not being measured in the studies that did parse, was distinguishable
only by whether `experiments` happened to be non-empty.

The filter was also silent about its own work. Against the live 4,562-experiment GxA
catalogue (DSR-629), "neuroendocrine tumor" funnels differential 4187 -> human 1528 -> term
match 1 -> +normal-word 0 -> final 0, and the one candidate, E-MTAB-6473, was dropped for
naming no normal/control/adjacent comparison. The caller saw none of that, nor that the
tool had silently rewritten "neuroendocrine tumor" to "neuroendocrine" before searching.

**The filter stays strict.** None of this loosens it; the point is to say what was rejected
and why, and to name the escape hatch (`experiment=<accession>`) that bypasses it entirely.
"""

import pytest

from tooluniverse.tools_sr import differential as mod

pytestmark = pytest.mark.unit


def _study(accession, description, kind="RNASEQ_MRNA_DIFFERENTIAL", species="Homo sapiens"):
    """Shaped like the live GxA catalogue rows the filter consumes."""
    return {"experimentAccession": accession, "experimentType": kind, "species": species,
            "experimentDescription": description}


CATALOG = [
    _study("E-MTAB-6473", "Gastric gene expression of patients with type-1 gastric "
                          "neuroendocrine tumours"),
    _study("E-MTAB-0001", "neuroendocrine tumour versus normal in mouse",
           species="Mus musculus"),
    _study("E-MTAB-0002", "neuroendocrine tumour versus adjacent normal tissue",
           kind="RNASEQ_MRNA_BASELINE"),
    _study("E-MTAB-0003", "neuroendocrine carcinoma versus adjacent normal tissue"),
]


def _empty_row(status="no_matching_studies"):
    return mod.empty_rows(["CCKBR"], status=status, funnel={})[0]


def test_the_funnel_reports_each_stage_it_dropped_at():
    _, funnel = mod.filter_experiments(CATALOG, "neuroendocrine")

    stages = funnel["stages"]
    assert stages["catalog"] == 4
    assert stages["differential"] == 3, "the baseline study is not differential"
    assert stages["human"] == 2, "the mouse study is not human"
    assert stages["final"] == 1


def test_a_rejected_candidate_names_the_filter_that_dropped_it():
    """E-MTAB-6473 is the real one: it matches the term but names no control arm."""
    _, funnel = mod.filter_experiments(CATALOG, "neuroendocrine")

    dropped = {r["accession"]: r["dropped_by"] for r in funnel["rejected"]}

    assert dropped["E-MTAB-6473"] == "no_normal_comparison", dropped


def test_the_search_terms_actually_used_are_reported():
    """The tool rewrites "neuroendocrine tumor" -> "neuroendocrine" and never said so."""
    _, funnel = mod.filter_experiments(CATALOG, "neuroendocrine tumor")

    assert "neuroendocrine" in funnel["search_terms"]


def test_no_studies_and_a_dead_network_are_different_statuses():
    assert _empty_row()["status"] == "no_matching_studies"
    assert _empty_row("studies_found_fetch_failed")["status"] == "studies_found_fetch_failed"


def test_an_empty_row_keeps_the_columns_the_pipeline_reads():
    """The table pipeline downstream still expects the original column set."""
    row = _empty_row()

    for column in ("_input_gene_name", "median_log2fc", "best_p_value", "direction",
                   "consensus", "n_studies", "overexpressed", "experiments"):
        assert column in row, column
    assert row["_input_gene_name"] == "CCKBR"
    assert row["n_studies"] == 0


def test_the_empty_row_names_the_escape_hatch():
    """`experiment=` bypasses the description filter, and is the honest next step."""
    assert "experiment" in _empty_row()["widen_with"]


def test_a_zero_is_never_presented_as_evidence_of_absence():
    assert "not evidence" in _empty_row()["status_detail"].lower()


def _run_with(monkeypatch, analytics):
    """Drive exec_differential_expression with the two network calls stubbed."""
    monkeypatch.setattr(mod, "_get_experiments_catalog", lambda **k: CATALOG)
    monkeypatch.setattr(
        mod, "gxa_fetch_analytics", lambda acc, timeout=60: (analytics, "cancer vs normal"))
    return mod.exec_differential_expression(
        {"indication": "neuroendocrine carcinoma", "gene": "CCKBR"}, None, None, None)


@pytest.mark.parametrize("analytics,status,n_studies,detail", [
    # Case C: studies matched AND parsed, the gene just was not in them.
    ([{"gene_name": "TP53", "gene_id": "ENSG1", "log2fc": 1.5, "p_value": 0.01}],
     "gene_not_measured", 0, None),
    ([{"gene_name": "CCKBR", "gene_id": "ENSG2", "log2fc": 2.0, "p_value": 0.001}],
     "ok", 1, None),
    # Case B end to end: studies matched, every fetch failed.
    ([], "studies_found_fetch_failed", 0, "transport failure"),
])
def test_the_status_tells_the_three_empty_cases_apart(monkeypatch, analytics, status,
                                                      n_studies, detail):
    rows = _run_with(monkeypatch, analytics)

    assert rows[0]["status"] == status, rows[0]
    assert rows[0]["n_studies"] == n_studies
    assert detail is None or detail in rows[0]["status_detail"].lower()
