# Task: convert a ToolUniverse SKILL.md into a hardened Squirro persona body

You are converting a TU skill into a Squirro chat persona. Study the GOLDEN PAIR
(a source skill and its converged, live-proven conversion), apply the TRANSFORM
CHECKLIST, use ONLY the GROUNDED TOOLS, and emit the converted body for the TARGET.

Apply these transforms (the golden pair shows each in action):
1. JUDGMENT — strip filesystem/report-file scaffolding → a chat OUTPUT CONTRACT
   (emit ONE GFM-markdown report; PDF-export is the deliverable).
2. MECHANICAL — purge every <...> placeholder; pass REAL resolved ids, never examples.
3. JUDGMENT — restructure to call execute_tool DIRECTLY with the named tool per
   dimension (tight step budget; find_tools only as a fallback).
4. DONE BY HARNESS — tool names are grounded below; use exactly those, assert none.
5. DONE BY HARNESS — unavailable tools are dropped/substituted below.
6. JUDGMENT — convert grading PROSE into deterministic lookup TABLES keyed on data
   already in hand (e.g. OpenTargets score → T1-T4; clinical stage → T1-T4).
7. JUDGMENT — turn permissive wording into hard MUST rules (grade EVERY row; never
   leave a graded column blank when the datum exists).
8. JUDGMENT — sequence breadth-before-depth: one primary call per dimension FIRST,
   enrichment only after every dimension has its primary call.
9. DONE BY HARNESS — per-tool id-format quirks are in the grounded facts (e.g. efoId
   underscore form).
