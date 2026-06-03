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
- FDA_get_adverse_reactions_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- FAERS_stratify_by_demographics signature={'properties': {'adverse_event': {'description': 'MedDRA Preferred Term. Use exact MedDRA Preferred Term capitalization (e.g., "Haemorrhage" not "hemorrhage").', 'required': False, 'type': 'string'}, 'demographic': {'description': 'Alias for stratify_by. Demographic dimension to stratify by (sex, age, or country).', 'enum': ['sex', 'age', 'country'], 'required': False, 'type': 'string'}, 'drug': {'description': 'Alias for drug_name. Generic drug name.', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Generic drug name', 'required': False, 'type': 'string'}, 'operation': {'const': 'stratify_by_demographics', 'description': 'Operation type (fixed)', 'required': False}, 'reaction': {'description': 'Alias for adverse_event. MedDRA Preferred Term for the adverse drug reaction (e.g., "hemorrhage", "nausea").', 'required': False, 'type': 'string'}, 'stratify_by': {'default': 'sex', 'description': 'Demographic dimension to stratify by. Use "sex", "age", or "country" ("age_group" is also accepted as alias for "age").', 'enum': ['sex', 'age', 'country'], 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- OpenTargets_get_drug_chembId_by_generic_name signature={'properties': {'drugName': {'description': 'The generic name of the drug for which the ID is required.', 'required': True, 'type': 'string'}}, 'required': ['drugName'], 'type': 'object'}
- OpenTargets_get_drug_indications_by_chemblId signature={'properties': {'chemblId': {'description': 'The chemblId of the drug for which to retrieve treatable phenotypes information.', 'required': True, 'type': 'string'}}, 'required': ['chemblId'], 'type': 'object'}
- FAERS_count_reactions_by_drug_event signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}, 'occurcountry': {'description': "Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.", 'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'reactionmeddraverse': {'description': 'Optional: Filter by MedDRA reaction term (Lowest Level Term). When omitted, returns all adverse reactions with their counts. When specified, filters results to only include that specific reaction term.', 'required': False, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'seriousnessdeath': {'description': "Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit this parameter to include all reports regardless of death outcome.", 'enum': ['Yes'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FAERS_count_seriousness_by_drug_event signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}, 'occurcountry': {'description': "Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.", 'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FAERS_count_outcomes_by_drug_event signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}, 'occurcountry': {'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FAERS_count_patient_age_distribution signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FAERS_count_death_related_by_drug signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FAERS_count_reportercountry_by_drug_event signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FAERS_filter_serious_events signature={'properties': {'adverse_event': {'description': 'Specific adverse event MedDRA term to filter within serious events (e.g., MYOCARDIAL INFARCTION, DEATH). Use uppercase MedDRA PT terms.', 'required': False, 'type': 'string'}, 'drug': {'description': 'Alias for drug_name. Generic drug name.', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Generic drug name', 'required': False, 'type': 'string'}, 'event_type': {'description': 'Alias for seriousness_type. Type of serious event (e.g., hospitalization, death, life_threatening).', 'required': False, 'type': 'string'}, 'operation': {'const': 'filter_serious_events', 'description': 'Operation type (fixed)', 'required': False}, 'seriousness_type': {'default': 'all', 'description': 'Type of serious event to filter', 'enum': ['all', 'death', 'hospitalization', 'disability', 'life_threatening'], 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- FAERS_rollup_meddra_hierarchy signature={'properties': {'drug': {'description': 'Alias for drug_name. Generic drug name.', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Generic drug name', 'required': False, 'type': 'string'}, 'operation': {'const': 'rollup_meddra_hierarchy', 'description': 'Operation type (fixed)', 'required': False}}, 'required': [], 'type': 'object'}
- FAERS_calculate_disproportionality signature={'properties': {'adverse_event': {'description': 'MedDRA Preferred Term (e.g., \'Hepatotoxicity\', \'Myopathy\'). Use exact MedDRA Preferred Term capitalization (e.g., "Haemorrhage" not "hemorrhage").', 'required': False, 'type': 'string'}, 'drug': {'description': 'Alias for drug_name. Generic drug name.', 'required': False, 'type': 'string'}, 'drug_name': {'description': "Generic drug name (e.g., 'IBUPROFEN', 'ATORVASTATIN')", 'required': False, 'type': 'string'}, 'operation': {'const': 'calculate_disproportionality', 'description': 'Operation type (fixed)', 'required': False}, 'reaction': {'description': 'Alias for adverse_event. MedDRA Preferred Term for the adverse drug reaction.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- FDA_get_boxed_warning_info_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FDA_get_contraindications_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FDA_get_warnings_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FDA_get_drug_interactions_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FDA_get_geriatric_use_info_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FDA_get_pediatric_use_info_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FDA_get_pharmacogenomics_info_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- ADMETAI_predict_toxicity signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_CYP_interactions signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- OpenTargets_get_drug_warnings_by_chemblId signature={'properties': {'chemblId': {'description': 'The ChEMBL ID of the drug.', 'required': True, 'type': 'string'}}, 'required': ['chemblId'], 'type': 'object'}
- FAERS_compare_drugs signature={'properties': {'adverse_event': {'description': 'MedDRA Preferred Term to compare. Use exact MedDRA Preferred Term capitalization (e.g., "Haemorrhage" not "hemorrhage").', 'required': False, 'type': 'string'}, 'drug1': {'description': 'First drug name (generic)', 'required': False, 'type': 'string'}, 'drug2': {'description': 'Second drug name (generic)', 'required': False, 'type': 'string'}, 'drugs': {'description': 'Alias for drug1/drug2. List of two drug names to compare, e.g., ["tofacitinib", "baricitinib"].', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'operation': {'const': 'compare_drugs', 'description': 'Operation type (fixed)', 'required': False}, 'reaction': {'description': 'Alias for adverse_event. MedDRA Preferred Term for the adverse drug reaction.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- FAERS_count_additive_adverse_reactions signature={'properties': {'medicinalproducts': {'description': 'Array of medicinal product names.', 'items': {'type': 'string'}, 'required': True, 'type': 'array'}, 'occurcountry': {'description': "Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.", 'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'seriousnessdeath': {'description': "Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit this parameter to include all reports regardless of death outcome.", 'enum': ['Yes'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproducts'], 'type': 'object'}
- DailyMed_parse_drug_interactions signature={'properties': {'drug_name': {'description': 'Drug name for automatic Set ID lookup (alternative to setid)', 'required': False, 'type': 'string'}, 'operation': {'const': 'parse_drug_interactions', 'description': 'Operation type (fixed)', 'required': False}, 'setid': {'description': 'SPL Set ID to parse', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- PharmGKB_search_drugs signature={'properties': {'drug': {'description': 'Alias for query. Drug name to search.', 'required': False, 'type': 'string'}, 'drug_name': {'description': "Alias for query. Drug name to search (e.g., 'warfarin', 'metformin').", 'required': False, 'type': 'string'}, 'name': {'description': 'Alias for query. Drug name to search.', 'required': False, 'type': 'string'}, 'query': {'description': "Drug name or PharmGKB Chemical ID (e.g., 'warfarin', 'PA452637'). Aliases: drug_name, name, drug.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- PharmGKB_get_drug_details signature={'properties': {'drug_id': {'description': "PharmGKB Chemical ID (e.g., 'PA452637').", 'required': True, 'type': 'string'}}, 'required': ['drug_id'], 'type': 'object'}
- PharmGKB_get_dosing_guidelines signature={'properties': {'gene': {'description': "Gene symbol (e.g., 'CYP2D6'). NOTE: Filtering by gene symbol is unreliable and may return a generic prompt instead of actual guidelines. Use guideline_id instead.", 'required': False, 'type': 'string'}, 'guideline_id': {'description': "PharmGKB ClinPGx guideline ID from CPIC_list_guidelines 'clinpgxid' field (e.g., 'PA166251465' for warfarin, 'PA166251454' for opioids/codeine, 'PA166251458' for tamoxifen). Use clinpgxid, NOT pharmgkbid.", 'required': True, 'type': 'string'}}, 'required': ['guideline_id'], 'type': 'object'}
- fda_pharmacogenomic_biomarkers signature={'properties': {'biomarker': {'description': "Filter by the specific biomarker (e.g., 'CYP2D6', 'HLA-B*5701'). Case-insensitive partial match.", 'required': False, 'type': 'string'}, 'drug_name': {'description': "Filter by the name of the drug (e.g., 'Sivextro', 'Abacavir'). Case-insensitive partial match.", 'required': False, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of results to return.', 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- openalex_search_works signature={'anyOf': [{'required': ['search']}, {'required': ['query']}], 'properties': {'filter': {'description': 'OpenAlex filter string (comma-separated). Example: "from_publication_date:2020-01-01,is_oa:true".', 'required': False, 'type': 'string'}, 'fulltext_terms': {'description': 'Optional list of terms to match in OpenAlex full-text index. Adds one or more fulltext.search:<term> filters and implicitly enables require_has_fulltext.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'description': 'Alias for `per_page` (OpenAlex max 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'mailto': {'description': 'Optional contact email for OpenAlex polite pool. If omitted, ToolUniverse uses a default.', 'required': False, 'type': 'string'}, 'page': {'default': 1, 'description': 'Page number (1-indexed).', 'minimum': 1, 'required': False, 'type': 'integer'}, 'per_page': {'default': 10, 'description': 'Results per page (OpenAlex max 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'query': {'description': 'Alias for `search` (recommended when you standardize on `query` across multiple paper-search tools).', 'required': False, 'type': 'string'}, 'require_has_fulltext': {'default': False, 'description': 'If true, appends OpenAlex filter has_fulltext:true (keeps only works with full-text index available).', 'required': False, 'type': 'boolean'}, 'search': {'description': 'Search query for works. Use filter + fulltext_terms/require_has_fulltext when you need full-text-index-only matching.', 'required': False, 'type': 'string'}, 'sort': {'description': 'Sort order string, e.g. "cited_by_count:desc".', 'required': False, 'type': 'string'}}, 'type': 'object'}
- EuropePMC_search_articles signature={'properties': {'enrich_missing_abstract': {'default': False, 'description': 'If true, best-effort fills missing abstracts by fetching Europe PMC fullTextXML (bounded to a few results).', 'required': False, 'type': 'boolean'}, 'extract_terms_from_fulltext': {'description': "Optional list of terms to extract from full text (open access only). When provided, automatically fetches fullTextXML for open-access articles and returns snippets around these terms. Terms are processed in batches of 5 internally, so any number of terms is accepted. Bounded to first 3 OA articles to avoid latency. Returns snippets in a 'fulltext_snippets' field for each article.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'fulltext_terms': {'description': 'Optional list of terms that must occur in the indexed full text (Europe PMC BODY field). When provided, the tool adds a BODY:"..." clause and automatically enables `require_has_ft`.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'default': 5, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from Europe PMC.', 'required': False, 'type': 'integer'}, 'page_size': {'description': 'Alias for limit â\x80\x94 number of results to return', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Europe PMC. Supports Lucene-like fielded syntax (e.g., BODY:"term", INTRO:"term", METHODS:"term").', 'required': True, 'type': 'string'}, 'require_has_ft': {'default': False, 'description': 'If true, appends `HAS_FT:Y` to the query to restrict results to records where Europe PMC has full text indexed. This is NOT the same as having a link to free full text elsewhere (e.g., PMC) and is often the key reason body-only keywords cannot be found via Europe PMC search.', 'required': False, 'type': 'boolean'}}, 'required': ['query'], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- OpenTargets_get_drug_mechanisms_of_action_by_chemblId
- drugbank_get_targets_by_drug_name_or_drugbank_id
- drugbank_get_drug_interactions_by_drug_name_or_id
- OpenTargets_get_drug_blackbox_status_by_chembl_ID
- drugbank_get_safety_by_drug_name_or_drugbank_id
- FDA_get_pregnancy_or_breastfeeding_info_by_drug_name
- OpenTargets_get_target_safety_profile_by_ensemblID
- OpenTargets_get_drug_adverse_events_by_chemblId
- FAERS_count_additive_seriousness_classification

# TARGET SKILL TO CONVERT
---
name: tooluniverse-adverse-event-detection
description: Detect and analyze adverse drug event signals using FDA FAERS reports, drug labels, and disproportionality statistics (PRR, ROR, IC). Generates quantitative safety signal scores (0-100) with evidence grading. Use for post-market surveillance, pharmacovigilance, drug safety assessment, regulatory submissions, and detecting rare AE signals not visible in clinical trials.
disable-model-invocation: true
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Adverse Drug Event Signal Detection & Analysis

Automated pipeline for detecting, quantifying, and contextualizing adverse drug event signals using FAERS disproportionality analysis, FDA label mining, mechanism-based prediction, and literature evidence. Produces a quantitative Safety Signal Score (0-100) for regulatory and clinical decision-making.

**KEY PRINCIPLES**:
1. **Signal quantification first** - Every adverse event must have PRR/ROR/IC with confidence intervals
2. **Serious events priority** - Deaths, hospitalizations, life-threatening events always analyzed first
3. **Multi-source triangulation** - FAERS + FDA labels + OpenTargets + DrugBank + literature
4. **Context-aware assessment** - Distinguish drug-specific vs class-wide vs confounding signals
5. **Report-first approach** - Create report file FIRST, update progressively
6. **Evidence grading mandatory** - T1 (regulatory/boxed warning) through T4 (computational)
7. **English-first queries** - Always use English drug names in tool calls, respond in user's language

**REASONING STRATEGY — Start Here**:
Start with the signal: What adverse event was reported more than expected? (PRR >= 2.0, N >= 3, lower CI > 1.0 is the threshold). Then ask three questions in order:
1. **Biologically plausible?** Given the drug's mechanism of action and targets, does this adverse event make sense? An off-target kinase inhibitor causing cardiac events is plausible; a topical agent causing systemic toxicity needs more scrutiny. LOOK UP DON'T GUESS — use `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` and `drugbank_get_targets_by_drug_name_or_drugbank_id` to check targets before asserting plausibility.
2. **Timing consistent?** Acute reactions (within hours/days) suggest immune or direct pharmacologic mechanism. Delayed reactions (weeks/months) suggest cumulative toxicity or idiosyncratic response. Check FAERS time-to-onset distribution.
3. **Could confounders explain it?** Patients taking this drug likely have the underlying disease — compare against background rate in that population, not the general population. Class-wide signals (appearing for all drugs in the class) suggest mechanism-based rather than molecule-specific toxicity.

**Causality Assessment — Naranjo Algorithm Reasoning**:
When determining whether an adverse event is drug-caused (not just associated), apply these steps systematically. LOOK UP DON'T GUESS — search FAERS and FDA labels for each criterion:
1. **Prior reports?** Are there previous conclusive reports of this reaction? Check FDA label (`FDA_get_adverse_reactions_by_drug_name`) and literature (`PubMed_search_articles`). Yes = +1.
2. **Temporal relationship?** Did the AE appear after drug administration? Onset within expected pharmacokinetic window (1-5 half-lives) = +2. Use `FAERS_stratify_by_demographics` for time-to-onset data.
3. **Dechallenge?** Did the AE improve when the drug was stopped? Positive dechallenge = +1. Look for rechallenge/dechallenge case reports in literature.
4. **Rechallenge?** Did the AE reappear when the drug was restarted? Positive rechallenge = +2 (strongest single piece of evidence for causality).
5. **Alternative causes?** Could the underlying disease, concomitant drugs, or other factors explain the AE? Check `drugbank_get_drug_interactions_by_drug_name_or_id` for interacting drugs.
6. **Dose-response?** Did the reaction worsen with higher doses or improve with lower doses? Dose-dependent AEs suggest on-target toxicity.
7. **Drug level confirmation?** Was the drug detected in body fluids at toxic concentrations?
- Score: Definite (>=9), Probable (5-8), Possible (1-4), Doubtful (<=0).
- Even without individual patient data, you can estimate causality from aggregate FAERS signals + label evidence + mechanistic plausibility.

**Reference files** (in this directory):
- `PHASE_DETAILS.md` - Detailed tool calls, code examples, and output templates per phase
- `REPORT_TEMPLATE.md` - Full report template and completeness checklist
- `TOOL_REFERENCE.md` - Tool parameter reference and fallback chains
- `QUICK_START.md` - Quick examples and common drug names

---

## When to Use

Apply when user asks:
- "What are the safety signals for [drug]?"
- "Detect adverse events for [drug]"
- "Is [drug] associated with [adverse event]?"
- "What are the FAERS signals for [drug]?"
- "Compare safety of [drug A] vs [drug B] for [adverse event]"
- "What are the serious adverse events for [drug]?"
- "Are there emerging safety signals for [drug]?"
- "Post-market surveillance report for [drug]"
- "Pharmacovigilance signal detection for [drug]"

**Differentiation from tooluniverse-pharmacovigilance**: This skill focuses specifically on **signal detection and quantification** using disproportionality analysis (PRR, ROR, IC) with statistical rigor, produces a quantitative **Safety Signal Score (0-100)**, and performs **comparative safety analysis** across drug classes.

---

## Workflow Overview

```
Phase 0: Input Parsing & Drug Disambiguation
  Parse drug name, resolve to ChEMBL ID, DrugBank ID
  Identify drug class, mechanism, and approved indications
    |
Phase 1: FAERS Adverse Event Profiling
  Top adverse events by frequency
  Seriousness and outcome distributions
  Demographics (age, sex, country)
    |
Phase 2: Disproportionality Analysis (Signal Detection)
  Calculate PRR, ROR, IC with 95% CI for each AE
  Apply signal detection criteria
  Classify signal strength (Strong/Moderate/Weak/None)
    |
Phase 3: FDA Label Safety Information
  Boxed warnings, contraindications
  Warnings and precautions, adverse reactions
  Drug interactions, special populations
    |
Phase 4: Mechanism-Based Adverse Event Context
  Target-based AE prediction (OpenTargets safety)
  Off-target effects, ADMET predictions
  Drug class effects comparison
    |
Phase 5: Comparative Safety Analysis
  Compare to drugs in same class
  Identify unique vs class-wide signals
  Head-to-head disproportionality comparison
    |
Phase 6: Drug-Drug Interactions & Risk Factors
  Known DDIs causing AEs
  Pharmacogenomic risk factors (PharmGKB)
  FDA PGx biomarkers
    |
Phase 7: Literature Evidence
  PubMed safety studies, case reports
  OpenAlex citation analysis
  Preprint emerging signals (EuropePMC)
    |
Phase 8: Risk Assessment & Safety Signal Score
  Calculate Safety Signal Score (0-100)
  Evidence grading (T1-T4) for each signal
  Clinical significance assessment
    |
Phase 9: Report Synthesis & Recommendations
  Monitoring recommendations
  Risk mitigation strategies
  Completeness checklist
```

---

## Phase Summaries

### Phase 0: Input Parsing & Drug Disambiguation
Resolve drug name to ChEMBL ID, DrugBank ID. Get mechanism of action, blackbox warning status, targets, and approved indications.
- **Tools**: `OpenTargets_get_drug_chembId_by_generic_name`, `OpenTargets_get_drug_mechanisms_of_action_by_chemblId`, `OpenTargets_get_drug_blackbox_status_by_chembl_ID`, `drugbank_get_safety_by_drug_name_or_drugbank_id`, `drugbank_get_targets_by_drug_name_or_drugbank_id`, `OpenTargets_get_drug_indications_by_chemblId`

### Phase 1: FAERS Adverse Event Profiling
Query FAERS for top adverse events, seriousness distribution, outcomes, demographics, and death-related events. Filter serious events by type (death, hospitalization, life-threatening). Get MedDRA hierarchy rollup.
- **Tools**: `FAERS_count_reactions_by_drug_event`, `FAERS_count_seriousness_by_drug_event`, `FAERS_count_outcomes_by_drug_event`, `FAERS_count_patient_age_distribution`, `FAERS_count_death_related_by_drug`, `FAERS_count_reportercountry_by_drug_event`, `FAERS_filter_serious_events`, `FAERS_rollup_meddra_hierarchy`

### Phase 2: Disproportionality Analysis (Signal Detection)
**CRITICAL PHASE**. For each top adverse event (at least 15-20), calculate PRR, ROR, IC with 95% CI. Classify signal strength. Stratify strong signals by demographics.
- **Tools**: `FAERS_calculate_disproportionality`, `FAERS_stratify_by_demographics`
- **MedDRA term level note**: `FAERS_count_reactions_by_drug_event` filters by MedDRA Lowest Level Term (`reactionmeddraverse`) while `FAERS_calculate_disproportionality` uses Preferred Terms. Case counts can differ dramatically — always use disproportionality analysis as the primary signal metric, not raw counts.
- **Signal criteria**: PRR >= 2.0 AND lower CI > 1.0 AND N >= 3
- **Strength**: Strong (PRR >= 5), Moderate (PRR 3-5), Weak (PRR 2-3)
- See `PHASE_DETAILS.md` for full signal classification table

### Phase 3: FDA Label Safety Information
Extract boxed warnings, contraindications, warnings/precautions, adverse reactions, drug interactions, and special population info. Note: `{error: {code: "NOT_FOUND"}}` is normal when a section does not exist.
- **Tools**: `FDA_get_boxed_warning_info_by_drug_name`, `FDA_get_contraindications_by_drug_name`, `FDA_get_warnings_by_drug_name`, `FDA_get_adverse_reactions_by_drug_name`, `FDA_get_drug_interactions_by_drug_name`, `FDA_get_pregnancy_or_breastfeeding_info_by_drug_name`, `FDA_get_geriatric_use_info_by_drug_name`, `FDA_get_pediatric_use_info_by_drug_name`, `FDA_get_pharmacogenomics_info_by_drug_name`

### Phase 4: Mechanism-Based Adverse Event Context
Get target safety profile, OpenTargets adverse events, ADMET toxicity predictions (if SMILES available), and drug warnings.
- **Tools**: `OpenTargets_get_target_safety_profile_by_ensemblID`, `OpenTargets_get_drug_adverse_events_by_chemblId`, `ADMETAI_predict_toxicity`, `ADMETAI_predict_CYP_interactions`, `OpenTargets_get_drug_warnings_by_chemblId`

### Phase 5: Comparative Safety Analysis
Head-to-head comparison with class members using `FAERS_compare_drugs`. Aggregate class AEs. Identify class-wide vs drug-specific signals.
- **Tools**: `FAERS_compare_drugs`, `FAERS_count_additive_adverse_reactions`, `FAERS_count_additive_seriousness_classification`

### Phase 6: Drug-Drug Interactions & Risk Factors
Extract DDIs from FDA label, DrugBank, and DailyMed. Query PharmGKB for pharmacogenomic risk factors and dosing guidelines. Check FDA PGx biomarkers.
- **Tools**: `FDA_get_drug_interactions_by_drug_name`, `drugbank_get_drug_interactions_by_drug_name_or_id`, `DailyMed_parse_drug_interactions`, `PharmGKB_search_drugs`, `PharmGKB_get_drug_details`, `PharmGKB_get_dosing_guidelines`, `fda_pharmacogenomic_biomarkers`

### Phase 7: Literature Evidence
Search PubMed, OpenAlex, and EuropePMC for safety studies, case reports, and preprints.
- **Tools**: `PubMed_search_articles`, `openalex_search_works`, `EuropePMC_search_articles`

### Phase 8: Risk Assessment & Safety Signal Score
Calculate Safety Signal Score (0-100) from four components: FAERS signal strength (0-35), serious AEs (0-30), FDA label warnings (0-25), literature evidence (0-10). Grade each signal T1-T4. See `PHASE_DETAILS.md` for scoring rubric.

### Phase 9: Report Synthesis
Generate comprehensive markdown report with executive summary, all phase outputs, monitoring recommendations, risk mitigation strategies, patient counseling points, and completeness checklist. See `REPORT_TEMPLATE.md` for full template.

---

## Edge Cases

- **No FAERS reports**: Skip Phases 1-2; rely on FDA label, mechanism predictions, literature
- **Generic vs Brand name**: Try both in FAERS; use `OpenTargets_get_drug_chembId_by_generic_name` to resolve
- **Drug combinations**: Use `FAERS_count_additive_adverse_reactions` for aggregate class analysis
- **Confounding by indication**: Compare AE profile to the disease being treated; note limitation in report
- **Drugs with boxed warnings**: Score component automatically 25/25 for label warnings; prioritize boxed warning events


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
