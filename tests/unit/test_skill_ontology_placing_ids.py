"""A mapped term that is already an ontology id is placed on that id, not searched as a label.

Open Targets names its diseases by id (MONDO_0008170 is ovarian cancer). Searched as a label,
the id matches nothing, so the term read as belonging to no ontology. The responses are live
OLS4 answers recorded on 2026-09-24, keyed by the URL the lookup fetched.
"""

import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse import skill_ontology_placing  # noqa: E402
from tooluniverse.skill_ontology_placing import lookup, ontology_id, place  # noqa: E402
from tooluniverse.skill_runner import placed_mapping  # noqa: E402

pytestmark = pytest.mark.unit

RECORDED = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ols"
                       / "placing_ids_2026-09-24.json").read_text())["responses"]
OVARY = ["ovarian", "cancer"]


@pytest.fixture
def fetched(monkeypatch):
    """Serve the recorded OLS4 answers; a URL never recorded fails the test loudly."""
    urls: list[str] = []

    def _get(url, timeout=30):
        urls.append(url)
        answer = RECORDED[url]
        if answer["status"] != 200:
            raise urllib.error.HTTPError(url, answer["status"], "recorded", {},
                                         io.BytesIO(json.dumps(answer["body"]).encode()))
        return answer["body"]

    monkeypatch.setattr(skill_ontology_placing, "_get", _get)
    return urls


def test_a_disease_mapped_as_a_mondo_id_is_placed_on_that_term(fetched):
    """The sr-dev drug-target run for ovarian cancer published this row as unknown."""
    spec = {"mapping": {"disease_choice": {"of": "disease",
                                           "onto": {"rows": "disease_candidates", "field": "id"}}}}
    outcome = {"facts": {"disease_choice": [{"of": "ovarian cancer", "term": "MONDO_0008170",
                                             "reason": "the disease itself", "concept": OVARY}]}}

    row = placed_mapping(spec, outcome, lookup)["facts"]["disease_choice"][0]

    assert row["placing"] == "placed"
    assert row["ontology"] == "mondo"
    assert row["ontology_term"] == "MONDO:0008170" and row["ontology_label"] == "ovarian cancer"
    assert row["under"] == "female reproductive organ cancer"   # the first recorded ancestor naming one


@pytest.mark.parametrize("term, ontology, obo_id, label", [
    ("MONDO:0008170", "mondo", "MONDO:0008170", "ovarian cancer"),
    ("http://purl.obolibrary.org/obo/MONDO_0008170", "mondo", "MONDO:0008170", "ovarian cancer"),
    ("HP:0000365", "hp", "HP:0000365", "Hearing impairment"),
    ("Orphanet_98261", "ordo", "ORDO:98261", "Progressive myoclonic epilepsy"),
])
def test_each_id_form_is_looked_up_by_its_iri_in_its_own_ontology(fetched, term, ontology,
                                                                  obo_id, label):
    verdict = place(lookup(term), [])

    assert verdict["placing"] == "not placed"          # known to the ontology; no concept given
    assert (verdict["ontology"], verdict["term"], verdict["label"]) == (ontology, obo_id, label)
    assert all("/search?" not in url for url in fetched)


def test_an_id_the_ontology_does_not_know_is_unknown_not_placed_and_not_a_service_failure(fetched):
    verdict = place(lookup("MONDO_9999999"), OVARY)

    assert verdict["placing"] == "unknown" and verdict["term"] is None
    assert "note" not in verdict


@pytest.mark.parametrize("label", ["OTAR_0000018", "obsolete_ovarian carcinoma", "ovarian cancer",
                                   "BLOOD CREATININE INCREASED", "COVID_19"])
def test_a_label_is_not_read_as_an_id(label):
    """Only a known prefix followed by digits is an id; an underscore alone is not."""
    assert ontology_id(label) is None


def test_a_term_with_an_unknown_prefix_still_goes_to_label_search(fetched):
    """OTAR_ is Open Targets' own therapeutic-area id: no ontology to look it up in."""
    responses = lookup("OTAR_0000018")

    assert fetched and all("/search?" in url for url in fetched)
    assert set(responses) == set(skill_ontology_placing.ONTOLOGIES)
    assert place(responses, OVARY)["placing"] == "unknown"


# --- a retired term -----------------------------------------------------------------------
#
# EFO retired EFO_0000305 for MONDO_0004989; Open Targets can still hand over the EFO id.

BREAST = ["breast", "cancer"]
DISEASE_MAPPING = {"mapping": {"disease_choice": {
    "of": "disease", "onto": {"rows": "disease_candidates", "field": "id"}}}}


def _placed_row(term, concept):
    outcome = {"facts": {"disease_choice": [{"of": "the disease", "term": term,
                                             "reason": "the disease itself", "concept": concept}]}}
    return placed_mapping(DISEASE_MAPPING, outcome, lookup)["facts"]["disease_choice"][0]


def test_an_obsolete_id_with_a_replacement_is_placed_on_the_replacement_and_names_both(fetched):
    row = _placed_row("EFO_0000305", BREAST)

    assert row["term"] == "EFO_0000305"                     # the source's id is kept
    assert row["placing"] == "placed" and row["ontology"] == "mondo"
    assert row["ontology_term"] == "MONDO:0004989" and row["ontology_label"] == "breast carcinoma"
    assert row["obsolete_term"] == "EFO:0000305" and row["replaced_by"] == "MONDO:0004989"
    assert "obsolete" in row["note"] and "MONDO:0004989" in row["note"]


def test_an_obsolete_id_with_no_replacement_reads_obsolete_and_says_so(fetched):
    row = _placed_row("MONDO_0015964", BREAST)

    assert row["placing"] == "obsolete"
    assert row["obsolete_term"] == "MONDO:0015964" and "replaced_by" not in row
    assert "no replacement" in row["note"] and "not placed" in row["note"]


def _mapping_failures(draft, row):
    from tooluniverse.skill_report_check import check_report
    received = {"handover": {"facts": {"disease_choice": [row]},
                             "mappings": ["disease_choice"], "tables": []}}
    return [f for f in check_report(draft, received) if f["kind"].startswith("mapping_")]


def test_the_report_must_call_a_replaced_term_obsolete_and_name_its_replacement(fetched):
    row = _placed_row("EFO_0000305", BREAST)

    silent = _mapping_failures("Breast cancer, read as EFO_0000305 (placed under breast disorder).", row)
    shown = _mapping_failures("Breast cancer, read as EFO_0000305, which EFO made obsolete; placed "
                              "on its replacement MONDO_0004989 under breast disorder.", row)

    assert [f["kind"] for f in silent] == ["mapping_obsolete_not_shown"]
    assert "MONDO:0004989" in silent[0]["context"]
    assert shown == []


def test_the_report_still_requires_the_source_id_of_a_replaced_term(fetched):
    """Naming only the replacement would hide which id the source was read onto."""
    row = _placed_row("EFO_0000305", BREAST)

    failures = _mapping_failures("Breast cancer is obsolete here; placed on MONDO:0004989.", row)

    assert [f["kind"] for f in failures] == ["mapping_not_shown"]


def test_the_report_must_call_an_unreplaced_obsolete_term_obsolete(fetched):
    row = _placed_row("MONDO_0015964", BREAST)

    assert [f["kind"] for f in _mapping_failures("Read as MONDO_0015964, not placed.", row)] == \
        ["mapping_obsolete_not_shown"]
    assert _mapping_failures("Read as MONDO_0015964: obsolete, with no replacement.", row) == []