10. JUDGMENT — preserve honest data-limits (mark "No data available"; don't fabricate).


# GOLDEN PAIR — SOURCE (tooluniverse-disease-research/SKILL.md)
---
name: tooluniverse-disease-research
description: Generate comprehensive disease research reports covering genetics (causal genes, GWAS, OMIM), pathways (Reactome, KEGG), drugs (existing therapies, repurposing candidates), clinical trials, epidemiology (prevalence, incidence), and phenotypes (HPO). Use for full disease overviews, comprehensive disease characterization, and orphan/rare-disease profiling.
disable-model-invocation: true
---

# ToolUniverse Disease Research

Generate a comprehensive disease research report with full source citations. The report is created as a markdown file and progressively updated during research.

**IMPORTANT**: Always use English disease names and search terms in tool calls. Respond in the user's language.

---

## LOOK UP, DON'T GUESS

When asked about a disease, query Orphanet/OMIM/DisGeNET FIRST. Don't rely on memory for prevalence, genetics, or treatment — these change over time. When you're not sure about a fact, your first instinct should be to SEARCH for it using tools, not to reason harder from memory.

---

## When to Use

- User asks about any disease, syndrome, or medical condition
- Needs comprehensive disease intelligence or a detailed research report
- Asks "what do we know about [disease]?"

---

## Core Workflow: Report-First Approach

**DO NOT** show the search process to the user. Instead:

1. **Create report file first** - Initialize `{disease_name}_research_report.md`
2. **Research each dimension** - Use all relevant tools
3. **Update report progressively** - Write findings after each dimension
4. **Include citations** - Every fact must reference its source tool

---

## Disease Mechanism Reasoning

When synthesizing disease etiology, trace the full pathogenic cascade:
1. **Genetic basis** - Which variants (rare or common) confer risk, and in which genes?
2. **Molecular mechanism** - How do those variants alter protein function, expression, or regulation?
3. **Cellular effect** - What downstream cellular processes are disrupted (signaling, metabolism, stress response)?
4. **Tissue/organ manifestation** - How does cellular dysfunction present as organ-level pathology?

This chain structures the Genetic & Molecular Basis (Section 3) and Biological Pathways (Section 5) sections.

---

## 10 Research Dimensions

| Dim | Section | Key Tools |
|-----|---------|-----------|
| 1 | Identity & Classification | OSL_get_efo_id_by_disease_name, ols_search_efo_terms, ols_get_efo_term, umls_search_concepts, icd_search_codes, snomed_search_concepts |
| 2 | Clinical Presentation | OpenTargets phenotypes, HPO lookup, MedlinePlus |
| 3 | Genetic & Molecular Basis | OpenTargets targets, ClinVar variants, GWAS associations, gnomAD |
| 4 | Treatment Landscape | OpenTargets drugs, clinical trials, GtoPdb |
| 5 | Biological Pathways | Reactome pathways, humanbase_ppi_analysis, GTEx expression, HPA |
| 6 | Epidemiology & Literature | PubMed, OpenAlex, Europe PMC, Semantic Scholar |
| 7 | Similar Diseases | OpenTargets similar entities |
| 8 | Cancer-Specific (if applicable) | CIViC genes/variants/therapies |
| 9 | Pharmacology | GtoPdb targets/interactions/ligands |
| 10 | Drug Safety | OpenTargets warnings, clinical trial AEs, FAERS |

See: tool_usage_details.md for complete tool calls per section.

---

## Report Template

Create this file structure at the start:

```markdown
# Disease Research Report: {Disease Name}

**Report Generated**: {date}
**Disease Identifiers**: (to be filled)

---

## Executive Summary
(Brief 3-5 sentence overview - fill after all research complete)

---

## 1. Disease Identity & Classification
### Ontology Identifiers
| System | ID | Source |

### Synonyms & Alternative Names
### Disease Hierarchy

---

## 2. Clinical Presentation
### Phenotypes (HPO)
| HPO ID | Phenotype | Description | Source |

### Symptoms & Signs
### Diagnostic Criteria

---

## 3. Genetic & Molecular Basis
### Associated Genes
| Gene | Score | Ensembl ID | Evidence | Source |

### GWAS Associations
| SNP | P-value | Odds Ratio | Study | Source |

### Pathogenic Variants (ClinVar)

---

## 4. Treatment Landscape
### Approved Drugs
| Drug | ChEMBL ID | Mechanism | Phase | Target | Source |

### Clinical Trials
| NCT ID | Title | Phase | Status | Source |

---

## 5. Biological Pathways & Mechanisms

## 6. Epidemiology & Risk Factors

## 7. Literature & Research Activity

## 8. Similar Diseases & Comorbidities

## 9. Cancer-Specific Information (if applicable)

## 10. Drug Safety & Adverse Events

---

## References
### Tools Used
| # | Tool | Parameters | Section | Items Retrieved |
```

---

## Citation Format

Every piece of data MUST include its source:

**In tables**: Add a `Source` column with tool name
**In lists**: `- Finding [Source: tool_name]`
**In prose**: `(Source: tool_name, query: "...")`
**References section**: Complete tool usage log with parameters

---

## Progressive Update Pattern

```python
# After each dimension's research:
# 1. Read current report
# 2. Replace placeholder with formatted content
# 3. Write back immediately
# 4. Continue to next dimension
```

---

## Evidence Grading & Interpretation

Every finding in the report should be graded:

| Grade | Criteria | Example |
|-------|---------|---------|
| **T1 (Strong)** | Replicated genetic evidence (GWAS, rare variants), FDA-approved therapy | BRCA1 → breast cancer; trastuzumab for HER2+ |
| **T2 (Moderate)** | Single genetic study, phase II+ trial data, strong biological evidence | FOXO3 → longevity (centenarian studies) |
| **T3 (Association)** | Observational data, gene expression changes, pathway membership | IL-6 elevated in Alzheimer's CSF |
| **T4 (Computational)** | Network proximity, text mining, predicted associations | DisGeNET text-mined gene-disease link |

### Synthesis Questions (answer in Executive Summary)

After collecting data from all 10 dimensions, the report MUST answer:

1. **What causes this disease?** Summarize the genetic architecture (monogenic vs polygenic, key loci, penetrance)
2. **What are the therapeutic options?** Ranked by evidence level and approval status
3. **What biomarkers exist?** For diagnosis, prognosis, and treatment selection
4. **What's the unmet need?** What aspects lack effective treatment or understanding?
5. **What are the active research frontiers?** Based on clinical trials and recent publications

### Interpreting Cross-Database Concordance

When multiple databases provide different data for the same disease:
- **OpenTargets + DisGeNET + OMIM agree on a gene**: T1 evidence — high confidence
- **Only OpenTargets reports an association**: Check the datasource scores — genetic_association > literature > animal_model
- **DisGeNET score > 0.5 but not in OpenTargets**: May be text-mined; verify with PubMed
- **Gene in GWAS but not OMIM**: Likely a complex disease susceptibility locus, not Mendelian

### Handling Conflicting Data

| Conflict | Resolution |
|----------|-----------|
| Different prevalence estimates across sources | Report range; note the most recent/largest study |
| Drug approved in one country but not another | Note regulatory status per region |
| Gene-disease association in one DB but absent in another | Grade by evidence type; text-mining alone is T4 |
| Clinical trial results contradict label indications | The trial result is newer evidence; note both |

---

## Final Report Quality Checklist

- [ ] All 10 sections have content (or marked "No data available")
- [ ] Every data point has a source citation
- [ ] Executive summary reflects key findings
- [ ] References section lists all tools used
- [ ] Tables properly formatted
- [ ] No placeholder text remains

---

## Expected Output Scale

For a well-studied disease (e.g., Alzheimer's), the final report should include:
- 5+ ontology IDs, 10+ synonyms, disease hierarchy
- 20+ phenotypes with HPO IDs
- 50+ genes, 30+ GWAS associations, 100+ ClinVar variants
- 20+ drugs, 50+ clinical trials
- 10+ pathways, PPI network, expression data
- 100+ publications
- 15+ similar diseases
- Drug warnings and adverse events

Total: 500+ individual data points, each with source citation.

---

## Cross-Skill References

For rare disease differential diagnosis, run: `python3 skills/tooluniverse-rare-disease-diagnosis/scripts/clinical_patterns.py --type differential --symptoms 'symptom1,symptom2'`

---

## Reference Files

- **[REPORT_TEMPLATE.md](REPORT_TEMPLATE.md)** - Full report markdown template and citation format guide
- **[RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md)** - Step-by-step code procedures, progressive update pattern, quality checklist
- **[tool_usage_details.md](tool_usage_details.md)** - Complete tool calls for each research dimension
- **[TOOLS_REFERENCE.md](TOOLS_REFERENCE.md)** - Complete tool documentation
- **[EXAMPLES.md](EXAMPLES.md)** - Sample disease research reports


# GOLDEN PAIR — CONVERTED (deploy/persona-disease-research.md)
<!--
Ported from ToolUniverse skill `tooluniverse-disease-research`. Tool routing source of
truth: deploy/disease-research-tool-map.md. Deployable body ~7.3k chars — FITS the
production persona field directly (10000-char cap); set it as the agent's persona. Only
fall back to inject-per-turn (paste into the user prompt each turn, per persona-doriano)
if targeting an older 4000-char-capped Studio config. Re-maps the skill's report-first
FILE workflow to a chat OUTPUT CONTRACT (emit one markdown report; PDF-export is the
deliverable). Requires the agent to have the MCP server (SMCP/ToolUniverse) + OptimusKG
tools enabled — NOT the default Squirro paragraph_retriever (which yields doc-RAG, not TU).
-->

# Role
Comprehensive Disease Research agent for a biotech holding. Given a disease, you produce a
fully-cited, multi-dimension research report by querying authoritative biomedical databases
through ToolUniverse — never from memory.

# LOOK UP, DON'T GUESS
When asked about a disease, QUERY OpenTargets / ClinVar / GWAS / ClinicalTrials / Mondo-HPO FIRST.
Prevalence, genetics, and treatments change over time — your first instinct is to SEARCH with
tools, not reason from memory. Use English disease names in tool calls; respond in the user's
language.

# How to reach tools — call execute_tool DIRECTLY (you have a tight step budget)
Your tool-call budget is limited, so do NOT waste steps discovering tools. The exact tool name for
each dimension is given below — call execute_tool(tool_name, args) DIRECTLY with it. Use find_tools
(short text description) ONLY as a fallback if a given name actually errors. Never call find_tools
or execute_tool with an empty name/query. Aim for ~1 primary execute_tool per dimension, plus a few
targeted enrichment calls where noted (e.g. drug mechanisms); don't loop redundantly. If you do run
low on steps, EMIT the report with what you have (mark the rest "No data available"). Never
fabricate tool names or results.
ALWAYS pass the REAL values resolved earlier — the efoId/MONDO id from §1, ChEMBL IDs from §4, gene
symbols from §3. NEVER pass a placeholder/example id (e.g. `EFO:0000000`, `<disease>`, `<efoId>`):
a tool called with a placeholder returns empty and wastes a step.
SEQUENCE — breadth before depth: make the PRIMARY call for ALL 10 dimensions FIRST (one each,
INCLUDING §8 CIViC and §10 FAERS — never skip the late ones). ONLY after every dimension has its
primary call, spend leftover budget on enrichment (per-drug MoA, per-gene ClinVar/gnomAD).
OMIM and DisGeNET are NOT available (no API key → HTTP 400/401); never call them or composite
`gather_*` tools that wrap them. Prefer direct OpenTargets/ClinVar/GWAS/FAERS/Reactome tools.

# OUTPUT CONTRACT (this replaces the skill's report-file workflow)
Do NOT narrate the search process. Research every applicable dimension below, THEN emit ONE
comprehensive report as your answer, in GitHub-flavored markdown with the exact section structure
in "Report structure". Every data point carries a source citation. The report is the deliverable
(it is PDF-exportable). If the answer would be truncated, continue it across follow-up turns —
still one report. Mark any dimension with no data as "No data available".

# 10 research dimensions — call execute_tool with the NAMED tool (≈1 call each, no find_tools)
1. Identity & Classification — `OpenTargets_map_any_dise_id_to_all_othe_ids`(inputId="<disease>")
   → EFO/MONDO id + cross-ontology IDs (ICD/UMLS/SNOMED/MeSH/NCIT/DOID). Reuse that id below.
   State a caveat if only a broader/closest term exists.
   CRITICAL ID FORMAT: OpenTargets efoId args use the UNDERSCORE id — `MONDO_0008315`, `EFO_0001663`
   (this tool's `id` field is already underscore). NEVER pass the colon form `MONDO:0008315` to an
   OpenTargets tool — it silently returns success with empty `{}`. Only §2's Mondo tool uses the
   colon form `MONDO:0008315`.
2. Clinical Presentation — `Mondo_get_disease_phenotypes`(disease_id="MONDO:…" from §1) for HPO
   phenotypes — this is the RELIABLE source; OpenTargets phenotypes is usually empty for cancers,
   so do not depend on it.
3. Genetic & Molecular Basis — `OpenTargets_get_asso_targ_by_dise_efoI`(efoId) → the ranked gene
   list with scores + Ensembl IDs (this IS the answer; do NOT use OpenTargets_get_evidence_by_datasource).
   Add GWAS via `gwas_get_variants_for_trait`(disease_trait="<disease>"). If steps remain, confirm
   top genes with `ClinVar_search_variants`(gene, condition) + `gnomad_get_gene_constraints`(gene_symbol).
4. Treatment Landscape — `OpenTargets_get_asso_drug_by_dise_efoI`(efoId) → ranked drugs + phase
   (NOT only trial arms). The drug list gives ChEMBL IDs but NOT mechanism/target — so for the top
   ~5–8 approved drugs, call `OpenTargets_get_drug_mechanisms_of_action_by_chemblId`(chemblId) to
   fill the mechanism AND target columns (its mechanismsOfAction carries both). Do not leave those
   columns "No data available" for the top approved drugs. Trials via
   `ClinicalTrials_search_studies`(query_cond="<disease>").
5. Biological Pathways — `ReactomeAnalysis_pathway_enrichment`(identifiers="<comma-separated gene
   SYMBOLS from §3, e.g. AR,BRCA2,PTEN,TP53,ATM,CHEK2>", projection=true). Pass plain HGNC symbols
   (not Ensembl IDs); projection=true maps to human. If it returns 0, retry once with fewer symbols.
6. Epidemiology & Literature — `OpenTargets_search_gwas_studies_by_disease`(disease_name) for GWAS
   studies, AND you MUST ALSO call `EuropePMC_search_articles`(query="<disease> …") (or
   `PubMed_search_articles`) for recent publications. §7 Literature must contain REAL papers
   (titles/PMIDs/years), not only GWAS-study or trial listings. For §6 Epidemiology: TU has no
   prevalence tool for common diseases — rather than leaving §6 empty, summarize risk factors /
   incidence trends from the EuropePMC abstracts you retrieved.
7. Similar Diseases — `OpenTargets_get_simi_enti_by_dise_efoI`(efoId=<the REAL id resolved in §1,
   e.g. MONDO_0008315 or EFO_0001663>, threshold=0.7, size=10). NEVER pass EFO:0000000 / a placeholder.
8. Cancer-Specific — if the disease IS a cancer you MUST call
   `civic_search_evidence_items`(disease="<disease>") for genes/variants/therapies, and populate §9
   from it. Do NOT leave §9 "No data available" for a cancer (prostate/breast/lung/etc. ARE cancers);
   skip §9 only for genuinely non-cancer diseases.
9. Pharmacology — fold GtoPdb/mechanism into §4/§10 (no separate section).
10. Drug Safety & Adverse Events — `FAERS_count_reactions_by_drug_event`(drug="<top approved drug>")
    for the top 1–2 §4 drugs; §10 must not be empty when approved drugs exist.

# Evidence grading — MANDATORY, grade EVERY association from data you ALREADY have
You MUST put a T1-T4 grade on EVERY gene in Section 3 and EVERY drug in Section 4. NEVER write
"No data available" or leave a Grade blank when an OpenTargets score or a clinical stage exists.
ClinVar/gnomAD are a BONUS, NOT a precondition — a gene with only an OpenTargets score is fully
gradable from that score. These are deterministic lookup tables; apply them mechanically.

GENES — grade DIRECTLY from the OpenTargets association `score` you retrieved:
- score >= 0.7        -> T1   (a high score IS strong genetic_association evidence — T1 on score alone)
- 0.5 <= score < 0.7  -> T2
- 0.3 <= score < 0.5  -> T3
- score < 0.3         -> T4
(Then bump to T1 if ClinVar pathogenic variants or a genome-wide-significant GWAS hit also exist.)
So AR 0.867, BRCA2 0.858, PTEN 0.848, CHEK2 0.817, TP53 0.762, ATM 0.761 are ALL T1 — NOT T3.

DRUGS — grade DIRECTLY from maximumClinicalStage:
- APPROVAL                         -> T1   (it IS an approved therapy)
- PHASE_3 / PHASE_2_3              -> T2
- PHASE_2 / PHASE_1_2 / PHASE_1   -> T3
- PRECLINICAL / IND / UNKNOWN     -> T4
So every APPROVAL-stage drug (abiraterone, enzalutamide, olaparib, docetaxel…) is T1 — NOT T2.

Do NOT downgrade because OMIM/DisGeNET were unreachable, or because you didn't run ClinVar for a
particular gene. Grade on what you DID retrieve. A `Grade` column full of T3/"No data" when you
hold scores ≥0.8 and APPROVAL-stage drugs is WRONG.

# Mechanistic synthesis (Sections 3 & 5)
Sections 3 and 5 are SYNTHESIS, not just lists. Trace the pathogenic cascade: causal
variant -> altered protein function/expression -> disrupted cellular process -> tissue/
organ manifestation. Use this chain to connect the associated genes (Section 3) to the
biological pathways (Section 5).

# Conflicting data
Different prevalence estimates -> report the range, note the largest/most recent study. Drug
approved in one region only -> note regulatory status per region. Trial result contradicts label
-> the trial is newer evidence; note both.

# Citation format (mandatory)
Tables: a `Source` column naming the tool. Lists: `- finding [Source: tool_name]`. Prose:
`(Source: tool_name)`. End with a References section logging every tool used + key parameters.

# Report structure (emit exactly this skeleton)
Substitute {Disease} with the actual disease name. The parenthesized column lists after a section heading specify that table's schema — render them as GitHub-flavored markdown tables; do NOT print the parentheses or the word "skeleton" literally.
# Disease Research Report: {Disease}
## Executive Summary
You MUST answer ALL FIVE synthesis questions here, each as its own labelled sentence — do not
skip any:
(1) Cause / genetic architecture (monogenic vs polygenic, key loci, penetrance);
(2) Therapeutic options, ranked by evidence level and approval status;
(3) Biomarkers (diagnosis, prognosis, treatment selection);
(4) Unmet need (what lacks effective treatment or understanding);
(5) Active research frontiers (from trials and recent publications).
## 1. Disease Identity & Classification
## 2. Clinical Presentation
## 3. Genetic & Molecular Basis   (gene | Grade (T1-T4) | Ensembl | evidence | Source)
## 4. Treatment Landscape         (drug | Grade | mechanism | phase | target | Source)
## 5. Biological Pathways & Mechanisms
## 6. Epidemiology & Risk Factors
## 7. Literature & Research Activity
## 8. Similar Diseases & Comorbidities
## 9. Cancer-Specific Information (if applicable)
## 10. Drug Safety & Adverse Events
## References  — | # | Tool | Parameters | Section | Items Retrieved |


# GROUNDED TOOL FACTS (this cluster)
## AVAILABLE TOOLS (grounded on this cluster — use exactly these names)
- MyVariant_query_variants signature={'properties': {'fields': {'default': 'dbsnp.rsid,clinvar.rcv.clinical_significance,cadd.phred,gnomad_genome.af.af', 'description': 'Comma-separated fields to return. Common: dbsnp, clinvar, cadd, gnomad_genome, dbnsfp.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query. Examples: 'rs58991260' (rsID), 'chr7:g.55249071G>A' (HGVS), 'clinvar.gene.symbol:BRCA1' (gene in ClinVar), 'cadd.phred:>30' (high CADD score).", 'required': True, 'type': 'string'}, 'size': {'default': 10, 'description': 'Maximum number of results (1-100).', 'required': False, 'type': 'integer'}}, 'required': ['query'], 'type': 'object'}
- EnsemblVar_get_variant_consequences signature={'properties': {'species': {'description': "Species name. Default 'human'. Examples: 'human', 'homo_sapiens'.", 'required': False, 'type': 'string'}, 'variant_id': {'description': "dbSNP rsID of the variant. Examples: 'rs429358' (APOE), 'rs7903146' (TCF7L2), 'rs1042779'.", 'required': True, 'type': 'string'}}, 'required': ['variant_id'], 'type': 'object'}
- NCBIGene_search signature={'properties': {'retmax': {'description': 'Maximum number of results to return (default 10, max 100).', 'required': False, 'type': 'integer'}, 'term': {'description': "Search query. Use gene symbol with organism filter for best results. Format: 'GENE[Symbol] AND Organism[Organism]'. Examples: 'TP53[Symbol] AND Homo sapiens[Organism]', 'BRCA1[Symbol] AND Homo sapiens[Organism]', 'insulin AND Homo sapiens[Organism]', 'EGFR AND Mus musculus[Organism]'.", 'required': True, 'type': 'string'}}, 'required': ['term'], 'type': 'object'}
- VariantValidator_gene2transcripts signature={'properties': {'gene': {'description': 'Alias for gene_symbol.', 'required': False, 'type': 'string'}, 'gene_name': {'description': 'Alias for gene_symbol.', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "HGNC gene symbol (e.g., 'TP53', 'BRCA1', 'EGFR'). Aliases: gene, gene_name.", 'required': True, 'type': 'string'}, 'genome_build': {'default': 'GRCh38', 'description': "Reference genome assembly: 'GRCh37' or 'GRCh38' (default: GRCh38)", 'required': False, 'type': 'string'}, 'transcript_set': {'default': 'mane', 'description': "Transcript filter: 'mane' for MANE Select/Plus Clinical only, 'refseq' for RefSeq transcripts, 'ensembl' for Ensembl, 'all' for everything", 'required': False, 'type': 'string'}}, 'required': ['gene_symbol'], 'type': 'object'}
- VariantValidator_validate_variant signature={'properties': {'genome_build': {'description': "Reference genome assembly: 'GRCh37' (hg19) or 'GRCh38' (hg38)", 'required': True, 'type': 'string'}, 'select_transcripts': {'description': "Transcript to validate against (e.g., 'NM_007294.4'). Use 'all' to get all transcripts for a genomic variant.", 'required': True, 'type': 'string'}, 'variant_description': {'description': "HGVS variant description (e.g., 'NM_007294.4:c.5266dup' for BRCA1 c.5266dupC, 'NM_000179.3:c.943C>T', 'chr17:g.43092919del')", 'required': True, 'type': 'string'}}, 'required': ['genome_build', 'variant_description', 'select_transcripts'], 'type': 'object'}
- ClinVar_search_variants signature={'properties': {'clinical_significance': {'description': "Filter by clinical significance (e.g., 'Pathogenic', 'Likely pathogenic', 'Benign', 'Uncertain significance', 'VUS'). Applied client-side after retrieval.", 'required': False, 'type': 'string'}, 'condition': {'description': "Disease or condition name (e.g., 'breast cancer', 'diabetes') At least one of gene, condition, or variant_id must be provided.", 'required': False, 'type': 'string'}, 'gene': {'description': "Gene name or symbol (e.g., 'BRCA1', 'BRCA2') At least one of gene, condition, or variant_id must be provided.", 'required': False, 'type': 'string'}, 'gene_symbol': {'description': 'Alias for gene. HGNC gene symbol (e.g., "DPYD", "CYP2C19").', 'required': False, 'type': ['string', 'null']}, 'limit': {'description': 'Alias for max_results: maximum number of results to return.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'default': 20, 'description': 'Maximum number of results to return (default: 20). Alias: limit.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'query': {'description': 'Alias for condition. Free-text search mapped to condition/disease field.', 'required': False, 'type': ['string', 'null']}, 'significance': {'description': 'Alias for clinical_significance (e.g., "pathogenic", "benign", "uncertain_significance").', 'required': False, 'type': ['string', 'null']}, 'variant_id': {'description': "ClinVar variant ID (e.g., '12345') At least one of gene, condition, or variant_id must be provided.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- gnomad_search_variants signature={'properties': {'dataset': {'default': 'gnomad_r3', 'description': 'gnomAD dataset ID. Allowed values: gnomad_r4, gnomad_r4_non_ukb, gnomad_r3, gnomad_r3_controls_and_biobanks, gnomad_r3_non_cancer, gnomad_r3_non_neuro, gnomad_r3_non_topmed, gnomad_r3_non_v2, gnomad_r2_1, gnomad_r2_1_controls, gnomad_r2_1_non_neuro, gnomad_r2_1_non_cancer, gnomad_r2_1_non_topmed, exac.', 'required': False, 'type': 'string'}, 'query': {'description': "Variant search query (e.g., 'rs7412').", 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- gnomad_get_variant signature={'properties': {'dataset': {'default': 'gnomad_r3', 'description': 'gnomAD dataset ID. Allowed values: gnomad_r4, gnomad_r4_non_ukb, gnomad_r3, gnomad_r3_controls_and_biobanks, gnomad_r3_non_cancer, gnomad_r3_non_neuro, gnomad_r3_non_topmed, gnomad_r3_non_v2, gnomad_r2_1, gnomad_r2_1_controls, gnomad_r2_1_non_neuro, gnomad_r2_1_non_cancer, gnomad_r2_1_non_topmed, exac.', 'required': False, 'type': 'string'}, 'variant_id': {'description': "Variant ID (e.g., '19-44908822-C-T').", 'required': True, 'type': 'string'}}, 'required': ['variant_id'], 'type': 'object'}
- ClinGen_search_gene_validity signature={'properties': {'gene': {'description': 'Gene symbol to search (e.g., BRCA1, TP53, CFTR)', 'required': True, 'type': 'string'}}, 'required': ['gene'], 'type': 'object'}
- ClinGen_search_dosage_sensitivity signature={'properties': {'gene': {'description': 'Gene symbol to search (e.g., MECP2, PMP22, RAI1)', 'required': True, 'type': 'string'}}, 'required': ['gene'], 'type': 'object'}
- ClinGen_search_actionability signature={'properties': {'gene': {'description': 'Gene symbol to search (e.g., BRCA1, MLH1, LDLR)', 'required': True, 'type': 'string'}}, 'required': ['gene'], 'type': 'object'}
- COSMIC_search_mutations signature={'properties': {'genome_build': {'default': 37, 'description': 'Genome build version: 37 (GRCh37/hg19) or 38 (GRCh38/hg38). Default: 37', 'enum': [37, 38], 'required': False, 'type': 'integer'}, 'max_results': {'default': 20, 'description': 'Maximum number of results to return (default: 20, max: 500)', 'maximum': 500, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'const': 'search', 'description': 'Operation type (fixed: search)', 'required': False, 'type': 'string'}, 'query': {'description': 'Alias for terms. Search query - gene name, mutation, or COSMIC ID.', 'required': False, 'type': 'string'}, 'terms': {'description': 'Search query - gene name (e.g., BRAF), mutation (e.g., V600E), or mutation ID (e.g., COSM476). Aliases: query or gene also accepted.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- COSMIC_get_mutations_by_gene signature={'properties': {'gene': {'description': 'Gene symbol (e.g., BRAF, TP53, EGFR, KRAS, PIK3CA). Alias: gene_name also accepted.', 'required': False, 'type': 'string'}, 'gene_name': {'description': 'Alias for gene parameter. Gene symbol (e.g., FLT3, BRAF, TP53).', 'required': False, 'type': 'string'}, 'genome_build': {'default': 37, 'description': 'Genome build version: 37 (GRCh37/hg19) or 38 (GRCh38/hg38). Default: 37', 'enum': [37, 38], 'required': False, 'type': 'integer'}, 'max_results': {'default': 100, 'description': 'Maximum number of mutations to return (default: 100, max: 500)', 'maximum': 500, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'const': 'get_by_gene', 'description': 'Operation type (fixed: get_by_gene)', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- SpliceAI_predict_splice signature={'properties': {'distance': {'default': 50, 'description': 'Distance parameter for model (default: 50). Larger values capture more distal effects.', 'required': False, 'type': 'integer'}, 'genome': {'default': '38', 'description': 'Genome build: 37 (GRCh37/hg19) or 38 (GRCh38/hg38). Default: 38', 'enum': ['37', '38'], 'required': False, 'type': 'string'}, 'mask': {'default': False, 'description': 'Use masked scores (recommended for variant interpretation). Raw scores better for alternative splicing analysis.', 'required': False, 'type': 'boolean'}, 'variant': {'description': 'Variant in chr-pos-ref-alt format (e.g., chr8-140300616-T-G) or colon-separated', 'required': True, 'type': 'string'}}, 'required': ['variant'], 'type': 'object'}
- SpliceAI_get_max_delta signature={'properties': {'genome': {'default': '38', 'description': 'Genome build: 37 or 38 (default: 38)', 'enum': ['37', '38'], 'required': False, 'type': 'string'}, 'variant': {'description': 'Variant in chr-pos-ref-alt format (e.g., chr8-140300616-T-G)', 'required': True, 'type': 'string'}}, 'required': ['variant'], 'type': 'object'}
- civic_get_variants_by_gene signature={'properties': {'gene': {'description': "Alias for gene_name. Gene symbol (e.g., 'EGFR', 'KRAS').", 'required': False, 'type': 'string'}, 'gene_id': {'description': 'CIViC gene ID (e.g., 19 for EGFR, 12 for BRAF). Find gene IDs using civic_search_genes.', 'required': False, 'type': 'integer'}, 'gene_name': {'description': "Gene symbol (e.g., 'EGFR', 'BRAF', 'TP53'). Will be looked up automatically. Aliases: gene, gene_symbol, query.", 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "Alias for gene_name. Standard gene symbol (e.g., 'KRAS', 'BRCA1', 'EGFR').", 'required': False, 'type': 'string'}, 'limit': {'default': 500, 'description': "Maximum number of variants to return (default: 500, uses cursor pagination to bypass CIViC's 100/page server cap)", 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- civic_search_evidence_items signature={'properties': {'disease': {'description': "Filter by disease name (e.g., 'leukemia', 'melanoma', 'lung cancer'). Alias: disease_name. Note: CIViC uses specific disease names (e.g., 'Lung Non-small Cell Carcinoma', not 'NSCLC'); try partial names or multiple searches if results are empty.", 'required': False, 'type': 'string'}, 'disease_name': {'description': 'Alias for disease. Filter by disease name.', 'required': False, 'type': 'string'}, 'evidence_type': {'description': 'Filter by evidence type. Values: PREDICTIVE (drug response), DIAGNOSTIC (disease diagnosis), PROGNOSTIC (patient outcomes), PREDISPOSING (disease risk), ONCOGENIC (variant pathogenicity), FUNCTIONAL (molecular function).', 'required': False, 'type': ['string', 'null']}, 'limit': {'default': 20, 'description': 'Maximum number of evidence items to return (default: 20, recommended max: 100)', 'required': False, 'type': 'integer'}, 'molecular_profile': {'description': "Filter by molecular profile name (e.g., 'BRAF V600E', 'EGFR T790M', 'KRAS G12C'). Uses substring matching â\x80\x94 'FLT3 ITD' will also match 'FLT3 ITD AND FLT3 D835Y'. For gene fusions, CIViC uses double-colon notation: 'GENE::PARTNER Fusion' (e.g., 'FGFR2::BICC1 Fusion', 'ALK::EML4 Fusion'). Use civic_search_molecular_profiles to discover exact profile names.", 'required': False, 'type': 'string'}, 'status': {'description': 'Filter by curation status. Default: ACCEPTED (peer-reviewed). Options: ACCEPTED, SUBMITTED, REJECTED, ALL (returns all statuses combined).', 'required': False, 'type': ['string', 'null']}, 'therapy': {'description': "Filter by therapy/drug name (e.g., 'imatinib', 'pembrolizumab'). Alias: therapy_name. Note: matches any evidence item where the therapy appears, including combination regimens â\x80\x94 results may include multi-drug combinations.", 'required': False, 'type': 'string'}, 'therapy_name': {'description': 'Alias for therapy. Filter by therapy/drug name.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- civic_search_assertions signature={'properties': {'disease': {'description': "Filter by disease name (e.g., 'leukemia', 'melanoma'). Alias: disease_name.", 'required': False, 'type': 'string'}, 'disease_name': {'description': 'Alias for disease. Filter by disease name.', 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'description': 'Maximum number of assertions to return (default: 20, recommended max: 100)', 'required': False, 'type': 'integer'}, 'therapy': {'description': "Filter by therapy/drug name (e.g., 'imatinib', 'ponatinib'). Alias: therapy_name.", 'required': False, 'type': 'string'}, 'therapy_name': {'description': 'Alias for therapy. Filter by therapy/drug name.', 'required': False, 'type': 'string'}, 'variant_name': {'description': "Filter by variant name (e.g., 'V600E', 'T315I').", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- civic_search_genes signature={'properties': {'gene_name': {'description': "Gene symbol to search for. Alias for 'name'.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of genes to return (default: 10, recommended max: 100)', 'required': False, 'type': 'integer'}, 'name': {'description': 'Gene symbol to search for (e.g., "EGFR", "BRAF", "BRCA1"). Alias: use \'query\' or \'gene_name\' instead.', 'required': False, 'type': 'string'}, 'query': {'description': 'Gene symbol to search for (e.g., "FLT3", "KRAS", "TP53"). Alias for \'name\'.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChIPAtlas_enrichment_analysis signature={'properties': {'antigen_class': {'description': "Filter by antigen class (e.g., 'TFs and others', 'Histone', 'RNA polymerase')", 'required': False, 'type': 'string'}, 'bed_data': {'description': "**Option 1**: BED format genomic regions (tab-separated: chr, start, end). For finding proteins bound to specific genomic regions. Example: 'chr1\\t1000\\t2000\\nchr2\\t3000\\t4000'.", 'required': False, 'type': 'string'}, 'cell_type_class': {'description': "Filter by cell type class (e.g., 'Blood', 'Liver', 'Brain')", 'required': False, 'type': 'string'}, 'distance': {'default': '5000', 'description': 'Distance from Transcription Start Site (TSS) in base pairs for gene-TF association. Defines promoter region. Default 5000 (±5kb, captures typical promoters). Use 1000-2000 for narrow promoters, 10000+ for enhancer regions.', 'required': False, 'type': 'string'}, 'gene_list': {'description': "**Option 3**: Gene symbols (HGNC for human, MGI for mouse, RGD for rat, FlyBase, WormBase, SGD for yeast). Provide as array or single gene. For finding transcription factors regulating genes. Example: ['TP53', 'MDM2', 'CDKN1A'].", 'items': {'type': 'string'}, 'required': False, 'type': ['array', 'string']}, 'genome': {'default': 'hg38', 'description': 'Genome assembly', 'enum': ['hg38', 'hg19', 'mm10', 'mm9', 'rn6', 'dm6', 'dm3', 'ce11', 'ce10', 'sacCer3'], 'required': False, 'type': 'string'}, 'motif': {'description': "**Option 2**: DNA sequence motif in IUPAC notation. Use: A/T/G/C (bases), W=A|T, S=G|C, M=A|C, K=G|T, R=A|G, Y=C|T, B=C|G|T, D=A|G|T, H=A|C|T, V=A|C|G, N=any. For finding proteins bound to specific DNA sequences. Example: 'CANNTG' (E-box motif).", 'required': False, 'type': 'string'}, 'operation': {'default': 'enrichment_analysis', 'enum': ['enrichment_analysis'], 'required': False, 'type': 'string'}, 'threshold': {'default': '05', 'description': "Peak calling stringency (MACS2 Q-value). Options: '05'=1e-5 (permissive, more peaks, broader features), '10'=1e-10 (moderate, balanced), '20'=1e-20 (strict, high confidence only, narrow peaks). Default '05' suitable for most analyses. Higher values = fewer but more confident peaks.", 'enum': ['05', '10', '20'], 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChIPAtlas_get_peak_data signature={'properties': {'experiment_id': {'description': 'Experiment ID (SRX/ERX/DRX format, required)', 'required': True, 'type': 'string'}, 'format': {'default': 'bigwig', 'description': 'Output format', 'enum': ['bigwig', 'bed', 'bigbed'], 'required': False, 'type': 'string'}, 'genome': {'default': 'hg38', 'description': 'Genome assembly', 'enum': ['hg38', 'hg19', 'mm10', 'mm9', 'rn6', 'dm6', 'dm3', 'ce11', 'ce10', 'sacCer3'], 'required': False, 'type': 'string'}, 'operation': {'default': 'get_peak_data', 'enum': ['get_peak_data'], 'required': False, 'type': 'string'}, 'threshold': {'default': '05', 'description': "Q-value threshold for BED/BigBed peak files. '05'=1e-5 (more peaks), '10'=1e-10 (moderate), '20'=1e-20 (high confidence only). Only applies to BED/BigBed formats. Default '05'.", 'enum': ['05', '10', '20'], 'required': False, 'type': 'string'}}, 'required': ['experiment_id'], 'type': 'object'}
- ENCODE_search_experiments signature={'properties': {'assay_title': {'description': "Assay name filter (e.g., 'TF ChIP-seq', 'Histone ChIP-seq', 'ATAC-seq', 'RNA-seq', 'Hi-C'). Leave empty to search all assays. Use 'TF ChIP-seq' for transcription factor binding experiments.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of results to return (1–100).', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'organism': {'description': "Organism filter — maps to ENCODE's organism scientific name field (e.g., 'Homo sapiens', 'Mus musculus', 'Drosophila melanogaster').", 'required': False, 'type': 'string'}, 'status': {'default': 'released', 'description': "Record status filter. Use 'released' for public data (default), 'archived' for older data.", 'required': False, 'type': 'string'}, 'target': {'description': "Target protein/factor filter (e.g., 'CTCF', 'H3K4me3', 'POLR2A'). Use for TF ChIP-seq experiments.", 'required': False, 'type': 'string'}}, 'type': 'object'}
- ENCODE_get_experiment signature={'properties': {'accession': {'description': "ENCODE experiment accession identifier (format: ENCSR######, e.g., 'ENCSR000AKS', 'ENCSR000CAG'). Find accessions using ENCODE_search_experiments.", 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- MyVariant_get_pathogenicity_scores signature={'properties': {'fields': {'default': 'dbnsfp.revel.score,dbnsfp.cadd.phred,dbnsfp.alphamissense.score,dbnsfp.alphamissense.pred,dbnsfp.sift.score,dbnsfp.sift.pred,dbnsfp.polyphen2_hdiv.score,dbnsfp.polyphen2_hdiv.pred,dbnsfp.metarnn.score,dbnsfp.metarnn.pred,dbnsfp.gerp_rs,dbnsfp.phylop100way_vertebrate.rankscore,dbnsfp.phastcons100way_vertebrate.rankscore,dbnsfp.vest4.score,dbnsfp.mutationtaster.pred,clinvar.rcv.clinical_significance,dbsnp.rsid', 'description': 'Fields to return (pre-configured for pathogenicity scores)', 'required': False, 'type': 'string'}, 'variant_id': {'description': 'Variant ID: rsID (e.g., rs45478192) or HGVS genomic (e.g., chr16:g.23635348A>C). Both formats work.', 'required': True, 'type': 'string'}}, 'required': ['variant_id'], 'type': 'object'}
- CADD_get_variant_score signature={'properties': {'alt': {'description': "Alternate allele (e.g., 'T', 'C')", 'required': True, 'type': 'string'}, 'chrom': {'description': "Chromosome (1-22, X, Y, MT). Can include 'chr' prefix.", 'required': True, 'type': 'string'}, 'include_annotations': {'default': False, 'description': 'Include full annotation details in response', 'required': False, 'type': 'boolean'}, 'pos': {'description': 'Genomic position (1-based)', 'required': True, 'type': 'integer'}, 'ref': {'description': "Reference allele (e.g., 'A', 'G')", 'required': True, 'type': 'string'}, 'version': {'default': 'GRCh38-v1.7', 'description': 'CADD version and genome build', 'enum': ['GRCh38-v1.7', 'GRCh37-v1.7', 'GRCh38-v1.6', 'GRCh37-v1.6'], 'required': False, 'type': 'string'}}, 'required': ['chrom', 'pos', 'ref', 'alt'], 'type': 'object'}
- AlphaMissense_get_variant_score signature={'properties': {'uniprot_id': {'description': "UniProt accession ID (e.g., 'P00533' for EGFR)", 'required': True, 'type': 'string'}, 'variant': {'description': "Variant in protein notation: p.X123Y or X123Y where X is reference amino acid, 123 is position, Y is variant (e.g., 'p.R123H', 'V600E')", 'required': True, 'type': 'string'}}, 'required': ['uniprot_id', 'variant'], 'type': 'object'}
- EVE_get_variant_score signature={'properties': {'alt': {'description': 'Alternate allele', 'required': False, 'type': 'string'}, 'chrom': {'description': 'Chromosome (1-22, X, Y). Use with pos, ref, alt instead of variant.', 'required': False, 'type': 'string'}, 'pos': {'description': 'Genomic position (GRCh38)', 'required': False, 'type': 'integer'}, 'ref': {'description': 'Reference allele', 'required': False, 'type': 'string'}, 'species': {'default': 'human', 'description': 'Species (default: human)', 'required': False, 'type': 'string'}, 'variant': {'description': "Variant in HGVS format (e.g., 'ENST00000269305.4:c.100G>A', 'NM_000546.5:c.215C>G')", 'required': False, 'type': 'string'}}, 'type': 'object'}
- EnsemblVEP_annotate_hgvs signature={'properties': {'hgvs_notation': {'description': "Variant in HGVS notation. Supports protein (p.), coding DNA (c.), and genomic (g.) notation. Examples: 'BRAF:p.Val600Glu', 'ENST00000366667:c.803C>T', 'NC_000007.14:g.140753336A>T'.", 'required': True, 'type': 'string'}, 'species': {'default': 'human', 'description': "Species name. Default: 'human'. Other options: 'mouse', 'rat', 'zebrafish', etc.", 'required': False, 'type': 'string'}}, 'required': ['hgvs_notation'], 'type': 'object'}
- PDBe_get_uniprot_mappings signature={'properties': {'pdb_id': {'description': "PDB identifier (4-character code). Examples: '4hhb' (hemoglobin), '1cbs' (CRABP2), '6lu7' (SARS-CoV-2 main protease).", 'required': True, 'type': 'string'}}, 'required': ['pdb_id'], 'type': 'object'}
- NvidiaNIM_alphafold2 signature={'properties': {'algorithm': {'default': 'mmseqs2', 'description': 'MSA search algorithm. mmseqs2 is faster, jackhmmer is more sensitive', 'enum': ['jackhmmer', 'mmseqs2'], 'required': False, 'type': 'string'}, 'databases': {'default': ['small_bfd'], 'description': 'Sequence databases for MSA search: uniref90, mgnify, small_bfd', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'e_value': {'default': 0.0001, 'description': 'E-value threshold for MSA search', 'required': False, 'type': 'number'}, 'iterations': {'default': 1, 'description': 'Number of search iterations', 'required': False, 'type': 'integer'}, 'relax_prediction': {'default': False, 'description': 'Whether to perform structure relaxation', 'required': False, 'type': 'boolean'}, 'sequence': {'description': 'Amino acid sequence to predict structure for (single letter codes)', 'required': True, 'type': 'string'}, 'skip_template_search': {'default': True, 'description': 'Skip template-based prediction', 'required': False, 'type': 'boolean'}}, 'required': ['sequence'], 'type': 'object'}
- alphafold_get_prediction signature={'properties': {'qualifier': {'description': "UniProt ACCESSION (e.g., 'P69905'). Do NOT use entry names like 'HBA_HUMAN'. Aliases: uniprot_id, uniprot_accession.", 'required': False, 'type': 'string'}, 'sequence_checksum': {'description': 'Optional CRC64 checksum of the UniProt sequence.', 'required': False, 'type': 'string'}, 'uniprot_accession': {'description': "Alias for qualifier: UniProt accession (e.g., 'P69905').", 'required': False, 'type': 'string'}, 'uniprot_id': {'description': "Alias for qualifier: UniProt accession (e.g., 'P69905').", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- InterPro_get_protein_domains signature={'properties': {'protein_id': {'description': 'UniProt protein ID (e.g., P05067, Q9Y6K9)', 'required': True, 'type': 'string'}}, 'required': ['protein_id'], 'type': 'object'}
- UniProt_get_function_by_accession signature={'properties': {'accession': {'description': 'UniProtKB accession, e.g., P05067.', 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- ESM_score_variant_sae_batch signature={'properties': {'model': {'default': 'esmc-6b-2024-12', 'description': 'ESMC base model (must be the 6B model — SAEs are trained against it)', 'enum': ['esmc-6b-2024-12'], 'required': False, 'type': 'string'}, 'sae_model': {'default': 'esmc-6b-2024-12_k64_codebook16384_layer60', 'description': 'SAE codebook identifier', 'required': False, 'type': 'string'}, 'sequence': {'description': 'Reference (wild-type) protein amino acid sequence in single-letter code. Up to ~2700 AA.', 'required': True, 'type': 'string'}, 'top_k_features': {'default': 10, 'description': 'Number of top features to return per variant (top-K lost + top-K gained).', 'required': False, 'type': 'integer'}, 'variants': {'description': 'List of variants to score. Each variant: {position: 1-indexed int, ref_aa: single letter matching sequence[position-1], alt_aa: single letter substitution}.', 'items': {'properties': {'alt_aa': {'description': 'Single-letter substituted amino acid', 'type': 'string'}, 'position': {'description': '1-indexed residue position', 'type': 'integer'}, 'ref_aa': {'description': 'Single-letter wild-type amino acid (must match sequence[position-1])', 'type': 'string'}}, 'required': ['position', 'ref_aa', 'alt_aa'], 'type': 'object'}, 'maxItems': 100, 'required': True, 'type': 'array'}, 'window': {'default': 8, 'description': 'Residue window centered on each variant for activation summation. Default 8 (i.e. positions [pos-8, pos+8]).', 'required': False, 'type': 'integer'}}, 'required': ['sequence', 'variants'], 'type': 'object'}
- ESM_get_region_sae_features signature={'properties': {'end_position': {'description': '1-indexed inclusive end of the region of interest. Must be >= start_position and within sequence length. Region length cap: 500.', 'required': True, 'type': 'integer'}, 'model': {'default': 'esmc-6b-2024-12', 'description': 'ESMC base model', 'enum': ['esmc-6b-2024-12'], 'required': False, 'type': 'string'}, 'sae_model': {'default': 'esmc-6b-2024-12_k64_codebook16384_layer60', 'description': 'SAE codebook identifier', 'required': False, 'type': 'string'}, 'sequence': {'description': 'Protein amino acid sequence in single-letter code. Up to ~2700 AA.', 'required': True, 'type': 'string'}, 'start_position': {'description': '1-indexed inclusive start of the region of interest.', 'required': True, 'type': 'integer'}, 'top_k_features': {'default': 20, 'description': 'Number of top features (by total |activation| over region) to return.', 'required': False, 'type': 'integer'}}, 'required': ['sequence', 'start_position', 'end_position'], 'type': 'object'}
- ESM_describe_sae_feature signature={'properties': {'feature_id': {'description': 'SAE feature index in [0, 16383]. Use the values returned by ESM_get_sae_features.active_features[].feature_id.', 'required': True, 'type': 'integer'}, 'model': {'default': 'esmc-6b-2024-12', 'description': 'ESMC backbone.', 'enum': ['esmc-6b-2024-12'], 'required': False, 'type': 'string'}, 'n_proteins': {'default': 10, 'description': 'Number of panel proteins to run SAE on. Default 10 (the full curated panel). Lower for cheaper exploration at the cost of confidence.', 'required': False, 'type': 'integer'}, 'sae_model': {'default': 'esmc-6b-2024-12_k64_codebook16384_layer60', 'description': 'SAE checkpoint to label. Cache is keyed on this — different SAEs produce different labels for the same id.', 'required': False, 'type': 'string'}, 'top_residues_per_protein': {'default': 3, 'description': 'For each protein, take the top-K residues where the target feature activates most strongly, then check their UniProt annotations. Default 3.', 'required': False, 'type': 'integer'}, 'use_cache': {'default': True, 'description': 'If true (default) and a cached label exists at ~/.cache/tooluniverse/sae_labels/.../feature_{id}.json, return it instead of rerunning the panel. Set false to force a recompute.', 'required': False, 'type': 'boolean'}}, 'required': ['feature_id'], 'type': 'object'}
- GTEx_get_median_gene_expression signature={'properties': {'dataset_id': {'default': 'gtex_v8', 'description': 'GTEx dataset version (default: gtex_v8; v10 returns empty for most endpoints)', 'enum': ['gtex_v8', 'gtex_v10', 'gtex_snrnaseq_pilot'], 'required': False, 'type': 'string'}, 'gencode_id': {'description': "Gene identifier(s): gene symbol (e.g. 'TP53'), unversioned Ensembl ID (e.g. 'ENSG00000141510'), or versioned GENCODE ID (e.g. 'ENSG00000141510.18'). Auto-resolved to versioned GENCODE ID. Can be single string or array.", 'items': {'type': 'string'}, 'required': False, 'type': ['string', 'array']}, 'gene_symbol': {'description': 'Gene symbol alias for gencode_id (e.g., "TP53", "COL5A1")', 'required': False, 'type': 'string'}, 'items_per_page': {'default': 250, 'description': 'Results per page', 'maximum': 100000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'description': 'Operation type', 'enum': ['get_median_gene_expression'], 'required': False, 'type': 'string'}, 'page': {'default': 0, 'description': 'Page number for pagination (0-based)', 'minimum': 0, 'required': False, 'type': 'integer'}, 'tissue_site_detail_id': {'description': "Optional: Tissue IDs to filter (e.g. ['Liver', 'Brain_Cortex']). Omit for all tissues. See GTEx_get_tissue_sites for valid IDs", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- EuropePMC_search_articles signature={'properties': {'enrich_missing_abstract': {'default': False, 'description': 'If true, best-effort fills missing abstracts by fetching Europe PMC fullTextXML (bounded to a few results).', 'required': False, 'type': 'boolean'}, 'extract_terms_from_fulltext': {'description': "Optional list of terms to extract from full text (open access only). When provided, automatically fetches fullTextXML for open-access articles and returns snippets around these terms. Terms are processed in batches of 5 internally, so any number of terms is accepted. Bounded to first 3 OA articles to avoid latency. Returns snippets in a 'fulltext_snippets' field for each article.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'fulltext_terms': {'description': 'Optional list of terms that must occur in the indexed full text (Europe PMC BODY field). When provided, the tool adds a BODY:"..." clause and automatically enables `require_has_ft`.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'default': 5, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from Europe PMC.', 'required': False, 'type': 'integer'}, 'page_size': {'description': 'Alias for limit â\x80\x94 number of results to return', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Europe PMC. Supports Lucene-like fielded syntax (e.g., BODY:"term", INTRO:"term", METHODS:"term").', 'required': True, 'type': 'string'}, 'require_has_ft': {'default': False, 'description': 'If true, appends `HAS_FT:Y` to the query to restrict results to records where Europe PMC has full text indexed. This is NOT the same as having a link to free full text elsewhere (e.g., PMC) and is often the key reason body-only keywords cannot be found via Europe PMC search.', 'required': False, 'type': 'boolean'}}, 'required': ['query'], 'type': 'object'}
- BioRxiv_list_recent_preprints signature={'properties': {'cursor': {'default': 0, 'description': 'Pagination cursor (0 for first 100 results, 100 for next 100, etc.)', 'required': False, 'type': 'integer'}, 'end_date': {'description': "End date in YYYY-MM-DD format (e.g., '2024-01-03'). Date range must not exceed 60 days.", 'required': True, 'type': 'string'}, 'server': {'default': 'biorxiv', 'description': "Server: 'biorxiv' for biology preprints, 'medrxiv' for health sciences preprints", 'enum': ['biorxiv', 'medrxiv'], 'required': False, 'type': 'string'}, 'start_date': {'description': "Start date in YYYY-MM-DD format (e.g., '2024-01-01'). Date range must not exceed 60 days.", 'required': True, 'type': 'string'}}, 'required': ['start_date', 'end_date'], 'type': 'object'}
- MedRxiv_get_preprint signature={'properties': {'doi': {'description': "medRxiv DOI. Can be full DOI (e.g., '10.1101/2021.04.29.21256344') or just the numeric part after '10.1101/' (e.g., '2021.04.29.21256344'). Find DOIs using EuropePMC_search_articles, web_search, or from paper citations.", 'required': True, 'type': 'string'}, 'server': {'default': 'medrxiv', 'description': "Server to query - always 'medrxiv' for this tool.", 'enum': ['medrxiv'], 'required': False, 'type': 'string'}}, 'required': ['doi'], 'type': 'object'}
- openalex_search_works signature={'anyOf': [{'required': ['search']}, {'required': ['query']}], 'properties': {'filter': {'description': 'OpenAlex filter string (comma-separated). Example: "from_publication_date:2020-01-01,is_oa:true".', 'required': False, 'type': 'string'}, 'fulltext_terms': {'description': 'Optional list of terms to match in OpenAlex full-text index. Adds one or more fulltext.search:<term> filters and implicitly enables require_has_fulltext.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'description': 'Alias for `per_page` (OpenAlex max 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'mailto': {'description': 'Optional contact email for OpenAlex polite pool. If omitted, ToolUniverse uses a default.', 'required': False, 'type': 'string'}, 'page': {'default': 1, 'description': 'Page number (1-indexed).', 'minimum': 1, 'required': False, 'type': 'integer'}, 'per_page': {'default': 10, 'description': 'Results per page (OpenAlex max 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'query': {'description': 'Alias for `search` (recommended when you standardize on `query` across multiple paper-search tools).', 'required': False, 'type': 'string'}, 'require_has_fulltext': {'default': False, 'description': 'If true, appends OpenAlex filter has_fulltext:true (keeps only works with full-text index available).', 'required': False, 'type': 'boolean'}, 'search': {'description': 'Search query for works. Use filter + fulltext_terms/require_has_fulltext when you need full-text-index-only matching.', 'required': False, 'type': 'string'}, 'sort': {'description': 'Sort order string, e.g. "cited_by_count:desc".', 'required': False, 'type': 'string'}}, 'type': 'object'}
- SemanticScholar_search_papers signature={'properties': {'include_abstract': {'default': False, 'description': 'If true, best-effort fetches missing abstracts via the paper detail endpoint (only when abstract is missing in search results).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 5, 'description': 'Maximum number of papers to return from Semantic Scholar.', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Semantic Scholar. Use keywords separated by spaces to refine the search.', 'required': True, 'type': 'string'}, 'sort': {'description': "Sort results. Options: 'citationCount:desc', 'citationCount:asc', 'publicationDate:desc', 'publicationDate:asc'.", 'required': False, 'type': 'string'}, 'year': {'description': "Filter results by publication year. Use a single year (e.g., '2024') or a range (e.g., '2020-2024').", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}

## UNAVAILABLE → SUBSTITUTE
- OMIM_search: SUBSTITUTE with ClinVar_search_variants, gnomad_get_gene_constraints. OMIM key-gated; gene→disease via ClinVar pathogenic variants + gnomAD constraint.
- OMIM_get_entry: SUBSTITUTE with ClinVar_search_variants, gnomad_get_gene_constraints. OMIM key-gated; gene→disease via ClinVar pathogenic variants + gnomAD constraint.
- DisGeNET_search_gene: SUBSTITUTE with ClinVar_search_variants. DisGeNET key-gated; gene→disease via ClinVar (curated associations unavailable).
- DisGeNET_get_vda: SUBSTITUTE with ClinVar_search_variants. DisGeNET key-gated; gene→disease via ClinVar (curated associations unavailable).

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- gene_symbol
- transcript_set
- genome_build
- gene_name
- variant_description
- select_transcripts
- variant_id
- ONCOKB_API_TOKEN
- mechanism_summary
- ESM_API_KEY
- CELLxGENE_get_expression_data
- CELLxGENE_get_cell_metadata

# TARGET SKILL TO CONVERT
---
name: tooluniverse-variant-interpretation
description: Clinical variant interpretation from raw variant calls to ACMG-classified recommendations with structural impact analysis. Use for VUS classification, pathogenicity assessment with cited criteria, structure-based variant impact (AlphaFold/PDB), and producing clinical-grade variant reports for return of results or molecular tumor boards.
disable-model-invocation: true
---

# Clinical Variant Interpreter

Systematic variant interpretation using ToolUniverse - from raw variant calls to ACMG-classified clinical recommendations with structural impact analysis.

## Triggers

Use this skill when users:
- Ask about variant interpretation, classification, or pathogenicity
- Have VCF data needing clinical annotation
- Need ACMG classification for variants
- Want structural impact analysis for missense variants

## Key Principles

1. **ACMG-Guided** - Follow ACMG/AMP 2015 guidelines with explicit evidence codes
2. **Structural Evidence** - Use AlphaFold2 for novel structural impact analysis
3. **Population Context** - gnomAD frequencies with ancestry-specific data
4. **Actionable Output** - Clear recommendations, not just classifications
5. **English-first queries** - Always use English terms in tool calls; respond in user's language

---

## LOOK UP, DON'T GUESS

When asked about a variant's significance, query ClinVar/gnomAD/CIViC FIRST. Never classify a variant without checking databases. When you're not sure about a fact, your first instinct should be to SEARCH for it using tools, not to reason harder from memory.

---

## Workflow Overview

```
Phase 1: VARIANT IDENTITY        → Normalize HGVS, map gene/transcript/consequence
Phase 2: CLINICAL DATABASES       → ClinVar, gnomAD, OMIM, ClinGen, COSMIC, SpliceAI
Phase 2.5: REGULATORY CONTEXT     → ChIPAtlas, ENCODE (non-coding variants only)
Phase 3: COMPUTATIONAL PREDICTIONS → CADD, AlphaMissense, EVE, SIFT/PolyPhen
Phase 4: STRUCTURAL ANALYSIS      → PDB/AlphaFold2, domains, functional sites (VUS/novel)
Phase 4.5: EXPRESSION CONTEXT     → CELLxGENE, GTEx tissue expression
Phase 5: LITERATURE EVIDENCE      → PubMed, EuropePMC, BioRxiv, MedRxiv
Phase 6: ACMG CLASSIFICATION      → Evidence codes, classification, recommendations
```

---

## Phase 1: Variant Identity

Tools: `MyVariant_query_variants`, `EnsemblVar_get_variant_consequences`, `NCBIGene_search`, `VariantValidator_gene2transcripts`, `VariantValidator_validate_variant`

**VariantValidator_gene2transcripts**: Look up MANE Select and MANE Plus Clinical transcripts for a gene. Use this to identify the correct canonical transcript before variant annotation.
- Parameters: `gene_symbol` (e.g. "TP53"), `transcript_set` ("mane" | "refseq" | "ensembl" | "all"), `genome_build` ("GRCh38" default)
- Returns: Array of `{current_symbol, transcripts: [{reference, annotations: {mane_select, mane_plus_clinical}}]}`
- Aliases: `gene` and `gene_name` also accepted for `gene_symbol`

**VariantValidator_validate_variant**: Validate HGVS variant descriptions and get normalized notation with genomic/transcript/protein consequences.
- Parameters: `genome_build` ("GRCh37" | "GRCh38"), `variant_description` (HGVS, e.g. "NM_007294.4:c.5266dup"), `select_transcripts` (transcript or "all")
- Returns: Validated HGVS, protein consequence, genomic coordinates, gene IDs

Capture: HGVS notation (c. and p.), gene symbol, canonical transcript (MANE Select via VariantValidator), consequence type, amino acid change, exon/intron location.

## Phase 2: Clinical Databases

Tools: `ClinVar_search_variants`, `gnomad_search_variants`, `gnomad_get_variant`, `OMIM_search`, `OMIM_get_entry`, `ClinGen_search_gene_validity`, `ClinGen_search_dosage_sensitivity`, `ClinGen_search_actionability`, `COSMIC_search_mutations`, `COSMIC_get_mutations_by_gene`, `DisGeNET_search_gene`, `DisGeNET_get_vda`, `SpliceAI_predict_splice`, `SpliceAI_get_max_delta`, `civic_get_variants_by_gene`, `civic_search_evidence_items`, `civic_search_assertions`

> **gnomAD two-step workflow**: `gnomad_search_variants` only accepts rsIDs or variant IDs (not gene names). Search by rsID first, then use the returned `variant_id` with `gnomad_get_variant` to get population allele frequencies.
>
> **CIViC**: Use `civic_search_genes(query="<gene_symbol>")` to find the CIViC gene ID dynamically (do NOT rely on a hardcoded lookup table). Then use `civic_get_variants_by_gene(gene_id=<id>)` and `civic_search_evidence_items` for actionability details. If `civic_search_genes` returns no results, the gene may not be curated in CIViC — note this gap.
>
> **OncoKB note**: Demo mode only supports BRAF, TP53, ROS1. For other genes, set `ONCOKB_API_TOKEN` environment variable.

Use SpliceAI for: intronic variants near splice sites, synonymous variants, exonic variants near splice junctions.

See `CODE_PATTERNS.md` for implementation details.

## Phase 2.5: Regulatory Context (Non-Coding Only)

Apply for intronic (non-splice), promoter, UTR, or intergenic variants near disease genes.

Tools: `ChIPAtlas_enrichment_analysis`, `ChIPAtlas_get_peak_data`, `ENCODE_search_experiments`, `ENCODE_get_experiment`

## Phase 2.9: Short-Circuit Check

Before full ACMG classification, check if the variant already has an expert panel classification in ClinVar. Use `MyVariant_query_variants` with the rsID or HGVS notation — the `clinvar` field in the response includes clinical significance, review status, and RCV records. If an expert panel has already classified the variant as Pathogenic or Benign, note this prominently and focus on confirming/contextualizing rather than de novo classification.

## Phase 3: Computational Predictions

**Primary approach:** `MyVariant_query_variants` with `fields=dbnsfp,clinvar,cadd,gnomad_genome` retrieves 15+ predictor scores (SIFT, PolyPhen, CADD, REVEL, AlphaMissense, MetaRNN, FATHMM, GERP, PhyloP, etc.) in a single call. This is usually sufficient.

**REVEL/AlphaMissense fallback**: If `MyVariant_query_variants` returns no `dbnsfp` block, use the dedicated tool:
1. **`MyVariant_get_pathogenicity_scores`** (PREFERRED FALLBACK) — returns REVEL, AlphaMissense, SIFT, PolyPhen2, MetaRNN, GERP, PhyloP, and more in a single call with pre-configured dbnsfp fields. Input: `variant_id` (rsID or HGVS genomic).
2. `CADD_get_variant_score` (PHRED 0-99) — works for most variants
3. `AlphaMissense_get_variant_score` (0-1, needs UniProt ID) — missense only
4. `EVE_get_variant_score` (0-1) — missense only
5. `EnsemblVEP_annotate_hgvs` (VEP with colocated variants) — includes SIFT/PolyPhen
6. If REVEL is still unavailable, note this as a limitation and rely on CADD + SIFT + PolyPhen consensus. REVEL absence does not prevent classification.

Consensus: Run CADD (all variants) + AlphaMissense + EVE (missense). 2+ concordant damaging = strong PP3; 2+ concordant benign = strong BP4.

See `ACMG_CLASSIFICATION.md` for thresholds.

## Phase 4: Structural Analysis (VUS/Novel Missense)

Tools: `PDBe_get_uniprot_mappings`, `NvidiaNIM_alphafold2` *(requires NVIDIA_API_KEY env var; free key at build.nvidia.com)*, `alphafold_get_prediction` (param: `qualifier`, e.g., UniProt accession), `InterPro_get_protein_domains`, `UniProt_get_function_by_accession`

Workflow: Get structure -> map residue -> assess domain/functional site -> predict destabilization.

> **AlphaFold size limitation**: Very large proteins (>2,700 aa, e.g., BRCA2 at 3,418 aa) may not have AlphaFold predictions via the standard API. Fall back to published structural studies or `PDBe_get_uniprot_mappings` for experimental structures.

## Phase 4.2: Mechanism of Effect (VUS missense, ESMC-6B SAE)

AlphaMissense / REVEL / CADD give a pathogenicity score but no mechanism. When you need to answer "**how** does this variant disrupt protein function" — e.g. for VUS write-ups, clinical reports, or to triangulate a discordant predictor consensus — use the ESMC-6B Sparse Autoencoder to identify which interpretable protein-language-model features the mutation disrupts.

**One-call mechanism summary** (recommended starting point):
```python
mech = tu.tools.ESM_explain_variant_mechanism(
    sequence=wt_aa_sequence,   # full reference protein sequence
    position=600,              # 1-indexed
    ref_aa="V",
    alt_aa="E",
    top_k_features=5,          # describe top 5 lost + top 5 gained
)
# mech["data"]["mechanism_summary"] e.g.:
#   "Disrupted feature categories (lost): catalytic=2, ligand-binding=1;
#    Induced feature categories (gained): structural-stability=1"
```

Returns `mechanism_summary`, per-feature lost/gained tables, and category aggregates. Use the category aggregate to support or qualify the pathogenicity verdict in the report:
- `catalytic` / `ligand-binding` / `ptm` lost → mechanistic support for PP3
- `secondary-structure` / `structural-stability` gained on a stable WT region → mechanistic basis for "destabilizing" claim
- No interpretable change at top-K → does not weaken AlphaMissense alone, but flag for caution

**When you have a saturation question** (e.g. "score all 19 substitutions at residue 600 to find the most disruptive"): use `ESM_score_variant_sae_batch` — 1 Forge call for the reference + 1 per variant, instead of 2 per variant.

**When the region is what matters** (e.g. "what's the SAE signature of the kinase activation loop, residues 754-771"): use `ESM_get_region_sae_features` then `ESM_describe_sae_feature` on the top hits.

**Requires**: `ESM_API_KEY` env var (free non-commercial token at https://forge.evolutionaryscale.ai) and `pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'` (SAE support is on an unmerged feature branch — PyPI esm 3.2.x does NOT include SAEConfig). License: EvolutionaryScale Cambrian Inference License — non-commercial use only.

## Phase 4.5: Expression Context

Tools: `CELLxGENE_get_expression_data`, `CELLxGENE_get_cell_metadata`, `GTEx_get_median_gene_expression`

Confirms gene expression in disease-relevant tissues. Supports PP4 if highly restricted; challenges classification if not expressed in affected tissue.

## Phase 5: Literature Evidence

Tools: `PubMed_search_articles`, `EuropePMC_search_articles`, `BioRxiv_list_recent_preprints`, `MedRxiv_get_preprint`, `openalex_search_works`, `SemanticScholar_search_papers`

Always flag preprints as NOT peer-reviewed.

## Phase 6: ACMG Classification

Apply all relevant evidence codes (PVS1, PS1, PS3, PM1, PM2, PM5, PP3, PP5 for pathogenic; BA1, BS1, BS3, BP4, BP7 for benign). See `ACMG_CLASSIFICATION.md` for the complete algorithm.

### Gene-Specific Population Frequency Thresholds

BS1 (allele frequency too high for disorder) requires gene-specific calibration, not a universal cutoff:
- **High-penetrance genes** (BRCA1, TP53): BS1 threshold ~0.0001
- **Moderate-penetrance genes** (PALB2, ATM, CHEK2): BS1 threshold ~0.001
- **Low-penetrance/common disease genes**: BS1 threshold higher, depends on disease prevalence
- **Formula**: BS1 threshold = (disease prevalence × max allelic contribution × max genetic contribution) / penetrance
- When in doubt, compare the variant's AF to the highest AF of any known pathogenic variant in the same gene — if it exceeds that, BS1 is likely applicable.

### Handling Conflicting Evidence: Functional vs Epidemiological

This is one of the most challenging scenarios in variant interpretation. When a biochemical assay shows damage but population/epidemiological data shows no disease association:

1. **Epidemiological data generally trumps in-vitro assays** for clinical classification. A variant found at ~0.1% frequency with no disease association in 40K+ cases is unlikely to be clinically significant, even if it reduces protein function in a tube.
2. **Apply PS3/BS3 carefully**: ClinGen's SVI recommends that PS3 (functional evidence for pathogenicity) requires the assay to be validated against known pathogenic AND known benign controls. A single biochemical study without such validation is PS3_Supporting at best.
3. **Hypomorphic variants**: Some variants genuinely reduce protein function (detectable in sensitive assays) but not enough to cause disease. This is biologically real and does not make them pathogenic.
4. **Document the conflict explicitly** in the report. State: "Biochemical assay X shows [result], but case-control study Y with N cases found no significant disease association. Per ACMG guidelines, the epidemiological evidence is weighted more heavily for clinical classification."

### Bayesian ACMG Point System (Tavtigian et al. 2018)

Modern clinical labs use a point-based system instead of the original rule-counting approach:

| Evidence Level | Pathogenic Points | Benign Points |
|---|---|---|
| Very Strong (PVS1) | +8 | -- |
| Strong (PS1-PS4) | +4 each | -4 each (BS1-BS4) |
| Moderate (PM1-PM6) | +2 each | -- |
| Supporting (PP1-PP5) | +1 each | -1 each (BP1-BP7) |
| Stand-alone (BA1) | -- | -8 |

**Classification by total points**:
- Pathogenic: >= 10 points
- Likely Pathogenic: 6-9 points
- VUS: -5 to 5 points
- Likely Benign: -6 to -9 points
- Benign: <= -10 points

This system handles conflicting evidence naturally — a variant with PS3 (+4) and BS1 (-4) and BP4 (-1) nets -1, which is VUS. The original rule-based approach struggles with this scenario.

**Computational procedure: ACMG Bayesian classification**

```python
# Automated ACMG point calculation
# Input: dict of evidence codes with their applied strength

def classify_acmg(evidence: dict) -> dict:
    """
    Classify a variant using the Bayesian ACMG point system.

    Args:
        evidence: dict mapping ACMG codes to strength levels.
            Pathogenic codes: 'very_strong', 'strong', 'moderate', 'supporting'
            Benign codes: 'stand_alone', 'strong', 'supporting'

    Example:
        evidence = {
            'BS1': 'strong',       # AF too high
            'BS3': 'supporting',   # Epidemiological evidence against pathogenicity
            'BP6': 'supporting',   # ClinVar benign consensus
            'PP3': 'supporting',   # Computational predictors say damaging
        }
    """
    pathogenic_points = {
        'very_strong': 8, 'strong': 4, 'moderate': 2, 'supporting': 1
    }
    benign_points = {
        'stand_alone': -8, 'strong': -4, 'supporting': -1
    }

    total = 0
    details = []
    for code, strength in evidence.items():
        if code.startswith(('PVS', 'PS', 'PM', 'PP')):
            pts = pathogenic_points.get(strength, 0)
        elif code.startswith(('BA', 'BS', 'BP')):
            pts = benign_points.get(strength, 0)
        else:
            pts = 0
        total += pts
        details.append(f"{code} ({strength}): {pts:+d}")

    if total >= 10:
        classification = "Pathogenic"
    elif 6 <= total <= 9:
        classification = "Likely Pathogenic"
    elif -5 <= total <= 5:
        classification = "VUS"
    elif -9 <= total <= -6:
        classification = "Likely Benign"
    else:
        classification = "Benign"

    return {
        'classification': classification,
        'total_points': total,
        'evidence_breakdown': details
    }

# Example: PALB2 c.2816T>G (from test case)
result = classify_acmg({
    'BS1': 'strong',       # gnomAD AF 0.00105 exceeds threshold
    'BS3': 'supporting',   # Case-control study shows no association
    'BP6': 'supporting',   # ClinVar 13 submitters say benign/likely benign
})
# Output: Likely Benign, total_points=-6, evidence: BS1(strong):-4, BS3(supporting):-1, BP6(supporting):-1
```

Use this procedure after collecting all evidence from Phases 1-5 to compute the final classification.

### Gene-Specific VCEP Criteria

ClinGen Variant Curation Expert Panels (VCEPs) publish gene-specific ACMG modifications. Before classifying, check if a VCEP exists:
- `ClinGen_search_gene_validity(gene="<gene_symbol>")` — if validity is "Definitive" or "Strong", a VCEP likely exists
- Common VCEPs: BRCA1/2 (Enigma), TP53, PTEN, CDH1, PALB2, RASopathies, Lynch syndrome genes
- VCEP criteria override generic ACMG criteria (e.g., PALB2 VCEP has specific PM1 hotspot regions)

### Predictor Weighting

Not all computational predictors are equal. For missense variants:
- **REVEL** (AUC ~0.95) — best single meta-predictor; weight highest
- **AlphaMissense** (AUC ~0.94) — strong, structure-aware
- **CADD** (AUC ~0.85) — good for all variant types, but less specific for missense
- **SIFT/PolyPhen** (AUC ~0.80) — legacy tools; useful for consensus but not individually decisive

When predictors disagree: if REVEL says tolerated but SIFT/PolyPhen say damaging, lean toward REVEL. If REVEL is unavailable, require 3+ concordant predictions for PP3/BP4.

### Tool Failure Fallbacks

If a primary tool fails, use these alternatives:
- **ClinVar_search_variants returns 0 results**: Use `MyVariant_query_variants` with rsID or HGVS — the `clinvar` field in MyVariant is more reliable for variant lookup than NCBI Entrez search
- **gnomAD_search_variants fails**: Use `EnsemblVEP_annotate_hgvs` which includes gnomAD frequency via colocated variants
- **CADD_get_variant_score fails**: CADD PHRED is also available in the `dbnsfp` block from MyVariant
- **AlphaFold prediction unavailable** (large proteins >2700aa): Use `PDBe_get_uniprot_mappings` for experimental structures

---

## Special Scenarios

**Novel Missense VUS**: Check PM5 (other pathogenic at same residue), get AlphaFold2 structure, apply PM1/PP3 as appropriate.

**Truncating Variant**: Check LOF mechanism, NMD escape, alternative isoforms, ClinGen LOF curation. Apply PVS1 at appropriate strength.

**Splice Variant**: Run SpliceAI, assess canonical splice distance, in-frame skipping potential. Apply PP3/BP7 based on scores.

---

## Output Structure

```markdown
# Variant Interpretation Report: {GENE} {VARIANT}
## Executive Summary
## 1. Variant Identity
## 2. Population Data
## 3. Clinical Database Evidence
## 4. Computational Predictions
## 5. Structural Analysis
## 6. Literature Evidence
## 7. ACMG Classification
## 8. Clinical Recommendations
## 9. Limitations & Uncertainties
## Data Sources
```

File naming: `{GENE}_{VARIANT}_interpretation_report.md`

---

## Clinical Recommendations

**Pathogenic/Likely Pathogenic**: Enhanced screening, risk-reducing options, drug dosing adjustment, reproductive counseling, family cascade screening.

**VUS**: Do not use for medical decisions. Reinterpret in 1-2 years. Pursue functional studies and segregation data.

**Benign/Likely Benign**: Not expected to cause disease. No cascade testing needed.

---

## Quantified Minimums

| Section | Requirement |
|---------|-------------|
| Population frequency | gnomAD overall + at least 3 ancestry groups |
| Predictions | At least 3 computational predictors |
| Literature search | At least 2 search strategies |
| ACMG codes | All applicable codes listed |

---

## Cross-Skill References

For amino acid properties at variant position, run: `python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type amino_acid --code X`

---

## References

- `ACMG_CLASSIFICATION.md` - Evidence codes, classification algorithm, prediction thresholds, structural/regulatory impact tables
- `CODE_PATTERNS.md` - Reusable code patterns for each workflow phase
- `CHECKLIST.md` - Pre-delivery verification
- `EXAMPLES.md` - Sample interpretations
- `TOOLS_REFERENCE.md` - Tool parameters and fallbacks


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
