"""Descriptions promising a derived aggregate the return schema never declares (DSR-664).

An agent that reads "returns frequencies" and receives raw per-record rows with no
denominator presents counts as rates. That is the defect, and it is not a schema problem the
agent can see: the description is the only surface it reads before calling.

**This reports; it never fails the build.** Detection is mechanical, adjudication is not --
roughly four in five hits turn out truthful under a differently-named field, a nested block,
or a word that is not a statistic at all ("clade distribution", "publication frequency").
A gate on this would be red forever and would be switched off within a week.

Two things the mechanical rule cannot do, both handled by hand below.

It cannot see a promise made outside a returns-clause: ``GDC_get_mutation_frequency`` says
"Get pan-cancer mutation frequency statistics" in its opening sentence and never repeats it.

And it cannot see the canonical case at all. ``cBioPortal_get_mutations`` promises *nothing*
-- "Get mutation data for specific genes in a cancer study" -- and returns ``sampleId`` /
``patientId`` / ``proteinChange`` rows with no denominator anywhere. The overclaim is in the
silence: nothing tells the agent these are not frequencies, and the tool's subject matter
invites exactly that reading. Named additions carry cases like that into the queue.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["ADJUDICATED", "AGGREGATES", "Claim", "NAMED_ADDITIONS", "genuine_overclaims",
           "review_queue", "unadjudicated"]

# Words naming a derived quantity -- something computed over a set, which the caller cannot
# recover from rows alone without the denominator.
AGGREGATES = ("frequency", "frequencies", "prevalence", "rate", "rates", "enrichment",
              "proportion", "percentage", "incidence", "distribution", "ratio",
              "average", "mean", "median", "density", "score")

# Forms the schemas actually use for the same quantity. Observed while adjudicating, not
# guessed: `obsExp` for a ratio, `BAVER` for an average, `af` for allele frequency,
# `casesPerOneMillion` for a rate.
_SCHEMA_FORMS = {
    "frequency": ("freq", "maf", "af", "allele_freq"),
    "frequencies": ("freq", "maf", "af", "allele_freq"),
    "prevalence": ("prevalen", "pct", "percent"),
    "rate": ("rate", "per_", "peronemillion", "pct", "percent"),
    "rates": ("rate", "per_", "peronemillion", "percent"),
    "enrichment": ("enrich", "fold", "p_value", "pvalue", "fdr"),
    "proportion": ("proport", "pct", "percent", "fraction"),
    "percentage": ("pct", "percent"),
    "incidence": ("inciden", "prevalen", "rate"),
    "distribution": ("distrib", "histogram", "bins", "timeline"),
    "ratio": ("ratio", "obsexp", "fold", "_over_"),
    "average": ("avg", "average", "mean", "gravy", "baver"),
    "mean": ("mean", "avg", "average"),
    "median": ("median", "q0.50", "p50"),
    "density": ("densit",),
    "score": ("score", "lrs", "coverage", "p_value"),
}

_RETURNS_CLAUSE = re.compile(
    r"[^.]*\b(?:returns?|returning|provides?|reports?|yields?)\b[^.]*\.", re.IGNORECASE
)

# Cases the mechanical rule cannot reach, carried into the queue by name.
NAMED_ADDITIONS = {
    "cBioPortal_get_mutations":
        "promises nothing and returns per-sample rows with no denominator; the silence is "
        "the overclaim",
    "GDC_get_mutation_frequency":
        "promises frequency in its opening sentence, outside any returns-clause",
}

# verdict -> one of "overclaim", "undeclared-schema", "truthful"
ADJUDICATED: dict[str, tuple[str, str]] = {
    # --- genuine overclaims: a count or a text section offered as a rate ---
    "cBioPortal_get_mutations": ("overclaim",
        "returns per-sample mutation rows with no cohort denominator; nothing says these "
        "are not frequencies. The canonical instance."),
    "GDC_get_mutation_frequency": ("overclaim",
        "named 'frequency' and described as frequency statistics; returns an SSM "
        "occurrence count with no denominator"),
    "DailyMed_parse_adverse_reactions": ("overclaim",
        "says 'Returns AE frequencies'; returns parsed label text and a count"),
    "EPMC_get_article_genes": ("overclaim",
        "says 'mention frequency'; returns annotation_counts with no token total"),
    "EPMC_get_article_diseases": ("overclaim", "as EPMC_get_article_genes"),
    "EPMC_get_article_chemicals": ("overclaim", "as EPMC_get_article_genes"),
    "EPMC_get_article_organisms": ("overclaim", "as EPMC_get_article_genes"),

    # --- cannot be checked either way: no return_schema at all ---
    "MonarchV3_phenotype_similarity_search": ("undeclared-schema",
        "promises a ranked overlap score and declares no return_schema"),
    "competition_landscape": ("undeclared-schema",
        "promises a 0-1 competition score and declares no return_schema; ours to fix"),
    "enrichr_gene_enrichment_analysis": ("undeclared-schema",
        "promises enrichment terms and declares no return_schema"),
    "organs_at_risk": ("undeclared-schema",
        "promises a 0-1 normal-tissue toxicity score and declares no return_schema; ours"),
    "shedding_risk": ("undeclared-schema",
        "promises a shedding-risk score and declares no return_schema; ours"),
    "patent_landscape": ("undeclared-schema",
        "promises a landscape score and declares no return_schema; ours"),
    "pdbe_get_entry_observed_residues_ratio": ("truthful",
        "the ratio is the tool's whole subject and arrives inside the data block"),

    # --- truthful: the quantity is there under another name, nested, or is not a statistic ---
    "ClinGenAR_get_external_records": ("truthful",
        "'frequencies' describes what the linked databases hold, not its own return"),
    "EBIProteins_get_variation": ("truthful", "as above: names gnomAD/ExAC as sources"),
    "Crossref_get_journal": ("truthful",
        "'publication frequency' is a journal's cadence, not a computed rate"),
    "DataQuality_assess": ("truthful", "the mean sits inside the per-column detail block"),
    "Dfam_get_family": ("truthful", "'clade distribution' is taxonomic spread; see clades"),
    "POWO_search_plants": ("truthful", "'distribution' is geographic range, not statistical"),
    "DiseaseSH_get_vaccine_coverage": ("truthful", "the percentage sits inside timeline"),
    "EVA_get_variants_by_gene": ("truthful", "allele frequencies nested under sourceEntries"),
    "EVA_get_variants_by_region": ("truthful", "as EVA_get_variants_by_gene"),
    "EnsemblReg_get_binding_matrix": ("truthful", "the matrix IS the frequency matrix"),
    "GTDB_get_genome": ("truthful", "coding density nested under metadata_gene"),
    "GTEx_get_gene_expression": ("truthful",
        "returns per-sample values so the caller can compute a distribution, and says so"),
    "JPLHorizons_get_body_data": ("truthful", "returns the raw Horizons text in result"),
    "MaveDB_search_score_sets": ("truthful", "returns score SETS, not scores"),
    "NeuroMorpho_get_morphometry": ("truthful", "diameter is the average diameter"),
    "PDB_REDO_get_structure_quality": ("truthful", "BAVER is the average B-factor"),
    "PDBe_get_residue_listing": ("truthful",
        "'electron density' explains observed_ratio; not a returned aggregate"),
    "PyPIPackageInspector": ("truthful",
        "release frequency is carried by days_since_last_release"),
    "STRING_get_functional_annotations": ("truthful",
        "lists annotation categories; enrichment is STRING_ppi_enrichment's job"),
    "STRING_get_network": ("truthful", "as STRING_get_functional_annotations"),
    "SoilGrids_get_properties": ("truthful", "bulk density is a mapped layer property"),
    "TIMER2_survival_association": ("truthful",
        "median survival sits inside the two expression-group blocks"),
    "UCSC_get_cpg_islands": ("truthful", "obsExp is the observed/expected ratio"),
    "USGSWater_get_streamflow": ("truthful", "flow rate is a measured value, not derived"),
    "eQTL_list_datasets": ("truthful", "'transcript ratio' glosses a quant_method enum"),
    "euhealthinfo_search_cancer": ("truthful",
        "describes what the listed datasets contain, not its own return"),
    "euhealthinfo_search_primary_care_workforce": ("truthful", "as euhealthinfo_search_cancer"),
    "gather_disease_profile": ("truthful", "prevalence nested inside profile"),
    "gnomad_get_sv_by_gene": ("truthful", "af is the allele frequency"),
    "gnomad_get_sv_by_region": ("truthful", "af is the allele frequency"),
    "gnomad_get_sv_detail": ("truthful", "af is the allele frequency"),
    "ThreeDBeacons_get_structures": ("truthful", "coverage carries the per-model score"),
    "GeneNetwork_get_trait_info": ("truthful", "lrs is the likelihood-ratio statistic"),
    "MODOMICS_get_modification": ("truthful", "mass_avg is the average mass"),
    "ProtParam_calculate": ("truthful", "gravy is the grand average of hydropathy"),
    "GMrepo_search_species": ("truthful", "pct_of_all_samples is the prevalence"),
    "DiseaseSh_get_country_stats": ("truthful", "casesPerOneMillion is the rate"),
    "DiseaseSh_get_global_stats": ("truthful", "activePerOneMillion is the rate"),
    "Orphanet_get_epidemiology": ("truthful", "prevalences and mean_value are declared"),
    "DoseResponse_compare_potency": ("truthful", "ic50_fold_shift_b_over_a is the ratio"),
    "OpenFoodFacts_search_products": ("truthful", "nutriscore fields are declared per-100g"),
    "FinnGen_get_region_associations": ("truthful", "maf is the minor allele frequency"),
    "STRING_ppi_enrichment": ("truthful", "p_value is the enrichment statistic"),
}


class Claim:
    """One description promising an aggregate its return schema does not declare."""

    def __init__(self, tool: str, promised: list[str], declared: list[str], note: str = ""):
        self.tool = tool
        self.promised = promised
        self.declared = declared
        self.note = note

    @property
    def verdict(self) -> str:
        return ADJUDICATED.get(self.tool, ("unreviewed", ""))[0]

    @property
    def reason(self) -> str:
        return ADJUDICATED.get(self.tool, ("", "not yet adjudicated"))[1]

    @property
    def message(self) -> str:
        """The first eight declared fields, saying so when there are more.

        A reader deciding whether the promised quantity is present under another name must
        know the list was cut -- otherwise a truthful tool with a ninth field named
        `allele_frequency` reads as an overclaim. Total shown for exactly that reason.
        """
        shown = self.declared[:8]
        total = len(self.declared)
        if not total:
            fields = "(no return_schema)"
        elif total > len(shown):
            fields = f"{', '.join(shown)} (+{total - len(shown)} more of {total})"
        else:
            fields = ", ".join(shown)
        return (f"{self.tool}: promises {', '.join(self.promised)}; "
                f"declares {fields} -> {self.verdict}: {self.reason}")

    def __repr__(self) -> str:
        return f"<Claim {self.tool} {self.promised} {self.verdict}>"


def _return_fields(tool: dict) -> set[str]:
    from .description_contract import _return_fields as fields

    return fields(tool)


def review_queue(tools: dict[str, dict]) -> list[Claim]:
    """Every tool promising an aggregate it does not declare, plus the named additions."""
    claims: list[Claim] = []
    for name, tool in sorted(tools.items()):
        description = tool.get("description") or ""
        clause = " ".join(_RETURNS_CLAUSE.findall(description)).lower()
        declared = sorted(_return_fields(tool))
        schema_text = " ".join(declared).lower()

        promised = [
            word for word in AGGREGATES
            if clause and re.search(rf"\b{word}\b", clause)
            and not any(form in schema_text for form in _SCHEMA_FORMS[word])
        ]
        note = NAMED_ADDITIONS.get(name, "")
        if promised or note:
            claims.append(Claim(name, promised or ["(by name)"], declared, note))
    return claims


def unadjudicated(tools: dict[str, dict]) -> list[Claim]:
    """Queue entries nobody has ruled on yet. The list a human works through."""
    return [claim for claim in review_queue(tools) if claim.verdict == "unreviewed"]


def genuine_overclaims(tools: dict[str, dict]) -> list[Claim]:
    """The follow-up path: entries ruled a real overclaim, and those with no schema."""
    return [
        claim for claim in review_queue(tools)
        if claim.verdict in {"overclaim", "undeclared-schema"}
    ]


def report(tools: dict[str, dict]) -> str:
    """The queue as text, grouped by verdict. Printed, never asserted on."""
    claims = review_queue(tools)
    lines = [f"aggregate-claim review queue: {len(claims)} entries"]
    for verdict in ("overclaim", "undeclared-schema", "unreviewed", "truthful"):
        group = [c for c in claims if c.verdict == verdict]
        if not group:
            continue
        lines.append(f"\n{verdict} ({len(group)}):")
        lines += [f"  {c.message}" for c in group]
    return "\n".join(lines)


def data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data"
