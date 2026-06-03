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
- PubChem_get_compound_properties_by_CID signature={'properties': {'cid': {'description': 'PubChem compound ID to query, e.g., 2244 (Aspirin).', 'required': True, 'type': 'integer'}}, 'required': ['cid'], 'type': 'object'}
- ChEMBL_get_molecule_targets signature={'properties': {'limit': {'default': 500, 'description': 'Maximum number of activity records to fetch for target deduplication (default 500).', 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Alias for molecule_chembl_id__exact. ChEMBL molecule ID.', 'required': False, 'type': 'string'}, 'molecule_chembl_id__exact': {'description': "ChEMBL molecule ID (e.g., 'CHEMBL25' for aspirin). To find a molecule ID, use ChEMBL_search_molecules. Alias: molecule_chembl_id.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- PubChem_get_CID_by_compound_name signature={'properties': {'compound_name': {'description': 'Alias for name. The compound name to look up.', 'required': False, 'type': 'string'}, 'name': {'description': 'Chemical compound name (e.g., "Aspirin", "Acetaminophen") or IUPAC name. Do not use disease names or medical conditions.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_search_drugs signature={'properties': {'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'max_phase': {'description': 'Filter by maximum development phase (0-4)', 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Filter by ChEMBL molecule ID (e.g., "CHEMBL1201581" for adalimumab).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'query': {'description': 'Drug name to search for (partial match, case-insensitive). E.g., "sotorasib", "olaparib", "imatinib".', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_search_activities signature={'properties': {'assay_chembl_id': {'description': 'Filter by assay ChEMBL ID', 'required': False, 'type': 'string'}, 'fields': {'description': "Optional list of ChEMBL activity fields to include in each returned activity object (projection). ToolUniverse maps this to ChEMBL's `only` query parameter (comma-separated). Supported fields: activity_id, molecule_chembl_id, target_chembl_id, assay_chembl_id, standard_type, standard_value, standard_units, pchembl_value, standard_relation, standard_flag.", 'items': {'enum': ['activity_id', 'molecule_chembl_id', 'target_chembl_id', 'assay_chembl_id', 'standard_type', 'standard_value', 'standard_units', 'pchembl_value', 'standard_relation', 'standard_flag'], 'type': 'string'}, 'required': False, 'type': 'array', 'uniqueItems': True}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Filter by molecule ChEMBL ID', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'standard_type': {'description': "Filter by activity type (e.g., 'IC50', 'Ki', 'EC50')", 'required': False, 'type': 'string'}, 'standard_value__gte': {'description': 'Filter by minimum activity value', 'required': False, 'type': 'number'}, 'standard_value__lte': {'description': 'Filter by maximum activity value', 'required': False, 'type': 'number'}, 'target_chembl_id': {'description': 'Filter by target ChEMBL ID', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_activity signature={'properties': {'activity_id': {'description': 'ChEMBL activity ID', 'required': True, 'type': 'string'}}, 'required': ['activity_id'], 'type': 'object'}
- PubChemBioAssay_get_assay_summary signature={'properties': {'aid': {'description': 'PubChem BioAssay ID (AID). Examples: 1259393, 504832, 1234.', 'required': True, 'type': 'integer'}}, 'required': ['aid'], 'type': 'object'}
- DailyMed_search_spls signature={'properties': {'drug_name': {'description': "Generic or brand name of the drug, e.g., 'TAMSULOSIN HYDROCHLORIDE'.", 'required': True, 'type': 'string'}, 'ndc': {'description': 'National Drug Code (NDC).', 'required': False, 'type': 'string'}, 'page': {'default': 1, 'description': 'Page number, starts from 1, default 1.', 'required': False, 'type': 'integer'}, 'pagesize': {'default': 100, 'description': 'Number of items per page, maximum 100, default 100.', 'required': False, 'type': 'integer'}, 'published_date_eq': {'description': "Published date == specified date, format 'YYYY-MM-DD'.", 'required': False, 'type': 'string'}, 'published_date_gte': {'description': "Published date >= specified date, format 'YYYY-MM-DD'.", 'required': False, 'type': 'string'}, 'rxcui': {'description': 'RxNorm Code (RXCUI).', 'required': False, 'type': 'string'}, 'setid': {'description': 'Set ID corresponding to the SPL.', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': ['drug_name'], 'type': 'object'}
- PubChemTox_get_acute_effects signature={'properties': {'cid': {'description': 'PubChem Compound ID. Examples: 5359596 (arsenic), 887 (methanol), 702 (ethanol), 241 (benzene).', 'required': False, 'type': ['integer', 'null']}, 'compound_name': {'description': "Compound name (used if cid is not provided). Examples: 'arsenic', 'methanol', 'cyanide', 'chlorine'.", 'required': False, 'type': ['string', 'null']}}, 'required': [], 'type': 'object'}
- PharmGKB_search_drugs signature={'properties': {'drug': {'description': 'Alias for query. Drug name to search.', 'required': False, 'type': 'string'}, 'drug_name': {'description': "Alias for query. Drug name to search (e.g., 'warfarin', 'metformin').", 'required': False, 'type': 'string'}, 'name': {'description': 'Alias for query. Drug name to search.', 'required': False, 'type': 'string'}, 'query': {'description': "Drug name or PharmGKB Chemical ID (e.g., 'warfarin', 'PA452637'). Aliases: drug_name, name, drug.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- PharmGKB_get_dosing_guidelines signature={'properties': {'gene': {'description': "Gene symbol (e.g., 'CYP2D6'). NOTE: Filtering by gene symbol is unreliable and may return a generic prompt instead of actual guidelines. Use guideline_id instead.", 'required': False, 'type': 'string'}, 'guideline_id': {'description': "PharmGKB ClinPGx guideline ID from CPIC_list_guidelines 'clinpgxid' field (e.g., 'PA166251465' for warfarin, 'PA166251454' for opioids/codeine, 'PA166251458' for tamoxifen). Use clinpgxid, NOT pharmgkbid.", 'required': True, 'type': 'string'}}, 'required': ['guideline_id'], 'type': 'object'}
- FAERS_count_reactions_by_drug_event signature={'properties': {'medicinalproduct': {'description': 'Drug name.', 'required': True, 'type': 'string'}, 'occurcountry': {'description': "Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.", 'pattern': '^[A-Z]{2}$', 'required': False, 'type': 'string'}, 'patientagegroup': {'description': "Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.", 'enum': ['Neonate', 'Infant', 'Child', 'Adolescent', 'Adult', 'Elderly'], 'required': False, 'type': 'string'}, 'patientsex': {'description': "Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.", 'enum': ['Male', 'Female'], 'required': False, 'type': 'string'}, 'reactionmeddraverse': {'description': 'Optional: Filter by MedDRA reaction term (Lowest Level Term). When omitted, returns all adverse reactions with their counts. When specified, filters results to only include that specific reaction term.', 'required': False, 'type': 'string'}, 'serious': {'description': "Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.", 'enum': ['Yes', 'No'], 'required': False, 'type': 'string'}, 'seriousnessdeath': {'description': "Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit this parameter to include all reports regardless of death outcome.", 'enum': ['Yes'], 'required': False, 'type': 'string'}}, 'required': ['medicinalproduct'], 'type': 'object'}
- DailyMed_parse_clinical_pharmacology signature={'properties': {'drug_name': {'description': 'Drug name for automatic Set ID lookup (alternative to setid)', 'required': False, 'type': 'string'}, 'operation': {'const': 'parse_clinical_pharmacology', 'description': 'Operation type (fixed)', 'required': False}, 'setid': {'description': 'SPL Set ID to parse', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_target signature={'properties': {'format': {'default': 'json', 'enum': ['json', 'xml', 'yaml'], 'required': False, 'type': 'string'}, 'target_chembl_id': {'description': "ChEMBL target ID (e.g., 'CHEMBL2074'). To find a target ID, use ChEMBL_search_targets with a target name or gene symbol.", 'required': True, 'type': 'string'}}, 'required': ['target_chembl_id'], 'type': 'object'}
- DGIdb_get_drug_info signature={'properties': {'drugs': {'description': 'Drug name(s) to look up. Accepts a single name or a list.', 'oneOf': [{'description': 'Single drug name (e.g., "imatinib").', 'type': 'string'}, {'description': 'List of drug names (e.g., ["imatinib", "erlotinib"]).', 'items': {'type': 'string'}, 'type': 'array'}], 'required': True}}, 'required': ['drugs'], 'type': 'object'}
- search_clinical_trials signature={'properties': {'condition': {'description': 'Query for condition or disease using Essie expression syntax (e.g., \'lung cancer\', \'(head OR neck) AND pain AND NOT "back pain"\'). ', 'required': False, 'type': 'string'}, 'intervention': {'description': "Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').", 'required': False, 'type': 'string'}, 'keyword': {'description': 'Alias for query_term. Free-text keyword search across all trial fields (e.g., drug name, condition, investigator).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Alias for max_results: maximum number of studies to return (default 10, max 1000).', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Maximum number of studies to return (alias for pageSize, default 10, max 1000).', 'required': False, 'type': 'integer'}, 'overall_status': {'description': "Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUITING', 'NOT_YET_RECRUITING']). Valid values: RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED, WITHDRAWN.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'pageSize': {'description': 'Maximum number of studies to return per page (default 10, max 1000).', 'required': False, 'type': 'integer'}, 'pageToken': {'description': "Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.", 'required': False, 'type': 'string'}, 'query_term': {'description': "Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.", 'required': False, 'type': 'string'}, 'status': {'description': 'Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLETED".', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': False}}, 'required': [], 'type': 'object'}
- extract_clinical_trial_outcomes signature={'properties': {'nct_ids': {'description': "List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).", 'items': {'type': 'string'}, 'required': True, 'type': 'array'}, 'outcome_measure': {'description': "Outcome measure to extract. Example values include 'primary' (primary outcomes only), 'secondary' (secondary outcomes only), 'all' (all outcomes), or specific measure names such as 'survival', 'overall survival'. For specific measure names, outcome measures will be matched as long as the input partially matches their titles or descriptions (case agnostic). Querying for specific measure names is recommended after getting an overview of outcome measures ('primary'). If querying for specific measure names does not return any results, this parameter should be set to 'primary' for sanity check. By default, the value is set to 'primary', i.e. the tool will extract all primary outcome results.", 'required': False, 'type': 'string'}}, 'required': ['nct_ids'], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- EuropePMC_search_articles signature={'properties': {'enrich_missing_abstract': {'default': False, 'description': 'If true, best-effort fills missing abstracts by fetching Europe PMC fullTextXML (bounded to a few results).', 'required': False, 'type': 'boolean'}, 'extract_terms_from_fulltext': {'description': "Optional list of terms to extract from full text (open access only). When provided, automatically fetches fullTextXML for open-access articles and returns snippets around these terms. Terms are processed in batches of 5 internally, so any number of terms is accepted. Bounded to first 3 OA articles to avoid latency. Returns snippets in a 'fulltext_snippets' field for each article.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'fulltext_terms': {'description': 'Optional list of terms that must occur in the indexed full text (Europe PMC BODY field). When provided, the tool adds a BODY:"..." clause and automatically enables `require_has_ft`.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'default': 5, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from Europe PMC.', 'required': False, 'type': 'integer'}, 'page_size': {'description': 'Alias for limit â\x80\x94 number of results to return', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Europe PMC. Supports Lucene-like fielded syntax (e.g., BODY:"term", INTRO:"term", METHODS:"term").', 'required': True, 'type': 'string'}, 'require_has_ft': {'default': False, 'description': 'If true, appends `HAS_FT:Y` to the query to restrict results to records where Europe PMC has full text indexed. This is NOT the same as having a link to free full text elsewhere (e.g., PMC) and is often the key reason body-only keywords cannot be found via Europe PMC search.', 'required': False, 'type': 'boolean'}}, 'required': ['query'], 'type': 'object'}
- PubChem_search_compounds_by_similarity signature={'properties': {'max_results': {'default': 10, 'description': 'Maximum number of CIDs to return (default: 10, max: 10000).', 'required': False, 'type': 'integer'}, 'smiles': {'description': 'SMILES expression of target molecule.', 'required': True, 'type': 'string'}, 'threshold': {'default': 0.9, 'description': 'Similarity threshold (between 0 and 1), e.g., 0.9 means 90% similarity.', 'required': True, 'type': 'number'}}, 'required': ['smiles', 'threshold'], 'type': 'object'}

# TARGET SKILL TO CONVERT
---
name: tooluniverse-drug-research
description: Comprehensive drug profiling — mechanism, primary/secondary targets, drug interactions, clinical-trial status, adverse events (FAERS), pharmacogenomics, and approval history. Use for full drug investigation reports, 'tell me about drug X' queries, and assembling drug profiles for clinicians, researchers, or regulatory work.
disable-model-invocation: true
---

# Drug Research Strategy

Comprehensive drug investigation using 50+ ToolUniverse tools across chemical databases, clinical trials, adverse events, pharmacogenomics, and literature.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Compound disambiguation FIRST** - Resolve identifiers before research
3. **Citation requirements** - Every fact must have inline source attribution
4. **Evidence grading** - Grade claims by evidence strength (T1-T4)
5. **Mandatory completeness** - All sections must exist, even if "data unavailable"
6. **English-first queries** - Always use English drug/compound names in tool calls, even if the user writes in another language. Only try original-language terms as a fallback. Respond in the user's language

---

## LOOK UP, DON'T GUESS

When asked about a drug, query ChEMBL/PubChem/DailyMed FIRST. Don't guess at mechanism, targets, or side effects — look them up. When you're not sure about a fact, your first instinct should be to SEARCH for it using tools, not to reason harder from memory.

---

## Drug Mechanism Reasoning

When investigating a drug's mechanism of action, trace the full causal chain:
1. **Target engagement** - Which protein(s) does the drug bind, and with what affinity/selectivity?
2. **Molecular effect** - Does binding inhibit, activate, or modulate the target's function?
3. **Pathway consequence** - Which signaling or metabolic pathway is altered downstream?
4. **Cellular phenotype** - What changes occur at the cell level (proliferation, apoptosis, secretion)?
5. **Physiological outcome** - How does the cellular effect translate to the therapeutic benefit in the patient?

---

## Workflow Overview

### 1. Report-First Approach (MANDATORY)

**DO NOT** show the search process or tool outputs to the user. Instead:

1. **Create the report file FIRST** - `[DRUG]_drug_report.md` with all 11 section headers and `[Researching...]` placeholders. See [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) for the full template.
2. **Progressively update the report** - Replace placeholders with findings as you query each tool.
3. **Use ALL relevant tools** - Query multiple databases for each data type; cross-reference across sources.

### 2. Citation Requirements (MANDATORY)

Every piece of information MUST include its source. Use inline citations:
```markdown
*Source: PubChem via `PubChem_get_compound_properties_by_CID` (CID: 4091)*
```

### 3. Progressive Writing Workflow

```
Step 1:  Create report file with all section headers
Step 2:  Resolve compound identifiers -> Update Section 1
Step 3:  Query PubChem/ADMET-AI/DailyMed SPL -> Update Section 2 (Chemistry)
Step 4:  Query FDA Label MOA + ChEMBL + DGIdb -> Update Section 3 (Mechanism)
Step 5:  Query ADMET-AI tools -> Update Section 4 (ADMET)
Step 6:  Query ClinicalTrials.gov -> Update Section 5 (Clinical)
Step 7:  Query FAERS/DailyMed -> Update Section 6 (Safety)
Step 8:  Query PharmGKB -> Update Section 7 (Pharmacogenomics)
Step 9:  Query DailyMed/Orange Book -> Update Section 8 (Regulatory)
Step 10: Query PubMed/literature -> Update Section 9 (Literature)
Step 11: Synthesize findings -> Update Executive Summary & Section 10
Step 12: Document all sources -> Update Section 11 (Data Sources)
```

---

## Compound Disambiguation (Phase 1)

**CRITICAL**: Establish compound identity before any research.

### Identifier Resolution Chain

```
1. PubChem_get_CID_by_compound_name(compound_name)
   -> Extract: CID, canonical SMILES, formula

2. ChEMBL_search_compounds(query=drug_name)
   -> Extract: ChEMBL ID, pref_name

3. DailyMed_search_spls(drug_name)
   -> Extract: Set ID, NDC codes (if approved)

4. PharmGKB_search_drugs(query=drug_name)
   -> Extract: PharmGKB ID (PA...)
```

### Handle Naming Ambiguity

| Issue | Example | Resolution |
|-------|---------|------------|
| Salt forms | metformin vs metformin HCl | Note all CIDs; use parent compound |
| Isomers | omeprazole vs esomeprazole | Verify SMILES; separate entries if distinct |
| Prodrugs | enalapril vs enalaprilat | Document both; note conversion |
| Brand confusion | Different products same name | Clarify with user |

---

## Research Paths Summary

Each path has detailed tool chains and output examples in [REPORT_GUIDELINES.md](REPORT_GUIDELINES.md).

### PATH 1: Chemical Properties & CMC
**Tools**: PubChem properties -> ADMET-AI physicochemical -> ADMET-AI solubility -> DailyMed chemistry/description
**Output**: Physicochemical table, Lipinski assessment, QED score, salt forms, formulation comparison

### PATH 2: Mechanism & Targets
**Tools**: DailyMed MOA -> ChEMBL activities (NOT `ChEMBL_get_molecule_targets`) -> ChEMBL target details -> DGIdb -> PubChem bioactivity
**Critical**: Derive targets from activities filtered to pChEMBL >= 6.0. Avoid `ChEMBL_get_molecule_targets`.
**Output**: FDA MOA text, target table with UniProt/potency, selectivity profile

### PATH 3: ADMET Properties
**Tools**: ADMET-AI (bioavailability, BBB, CYP, clearance, toxicity)
**Fallback**: DailyMed clinical_pharmacology + pharmacokinetics + drug_interactions
**Critical**: If ADMET-AI fails, automatically use fallback. Never leave Section 4 empty.

### PATH 4: Clinical Trials
**Tools**: search_clinical_trials -> compute phase counts -> extract outcomes/AEs -> fda_pharmacogenomic_biomarkers
**Critical**: Section 5.2 must show actual counts by phase/status in table format.

### PATH 5: Post-Marketing Safety
**Tools**: FAERS (reactions, seriousness, outcomes, deaths, age) + DailyMed (DDI, dosing, warnings)
**Critical**: Include FAERS date window, seriousness breakdown, and limitations paragraph.

### PATH 6: Pharmacogenomics
**Tools**: PharmGKB (search -> details -> annotations -> guidelines)
**Fallback**: DailyMed pharmacogenomics section + PubMed literature

### PATH 7: Regulatory & Patents
**Tools**: FDA Orange Book (search, approval history, exclusivity, patents, generics) + DailyMed (special populations via LOINC codes)
**Note**: US-only data; document EMA/PMDA limitation.

### PATH 8: Real-World Evidence
**Tools**: ClinicalTrials.gov (OBSERVATIONAL studies) + PubMed (real-world, registry, surveillance)

### PATH 9: Comparative Analysis
**Tools**: Abbreviated tool chains for each comparator + head-to-head trial search + PubMed meta-analyses

---

## FDA Label Core Fields

For approved drugs, retrieve these DailyMed sections early (after getting set_id):

| Batch | Sections | Maps to Report |
|-------|----------|---------------|
| Phase 1 | mechanism_of_action, pharmacodynamics, chemistry | Sections 2-3 |
| Phase 2 | clinical_pharmacology, pharmacokinetics, drug_interactions | Sections 4, 6.5 |
| Phase 3 | warnings_and_cautions, adverse_reactions, dosage_and_administration | Sections 6, 8.2 |
| Phase 4 | pharmacogenomics, clinical_studies, description, inactive_ingredients | Sections 5, 7 |

---

## Fallback Chains

| Primary Tool | Fallback | Use When |
|--------------|----------|----------|
| `PubChem_get_CID_by_compound_name` | `ChEMBL_search_drugs` | Name not in PubChem |
| `ChEMBL_get_molecule_targets` | **Use `ChEMBL_search_activities` instead** | Always avoid this tool |
| `ChEMBL_get_activity` | `PubChemBioAssay_get_assay_summary` | No ChEMBL ID |
| `DailyMed_search_spls` | `PubChemTox_get_acute_effects` | DailyMed timeout |
| `PharmGKB_search_drugs` | DailyMed PGx sections + PubMed | PharmGKB unavailable |
| `PharmGKB_get_dosing_guidelines` | DailyMed pharmacogenomics section | PharmGKB API error |
| `FAERS_count_reactions_by_drug_event` | Document "FAERS unavailable" + use label AEs | API error |
| `ADMETAI_*` (all tools) | DailyMed clinical_pharmacology + pharmacokinetics | Invalid SMILES or API error |

---

## Quick Reference: Tools by Use Case

| Use Case | Primary Tool | Fallback | Evidence |
|----------|--------------|----------|----------|
| Name -> CID | `PubChem_get_CID_by_compound_name` | `ChEMBL_search_drugs` | T1 |
| Properties | `PubChem_get_compound_properties_by_CID` | ADMET-AI physicochemical | T1/T2 |
| FDA MOA | `DailyMed_parse_clinical_pharmacology` (mechanism_of_action) | - | T1 |
| Targets | `ChEMBL_search_activities` -> `ChEMBL_get_target` | `DGIdb_get_drug_info` | T1 |
| ADMET | `ADMETAI_predict_*` (5 tools) | DailyMed PK sections | T2/T1 |
| Trials | `search_clinical_trials` | - | T1 |
| Trial outcomes | `extract_clinical_trial_outcomes` | - | T1 |
| FAERS | `FAERS_count_reactions_by_drug_event` | Label adverse_reactions | T1 |
| Dose mods | `DailyMed_parse_clinical_pharmacology` (dosage, warnings) | - | T1 |
| PGx | `PharmGKB_search_drugs` | DailyMed PGx + PubMed | T2/T1 |
| Label | `DailyMed_search_spls` | `PubChemTox_get_acute_effects` | T1 |
| Literature | `PubMed_search_articles` | `EuropePMC_search_articles` | Varies |
| Regulatory | `FDA_OrangeBook_*` tools | DailyMed label data | T1 |

See [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) for the complete tool listing with parameters and input format requirements.

---

## Type Normalization

Many tools require **string** inputs. Always convert IDs before API calls:
- ChEMBL IDs, PubMed IDs, NCT IDs: convert int -> str
- SMILES for ADMET-AI: pass as list `["SMILES_STRING"]`
- FAERS drug names: use UPPERCASE (e.g., `"METFORMIN"`)
- ChEMBL IDs: full format `"CHEMBL1431"` not `"1431"`
- PharmGKB IDs: PA prefix `"PA450657"` not `"450657"`

---

## Common Use Cases

| Use Case | Primary Sections | Light Sections |
|----------|------------------|----------------|
| Approved Drug Profile | All 11 sections | None |
| Investigational Compound | 1, 2, 3, 4, 9 | 5, 6, 7, 8 |
| Safety Review | 1, 5, 6, 7, 9 | 2, 3, 4, 8 |
| ADMET Assessment | 1, 2, 4 | 3, 5, 6, 7, 8, 9 |
| Clinical Development Landscape | 1, 5, 9 | 2, 3, 4, 6, 7, 8 |

Always maintain all section headers but adjust depth based on query focus and data availability.

---

## When NOT to Use This Skill

- **Target research** -> Use target-intelligence-gatherer skill
- **Disease research** -> Use disease-research skill
- **Literature-only** -> Use literature-deep-research skill
- **Single property lookup** -> Call tool directly
- **Structure similarity search** -> Use `PubChem_search_compounds_by_similarity` directly

---

## Cross-Skill References

For drug interaction checking, run: `python3 skills/tooluniverse-drug-drug-interaction/scripts/pharmacology_ref.py --type interaction --drug1 X --drug2 Y`

---

## Additional Resources

- **Report template**: [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) - Initial file template, citation format, evidence grading, scorecard, audit template
- **Report guidelines**: [REPORT_GUIDELINES.md](REPORT_GUIDELINES.md) - Detailed section-by-section instructions with output examples
- **Tool reference**: [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) - Complete tool listing with parameters and input formats
- **Verification checklist**: [CHECKLIST.md](CHECKLIST.md) - Section-by-section pre-delivery verification
- **Examples**: [EXAMPLES.md](EXAMPLES.md) - Detailed workflow examples for different use cases


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
