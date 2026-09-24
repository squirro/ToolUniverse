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
