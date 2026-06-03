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
- CPIC_get_recommendations signature={'properties': {'drug': {'description': "Drug name to auto-resolve guideline_id (e.g., 'codeine', 'abacavir', 'tamoxifen').", 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Alias for drug.', 'required': False, 'type': 'string'}, 'guideline_id': {'description': 'CPIC guideline numeric ID. Alternative to drug/drug_name. Use CPIC_list_guidelines to browse IDs.', 'required': False, 'type': 'integer'}, 'limit': {'description': 'Maximum number of recommendations to return (default 50)', 'required': False, 'type': ['integer', 'null']}, 'offset': {'description': 'Number of recommendations to skip for pagination (default 0)', 'required': False, 'type': ['integer', 'null']}}, 'required': [], 'type': 'object'}
- PharmGKB_get_dosing_guidelines signature={'properties': {'gene': {'description': "Gene symbol (e.g., 'CYP2D6'). NOTE: Filtering by gene symbol is unreliable and may return a generic prompt instead of actual guidelines. Use guideline_id instead.", 'required': False, 'type': 'string'}, 'guideline_id': {'description': "PharmGKB ClinPGx guideline ID from CPIC_list_guidelines 'clinpgxid' field (e.g., 'PA166251465' for warfarin, 'PA166251454' for opioids/codeine, 'PA166251458' for tamoxifen). Use clinpgxid, NOT pharmgkbid.", 'required': True, 'type': 'string'}}, 'required': ['guideline_id'], 'type': 'object'}
- PharmGKB_get_clinical_annotations signature={'properties': {'annotation_id': {'description': "PharmGKB clinical annotation ID (e.g., '1447954390'). Required for reliable results.", 'required': False, 'type': 'string'}, 'gene': {'description': 'NOT SUPPORTED: PharmGKB API requires a specific annotation_id (e.g. "1447954390"), not a gene symbol. Browse https://www.pharmgkb.org/clinicalAnnotation to find annotation IDs. For gene-drug dosing use CPIC_list_guidelines instead.', 'required': False, 'type': 'string'}, 'gene_id': {'description': 'PharmGKB Gene Accession ID (e.g., "PA128"). NOTE: Gene-based lookup is not supported — will return an error with instructions to use annotation_id instead.', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': 'Alias for gene — NOT SUPPORTED. See gene parameter.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- CPIC_get_drug_info signature={'properties': {'name': {'description': "Drug name in lowercase (e.g., 'warfarin', 'codeine', 'clopidogrel', 'simvastatin')", 'required': True, 'type': 'string'}}, 'required': ['name'], 'type': 'object'}
- FDA_get_pharmacogenomics_info_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- CPIC_list_guidelines signature={'properties': {'drug': {'description': "Filter by drug name (e.g., 'codeine', 'warfarin', 'clopidogrel'). Case-insensitive substring match against drug names in the guideline.", 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Alias for drug.', 'required': False, 'type': 'string'}, 'gene': {'description': 'Filter by gene symbol (e.g., CYP2D6, TPMT). Returns only guidelines involving this gene.', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': 'Alias for gene. Filter by gene symbol (e.g., CYP2D6, TPMT).', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- fda_pharmacogenomic_biomarkers signature={'properties': {'biomarker': {'description': "Filter by the specific biomarker (e.g., 'CYP2D6', 'HLA-B*5701'). Case-insensitive partial match.", 'required': False, 'type': 'string'}, 'drug_name': {'description': "Filter by the name of the drug (e.g., 'Sivextro', 'Abacavir'). Case-insensitive partial match.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of results to return.', 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- DGIdb_get_drug_gene_interactions signature={'properties': {'gene': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'genes': {'description': "List of gene symbols (e.g., ['EGFR', 'BRAF']). Also accepts a single gene as string. Aliases: gene_name, gene.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_sources': {'description': "Optional filter by data sources (e.g., ['DrugBank', 'ChEMBL']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_types': {'description': "Optional filter by interaction types (e.g., ['inhibitor', 'antagonist']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- DGIdb_get_gene_druggability signature={'properties': {'gene': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'genes': {'description': 'List of gene symbols to check druggability. Aliases: gene_name, gene.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- CPIC_search_gene_drug_pairs signature={'additionalProperties': False, 'properties': {'cpiclevel': {'description': "CPIC evidence level to filter by (e.g., 'A', 'B', 'B/C', 'C', 'D'). Omit to include all levels.", 'required': False, 'type': ['string', 'null']}, 'gene': {'description': "Gene symbol alias (e.g., 'CYP2D6') — alternative to genesymbol", 'required': False, 'type': ['string', 'null']}, 'gene_symbol': {'description': "Gene symbol alias (e.g., 'CYP2D6', 'VKORC1') — alternative to genesymbol", 'required': False, 'type': ['string', 'null']}, 'genesymbol': {'description': "Gene symbol to filter by (e.g., 'CYP2D6', 'DPYD', 'TPMT'). Omit to search all genes.", 'required': False, 'type': ['string', 'null']}, 'limit': {'description': 'Maximum number of results to return (default 50)', 'required': False, 'type': ['integer', 'null']}}, 'required': [], 'type': 'object'}
- CPIC_get_gene_drug_pairs signature={'properties': {'gene': {'description': "Alias for genesymbol (e.g., 'CYP2D6')", 'required': False, 'type': ['string', 'null']}, 'gene_symbol': {'description': "Alias for genesymbol (e.g., 'CYP2D6')", 'required': False, 'type': ['string', 'null']}, 'genesymbol': {'description': "Gene symbol (e.g., 'CYP2D6', 'CYP2C19', 'SLCO1B1', 'TPMT', 'DPYD', 'VKORC1')", 'required': False, 'type': ['string', 'null']}}, 'required': [], 'type': 'object'}

## UNAVAILABLE → SUBSTITUTE
- DisGeNET_get_vda: NO grounded alternative — ESCALATE TO HUMAN. DisGeNET (gene-disease) has no drug-centric substitute; omit.

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- gene_symbol
- gene_name
- guideline_id
- drug_name
- annotation_id
- gene_id
- drug_id
- interaction_types
- interaction_sources
- seriousness_type
- adverse_event
- pgx_on_fda_label

# TARGET SKILL TO CONVERT
---
name: tooluniverse-pharmacogenomics
description: Pharmacogenomics (PGx) research — drug-gene interactions (CPIC, PharmGKB), CPIC dosing guidelines, variant-drug-response associations, ethnic-allele-frequency considerations, and metabolizer-status scoring. Use for PGx-informed dosing recommendations, CYP/HLA pharmacogenomic allele interpretation, and clinically-actionable PGx report generation.
disable-model-invocation: true
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Pharmacogenomics (PGx) Research Skill

Systematic PGx analysis: resolve gene-drug pairs, retrieve CPIC dosing guidelines, annotate alleles and variants with PharmGKB, check FDA PGx biomarker labeling, and generate evidence-graded clinical recommendations.

## When to Use

- "What CPIC guidelines exist for CYP2D6?"
- "Get dosing recommendations for codeine based on CYP2D6 poor metabolizer status"
- "Which drugs have FDA pharmacogenomic biomarkers for CYP2C19?"
- "Find PharmGKB clinical annotations for rs1799853"
- "Is this patient's CYP2D6 genotype relevant to tamoxifen dosing?"
- "What is the functional status of CYP2D6*4?"
- "List all CPIC level A gene-drug pairs for CYP2D6"

## Workflow Overview

```
Input (gene/drug/variant/phenotype)
  |
  v
Phase 0: Disambiguation (resolve gene symbols, drug names, rsIDs)
  |
  v
Phase 1: Gene-Drug Pair Identification (CPIC pairs + evidence levels)
  |
  v
Phase 2: Guideline & Dosing Retrieval (CPIC recommendations + PharmGKB)
  |
  v
Phase 3: Allele & Variant Annotation (star alleles, function, activity scores)
  |
  v
Phase 4: FDA Biomarker Labeling (regulatory PGx status)
  |
  v
Phase 5: Cross-Database Enrichment (EpiGraphDB, DGIdb, OpenTargets PGx)
  |
  v
Phase 6: Report (evidence-graded clinical summary)
```

---

## Phase 0: Disambiguation

Resolve user input to canonical identifiers before querying PGx databases.

**PharmGKB_search_genes**: `query` (string REQUIRED, e.g., "CYP2D6"). Returns `{status, data: [{id, symbol, name}]}`.
- Use to get PharmGKB gene accession ID (e.g., "PA128" for CYP2D6).

**PharmGKB_search_drugs**: `query` (string REQUIRED, e.g., "codeine"). Returns `{status, data: [{id, name, types}]}`.
- Use to get PharmGKB chemical ID (e.g., "PA449088" for codeine).

**PharmGKB_search_variants**: `query` (string REQUIRED, rsID e.g., "rs1799853"). Returns `{status, data: [{id, symbol, changeClassification, clinicalSignificance}]}`.
- Use to resolve rsIDs and find PharmGKB annotation IDs.

**CPIC_get_drug_info**: `name` (string REQUIRED, lowercase, e.g., "codeine"). Returns drug identifiers including `drugid`, `rxnormid`, `drugbankid`, `atcid`, `guidelineid`, and `flowchart` URL.
- Also resolves drug names: can be used to find the `guidelineid` directly from a drug name.

**CPIC_get_gene_info**: `symbol` (string REQUIRED, e.g., "CYP2D6"). Returns gene coordinates, PharmGKB/HGNC/Ensembl IDs, `lookupmethod` (ACTIVITY_SCORE or PHENOTYPE), and allele frequency methodology.

---

## Phase 1: Identify Gene-Drug Pairs

**CPIC_search_gene_drug_pairs**: `gene_symbol` (string), `cpiclevel` ("A"/"B"/"C"/"D"), `limit` (int, default 50). Returns `{status, data: [{genesymbol, drugid, cpiclevel, guidelineid, pgxtesting, clinpgxlevel, usedforrecommendation}]}`.
- Primary tool for filtering by evidence level. CPIC levels: A = strongest/actionable, B = moderate, C = informational, D = insufficient.
- **PostgREST auto-normalization**: Accepts plain gene symbols (e.g., "CYP2D6") -- the tool auto-prepends `eq.` prefix.
- Also accepts aliases: `gene` or `gene_symbol` both resolve to `genesymbol`.

**CPIC_get_gene_drug_pairs**: `genesymbol` (string REQUIRED). Returns ALL pairs for one gene including `drug: {name}`, `citations`, `guidelineid`.
- Returns drug names in response (unlike search which returns RxNorm IDs only).

**CPIC_list_drugs**: No params. Returns all drugs with guideline IDs. Use for browsing.

**CPIC_list_pgx_genes**: No params. Returns all PGx genes curated by CPIC with `symbol`, `lookupmethod`, `ensemblid`.

**EpiGraphDB_get_gene_drug_associations**: `gene_name` (string REQUIRED, e.g., "CYP2D6"). Returns `{status, data: {gene_drug_associations: [{gene, drug, source, pharmgkb_evidence, cpic_level, pgx_on_fda_label, guideline}]}}`.
- Aggregates CPIC + PharmGKB evidence with FDA label status in one call. Good for quick overview.

### Finding Guideline IDs

Don't memorize guideline IDs. Use `CPIC_list_guidelines(gene="CYP2D6")` or `CPIC_list_guidelines(drug="codeine")` to discover them. Each result includes both the numeric `id` (for `CPIC_get_recommendations`) and the `clinpgxid` string (for `PharmGKB_get_dosing_guidelines`).

---

## Phase 2: Retrieve Dosing Guidelines

**CPIC_get_recommendations** (CPICGetRecommendationsTool): `guideline_id` (integer, OR `drug`/`drug_name` string for auto-resolution), `limit` (int, default 50), `offset` (int). Returns `{status, data: {guideline_id, recommendations: [{drugrecommendation, classification, phenotypes, implications, activityscore, lookupkey, population, drug: {name}}], count}}`.
- Preferred usage: `CPIC_get_recommendations(drug="codeine", limit=50)` — auto-resolves drug name to guideline_id via CPIC API, and filters within multi-drug guidelines (e.g., CYP2D6 opioid guideline covers codeine + tramadol) using RxNorm ID matching.
- `classification`: "Strong", "Moderate", or "Optional". `phenotypes`: maps gene → metabolizer phenotype. `activityscore`: maps gene → activity score.
- Fallback: `CPIC_get_drug_info(name="codeine")` to extract guidelineid, then `CPIC_get_recommendations(guideline_id=100416, limit=50)`.

**CPIC_get_drug_info**: `name` (string REQUIRED, lowercase, e.g., "codeine"). Returns `{status, data: [{drugid, guidelineid, flowchart, rxnormid, drugbankid}]}`.
- Key shortcut: returns `guidelineid` directly. Still useful for extracting DrugBank/ATC IDs.

**PharmGKB_get_dosing_guidelines**: `guideline_id` (string REQUIRED -- use `clinpgxid` from CPIC_list_guidelines, e.g., "PA166251445"). Returns `{status, data: {id, name, level, literature: [{title, crossReferences}], link}}`.
- Provides CPIC guideline metadata, literature citations, and link to full guideline.

**CPIC_list_guidelines**: `gene` (string, optional), `drug` (string, optional). Returns `{status, data: [{id, name, url, genes, clinpgxid}]}`. Returns all ~29 guidelines; supports built-in filtering by gene/drug.
- Use this to discover `clinpgxid` values for PharmGKB_get_dosing_guidelines.

> **Note**: `PharmGKB_get_clinical_annotations` requires an `annotation_id` (e.g., "1447954390"). To discover annotation IDs, use `PharmGKB_search_variants(query=rsID)` first, then extract annotation IDs from the results.

### Gotchas

- **Warfarin** (guideline 100425): Algorithm-based dosing; `CPIC_get_recommendations` returns 0 rows. Direct users to CPIC website or PharmGKB.
- **PharmGKB guideline linking**: Use `clinpgxid` (e.g., "PA166251445"), NOT `pharmgkbid` (old format returns 404).
- **Multi-gene guidelines**: TCA guideline (100414) covers both CYP2D6 and CYP2C19; recommendations have phenotype combinations.
- **Drug name case**: `CPIC_get_drug_info` requires lowercase. `CPIC_get_recommendations` with `drug=` uses ilike matching (case-insensitive).
- **CPIC_get_recommendations returns wrapped data**: Response is `{status, data: {guideline_id, recommendations: [...], count}}` -- recommendations are nested under `data.recommendations`.

---

## Phase 3: Allele & Variant Annotation

**CPIC_get_alleles**: `genesymbol` (string REQUIRED), `limit` (int, default 50). Returns `{status, data: [{name, clinicalfunctionalstatus, activityvalue, functionalstatus}]}`.
- Use `clinicalfunctionalstatus` (not `functionalstatus` which may be null). Values: "Normal function", "Decreased function", "No function", "Increased function", "Uncertain function", "Unknown function".
- `activityvalue`: numeric string (e.g., "1.0", "0.5", "0.0") or "n/a".

**PharmGKB_search_variants**: `query` (string REQUIRED, rsID). Returns variant classification and clinical significance.

**PharmGKB_get_clinical_annotations**: `annotation_id` (string REQUIRED, e.g., "1447954390"). Returns `{status, data: {accessionId, allelePhenotypes: [{allele, phenotype, limitedEvidence}], levelOfEvidence: {term}}}`.
- REQUIRES annotation_id -- cannot query by gene/drug directly. Discover IDs via `PharmGKB_search_variants(query=rsID)` or from the PharmGKB website.
- `levelOfEvidence.term`: "1A", "1B", "2A", "2B", "3", "4" (PharmGKB evidence levels).

**PharmGKB_get_gene_details**: `gene_id` (string REQUIRED, PharmGKB accession e.g., "PA128"). Returns detailed gene info including allele definition files, VIP citations.

**PharmGKB_get_drug_details**: `drug_id` (string REQUIRED, PharmGKB chemical ID e.g., "PA449088"). Returns drug metadata including SMILES, InChI, type (Drug/Prodrug).

**OpenTargets_drug_pharmacogenomics_data**: `chemblId` (string REQUIRED, e.g., "CHEMBL1201560"), `size` (int). Returns PGx variant data from OpenTargets including variant consequences and drug associations.
- Queries by drug (ChEMBL ID), not by gene. Use when you have a ChEMBL ID and want PGx variant annotations from OpenTargets.

### Metabolizer Status Reasoning

A poor metabolizer has reduced or absent enzyme activity. What that means clinically depends entirely on whether the drug is active or a prodrug:

- **Active drug + poor metabolizer**: drug accumulates → toxicity risk (e.g., codeine is a prodrug — this case doesn't apply; but nortriptyline is active — PM → high plasma levels → side effects).
- **Prodrug + poor metabolizer**: less conversion to active form → reduced efficacy (e.g., codeine → morphine; clopidogrel → active thienopyridine).
- **Prodrug + ultrarapid metabolizer**: excess activation → toxicity (classic case: codeine in CYP2D6 UM → morphine accumulation → respiratory depression).

This active-vs-prodrug distinction determines the direction of clinical concern. Get it right before interpreting any metabolizer phenotype.

**Star allele reasoning**: Don't memorize allele tables. The logic is always: allele function status (normal / decreased / no function) → diplotype → predicted enzyme activity → phenotype (UM/NM/IM/PM) → clinical recommendation. Use `CPIC_get_alleles(genesymbol=...)` to look up function status for any specific allele.

---

## Phase 4: FDA Biomarker Labeling

**fda_pharmacogenomic_biomarkers**: `drug_name` (string, optional), `biomarker` (string, optional, e.g., "CYP2D6"), `limit` (integer, default 10). Returns `{status, count, shown, results: [{Drug, TherapeuticArea, Biomarker, LabelingSection}]}`.
- ALWAYS pass `limit=1000` for complete results (default is 10).
- `LabelingSection` values: "Dosage and Administration", "Clinical Pharmacology", "Precautions", "Use in Specific Populations", "Boxed Warning", "Contraindications".
- Can query by drug, biomarker, or both.
- Not all drugs have entries (e.g., simvastatin absent for SLCO1B1; use rosuvastatin for SLCO1B1 PGx testing).

**FDA_get_pharmacogenomics_info_by_drug_name**: `drug_name` (string REQUIRED). Returns FDA label PGx sections with brand/generic names. Good for finding PGx labeling text in actual FDA labels.

### FDA PGx Label Reasoning

The `LabelingSection` field tells you how actionable the PGx information is. "Boxed Warning" or "Contraindications" means testing may be required or the drug contraindicated in certain genotypes — highest urgency. "Dosage and Administration" means genotype directly drives dose selection. "Clinical Pharmacology" is usually informational (PK/PD data), not a prescribing directive. When in doubt, retrieve the full label text with `FDA_get_pharmacogenomics_info_by_drug_name`.

---

## Phase 5: Cross-Database Enrichment

**DGIdb_get_drug_gene_interactions**: `genes` (array of strings REQUIRED, e.g., `["CYP2D6"]`), `interaction_types` (array, optional), `interaction_sources` (array, optional). Returns drug-gene interactions with sources.
- Broader coverage than CPIC; includes non-PGx interactions.
- Client-side filtering applied for `interaction_types` and `sources` parameters.

**DGIdb_get_gene_druggability**: `genes` (array of strings REQUIRED). Returns `{status, data: {data: {genes: {nodes: [{name, geneCategories}]}}}}`.
- Returns gene categories (e.g., "CLINICALLY ACTIONABLE", "DRUGGABLE GENOME").

**PharmGKB_get_dosing_guidelines**: (also in Phase 2) Provides DPWG (Dutch Pharmacogenetics Working Group) guidelines alongside CPIC.

**OpenTargets_drug_pharmacogenomics_data**: `chemblId` (string REQUIRED), `size` (int). Returns PGx variant annotations from the OpenTargets platform.
- Complements CPIC data with additional variant-level PGx evidence.

### Adverse Event Signal Detection for PGx-Relevant Drugs

**FAERS_filter_serious_events**: `drug_name` (string REQUIRED), `seriousness_type` ("all"/"death"/"hospitalization"/"disability"/"life_threatening"), `adverse_event` (string, optional). Use to detect serious adverse event signals for PGx-relevant drugs — e.g., respiratory depression reports for codeine in the context of CYP2D6 UM status. The `adverse_event` parameter filters to reports containing that specific reaction term.

**Optional**: `DisGeNET_get_vda` for variant-disease associations (requires DISGENET_API_KEY).

---

## When PGx Testing Changes Clinical Decisions

PGx testing changes clinical decisions ONLY for drugs with narrow therapeutic indices metabolized by polymorphic enzymes where genotype reliably predicts outcome. If the drug has a wide therapeutic index or is cleared by multiple redundant pathways, PGx status rarely alters the prescribing decision even when a variant is present.

**Evidence grading — reasoning approach**: CPIC levels A/B represent actionable evidence; C/D are informational. PharmGKB level 1A means the annotation is already embedded in a CPIC or DPWG guideline — the highest confidence tier. Levels 3/4 are hypothesis-generating, not prescribing-grade. CPIC recommendation strength (Strong/Moderate/Optional) within a guideline reflects how certain the genotype-to-outcome link is for that specific phenotype.

The key question is not "what level is this?" but "does this level justify changing the prescription?" For Level A CPIC with Strong classification, yes. For PharmGKB level 3, no — report it but don't act on it alone.

---

## Key Parameter Notes

Critical parameter behaviors to remember — these are the ones that actually cause failures:

- `CPIC_get_recommendations`: accepts `guideline_id` (integer) OR `drug`/`drug_name` (string). Never pass guideline_id as a string.
- `PharmGKB_get_dosing_guidelines`: requires `clinpgxid` (e.g., "PA166251445"), not the numeric `pharmgkbid`. Get clinpgxid from `CPIC_list_guidelines`.
- `PharmGKB_get_clinical_annotations`: requires `annotation_id`. Cannot query by gene or drug. Discover IDs via `PharmGKB_search_variants(query=rsID)`.
- `fda_pharmacogenomic_biomarkers`: default `limit=10` is almost always too small. Pass `limit=1000`.
- `CPIC_get_drug_info`: drug name must be lowercase.
- `DGIdb_get_drug_gene_interactions` and `DGIdb_get_gene_druggability`: `genes` is an array, not a string (e.g., `["CYP2D6"]`).
- `CPIC_search_gene_drug_pairs`: returns RxNorm IDs, not drug names. Use `CPIC_get_gene_drug_pairs` when you need drug names.

---

## CPIC Guideline Application Reasoning

CPIC guidelines give genotype → phenotype → recommendation mappings. The skill is knowing when to apply them, not memorizing the mappings themselves. Use tools to retrieve the specific recommendation for the specific phenotype. The reasoning chain is:

1. Does a CPIC guideline exist for this gene-drug pair? (Level A or B = actionable)
2. What is the patient's phenotype? (from diplotype + allele function statuses)
3. What does the guideline recommend for that phenotype? (retrieve with `CPIC_get_recommendations`)
4. Is there FDA label reinforcement? (check `fda_pharmacogenomic_biomarkers`)

If step 1 is no, fall back to PharmGKB variant annotations for evidence-graded but non-guideline information.

---

## Fallback Strategies

- **No CPIC guideline** -> Use `PharmGKB_search_variants(query=rsID)` for variant-level annotations; check EpiGraphDB for gene-drug evidence
- **CPIC_get_recommendations returns 0 rows** -> Check if algorithm-based (warfarin); use PharmGKB_get_dosing_guidelines
- **CPIC_get_recommendations drug auto-resolve fails** -> Fall back to CPIC_get_drug_info(name=drug) + manual guideline_id extraction
- **No FDA biomarker entry** -> Check DGIdb for known interactions; check EpiGraphDB `pgx_on_fda_label` field
- **Unknown variant** -> PharmGKB_search_variants by rsID; note as uncharacterized if absent
- **Need drug name from RxNorm ID** -> Use CPIC_get_gene_drug_pairs (returns `drug: {name}`) instead of CPIC_search_gene_drug_pairs (returns only RxNorm IDs)
- **PharmGKB annotation_id unknown** -> Get annotation IDs from PharmGKB website or via `PharmGKB_search_variants(query=rsID)`
- **Need additional PGx variant data** -> Use `OpenTargets_drug_pharmacogenomics_data(chemblId=...)` with ChEMBL ID

---

## Example Workflows

**Drug-first (codeine + CYP2D6 PM)**: `CPIC_get_recommendations(drug="codeine", limit=50)` → filter `phenotypes.CYP2D6="Poor Metabolizer"` → Strong recommendation: avoid codeine. Then `CPIC_get_alleles(genesymbol="CYP2D6", limit=100)` to confirm star allele function (e.g., *4/*4 → no function, AS 0.0). Then `fda_pharmacogenomic_biomarkers(drug_name="codeine", limit=1000)` to confirm FDA label status. Gene-first alternative: `CPIC_get_gene_drug_pairs(genesymbol="CYP2D6")` to list all associated drugs.

**Gene-first (all CYP2C19 drugs)**: `CPIC_search_gene_drug_pairs(gene_symbol="CYP2C19", cpiclevel="A")` for Level A pairs. `EpiGraphDB_get_gene_drug_associations(gene_name="CYP2C19")` for CPIC + PharmGKB + FDA label overview in one call. `fda_pharmacogenomic_biomarkers(biomarker="CYP2C19", limit=1000)` for complete FDA coverage.

**Variant-first (rs1799853)**: `PharmGKB_search_variants(query="rs1799853")` → CYP2C9 variant, drug-response significance. `CPIC_get_alleles(genesymbol="CYP2C9", limit=100)` → maps to *2, "Decreased function". `CPIC_get_gene_drug_pairs(genesymbol="CYP2C9")` → warfarin, phenytoin, NSAIDs. For each drug with a guideline: `CPIC_get_recommendations(drug="phenytoin", limit=50)`.

---

## Drug Class Context (RxClass)

When PGx analysis involves understanding which drug class a substrate belongs to, or finding all drugs in a class that share the same metabolizing enzyme: use `RxClass_get_drug_classes(drug_name=...)` to get all class memberships for a drug, `RxClass_find_classes(query=..., class_type=...)` to find class IDs from a keyword, and `RxClass_get_class_members(class_id=..., rela_source=..., ttys="IN")` to list all drugs in a class. Example: find all SSRIs to advise which require CYP2D6 testing as a class note.

## FDA Substance Identification (FDAGSRS)

For canonical FDA substance identification (UNII codes, cross-references to ATC/DrugBank/CAS): use `FDAGSRS_search_substances(query=...)` to find the UNII code, `FDAGSRS_get_substance(unii=...)` for the full record with all names and cross-references, and `FDAGSRS_get_structure(unii=...)` for SMILES/InChIKey. Useful to confirm that two drug name variants (e.g., "warfarin sodium" and "warfarin") share the same UNII before cross-referencing in CPIC or PharmGKB.

---

## Limitations

- CPIC covers ~29 guidelines (~130 genes); many drug-gene pairs lack formal guidelines.
- PharmGKB clinical annotation IDs must be discovered (not derivable from gene/drug names alone -- use PharmGKB website or PharmGKB_search_variants for rsID-based lookup).
- Warfarin dosing requires algorithmic calculation (CPIC website), not simple table lookup.
- FDA biomarker table may lag behind current labeling changes.
- DisGeNET requires API key (DISGENET_API_KEY).
- CPIC_search_gene_drug_pairs returns RxNorm drug IDs, not drug names; use CPIC_get_gene_drug_pairs for names.
- Activity score interpretation varies by gene (CYP2D6 uses numeric scores; others may use phenotype-based lookup).
- CPIC_get_recommendations drug auto-resolution uses ilike matching -- ambiguous drug names may match multiple entries.


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
