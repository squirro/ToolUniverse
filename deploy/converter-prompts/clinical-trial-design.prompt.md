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
- search_clinical_trials signature={'properties': {'condition': {'description': 'Query for condition or disease using Essie expression syntax (e.g., \'lung cancer\', \'(head OR neck) AND pain AND NOT "back pain"\'). ', 'required': False, 'type': 'string'}, 'intervention': {'description': "Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').", 'required': False, 'type': 'string'}, 'keyword': {'description': 'Alias for query_term. Free-text keyword search across all trial fields (e.g., drug name, condition, investigator).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Alias for max_results: maximum number of studies to return (default 10, max 1000).', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Maximum number of studies to return (alias for pageSize, default 10, max 1000).', 'required': False, 'type': 'integer'}, 'overall_status': {'description': "Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUITING', 'NOT_YET_RECRUITING']). Valid values: RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED, WITHDRAWN.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'pageSize': {'description': 'Maximum number of studies to return per page (default 10, max 1000).', 'required': False, 'type': 'integer'}, 'pageToken': {'description': "Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.", 'required': False, 'type': 'string'}, 'query_term': {'description': "Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.", 'required': False, 'type': 'string'}, 'status': {'description': 'Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLETED".', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': False}}, 'required': [], 'type': 'object'}
- OpenFDA_get_approval_history signature={'properties': {'application_number': {'description': "FDA application number (e.g., 'NDA021457'). More specific than drug_name.", 'required': False, 'type': ['string', 'null']}, 'drug_name': {'description': "Drug name (brand or generic, e.g., 'warfarin', 'Eliquis', 'pembrolizumab')", 'required': False, 'type': ['string', 'null']}, 'operation': {'description': 'Operation type', 'enum': ['get_approval_history'], 'required': True, 'type': 'string'}}, 'required': ['operation'], 'type': 'object'}
- ClinVar_search_variants signature={'properties': {'clinical_significance': {'description': "Filter by clinical significance (e.g., 'Pathogenic', 'Likely pathogenic', 'Benign', 'Uncertain significance', 'VUS'). Applied client-side after retrieval.", 'required': False, 'type': 'string'}, 'condition': {'description': "Disease or condition name (e.g., 'breast cancer', 'diabetes') At least one of gene, condition, or variant_id must be provided.", 'required': False, 'type': 'string'}, 'gene': {'description': "Gene name or symbol (e.g., 'BRCA1', 'BRCA2') At least one of gene, condition, or variant_id must be provided.", 'required': False, 'type': 'string'}, 'gene_symbol': {'description': 'Alias for gene. HGNC gene symbol (e.g., "DPYD", "CYP2C19").', 'required': False, 'type': ['string', 'null']}, 'limit': {'description': 'Alias for max_results: maximum number of results to return.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'default': 20, 'description': 'Maximum number of results to return (default: 20). Alias: limit.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'query': {'description': 'Alias for condition. Free-text search mapped to condition/disease field.', 'required': False, 'type': ['string', 'null']}, 'significance': {'description': 'Alias for clinical_significance (e.g., "pathogenic", "benign", "uncertain_significance").', 'required': False, 'type': ['string', 'null']}, 'variant_id': {'description': "ClinVar variant ID (e.g., '12345') At least one of gene, condition, or variant_id must be provided.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- gnomad_search_variants signature={'properties': {'dataset': {'default': 'gnomad_r3', 'description': 'gnomAD dataset ID. Allowed values: gnomad_r4, gnomad_r4_non_ukb, gnomad_r3, gnomad_r3_controls_and_biobanks, gnomad_r3_non_cancer, gnomad_r3_non_neuro, gnomad_r3_non_topmed, gnomad_r3_non_v2, gnomad_r2_1, gnomad_r2_1_controls, gnomad_r2_1_non_neuro, gnomad_r2_1_non_cancer, gnomad_r2_1_non_topmed, exac.', 'required': False, 'type': 'string'}, 'query': {'description': "Variant search query (e.g., 'rs7412').", 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- ClinVar_get_variant_details signature={'properties': {'variant_id': {'description': "ClinVar variant ID (e.g., '12345', '123456')", 'required': True, 'type': 'string'}}, 'required': ['variant_id'], 'type': 'object'}
- COSMIC_search_mutations signature={'properties': {'genome_build': {'default': 37, 'description': 'Genome build version: 37 (GRCh37/hg19) or 38 (GRCh38/hg38). Default: 37', 'enum': [37, 38], 'required': False, 'type': 'integer'}, 'max_results': {'default': 20, 'description': 'Maximum number of results to return (default: 20, max: 500)', 'maximum': 500, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'const': 'search', 'description': 'Operation type (fixed: search)', 'required': False, 'type': 'string'}, 'query': {'description': 'Alias for terms. Search query - gene name, mutation, or COSMIC ID.', 'required': False, 'type': 'string'}, 'terms': {'description': 'Search query - gene name (e.g., BRAF), mutation (e.g., V600E), or mutation ID (e.g., COSM476). Aliases: query or gene also accepted.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- gnomad_get_variant signature={'properties': {'dataset': {'default': 'gnomad_r3', 'description': 'gnomAD dataset ID. Allowed values: gnomad_r4, gnomad_r4_non_ukb, gnomad_r3, gnomad_r3_controls_and_biobanks, gnomad_r3_non_cancer, gnomad_r3_non_neuro, gnomad_r3_non_topmed, gnomad_r3_non_v2, gnomad_r2_1, gnomad_r2_1_controls, gnomad_r2_1_non_neuro, gnomad_r2_1_non_cancer, gnomad_r2_1_non_topmed, exac.', 'required': False, 'type': 'string'}, 'variant_id': {'description': "Variant ID (e.g., '19-44908822-C-T').", 'required': True, 'type': 'string'}}, 'required': ['variant_id'], 'type': 'object'}
- FDA_OrangeBook_search_drug signature={'properties': {'application_number': {'description': "FDA application number (e.g., 'NDA020402', 'ANDA078394')", 'required': False, 'type': 'string'}, 'brand_name': {'description': "Brand/trade name of drug (e.g., 'ADVIL', 'LIPITOR')", 'required': False, 'type': 'string'}, 'generic_name': {'description': "Generic/active ingredient name (e.g., 'IBUPROFEN', 'ATORVASTATIN')", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of results (1-100, default 10)', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'const': 'search_drug', 'description': 'Operation type (fixed)', 'required': False}}, 'required': [], 'type': 'object'}
- FDA_get_warnings_and_cautions_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FAERS_search_reports_by_drug_and_reaction signature={'properties': {'limit': {'default': 10, 'description': 'Maximum number of reports to return. Must be between 1 and 100.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'medicinalproduct': {'description': 'Drug name (required).', 'required': True, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'reactionmeddrapt': {'description': "MedDRA preferred term for the adverse reaction (required). Example: 'INFUSION RELATED REACTION', 'DYSPNOEA'.", 'required': True, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'skip': {'default': 0, 'description': 'Number of reports to skip for pagination. Must be non-negative.', 'minimum': 0, 'required': False, 'type': 'integer'}}, 'required': ['medicinalproduct', 'reactionmeddrapt'], 'type': 'object'}
- FAERS_count_reactions_by_drug_event signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}, 'occurcountry': {'description': "Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.", 'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'reactionmeddraverse': {'description': 'Optional: Filter by MedDRA reaction term (Lowest Level Term). When omitted, returns all adverse reactions with their counts. When specified, filters results to only include that specific reaction term.', 'required': False, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'seriousnessdeath': {'description': "Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit this parameter to include all reports regardless of death outcome.", 'enum': ['Yes'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FAERS_count_death_related_by_drug signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- OpenTargets_get_disease_id_description_by_name
- OpenTargets_get_diseases_phenotypes_by_target_ensembl
- drugbank_get_drug_basic_info_by_drug_name_or_id
- drugbank_get_indications_by_drug_name_or_drugbank_id
- drugbank_get_pharmacology_by_drug_name_or_drugbank_id

# TARGET SKILL TO CONVERT
---
name: tooluniverse-clinical-trial-design
description: Strategic clinical trial design feasibility assessment. Analyzes 6 dimensions (endpoint, population, comparator, effect size, duration, regulatory pathway) using precedent trials and FDA guidance. Produces enrollment projections, endpoint recommendations, and approval-pathway analysis. Use for trial-protocol design, power/sample-size estimation, comparator selection, and FDA submission strategy. Driven by precedent-based reasoning rather than first-principles math.
disable-model-invocation: true
---

# Clinical Trial Design Feasibility Assessment

Systematically assess clinical trial feasibility by analyzing 6 research dimensions. Produces comprehensive feasibility reports with quantitative enrollment projections, endpoint recommendations, and regulatory pathway analysis.

**IMPORTANT**: Always use English terms in tool calls (drug names, disease names, biomarker names), even if the user writes in another language. Only try original-language terms as a fallback if English returns no results. Respond in the user's language.

## Reasoning Before Searching

Trial design starts with the question, not the methods. Answer these four questions before running any tools — they determine everything else:

1. **What is the primary endpoint?** Is it overall survival (gold standard but slow), PFS (faster but surrogate), ORR (single-arm friendly but not always accepted), or a biomarker (needs validation as surrogate first)? The endpoint determines FDA pathway, statistical design, and duration.
2. **Who is the population?** Broad unselected vs. biomarker-enriched. Enriched populations have higher response rates, allowing smaller trials — but require a validated companion diagnostic and reduce the eligible patient pool.
3. **What is the comparator?** Placebo (only if no standard of care exists), active control (requires non-inferiority or superiority framing), or single-arm with historical control (acceptable for rare diseases or breakthrough designations, but FDA scrutiny is high).
4. **Is the effect size realistic given the mechanism?** A 20% improvement in ORR over SOC requires ~100 patients per arm. A 50% improvement requires ~30. If the mechanism only justifies a 10% improvement, the trial may be underpowered regardless of design. Check precedent effect sizes in similar trials before committing to an endpoint.

These four answers determine sample size, duration, and trial design. Look them up from precedent trials and FDA guidance — do not derive them from first principles.

**LOOK UP DON'T GUESS**: Never assume what the standard of care is for an indication — look it up with DrugBank and FDA tools. Never assume an endpoint is FDA-accepted — verify with `search_clinical_trials` precedents and `OpenFDA_get_approval_history`. Never estimate prevalence from memory — use OpenTargets, gnomAD, or COSMIC.

## Core Principles

### 1. Report-First Approach (MANDATORY)
**DO NOT** show tool outputs to user. Instead:
1. Create `[INDICATION]_trial_feasibility_report.md` FIRST
2. Initialize with all section headers
3. Progressively update as data arrives
4. Present only the final report

### 2. Evidence Grading System

| Grade | Symbol | Criteria | Examples |
|-------|--------|----------|----------|
| **A** | 3-star | Regulatory acceptance, multiple precedents | FDA-approved endpoint in same indication |
| **B** | 2-star | Clinical validation, single precedent | Phase 3 trial in related indication |
| **C** | 1-star | Preclinical or exploratory | Phase 1 use, biomarker validation ongoing |
| **D** | 0-star | Proposed, no validation | Novel endpoint, no precedent |

### 3. Feasibility Score (0-100)
Weighted composite score:
- **Patient Availability** (30%): Population size x biomarker prevalence x geography
- **Endpoint Precedent** (25%): Historical use, regulatory acceptance
- **Regulatory Clarity** (20%): Pathway defined, precedents exist
- **Comparator Feasibility** (15%): Standard of care availability
- **Safety Monitoring** (10%): Known risks, monitoring established

**Interpretation**: >=75 HIGH (proceed), 50-74 MODERATE (additional validation), <50 LOW (de-risking required)

---

## When to Use This Skill

Apply when users:
- Plan early-phase trials (Phase 1/2 emphasis)
- Need enrollment feasibility assessment
- Design biomarker-selected trials
- Evaluate endpoint strategies
- Assess regulatory pathways
- Compare trial design options
- Need safety monitoring plans

**Trigger phrases**: "clinical trial design", "trial feasibility", "enrollment projections", "endpoint selection", "trial planning", "Phase 1/2 design", "basket trial", "biomarker trial"

---

## Core Strategy: 6 Research Paths

Execute 6 parallel research dimensions. See `STUDY_DESIGN_PROCEDURES.md` for detailed steps per path.

```
Trial Design Query
|
+-- PATH 1: Patient Population Sizing
|   Disease prevalence, biomarker prevalence, geographic distribution,
|   eligibility criteria impact, enrollment projections
|
+-- PATH 2: Biomarker Prevalence & Testing
|   Mutation frequency, testing availability, turnaround time,
|   cost/reimbursement, alternative biomarkers
|
+-- PATH 3: Comparator Selection
|   Standard of care, approved comparators, historical controls,
|   placebo appropriateness, combination therapy
|
+-- PATH 4: Endpoint Selection
|   Primary endpoint precedents, FDA acceptance history,
|   measurement feasibility, surrogate vs clinical endpoints
|
+-- PATH 5: Safety Endpoints & Monitoring
|   Mechanism-based toxicity, class effects, organ-specific monitoring,
|   DLT history, safety monitoring plan
|
+-- PATH 6: Regulatory Pathway
    Regulatory precedents (505(b)(1), 505(b)(2)), breakthrough therapy,
    orphan drug, fast track, FDA guidance
```

---

## Report Structure (14 Sections)

Create `[INDICATION]_trial_feasibility_report.md` with all 14 sections. See `REPORT_TEMPLATE.md` for full templates with fillable fields.

1. **Executive Summary** - Feasibility score, key findings, go/no-go recommendation
2. **Disease Background** - Prevalence, incidence, SOC, unmet need
3. **Patient Population Analysis** - Base population, biomarker selection, eligibility funnel, enrollment projections
4. **Biomarker Strategy** - Primary biomarker, alternatives, testing logistics
5. **Endpoint Selection & Justification** - Primary/secondary/exploratory endpoints, statistical considerations
6. **Comparator Analysis** - SOC, trial design options (single-arm vs randomized vs non-inferiority), drug sourcing
7. **Safety Endpoints & Monitoring Plan** - DLT definition, mechanism-based toxicities, organ monitoring, SMC
8. **Study Design Recommendations** - Phase, design type, schema, eligibility, treatment plan, assessment schedule
9. **Enrollment & Site Strategy** - Site selection, enrollment projections, recruitment strategies
10. **Regulatory Pathway** - FDA pathway, precedents, pre-IND meeting, IND timeline
11. **Budget & Resource Considerations** - Cost drivers, timeline, FTE requirements
12. **Risk Assessment** - Feasibility risks, scientific risks, mitigation strategies
13. **Success Criteria & Go/No-Go Decision** - Phase 1/2 criteria, interim analysis, feasibility scorecard
14. **Recommendations & Next Steps** - Final recommendation, critical path to IND, alternative designs

---

## Tool Reference by Research Path

### PATH 1: Patient Population Sizing
- `OpenTargets_get_disease_id_description_by_name` - Disease lookup
- `OpenTargets_get_diseases_phenotypes_by_target_ensembl` - Prevalence data
- `ClinVar_search_variants` - Biomarker mutation frequency
- `gnomad_search_variants` - Population allele frequencies
- `PubMed_search_articles` - Epidemiology literature
- `search_clinical_trials` - Enrollment feasibility from past trials

### PATH 2: Biomarker Prevalence & Testing
- `ClinVar_get_variant_details` - Variant pathogenicity
- `COSMIC_search_mutations` - Cancer-specific mutation frequencies
- `gnomad_get_variant` - Population genetics
- `PubMed_search_articles` - CDx test performance, guidelines

### PATH 3: Comparator Selection
- `drugbank_get_drug_basic_info_by_drug_name_or_id` - Drug info
- `drugbank_get_indications_by_drug_name_or_drugbank_id` - Approved indications
- `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` - Mechanism
- `FDA_OrangeBook_search_drug` - Generic availability
- `OpenFDA_get_approval_history` - Approval details
- `search_clinical_trials` - Historical control data

### PATH 4: Endpoint Selection
- `search_clinical_trials` - Precedent trials, endpoints used
- `PubMed_search_articles` - FDA acceptance history, endpoint validation
- `OpenFDA_get_approval_history` - Approved endpoints by indication

### PATH 5: Safety Endpoints & Monitoring
- `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` - Mechanism toxicity
- `FDA_get_warnings_and_cautions_by_drug_name` - FDA black box warnings
- `FAERS_search_reports_by_drug_and_reaction` - Real-world adverse events
- `FAERS_count_reactions_by_drug_event` - AE frequency
- `FAERS_count_death_related_by_drug` - Serious outcomes
- `PubMed_search_articles` - DLT definitions, monitoring strategies

### PATH 6: Regulatory Pathway
- `OpenFDA_get_approval_history` - Precedent approvals
- `PubMed_search_articles` - Breakthrough designations, FDA guidance
- `search_clinical_trials` - Regulatory precedents (accelerated approval)

---

## Quick Start Example

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Example: EGFR+ NSCLC trial feasibility
# Step 1: Disease prevalence
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName="non-small cell lung cancer"
)
prevalence = tu.tools.OpenTargets_get_diseases_phenotypes(
    efoId=disease_info['data']['id']
)

# Step 2: Biomarker prevalence
variants = tu.tools.ClinVar_search_variants(gene="EGFR", significance="pathogenic")

# Step 3: Precedent trials
trials = tu.tools.search_clinical_trials(
    condition="EGFR positive non-small cell lung cancer",
    status="completed", phase="2"
)

# Step 4: Standard of care comparator
soc = tu.tools.FDA_OrangeBook_search_drug(ingredient="osimertinib")

# Compile into feasibility report...
```

See `WORKFLOW_DETAILS.md` for the complete 6-path Python workflow and use case examples.

---

## Integration with Other Skills

- **tooluniverse-drug-research**: Investigate mechanism, preclinical data
- **tooluniverse-disease-research**: Deep dive on disease biology
- **tooluniverse-target-research**: Validate drug target, essentiality
- **tooluniverse-pharmacovigilance**: Post-market safety for comparator drugs
- **tooluniverse-precision-oncology**: Biomarker biology, resistance mechanisms

---

## Programmatic Access (Beyond Tools)

When ToolUniverse tools return limited trial metadata, use the ClinicalTrials.gov v2 API directly:

```python
import requests, pandas as pd

# Search with pagination (all lung cancer immunotherapy trials with results)
all_studies = []
token = None
while True:
    params = {"query.cond": "lung cancer", "query.intr": "immunotherapy",
              "filter.overallStatus": "COMPLETED", "filter.results": "WITH_RESULTS", "pageSize": 100}
    if token: params["pageToken"] = token
    resp = requests.get("https://clinicaltrials.gov/api/v2/studies", params=params).json()
    all_studies.extend(resp.get("studies", []))
    token = resp.get("nextPageToken")
    if not token: break

# Extract structured data
rows = []
for s in all_studies:
    proto = s.get("protocolSection", {})
    rows.append({
        "nctId": proto.get("identificationModule", {}).get("nctId"),
        "title": proto.get("identificationModule", {}).get("briefTitle"),
        "enrollment": proto.get("designModule", {}).get("enrollmentInfo", {}).get("count"),
        "phase": proto.get("designModule", {}).get("phases", [None])[0] if proto.get("designModule", {}).get("phases") else None,
    })
df = pd.DataFrame(rows)

# FDA drug approval history
drug = "pembrolizumab"
fda = requests.get(f"https://api.fda.gov/drug/drugsfda.json?search=openfda.brand_name:{drug}&limit=10").json()
```

See `tooluniverse-data-wrangling` skill for pagination, error handling, and bulk download patterns.

---

## Reference Files

| File | Content |
|------|---------|
| `REPORT_TEMPLATE.md` | Full 14-section report template with fillable fields |
| `STUDY_DESIGN_PROCEDURES.md` | Detailed steps for each of the 6 research paths |
| `WORKFLOW_DETAILS.md` | Complete Python example workflow and 5 use case summaries |
| `BEST_PRACTICES.md` | Best practices, common pitfalls, output format requirements |
| `EXAMPLES.md` | Additional examples |
| `QUICK_START.md` | Quick start guide |

---

## Version Information

- **Version**: 1.0.0
- **Last Updated**: February 2026
- **Compatible with**: ToolUniverse 0.5+
- **Focus**: Phase 1/2 early clinical development


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
