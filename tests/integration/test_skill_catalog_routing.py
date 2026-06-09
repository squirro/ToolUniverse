"""Typical-question-per-skill catalog + find_skill routing acceptance (ADR-0009).

Each served skill has ONE typical user question (these double as demo prompts). The test
asserts find_skill routes each question to its own skill within top-3, and that every served
skill has a catalog entry. Reads the REAL served bodies from ``deploy/`` (repo data, no
network). Mis-routes are fixed by adding a ``Triggers:`` line to the skill's header comment.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from tooluniverse.skill_index import build_index, search

pytestmark = pytest.mark.integration

_ROOT = Path(__file__).resolve().parents[2]
_DEPLOY = _ROOT / "deploy"
_EXCLUDE = {"router", "router-spike", "doriano", "smcp-only"}

# One typical question per served skill. Realistic user phrasing; SR-flavoured where natural.
CATALOG: dict[str, str] = {
    "acmg-variant-classification": "Apply ACMG criteria to classify the pathogenicity of the BRCA1 variant c.5266dupC.",
    "adverse-event-detection": "Mine FAERS for adverse-event signals associated with ezogabine.",
    "antibody-engineering": "What therapeutic antibody engineering precedent and structures exist for the HER2 antigen?",
    "binder-discovery": "Discover novel small-molecule binders for the SSTR2 receptor.",
    "cancer-classification": "Classify this tumor sample: poorly differentiated lung adenocarcinoma.",
    "cancer-genomics-tcga": "What are the TCGA pan-cancer mutation frequencies for KRAS?",
    "cancer-variant-interpretation": "What does the cancer mutation BRAF V600E mean clinically and for therapy?",
    "chemical-compound-retrieval": "Look up the chemical structure, identifiers and properties of imatinib.",
    "chemical-safety": "What is the GHS hazard classification and toxicology profile of acrylamide?",
    "clinical-guidelines": "What do current clinical practice guidelines recommend for first-line type 2 diabetes treatment?",
    "clinical-trial-design": "Help me design a randomized phase 2 clinical trial for a new epilepsy drug.",
    "clinical-trial-matching": "Which clinical trials best fit a patient with EGFR-mutant non-small-cell lung cancer?",
    "crispr-screen-analysis": "Interpret these CRISPR-Cas9 dropout screen hits and prioritize them as targets.",
    "disease-research": "What is known about cystic fibrosis — its biology, targets, drugs and trials overview?",
    "drug-drug-interaction": "Is there a drug-drug interaction between warfarin and aspirin?",
    "drug-mechanism-research": "How does imatinib work — its mechanism of action from target to pathway to outcome?",
    "drug-regulatory": "What is the FDA regulatory status, approvals and boxed warnings for cenobamate?",
    "drug-repurposing": "What new indications could the existing drug metformin be repurposed for?",
    "drug-research": "Give me a full profile of imatinib — chemistry, targets, indications and safety.",
    "drug-target-validation": "Is KRAS a druggable target worth pursuing — give me a go/no-go validation.",
    "expression-data-retrieval": "Find public gene-expression datasets measuring SSTR2.",
    "functional-genomics-screens": "Prioritize the candidate genes from a genome-wide essentiality screen as drug targets.",
    "gene-disease-association": "What is the gene-disease validity evidence linking CFTR to cystic fibrosis?",
    "gene-enrichment": "Run GO and pathway over-representation enrichment on this gene set: TP53, MDM2, CDKN2A, RB1, ATM.",
    "gene-regulatory-networks": "Which transcription factors regulate the gene TP53?",
    "gpcr-structural-pharmacology": "Analyze the GPCR structural pharmacology of the somatostatin receptor SSTR2.",
    "gwas-drug-discovery": "What druggable drug targets emerge from GWAS associations for type 2 diabetes?",
    "gwas-finemapping": "Fine-map the causal variant at the TCF7L2 GWAS locus.",
    "gwas-snp-interpretation": "Interpret the GWAS SNP rs7903146 and its trait associations.",
    "gwas-study-explorer": "What GWAS studies and associations have been reported for type 2 diabetes?",
    "gwas-trait-to-gene": "Which genes does GWAS implicate for the trait LDL cholesterol?",
    "hla-immunogenomics": "Analyze HLA-A*02:01 epitope binding and immunogenicity.",
    "immunology": "Characterize the immunology of the IL-23 / Th17 pathway.",
    "immunotherapy-response-prediction": "Predict checkpoint immunotherapy response for a tumor with high mutational burden.",
    "infectious-disease": "Research the pathogen biology and treatment options for tuberculosis.",
    "kegg-disease-drug": "Map the KEGG disease-gene-drug pathway network for type 2 diabetes.",
    "literature-deep-research": "From the primary literature, what is the prevalence of AR-V7 in late-stage vs early prostate cancer?",
    "network-pharmacology": "Run a network-pharmacology analysis of a multi-target kinase inhibitor.",
    "pathway-disease-genetics": "Which biological pathways and genes underlie Parkinson's disease?",
    "pharmacogenomics": "How does CYP2D6 genotype affect metabolizer status and drug dosing?",
    "pharmacovigilance": "Build a pharmacovigilance safety profile for ezogabine.",
    "precision-medicine-stratification": "Stratify patients for a targeted therapy based on their molecular biomarkers.",
    "precision-oncology": "Recommend a tiered therapy for BRAF V600E mutant melanoma.",
    "protein-interactions": "What are the protein-protein interaction partners of TP53?",
    "protein-lof-mechanism": "What is the molecular loss-of-function mechanism of the TP53 R175H variant?",
    "protein-structural-annotation-pdb": "Annotate the per-residue secondary structure and interface of KRAS in PDB entry 6VJJ.",
    "protein-structure-prediction": "Predict the 3D structure of the SSTR2 protein from its sequence.",
    "protein-structure-retrieval": "Retrieve the experimental PDB and AlphaFold structures available for KRAS.",
    "rare-disease-diagnosis": "Diagnose a likely rare disease from this patient's phenotypes and candidate genes.",
    "rare-disease-genomics": "What is the rare-disease genomics — causative genes and variants — of Gaucher disease?",
    "regulatory-variant-analysis": "Is the noncoding variant rs78378222 located in an active regulatory element, and what gene does it regulate?",
    "small-molecule-discovery": "Discover small-molecule scaffolds and analogs active against a kinase target.",
    "structural-proteomics": "Assess the structural druggability of KRAS across its PDB structures and AlphaFold model.",
    "structural-variant-analysis": "Classify the clinical pathogenicity of a 22q11.2 deletion structural variant.",
    "systems-biology": "Build a systems-biology pathway model of insulin signaling.",
    "target-research": "Produce a full multi-dimension target dossier on SSTR2.",
    "toxicology": "What is the mechanistic toxicology, toxicogenomics and hazard of this chemical compound?",
    "variant-analysis": "Analyze and annotate the genetic variant BRAF V600E.",
    "variant-functional-annotation": "Annotate the functional and molecular consequence of a coding missense variant.",
    "variant-interpretation": "Interpret the clinical significance of a germline variant for a patient.",
    "variant-to-mechanism": "Trace the path from a pathogenic variant to its downstream functional mechanism.",
}


@pytest.fixture(scope="module")
def served_index():
    """Build the find_skill index from the REAL served bodies (deploy/persona-*.md)."""
    staging = Path(tempfile.mkdtemp())
    try:
        for p in _DEPLOY.glob("persona-*.md"):
            name = p.stem[len("persona-"):]
            if name not in _EXCLUDE:
                shutil.copy(p, staging / f"{name}.md")
        yield build_index(staging)
    finally:
        shutil.rmtree(staging)


def test_catalog_covers_every_served_skill(served_index):
    """Every served skill has exactly one typical question (no drift in either direction)."""
    served = {d.name for d in served_index}
    assert set(CATALOG) == served, (
        f"missing questions: {served - set(CATALOG)}; extra: {set(CATALOG) - served}"
    )


@pytest.mark.parametrize("skill,question", sorted(CATALOG.items()))
def test_typical_question_routes_to_its_skill(served_index, skill, question):
    """find_skill ranks each skill's own typical question within the top-3 results."""
    names = [h.name for h in search(served_index, question, limit=3)]
    assert skill in names, f"{skill!r} not in top-3 for its question; got {names}"
