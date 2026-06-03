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
- CPIC_list_guidelines signature={'properties': {'drug': {'description': "Filter by drug name (e.g., 'codeine', 'warfarin', 'clopidogrel'). Case-insensitive substring match against drug names in the guideline.", 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Alias for drug.', 'required': False, 'type': 'string'}, 'gene': {'description': 'Filter by gene symbol (e.g., CYP2D6, TPMT). Returns only guidelines involving this gene.', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': 'Alias for gene. Filter by gene symbol (e.g., CYP2D6, TPMT).', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- FAERS_count_reactions_by_drug_event signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}, 'occurcountry': {'description': "Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.", 'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'reactionmeddraverse': {'description': 'Optional: Filter by MedDRA reaction term (Lowest Level Term). When omitted, returns all adverse reactions with their counts. When specified, filters results to only include that specific reaction term.', 'required': False, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'seriousnessdeath': {'description': "Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit this parameter to include all reports regardless of death outcome.", 'enum': ['Yes'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FAERS_filter_serious_events signature={'properties': {'adverse_event': {'description': 'Specific adverse event MedDRA term to filter within serious events (e.g., MYOCARDIAL INFARCTION, DEATH). Use uppercase MedDRA PT terms.', 'required': False, 'type': 'string'}, 'drug': {'description': 'Alias for drug_name. Generic drug name.', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Generic drug name', 'required': False, 'type': 'string'}, 'event_type': {'description': 'Alias for seriousness_type. Type of serious event (e.g., hospitalization, death, life_threatening).', 'required': False, 'type': 'string'}, 'operation': {'const': 'filter_serious_events', 'description': 'Operation type (fixed)', 'required': False}, 'seriousness_type': {'default': 'all', 'description': 'Type of serious event to filter', 'enum': ['all', 'death', 'hospitalization', 'disability', 'life_threatening'], 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- FAERS_stratify_by_demographics signature={'properties': {'adverse_event': {'description': 'MedDRA Preferred Term. Use exact MedDRA Preferred Term capitalization (e.g., "Haemorrhage" not "hemorrhage").', 'required': False, 'type': 'string'}, 'demographic': {'description': 'Alias for stratify_by. Demographic dimension to stratify by (sex, age, or country).', 'enum': ['sex', 'age', 'country'], 'required': False, 'type': 'string'}, 'drug': {'description': 'Alias for drug_name. Generic drug name.', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Generic drug name', 'required': False, 'type': 'string'}, 'operation': {'const': 'stratify_by_demographics', 'description': 'Operation type (fixed)', 'required': False}, 'reaction': {'description': 'Alias for adverse_event. MedDRA Preferred Term for the adverse drug reaction (e.g., "hemorrhage", "nausea").', 'required': False, 'type': 'string'}, 'stratify_by': {'default': 'sex', 'description': 'Demographic dimension to stratify by. Use "sex", "age", or "country" ("age_group" is also accepted as alias for "age").', 'enum': ['sex', 'age', 'country'], 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- DailyMed_search_spls signature={'properties': {'drug_name': {'description': "Generic or brand name of the drug, e.g., 'TAMSULOSIN HYDROCHLORIDE'.", 'required': True, 'type': 'string'}, 'ndc': {'description': 'National Drug Code (NDC).', 'required': False, 'type': 'string'}, 'page': {'default': 1, 'description': 'Page number, starts from 1, default 1.', 'required': False, 'type': 'integer'}, 'pagesize': {'default': 100, 'description': 'Number of items per page, maximum 100, default 100.', 'required': False, 'type': 'integer'}, 'published_date_eq': {'description': "Published date == specified date, format 'YYYY-MM-DD'.", 'required': False, 'type': 'string'}, 'published_date_gte': {'description': "Published date >= specified date, format 'YYYY-MM-DD'.", 'required': False, 'type': 'string'}, 'rxcui': {'description': 'RxNorm Code (RXCUI).', 'required': False, 'type': 'string'}, 'setid': {'description': 'Set ID corresponding to the SPL.', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': ['drug_name'], 'type': 'object'}
- PharmGKB_search_drugs signature={'properties': {'drug': {'description': 'Alias for query. Drug name to search.', 'required': False, 'type': 'string'}, 'drug_name': {'description': "Alias for query. Drug name to search (e.g., 'warfarin', 'metformin').", 'required': False, 'type': 'string'}, 'name': {'description': 'Alias for query. Drug name to search.', 'required': False, 'type': 'string'}, 'query': {'description': "Drug name or PharmGKB Chemical ID (e.g., 'warfarin', 'PA452637'). Aliases: drug_name, name, drug.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- OpenFDA_search_drug_events signature={'properties': {'adverse_event': {'description': 'Alias for reaction. MedDRA adverse reaction term (British spelling).', 'required': False, 'type': ['string', 'null']}, 'count': {'description': "Field to count by for frequency analysis (e.g., 'patient.reaction.reactionmeddrapt.exact' to get most common reactions)", 'required': False, 'type': ['string', 'null']}, 'drug_name': {'description': "Drug name to search for adverse events (e.g., 'warfarin', 'metformin'). Alternative to writing a full Lucene 'search' query.", 'required': False, 'type': ['string', 'null']}, 'limit': {'description': 'Maximum number of reports to return (default 1, max 100)', 'required': False, 'type': ['integer', 'null']}, 'reaction': {'description': "MedDRA adverse reaction term (British spelling: 'haemorrhage' not 'hemorrhage', 'haematoma' not 'hematoma'). Used with drug_name to filter by reaction.", 'required': False, 'type': ['string', 'null']}, 'search': {'description': 'Lucene query for adverse event reports. Use AND/OR with spaces (not +AND+). Examples: \'patient.drug.medicinalproduct:aspirin\', \'patient.reaction.reactionmeddrapt:"myocardial infarction"\', \'serious:1 AND patient.drug.medicinalproduct:warfarin\'. Combine drugs: \'patient.drug.medicinalproduct:metformin AND patient.drug.medicinalproduct:atorvastatin\'.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- OpenFDA_search_drug_labels signature={'properties': {'limit': {'description': 'Maximum number of results (default 1, max 100)', 'required': False, 'type': ['integer', 'null']}, 'search': {'description': 'Lucene query to search drug labels (e.g., \'openfda.brand_name:aspirin\', \'openfda.generic_name:metformin\', \'indications_and_usage:diabetes\', \'openfda.pharm_class_epc:"beta blocker"\')', 'required': True, 'type': 'string'}}, 'required': ['search'], 'type': 'object'}
- search_clinical_trials signature={'properties': {'condition': {'description': 'Query for condition or disease using Essie expression syntax (e.g., \'lung cancer\', \'(head OR neck) AND pain AND NOT "back pain"\'). ', 'required': False, 'type': 'string'}, 'intervention': {'description': "Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').", 'required': False, 'type': 'string'}, 'keyword': {'description': 'Alias for query_term. Free-text keyword search across all trial fields (e.g., drug name, condition, investigator).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Alias for max_results: maximum number of studies to return (default 10, max 1000).', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Maximum number of studies to return (alias for pageSize, default 10, max 1000).', 'required': False, 'type': 'integer'}, 'overall_status': {'description': "Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUITING', 'NOT_YET_RECRUITING']). Valid values: RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED, WITHDRAWN.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'pageSize': {'description': 'Maximum number of studies to return per page (default 10, max 1000).', 'required': False, 'type': 'integer'}, 'pageToken': {'description': "Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.", 'required': False, 'type': 'string'}, 'query_term': {'description': "Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.", 'required': False, 'type': 'string'}, 'status': {'description': 'Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLETED".', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': False}}, 'required': [], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- time_to_onset
- drug_name
- adverse_event
- filter_serious_events

# TARGET SKILL TO CONVERT
---
name: tooluniverse-pharmacovigilance
description: Drug safety and adverse event analysis — FAERS spontaneous-report mining, FDA black-box warnings, signal detection (PRR, ROR, IC), risk factors by demographic/comorbidity, and label change tracking. Use for post-market safety surveillance, AE signal investigation, drug-AE association strength scoring, and pharmacovigilance reports.
disable-model-invocation: true
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Pharmacovigilance Safety Analyzer

Systematic drug safety analysis using FAERS adverse event data, FDA labeling, PharmGKB pharmacogenomics, and clinical trial safety signals.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, update progressively
2. **Signal quantification** - Use disproportionality measures (PRR, ROR)
3. **Severity stratification** - Prioritize serious/fatal events
4. **Multi-source triangulation** - FAERS, labels, trials, literature
5. **Pharmacogenomic context** - Include genetic risk factors
6. **Actionable output** - Risk-benefit summary with recommendations
7. **English-first queries** - Always use English drug names in tool calls

---

## When to Use

Apply when user asks:
- "What are the safety concerns for [drug]?"
- "What adverse events are associated with [drug]?"
- "Is [drug] safe? What are the risks?"
- "Compare safety profiles of [drug A] vs [drug B]"
- "Pharmacovigilance analysis for [drug]"

---

## Clinical Reasoning Framework

### Reasoning Strategy 1: On-Target vs Off-Target Thinking

Ask: is this adverse effect a predictable extension of the drug's mechanism (on-target), or something the mechanism doesn't explain (off-target)? On-target effects are dose-dependent and predictable. Off-target effects are often idiosyncratic and harder to predict.

**How to apply this**:
1. Look up the drug's primary mechanism of action (use ChEMBL or DailyMed label)
2. For each reported adverse event, ask: "Does this follow logically from what the drug does to its target?" If yes, it is on-target toxicity — expect dose-dependence and manage with dose reduction
3. If the adverse event cannot be explained by the primary mechanism, consider off-target receptor binding or reactive metabolite formation. These require different management (drug discontinuation, not dose adjustment)
4. Use KEGG pathway data to identify metabolic routes that could produce toxic intermediates

---

### Reasoning Strategy 2: Timeline as Diagnostic Tool

When did the adverse event start relative to drug initiation? The timeline alone narrows the mechanism:

- **Hours** = anaphylaxis, immediate hypersensitivity, or direct pharmacological overshoot
- **Days** = serum sickness, cytotoxic reactions, cumulative pharmacological effects
- **1-6 weeks** = delayed hypersensitivity (SJS/TEN, DRESS), organ accumulation
- **Months** = chronic toxicity, cumulative organ damage
- **Years** = long-term cumulative effects

**How to apply this**: When reviewing FAERS case reports, always check the `time_to_onset` field. If the reported timeline is biologically implausible for the proposed mechanism, suspect confounding or misattribution. A reaction appearing years after drug start is unlikely to be immune-mediated but could be chronic accumulation.

---

### Reasoning Strategy 3: Dose-Dependent vs Idiosyncratic Classification

This distinction determines monitoring strategy and management:

- **Dose-dependent (Type A)**: Predictable from pharmacology. Dose-response relationship exists. Can be managed by dose reduction. These are on-target toxicities pushed too far.
- **Idiosyncratic (Type B)**: Not predictable from pharmacology alone. No clear dose-response. Often immune-mediated or due to metabolic idiosyncrasy (e.g., genetic variation in drug metabolism). Drug must be stopped — dose reduction will not help.
- **Mixed**: Some reactions are dose-dependent in most patients but become idiosyncratic in genetically susceptible individuals. When you see a "Type A" reaction occurring at unexpectedly low doses, suspect a pharmacogenomic contributor.

**How to apply this**: When evaluating a safety signal, classify it as Type A or B. This determines whether you recommend dose adjustment (Type A) or drug avoidance with potential pharmacogenomic screening (Type B).

---

### Reasoning Strategy 4: The Naranjo Algorithm for Causality Classification

When investigating a suspected drug adverse event, the Naranjo algorithm asks: (1) Did the event appear after the drug was given? (2) Did it improve when the drug was stopped? (3) Did it reappear when restarted? (4) Could other causes explain it? Score each question to classify causality.

### Reasoning Strategy 5: The Rechallenge Question

Did the event recur when the drug was restarted? Positive rechallenge is the strongest evidence for causation in an individual case. But rechallenge is often unethical for serious reactions, so absence of rechallenge data doesn't exonerate the drug.

**How to apply this**: When reviewing case narratives or FAERS reports, check for dechallenge (did the event resolve when the drug was stopped?) and rechallenge (did it recur on re-exposure?). A positive dechallenge + positive rechallenge is near-definitive. Negative dechallenge weakens the causal link considerably.

---

### Reasoning Strategy 5: Disproportionality Reasoning

A signal in FAERS means the drug-event pair is REPORTED more than expected. It does not mean the drug CAUSES the event. Think about reporting biases:

- Serious events get reported more than mild ones
- New drugs get reported more than old ones (Weber effect)
- Drugs prescribed to sick populations get events attributed to them that may reflect the underlying disease
- Media attention or regulatory alerts create reporting spikes

**How to apply this**: Always ask — what is the base rate of this event in the untreated population? A high PRR for "cardiac arrest" in a drug used by ICU patients may reflect the patient population, not the drug. Cross-reference with clinical trial placebo-arm rates when available.

---

### Reasoning Strategy 6: When to Use Tools vs Reason

Use FAERS/OpenFDA tools to QUANTIFY a signal you have already hypothesized based on mechanism. Do not mine FAERS without a hypothesis — you will find spurious associations.

**The correct sequence**:
1. Reason about mechanism first (what adverse events are plausible given this drug's pharmacology?)
2. Form specific hypotheses (e.g., "this drug may cause QT prolongation because it blocks hERG channels")
3. Query tools to test each hypothesis (FAERS for reporting frequency, DailyMed for label warnings, PharmGKB for genetic risk factors)
4. Interpret results in context (is the signal consistent with the mechanism? Is the timeline plausible? Are there confounders?)

---

### Reasoning Strategy 7: Pharmacogenomic Risk Assessment

Rather than memorizing gene-drug pairs, apply this reasoning framework:

1. **Identify the drug's metabolic pathway** (use KEGG or DailyMed label): Which CYP enzymes metabolize it? Is it a prodrug requiring activation?
2. **Assess the consequence of altered metabolism**: For active drugs, poor metabolizers accumulate the drug (toxicity risk). For prodrugs, poor metabolizers fail to activate (efficacy failure). Ultra-rapid metabolizers show the opposite pattern.
3. **Check for immune-mediated risk**: If the drug is associated with severe cutaneous reactions (SJS/TEN, DRESS) or hypersensitivity syndrome, query PharmGKB for HLA associations. These are population-specific.
4. **Use PharmGKB evidence levels to guide action**: Level 1A/1B (guideline-based) = actionable now. Level 2A/2B = may inform. Level 3 = not clinically actionable yet.

Query `PharmGKB_search_drug(query=...)` and `CPIC_list_guidelines` to get current pharmacogenomic annotations rather than relying on memorized associations, which may be outdated.

---

## Critical Workflow Requirements

### Report-First Approach (MANDATORY)

1. Create `[DRUG]_safety_report.md` FIRST with all section headers and `[Researching...]` placeholders
2. Apply mechanistic reasoning first (on-target toxicity, time-to-onset, dose vs. idiosyncratic, PGx)
3. Progressively update as data is gathered
4. Output separate data files: `[DRUG]_adverse_events.csv` and `[DRUG]_pharmacogenomics.csv`

### Citation Requirements (MANDATORY)

Every safety signal MUST include source tool, data period, PRR, case counts, and serious/fatal breakdown.

---

## Tool Parameter Reference (CRITICAL)

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `FAERS_count_reactions_by_drug_event` | `drug` | `drug_name` |
| `FAERS_filter_serious_events` | American spelling (e.g., "Hemorrhage") | MedDRA British spelling (e.g., "Haemorrhage") |
| `FAERS_stratify_by_demographics` | Requiring `adverse_event` | `adverse_event` is optional (omit for all-event stratification) |
| `DailyMed_search_spls` | `name` | `drug_name` |
| `PharmGKB_search_drugs` | `drug` | `query` |
| `OpenFDA_search_drug_events` | `drug_name` | `search` |

---

## Workflow Overview

```
Phase 0: Mechanistic Reasoning (BEFORE tools)
  On-target toxicity, time-to-onset, dose vs idiosyncratic, PGx risk

Phase 1: Drug Disambiguation
  -> Resolve drug name, get identifiers (ChEMBL, DrugBank)

Phase 2: Adverse Event Profiling (FAERS)
  -> Query FAERS, calculate PRR, stratify by seriousness

Phase 3: Label Warning Extraction
  -> DailyMed boxed warnings, contraindications, precautions

Phase 4: Pharmacogenomic Risk
  -> PharmGKB clinical annotations, high-risk genotypes

Phase 5: Clinical Trial Safety
  -> ClinicalTrials.gov Phase 3/4 safety data

Phase 5.5: Pathway & Mechanism Context
  -> KEGG drug metabolism, target pathway analysis

Phase 5.6: Literature Intelligence
  -> PubMed, BioRxiv/MedRxiv, OpenAlex citation analysis

Phase 6: Signal Prioritization
  -> Rank by PRR x severity x frequency

Phase 7: Report Synthesis
```

---

## Phase 0: Mechanistic Reasoning (DO THIS BEFORE TOOLS)

1. Identify drug class and primary mechanism (use DailyMed label or ChEMBL)
2. Apply on-target vs off-target thinking (Strategy 1) to predict plausible adverse events
3. Estimate expected time-to-onset for each predicted event (Strategy 2)
4. Classify each as dose-dependent vs idiosyncratic (Strategy 3)
5. Formulate specific, testable safety hypotheses to guide tool queries (Strategy 6)

## Phase 1: Drug Disambiguation

1. Search DailyMed via `DailyMed_search_spls(drug_name=...)` for NDC, SPL setid, generic name
2. Search ChEMBL via `ChEMBL_search_drugs(query=...)` for molecule ID, max phase
3. Document: generic name, brand names, drug class, mechanism, approval date

## Phase 2: Adverse Event Profiling (FAERS)

1. Query `FAERS_count_reactions_by_drug_event(drug_name=..., limit=50)` for top events
2. For each event, get detailed breakdown (serious, fatal, hospitalization counts)
3. Calculate PRR: `(A/B) / (C/D)` where A=drug+event, B=drug+any, C=event+any_other, D=total_other
4. Apply signal thresholds: PRR > 2.0 (signal), > 3.0 (strong signal), case count >= 3

**Severity classification**:
- Fatal (highest priority), Life-threatening, Hospitalization, Disability, Other serious, Non-serious

### FAERS `filter_serious_events` -- MedDRA Spelling (CRITICAL)

`FAERS_filter_serious_events` uses **MedDRA preferred terms** which follow British
English spelling conventions. Common examples:

| Incorrect (American) | Correct (MedDRA/British) |
|----------------------|--------------------------|
| HEMORRHAGE | Haemorrhage |
| ANEMIA | Anaemia |
| EDEMA | Oedema |
| DIARRHEA | Diarrhoea |
| LEUKOPENIA | Leucopenia |
| ESOPHAGITIS | Oesophagitis |

The `adverse_event` parameter should use the **exact MedDRA preferred term spelling**.
When in doubt, first query `FAERS_count_reactions_by_drug_event` to see the exact event
names as they appear in the FAERS database, then use those exact strings.

**Additional FAERS notes:**
- `adverse_event` is now correctly appended to the OpenFDA query in `_filter_serious_events`
- `FAERS_stratify_by_demographics`: `adverse_event` is optional — when omitted, stratification covers all events for the drug. Sex codes: 0=Unknown, 1=Male, 2=Female

See [SIGNAL_DETECTION.md](SIGNAL_DETECTION.md) for detailed disproportionality formulas and example output tables.

## Phase 3: Label Warning Extraction

1. Get label via `DailyMed_get_spl_by_set_id(setid=...)`
2. Extract: boxed warnings, contraindications, warnings/precautions, drug interactions
3. Categorize severity: Boxed Warning > Contraindication > Warning > Precaution

## Phase 4: Pharmacogenomic Risk

1. Search `PharmGKB_search_drug(query=...)` for clinical annotations
2. Document actionable variants with evidence levels (1A/1B/2A/2B/3)
3. Note CPIC/DPWG guideline status

**PGx Evidence Levels**:
| Level | Description | Action |
|-------|-------------|--------|
| 1A | CPIC/DPWG guideline, implementable | Follow guideline |
| 1B | CPIC/DPWG guideline, annotation | Consider testing |
| 2A | VIP annotation, moderate evidence | May inform |
| 2B | VIP annotation, weaker evidence | Research |
| 3 | Low-level annotation | Not actionable |

## Phase 5: Clinical Trial Safety

1. Search `search_clinical_trials(intervention=..., phase="Phase 3", status="Completed")`
2. Extract serious AE rates, discontinuation rates, deaths
3. Compare drug vs placebo rates

## Phase 5.5: Pathway & Mechanism Context

1. Query KEGG for drug metabolism pathways
2. Analyze target pathways for mechanistic basis of AEs
3. Document pathway-AE relationships

## Phase 5.6: Literature Intelligence

1. PubMed: `PubMed_search_articles(query='"[drug]" AND (safety OR adverse OR toxicity)')`
2. BioRxiv/MedRxiv: Search for recent preprints (flag as not peer-reviewed)
3. OpenAlex: Citation analysis for key safety papers

## Phase 6: Signal Prioritization

**Signal Score** = PRR x Severity_Weight x log10(Case_Count + 1)

Severity weights: Fatal=10, Life-threatening=8, Hospitalization=5, Disability=5, Other serious=3, Non-serious=1

Categorize signals:
- **Critical** (immediate attention): High PRR + fatal outcomes
- **Moderate** (monitor): Moderate PRR + serious outcomes
- **Known/Expected** (manage clinically): Low PRR, in label

**Cross-check against mechanistic prediction**: A signal not predicted mechanistically warrants additional scrutiny (possible confounding, reporting bias, or genuinely novel finding).

---

## Output Report

Save as `[DRUG]_safety_report.md`. See [REPORT_TEMPLATES.md](REPORT_TEMPLATES.md) for the full report structure and example outputs.

---

## Evidence Grading

| Tier | Criteria | Example |
|------|----------|---------|
| T1 | PRR >10, fatal outcomes, boxed warning | Lactic acidosis |
| T2 | PRR 3-10, serious outcomes | Hepatotoxicity |
| T3 | PRR 2-3, moderate concern | Hypoglycemia |
| T4 | PRR <2, known/expected | GI side effects |

---

## Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `FAERS_count_reactions_by_drug_event` | `OpenFDA_search_drug_events` | Literature search |
| `DailyMed_search_spls` | `OpenFDA_search_drug_labels` | DailyMed website |
| `PharmGKB_search_drugs` | `CPIC_list_guidelines` | Literature search |
| `search_clinical_trials` | `ClinicalTrials.gov` API | PubMed for trial results |

---

## Completeness Checklist

See [CHECKLIST.md](CHECKLIST.md) for the full phase-by-phase verification checklist.

---

## References

- FAERS: https://www.fda.gov/drugs/questions-and-answers-fdas-adverse-event-reporting-system-faers
- DailyMed: https://dailymed.nlm.nih.gov
- PharmGKB: https://www.pharmgkb.org
- ClinicalTrials.gov: https://clinicaltrials.gov
- OpenFDA: https://open.fda.gov
- KEGG Drug: https://www.genome.jp/kegg/drug
- Tool documentation: [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md)


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
