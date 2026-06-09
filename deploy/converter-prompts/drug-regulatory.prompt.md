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
- FDA_OrangeBook_get_exclusivity signature={'properties': {'application_number': {'description': 'FDA application number', 'required': False, 'type': 'string'}, 'brand_name': {'description': 'Brand name of drug', 'required': False, 'type': 'string'}, 'operation': {'const': 'get_exclusivity', 'description': 'Operation type (fixed)', 'required': False}}, 'required': [], 'type': 'object'}
- OpenFDA_get_approval_history signature={'properties': {'application_number': {'description': "FDA application number (e.g., 'NDA021457'). More specific than drug_name.", 'required': False, 'type': ['string', 'null']}, 'drug_name': {'description': "Drug name (brand or generic, e.g., 'warfarin', 'Eliquis', 'pembrolizumab')", 'required': False, 'type': ['string', 'null']}, 'operation': {'description': 'Operation type', 'enum': ['get_approval_history'], 'required': True, 'type': 'string'}}, 'required': ['operation'], 'type': 'object'}
- FAERS_count_reactions_by_drug_event signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}, 'occurcountry': {'description': "Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.", 'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'reactionmeddraverse': {'description': 'Optional: Filter by MedDRA reaction term (Lowest Level Term). When omitted, returns all adverse reactions with their counts. When specified, filters results to only include that specific reaction term.', 'required': False, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'seriousnessdeath': {'description': "Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit this parameter to include all reports regardless of death outcome.", 'enum': ['Yes'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- RxNorm_get_drug_names signature={'properties': {'drug_name': {'description': "The name of the drug to search for (e.g., 'ibuprofen', 'aspirin', 'acetaminophen'). Can be a generic name, brand name, or any drug name variant.", 'required': True, 'type': 'string'}}, 'required': ['drug_name'], 'type': 'object'}
- drugbank_vocab_search signature={'properties': {'case_sensitive': {'description': 'Whether the search should be case sensitive.', 'required': True, 'type': 'boolean'}, 'exact_match': {'description': 'Whether to perform exact matching instead of substring matching.', 'required': True, 'type': 'boolean'}, 'limit': {'description': 'Maximum number of results to return.', 'maximum': 1000, 'minimum': 1, 'required': True, 'type': 'integer'}, 'query': {'description': 'Search query string. Can be drug name, synonym, DrugBank ID, or any text to search for.', 'minLength': 1, 'required': True, 'type': 'string'}, 'search_fields': {'description': "Fields to search in. Available fields: 'DrugBank ID', 'Accession Numbers', 'Common name', 'CAS', 'UNII', 'Synonyms', 'Standard InChI Key'.", 'items': {'type': 'string'}, 'required': True, 'type': 'array'}}, 'required': ['query', 'search_fields', 'case_sensitive', 'exact_match', 'limit'], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- FDAGSRS_get_substance signature={'properties': {'unii': {'description': "FDA UNII (Unique Ingredient Identifier) code. 10-character alphanumeric string. Examples: 'R16CO5Y76E' (aspirin), '9100L32L2N' (ibuprofen), '4T6H12BN9U' (metformin), '57GNO57U7G' (semaglutide).", 'required': True, 'type': 'string'}}, 'required': ['unii'], 'type': 'object'}
- RxClass_get_class_members signature={'properties': {'class_id': {'description': "Drug class identifier. ATC class codes: 'M01AE' (propionic acid derivatives), 'N02BA' (salicylic acid derivatives), 'A10BA' (biguanides). FDA EPC IDs are long numeric strings.", 'required': True, 'type': 'string'}, 'limit': {'description': 'Maximum number of drugs to return (default 50).', 'required': False, 'type': ['integer', 'null']}, 'rela_source': {'description': "Classification source system. Options: 'ATC' (default), 'FDASPL', 'MESH', 'VA', 'DAILYMED'.", 'required': False, 'type': ['string', 'null']}, 'ttys': {'description': "RxNorm term types to include. Options: 'IN' (ingredients, default), 'PIN' (precise ingredients), 'MIN' (multi-ingredients), 'SCD' (semantic clinical drugs). Default: 'IN'.", 'required': False, 'type': ['string', 'null']}}, 'required': ['class_id'], 'type': 'object'}
- FDAGSRS_search_substances signature={'properties': {'limit': {'description': 'Maximum number of results to return (1-50, default 10).', 'required': False, 'type': ['integer', 'null']}, 'query': {'description': "Search query: drug/chemical name, UNII code, InChIKey, or molecular formula. Examples: 'aspirin', 'semaglutide', 'R16CO5Y76E', 'C9H8O4', 'BSYNRYMUTXBXSQ-UHFFFAOYSA-N'.", 'required': True, 'type': 'string'}, 'substance_class': {'description': "Filter by substance class. Options: 'chemical', 'protein', 'mixture', 'polymer', 'nucleicAcid', 'structurallyDiverse', 'specifiedSubstanceG1'. Default: no filter (all classes).", 'required': False, 'type': ['string', 'null']}}, 'required': ['query'], 'type': 'object'}
- FDAGSRS_get_structure signature={'properties': {'unii': {'description': "FDA UNII code for the chemical substance. Examples: 'R16CO5Y76E' (aspirin), '9100L32L2N' (ibuprofen), '4T6H12BN9U' (metformin), 'IY9XDZ35W2' (cisplatin).", 'required': True, 'type': 'string'}}, 'required': ['unii'], 'type': 'object'}
- search_clinical_trials signature={'properties': {'condition': {'description': 'Query for condition or disease using Essie expression syntax (e.g., \'lung cancer\', \'(head OR neck) AND pain AND NOT "back pain"\'). ', 'required': False, 'type': 'string'}, 'intervention': {'description': "Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').", 'required': False, 'type': 'string'}, 'keyword': {'description': 'Alias for query_term. Free-text keyword search across all trial fields (e.g., drug name, condition, investigator).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Alias for max_results: maximum number of studies to return (default 10, max 1000).', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Maximum number of studies to return (alias for pageSize, default 10, max 1000).', 'required': False, 'type': 'integer'}, 'overall_status': {'description': "Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUITING', 'NOT_YET_RECRUITING']). Valid values: RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED, WITHDRAWN.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'pageSize': {'description': 'Maximum number of studies to return per page (default 10, max 1000).', 'required': False, 'type': 'integer'}, 'pageToken': {'description': "Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.", 'required': False, 'type': 'string'}, 'query_term': {'description': "Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.", 'required': False, 'type': 'string'}, 'status': {'description': 'Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLETED".', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': False}}, 'required': [], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- substance_class
- cross_references
- drug_name
- rela_source
- class_type
- class_id
- brand_name
- generic_name
- application_number
- te_code
- exclusivity_code
- query_term
- max_results
- overall_status
- total_count

# TARGET SKILL TO CONVERT
---
name: tooluniverse-drug-regulatory
description: Drug regulatory and approval research — FDA substance registry, ATC/EPC classification, EMA decisions, generic-drug status, FDA Orange Book exclusivity, NDA/BLA pathways. Use for jurisdiction-aware approval status (FDA vs EMA), generic vs brand availability, exclusivity expiry tracking, and regulatory pathway selection. Always specifies the market when reporting status.
triggers:
  - keywords: [FDA, Orange Book, generic drug, UNII, RxClass, ATC code, drug class, NDA, ANDA, patent, exclusivity, DailyMed, drug label, adverse reactions, regulatory, approval]
  - patterns: ["FDA approved", "generic available", "patent expiration", "drug class", "ATC code", "Orange Book", "DailyMed", "drug labeling", "UNII"]
disable-model-invocation: true
---

# Drug Regulatory Research

**Regulatory status depends on jurisdiction.** FDA approval does not equal EMA approval — check the specific market the user is asking about. Generic availability depends on BOTH patent expiry AND regulatory approval — a patent may have expired but no ANDA may yet be filed or approved. Exclusivity codes (NCE, ODE, PED) can block generics even after patent expiry; always check `FDA_OrangeBook_get_exclusivity` before concluding a generic can enter. A 505(b)(2) NDA is not a generic — it requires its own clinical data and gets its own exclusivity period.

**LOOK UP DON'T GUESS**: never assume NDA numbers, exclusivity dates, or ATC codes — always call FDAGSRS, Orange Book, and RxClass tools to retrieve current data; regulatory status changes with new approvals and expirations.

Regulatory intelligence for drugs: identify FDA substances, classify drugs by therapeutic
category, check approval and generic status, retrieve label sections, and find clinical trials.

## When to Use

- "What is the FDA regulatory status of semaglutide?"
- "Is there a generic for Humira?"
- "What ATC class does metformin belong to?"
- "Get adverse reactions from the ibuprofen drug label"
- "When does the patent for Eliquis expire?"
- "List all drugs in the ACE inhibitor class"
- "Find clinical trials for a biosimilar of adalimumab"

## NOT for (use other skills instead)

- Drug-drug interactions -> Use `tooluniverse-drug-drug-interaction`
- Pharmacogenomics / dosing by genotype -> Use `tooluniverse-pharmacogenomics`
- Drug mechanism of action / target binding -> Use `tooluniverse-drug-mechanism-research`
- Drug repurposing / new indications -> Use `tooluniverse-drug-repurposing`

---

## Workflow Overview

```
Input (drug name / brand name / UNII)
  |
  v
Phase 1: Substance Identification  -- FDAGSRS_search_substances, FDAGSRS_get_substance
  |
  v
Phase 2: Drug Classification       -- RxClass_get_drug_classes, RxClass_find_classes
  |
  v
Phase 3: Approval & Generic Status -- FDA_OrangeBook_search_drug, FDA_OrangeBook_check_generic_availability
  |
  v
Phase 4: Patent & Exclusivity      -- FDA_OrangeBook_get_patent_info, FDA_OrangeBook_get_exclusivity
  |
  v
Phase 5: Label Parsing             -- DailyMed_parse_adverse_reactions, DailyMed_parse_dosing, etc.
  |
  v
Phase 6: Clinical Trials           -- search_clinical_trials
  |
  v
Phase 7: Pharmacovigilance         -- FAERS_count_reactions_by_drug_event (param: medicinalproduct)
  |
  v
Phase 8: Literature & Approval     -- PubMed_search_articles, OpenFDA_get_approval_history, RxNorm_get_drug_names
```

> **Supplementary tools** (not in core phases but useful):
> - `OpenFDA_get_approval_history` — full FDA submission/approval history (requires `operation` param)
> - `FAERS_count_reactions_by_drug_event` — top adverse events by report count (param: `medicinalproduct`, ALL CAPS)
> - `RxNorm_get_drug_names` — resolve drug to RXCUI and brand names
> - `drugbank_vocab_search` — DrugBank ID, CAS, UNII lookup
> - `PubMed_search_articles` — regulatory and clinical literature

---

## Phase 1: Substance Identification (FDAGSRS)

**FDAGSRS_search_substances**: `query` (string REQUIRED -- drug name, UNII, InChIKey, or formula), `substance_class` (string, optional: "chemical"/"protein"/"nucleic acid"/"polymer"/"mixture"), `limit` (int, 1-50, default 10).
Returns `{status, data: {substances: [{unii, name, substance_class, status, cross_references: [{type, value}]}]}}`.
- `cross_references` contains DrugBank IDs, WHO-ATC codes, CAS numbers, CFR citations.
- Use to get the official UNII identifier before calling `FDAGSRS_get_substance`.

**FDAGSRS_get_substance**: `unii` (string REQUIRED, 10-char FDA UNII code).
Returns complete substance record including all synonyms, names, structure, and cross-references.
- Provides definitive list of all registered names (INN, USAN, brand, chemical).

**FDAGSRS_get_structure**: `unii` (string REQUIRED).
Returns `{status, data: {smiles, formula, inchikey, molfile, molecular_weight, stereochemistry, optical_activity}}`.
- Only works for chemical substances; returns error for biologics, mixtures, polymers.

```python
# Full substance lookup workflow
search = tu.tools.FDAGSRS_search_substances(query="semaglutide")
unii = search["data"]["substances"][0]["unii"]
full = tu.tools.FDAGSRS_get_substance(unii=unii)
```

---

## Phase 2: Drug Classification (RxClass)

**RxClass_get_drug_classes**: `drug_name` (string, drug name), `rxcui` (string, RxNorm RXCUI -- alternative to drug_name), `rela_source` (string, optional: "ATC"/"FDASPL"/"MESH"/"VA"), `limit` (int, default 20).
Returns `{status, data: {classes: [{class_id, class_name, class_type, rela}]}}`.
- Returns ALL classification systems unless `rela_source` filters to one.
- `class_type` values: "ATC1-4", "EPC" (FDA Established Pharmacologic Class), "MoA", "VA", "MESH".
- Use to find a drug's ATC code, pharmacological class, mechanism of action label.

**RxClass_find_classes**: `query` (string REQUIRED, keyword e.g., "beta blocker"), `class_type` (string, optional: "ATC1-4"/"EPC"/"MoA"), `limit` (int, default 20).
Returns matching drug classes with class IDs.
- Use when you need to find a class ID before calling `RxClass_get_class_members`.

**RxClass_get_class_members**: `class_id` (string REQUIRED, e.g., "M01AE"), `rela_source` (string, optional: "ATC"/"FDASPL"), `ttys` (string, optional: "IN" for ingredients), `limit` (int, default 50).
Returns all drug ingredients in the class with RXCUIs and names.
- `ttys="IN"` restricts to active ingredient-level entries (recommended).

```python
# Find all proton pump inhibitors
classes = tu.tools.RxClass_find_classes(query="proton pump inhibitor", class_type="EPC")
class_id = classes["data"]["classes"][0]["class_id"]
members = tu.tools.RxClass_get_class_members(class_id=class_id, ttys="IN")
```

---

## Phase 3: Approval & Generic Status (FDA Orange Book)

**FDA_OrangeBook_search_drug**: `brand_name` (string), `generic_name` (string), `application_number` (string), `limit` (int, default 10).
Returns `{status, data: {products: [{brand_name, generic_name, dosage_form, strength, te_code, application_number, approval_date}]}}`.
- Use brand name (UPPERCASE) or generic name to find NDA/ANDA numbers and approval info.
- `te_code`: Therapeutic Equivalence code (e.g., "AB" = therapeutically equivalent).

**FDA_OrangeBook_check_generic_availability**: `brand_name` (string), `generic_name` (string).
Returns `{status, data: {reference_listed_drug, generics_available: bool, generics_count, generic_products: [...]}}`.
- Primary tool for "is there a generic?" questions.

**FDA_OrangeBook_get_te_code**: No special params beyond `brand_name`/`application_number`.
Returns therapeutic equivalence codes for substitutability assessment.

**FDA_OrangeBook_get_approval_history**: `application_number` (string, e.g., "NDA020402").
Returns chronological approval history including supplemental approvals and label changes.

```python
# Check generic availability
result = tu.tools.FDA_OrangeBook_check_generic_availability(brand_name="LIPITOR")
# result["data"]["generics_available"] -> True
# result["data"]["generics_count"] -> N
```

---

## Phase 4: Patent & Exclusivity

**FDA_OrangeBook_get_patent_info**: `application_number` (string), `brand_name` (string).
Returns patent information. Note: Full patent numbers and expiration dates require Orange Book data files.

**FDA_OrangeBook_get_exclusivity**: `application_number` (string), `brand_name` (string).
Returns `{status, data: {exclusivities: [{exclusivity_code, exclusivity_date, description}]}}`.
- `exclusivity_code` values: "NCE" (New Chemical Entity, 5 years), "ODE" (Orphan Drug, 7 years), "PED" (Pediatric, 6 months), "NP" (New Product), "M" (new formulation).

---

## Phase 5: Label Parsing (DailyMed)

All DailyMed parse tools accept either `setid` (SPL Set ID UUID) OR `drug_name` (auto-lookup).
Using `drug_name` is recommended when the setid is unknown.

**DailyMed_parse_adverse_reactions**: `setid` or `drug_name`. Returns structured adverse reaction table with frequencies and severity.

**DailyMed_parse_dosing**: `setid` or `drug_name`. Returns dosage and administration section (doses, schedules, renal/hepatic adjustments).

**DailyMed_parse_contraindications**: `setid` or `drug_name`. Returns contraindications section.

**DailyMed_parse_drug_interactions**: `setid` or `drug_name`. Returns drug-drug interaction section with clinical management guidance.

**DailyMed_parse_clinical_pharmacology**: `setid` or `drug_name`. Returns PK/PD data (Cmax, AUC, half-life, protein binding, metabolism pathway).

**DailyMed_search_spls**: `drug_name` (string), returns SPL Set IDs for that drug. Use to find `setid` when needed explicitly.

```python
# Parse adverse reactions for apixaban
ae = tu.tools.DailyMed_parse_adverse_reactions(drug_name="apixaban")
```

---

## Phase 6: Clinical Trials

**search_clinical_trials**: `condition` (string), `intervention` (string), `query_term` (string), `pageSize` (int, alias: `max_results`/`limit`), `overall_status` (array, alias: `status`).
Returns `{status, data: {studies: [{NCT ID, brief_title, brief_summary, overall_status, phase}], total_count}}`.
- Use `intervention` for drug name, `condition` for disease.
- Filter `overall_status=["RECRUITING"]` for active enrollment.
- `total_count` may be None even when results exist; check `len(studies) > 0`.

```python
# Find recruiting trials for a biosimilar
trials = tu.tools.search_clinical_trials(
    intervention="adalimumab biosimilar",
    overall_status=["RECRUITING"],
    pageSize=10
)
```

---

## Example Workflows

### Workflow 1: Full Regulatory Profile for a Drug

```
1. FDAGSRS_search_substances(query="apixaban")
   -> UNII, substance class, ATC/DrugBank cross-refs

2. RxClass_get_drug_classes(drug_name="apixaban", rela_source="ATC")
   -> ATC code B01AF02 (direct factor Xa inhibitor)

3. FDA_OrangeBook_search_drug(brand_name="ELIQUIS")
   -> NDA206518, approval date, TE code

4. FDA_OrangeBook_check_generic_availability(brand_name="ELIQUIS")
   -> Generic availability status

5. FDA_OrangeBook_get_exclusivity(brand_name="ELIQUIS")
   -> Exclusivity codes and expiration dates

6. DailyMed_parse_adverse_reactions(drug_name="apixaban")
   -> Bleeding rates and other AEs from label
```

### Workflow 2: List All Drugs in a Therapeutic Class

```
1. RxClass_find_classes(query="ACE inhibitor", class_type="EPC")
   -> class_id for "Angiotensin-Converting Enzyme Inhibitor"

2. RxClass_get_class_members(class_id=<id>, ttys="IN")
   -> All ACE inhibitors (enalapril, lisinopril, ramipril, etc.)

3. For each drug: RxClass_get_drug_classes(drug_name=drug)
   -> Confirm ATC code and additional classifications
```

### Workflow 3: Drug Label Review

```
1. DailyMed_parse_adverse_reactions(drug_name="metformin")
   -> AE frequencies (GI: lactic acidosis, nausea, diarrhea)

2. DailyMed_parse_contraindications(drug_name="metformin")
   -> eGFR thresholds, renal impairment contraindications

3. DailyMed_parse_drug_interactions(drug_name="metformin")
   -> Iodinated contrast, carbonic anhydrase inhibitor interactions

4. DailyMed_parse_clinical_pharmacology(drug_name="metformin")
   -> Half-life, renal clearance, bioavailability
```

---

## Common Mistakes

- Orange Book `brand_name` must be UPPERCASE (e.g., `"LIPITOR"`)
- `FDAGSRS_get_substance` requires UNII, not drug name — call `FDAGSRS_search_substances` first
- `FDAGSRS_get_structure` only works for chemical substances, not biologics
- `RxClass_get_class_members`: pass `ttys="IN"` to restrict to active ingredients
- `search_clinical_trials` `overall_status` must be an array: `["RECRUITING"]`

---

## Reasoning Framework

### Interpretation Guidance

**Approval pathways**: A 505(b)(1) NDA is a full new drug application with complete safety/efficacy data from the sponsor. A 505(b)(2) NDA relies partly on published literature or FDA findings for an already-approved drug (common for reformulations, new routes). An ANDA (Abbreviated NDA) is the generic pathway requiring only bioequivalence to the reference listed drug.

**Orange Book patent and exclusivity**: NCE (New Chemical Entity) exclusivity gives 5 years of data protection. ODE (Orphan Drug Exclusivity) gives 7 years. PED (Pediatric) adds 6 months to existing patents/exclusivity. A TE code of "AB" means the generic is therapeutically equivalent and substitutable. No TE code or "BX" means substitutability is not established.

**DailyMed label sections**: The "Adverse Reactions" section distinguishes clinical trial rates (controlled) from post-marketing reports (uncontrolled, signal-only). "Contraindications" are absolute; "Warnings and Precautions" are conditional risks. "Clinical Pharmacology" provides PK parameters (Cmax, AUC, half-life) essential for drug interaction and dosing assessment.

### Synthesis Questions

A complete drug regulatory report should answer:
1. What is the current FDA approval status and pathway (NDA vs ANDA vs 505(b)(2))?
2. Are generic equivalents available, and what is their therapeutic equivalence rating?
3. When do key patents and exclusivities expire (or have they already)?
4. What drug class does this belong to (ATC, EPC, MoA), and what are peer drugs in the class?
5. What are the most clinically significant adverse reactions and contraindications from the label?



# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
