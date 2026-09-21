"""A judged mapping is shown with a placing from the Ontology Lookup Service (rule 2).

The check proves membership, not meaning: the agent mapped "ototoxicity" onto DIZZINESS and
FALL, and the server accepted both because both are FAERS terms. The placing says, for each
term, whether an ontology puts it under the concept the user named. It is evidence, never a
gate: as a gate it would strike three correct renal terms of ten.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_ontology_placing import place  # noqa: E402

pytestmark = pytest.mark.unit

RECORDED = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ols"
                       / "placing_probe_2026-09-21.json").read_text())
EAR = ["ear", "hearing", "vestibular"]
KIDNEY = ["kidney", "renal", "urinary"]


@pytest.mark.parametrize("term, concept, expected", [
    ("DEAFNESS", EAR, "placed"),
    ("TINNITUS", EAR, "placed"),
    ("DIZZINESS", EAR, "placed"),                  # a synonym of HPO Vertigo, under the inner ear
    ("FALL", EAR, "not placed"),                   # SNOMED knows it; nothing about the ear above it
    ("ACUTE KIDNEY INJURY", KIDNEY, "placed"),
    ("HYPOMAGNESAEMIA", KIDNEY, "not placed"),     # a consequence, not an abnormality of the kidney
    ("BLOOD CREATININE INCREASED", KIDNEY, "unknown"),
    ("NEPHROPATHY TOXIC", KIDNEY, "unknown"),
])
def test_each_probed_term_is_placed_as_the_recorded_ontologies_say(term, concept, expected):
    verdict = place(RECORDED[term], concept)

    assert verdict["placing"] == expected


def test_a_placed_term_names_the_ontology_term_and_the_ancestor_that_placed_it():
    verdict = place(RECORDED["DIZZINESS"], EAR)

    assert verdict["term"] == "HP:0002321" and verdict["label"] == "Vertigo"
    assert "ear" in verdict["under"].lower()


def test_a_service_failure_reads_as_unknown_and_says_so():
    verdict = place({"hp": {"error": "HTTPError: 503"}, "snomed": {"error": "HTTPError: 503"}}, EAR)

    assert verdict["placing"] == "unknown" and "503" in verdict["note"]
