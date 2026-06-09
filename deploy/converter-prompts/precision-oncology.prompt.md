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
- civic_search_evidence_items signature={'properties': {'disease': {'description': "Filter by disease name (e.g., 'leukemia', 'melanoma', 'lung cancer'). Alias: disease_name. Note: CIViC uses specific disease names (e.g., 'Lung Non-small Cell Carcinoma', not 'NSCLC'); try partial names or multiple searches if results are empty.", 'required': False, 'type': 'string'}, 'disease_name': {'description': 'Alias for disease. Filter by disease name.', 'required': False, 'type': 'string'}, 'evidence_type': {'description': 'Filter by evidence type. Values: PREDICTIVE (drug response), DIAGNOSTIC (disease diagnosis), PROGNOSTIC (patient outcomes), PREDISPOSING (disease risk), ONCOGENIC (variant pathogenicity), FUNCTIONAL (molecular function).', 'required': False, 'type': ['string', 'null']}, 'limit': {'default': 20, 'description': 'Maximum number of evidence items to return (default: 20, recommended max: 100)', 'required': False, 'type': 'integer'}, 'molecular_profile': {'description': "Filter by molecular profile name (e.g., 'BRAF V600E', 'EGFR T790M', 'KRAS G12C'). Uses substring matching â\x80\x94 'FLT3 ITD' will also match 'FLT3 ITD AND FLT3 D835Y'. For gene fusions, CIViC uses double-colon notation: 'GENE::PARTNER Fusion' (e.g., 'FGFR2::BICC1 Fusion', 'ALK::EML4 Fusion'). Use civic_search_molecular_profiles to discover exact profile names.", 'required': False, 'type': 'string'}, 'status': {'description': 'Filter by curation status. Default: ACCEPTED (peer-reviewed). Options: ACCEPTED, SUBMITTED, REJECTED, ALL (returns all statuses combined).', 'required': False, 'type': ['string', 'null']}, 'therapy': {'description': "Filter by therapy/drug name (e.g., 'imatinib', 'pembrolizumab'). Alias: therapy_name. Note: matches any evidence item where the therapy appears, including combination regimens â\x80\x94 results may include multi-drug combinations.", 'required': False, 'type': 'string'}, 'therapy_name': {'description': 'Alias for therapy. Filter by therapy/drug name.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- civic_search_variants signature={'properties': {'gene': {'description': "Gene symbol to filter variants by (e.g., 'EGFR', 'BRAF', 'KRAS'). Returns all variants for that gene.", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for gene. Gene symbol (e.g., 'TP53', 'BRCA1').", 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'description': 'Maximum number of variants to return (default: 20, recommended max: 100)', 'required': False, 'type': 'integer'}, 'query': {'description': 'Variant name to search for (e.g., "T790M", "V600E", "exon 19 deletion"). Returns name-matching variants.', 'required': False, 'type': 'string'}, 'variant_name': {'description': "Specific variant name to filter within a gene (e.g., 'L858R', 'V600E', 'T790M'). Use together with gene_name â\x80\x94 CIViC stores variants without the gene prefix (use 'L858R' not 'EGFR L858R').", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- search_clinical_trials signature={'properties': {'condition': {'description': 'Query for condition or disease using Essie expression syntax (e.g., \'lung cancer\', \'(head OR neck) AND pain AND NOT "back pain"\'). ', 'required': False, 'type': 'string'}, 'intervention': {'description': "Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').", 'required': False, 'type': 'string'}, 'keyword': {'description': 'Alias for query_term. Free-text keyword search across all trial fields (e.g., drug name, condition, investigator).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Alias for max_results: maximum number of studies to return (default 10, max 1000).', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Maximum number of studies to return (alias for pageSize, default 10, max 1000).', 'required': False, 'type': 'integer'}, 'overall_status': {'description': "Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUITING', 'NOT_YET_RECRUITING']). Valid values: RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED, WITHDRAWN.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'pageSize': {'description': 'Maximum number of studies to return per page (default 10, max 1000).', 'required': False, 'type': 'integer'}, 'pageToken': {'description': "Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.", 'required': False, 'type': 'string'}, 'query_term': {'description': "Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.", 'required': False, 'type': 'string'}, 'status': {'description': 'Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLETED".', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': False}}, 'required': [], 'type': 'object'}
- GDC_get_mutation_frequency signature={'additionalProperties': False, 'properties': {'gene': {'description': 'Gene symbol alias â\x80\x94 alternative to gene_symbol', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "Gene symbol (e.g., 'TP53', 'KRAS', 'EGFR')", 'required': True, 'type': 'string'}}, 'required': ['gene_symbol'], 'type': 'object'}
- cBioPortal_get_mutations signature={'properties': {'gene_list': {'description': "Comma-separated gene symbols (e.g., 'BRCA1,BRCA2')", 'required': True, 'type': 'string'}, 'sample_list_id': {'description': 'Optional sample list ID. If not provided, uses all samples in the study.', 'required': False, 'type': 'string'}, 'study_id': {'description': "Cancer study ID (e.g., 'brca_tcga')", 'required': True, 'type': 'string'}}, 'required': ['study_id', 'gene_list'], 'type': 'object'}
- civic_get_variant signature={'properties': {'variant_id': {'description': 'CIViC variant ID (e.g., 4170)', 'required': True, 'type': 'integer'}}, 'required': ['variant_id'], 'type': 'object'}
- civic_get_evidence_item signature={'properties': {'evidence_id': {'description': 'CIViC evidence item ID (e.g., 116)', 'required': True, 'type': 'integer'}}, 'required': ['evidence_id'], 'type': 'object'}
- MyGene_query_genes signature={'properties': {'fields': {'default': 'symbol,name,entrezgene,ensembl.gene,summary', 'description': 'Comma-separated list of fields to return. Common fields: symbol, name, entrezgene, ensembl.gene, summary, go, pathway, interpro.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query. Can be gene symbol (e.g., 'CDK2'), name ('cyclin dependent kinase'), Entrez ID ('1017'), or Ensembl ID ('ENSG00000123374'). Supports wildcards (*) and boolean operators (AND, OR, NOT).", 'required': True, 'type': 'string'}, 'size': {'default': 10, 'description': 'Maximum number of results to return (1-100).', 'required': False, 'type': 'integer'}, 'species': {'default': 'human', 'description': "Species filter. Use common name or NCBI taxonomy ID. Examples: 'human', 'mouse', '9606' (human), 'all'.", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- UniProt_search signature={'properties': {'fields': {'description': "List of field names to return (e.g., ['accession','gene_primary','length','organism_name']). When specified, returns raw API response with requested fields. Common fields: accession, id, gene_names, gene_primary, protein_name, organism_name, organism_id, length, mass, sequence, reviewed, cc_function. See UniProt API docs for full list. Default (no fields): returns formatted response with accession, id, protein_name, gene_names, organism, length.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'description': 'Maximum number of results to return (default: 25, max: 500). Accepts string or integer.', 'required': False, 'type': 'integer'}, 'max_length': {'description': 'Maximum sequence length. Auto-converts to an open-ended length range query (unbounded to max).', 'required': False, 'type': 'integer'}, 'min_length': {'description': 'Minimum sequence length. Auto-converts to an open-ended length range query (min to unbounded).', 'required': False, 'type': 'integer'}, 'organism': {'description': "Optional organism filter. Use common names ('human', 'mouse', 'rat', 'yeast') or taxonomy ID ('9606'). Automatically combined with query using AND. Will not duplicate if organism is already in query.", 'required': False, 'type': 'string'}, 'query': {'description': "Search query using UniProt syntax. Simple: 'MEIOB', 'insulin'. Field searches: 'gene:TP53', 'protein_name:insulin', 'organism_id:9606', 'reviewed:true'. Ranges: 'length:[100 TO 500]', 'mass:[20000 TO 50000]'. Wildcards: 'gene:MEIOB*'. Boolean: 'gene:TP53 AND organism_id:9606', 'tissue:brain OR tissue:liver', 'reviewed:true NOT fragment:true'. Use parentheses for grouping: '(organism_id:9606 OR organism_id:10090) AND gene:TP53'. Note: 'organism:' auto-converts to 'organism_id:'.", 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- ChEMBL_search_targets signature={'properties': {'fields': {'description': "Optional list of ChEMBL target fields to include in each returned target object (projection). ToolUniverse maps this to ChEMBL's `only` query parameter (comma-separated). Supported fields: target_chembl_id, pref_name, organism, target_type, target_components.", 'items': {'enum': ['target_chembl_id', 'pref_name', 'organism', 'target_type', 'target_components'], 'type': 'string'}, 'required': False, 'type': 'array', 'uniqueItems': True}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'organism': {'description': "Filter by organism (e.g., 'Homo sapiens')", 'required': False, 'type': 'string'}, 'pref_name__contains': {'description': 'Filter by target name (contains)', 'required': False, 'type': 'string'}, 'target_chembl_id': {'description': 'Filter by target ChEMBL ID', 'required': False, 'type': 'string'}, 'target_type': {'description': "Filter by target type (e.g., 'SINGLE PROTEIN', 'PROTEIN COMPLEX')", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- COSMIC_get_mutations_by_gene signature={'properties': {'gene': {'description': 'Gene symbol (e.g., BRAF, TP53, EGFR, KRAS, PIK3CA). Alias: gene_name also accepted.', 'required': False, 'type': 'string'}, 'gene_name': {'description': 'Alias for gene parameter. Gene symbol (e.g., FLT3, BRAF, TP53).', 'required': False, 'type': 'string'}, 'genome_build': {'default': 37, 'description': 'Genome build version: 37 (GRCh37/hg19) or 38 (GRCh38/hg38). Default: 37', 'enum': [37, 38], 'required': False, 'type': 'integer'}, 'max_results': {'default': 100, 'description': 'Maximum number of mutations to return (default: 100, max: 500)', 'maximum': 500, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'const': 'get_by_gene', 'description': 'Operation type (fixed: get_by_gene)', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- COSMIC_search_mutations signature={'properties': {'genome_build': {'default': 37, 'description': 'Genome build version: 37 (GRCh37/hg19) or 38 (GRCh38/hg38). Default: 37', 'enum': [37, 38], 'required': False, 'type': 'integer'}, 'max_results': {'default': 20, 'description': 'Maximum number of results to return (default: 20, max: 500)', 'maximum': 500, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'const': 'search', 'description': 'Operation type (fixed: search)', 'required': False, 'type': 'string'}, 'query': {'description': 'Alias for terms. Search query - gene name, mutation, or COSMIC ID.', 'required': False, 'type': 'string'}, 'terms': {'description': 'Search query - gene name (e.g., BRAF), mutation (e.g., V600E), or mutation ID (e.g., COSM476). Aliases: query or gene also accepted.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- GDC_get_ssm_by_gene signature={'properties': {'gene_symbol': {'description': "Gene symbol (e.g., 'TP53', 'EGFR', 'BRAF', 'KRAS')", 'required': True, 'type': 'string'}, 'project_id': {'description': "Optional: Filter by project (e.g., 'TCGA-BRCA', 'TCGA-LUAD')", 'required': False, 'type': 'string'}, 'size': {'default': 20, 'description': 'Number of results (1â\x80\x93100)', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}}, 'required': ['gene_symbol'], 'type': 'object'}
- GDC_get_gene_expression signature={'properties': {'gene_id': {'description': "Optional: Ensembl gene ID (e.g., 'ENSG00000141510' for TP53)", 'required': False, 'type': 'string'}, 'project_id': {'description': "GDC project (e.g., 'TCGA-BRCA', 'TCGA-LUAD', 'TCGA-GBM')", 'required': True, 'type': 'string'}, 'size': {'default': 10, 'description': 'Number of results', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}}, 'required': ['project_id'], 'type': 'object'}
- GDC_get_cnv_data signature={'properties': {'gene_symbol': {'description': 'Optional: Gene symbol to focus analysis', 'required': False, 'type': 'string'}, 'project_id': {'description': "GDC project (e.g., 'TCGA-BRCA')", 'required': True, 'type': 'string'}, 'size': {'default': 10, 'description': 'Number of results', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}}, 'required': ['project_id'], 'type': 'object'}
- GDC_get_survival signature={'properties': {'gene_symbol': {'description': "Optional: gene symbol to filter cases with mutations in this gene (e.g., 'TP53', 'KRAS')", 'required': False, 'type': 'string'}, 'project_id': {'description': "GDC project identifier (e.g., 'TCGA-BRCA', 'TCGA-LUAD', 'TCGA-GBM')", 'required': True, 'type': 'string'}}, 'required': ['project_id'], 'type': 'object'}
- GDC_get_clinical_data signature={'properties': {'disease_type': {'description': "Disease type filter (e.g., 'Ductal and Lobular Neoplasms')", 'required': False, 'type': 'string'}, 'gender': {'description': "Gender filter: 'female' or 'male'", 'enum': ['female', 'male'], 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'description': 'Pagination offset (0-based)', 'minimum': 0, 'required': False, 'type': 'integer'}, 'primary_site': {'description': "Primary anatomical site (e.g., 'Breast', 'Lung', 'Brain')", 'required': False, 'type': 'string'}, 'project_id': {'description': "GDC project identifier (e.g., 'TCGA-BRCA', 'TCGA-LUAD', 'TARGET-AML')", 'required': False, 'type': 'string'}, 'size': {'default': 10, 'description': 'Number of cases to return (1-100)', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'vital_status': {'description': "Vital status filter: 'Alive' or 'Dead'", 'enum': ['Alive', 'Dead'], 'required': False, 'type': 'string'}}, 'type': 'object'}
- Progenetix_cnv_search signature={'properties': {'end': {'description': 'End position (1-based, GRCh38). Example: 55211628 for EGFR end.', 'required': True, 'type': 'integer'}, 'filters': {'default': '', 'description': "Optional NCIt ontology code to filter by cancer type. Example: 'NCIT:C4017' for breast cancer.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of biosamples to return (default: 10).', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'reference_name': {'description': "RefSeq chromosome accession. Examples: 'refseq:NC_000007.14' (chr7/GRCh38), 'refseq:NC_000017.11' (chr17/GRCh38), 'refseq:NC_000001.11' (chr1/GRCh38).", 'required': True, 'type': 'string'}, 'start': {'description': 'Start position (1-based, GRCh38). Example: 55019017 for EGFR start.', 'required': True, 'type': 'integer'}, 'variant_type': {'default': '', 'description': "CNV type: 'DUP' for amplification/duplication, 'DEL' for deletion. Leave empty for any CNV type.", 'required': False, 'type': 'string'}}, 'required': ['reference_name', 'start', 'end'], 'type': 'object'}
- DepMap_get_gene_dependencies signature={'properties': {'gene_symbol': {'description': "Gene symbol (e.g., 'EGFR', 'KRAS', 'TP53')", 'required': True, 'type': 'string'}, 'model_id': {'description': 'Optional: Filter by specific cell line', 'required': False, 'type': 'string'}}, 'required': ['gene_symbol'], 'type': 'object'}
- PharmacoDB_get_experiments signature={'properties': {'cell_line_name': {'description': "Cell line name to filter experiments (e.g., 'MCF-7', 'A549')", 'required': False, 'type': ['string', 'null']}, 'compound_name': {'description': "Compound/drug name to filter experiments (e.g., 'Paclitaxel', 'Erlotinib')", 'required': False, 'type': ['string', 'null']}, 'dataset_name': {'description': "Dataset name to filter (e.g., 'GDSC1', 'CCLE', 'CTRPv2', 'PRISM')", 'required': False, 'type': ['string', 'null']}, 'operation': {'description': 'Operation type', 'enum': ['get_experiments'], 'required': True, 'type': 'string'}, 'per_page': {'default': 10, 'description': 'Number of experiments to return per page (default 10, max 100)', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}}, 'required': ['operation'], 'type': 'object'}
- cBioPortal_get_cancer_studies signature={'properties': {'limit': {'default': 20, 'description': 'Number of studies to return', 'required': False, 'type': 'integer'}}, 'type': 'object'}
- HPA_search_genes_by_query signature={'properties': {'search_query': {'description': "Gene name, alias, keyword, or cell line name to search for, e.g., 'EGFR', 'TP53', or 'MCF7'.", 'required': True, 'type': 'string'}}, 'required': ['search_query'], 'type': 'object'}
- DGIdb_get_drug_gene_interactions signature={'properties': {'gene': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'genes': {'description': "List of gene symbols (e.g., ['EGFR', 'BRAF']). Also accepts a single gene as string. Aliases: gene_name, gene.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_sources': {'description': "Optional filter by data sources (e.g., ['DrugBank', 'ChEMBL']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_types': {'description': "Optional filter by interaction types (e.g., ['inhibitor', 'antagonist']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- DailyMed_search_spls signature={'properties': {'drug_name': {'description': "Generic or brand name of the drug, e.g., 'TAMSULOSIN HYDROCHLORIDE'.", 'required': True, 'type': 'string'}, 'ndc': {'description': 'National Drug Code (NDC).', 'required': False, 'type': 'string'}, 'page': {'default': 1, 'description': 'Page number, starts from 1, default 1.', 'required': False, 'type': 'integer'}, 'pagesize': {'default': 100, 'description': 'Number of items per page, maximum 100, default 100.', 'required': False, 'type': 'integer'}, 'published_date_eq': {'description': "Published date == specified date, format 'YYYY-MM-DD'.", 'required': False, 'type': 'string'}, 'published_date_gte': {'description': "Published date >= specified date, format 'YYYY-MM-DD'.", 'required': False, 'type': 'string'}, 'rxcui': {'description': 'RxNorm Code (RXCUI).', 'required': False, 'type': 'string'}, 'setid': {'description': 'Set ID corresponding to the SPL.', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': ['drug_name'], 'type': 'object'}
- ChEMBL_get_drug_mechanisms signature={'properties': {'chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL ID (e.g., "CHEMBL3301622").', 'required': False, 'type': 'string'}, 'drug_chembl_id': {'description': 'ChEMBL drug/molecule ID (e.g., "CHEMBL1201581" for adalimumab, "CHEMBL4535757" for sotorasib).', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Drug name for automatic ChEMBL ID lookup (e.g., "trastuzumab", "lapatinib", "aspirin"). Case-insensitive. Triggers internal ChEMBL molecule search â\x80\x94 use drug_chembl_id if you already know the ID.', 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL molecule ID (e.g., "CHEMBL25" for aspirin).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- kegg_find_genes signature={'properties': {'keyword': {'description': 'Search keyword for gene names or descriptions', 'required': True, 'type': 'string'}, 'organism': {'default': '', 'description': "Organism code (e.g., 'hsa' for human, 'mmu' for mouse). Optional - searches all organisms if not specified", 'required': False, 'type': 'string'}}, 'required': ['keyword'], 'type': 'object'}
- kegg_get_gene_info signature={'properties': {'gene_id': {'description': "KEGG gene identifier (e.g., 'hsa:348', 'hsa:3480')", 'required': True, 'type': 'string'}}, 'required': ['gene_id'], 'type': 'object'}
- reactome_disease_target_score signature={'properties': {'efoId': {'description': "The EFO (Experimental Factor Ontology) ID of the disease, e.g., 'EFO_0000339' for chronic myelogenous leukemia", 'required': True, 'type': 'string'}, 'pageSize': {'default': 100, 'description': 'Number of results per page (default: 100, max: 100)', 'required': True, 'type': 'integer'}}, 'required': ['efoId', 'pageSize'], 'type': 'object'}
- intact_get_interaction_network signature={'properties': {'depth': {'default': 1, 'description': 'Network depth: 1 for direct interactions only, 2 for 2-hop network, etc. (default: 1)', 'maximum': 3, 'minimum': 1, 'required': False, 'type': 'integer'}, 'format': {'default': 'json', 'enum': ['json', 'xml'], 'required': False, 'type': 'string'}, 'gene_name': {'description': 'Alias for identifier: gene name.', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "Alias for identifier: gene symbol (e.g., 'BRCA1').", 'required': False, 'type': 'string'}, 'identifier': {'description': 'IntAct identifier, UniProt ID, or gene name. Aliases: uniprot_id, protein_id, gene_symbol, gene_name.', 'required': False, 'type': 'string'}, 'limit': {'default': 50, 'description': 'Maximum number of interactions to return (default: 50, max: 200). Alias: size.', 'required': False, 'type': 'integer'}, 'protein': {'description': "Alias for identifier. Gene symbol or protein name (e.g., 'TP53', 'BRCA1').", 'required': False, 'type': 'string'}, 'protein_id': {'description': 'Alias for identifier: protein identifier.', 'required': False, 'type': 'string'}, 'protein_name': {'description': 'Alias for gene_symbol/identifier. Common protein name (e.g., MDM2, TP53).', 'required': False, 'type': 'string'}, 'size': {'default': 50, 'description': 'Alias for limit. Maximum number of interactions to return (default: 50).', 'required': False, 'type': 'integer'}, 'uniprot_id': {'description': "Alias for identifier: UniProt accession (e.g., 'P04637').", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- alphafold_get_prediction signature={'properties': {'qualifier': {'description': "UniProt ACCESSION (e.g., 'P69905'). Do NOT use entry names like 'HBA_HUMAN'. Aliases: uniprot_id, uniprot_accession.", 'required': False, 'type': 'string'}, 'sequence_checksum': {'description': 'Optional CRC64 checksum of the UniProt sequence.', 'required': False, 'type': 'string'}, 'uniprot_accession': {'description': "Alias for qualifier: UniProt accession (e.g., 'P69905').", 'required': False, 'type': 'string'}, 'uniprot_id': {'description': "Alias for qualifier: UniProt accession (e.g., 'P69905').", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- get_clinical_trial_eligibility_criteria signature={'properties': {'eligibility_criteria': {'description': 'Unused filter parameter, kept for backward compatibility. Can be omitted or set to any string.', 'required': False, 'type': 'string'}, 'nct_ids': {'description': "List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).", 'items': {'type': 'string'}, 'required': True, 'type': 'array'}}, 'required': ['nct_ids'], 'type': 'object'}
- FAERS_search_adverse_event_reports signature={'properties': {'limit': {'default': 10, 'description': 'Maximum number of reports to return. Must be between 1 and 100.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'medicinalproduct': {'description': 'Drug name (required).', 'required': True, 'type': 'string'}, 'occurcountry': {'description': "Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.", 'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'seriousnessdeath': {'description': "Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit this parameter to include all reports regardless of death outcome.", 'enum': ['Yes'], 'required': False, 'type': 'string'}, 'skip': {'default': 0, 'description': 'Number of reports to skip for pagination. Must be non-negative.', 'minimum': 0, 'required': False, 'type': 'integer'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FDA_get_warnings_and_cautions_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FAERS_count_death_related_by_drug signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- CPIC_list_guidelines signature={'properties': {'drug': {'description': "Filter by drug name (e.g., 'codeine', 'warfarin', 'clopidogrel'). Case-insensitive substring match against drug names in the guideline.", 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Alias for drug.', 'required': False, 'type': 'string'}, 'gene': {'description': 'Filter by gene symbol (e.g., CYP2D6, TPMT). Returns only guidelines involving this gene.', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': 'Alias for gene. Filter by gene symbol (e.g., CYP2D6, TPMT).', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- fda_pharmacogenomic_biomarkers signature={'properties': {'biomarker': {'description': "Filter by the specific biomarker (e.g., 'CYP2D6', 'HLA-B*5701'). Case-insensitive partial match.", 'required': False, 'type': 'string'}, 'drug_name': {'description': "Filter by the name of the drug (e.g., 'Sivextro', 'Abacavir'). Case-insensitive partial match.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of results to return.', 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- BioRxiv_list_recent_preprints signature={'properties': {'cursor': {'default': 0, 'description': 'Pagination cursor (0 for first 100 results, 100 for next 100, etc.)', 'required': False, 'type': 'integer'}, 'end_date': {'description': "End date in YYYY-MM-DD format (e.g., '2024-01-03'). Date range must not exceed 60 days.", 'required': True, 'type': 'string'}, 'server': {'default': 'biorxiv', 'description': "Server: 'biorxiv' for biology preprints, 'medrxiv' for health sciences preprints", 'enum': ['biorxiv', 'medrxiv'], 'required': False, 'type': 'string'}, 'start_date': {'description': "Start date in YYYY-MM-DD format (e.g., '2024-01-01'). Date range must not exceed 60 days.", 'required': True, 'type': 'string'}}, 'required': ['start_date', 'end_date'], 'type': 'object'}
- MedRxiv_get_preprint signature={'properties': {'doi': {'description': "medRxiv DOI. Can be full DOI (e.g., '10.1101/2021.04.29.21256344') or just the numeric part after '10.1101/' (e.g., '2021.04.29.21256344'). Find DOIs using EuropePMC_search_articles, web_search, or from paper citations.", 'required': True, 'type': 'string'}, 'server': {'default': 'medrxiv', 'description': "Server to query - always 'medrxiv' for this tool.", 'enum': ['medrxiv'], 'required': False, 'type': 'string'}}, 'required': ['doi'], 'type': 'object'}
- openalex_search_works signature={'anyOf': [{'required': ['search']}, {'required': ['query']}], 'properties': {'filter': {'description': 'OpenAlex filter string (comma-separated). Example: "from_publication_date:2020-01-01,is_oa:true".', 'required': False, 'type': 'string'}, 'fulltext_terms': {'description': 'Optional list of terms to match in OpenAlex full-text index. Adds one or more fulltext.search:<term> filters and implicitly enables require_has_fulltext.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'description': 'Alias for `per_page` (OpenAlex max 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'mailto': {'description': 'Optional contact email for OpenAlex polite pool. If omitted, ToolUniverse uses a default.', 'required': False, 'type': 'string'}, 'page': {'default': 1, 'description': 'Page number (1-indexed).', 'minimum': 1, 'required': False, 'type': 'integer'}, 'per_page': {'default': 10, 'description': 'Results per page (OpenAlex max 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'query': {'description': 'Alias for `search` (recommended when you standardize on `query` across multiple paper-search tools).', 'required': False, 'type': 'string'}, 'require_has_fulltext': {'default': False, 'description': 'If true, appends OpenAlex filter has_fulltext:true (keeps only works with full-text index available).', 'required': False, 'type': 'boolean'}, 'search': {'description': 'Search query for works. Use filter + fulltext_terms/require_has_fulltext when you need full-text-index-only matching.', 'required': False, 'type': 'string'}, 'sort': {'description': 'Sort order string, e.g. "cited_by_count:desc".', 'required': False, 'type': 'string'}}, 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- OncoKB_annotate_variant
- variant_name
- variant_id
- OncoKB_get_gene_info
- HPA_get_comparative_expression_by_gene_and_cellline
- CELLxGENE_get_expression_data
- CELLxGENE_get_cell_metadata
- OpenTargets_get_associated_drugs_by_target_ensemblID
- get_diffdock_info
- ONCOKB_API_TOKEN

# TARGET SKILL TO CONVERT
---
name: tooluniverse-precision-oncology
description: Cancer treatment recommendations from molecular profile (mutations + cancer type + biomarkers) — FDA-approved + investigational therapies, resistance mechanisms, matching clinical trials, prognosis. Uses CIViC, ClinVar, OpenTargets, ClinicalTrials.gov. Use for tumor-board treatment recommendations, evidence-tiered actionability assessment, and FDA-precedent-driven therapy selection.
disable-model-invocation: true
---

# Precision Oncology Treatment Advisor

Provide actionable treatment recommendations for cancer patients based on their molecular profile using CIViC, ClinVar, OpenTargets, ClinicalTrials.gov, and structure-based analysis.

## Domain Reasoning

Treatment selection follows a strict evidence hierarchy: FDA-approved for this specific mutation in this cancer type ranks highest, followed by approval for this mutation in any cancer (tumor-agnostic), then active clinical trials, and finally off-label use. Skipping this hierarchy to recommend off-label therapies when an approved option exists is a clinical error. Always check current NCCN guidelines and recent literature, as approvals change rapidly — a drug that was investigational last year may now be first-line.

When looking up treatment for a specific mutation, search CIViC and OncoKB FIRST, not PubMed. These databases have curated evidence levels. PubMed is for when curated databases don't have the answer.

## Treatment Selection Reasoning

**Biomarker-to-drug logic** — When a biomarker is identified, the first-line targeted therapy follows established mappings. Always verify current approval status via OncoKB/CIViC, but use this as a starting framework:
- **NSCLC**: EGFR exon 19 del / L858R → osimertinib (1L); ALK fusion → alectinib/lorlatinib; ROS1 fusion → crizotinib/entrectinib; KRAS G12C → sotorasib/adagrasib; MET exon 14 skip → capmatinib/tepotinib; RET fusion → selpercatinib; BRAF V600E → dabrafenib+trametinib; NTRK fusion → larotrectinib/entrectinib (tumor-agnostic)
- **Breast**: HER2+ → trastuzumab+pertuzumab (1L), T-DXd (2L); HR+/HER2- → CDK4/6i (palbociclib/ribociclib) + AI; BRCA1/2 mut → olaparib/talazoparib; PIK3CA mut → alpelisib+fulvestrant
- **Colorectal**: BRAF V600E → encorafenib+cetuximab; MSI-H/dMMR → pembrolizumab (tumor-agnostic); KRAS/NRAS wild-type → cetuximab/panitumumab (anti-EGFR)
- **Melanoma**: BRAF V600E/K → dabrafenib+trametinib or encorafenib+binimetinib; wild-type → immunotherapy (nivolumab+ipilimumab)
- **Tumor-agnostic**: MSI-H/dMMR → pembrolizumab; NTRK fusion → larotrectinib; TMB-H (>=10 mut/Mb) → pembrolizumab; RET fusion → selpercatinib

**Resistance mechanism reasoning** — When a patient progresses on targeted therapy, distinguish primary resistance (never responded — check if the mutation was truly the driver, or if co-mutations like TP53/RB1 abrogate response) from acquired resistance (responded then progressed — on-target mutations or bypass activation). Common patterns:
- **EGFR TKIs**: 1st/2nd-gen resistance → T790M (50-60%); osimertinib resistance → C797S (10-25%), MET amp (15-20%), HER2 amp, histologic transformation (SCLC ~5%)
- **ALK TKIs**: crizotinib resistance → ALK secondary mutations (L1196M, G1269A); alectinib resistance → G1202R (solvent front); lorlatinib resistance → compound mutations
- **BRAF inhibitors**: MAPK reactivation (MEK mutations, BRAF amplification, NRAS mutations), PI3K/AKT bypass
- **Anti-HER2**: HER2 truncation (p95HER2), PIK3CA activation, HER3 upregulation
- **Immunotherapy (anti-PD1)**: B2M loss (MHC-I loss), JAK1/2 loss-of-function (IFN-gamma signaling escape), WNT/beta-catenin activation (T-cell exclusion)
For resistance workup: query `civic_search_evidence_items` with the drug name + "resistance", then `PubMed_search_articles` for recent mechanisms.

## LOOK UP DON'T GUESS

- FDA approval status for a mutation-drug pair: query `OncoKB_annotate_variant` and `civic_search_variants`; never assume approval status from memory.
- Active clinical trials: search `search_clinical_trials` with the specific condition and mutation; do not cite trials from memory.
- Resistance mechanisms for specific drugs: query `civic_search_evidence_items` and `PubMed_search_articles`; do not assume resistance pathways.
- Variant frequency in TCGA: retrieve from `GDC_get_mutation_frequency` or `cBioPortal_get_mutations`; do not estimate prevalence.

---

**KEY PRINCIPLES**:
1. **Report-first** - Create report file FIRST, update progressively
2. **Evidence-graded** - Every recommendation has evidence level
3. **Actionable output** - Prioritized treatment options, not data dumps
4. **Clinical focus** - Answer "what should we do?" not "what exists?"
5. **English-first queries** - Always use English terms in tool calls (mutations, drug names, cancer types), even if the user writes in another language. Only try original-language terms as a fallback. Respond in the user's language

---

## When to Use

- "Patient has [cancer] with [mutation] - what treatments?"
- "What are options for EGFR-mutant lung cancer?"
- "Patient failed [drug], what's next?"
- "Clinical trials for KRAS G12C?"
- "Why isn't [drug] working anymore?"

---

## Phase 0: Tool Verification

| Tool | WRONG | CORRECT |
|------|-------|---------|
| `civic_get_variant` | `variant_name` | `variant_id` (numeric, e.g., 4170) |
| `civic_get_evidence_item` | `variant_id` | `id` (numeric) |
| `OpenTargets_*` | `ensemblID` | `ensemblId` (camelCase) |
| `search_clinical_trials` | `disease` | `condition` |

---

## Workflow Overview

```
Input: Cancer type + Molecular profile (mutations, fusions, amplifications)

Phase 1: Profile Validation -> Resolve gene IDs (Ensembl, UniProt, ChEMBL)
Phase 2: Variant Interpretation -> CIViC, ClinVar, COSMIC, GDC/TCGA, DepMap, OncoKB, cBioPortal, HPA
Phase 2.5: Tumor Expression -> CELLxGENE cell-type expression, ChIPAtlas regulatory context
Phase 3: Treatment Options -> OpenTargets + DailyMed (approved), ChEMBL (off-label)
Phase 3.5: Pathway & Network -> KEGG/Reactome pathways, IntAct interactions
Phase 4: Resistance Analysis -> CIViC + PubMed + NvidiaNIM structure analysis
Phase 5: Clinical Trials -> ClinicalTrials.gov search + eligibility
Phase 5.5: Literature -> PubMed, BioRxiv/MedRxiv preprints, OpenAlex citations
Phase 6: Report Synthesis -> Executive summary + prioritized recommendations
```

---

## Key Tools by Phase

### Phase 1: Profile Validation
- `MyGene_query_genes` - Resolve gene to Ensembl ID
- `UniProt_search` - Get UniProt accession
- `ChEMBL_search_targets` - Get ChEMBL target ID

### Phase 2: Variant Interpretation
- `civic_search_variants` / `civic_get_variant` - CIViC evidence
- `COSMIC_get_mutations_by_gene` / `COSMIC_search_mutations` - Somatic mutations
- `GDC_get_mutation_frequency` / `GDC_get_ssm_by_gene` - TCGA patient data
- `GDC_get_gene_expression` / `GDC_get_cnv_data` - Expression and CNV
- `GDC_get_survival` - Kaplan-Meier survival data by project and optional gene mutation filter
- `GDC_get_clinical_data` - TCGA clinical metadata (stage, vital status, treatment, demographics)
- `Progenetix_cnv_search` - Copy number variation biosamples by genomic region and cancer type (NCIt code)
- `DepMap_get_gene_dependencies` / `PharmacoDB_get_experiments` - Target essentiality
- `OncoKB_annotate_variant` / `OncoKB_get_gene_info` - Actionability
- `cBioPortal_get_mutations` / `cBioPortal_get_cancer_studies` - Cross-study data
- `HPA_search_genes_by_query` / `HPA_get_comparative_expression_by_gene_and_cellline` - Expression

### Phase 2.5: Tumor Expression
- `CELLxGENE_get_expression_data` / `CELLxGENE_get_cell_metadata` - Cell-type expression

### Phase 3: Treatment Options
- `OpenTargets_get_associated_drugs_by_target_ensemblID` - Approved drugs (param: `ensemblId`, camelCase)
- `DGIdb_get_drug_gene_interactions` - Drug-gene interactions (param: `genes` as array, e.g., `["EGFR"]`). Comprehensive; covers inhibitors, antibodies, and investigational agents.
- `DailyMed_search_spls` - FDA label details
- `ChEMBL_get_drug_mechanisms` - Drug mechanism

### Phase 3.5: Pathway & Network
- `kegg_find_genes` / `kegg_get_gene_info` - KEGG pathways
- `reactome_disease_target_score` - Reactome disease relevance
- `intact_get_interaction_network` - Protein interactions

### Phase 4: Resistance Analysis
- `civic_search_evidence_items` - Search by known resistance mutations individually (e.g., `molecular_profile="EGFR C797S"`, `molecular_profile="MET Amplification"`). The `significance` field in results indicates Resistance/Sensitivity — filter on it after retrieval.
- `PubMed_search_articles` - Resistance literature (e.g., "osimertinib resistance C797S combination therapy")
- `alphafold_get_prediction` / `get_diffdock_info` - Structure-based analysis (AlphaFold for structure, DiffDock for docking)

### Phase 5: Clinical Trials
- `search_clinical_trials` - Find trials (param: `condition`, NOT `disease`)
- `get_clinical_trial_eligibility_criteria` - Eligibility details

### Phase 5.5: Safety & Pharmacogenomics (MANDATORY — do NOT skip)

**You MUST call FAERS for the leading approved drug before finalizing the report.** A clinical brief without real-world adverse-event data is incomplete.

- `FAERS_search_adverse_event_reports` — **REQUIRED**: call with `medicinalproduct="<drug_name>"` for at least the top 1-2 approved drugs. Report top 10 serious AEs + death count.
- `FDA_get_warnings_and_cautions_by_drug_name` — **REQUIRED**: boxed warnings + key precautions.
- `FAERS_count_death_related_by_drug` - Mortality signal for a drug
- `CPIC_list_guidelines` - Check for relevant PGx guidelines (e.g., DPYD for fluoropyrimidines in chemo regimens, UGT1A1 for irinotecan). No CPIC guidelines exist for EGFR TKIs.
- `fda_pharmacogenomic_biomarkers` - FDA-labeled PGx biomarkers for the drug

> **OncoKB demo mode**: Without `ONCOKB_API_TOKEN` env var, OncoKB only covers BRAF, TP53, ROS1. For other genes (EGFR, KRAS, ALK, etc.), set the API key or use CIViC as the primary evidence source.

### Phase 6: Literature
- `PubMed_search_articles` - Published evidence (use `limit`, `mindate`, `maxdate` for date filtering)
- `BioRxiv_list_recent_preprints` / `MedRxiv_get_preprint` - Preprints (flag as NOT peer-reviewed)
- `openalex_search_works` - Citation analysis

---

## Cross-Skill References

For CYP interaction with cancer drugs, run: `python3 skills/tooluniverse-drug-drug-interaction/scripts/pharmacology_ref.py --type cyp_substrate --drug drugname`

---

## References

- [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) - Complete tool documentation with parameters and examples
- [API_USAGE_PATTERNS.md](API_USAGE_PATTERNS.md) - Detailed code examples for each phase
- [TREATMENT_ALGORITHMS.md](TREATMENT_ALGORITHMS.md) - Evidence grading, treatment prioritization, cancer type mappings, DepMap interpretation
- [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) - Report template with output tables
- [EXAMPLES.md](EXAMPLES.md) - Worked examples (EGFR NSCLC, T790M resistance, KRAS G12C, no actionable mutations)
- [CHECKLIST.md](CHECKLIST.md) - Quality and completeness checklist


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
