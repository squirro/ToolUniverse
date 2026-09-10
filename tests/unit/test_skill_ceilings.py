"""Per-source in-flight ceilings for a Skill Run's fan-out.

A rate limit is a fact about a source, not about a skill, so the table lives
beside the worker and a process author never sees it. Sources start
conservative and are raised only from a measured run (DSR-724)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_ceilings import DEFAULT_CEILING, TABLE_PATH, ceiling_for, source_of  # noqa: E402


def test_a_tool_is_mapped_to_its_source_by_prefix():
    assert source_of("FAERS_calculate_disproportionality") == "openfda"
    assert source_of("OpenFDA_get_approval_history") == "openfda"
    assert source_of("ChEMBL_search_molecules") == "chembl"
    assert source_of("PubMed_search_articles") == "pubmed"


def test_the_spec_ceilings_are_the_ones_in_the_table():
    assert ceiling_for("FAERS_calculate_disproportionality") == 4
    assert ceiling_for("ChEMBL_search_molecules") == 2
    assert ceiling_for("PubMed_search_articles") == 3


def test_an_unknown_source_gets_the_conservative_default():
    assert source_of("get_HPO_ID_by_phenotype") == "get"
    assert ceiling_for("get_HPO_ID_by_phenotype") == DEFAULT_CEILING == 2


def test_a_raise_is_a_data_change():
    """The table is a file: raising a cap edits JSON, never code."""
    table = json.loads(TABLE_PATH.read_text())
    assert table["ceilings"]["openfda"] == 4
    assert "FAERS" in table["prefixes"] and table["prefixes"]["FAERS"] == "openfda"
