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
- OpenTargets_get_drug_chembId_by_generic_name signature={'properties': {'drugName': {'description': 'The generic name of the drug for which the ID is required.', 'required': True, 'type': 'string'}}, 'required': ['drugName'], 'type': 'object'}
- ChEMBL_get_drug signature={'properties': {'drug_chembl_id': {'description': "ChEMBL drug ID, e.g., 'CHEMBL1201581'", 'required': True, 'type': 'string'}, 'format': {'default': 'json', 'enum': ['json', 'xml', 'yaml'], 'required': False, 'type': 'string'}}, 'required': ['drug_chembl_id'], 'type': 'object'}
- PubChem_get_CID_by_compound_name signature={'properties': {'compound_name': {'description': 'Alias for name. The compound name to look up.', 'required': False, 'type': 'string'}, 'name': {'description': 'Chemical compound name (e.g., "Aspirin", "Acetaminophen") or IUPAC name. Do not use disease names or medical conditions.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_drug_mechanisms signature={'properties': {'chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL ID (e.g., "CHEMBL3301622").', 'required': False, 'type': 'string'}, 'drug_chembl_id': {'description': 'ChEMBL drug/molecule ID (e.g., "CHEMBL1201581" for adalimumab, "CHEMBL4535757" for sotorasib).', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Drug name for automatic ChEMBL ID lookup (e.g., "trastuzumab", "lapatinib", "aspirin"). Case-insensitive. Triggers internal ChEMBL molecule search â\x80\x94 use drug_chembl_id if you already know the ID.', 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL molecule ID (e.g., "CHEMBL25" for aspirin).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- DGIdb_get_drug_gene_interactions signature={'properties': {'gene': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'genes': {'description': "List of gene symbols (e.g., ['EGFR', 'BRAF']). Also accepts a single gene as string. Aliases: gene_name, gene.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_sources': {'description': "Optional filter by data sources (e.g., ['DrugBank', 'ChEMBL']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_types': {'description': "Optional filter by interaction types (e.g., ['inhibitor', 'antagonist']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- OpenTargets_get_drug_indications_by_chemblId signature={'properties': {'chemblId': {'description': 'The chemblId of the drug for which to retrieve treatable phenotypes information.', 'required': True, 'type': 'string'}}, 'required': ['chemblId'], 'type': 'object'}
- search_clinical_trials signature={'properties': {'condition': {'description': 'Query for condition or disease using Essie expression syntax (e.g., \'lung cancer\', \'(head OR neck) AND pain AND NOT "back pain"\'). ', 'required': False, 'type': 'string'}, 'intervention': {'description': "Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').", 'required': False, 'type': 'string'}, 'keyword': {'description': 'Alias for query_term. Free-text keyword search across all trial fields (e.g., drug name, condition, investigator).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Alias for max_results: maximum number of studies to return (default 10, max 1000).', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Maximum number of studies to return (alias for pageSize, default 10, max 1000).', 'required': False, 'type': 'integer'}, 'overall_status': {'description': "Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUITING', 'NOT_YET_RECRUITING']). Valid values: RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED, WITHDRAWN.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'pageSize': {'description': 'Maximum number of studies to return per page (default 10, max 1000).', 'required': False, 'type': 'integer'}, 'pageToken': {'description': "Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.", 'required': False, 'type': 'string'}, 'query_term': {'description': "Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.", 'required': False, 'type': 'string'}, 'status': {'description': 'Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLETED".', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': False}}, 'required': [], 'type': 'object'}
- PubMed_get_cited_by signature={'properties': {'limit': {'default': 20, 'description': 'Maximum number of citing articles to return (default: 20, max: 100).', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'pmid': {'description': "PubMed ID (PMID) for which to find citing articles (e.g., '12345678'). Find PMIDs using PubMed_search_articles.", 'required': True, 'type': 'string'}}, 'required': ['pmid'], 'type': 'object'}
- PubMed_get_related signature={'properties': {'limit': {'default': 20, 'description': 'Maximum number of related articles to return (default: 20, max: 100).', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'pmid': {'description': "PubMed ID (PMID) for which to find related articles (e.g., '20210808', '19879512'). Find PMIDs using PubMed_search_articles.", 'required': True, 'type': 'string'}}, 'required': ['pmid'], 'type': 'object'}
- SemanticScholar_get_recommendations signature={'properties': {'fields': {'default': 'title,year,citationCount,abstract,authors,externalIds', 'description': 'Comma-separated fields for recommended papers: title,year,citationCount,abstract,authors,externalIds', 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Number of recommendations to return (default 10, max 500)', 'required': False, 'type': 'integer'}, 'paper_id': {'description': "Semantic Scholar paper ID (40-char hex, e.g., '68d962effe5520777791bd6ec8ffa4b963ba4f38'). Get this from SemanticScholar_get_paper or SemanticScholar_search_papers.", 'required': True, 'type': 'string'}}, 'required': ['paper_id'], 'type': 'object'}
- OpenCitations_get_citations signature={'properties': {'doi': {'description': "DOI of the paper to find citations for. Do not include 'https://doi.org/' prefix. Examples: '10.1038/nature12373', '10.1002/jcc.21224'", 'required': True, 'type': 'string'}, 'limit': {'default': 100, 'description': 'Maximum number of citations to return. Highly-cited papers can have 10,000+ citations; use this to avoid oversized responses.', 'required': False, 'type': ['integer', 'null']}}, 'required': ['doi'], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- PMC_search_papers signature={'properties': {'article_type': {'description': "Article type filter (e.g., 'research-article', 'review', 'case-report'). Optional parameter to limit search to specific article types.", 'required': False, 'type': 'string'}, 'date_from': {'description': 'Start date for publication date filter (YYYY/MM/DD format). Optional parameter to limit search to papers published from this date onwards.', 'required': False, 'type': 'string'}, 'date_to': {'description': 'End date for publication date filter (YYYY/MM/DD format). Optional parameter to limit search to papers published up to this date.', 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, attempts to enrich results with an abstract (best-effort) by fetching PubMed abstracts for items that have a PMID.', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Maximum number of papers to return. This sets the maximum number of papers retrieved from PMC.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for PMC papers. Use keywords separated by spaces to refine your search.', 'required': True, 'type': 'string'}, 'retmax': {'description': 'Alias for limit (NCBI eutils naming). If both retmax and limit are provided, limit is used.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}}, 'required': ['query'], 'type': 'object'}
- EuropePMC_search_articles signature={'properties': {'enrich_missing_abstract': {'default': False, 'description': 'If true, best-effort fills missing abstracts by fetching Europe PMC fullTextXML (bounded to a few results).', 'required': False, 'type': 'boolean'}, 'extract_terms_from_fulltext': {'description': "Optional list of terms to extract from full text (open access only). When provided, automatically fetches fullTextXML for open-access articles and returns snippets around these terms. Terms are processed in batches of 5 internally, so any number of terms is accepted. Bounded to first 3 OA articles to avoid latency. Returns snippets in a 'fulltext_snippets' field for each article.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'fulltext_terms': {'description': 'Optional list of terms that must occur in the indexed full text (Europe PMC BODY field). When provided, the tool adds a BODY:"..." clause and automatically enables `require_has_ft`.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'default': 5, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from Europe PMC.', 'required': False, 'type': 'integer'}, 'page_size': {'description': 'Alias for limit â\x80\x94 number of results to return', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Europe PMC. Supports Lucene-like fielded syntax (e.g., BODY:"term", INTRO:"term", METHODS:"term").', 'required': True, 'type': 'string'}, 'require_has_ft': {'default': False, 'description': 'If true, appends `HAS_FT:Y` to the query to restrict results to records where Europe PMC has full text indexed. This is NOT the same as having a link to free full text elsewhere (e.g., PMC) and is often the key reason body-only keywords cannot be found via Europe PMC search.', 'required': False, 'type': 'boolean'}}, 'required': ['query'], 'type': 'object'}
- PubTator3_LiteratureSearch signature={'properties': {'limit': {'description': 'Maximum number of results to return (applied client-side). The PubTator3 API returns 10 results per page; this parameter truncates the results to the requested count.', 'required': False, 'type': 'integer'}, 'page': {'default': 0, 'description': 'Zero-based results page (optional; default = 0).', 'required': False, 'type': 'integer'}, 'page_size': {'default': 10, 'description': 'How many PMIDs to return per page (optional; default = 10; note: the PubTator3 API always returns 10 per page regardless of this value).', 'required': False, 'type': 'integer'}, 'query': {'description': 'What you want to search for. This can be plain keywords, a single PubTator ID, or the special relation syntax shown above.', 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- openalex_literature_search signature={'anyOf': [{'required': ['search_keywords']}, {'required': ['query']}], 'properties': {'fulltext_terms': {'description': 'Optional list of terms that must occur in OpenAlex full-text index (adds fulltext.search:<term> filters and implicitly enables require_has_fulltext).', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'description': 'Alias for `max_results` (OpenAlex max 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'default': 10, 'description': 'Maximum number of papers to retrieve (default: 10, maximum: 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'open_access': {'description': 'Filter for open access papers only. Set to true for open access papers, false for non-open access, or omit for all papers.', 'required': False, 'type': 'boolean'}, 'query': {'description': 'Alias for `search_keywords` (recommended when you standardize on `query` across multiple paper-search tools).', 'required': False, 'type': 'string'}, 'require_has_fulltext': {'default': False, 'description': 'If true, filters to works where OpenAlex indicates a full-text index is available (has_fulltext:true).', 'required': False, 'type': 'boolean'}, 'search_keywords': {'description': 'Keywords to search for in paper titles/abstracts/etc. For full-text-index-only matching, also use require_has_fulltext/fulltext_terms.', 'required': False, 'type': 'string'}, 'year_from': {'description': 'Start year for publication date filter (e.g., 2020). Optional parameter to limit search to papers published from this year onwards.', 'required': False, 'type': 'integer'}, 'year_to': {'description': 'End year for publication date filter (e.g., 2023). Optional parameter to limit search to papers published up to this year.', 'required': False, 'type': 'integer'}}, 'type': 'object'}
- ArXiv_search_papers signature={'properties': {'date_from': {'description': 'Filter results from this date (format: YYYY-MM-DD). Uses submittedDate range.', 'required': False, 'type': 'string'}, 'date_to': {'description': 'Filter results up to this date (format: YYYY-MM-DD). Uses submittedDate range.', 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Number of papers to return. This sets the maximum number of papers retrieved from arXiv.', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for arXiv papers. Use keywords separated by spaces to refine your search.', 'required': True, 'type': 'string'}, 'sort_by': {'default': 'relevance', 'description': "Sort order for results. Options: 'relevance', 'lastUpdatedDate', 'submittedDate'", 'required': False, 'type': 'string'}, 'sort_order': {'default': 'descending', 'description': "Sort direction. Options: 'ascending', 'descending'", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- DBLP_search_publications signature={'properties': {'limit': {'default': 10, 'description': 'Number of publications to return. This sets the maximum number of publications retrieved from DBLP.', 'required': True, 'type': 'integer'}, 'query': {'description': 'Search query for DBLP publications. Use keywords separated by spaces to refine your search.', 'required': True, 'type': 'string'}}, 'required': ['query', 'limit'], 'type': 'object'}
- SemanticScholar_search_papers signature={'properties': {'include_abstract': {'default': False, 'description': 'If true, best-effort fetches missing abstracts via the paper detail endpoint (only when abstract is missing in search results).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 5, 'description': 'Maximum number of papers to return from Semantic Scholar.', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Semantic Scholar. Use keywords separated by spaces to refine the search.', 'required': True, 'type': 'string'}, 'sort': {'description': "Sort results. Options: 'citationCount:desc', 'citationCount:asc', 'publicationDate:desc', 'publicationDate:asc'.", 'required': False, 'type': 'string'}, 'year': {'description': "Filter results by publication year. Use a single year (e.g., '2024') or a range (e.g., '2020-2024').", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- Crossref_search_works signature={'properties': {'filter': {'description': "Optional filter string for Crossref API. Examples: 'type:journal-article' (only journal articles), 'from-pub-date:2020-01-01' (published after date), 'has-abstract:true' (only with abstracts). Multiple filters comma-separated.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from Crossref. Max 100 per request.', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Crossref works. Use keywords separated by spaces to refine your search across titles, abstracts, authors, and other bibliographic fields.', 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- CORE_search_papers signature={'anyOf': [{'required': ['query']}, {'required': ['search']}, {'required': ['q']}], 'properties': {'language': {'description': "Language filter for papers (e.g., 'en', 'es', 'fr'). Optional parameter to limit search to papers in specific language.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of papers to return. This sets the maximum number of papers retrieved from CORE.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for `limit`.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'page_size': {'description': 'Alias for `limit`.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'q': {'description': 'Alias for `query`.', 'required': False, 'type': 'string'}, 'query': {'description': 'Search query for CORE papers. Use keywords separated by spaces to refine your search.', 'required': False, 'type': 'string'}, 'search': {'description': 'Alias for `query`.', 'required': False, 'type': 'string'}, 'year_from': {'description': 'Start year for publication date filter (e.g., 2020). Optional parameter to limit search to papers published from this year onwards.', 'required': False, 'type': 'integer'}, 'year_to': {'description': 'End year for publication date filter (e.g., 2024). Optional parameter to limit search to papers published up to this year.', 'required': False, 'type': 'integer'}}, 'type': 'object'}
- DOAJ_search_articles signature={'properties': {'max_results': {'default': 10, 'description': 'Maximum number of articles to return. Default is 10, maximum is 100.', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for DOAJ articles. Supports Lucene syntax for advanced queries.', 'required': True, 'type': 'string'}, 'type': {'default': 'articles', 'description': "Type of search: 'articles' or 'journals'. Default is 'articles'.", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- BioRxiv_get_preprint signature={'properties': {'doi': {'description': "bioRxiv or medRxiv DOI. Can be full DOI (e.g., '10.1101/2023.12.01.569554') or just the numeric part after '10.1101/' (e.g., '2023.12.01.569554'). Find DOIs using EuropePMC_search_articles, web_search, or from paper citations.", 'required': True, 'type': 'string'}, 'server': {'default': 'biorxiv', 'description': "Server to query: 'biorxiv' for bioRxiv preprints or 'medrxiv' for medRxiv preprints. Default is 'biorxiv'.", 'enum': ['biorxiv', 'medrxiv'], 'required': False, 'type': 'string'}}, 'required': ['doi'], 'type': 'object'}
- MedRxiv_get_preprint signature={'properties': {'doi': {'description': "medRxiv DOI. Can be full DOI (e.g., '10.1101/2021.04.29.21256344') or just the numeric part after '10.1101/' (e.g., '2021.04.29.21256344'). Find DOIs using EuropePMC_search_articles, web_search, or from paper citations.", 'required': True, 'type': 'string'}, 'server': {'default': 'medrxiv', 'description': "Server to query - always 'medrxiv' for this tool.", 'enum': ['medrxiv'], 'required': False, 'type': 'string'}}, 'required': ['doi'], 'type': 'object'}
- OSF_search_preprints signature={'properties': {'max_results': {'default': 10, 'description': 'Maximum number of results to return. Default is 10, maximum is 100.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'provider': {'description': "Optional preprint provider filter (e.g., 'osf', 'psyarxiv', 'socarxiv'). If not specified, searches all providers.", 'required': False, 'type': 'string'}, 'query': {'description': 'Search query for OSF preprints. Use keywords to search across titles and abstracts.', 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- advanced_literature_search_agent signature={'properties': {'query': {'description': 'Research query or topic to search in academic literature. The agent will automatically determine search strategy, database selection, filters, and result limits based on the query content and research domain.', 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- iCite_search_publications signature={'properties': {'limit': {'description': 'Maximum number of results (default 10, max 1000)', 'required': False, 'type': ['integer', 'null']}, 'offset': {'description': 'Offset for pagination (default 0)', 'required': False, 'type': ['integer', 'null']}, 'query': {'description': "Search query for PubMed (e.g., 'BRCA1 cancer', 'COVID-19 vaccine efficacy', 'CRISPR gene editing')", 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- iCite_get_publications signature={'properties': {'pmids': {'description': "Comma-separated PubMed IDs to look up (e.g., '24453150,24453148,31510562'). Maximum ~100 PMIDs per request.", 'required': True, 'type': 'string'}}, 'required': ['pmids'], 'type': 'object'}
- scite_get_tallies signature={'properties': {'doi': {'description': "DOI of the paper to get citation tallies for (e.g., '10.1038/nature12303', '10.1016/j.cell.2020.02.058'). Include the full DOI without URL prefix.", 'required': True, 'type': 'string'}}, 'required': ['doi'], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- drugbank_get_drug_basic_info_by_drug_name_or_id
- OpenTargets_get_associated_targets_by_drug_chemblId
- OpenTargets_get_drug_adverse_events_by_chemblId

# TARGET SKILL TO CONVERT
---
name: tooluniverse-literature-deep-research
description: Deep literature review — PubMed, EuropePMC, bioRxiv preprints, citation networks, evidence synthesis. Disambiguates queries, runs collision-aware searches, grades evidence T1-T4, and produces structured reports. Use for systematic literature review, meta-analysis evidence collection, and detailed answer-with-citations workflows.
disable-model-invocation: true
---

# Literature Deep Research

Systematic literature research: disambiguate, search with collision-aware queries, grade evidence, produce structured reports.

**KEY PRINCIPLES**: (1) Disambiguate first (2) Right-size deliverable (3) Grade every claim T1-T4 (4) All sections mandatory even if "limited evidence" (5) Source attribution for every claim (6) English-first queries, respond in user's language (7) Report = deliverable, not search log

---

## LOOK UP, DON'T GUESS

Search PubMed/EuropePMC FIRST before reasoning. A published paper beats memory.

**Factoid search strategy:**
1. Extract KEY TERMS (most specific nouns/verbs)
2. `EuropePMC_search_articles(query="term1 term2 term3", limit=5)`
3. No results -> BROADEN (remove most restrictive term)
4. Too many -> NARROW (add specific terms)
5. Answer usually in abstract of top results
6. Failed query -> try DIFFERENT TERMS/synonyms, don't repeat

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Workflow

```
Phase 0: Clarify + Mode Select → Phase 1: Disambiguate + Profile → Phase 2: Literature Search → Phase 3: Report
```

---

## Phase 0: Mode Selection

| Mode | When | Deliverable |
|------|------|-------------|
| **Factoid** | Single concrete question | 1-page fact-check report + bibliography |
| **Mini-review** | Narrow topic | 1-3 page narrative |
| **Full Deep-Research** | Comprehensive overview | 15-section report + bibliography |

### Factoid Mode (Fast Path)
```markdown
# [TOPIC]: Fact-check Report
## Question / ## Answer (with evidence rating) / ## Source(s) / ## Verification Notes / ## Limitations
```

### Domain Detection

| Pattern | Domain | Action |
|---------|--------|--------|
| Gene/protein symbol | Biological target | Full bio disambiguation |
| Drug name | Drug | Drug disambiguation (1.5) |
| Disease name | Disease | Disease disambiguation (1.6) |
| CS/ML topic | General academic | Skip bio tools, literature-only |
| Cross-domain | Interdisciplinary | Resolve each entity in its domain |

### Cross-Skill Delegation
- Gene/protein deep-dive: `tooluniverse-target-research`
- Drug profile: `tooluniverse-drug-research`
- Disease profile: `tooluniverse-disease-research`

Use this skill for **literature synthesis**. Use specialized skills for **entity profiling**. For max depth, run both.

---

## Phase 1: Subject Disambiguation + Profile

### 1.1 Biological Target Resolution
```
UniProt_search → UniProt_get_entry_by_accession → UniProt_id_mapping
ensembl_lookup_gene → MyGene_get_gene_annotation
```

### 1.2 Naming Collision Detection
Check first 20 results. If >20% off-topic, build negative filter: `NOT [collision1] NOT [collision2]`.
Gene family: `"ADAR" NOT "ADAR2" NOT "ADARB1"`. Cross-domain: add context terms.

### 1.3 Baseline Profile (Bio Targets)
```
InterPro_get_protein_domains, UniProt_get_ptm_processing_by_accession, HPA_get_subcellular_location,
GTEx_get_median_gene_expression, GO_get_annotations_for_gene, Reactome_map_uniprot_to_pathways,
STRING_get_protein_interactions, intact_get_interactions, OpenTargets_get_target_tractability_by_ensemblID
```
GPCR targets: delegate to `tooluniverse-target-research`.

### 1.5 Drug Disambiguation
**Identity**: `OpenTargets_get_drug_chembId_by_generic_name`, `ChEMBL_get_drug`, `PubChem_get_CID_by_compound_name`, `drugbank_get_drug_basic_info_by_drug_name_or_id`
**Targets**: `ChEMBL_get_drug_mechanisms`, `OpenTargets_get_associated_targets_by_drug_chemblId`, `DGIdb_get_drug_gene_interactions`
**Safety**: `OpenTargets_get_drug_adverse_events_by_chemblId`, `OpenTargets_get_drug_indications_by_chemblId`, `search_clinical_trials`

### 1.6 Disease Disambiguation
```
OpenTargets disease search → EFO/MONDO IDs
DisGeNET_get_disease_genes, DisGeNET_search_disease
CTD_get_disease_chemicals
```

### 1.7 Compound Queries (e.g., "metformin in breast cancer")
Resolve both entities, then cross-reference via CTD_get_chemical_gene_interactions, CTD_get_chemical_diseases, OpenTargets drug-target/drug-disease tools. Intersect shared targets/pathways.

### 1.8 General Academic / 1.9 Interdisciplinary
Non-bio: skip bio tools, use ArXiv/DBLP/OSF. Cross-domain: resolve bio entities with 1.1-1.3, search CS/general in parallel, merge and cross-reference.

---

## Phase 2: Literature Search

**Methodology stays internal. Report shows findings, not process.**

### 2.1 Query Strategy
**Step 1: Seeds** (15-30 core papers): domain-specific title searches with date/sort filters.
**Step 2: Citation expansion**: `PubMed_get_cited_by`, `EuropePMC_get_citations/references`, `PubMed_get_related`, `SemanticScholar_get_recommendations`, `OpenCitations_get_citations`
**Step 3: Collision-filtered broader queries**: `"[TERM]" AND ([context]) NOT [collision]`

### 2.2 Literature Tools

**Biomedical**: `PubMed_search_articles`, `PMC_search_papers`, `EuropePMC_search_articles`, `PubTator3_LiteratureSearch`
**Biology (ecology/evolution/plant)**: **EuropePMC as PRIMARY** (PubMed returns 0-1 for non-clinical biology). Also `openalex_literature_search`.
**CS/ML**: `ArXiv_search_papers`, `DBLP_search_publications`, `SemanticScholar_search_papers`
**General**: `openalex_literature_search`, `Crossref_search_works`, `CORE_search_papers`, `DOAJ_search_articles`
**Preprints**: `BioRxiv_get_preprint`, `MedRxiv_get_preprint`, `OSF_search_preprints`, `EuropePMC_search_articles(source='PPR')`
**Multi-source**: `advanced_literature_search_agent` (12+ DBs; needs Azure key -- fallback: query PubMed+ArXiv+SemanticScholar+OpenAlex individually)
**Citation impact**: `iCite_search_publications` (RCR/APT), `iCite_get_publications` (by PMID), `scite_get_tallies` (support/contradict). PubMed-only; for CS use SemanticScholar.

### 2.3-2.4 Full-Text & PubMed Zero-Result Fallback

Full-text: see `FULLTEXT_STRATEGY.md` for three-tier strategy.

**CRITICAL**: PubMed returns 0 for ~30% of valid queries. **Always retry with EuropePMC** when PubMed returns empty. This is not optional.

### 2.5 Tool Failure / OA Handling
Retry once -> fallback tool. Key fallbacks: PubMed_get_cited_by -> EuropePMC_get_citations -> OpenCitations. OA: Unpaywall if configured, else Europe PMC/PMC/OpenAlex flags.

---

## Phase 3: Evidence Grading

| Tier | Label | Bio Example | CS/ML Example |
|------|-------|-------------|---------------|
| **T1** | Mechanistic | CRISPR KO + rescue, RCT | Formal proof, controlled ablation |
| **T2** | Functional | siRNA knockdown phenotype | Benchmark with baselines |
| **T3** | Association | GWAS, screen hit | Observational, case study |
| **T4** | Mention | Review article | Survey, workshop abstract |

Inline: `Target X regulates Y [T1: PMID:12345678]`. Per theme: summarize evidence distribution.

---

## Report Output

| File | Mode |
|------|------|
| `[topic]_report.md` | Full |
| `[topic]_factcheck_report.md` | Factoid |
| `[topic]_bibliography.json` + `.csv` | All |

**Progressive update**: create report with all section headers immediately. Fill after each phase. Write Executive Summary LAST.

Use 15-section template from `REPORT_TEMPLATE.md`. Domain adaptations: bio (architecture/expression/GO/disease), drug (properties/MOA/PK/safety), disease (epi/patho/genes/treatments), general (history/theories/evidence/applications).

---

## Communication

Brief progress updates only: "Resolving identifiers...", "Building paper set...", "Grading evidence..."
Do NOT expose: raw tool outputs, dedup counts, search round details.

---

## References

- `TOOL_NAMES_REFERENCE.md` -- 123 tools with parameters
- `REPORT_TEMPLATE.md` -- template, domain adaptations, bibliography, completeness checklist
- `FULLTEXT_STRATEGY.md` -- three-tier full-text verification
- `WORKFLOW.md` -- compact cheat-sheet
- `EXAMPLES.md` -- worked examples


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
