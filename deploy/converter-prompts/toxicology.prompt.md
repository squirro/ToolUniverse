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
- AOPWiki_list_aops signature={'properties': {}, 'type': 'object'}
- AOPWiki_get_aop signature={'properties': {'aop_id': {'description': 'AOP numeric identifier. Find IDs using AOPWiki_list_aops. Example: 3 (mitochondrial complex I inhibition leading to parkinsonian motor deficits).', 'required': True, 'type': 'integer'}}, 'required': ['aop_id'], 'type': 'object'}
- FAERS_count_reactions_by_drug_event signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}, 'occurcountry': {'description': "Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.", 'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'reactionmeddraverse': {'description': 'Optional: Filter by MedDRA reaction term (Lowest Level Term). When omitted, returns all adverse reactions with their counts. When specified, filters results to only include that specific reaction term.', 'required': False, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'seriousnessdeath': {'description': "Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit this parameter to include all reports regardless of death outcome.", 'enum': ['Yes'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- FAERS_calculate_disproportionality signature={'properties': {'adverse_event': {'description': 'MedDRA Preferred Term (e.g., \'Hepatotoxicity\', \'Myopathy\'). Use exact MedDRA Preferred Term capitalization (e.g., "Haemorrhage" not "hemorrhage").', 'required': False, 'type': 'string'}, 'drug': {'description': 'Alias for drug_name. Generic drug name.', 'required': False, 'type': 'string'}, 'drug_name': {'description': "Generic drug name (e.g., 'IBUPROFEN', 'ATORVASTATIN')", 'required': False, 'type': 'string'}, 'operation': {'const': 'calculate_disproportionality', 'description': 'Operation type (fixed)', 'required': False}, 'reaction': {'description': 'Alias for adverse_event. MedDRA Preferred Term for the adverse drug reaction.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- DailyMed_parse_adverse_reactions signature={'properties': {'drug_name': {'description': 'Drug name for automatic Set ID lookup (alternative to setid)', 'required': False, 'type': 'string'}, 'operation': {'const': 'parse_adverse_reactions', 'description': 'Operation type (fixed)', 'required': False}, 'setid': {'description': 'SPL Set ID to parse', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- CTD_get_chemical_gene_interactions signature={'properties': {'input_terms': {'description': "Chemical name, MeSH name, synonym, CAS RN, or MeSH ID. Examples: 'bisphenol A', 'acetaminophen', 'D000082' (MeSH ID for acetaminophen).", 'required': True, 'type': 'string'}}, 'required': ['input_terms'], 'type': 'object'}
- CTD_get_chemical_diseases signature={'properties': {'input_terms': {'description': "Chemical name, MeSH name, synonym, CAS RN, or MeSH ID. Examples: 'arsenic', 'bisphenol A', 'C006780'.", 'required': True, 'type': 'string'}}, 'required': ['input_terms'], 'type': 'object'}
- PubChem_get_CID_by_compound_name signature={'properties': {'compound_name': {'description': 'Alias for name. The compound name to look up.', 'required': False, 'type': 'string'}, 'name': {'description': 'Chemical compound name (e.g., "Aspirin", "Acetaminophen") or IUPAC name. Do not use disease names or medical conditions.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_search_drugs signature={'properties': {'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'max_phase': {'description': 'Filter by maximum development phase (0-4)', 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Filter by ChEMBL molecule ID (e.g., "CHEMBL1201581" for adalimumab).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'query': {'description': 'Drug name to search for (partial match, case-insensitive). E.g., "sotorasib", "olaparib", "imatinib".', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- DailyMed_parse_contraindications signature={'properties': {'drug_name': {'description': 'Drug name for automatic Set ID lookup (alternative to setid)', 'required': False, 'type': 'string'}, 'operation': {'const': 'parse_contraindications', 'description': 'Operation type (fixed)', 'required': False}, 'setid': {'description': 'SPL Set ID to parse', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- DailyMed_parse_clinical_pharmacology signature={'properties': {'drug_name': {'description': 'Drug name for automatic Set ID lookup (alternative to setid)', 'required': False, 'type': 'string'}, 'operation': {'const': 'parse_clinical_pharmacology', 'description': 'Operation type (fixed)', 'required': False}, 'setid': {'description': 'SPL Set ID to parse', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- DailyMed_parse_drug_interactions signature={'properties': {'drug_name': {'description': 'Drug name for automatic Set ID lookup (alternative to setid)', 'required': False, 'type': 'string'}, 'operation': {'const': 'parse_drug_interactions', 'description': 'Operation type (fixed)', 'required': False}, 'setid': {'description': 'SPL Set ID to parse', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- OpenFDA_search_drug_events signature={'properties': {'adverse_event': {'description': 'Alias for reaction. MedDRA adverse reaction term (British spelling).', 'required': False, 'type': ['string', 'null']}, 'count': {'description': "Field to count by for frequency analysis (e.g., 'patient.reaction.reactionmeddrapt.exact' to get most common reactions)", 'required': False, 'type': ['string', 'null']}, 'drug_name': {'description': "Drug name to search for adverse events (e.g., 'warfarin', 'metformin'). Alternative to writing a full Lucene 'search' query.", 'required': False, 'type': ['string', 'null']}, 'limit': {'description': 'Maximum number of reports to return (default 1, max 100)', 'required': False, 'type': ['integer', 'null']}, 'reaction': {'description': "MedDRA adverse reaction term (British spelling: 'haemorrhage' not 'hemorrhage', 'haematoma' not 'hematoma'). Used with drug_name to filter by reaction.", 'required': False, 'type': ['string', 'null']}, 'search': {'description': 'Lucene query for adverse event reports. Use AND/OR with spaces (not +AND+). Examples: \'patient.drug.medicinalproduct:aspirin\', \'patient.reaction.reactionmeddrapt:"myocardial infarction"\', \'serious:1 AND patient.drug.medicinalproduct:warfarin\'. Combine drugs: \'patient.drug.medicinalproduct:metformin AND patient.drug.medicinalproduct:atorvastatin\'.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- aop_id
- drug_name
- reaction_meddra_pt
- serious_type
- input_terms

# TARGET SKILL TO CONVERT
---
name: tooluniverse-toxicology
description: Drug and chemical toxicity assessment via adverse outcome pathways (AOPs), real-world FAERS adverse event signals, FDA labels, and toxicogenomic associations. Triangulates molecular initiating event to cellular outcome to organ-level toxicity to clinical adverse event. Use for hepatotoxicity/cardiotoxicity/nephrotoxicity prediction and toxicology reports.
disable-model-invocation: true
---

# Toxicology Assessment via Adverse Outcome Pathways & Signal Detection

Systematic toxicology analysis that links molecular initiating events (MIEs) through adverse outcome
pathways (AOPs) to apical adverse outcomes, then triangulates with real-world FAERS signals, FDA
label data, and toxicogenomic associations.

## Domain Reasoning

Toxicity has many mechanisms, and the first interpretive question is temporal: is this acute toxicity (immediate effect from a high dose) or chronic toxicity (cumulative damage from long-term low-dose exposure)? Acute and chronic toxicity operate through different mechanisms — acute hepatotoxicity may reflect direct mitochondrial damage, while chronic hepatotoxicity may involve fibrosis from repeated low-level inflammation. They also have different regulatory frameworks: acute toxicity is captured by LD50 and emergency protocols, while chronic toxicity requires long-term carcinogenicity and repeat-dose studies.

## LOOK UP DON'T GUESS

- Adverse outcome pathways for a chemical: query `AOPWiki_list_aops` and `AOPWiki_get_aop`; do not describe mechanisms from memory.
- FAERS adverse event signals: retrieve from `FAERS_count_reactions_by_drug_event` and `FAERS_calculate_disproportionality`; never estimate PRR values.
- FDA label warnings: call `DailyMed_parse_adverse_reactions` and related tools; do not state boxed warnings from memory.
- CTD chemical-gene and chemical-disease associations: query `CTD_get_chemical_gene_interactions` and `CTD_get_chemical_diseases`; do not infer gene targets without database evidence.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use This Skill

**Triggers**:
- "What are the toxicity mechanisms for [drug/chemical]?"
- "Find adverse outcome pathways for [chemical]"
- "What AOPs are relevant to [target/organ/effect]?"
- "FAERS signal analysis for [drug]"
- "Toxicogenomic profile for [chemical]"
- "What is the mechanism of hepatotoxicity / cardiotoxicity / neurotoxicity for [drug]?"

**Use Cases**:
1. **AOP Tracing**: Map chemical MIE through key events to apical outcome using AOPWiki
2. **Real-World Signal Detection**: Quantify FAERS adverse event signals with PRR/ROR
3. **Label Safety Mining**: Extract FDA boxed warnings, contraindications, nonclinical toxicology
4. **Toxicogenomics**: Chemical-gene-disease associations from CTD
5. **Integrated Mechanism Report**: Combine AOP pathway + real-world signals into unified narrative

---

## KEY PRINCIPLES

1. **AOP-first thinking** - Frame all toxicity in terms of MIE → Key Events → Adverse Outcome
2. **Report-first approach** - Create report file FIRST, update progressively
3. **Evidence grading mandatory** - T1 (regulatory/clinical) through T4 (computational/AOP annotation)
4. **Distinguish mechanism from signal** - AOPWiki = mechanism; FAERS = real-world signal
5. **Disambiguation first** - Resolve drug/chemical identity before any queries
6. **English-first queries** - Always use English names in tool calls

---

## Evidence Grading

| Tier | Symbol | Criteria |
|------|--------|----------|
| T1 | [T1] | FDA boxed warning, clinical trial toxicity finding, regulatory label |
| T2 | [T2] | FAERS signal PRR > 2, AOP with high biological plausibility, CTD curated |
| T3 | [T3] | CTD inferred association, AOP annotation with moderate plausibility |
| T4 | [T4] | Text-mined CTD entry, early-stage AOP annotation |

---

## Workflow Overview

```
Chemical/Drug Query
|
+-- PHASE 0: Disambiguation
|   Resolve name -> identifiers (ChEMBL, PubChem CID, SMILES)
|
+-- PHASE 1: Adverse Outcome Pathway Mapping (AOPWiki)
|   List AOPs by keyword; retrieve key events, MIEs, and biological plausibility scores
|
+-- PHASE 2: Real-World Adverse Event Signals (FAERS)
|   Top reactions by drug; disproportionality (PRR); serious event filter
|
+-- PHASE 3: FDA Label Safety Mining
|   Boxed warnings, contraindications, nonclinical toxicology, adverse reactions
|
+-- PHASE 4: Toxicogenomics (CTD)
|   Chemical-gene interactions; chemical-disease associations
|
+-- SYNTHESIS: Integrated Toxicology Report
    AOP-linked mechanism + FAERS signal + CTD gene targets + Risk classification
```

---

## Phase 0: Disambiguation

**Objective**: Establish compound identity before any database queries.

Tools:
- `PubChem_get_CID_by_compound_name` (`name`: str) — get CID + SMILES
- `ChEMBL_search_drugs` (`query`: str) — get ChEMBL ID and max phase

Capture: generic name, SMILES, PubChem CID, ChEMBL ID, drug class.

---

## Phase 1: Adverse Outcome Pathway Mapping

**Objective**: Find AOPs relevant to the chemical's known or suspected toxicity mechanisms.

### Tools

**AOPWiki_list_aops**:
- **Input**: `keyword` (str) — e.g., organ ("liver", "kidney"), effect ("apoptosis", "inflammation"), or target ("AhR", "PPARalpha")
- **Output**: List of AOP IDs, titles, and short descriptions
- **Use**: Discovery scan to identify candidate AOPs

**AOPWiki_get_aop**:
- **Input**: `aop_id` (int) — ID from list_aops result
- **Output**: Full AOP details including MIE, key events (KEs), key event relationships (KERs), biological plausibility, and weight-of-evidence
- **Use**: Retrieve mechanistic pathway details for selected AOPs

### Workflow

1. Query `AOPWiki_list_aops` with organ-level keyword (e.g., "hepatotoxicity", "nephrotoxicity")
2. Query again with mechanism-level keyword (e.g., "oxidative stress", "mitochondria")
3. Select top 3-5 most relevant AOPs by title relevance
4. Call `AOPWiki_get_aop` for each selected AOP
5. Extract: MIE (molecular initiating event), key events in order, apical adverse outcome, biological plausibility score

### Decision Logic

- **AOP found**: Extract full pathway; note plausibility level (high/moderate/low)
- **No direct AOP match**: Try broader organ or mechanism terms; document as "no AOP directly mapped"
- **Multiple AOPs**: Report all; highlight shared key events as high-confidence mechanisms

### AOP Table Format

| AOP ID | Title | MIE | Apical Outcome | Plausibility |
|--------|-------|-----|----------------|-------------|
| 123 | ... | ... | ... | High |

---

## Phase 2: Real-World Adverse Event Signals (FAERS)

**Objective**: Quantify observed adverse events with statistical signal measures.

### Tools

**FAERS_count_reactions_by_drug_event**:
- **Input**: `drug_name` (str), `limit` (int, default 50)
- **Output**: Top adverse reactions with counts
- **Note**: param is `drug_name` not `drug`

**FAERS_calculate_disproportionality**:
- **Input**: `drug_name` (str), `reaction_meddra_pt` (str)
- **Output**: PRR, ROR, IC with confidence intervals

**FAERS_filter_serious_events**:
- **Input**: `drug_name` (str), `serious_type` (str: "death", "hospitalization", "life-threatening")
- **Output**: Serious event count and case details

**FAERS_stratify_by_demographics**:
- **Input**: `drug_name` (str), `reaction_meddra_pt` (str)
- **Output**: Age/sex breakdown for specific reaction

### Workflow

1. Get top 25 reactions via `FAERS_count_reactions_by_drug_event`
2. Filter to organ-system clusters matching the AOP outcomes from Phase 1
3. Calculate PRR for top 10 reactions via `FAERS_calculate_disproportionality`
4. Check serious events (deaths, hospitalizations) for highest-PRR reactions

### Signal Thresholds

| Signal Strength | PRR | Case Count |
|----------------|-----|------------|
| Strong | > 3.0 | >= 5 |
| Moderate | 2.0-3.0 | >= 3 |
| Weak | 1.5-2.0 | >= 3 |
| None | < 1.5 | any |

---

## Phase 3: FDA Label Safety Mining

**Objective**: Extract regulatory safety findings from approved drug labels.

### Tools

- `DailyMed_parse_adverse_reactions` (`drug_name`: str)
- `DailyMed_parse_contraindications` (`drug_name`: str)
- `DailyMed_parse_clinical_pharmacology` (`drug_name`: str)
- `DailyMed_parse_drug_interactions` (`drug_name`: str)

**Note**: These tools apply to FDA-approved drugs only. Environmental chemicals will have no label data — document explicitly.

### Workflow

1. Extract adverse reactions and note which match FAERS signals
2. Extract contraindications (highest evidence tier [T1])
3. Note pharmacological mechanism from clinical pharmacology section

---

## Phase 4: Toxicogenomics (CTD)

**Objective**: Map chemical-gene interactions and chemical-disease associations.

### Tools

**CTD_get_chemical_gene_interactions**:
- **Input**: `input_terms` (str) — chemical name or MeSH ID
- **Output**: Gene targets with interaction type (increases/decreases expression)
- **Use**: Find molecular targets mediating toxicity

**CTD_get_chemical_diseases**:
- **Input**: `input_terms` (str) — chemical name or MeSH ID
- **Output**: Disease associations with evidence type (curated/inferred)
- **Use**: Find downstream disease endpoints

### Workflow

1. Query CTD with compound name; note curated (higher confidence) vs inferred entries
2. Cross-reference gene targets with Phase 1 AOP key events
3. Note which CTD disease endpoints match AOP apical outcomes

---

## Synthesis: Integrated Toxicology Report

**Structure**:

```
# Toxicology Report: [Compound Name]
**Generated**: YYYY-MM-DD

## Executive Summary
Risk tier: CRITICAL / HIGH / MEDIUM / LOW / INSUFFICIENT DATA
Key finding summary (2-3 sentences)

## 1. Compound Identity
(disambiguation table)

## 2. Adverse Outcome Pathways [T3-T4]
(AOP table; pathway diagrams in text form)

## 3. Real-World Adverse Event Signals [T1-T2]
(FAERS top reactions + PRR table + serious events)

## 4. FDA Label Safety [T1]
(boxed warnings, contraindications, adverse reactions)

## 5. Toxicogenomics [T2-T4]
(CTD gene targets + disease associations)

## 6. Mechanistic Integration
(How AOP key events map to observed FAERS signals and CTD gene targets)

## 7. Risk Classification
(Final tier with rationale)

## Data Gaps & Limitations
(Missing data, confidence caveats)
```

### Risk Classification

| Tier | Criteria |
|------|----------|
| CRITICAL | FDA boxed warning OR FAERS PRR > 5 with deaths OR multiple T1 findings |
| HIGH | FAERS PRR 3-5 serious events OR FDA warning (non-boxed) OR high-plausibility AOP |
| MEDIUM | FAERS PRR 2-3 OR CTD curated associations OR moderate-plausibility AOP |
| LOW | All signals < PRR 2; no regulatory warnings; low-plausibility AOP only |
| INSUFFICIENT DATA | Fewer than 3 phases returned usable data |

---

## Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `AOPWiki_list_aops` | Broaden keyword | Search by organ system |
| `FAERS_count_reactions_by_drug_event` | `OpenFDA_search_drug_events` | Literature search |
| `DailyMed_parse_adverse_reactions` | `OpenFDA_search_drug_events` | FAERS serious events |
| `CTD_get_chemical_diseases` | `CTD_get_chemical_gene_interactions` | PubMed search |

---

## Tool Parameter Reference (Critical)

| Tool | WRONG | CORRECT |
|------|-------|---------|
| `FAERS_count_reactions_by_drug_event` | `drug` | `drug_name` |
| `AOPWiki_list_aops` | `query` | `keyword` |
| `CTD_get_chemical_gene_interactions` | `chemical` | `input_terms` |
| `CTD_get_chemical_diseases` | `chemical` | `input_terms` |

---

## Limitations

- **AOPWiki**: AOPs are in development; many lack high plausibility scores
- **FAERS**: Observational data; confounding by indication; underreporting bias
- **CTD**: Inferred associations have high false-positive rate
- **DailyMed**: FDA-approved drugs only; no environmental chemical coverage
- **Environmental chemicals**: Primarily Phase 1 (AOP) + Phase 4 (CTD) data available

---

## References

- AOPWiki: https://aopwiki.org
- FAERS: https://www.fda.gov/drugs/questions-and-answers-fdas-adverse-event-reporting-system-faers
- CTD: http://ctdbase.org
- DailyMed: https://dailymed.nlm.nih.gov
- OpenFDA: https://open.fda.gov


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
