"""differential_expression reported a transport failure as a biological negative.

`exec_differential_expression` has two early exits that return **byte-identical**
rows -- same empty `median_log2fc`, same `n_studies: 0`, same empty `experiments`:

    A. no GxA experiment survived the description filter
    B. experiments matched, but every analytics fetch failed

B is a network outage. A is a real, if narrow, answer. At the tool boundary they
are the same object, so an agent reading "n_studies: 0" cannot tell "no study has
ever looked" from "we failed to ask". A third case -- the gene simply not being
measured in the studies that did parse -- is only distinguishable by whether
`experiments` happens to be non-empty, which nothing documents.

The filter itself is also silent about its own work. Measured against the live
4,562-experiment GxA catalogue (DSR-629), the query "neuroendocrine tumor" funnels:

    differential 4187 -> human 1528 -> term match 1 -> +normal-word 0 -> final 0

and the one candidate it found, E-MTAB-6473 "Gastric gene expression of patients
with type-1 gastric neuroendocrine tumours", was dropped for naming no
normal/control/adjacent comparison. The caller saw none of that -- not the
rejection, not that the tool had silently rewritten "neuroendocrine tumor" to
"neuroendocrine" before searching.

**The filter stays strict.** Prior art holds and none of this loosens it; the
point is to say what was rejected and why, and to name the escape hatch
(`experiment=<accession>`) that bypasses the description filter entirely.
"""

import pytest

from tooluniverse.tools_sr import differential as mod

# Shaped like the live GxA catalogue rows the filter consumes.
NEUROENDOCRINE = {
    "experimentAccession": "E-MTAB-6473",
    "experimentType": "RNASEQ_MRNA_DIFFERENTIAL",
    "species": "Homo sapiens",
    "experimentDescription": (
        "Gastric gene expression of patients with type-1 gastric "
        "neuroendocrine tumours"
    ),
}
MOUSE_STUDY = {
    "experimentAccession": "E-MTAB-0001",
    "experimentType": "RNASEQ_MRNA_DIFFERENTIAL",
    "species": "Mus musculus",
    "experimentDescription": "neuroendocrine tumour versus normal in mouse",
}
BASELINE_STUDY = {
    "experimentAccession": "E-MTAB-0002",
    "experimentType": "RNASEQ_MRNA_BASELINE",
    "species": "Homo sapiens",
    "experimentDescription": "neuroendocrine tumour versus adjacent normal tissue",
}
GOOD_STUDY = {
    "experimentAccession": "E-MTAB-0003",
    "experimentType": "RNASEQ_MRNA_DIFFERENTIAL",
    "species": "Homo sapiens",
    "experimentDescription": "neuroendocrine carcinoma versus adjacent normal tissue",
}

CATALOG = [NEUROENDOCRINE, MOUSE_STUDY, BASELINE_STUDY, GOOD_STUDY]


@pytest.mark.unit
def test_the_funnel_reports_each_stage_it_dropped_at():
    _, funnel = mod.filter_experiments(CATALOG, "neuroendocrine")

    stages = funnel["stages"]
    assert stages["catalog"] == 4
    assert stages["differential"] == 3, "the baseline study is not differential"
    assert stages["human"] == 2, "the mouse study is not human"
    assert stages["final"] == 1


@pytest.mark.unit
def test_a_rejected_candidate_names_the_filter_that_dropped_it():
    """E-MTAB-6473 is the real one: it matches the term but names no control arm."""
    _, funnel = mod.filter_experiments(CATALOG, "neuroendocrine")

    dropped = {r["accession"]: r["dropped_by"] for r in funnel["rejected"]}

    assert dropped["E-MTAB-6473"] == "no_normal_comparison", dropped


@pytest.mark.unit
def test_the_search_terms_actually_used_are_reported():
    """The tool rewrites "neuroendocrine tumor" -> "neuroendocrine" and never said so."""
    _, funnel = mod.filter_experiments(CATALOG, "neuroendocrine tumor")

    assert "neuroendocrine" in funnel["search_terms"]


@pytest.mark.unit
def test_no_studies_and_a_dead_network_are_different_statuses():
    no_studies = mod.empty_rows(["CCKBR"], status="no_matching_studies", funnel={})
    fetch_failed = mod.empty_rows(
        ["CCKBR"], status="studies_found_fetch_failed", funnel={}
    )

    assert no_studies[0]["status"] == "no_matching_studies"
    assert fetch_failed[0]["status"] == "studies_found_fetch_failed"
    assert no_studies[0]["status"] != fetch_failed[0]["status"]


@pytest.mark.unit
def test_an_empty_row_keeps_the_columns_the_pipeline_reads():
    """The table pipeline downstream still expects the original column set."""
    row = mod.empty_rows(["CCKBR"], status="no_matching_studies", funnel={})[0]

    for column in (
        "_input_gene_name", "median_log2fc", "best_p_value", "direction",
        "consensus", "n_studies", "overexpressed", "experiments",
    ):
        assert column in row, column
    assert row["_input_gene_name"] == "CCKBR"
    assert row["n_studies"] == 0


@pytest.mark.unit
def test_the_empty_row_names_the_escape_hatch():
    """`experiment=` bypasses the description filter, and is the honest next step."""
    row = mod.empty_rows(["CCKBR"], status="no_matching_studies", funnel={})[0]

    assert "experiment" in row["widen_with"]


@pytest.mark.unit
def test_a_zero_is_never_presented_as_evidence_of_absence():
    row = mod.empty_rows(["CCKBR"], status="no_matching_studies", funnel={})[0]

    assert "not evidence" in row["status_detail"].lower()


def _run_with(monkeypatch, analytics):
    """Drive exec_differential_expression with the two network calls stubbed."""
    monkeypatch.setattr(mod, "_get_experiments_catalog", lambda **k: CATALOG)
    monkeypatch.setattr(
        mod, "gxa_fetch_analytics", lambda acc, timeout=60: (analytics, "cancer vs normal")
    )
    return mod.exec_differential_expression(
        {"indication": "neuroendocrine carcinoma", "gene": "CCKBR"}, None, None, None
    )


@pytest.mark.unit
def test_a_gene_absent_from_parsed_studies_is_its_own_status(monkeypatch):
    """Case C: studies matched AND parsed, the gene just was not in them."""
    rows = _run_with(
        monkeypatch,
        [{"gene_name": "TP53", "gene_id": "ENSG1", "log2fc": 1.5, "p_value": 0.01}],
    )

    assert rows[0]["status"] == "gene_not_measured", rows[0]
    assert rows[0]["n_studies"] == 0


@pytest.mark.unit
def test_a_measured_gene_reports_ok(monkeypatch):
    rows = _run_with(
        monkeypatch,
        [{"gene_name": "CCKBR", "gene_id": "ENSG2", "log2fc": 2.0, "p_value": 0.001}],
    )

    assert rows[0]["status"] == "ok", rows[0]
    assert rows[0]["n_studies"] == 1


@pytest.mark.unit
def test_a_dead_network_does_not_masquerade_as_a_missing_gene(monkeypatch):
    """Case B end to end: studies matched, every fetch failed."""
    rows = _run_with(monkeypatch, [])

    assert rows[0]["status"] == "studies_found_fetch_failed", rows[0]
    assert "transport failure" in rows[0]["status_detail"].lower()
