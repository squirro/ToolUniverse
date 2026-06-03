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
- OpenTargets_target_disease_evidence signature={'properties': {'disease_name': {'description': "Disease or phenotype name (e.g., 'Crohn disease', 'breast carcinoma'). Auto-resolved to efoId.", 'required': False, 'type': 'string'}, 'efoId': {'description': 'EFO/MONDO disease ID (e.g., EFO_0000384). Alternative to disease_name.', 'required': False, 'type': 'string'}, 'ensemblId': {'description': 'Ensembl gene ID (e.g., ENSG00000141510). Alternative to gene_symbol.', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "HGNC gene symbol (e.g., 'TP53', 'BRCA1'). Auto-resolved to ensemblId.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- MyGene_query_genes signature={'properties': {'fields': {'default': 'symbol,name,entrezgene,ensembl.gene,summary', 'description': 'Comma-separated list of fields to return. Common fields: symbol, name, entrezgene, ensembl.gene, summary, go, pathway, interpro.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query. Can be gene symbol (e.g., 'CDK2'), name ('cyclin dependent kinase'), Entrez ID ('1017'), or Ensembl ID ('ENSG00000123374'). Supports wildcards (*) and boolean operators (AND, OR, NOT).", 'required': True, 'type': 'string'}, 'size': {'default': 10, 'description': 'Maximum number of results to return (1-100).', 'required': False, 'type': 'integer'}, 'species': {'default': 'human', 'description': "Species filter. Use common name or NCBI taxonomy ID. Examples: 'human', 'mouse', '9606' (human), 'all'.", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- search_clinical_trials signature={'properties': {'condition': {'description': 'Query for condition or disease using Essie expression syntax (e.g., \'lung cancer\', \'(head OR neck) AND pain AND NOT "back pain"\'). ', 'required': False, 'type': 'string'}, 'intervention': {'description': "Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').", 'required': False, 'type': 'string'}, 'keyword': {'description': 'Alias for query_term. Free-text keyword search across all trial fields (e.g., drug name, condition, investigator).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Alias for max_results: maximum number of studies to return (default 10, max 1000).', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Maximum number of studies to return (alias for pageSize, default 10, max 1000).', 'required': False, 'type': 'integer'}, 'overall_status': {'description': "Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUITING', 'NOT_YET_RECRUITING']). Valid values: RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED, WITHDRAWN.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'pageSize': {'description': 'Maximum number of studies to return per page (default 10, max 1000).', 'required': False, 'type': 'integer'}, 'pageToken': {'description': "Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.", 'required': False, 'type': 'string'}, 'query_term': {'description': "Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.", 'required': False, 'type': 'string'}, 'status': {'description': 'Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLETED".', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': False}}, 'required': [], 'type': 'object'}
- civic_get_variants_by_gene signature={'properties': {'gene': {'description': "Alias for gene_name. Gene symbol (e.g., 'EGFR', 'KRAS').", 'required': False, 'type': 'string'}, 'gene_id': {'description': 'CIViC gene ID (e.g., 19 for EGFR, 12 for BRAF). Find gene IDs using civic_search_genes.', 'required': False, 'type': 'integer'}, 'gene_name': {'description': "Gene symbol (e.g., 'EGFR', 'BRAF', 'TP53'). Will be looked up automatically. Aliases: gene, gene_symbol, query.", 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "Alias for gene_name. Standard gene symbol (e.g., 'KRAS', 'BRCA1', 'EGFR').", 'required': False, 'type': 'string'}, 'limit': {'default': 500, 'description': "Maximum number of variants to return (default: 500, uses cursor pagination to bypass CIViC's 100/page server cap)", 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_drug_mechanisms signature={'properties': {'chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL ID (e.g., "CHEMBL3301622").', 'required': False, 'type': 'string'}, 'drug_chembl_id': {'description': 'ChEMBL drug/molecule ID (e.g., "CHEMBL1201581" for adalimumab, "CHEMBL4535757" for sotorasib).', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Drug name for automatic ChEMBL ID lookup (e.g., "trastuzumab", "lapatinib", "aspirin"). Case-insensitive. Triggers internal ChEMBL molecule search â\x80\x94 use drug_chembl_id if you already know the ID.', 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL molecule ID (e.g., "CHEMBL25" for aspirin).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- ensembl_lookup_gene signature={'properties': {'gene_id': {'description': "Ensembl gene ID or symbol (e.g., 'ENSG00000139618' or 'BRCA1'). If using a stable ID, the tool will automatically route to /lookup/id endpoint.", 'required': True, 'type': 'string'}, 'species': {'description': "Species name required for gene symbols (default 'homo_sapiens'). Examples: 'homo_sapiens', 'mus_musculus', 'rattus_norvegicus'", 'required': False, 'type': 'string'}}, 'required': ['gene_id'], 'type': 'object'}
- civic_search_genes signature={'properties': {'gene_name': {'description': "Gene symbol to search for. Alias for 'name'.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of genes to return (default: 10, recommended max: 100)', 'required': False, 'type': 'integer'}, 'name': {'description': 'Gene symbol to search for (e.g., "EGFR", "BRAF", "BRCA1"). Alias: use \'query\' or \'gene_name\' instead.', 'required': False, 'type': 'string'}, 'query': {'description': 'Gene symbol to search for (e.g., "FLT3", "KRAS", "TP53"). Alias for \'name\'.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- cBioPortal_get_mutations signature={'properties': {'gene_list': {'description': "Comma-separated gene symbols (e.g., 'BRCA1,BRCA2')", 'required': True, 'type': 'string'}, 'sample_list_id': {'description': 'Optional sample list ID. If not provided, uses all samples in the study.', 'required': False, 'type': 'string'}, 'study_id': {'description': "Cancer study ID (e.g., 'brca_tcga')", 'required': True, 'type': 'string'}}, 'required': ['study_id', 'gene_list'], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- UniProt_search signature={'properties': {'fields': {'description': "List of field names to return (e.g., ['accession','gene_primary','length','organism_name']). When specified, returns raw API response with requested fields. Common fields: accession, id, gene_names, gene_primary, protein_name, organism_name, organism_id, length, mass, sequence, reviewed, cc_function. See UniProt API docs for full list. Default (no fields): returns formatted response with accession, id, protein_name, gene_names, organism, length.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'description': 'Maximum number of results to return (default: 25, max: 500). Accepts string or integer.', 'required': False, 'type': 'integer'}, 'max_length': {'description': 'Maximum sequence length. Auto-converts to an open-ended length range query (unbounded to max).', 'required': False, 'type': 'integer'}, 'min_length': {'description': 'Minimum sequence length. Auto-converts to an open-ended length range query (min to unbounded).', 'required': False, 'type': 'integer'}, 'organism': {'description': "Optional organism filter. Use common names ('human', 'mouse', 'rat', 'yeast') or taxonomy ID ('9606'). Automatically combined with query using AND. Will not duplicate if organism is already in query.", 'required': False, 'type': 'string'}, 'query': {'description': "Search query using UniProt syntax. Simple: 'MEIOB', 'insulin'. Field searches: 'gene:TP53', 'protein_name:insulin', 'organism_id:9606', 'reviewed:true'. Ranges: 'length:[100 TO 500]', 'mass:[20000 TO 50000]'. Wildcards: 'gene:MEIOB*'. Boolean: 'gene:TP53 AND organism_id:9606', 'tissue:brain OR tissue:liver', 'reviewed:true NOT fragment:true'. Use parentheses for grouping: '(organism_id:9606 OR organism_id:10090) AND gene:TP53'. Note: 'organism:' auto-converts to 'organism_id:'.", 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- OpenTargets_get_target_id_description_by_name signature={'properties': {'targetName': {'description': 'The name of the target for which the ID is required.', 'required': True, 'type': 'string'}}, 'required': ['targetName'], 'type': 'object'}
- civic_get_variant signature={'properties': {'variant_id': {'description': 'CIViC variant ID (e.g., 4170)', 'required': True, 'type': 'integer'}}, 'required': ['variant_id'], 'type': 'object'}
- FDA_get_indications_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- cBioPortal_get_cancer_studies signature={'properties': {'limit': {'default': 20, 'description': 'Number of studies to return', 'required': False, 'type': 'integer'}}, 'type': 'object'}
- Reactome_map_uniprot_to_pathways signature={'properties': {'uniprot_id': {'description': "UniProt protein accession (e.g., 'P04637' for TP53, 'P00533' for EGFR)", 'required': True, 'type': 'string'}}, 'required': ['uniprot_id'], 'type': 'object'}
- GTEx_get_median_gene_expression signature={'properties': {'dataset_id': {'default': 'gtex_v8', 'description': 'GTEx dataset version (default: gtex_v8; v10 returns empty for most endpoints)', 'enum': ['gtex_v8', 'gtex_v10', 'gtex_snrnaseq_pilot'], 'required': False, 'type': 'string'}, 'gencode_id': {'description': "Gene identifier(s): gene symbol (e.g. 'TP53'), unversioned Ensembl ID (e.g. 'ENSG00000141510'), or versioned GENCODE ID (e.g. 'ENSG00000141510.18'). Auto-resolved to versioned GENCODE ID. Can be single string or array.", 'items': {'type': 'string'}, 'required': False, 'type': ['string', 'array']}, 'gene_symbol': {'description': 'Gene symbol alias for gencode_id (e.g., "TP53", "COL5A1")', 'required': False, 'type': 'string'}, 'items_per_page': {'default': 250, 'description': 'Results per page', 'maximum': 100000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'description': 'Operation type', 'enum': ['get_median_gene_expression'], 'required': False, 'type': 'string'}, 'page': {'default': 0, 'description': 'Page number for pagination (0-based)', 'minimum': 0, 'required': False, 'type': 'integer'}, 'tissue_site_detail_id': {'description': "Optional: Tissue IDs to filter (e.g. ['Liver', 'Brain_Cortex']). Omit for all tissues. See GTEx_get_tissue_sites for valid IDs", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- OpenTargets_get_associated_drugs_by_target_ensemblID
- query_term
- gene_symbol
- gene_id
- case_sensitive
- exact_match
- chembl_id
- ESM_API_KEY
- variant_id
- drug_name
- drugbank_get_drug_basic_info_by_drug_name_or_id
- study_id
- gene_list
- include_abstract
- gencode_id

# TARGET SKILL TO CONVERT
---
name: tooluniverse-cancer-variant-interpretation
description: "Clinical interpretation of somatic cancer mutations for precision oncology. Transforms a gene + variant + cancer-type input into an actionable report: clinical evidence tier (CIViC, OncoKB), therapeutic options (FDA-approved + investigational), resistance mechanisms, prognosis, and matching clinical trials. Use for tumor-board variant calls, somatic-mutation actionability assessment, and treatment selection. Always cancer-type-specific."
disable-model-invocation: true
---

# Cancer Variant Interpretation for Precision Oncology

Comprehensive clinical interpretation of somatic mutations in cancer. Transforms a gene + variant input into an actionable precision oncology report covering clinical evidence, therapeutic options, resistance mechanisms, clinical trials, and prognostic implications.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Evidence-graded** - Every recommendation has an evidence tier (T1-T4)
3. **Actionable output** - Prioritized treatment options, not data dumps
4. **Clinical focus** - Answer "what should we treat with?" not "what databases exist?"
5. **Resistance-aware** - Always check for known resistance mechanisms
6. **Cancer-type specific** - Tailor all recommendations to the patient's cancer type when provided
7. **Source-referenced** - Every statement must cite the tool/database source
8. **English-first queries** - Always use English terms in tool calls (gene names, drug names, cancer types), even if the user writes in another language. Respond in the user's language

---

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Apply when user asks:
- "What treatments exist for EGFR L858R in lung cancer?"
- "Patient has BRAF V600E melanoma - what are the options?"
- "Is KRAS G12C targetable?"
- "Patient progressed on osimertinib - what's next?"
- "What clinical trials are available for PIK3CA E545K?"
- "Interpret this somatic mutation: TP53 R273H"

---

## Input Parsing

**Required**: Gene symbol + variant notation (e.g., "EGFR L858R", "BRAF p.V600E", "EML4-ALK fusion", "HER2 amplification")
**Optional**: Cancer type (improves specificity)

Parse the gene symbol and variant separately. For fusions, use the kinase partner as the primary gene. For amplifications/deletions, use the gene name directly. Normalize common aliases: HER2 -> ERBB2, PD-L1 -> CD274, VEGF -> VEGFA.

---

## Phase 0: Tool Parameter Verification (CRITICAL)

**BEFORE calling ANY tool for the first time**, verify its parameters.

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblID` | `ensemblId` (camelCase) |
| `OpenTargets_get_drug_chembId_by_generic_name` | `genericName` | `drugName` |
| `OpenTargets_target_disease_evidence` | `ensemblID` | `ensemblId` + `efoId` |
| `MyGene_query_genes` | `q` | `query` |
| `search_clinical_trials` | `disease`, `biomarker` | `condition`, `query_term` (required) |
| `civic_get_variants_by_gene` | `gene_symbol` | `gene_id` (CIViC numeric ID) |
| `drugbank_*` | any 3 params | ALL 4 required: `query`, `case_sensitive`, `exact_match`, `limit` |
| `ChEMBL_get_drug_mechanisms` | `chembl_id` | `drug_chembl_id__exact` |
| `ensembl_lookup_gene` | no species | `species='homo_sapiens'` is REQUIRED |

---

## Workflow Overview

```
Input: Gene symbol + Variant notation + Optional cancer type

Phase 1: Gene Disambiguation & ID Resolution
  - Resolve gene to Ensembl ID, UniProt accession, Entrez ID
  - Get gene function, pathways, protein domains
  - Identify cancer type EFO ID (if cancer type provided)

Phase 2: Clinical Variant Evidence (CIViC)
  - Find gene in CIViC (via Entrez ID matching)
  - Get all variants for the gene, match specific variant
  - Retrieve evidence items (predictive, prognostic, diagnostic)

Phase 3: Mutation Prevalence (cBioPortal)
  - Frequency across cancer studies
  - Co-occurring mutations, cancer type distribution

Phase 4: Therapeutic Associations (OpenTargets + ChEMBL + FDA + DrugBank)
  - FDA-approved targeted therapies
  - Clinical trial drugs (phase 2-3), drug mechanisms
  - Combination therapies

Phase 5: Resistance Mechanisms
  - Known resistance variants (CIViC, literature)
  - Bypass pathway analysis (Reactome)

Phase 6: Clinical Trials
  - Active trials recruiting for this mutation
  - Trial phase, status, eligibility

Phase 7: Prognostic Impact & Pathway Context
  - Survival associations (literature)
  - Pathway context (Reactome), Expression data (GTEx)

Phase 8: Report Synthesis
  - Executive summary, clinical actionability score
  - Treatment recommendations (prioritized), completeness checklist
```

For detailed code snippets and API call patterns for each phase, see `ANALYSIS_DETAILS.md`.

---

## Clinical Reasoning Strategies

### Driver vs Passenger Reasoning

Not every mutation in a tumor is driving the cancer. Before querying databases, form a hypothesis:

- **Is this gene a known oncogene or tumor suppressor?** Genes like EGFR, BRAF, KRAS, TP53, PIK3CA are well-established cancer drivers. A mutation in one of these warrants deep investigation. A mutation in a gene with no known cancer role is likely a passenger.
- **Is this specific mutation recurrent across tumors (hotspot)?** Use cBioPortal to check. A mutation seen in hundreds of independent tumors (e.g., BRAF V600E) is almost certainly a driver. A unique, never-before-seen missense in the same gene is less certain.
- **What is the predicted functional impact?** Truncating mutations (nonsense, frameshift) in tumor suppressors are likely loss-of-function drivers. Missense mutations in oncogenes at known hotspot residues are likely gain-of-function drivers.
- **For unique (non-hotspot) missense in driver genes, look at mechanism, not just pathogenicity.** AlphaMissense gives a score; the ESMC-6B SAE composite `ESM_explain_variant_mechanism(sequence=wt_protein_seq, position=..., ref_aa=..., alt_aa=..., top_k_features=5)` answers *how* the substitution disrupts function — catalytic / ligand-binding / PTM / structural-stability loss. A unique missense that disrupts the same SAE feature category as a known driver hotspot in the same gene is more likely a driver than a missense that disrupts unrelated features. Requires `ESM_API_KEY`; missense only.
- **Conclusion pattern**: A recurrent mutation in a known driver gene is likely actionable. A unique mutation in a gene not associated with cancer is likely a passenger. State your assessment and the reasoning behind it.

### Actionability Reasoning

Actionable means a therapy exists that targets this alteration. Think in tiers based on evidence strength:

- **Tier 1**: FDA-approved drug for this mutation in this cancer type. The standard of care — recommend confidently. Example reasoning: "CIViC returns Level A evidence, FDA label confirms indication."
- **Tier 2**: FDA-approved for this mutation in a different cancer type, or strong clinical trial evidence (phase 2-3) in this cancer type. Reasonable to consider, especially under tumor-agnostic approvals or with molecular tumor board discussion.
- **Tier 3**: Preclinical evidence only — cell line data, animal models, or case reports. May justify clinical trial enrollment but not off-label use.
- **Tier 4**: Biological rationale but no direct evidence — the mutation is in a druggable pathway, or a structurally similar mutation responds to therapy. Hypothesis-generating only.

When synthesizing, state the tier and explain WHY you assigned it based on the evidence you found, not just which database returned a hit.

### Resistance Reasoning

If the patient has already been treated, ask: could this mutation be a resistance mechanism?

- **On-target resistance**: Mutations in the drug target gene itself that restore signaling despite drug binding. These typically emerge at the drug-binding site (e.g., EGFR T790M after erlotinib, EGFR C797S after osimertinib, ABL T315I after imatinib).
- **Bypass pathway activation**: Mutations in parallel signaling pathways that render the target irrelevant (e.g., MET amplification bypassing EGFR inhibition, BRAF activation bypassing MEK inhibition).
- **Phenotypic transformation**: Lineage changes (e.g., small cell transformation in EGFR-mutant lung cancer) that eliminate dependence on the original driver.
- **Timing matters**: If the mutation was detected AFTER treatment, it is more likely a resistance mechanism than if it was present at diagnosis.

### When to Use Which Tool

Form your clinical hypothesis FIRST based on gene function and mutation type, THEN use tools to validate:

- **CIViC** (`civic_search_genes`, `civic_get_variants_by_gene`): Your primary source for clinical evidence. Returns curated evidence items with evidence levels, clinical significance, and associated therapies. Start here for any variant with potential clinical relevance.
- **cBioPortal** (`cBioPortal_get_mutations`): Use to assess mutation prevalence — is this a hotspot? How common is it across cancer types? This informs your driver vs passenger assessment.
- **OpenTargets** (`OpenTargets_get_associated_drugs_by_target_ensemblID`): Use for actionability — what drugs target this gene? Cross-reference with CIViC evidence to assign tiers.
- **PubMed** (`PubMed_search_articles`): Use when CIViC lacks entries for your variant, or to find resistance mechanism reports and recent clinical trial results.
- **ClinicalTrials.gov** (`search_clinical_trials`): Use after establishing the variant is potentially actionable, to find enrollment opportunities.

---

## Tool Reference (Verified Parameters)

### Gene Resolution

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `MyGene_query_genes` | `query`, `species` | `hits[].ensembl.gene`, `.entrezgene`, `.symbol` |
| `UniProt_search` | `query`, `organism`, `limit` | `results[].accession` |
| `OpenTargets_get_target_id_description_by_name` | `targetName` | `data.search.hits[].id` |
| `ensembl_lookup_gene` | `gene_id`, `species` (REQUIRED) | `data.id`, `.version` |

### Clinical Evidence

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `civic_search_genes` | `query`, `limit` | `data.genes.nodes[].id`, `.entrezId` |
| `civic_get_variants_by_gene` | `gene_id` (CIViC numeric) | `data.gene.variants.nodes[]` |
| `civic_get_variant` | `variant_id` | `data.variant` |

### Drug Information

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblId`, `size` | `data.target.drugAndClinicalCandidates.rows[]` |
| `FDA_get_indications_by_drug_name` | `drug_name`, `limit` | `results[].indications_and_usage` |
| `drugbank_get_drug_basic_info_by_drug_name_or_id` | `query`, `case_sensitive`, `exact_match`, `limit` (ALL required) | `results[]` |

### Mutation Prevalence

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `cBioPortal_get_mutations` | `study_id`, `gene_list` | `data[].proteinChange` |
| `cBioPortal_get_cancer_studies` | `limit` | `[].studyId`, `.cancerTypeId` |

### Clinical Trials & Literature

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `search_clinical_trials` | `query_term` (required), `condition` | `studies[]` |
| `PubMed_search_articles` | `query`, `limit`, `include_abstract` | Returns **list** of dicts (NOT wrapped) |
| `Reactome_map_uniprot_to_pathways` | `id` (UniProt accession) | Pathway mappings |
| `GTEx_get_median_gene_expression` | `gencode_id`, `operation="median"` | Expression by tissue |

---

## Fallback Strategy

When a primary tool returns no results, fall back rather than reporting "no data found":
- **CIViC empty** -> search PubMed for "[gene] [variant] clinical evidence"
- **OpenTargets no drugs** -> try ChEMBL drug search by target
- **cBioPortal specific study empty** -> try pan-cancer study (msk_impact_2017 or similar)
- **Reactome no pathways** -> use UniProt function annotation for pathway context


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
