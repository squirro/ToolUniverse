"""drug-target-validation's identity step takes the Ensembl id from Ensembl's own lookup, and
MyGene's only when that lookup has nothing.

MyGene lists some genes on alternate loci as well: HPS5 on chromosome 11 and an HG2111 patch,
NEU1 on chromosome 6 and seven MHC haplotypes, each as a list rather than one object, so
`data.hits.0.ensembl.gene` reads nothing. Ensembl's lookup by symbol names the primary-assembly
gene, the only one of each list Open Targets knows. The responses are recorded live, unedited.
"""
import json
from pathlib import Path

import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
LISTED = json.loads((FIXTURES / "dtv" / "identity_ensembl_list_2026-09-25.json").read_text())["responses"]
FOLR1 = json.loads((FIXTURES / "dtv" / "folr1_ovarian_2026-09-22.json").read_text())
# Ensembl's answer for a symbol it has no gene for, recorded unedited.
NO_LOOKUP = json.loads((FIXTURES / "skill_processes" / "rare_disease_coarse_facies"
                        / "ensembl_lookup_gene_2026-09-25.json").read_text())[
    json.dumps({"gene_id": "SCA20", "species": "homo_sapiens"}, sort_keys=True)]


def _identity(target, served):
    asked = []

    def execute(tool, arguments):
        answer = served[tool]
        return json.loads(answer) if isinstance(answer, str) else answer

    def agent(question):
        asked.append(question)
        return {}

    runner = SkillRunner(load_graph("drug-target-validation"), execute=execute, ask=agent)
    out = runner.advance(runner.start({"target": target})["run_id"])
    assert out["step_id"] == "identity"
    return out, [q for q in asked if q["kind"] == "repair"]


@pytest.mark.parametrize("gene,primary,listed", [
    ("HPS5", "ENSG00000110756", 2), ("NEU1", "ENSG00000204386", 8)])
def test_a_gene_mygene_lists_on_alternate_loci_gets_its_primary_assembly_id(gene, primary, listed):
    served = LISTED[gene]
    hit = served["MyGene_query_genes"]["data"]["hits"][0]
    assert isinstance(hit["ensembl"], list) and len(hit["ensembl"]) == listed

    out, repairs = _identity(gene, served)

    assert repairs == []
    assert (out["extracted"]["symbol"], out["extracted"]["ensembl_id"]) == (gene, primary)
    assert out["extracted"]["ensembl_version"] == served["ensembl_lookup_gene"]["data"]["version"]


def test_a_gene_mygene_gives_one_object_keeps_that_id():
    out, repairs = _identity("FOLR1", FOLR1)

    assert repairs == [] and out["extracted"]["ensembl_id"] == "ENSG00000110195"


def test_without_an_ensembl_lookup_mygenes_single_id_is_the_fallback():
    out, repairs = _identity("FOLR1", {**FOLR1, "ensembl_lookup_gene": NO_LOOKUP})

    assert repairs == [] and out["extracted"]["ensembl_id"] == "ENSG00000110195"


def test_without_an_ensembl_lookup_a_listed_gene_goes_to_the_repair_not_to_a_guess():
    out, repairs = _identity("HPS5", {**LISTED["HPS5"], "ensembl_lookup_gene": NO_LOOKUP})

    assert len(repairs) == 1
    assert "ensembl_id" not in out["extracted"]
