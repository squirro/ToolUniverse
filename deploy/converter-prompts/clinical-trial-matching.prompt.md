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
- get_clinical_trial_descriptions signature={'properties': {'description_type': {'description': "Type of information to retrieve. Options are 'brief' for brief descriptions or 'full' for full descriptions.", 'enum': ['brief', 'full'], 'required': True, 'type': 'string'}, 'nct_ids': {'description': "List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).", 'items': {'type': 'string'}, 'required': True, 'type': 'array'}}, 'required': ['nct_ids', 'description_type'], 'type': 'object'}
- get_clinical_trial_eligibility_criteria signature={'properties': {'eligibility_criteria': {'description': 'Unused filter parameter, kept for backward compatibility. Can be omitted or set to any string.', 'required': False, 'type': 'string'}, 'nct_ids': {'description': "List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).", 'items': {'type': 'string'}, 'required': True, 'type': 'array'}}, 'required': ['nct_ids'], 'type': 'object'}
- get_clinical_trial_locations signature={'properties': {'location': {'description': 'Unused filter parameter, kept for backward compatibility. Can be omitted or set to any string.', 'required': False, 'type': 'string'}, 'nct_ids': {'description': "List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).", 'items': {'type': 'string'}, 'required': True, 'type': 'array'}}, 'required': ['nct_ids'], 'type': 'object'}
- get_clinical_trial_status_and_dates signature={'properties': {'nct_ids': {'description': "List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).", 'items': {'type': 'string'}, 'required': True, 'type': 'array'}, 'status_and_date': {'description': 'Unused filter parameter, kept for backward compatibility. Can be omitted or set to any string.', 'required': False, 'type': 'string'}}, 'required': ['nct_ids'], 'type': 'object'}
- get_clinical_trial_outcome_measures signature={'properties': {'nct_ids': {'description': "List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).", 'items': {'type': 'string'}, 'required': True, 'type': 'array'}, 'outcome_measures': {'description': "Decides whether to retrieve primary, secondary, or all outcome measures. Options are 'primary', 'secondary', or 'all'. Default is 'primary'.", 'enum': ['primary', 'secondary', 'all'], 'required': False, 'type': 'string'}}, 'required': ['nct_ids'], 'type': 'object'}
- MyGene_query_genes signature={'properties': {'fields': {'default': 'symbol,name,entrezgene,ensembl.gene,summary', 'description': 'Comma-separated list of fields to return. Common fields: symbol, name, entrezgene, ensembl.gene, summary, go, pathway, interpro.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query. Can be gene symbol (e.g., 'CDK2'), name ('cyclin dependent kinase'), Entrez ID ('1017'), or Ensembl ID ('ENSG00000123374'). Supports wildcards (*) and boolean operators (AND, OR, NOT).", 'required': True, 'type': 'string'}, 'size': {'default': 10, 'description': 'Maximum number of results to return (1-100).', 'required': False, 'type': 'integer'}, 'species': {'default': 'human', 'description': "Species filter. Use common name or NCBI taxonomy ID. Examples: 'human', 'mouse', '9606' (human), 'all'.", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- OpenTargets_get_target_id_description_by_name signature={'properties': {'targetName': {'description': 'The name of the target for which the ID is required.', 'required': True, 'type': 'string'}}, 'required': ['targetName'], 'type': 'object'}
- ols_search_efo_terms signature={'properties': {'query': {'description': 'Search query (free text).', 'required': True, 'type': 'string'}, 'rows': {'default': 10, 'description': 'Maximum number of results to return.', 'required': False, 'type': 'integer'}}, 'required': ['query'], 'type': 'object'}
- OpenTargets_get_drug_id_description_by_name signature={'properties': {'drugName': {'description': 'The name of the drug for which the ID is required.', 'required': True, 'type': 'string'}}, 'required': ['drugName'], 'type': 'object'}
- fda_pharmacogenomic_biomarkers signature={'properties': {'biomarker': {'description': "Filter by the specific biomarker (e.g., 'CYP2D6', 'HLA-B*5701'). Case-insensitive partial match.", 'required': False, 'type': 'string'}, 'drug_name': {'description': "Filter by the name of the drug (e.g., 'Sivextro', 'Abacavir'). Case-insensitive partial match.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of results to return.', 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- FDA_get_indications_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- civic_get_variants_by_gene signature={'properties': {'gene': {'description': "Alias for gene_name. Gene symbol (e.g., 'EGFR', 'KRAS').", 'required': False, 'type': 'string'}, 'gene_id': {'description': 'CIViC gene ID (e.g., 19 for EGFR, 12 for BRAF). Find gene IDs using civic_search_genes.', 'required': False, 'type': 'integer'}, 'gene_name': {'description': "Gene symbol (e.g., 'EGFR', 'BRAF', 'TP53'). Will be looked up automatically. Aliases: gene, gene_symbol, query.", 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "Alias for gene_name. Standard gene symbol (e.g., 'KRAS', 'BRCA1', 'EGFR').", 'required': False, 'type': 'string'}, 'limit': {'default': 500, 'description': "Maximum number of variants to return (default: 500, uses cursor pagination to bypass CIViC's 100/page server cap)", 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- PharmGKB_search_genes signature={'properties': {'query': {'description': "Gene name, symbol, or PharmGKB Accession ID (e.g., 'CYP2D6', 'PA128').", 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- civic_search_variants signature={'properties': {'gene': {'description': "Gene symbol to filter variants by (e.g., 'EGFR', 'BRAF', 'KRAS'). Returns all variants for that gene.", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for gene. Gene symbol (e.g., 'TP53', 'BRCA1').", 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'description': 'Maximum number of variants to return (default: 20, recommended max: 100)', 'required': False, 'type': 'integer'}, 'query': {'description': 'Variant name to search for (e.g., "T790M", "V600E", "exon 19 deletion"). Returns name-matching variants.', 'required': False, 'type': 'string'}, 'variant_name': {'description': "Specific variant name to filter within a gene (e.g., 'L858R', 'V600E', 'T790M'). Use together with gene_name â\x80\x94 CIViC stores variants without the gene prefix (use 'L858R' not 'EGFR L858R').", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- query_term
- nct_id
- nct_ids
- get_clinical_trial_conditions_and_interventions
- OpenTargets_get_disease_id_description_by_name
- OpenTargets_get_drug_mechanisms_of_action_by_chemblId
- OpenTargets_get_associated_drugs_by_target_ensemblID
- drugbank_get_targets_by_drug_name_or_drugbank_id
- case_sensitive
- exact_match
- drug_name
- max_results
- gene_id

# TARGET SKILL TO CONVERT
---
name: tooluniverse-clinical-trial-matching
description: AI-driven patient-to-trial matching for precision oncology and rare-disease care. Transforms a patient's molecular profile (mutations, biomarkers, expression) and clinical state into ranked clinical-trial recommendations with evidence tiers. Searches ClinicalTrials.gov plus cross-references CIViC, OpenTargets, ChEMBL, and FDA labels. Use for matching patients to trials by genotype, biomarker-driven trial selection, and trial-eligibility scoring.
disable-model-invocation: true
---

# Clinical Trial Matching for Precision Medicine

Transform patient molecular profiles and clinical characteristics into prioritized clinical trial recommendations. Searches ClinicalTrials.gov and cross-references with molecular databases (CIViC, OpenTargets, ChEMBL, FDA) to produce evidence-graded, scored trial matches.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Patient-centric** - Every recommendation considers the individual patient's profile
3. **Molecular-first matching** - Prioritize trials targeting patient's specific biomarkers

## Molecular Matching Priority

Match patients to trials by molecular profile FIRST (specific mutations), then by disease stage, then by prior treatments. A patient with EGFR L858R should match to EGFR-targeted trials regardless of other factors.
4. **Evidence-graded** - Every recommendation has an evidence tier (T1-T4)
5. **Quantitative scoring** - Trial Match Score (0-100) for every trial
6. **Eligibility-aware** - Parse and evaluate inclusion/exclusion criteria
7. **Actionable output** - Clear next steps, contact info, enrollment status
8. **Source-referenced** - Every statement cites the tool/database source
9. **Completeness checklist** - Mandatory section showing analysis coverage
10. **English-first queries** - Always use English terms in tool calls. Respond in user's language

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Apply when user asks:
- "What clinical trials are available for my NSCLC with EGFR L858R?"
- "Patient has BRAF V600E melanoma, failed ipilimumab - what trials?"
- "Find basket trials for NTRK fusion"
- "Breast cancer with HER2 amplification, post-CDK4/6 inhibitor trials"
- "KRAS G12C colorectal cancer clinical trials"
- "Immunotherapy trials for TMB-high solid tumors"
- "Clinical trials near Boston for lung cancer"
- "What are my options after failing osimertinib for EGFR+ NSCLC?"

**NOT for** (use other skills instead):
- Single variant interpretation without trial focus -> Use `tooluniverse-cancer-variant-interpretation`
- Drug safety profiling -> Use `tooluniverse-adverse-event-detection`
- Target validation -> Use `tooluniverse-drug-target-validation`
- General disease research -> Use `tooluniverse-disease-research`

---

## Input Parsing

### Required Input
- **Disease/cancer type**: Free-text disease name (e.g., "non-small cell lung cancer", "melanoma")

### Strongly Recommended
- **Molecular alterations**: One or more biomarkers (e.g., "EGFR L858R", "KRAS G12C", "PD-L1 50%", "TMB-high")
- **Stage/grade**: Disease stage (e.g., "Stage IV", "metastatic", "locally advanced")
- **Prior treatments**: Previous therapies and outcomes (e.g., "failed platinum chemotherapy", "progressed on osimertinib")

### Optional
- **Performance status**: ECOG or Karnofsky score
- **Geographic location**: City/state for proximity filtering
- **Trial phase preference**: I, II, III, IV, or "any"
- **Intervention type**: drug, biological, device, etc.
- **Recruiting status preference**: recruiting, not yet recruiting, active

For biomarker parsing rules and gene symbol normalization, see [MATCHING_ALGORITHMS.md](./MATCHING_ALGORITHMS.md).

---

## Workflow Overview

```
Input: Patient profile (disease + biomarkers + stage + prior treatments)

Phase 1: Patient Profile Standardization
  - Resolve disease to EFO/ontology IDs (OpenTargets, OLS)
  - Parse molecular alterations to gene + variant
  - Resolve gene symbols to Ensembl/Entrez IDs (MyGene)
  - Classify biomarker actionability (FDA-approved vs investigational)

Phase 2: Broad Trial Discovery
  - Disease-based trial search (ClinicalTrials.gov)
  - Biomarker-specific trial search
  - Intervention-based search (for known drugs targeting patient's biomarkers)
  - Deduplicate and collect NCT IDs

Phase 3: Trial Characterization (batch, groups of 10)
  - Eligibility criteria, conditions/interventions, locations, status, descriptions

Phase 4: Molecular Eligibility Matching
  - Parse eligibility text for biomarker requirements
  - Match patient's molecular profile to trial requirements
  - Score molecular eligibility (0-40 points)

Phase 5: Drug-Biomarker Alignment
  - Identify trial intervention drugs and mechanisms (OpenTargets, ChEMBL)
  - FDA approval status for biomarker-drug combinations
  - Classify drugs (targeted therapy, immunotherapy, chemotherapy)

Phase 6: Evidence Assessment
  - FDA-approved biomarker-drug combinations
  - Clinical trial results (PubMed), CIViC evidence, PharmGKB
  - Evidence tier classification (T1-T4)

Phase 7: Geographic & Feasibility Analysis
  - Trial site locations, enrollment status, proximity scoring

Phase 8: Alternative Options
  - Basket trials, expanded access, related studies

Phase 9: Scoring & Ranking (0-100 composite score)
  - Tier classification: Optimal (80-100) / Good (60-79) / Possible (40-59) / Exploratory (0-39)

Phase 10: Report Synthesis
  - Executive summary, ranked trial list, evidence grading, completeness checklist
```

---

## Critical Tool Parameters

### Clinical Trial Search Tools

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `search_clinical_trials` | `query_term` (REQ), `condition`, `intervention`, `pageSize` | Main search |
| `search_clinical_trials` | `action="search_studies"` (REQ), `condition`, `intervention`, `limit` | Alternative search |
| `get_clinical_trial_descriptions` | `action="get_study_details"` (REQ), `nct_id` (REQ) | Full trial details |

### Batch Trial Detail Tools (all take `nct_ids` array)

| Tool | Second Required Param | Returns |
|------|----------------------|---------|
| `get_clinical_trial_eligibility_criteria` | `eligibility_criteria="all"` | Eligibility text |
| `get_clinical_trial_locations` | `location="all"` | Site locations |
| `get_clinical_trial_conditions_and_interventions` | `condition_and_intervention="all"` | Arms/interventions |
| `get_clinical_trial_status_and_dates` | `status_and_date="all"` | Status/dates |
| `get_clinical_trial_descriptions` | `description_type="brief"` or `"full"` | Titles/summaries |
| `get_clinical_trial_outcome_measures` | `outcome_measures="all"` | Outcomes |

### Gene/Disease Resolution

| Tool | Key Parameters |
|------|---------------|
| `MyGene_query_genes` | `query`, `species` |
| `OpenTargets_get_disease_id_description_by_name` | `diseaseName` |
| `OpenTargets_get_target_id_description_by_name` | `targetName` |
| `ols_search_efo_terms` | `query`, `limit` |

### Drug Information

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `OpenTargets_get_drug_id_description_by_name` | `drugName` | Resolve drug to ChEMBL ID |
| `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | `chemblId` | Drug MoA and targets |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblId`, `size` | Drugs for a target |
| `drugbank_get_targets_by_drug_name_or_drugbank_id` | `query`, `case_sensitive`, `exact_match`, `limit` (ALL REQ) | Drug targets |
| `fda_pharmacogenomic_biomarkers` | (none) | FDA biomarker-drug list |
| `FDA_get_indications_by_drug_name` | `drug_name`, `limit` | FDA indications |

### Evidence Tools

| Tool | Key Parameters |
|------|---------------|
| `PubMed_search_articles` | `query`, `max_results` |
| `civic_get_variants_by_gene` | `gene_id` (CIViC int ID), `limit` |
| `PharmGKB_search_genes` | `query` |

### Known CIViC Gene IDs

EGFR=19, BRAF=5, ALK=1, ABL1=4, KRAS=30, TP53=45, ERBB2=20, NTRK1=197, NTRK2=560, NTRK3=561, PIK3CA=37, MET=52, ROS1=118, RET=122, BRCA1=2370, BRCA2=2371

### Critical Parameter Notes

1. **DrugBank tools**: ALL 4 parameters (`query`, `case_sensitive`, `exact_match`, `limit`) are REQUIRED
2. **`search_clinical_trials`**: `query_term` is REQUIRED even for disease-only searches
3. **`search_clinical_trials`**: `action` must be exactly `"search_studies"`
4. **CIViC `civic_search_variants`**: Does NOT filter by query - returns alphabetically
5. **CIViC `civic_get_variants_by_gene`**: Takes CIViC gene ID (integer), NOT gene symbol
6. **Batch clinical trial tools**: Accept arrays of NCT IDs, process in batches of 10

---

## Scoring Summary

**Trial Match Score (0-100)**:
- Molecular Match: 0-40 pts (exact variant=40, gene-level=30, pathway=20, none=10, excluded=0)
- Clinical Eligibility: 0-25 pts (all met=25, most=18, some=10, ineligible=0)
- Evidence Strength: 0-20 pts (FDA-approved=20, Phase III=15, Phase II=10, Phase I=5)
- Trial Phase: 0-10 pts (III=10, II=8, I/II=6, I=4)
- Geographic: 0-5 pts (local=5, same country=3, international=1)

**Recommendation Tiers**: Optimal (80-100), Good (60-79), Possible (40-59), Exploratory (0-39)

**Evidence Tiers**: T1 (FDA/guideline), T2 (Phase III), T3 (Phase I/II), T4 (computational)

For detailed scoring logic, see [SCORING_CRITERIA.md](./SCORING_CRITERIA.md).

---

## Parallelization Strategy

**Group 1** (Phase 1 - simultaneous):
- `MyGene_query_genes` per gene, `OpenTargets` disease search, `ols_search_efo_terms`, `fda_pharmacogenomic_biomarkers`

**Group 2** (Phase 2 - simultaneous):
- `search_clinical_trials` by disease, biomarker, and intervention; `search_clinical_trials` alternative

**Group 3** (Phase 3 - simultaneous):
- All batch detail tools (eligibility, interventions, locations, status, descriptions)

**Group 4** (Phases 5-6 - per drug):
- Drug resolution, MoA, FDA indications, PubMed evidence

---

## Error Handling

1. Wrap every tool call in try/except
2. Check for empty results and string error responses
3. Use fallback tools when primary fails (e.g., OLS if OpenTargets fails)
4. Document failures in completeness checklist
5. Never let one failure block the entire analysis

---

## Reference Files

| File | Contents |
|------|----------|
| [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md) | Full tool inventory with parameters and response structures |
| [MATCHING_ALGORITHMS.md](./MATCHING_ALGORITHMS.md) | Patient profile standardization, biomarker parsing, molecular eligibility matching, drug-biomarker alignment code |
| [SCORING_CRITERIA.md](./SCORING_CRITERIA.md) | Detailed scoring tables, molecular match logic, drug-biomarker alignment scoring |
| [REPORT_TEMPLATE.md](./REPORT_TEMPLATE.md) | Full markdown report template with all sections |
| [TRIAL_SEARCH_PATTERNS.md](./TRIAL_SEARCH_PATTERNS.md) | Search functions, batch retrieval, parallelization, common use patterns, edge cases |
| [EXAMPLES.md](./EXAMPLES.md) | Worked examples for different matching scenarios |
| [QUICK_START.md](./QUICK_START.md) | Quick-start guide for common workflows |


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
