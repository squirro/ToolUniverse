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
- UniProt_get_entry_by_accession signature={'properties': {'accession': {'description': 'UniProtKB entry accession, e.g., P05067.', 'required': True, 'type': 'string'}, 'compact': {'default': True, 'description': 'Return a bounded summary instead of the complete UniProtKB JSON entry. Defaults to true to avoid oversized LLM outputs. Set compact=false only when you explicitly need the raw UniProtKB JSON.', 'required': False, 'type': 'boolean'}}, 'required': ['accession'], 'type': 'object'}
- DGIdb_get_drug_gene_interactions signature={'properties': {'gene': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'genes': {'description': "List of gene symbols (e.g., ['EGFR', 'BRAF']). Also accepts a single gene as string. Aliases: gene_name, gene.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_sources': {'description': "Optional filter by data sources (e.g., ['DrugBank', 'ChEMBL']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_types': {'description': "Optional filter by interaction types (e.g., ['inhibitor', 'antagonist']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- ChEMBL_search_drugs signature={'properties': {'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'max_phase': {'description': 'Filter by maximum development phase (0-4)', 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Filter by ChEMBL molecule ID (e.g., "CHEMBL1201581" for adalimumab).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'query': {'description': 'Drug name to search for (partial match, case-insensitive). E.g., "sotorasib", "olaparib", "imatinib".', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_drug_mechanisms signature={'properties': {'chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL ID (e.g., "CHEMBL3301622").', 'required': False, 'type': 'string'}, 'drug_chembl_id': {'description': 'ChEMBL drug/molecule ID (e.g., "CHEMBL1201581" for adalimumab, "CHEMBL4535757" for sotorasib).', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Drug name for automatic ChEMBL ID lookup (e.g., "trastuzumab", "lapatinib", "aspirin"). Case-insensitive. Triggers internal ChEMBL molecule search â\x80\x94 use drug_chembl_id if you already know the ID.', 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL molecule ID (e.g., "CHEMBL25" for aspirin).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- FDA_get_warnings_and_cautions_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FAERS_search_reports_by_drug_and_reaction signature={'properties': {'limit': {'default': 10, 'description': 'Maximum number of reports to return. Must be between 1 and 100.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'medicinalproduct': {'description': 'Drug name (required).', 'required': True, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'reactionmeddrapt': {'description': "MedDRA preferred term for the adverse reaction (required). Example: 'INFUSION RELATED REACTION', 'DYSPNOEA'.", 'required': True, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'skip': {'default': 0, 'description': 'Number of reports to skip for pagination. Must be non-negative.', 'minimum': 0, 'required': False, 'type': 'integer'}}, 'required': ['medicinalproduct', 'reactionmeddrapt'], 'type': 'object'}
- FAERS_count_death_related_by_drug signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- ADMETAI_predict_physicochemical_properties signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_toxicity signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ReactomeAnalysis_pathway_enrichment signature={'properties': {'identifiers': {'description': "Newline-separated list of gene/protein identifiers. Supports gene symbols (TP53, BRCA1), UniProt IDs (P04637, P38398), or Ensembl IDs. Example: 'TP53\\nBRCA1\\nCDH1\\nEGFR\\nKRAS'.", 'required': True, 'type': 'string'}, 'include_disease': {'description': 'Include disease pathways in results (default true).', 'required': False, 'type': ['boolean', 'null']}, 'page_size': {'description': 'Number of pathways to return (default 20, max 50).', 'required': False, 'type': ['integer', 'null']}, 'projection': {'description': 'Project identifiers to human Reactome pathways for cross-species analysis (default true).', 'required': False, 'type': ['boolean', 'null']}}, 'required': ['identifiers'], 'type': 'object'}
- STRING_get_network signature={'properties': {'identifiers': {'description': "Protein identifier(s). For multiple proteins, separate with '\\r' (carriage return character). Examples: 'TP53', 'BRCA1\\rBRCA2\\rTP53', '9606.ENSP00000269305'", 'required': True, 'type': 'string'}, 'limit': {'default': 10, 'description': 'Maximum number of interaction partners to include (per protein). 0 = only interactions among input proteins.', 'required': False, 'type': 'integer'}, 'required_score': {'description': 'Minimum combined STRING score (0-1000). 400=medium, 700=high, 900=highest confidence. Default: 400.', 'required': False, 'type': ['integer', 'null']}, 'species': {'default': 9606, 'description': 'NCBI taxonomy ID. Examples: 9606 (human), 10090 (mouse), 7227 (Drosophila), 6239 (C. elegans)', 'required': False, 'type': 'integer'}}, 'required': ['identifiers'], 'type': 'object'}
- CTD_get_gene_diseases signature={'properties': {'gene_symbol': {'description': 'Gene symbol (alias for input_terms, e.g. TP53)', 'required': False, 'type': 'string'}, 'input_terms': {'description': "Gene symbol or NCBI Gene ID. Examples: 'TP53', 'BRCA1', 'CYP1A1', '7157' (Gene ID for TP53).", 'required': False, 'type': 'string'}, 'query': {'description': 'Gene symbol or name to search (alias for input_terms, e.g. TP53)', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- EuropePMC_search_articles signature={'properties': {'enrich_missing_abstract': {'default': False, 'description': 'If true, best-effort fills missing abstracts by fetching Europe PMC fullTextXML (bounded to a few results).', 'required': False, 'type': 'boolean'}, 'extract_terms_from_fulltext': {'description': "Optional list of terms to extract from full text (open access only). When provided, automatically fetches fullTextXML for open-access articles and returns snippets around these terms. Terms are processed in batches of 5 internally, so any number of terms is accepted. Bounded to first 3 OA articles to avoid latency. Returns snippets in a 'fulltext_snippets' field for each article.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'fulltext_terms': {'description': 'Optional list of terms that must occur in the indexed full text (Europe PMC BODY field). When provided, the tool adds a BODY:"..." clause and automatically enables `require_has_ft`.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'default': 5, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from Europe PMC.', 'required': False, 'type': 'integer'}, 'page_size': {'description': 'Alias for limit â\x80\x94 number of results to return', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Europe PMC. Supports Lucene-like fielded syntax (e.g., BODY:"term", INTRO:"term", METHODS:"term").', 'required': True, 'type': 'string'}, 'require_has_ft': {'default': False, 'description': 'If true, appends `HAS_FT:Y` to the query to restrict results to records where Europe PMC has full text indexed. This is NOT the same as having a link to free full text elsewhere (e.g., PMC) and is often the key reason body-only keywords cannot be found via Europe PMC search.', 'required': False, 'type': 'boolean'}}, 'required': ['query'], 'type': 'object'}
- search_clinical_trials signature={'properties': {'condition': {'description': 'Query for condition or disease using Essie expression syntax (e.g., \'lung cancer\', \'(head OR neck) AND pain AND NOT "back pain"\'). ', 'required': False, 'type': 'string'}, 'intervention': {'description': "Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').", 'required': False, 'type': 'string'}, 'keyword': {'description': 'Alias for query_term. Free-text keyword search across all trial fields (e.g., drug name, condition, investigator).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Alias for max_results: maximum number of studies to return (default 10, max 1000).', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Maximum number of studies to return (alias for pageSize, default 10, max 1000).', 'required': False, 'type': 'integer'}, 'overall_status': {'description': "Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUITING', 'NOT_YET_RECRUITING']). Valid values: RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED, WITHDRAWN.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'pageSize': {'description': 'Maximum number of studies to return per page (default 10, max 1000).', 'required': False, 'type': 'integer'}, 'pageToken': {'description': "Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.", 'required': False, 'type': 'string'}, 'query_term': {'description': "Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.", 'required': False, 'type': 'string'}, 'status': {'description': 'Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLETED".', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': False}}, 'required': [], 'type': 'object'}
- ADMETAI_predict_BBB_penetrance signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- OpenTargets_get_disease_id_description_by_name
- OpenTargets_get_associated_targets_by_disease_efoId
- drugbank_get_drug_name_and_description_by_target_name
- drugbank_get_drug_name_and_description_by_indication
- drugbank_get_drug_basic_info_by_drug_name_or_id
- drugbank_get_indications_by_drug_name_or_drugbank_id
- drugbank_get_pharmacology_by_drug_name_or_drugbank_id
- drugbank_get_targets_by_drug_name_or_drugbank_id
- drugbank_get_drug_interactions_by_drug_name_or_id
- query_term

# TARGET SKILL TO CONVERT
---
name: tooluniverse-drug-repurposing
description: Identify drug repurposing candidates via target-based, compound-based, and disease-based strategies. Combines drug-target-disease network reasoning with mechanism rationale, clinical-trial precedent, and patent/regulatory feasibility. Use for hypothesis-generating repurposing for orphan diseases, finding existing drugs for new indications, and prioritizing candidates by evidence and feasibility.
disable-model-invocation: true
---

# Drug Repurposing with ToolUniverse

Systematically identify and evaluate drug repurposing candidates using multiple computational strategies.

**IMPORTANT**: Always use English terms in tool calls. Respond in the user's language.

---

## Reasoning Before Searching

Start by asking: WHY might this drug work for a new disease? Three strategies:

- **(a) Same target**: The drug's primary target is also involved in the new disease. This is the strongest hypothesis — use OpenTargets to check if the target has genetic evidence in both diseases before any other search.
- **(b) Off-target activity**: The drug has secondary targets or off-target effects that are relevant to the new disease. Check ChEMBL bioactivity data for all known targets of the drug, not just its primary one.
- **(c) Shared pathways**: The original indication and new disease share molecular pathways, even if the target itself is not genetically linked. Use Reactome and STRING to compare pathway overlap between diseases.

Each strategy uses different tools and has different evidentiary weight. Identify which strategy applies FIRST, then choose the corresponding workflow below. Do not run all three strategies blindly — reason about which is most plausible given the drug's mechanism.

**LOOK UP DON'T GUESS**: Never assume a drug hits a target, never assume a target is disease-relevant, never assume pathway overlap. Verify each link with tool calls.

## Core Strategies

1. **Target-Based**: Disease targets -> Find drugs that modulate those targets
2. **Compound-Based**: Approved drugs -> Find new disease indications
3. **Disease-Driven**: Disease -> Targets -> Match to existing drugs

---

## Workflow Overview

```
Phase 1: Disease & Target Analysis
  Get disease info (OpenTargets), find associated targets, get target details

Phase 2: Drug Discovery
  Search DrugBank, DGIdb, ChEMBL for drugs targeting disease-associated genes
  Get drug details, indications, pharmacology

Phase 3: Safety & Feasibility Assessment
  FDA warnings, FAERS adverse events, drug interactions, ADMET predictions

Phase 4: Literature Evidence
  PubMed, Europe PMC, clinical trials for existing evidence

Phase 5: Scoring & Ranking
  Composite score: target association + safety + literature + drug properties
```

See: PROCEDURES.md for detailed step-by-step procedures and code patterns.

---

## Quick Start

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Step 1: Get disease targets
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="rheumatoid arthritis")
# Response nests ID at data.search.hits[0].id
disease_id = disease_info['data']['search']['hits'][0]['id']
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=disease_id, limit=10)

# Step 2: Find drugs for each target
# Response nests targets at data.disease.associatedTargets.rows
rows = targets['data']['disease']['associatedTargets']['rows']
for target in rows[:5]:
    gene = target['target']['approvedSymbol']
    drugs = tu.tools.DGIdb_get_drug_gene_interactions(genes=[gene])
```

---

## Key ToolUniverse Tools

**Disease & Target**:
- `OpenTargets_get_disease_id_description_by_name` - Disease lookup
- `OpenTargets_get_associated_targets_by_disease_efoId` - Disease targets
- `UniProt_get_entry_by_accession` - Protein details

**Drug Discovery**:
- `drugbank_get_drug_name_and_description_by_target_name` - Drugs by target. **Param: `query=` (NOT `target_name=`)**
- `drugbank_get_drug_name_and_description_by_indication` - Drugs by indication. **Param: `query=` (NOT `indication=`)**
- `DGIdb_get_drug_gene_interactions` - Drug-gene interactions. Response path: `data.data.genes.nodes[0].interactions`
- `ChEMBL_search_drugs` / `ChEMBL_get_drug_mechanisms` - Drug search and MOA

**Drug Information** (ALL DrugBank tools use `query=` as the search parameter, plus `case_sensitive=False`, `exact_match=False`, `limit=N`):
- `drugbank_get_drug_basic_info_by_drug_name_or_id` - Basic info. **Param: `query="drug_name"`**
- `drugbank_get_indications_by_drug_name_or_drugbank_id` - Approved indications. **Param: `query="drug_name"`**
- `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` - Pharmacology. **Param: `query="drug_name"`**
- `drugbank_get_targets_by_drug_name_or_drugbank_id` - Drug targets. **Param: `query="drug_name"`**

**Safety**:
- `FDA_get_warnings_and_cautions_by_drug_name` - FDA warnings
- `FAERS_search_reports_by_drug_and_reaction` - Adverse events. **Param: `medicinalproduct=` (NOT `drug_name=`)**
- `FAERS_count_death_related_by_drug` - Serious outcomes. **Param: `medicinalproduct=` (NOT `drug_name=`)**
- `drugbank_get_drug_interactions_by_drug_name_or_id` - Interactions

**Property Prediction**:
- `ADMETAI_predict_physicochemical_properties` / `ADMETAI_predict_toxicity` - ADMET and toxicity

**Pathway & Network Analysis**:
- `ReactomeAnalysis_pathway_enrichment` - Pathway enrichment. **Param: `identifiers="SOD1\nTARDBP\nFUS"` (newline-separated string, NOT array)**
- `STRING_get_network` - Protein interaction networks. **Param: `identifiers="SOD1\rTARDBP\rFUS"` (CR-separated string), `species=9606`**
- `CTD_get_gene_diseases` - Curated gene-disease associations. **Param: `input_terms="gene_symbol"` (NOT `gene_symbol=`)**

**Literature & Clinical Trials**:
- `PubMed_search_articles` / `EuropePMC_search_articles` - Literature search
- `search_clinical_trials` - ClinicalTrials.gov search. Use `condition` for disease name. The `intervention` filter is strict and may miss trials — use `query_term` for broader drug-name matching as fallback.

> **CNS diseases note**: For neurological indications (ALS, Alzheimer's, Parkinson's), prioritize BBB-penetrant candidates. Use ChEMBL molecular properties (MW < 500, PSA < 90) as BBB proxy since `ADMETAI_predict_BBB_penetrance` may require the `tooluniverse[ml]` extra. Consider route of administration (oral preferred for patients with swallowing difficulty) and sex-specific effects from preclinical models.

---

## Scoring & Decision Framework

### Repurposing Viability Score (0-100)

| Category | Points | How to Score |
|----------|--------|-----------|
| **Target Association** | 0-40 | **40**: Target has genetic evidence in disease (GWAS, rare variants); **25**: Target is in a disease-associated pathway (Reactome, KEGG); **15**: Target is differentially expressed in disease tissue; **5**: Target shares a GO term with disease genes |
| **Safety Profile** | 0-30 | **30**: FDA-approved drug, no black box warning, established safety record; **20**: FDA-approved with manageable warnings; **10**: Phase II+ data, acceptable safety; **0**: Preclinical only or serious safety signals |
| **Literature Evidence** | 0-20 | **20**: Phase II+ trial for the new indication exists; **15**: Case reports or retrospective studies show efficacy; **10**: Preclinical in-vivo evidence (animal models); **5**: In-vitro evidence only; **0**: No prior evidence |
| **Drug Properties** | 0-10 | **10**: Oral, good bioavailability, IP available; **5**: Injectable or narrow therapeutic window; **0**: Poor PK or formulation challenges |

**Classification**:
- **80-100**: Strong candidate — proceed to clinical evaluation
- **60-79**: Promising — worth preclinical validation or retrospective study
- **40-59**: Speculative — needs significant additional evidence
- **<40**: Weak — likely not worth pursuing without new mechanistic insight

### Evidence Grading for Repurposing

| Grade | Definition | Action |
|-------|-----------|--------|
| **E1 (Clinical)** | Existing clinical trial for new indication (any phase) | High priority — check trial results |
| **E2 (Epidemiological)** | Retrospective/observational data showing benefit | Moderate priority — design prospective study |
| **E3 (Preclinical)** | Animal model evidence for new indication | Standard priority — validate mechanism |
| **E4 (Computational)** | Target overlap, network proximity, or molecular similarity only | Low priority — needs experimental validation |

### How to Interpret and Combine Results

After running Phases 1-4, synthesize by answering:

1. **Is the target validated for this disease?** Check OpenTargets association score (>0.5 = strong). Cross-reference with genetic evidence (GWAS hits, rare variant studies). If target association is only pathway-level, the repurposing hypothesis is speculative.

2. **Does the drug actually hit the target at achievable doses?** Check ChEMBL IC50/Ki values. If the drug's affinity for the new target is >10x weaker than for its original target, clinical efficacy is unlikely at safe doses.

3. **What's the safety margin?** Compare the dose needed for the new indication to the approved dose. If higher doses are needed, safety data from the original indication may not apply.

4. **Is there prior clinical evidence?** A Phase II trial for the new indication (even failed) is more informative than 100 computational predictions. Check `search_clinical_trials` first.

5. **What's the competitive landscape?** If better drugs already exist for the disease, repurposing offers little value. Check DrugBank indications for approved therapies.

---

## Best Practices

1. **Check clinical trials FIRST**: `search_clinical_trials(condition="[disease]", intervention="[drug]")` — if a trial already exists, start there
2. **Validate targets with genetics**: Genetic evidence (GWAS, rare variants) is the strongest predictor of successful drug development
3. **Safety first**: Prioritize approved drugs with known safety profiles
4. **Dose matters**: A drug that hits a disease target at 100x its approved dose is not a repurposing candidate
5. **Mechanism over correlation**: Network proximity alone is insufficient — explain WHY the drug should work
6. **Consider IP and formulation**: Generic drugs are easier to repurpose but harder to fund trials for

### Computational Procedure: Drug-Target Dose Feasibility Check

A drug that hits a new target only at 100x its approved dose is NOT a viable repurposing candidate. Use this procedure after identifying drug-target pairs:

```python
# Drug-target dose feasibility analysis
# Uses ChEMBL bioactivity data from ToolUniverse
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

def check_dose_feasibility(drug_name, original_target, new_target):
    """
    Compare drug's potency at original vs new target.
    If new_target IC50 > 10x original_target IC50, flag as unlikely feasible.
    """
    # Get bioactivity for original target
    orig = tu.run_one_function({
        'name': 'ChEMBL_get_bioactivities',
        'arguments': {
            'molecule_chembl_id': drug_name,  # or search first
            'target_chembl_id': original_target,
            'limit': 10
        }
    })

    # Get bioactivity for new target
    new = tu.run_one_function({
        'name': 'ChEMBL_get_bioactivities',
        'arguments': {
            'molecule_chembl_id': drug_name,
            'target_chembl_id': new_target,
            'limit': 10
        }
    })

    # Extract IC50/Ki values and compare
    # If new target requires >10x concentration → NOT FEASIBLE at safe doses
    # If new target is within 3x → PROMISING
    # If new target is within 1x → STRONG candidate
    pass  # Parse actual values from results

# Alternative: Quick Cmax check
# If published Cmax at approved dose < IC50 for new target → NOT FEASIBLE
# Cmax data can be found in:
#   - DrugBank pharmacology section
#   - DailyMed clinical pharmacology section
#   - PubMed PK studies
```

**Key principle**: The most common reason repurposing fails is insufficient drug exposure at the new target. Always check whether the drug's concentration at approved doses reaches the IC50 for the new target.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Disease not found | Try synonyms or EFO ID lookup |
| No drugs for target | Check HUGO nomenclature, expand to pathway-level, try similar targets |
| Insufficient literature | Search drug class instead, check preclinical/animal studies |
| Safety data unavailable | Drug may not be US-approved, check EMA or clinical trial safety |

---

## Reference Files

- **REFERENCE.md** - Detailed reference documentation
- **EXAMPLES.md** - Sample repurposing analyses
- **PROCEDURES.md** - Step-by-step procedures with code
- **REPORT_TEMPLATE.md** - Output report template
- Related skills: disease-intelligence-gatherer, chemical-compound-retrieval, tooluniverse-sdk


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
