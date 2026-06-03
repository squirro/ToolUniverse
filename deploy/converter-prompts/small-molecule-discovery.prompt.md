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
- PubChem_get_CID_by_compound_name signature={'properties': {'compound_name': {'description': 'Alias for name. The compound name to look up.', 'required': False, 'type': 'string'}, 'name': {'description': 'Chemical compound name (e.g., "Aspirin", "Acetaminophen") or IUPAC name. Do not use disease names or medical conditions.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_search_molecules signature={'properties': {'fields': {'description': "Optional list of ChEMBL molecule fields to include in each returned molecule object (projection). ToolUniverse maps this to ChEMBL's `only` query parameter (comma-separated). Supported fields: molecule_chembl_id, pref_name, molecule_type, max_phase, first_approval, black_box_warning, withdrawn_flag, molecule_structures, molecule_properties.", 'items': {'enum': ['molecule_chembl_id', 'pref_name', 'molecule_type', 'max_phase', 'first_approval', 'black_box_warning', 'withdrawn_flag', 'molecule_structures', 'molecule_properties'], 'type': 'string'}, 'required': False, 'type': 'array', 'uniqueItems': True}, 'format': {'default': 'json', 'enum': ['json', 'xml', 'yaml'], 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'description': 'Maximum number of results (default: 20, max: 1000)', 'maximum': 1000, 'required': False, 'type': 'integer'}, 'max_results': {'default': 20, 'description': 'Maximum number of results to return. Alias for limit.', 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Filter by ChEMBL ID (exact match)', 'required': False, 'type': 'string'}, 'molecule_type': {'description': "Filter by molecule type (e.g., 'Small molecule', 'Antibody')", 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'description': 'Offset for pagination (default: 0)', 'required': False, 'type': 'integer'}, 'pref_name__contains': {'description': 'Filter by preferred name (contains). Note: `pref_name` coverage is incomplete in ChEMBL, so this can legitimately return zero results even for common names; prefer `molecule_chembl_id` for reliable retrieval.', 'required': False, 'type': 'string'}, 'query': {'description': 'Molecule name to search for. Alias for pref_name__contains.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- SwissADME_calculate_adme signature={'properties': {'molecule_name': {'description': "Optional name for the molecule. If not provided, SwissADME assigns 'Molecule 1'.", 'required': False, 'type': ['string', 'null']}, 'operation': {'description': 'Operation type', 'enum': ['calculate_adme'], 'required': True, 'type': 'string'}, 'smiles': {'description': 'SMILES string of the molecule to analyze. Must be a valid small molecule SMILES. Examples: CC(=O)Oc1ccccc1C(=O)O (aspirin), CC(C)Cc1ccc(cc1)C(C)C(=O)O (ibuprofen), c1ccc2[nH]c(-c3ccncc3)cc2c1 (omeprazole core)', 'required': True, 'type': 'string'}}, 'required': ['operation', 'smiles'], 'type': 'object'}
- ChEMBL_search_activities signature={'properties': {'assay_chembl_id': {'description': 'Filter by assay ChEMBL ID', 'required': False, 'type': 'string'}, 'fields': {'description': "Optional list of ChEMBL activity fields to include in each returned activity object (projection). ToolUniverse maps this to ChEMBL's `only` query parameter (comma-separated). Supported fields: activity_id, molecule_chembl_id, target_chembl_id, assay_chembl_id, standard_type, standard_value, standard_units, pchembl_value, standard_relation, standard_flag.", 'items': {'enum': ['activity_id', 'molecule_chembl_id', 'target_chembl_id', 'assay_chembl_id', 'standard_type', 'standard_value', 'standard_units', 'pchembl_value', 'standard_relation', 'standard_flag'], 'type': 'string'}, 'required': False, 'type': 'array', 'uniqueItems': True}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Filter by molecule ChEMBL ID', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'standard_type': {'description': "Filter by activity type (e.g., 'IC50', 'Ki', 'EC50')", 'required': False, 'type': 'string'}, 'standard_value__gte': {'description': 'Filter by minimum activity value', 'required': False, 'type': 'number'}, 'standard_value__lte': {'description': 'Filter by maximum activity value', 'required': False, 'type': 'number'}, 'target_chembl_id': {'description': 'Filter by target ChEMBL ID', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- BindingDB_get_ligands_by_uniprot signature={'properties': {'affinity_cutoff': {'default': 10000, 'description': 'Maximum affinity in nM (default: 10000)', 'required': False, 'type': 'integer'}, 'uniprot_id': {'description': 'UniProt accession ID (e.g., P00533 for EGFR)', 'required': True, 'type': 'string'}}, 'required': ['uniprot_id'], 'type': 'object'}
- eMolecules_search signature={'properties': {'max_results': {'default': 20, 'description': 'Maximum results (default: 20)', 'required': False, 'type': 'integer'}, 'operation': {'const': 'search', 'required': False, 'type': 'string'}, 'query': {'description': 'Search query - compound name or keyword', 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- Enamine_search_catalog signature={'properties': {'catalog': {'default': 'all', 'description': 'Catalog: REAL (make-on-demand), BB (building blocks), SCR (screening), all (default: all)', 'required': False, 'type': 'string'}, 'operation': {'const': 'search_catalog', 'required': False, 'type': 'string'}, 'query': {'description': 'Search query - compound name or keyword', 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- PubChem_get_CID_by_SMILES signature={'properties': {'smiles': {'description': 'SMILES expression (e.g., "CC(=O)OC1=CC=CC=C1C(=O)O" corresponds to aspirin).', 'required': True, 'type': 'string'}}, 'required': ['smiles'], 'type': 'object'}
- PubChem_get_compound_properties_by_CID signature={'properties': {'cid': {'description': 'PubChem compound ID to query, e.g., 2244 (Aspirin).', 'required': True, 'type': 'integer'}}, 'required': ['cid'], 'type': 'object'}
- PubChem_search_compounds_by_similarity signature={'properties': {'max_results': {'default': 10, 'description': 'Maximum number of CIDs to return (default: 10, max: 10000).', 'required': False, 'type': 'integer'}, 'smiles': {'description': 'SMILES expression of target molecule.', 'required': True, 'type': 'string'}, 'threshold': {'default': 0.9, 'description': 'Similarity threshold (between 0 and 1), e.g., 0.9 means 90% similarity.', 'required': True, 'type': 'number'}}, 'required': ['smiles', 'threshold'], 'type': 'object'}
- PubChem_search_compounds_by_substructure signature={'properties': {'max_results': {'default': 10, 'description': 'Maximum number of CIDs to return (default: 10, max: 10000).', 'required': False, 'type': 'integer'}, 'smiles': {'description': 'SMILES of substructure (e.g., "c1ccccc1" corresponds to benzene ring).', 'required': True, 'type': 'string'}}, 'required': ['smiles'], 'type': 'object'}
- PubChem_get_compound_synonyms_by_CID signature={'properties': {'cid': {'description': 'Compound ID to query synonyms for, e.g., 2244.', 'required': True, 'type': 'integer'}}, 'required': ['cid'], 'type': 'object'}
- ChEMBL_get_molecule signature={'properties': {'chembl_id': {'description': "ChEMBL molecule ID, e.g., 'CHEMBL25'", 'required': False, 'type': 'string'}, 'format': {'default': 'json', 'description': 'Response format', 'enum': ['json', 'xml', 'yaml'], 'required': False, 'type': 'string'}, 'molecule_chembl_id': {'description': 'Alias for chembl_id. ChEMBL molecule ID, e.g., CHEMBL1229517.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_search_similar_molecules signature={'properties': {'max_results': {'default': 20, 'description': 'Maximum number of results to return.', 'required': True, 'type': 'integer'}, 'query': {'description': 'SMILES string, chembl_id, or compound or drug name. Note: Only small molecule compounds are supported. Biologics (antibodies, proteins, etc.) will return an error as they lack SMILES structures.', 'required': True, 'type': 'string'}, 'similarity_threshold': {'default': 80, 'description': 'Similarity threshold (0–100).', 'required': True, 'type': 'integer'}}, 'required': ['query', 'similarity_threshold', 'max_results'], 'type': 'object'}
- ChEMBL_get_drug_mechanisms signature={'properties': {'chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL ID (e.g., "CHEMBL3301622").', 'required': False, 'type': 'string'}, 'drug_chembl_id': {'description': 'ChEMBL drug/molecule ID (e.g., "CHEMBL1201581" for adalimumab, "CHEMBL4535757" for sotorasib).', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Drug name for automatic ChEMBL ID lookup (e.g., "trastuzumab", "lapatinib", "aspirin"). Case-insensitive. Triggers internal ChEMBL molecule search â\x80\x94 use drug_chembl_id if you already know the ID.', 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL molecule ID (e.g., "CHEMBL25" for aspirin).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- ChEMBL_search_targets signature={'properties': {'fields': {'description': "Optional list of ChEMBL target fields to include in each returned target object (projection). ToolUniverse maps this to ChEMBL's `only` query parameter (comma-separated). Supported fields: target_chembl_id, pref_name, organism, target_type, target_components.", 'items': {'enum': ['target_chembl_id', 'pref_name', 'organism', 'target_type', 'target_components'], 'type': 'string'}, 'required': False, 'type': 'array', 'uniqueItems': True}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'organism': {'description': "Filter by organism (e.g., 'Homo sapiens')", 'required': False, 'type': 'string'}, 'pref_name__contains': {'description': 'Filter by target name (contains)', 'required': False, 'type': 'string'}, 'target_chembl_id': {'description': 'Filter by target ChEMBL ID', 'required': False, 'type': 'string'}, 'target_type': {'description': "Filter by target type (e.g., 'SINGLE PROTEIN', 'PROTEIN COMPLEX')", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_target_activities signature={'oneOf': [{'required': ['target_chembl_id__exact']}, {'required': ['target_chembl_id']}], 'properties': {'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'target_chembl_id': {'description': 'Alias for target_chembl_id__exact. ChEMBL target ID (e.g., CHEMBL213).', 'required': False, 'type': 'string'}, 'target_chembl_id__exact': {'description': "ChEMBL target ID (e.g., 'CHEMBL2074'). To find a target ID, use ChEMBL_search_targets with a target name or gene symbol.", 'required': False, 'type': 'string'}}, 'type': 'object'}
- SwissADME_check_druglikeness signature={'properties': {'operation': {'description': 'Operation type', 'enum': ['check_druglikeness'], 'required': True, 'type': 'string'}, 'rules': {'description': 'Optional list of specific drug-likeness rules to check. If null, all 5 rules are evaluated. Valid values: lipinski, ghose, veber, egan, muegge.', 'items': {'enum': ['lipinski', 'ghose', 'veber', 'egan', 'muegge'], 'type': 'string'}, 'required': False, 'type': ['array', 'null']}, 'smiles': {'description': 'SMILES string of the molecule to check. Must be a valid small molecule SMILES.', 'required': True, 'type': 'string'}}, 'required': ['operation', 'smiles'], 'type': 'object'}
- ADMETAI_predict_physicochemical_properties signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_bioavailability signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_BBB_penetrance signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_toxicity signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_CYP_interactions signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- SwissTargetPrediction_predict signature={'properties': {'operation': {'description': 'Operation type', 'enum': ['predict'], 'required': True, 'type': 'string'}, 'organism': {'default': 'Homo_sapiens', 'description': 'Target organism proteome. Use underscores. Valid options: Homo_sapiens (default), Mus_musculus, Rattus_norvegicus, Bos_taurus, Sus_scrofa', 'required': False, 'type': ['string', 'null']}, 'smiles': {'description': 'SMILES representation of the query molecule. Must be a valid, druglike small molecule (not peptides or macromolecules). Examples: CC(=O)Oc1ccccc1C(=O)O (aspirin), CC(C)Cc1ccc(cc1)C(C)C(=O)O (ibuprofen), c1ccc2c(c1)cc1ccc3cccc4ccc2c1c34 (benzo[a]pyrene)', 'required': True, 'type': 'string'}, 'top_n': {'description': 'Return only the top N predictions ranked by probability. If null, returns all predictions (typically ~100 targets).', 'required': False, 'type': ['integer', 'null']}}, 'required': ['operation', 'smiles'], 'type': 'object'}
- eMolecules_search_smiles signature={'properties': {'max_results': {'default': 20, 'description': 'Maximum results (default: 20)', 'required': False, 'type': 'integer'}, 'operation': {'const': 'search_smiles', 'required': False, 'type': 'string'}, 'search_type': {'default': 'similarity', 'description': 'Search type: exact, substructure, similarity (default: similarity)', 'required': False, 'type': 'string'}, 'smiles': {'description': 'SMILES string for the query compound', 'required': True, 'type': 'string'}}, 'required': ['smiles'], 'type': 'object'}
- eMolecules_get_vendors signature={'properties': {'operation': {'const': 'get_vendors', 'required': False, 'type': 'string'}, 'smiles': {'description': 'SMILES string for the compound', 'required': True, 'type': 'string'}}, 'required': ['smiles'], 'type': 'object'}
- Enamine_search_smiles signature={'properties': {'operation': {'const': 'search_smiles', 'required': False, 'type': 'string'}, 'search_type': {'default': 'similarity', 'description': 'Search type: exact, substructure, similarity (default: similarity)', 'required': False, 'type': 'string'}, 'smiles': {'description': 'SMILES string for the query compound', 'required': True, 'type': 'string'}}, 'required': ['smiles'], 'type': 'object'}
- Enamine_get_libraries signature={'properties': {'operation': {'const': 'get_libraries', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- Enamine_get_compound signature={'properties': {'enamine_id': {'description': 'Enamine compound ID (e.g., Z1234567890)', 'required': True, 'type': 'string'}, 'operation': {'const': 'get_compound', 'required': False, 'type': 'string'}}, 'required': ['enamine_id'], 'type': 'object'}
- BindingDB_get_targets_by_compound signature={'properties': {'similarity_cutoff': {'default': 0.85, 'description': 'Similarity threshold 0-1 (default: 0.85)', 'required': False, 'type': 'number'}, 'smiles': {'description': 'SMILES structure of compound', 'required': True, 'type': 'string'}}, 'required': ['smiles'], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- compound_name
- chembl_id
- molecule_chembl_id
- target_chembl_id
- drug_chembl_id
- drug_name
- compound_id
- search_type
- enamine_id
- uniprot_id

# TARGET SKILL TO CONVERT
---
name: tooluniverse-small-molecule-discovery
description: Small molecule identification, characterization, and procurement — PubChem, ChEMBL, BindingDB, ADMET-AI, SwissADME, eMolecules, Enamine. Covers compound name to structure to activity to ADMET properties to commercial sourcing. Use for chemical biology, lead identification, probe selection, and the full small-molecule discovery pipeline.
disable-model-invocation: true
---

# Small Molecule Discovery Skill

Systematic small molecule identification, characterization, and sourcing using PubChem, ChEMBL, BindingDB, ADMET-AI, SwissADME, eMolecules, and Enamine. Covers the full pipeline from compound name to structure, activity, ADMET properties, and commercial procurement.

## Domain Reasoning

Drug-likeness is not a binary property. Lipinski's Rule of 5 was derived from orally administered, passively absorbed drugs and has many well-known exceptions: natural products, macrocycles, PROTACs, and many approved drugs violate one or more rules. The relevant question is not "does this pass Ro5?" but "does this compound's physicochemical profile match the requirements of the target, the intended route of administration, and the therapeutic context?" Focus on the specific requirements, not rigid rules.

## LOOK UP DON'T GUESS

- Compound identity (CID, ChEMBL ID, SMILES): call `PubChem_get_CID_by_compound_name` and `ChEMBL_search_molecules`; do not assume IDs from memory.
- ADMET properties: run `SwissADME_calculate_adme` or `ADMETAI_predict_*` on the actual SMILES; do not estimate logP, TPSA, or bioavailability.
- Binding affinities against a target: query `ChEMBL_search_activities` or `BindingDB_get_ligands_by_uniprot`; never cite IC50 values from memory.
- Commercial availability: check `eMolecules_search` or `Enamine_search_catalog`; do not assume availability.

---

**KEY PRINCIPLES**:
1. **Resolve identity first** - Always get CID and ChEMBL ID before research
2. **SMILES required for property prediction** - Extract canonical SMILES from PubChem early
3. **English names in tools** - Use IUPAC or common English names; avoid abbreviations in tool calls
4. **BindingDB is often unavailable** - Fall back to ChEMBL activities when BindingDB times out
5. **eMolecules/Enamine return URLs** - These tools generate search URLs, not direct data; note this to user

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

- "Find information about compound X"
- "What is the drug-likeness of this SMILES?"
- "Show binding affinities for EGFR inhibitors"
- "Search for compounds similar to imatinib"
- "Is this compound commercially available?"
- "What are the ADMET properties of this molecule?"
- "Find ChEMBL activities for target Y"
- "Predict targets for this small molecule"

---

## Key Tools

| Tool | Purpose | Key Params |
|------|---------|-----------|
| `PubChem_get_CID_by_compound_name` | Name to CID lookup | `compound_name` |
| `PubChem_get_CID_by_SMILES` | SMILES to CID lookup | `smiles` |
| `PubChem_get_compound_properties_by_CID` | MW, formula, SMILES, InChIKey | `cid`, `properties` |
| `PubChem_search_compounds_by_similarity` | Find structurally similar compounds | `smiles`, `threshold` (0-100) |
| `PubChem_search_compounds_by_substructure` | Substructure search | `smiles` |
| `PubChem_get_compound_synonyms_by_CID` | All names/synonyms | `cid` |
| `ChEMBL_search_molecules` | Search ChEMBL by name or ID | `query` |
| `ChEMBL_get_molecule` | Full ChEMBL molecule record | `chembl_id` |
| `ChEMBL_search_similar_molecules` | Similarity search in ChEMBL | `query` (SMILES or ChEMBL ID) |
| `ChEMBL_search_activities` | Binding affinities and assay data | `molecule_chembl_id`, `target_chembl_id`, `pchembl_value__gte` |
| `ChEMBL_get_drug_mechanisms` | MOA for approved drugs | `drug_chembl_id` or `drug_name` |
| `ChEMBL_search_targets` | Find targets by name | `query`, `organism` |
| `ChEMBL_get_target_activities` | All ligands for a target | `target_chembl_id` |
| `SwissADME_calculate_adme` | Physicochemical + ADMET properties | `operation="calculate_adme"`, `smiles` |
| `SwissADME_check_druglikeness` | Lipinski, Veber, Egan rules | `operation="check_druglikeness"`, `smiles` |
| `ADMETAI_predict_physicochemical_properties` | MW, logP, TPSA, HBD/HBA | `smiles` (list) |
| `ADMETAI_predict_bioavailability` | Oral bioavailability prediction | `smiles` (list) |
| `ADMETAI_predict_BBB_penetrance` | Blood-brain barrier permeability | `smiles` (list) |
| `ADMETAI_predict_toxicity` | hERG, DILI, mutagenicity | `smiles` (list) |
| `ADMETAI_predict_CYP_interactions` | CYP450 inhibition/substrate | `smiles` (list) |
| `SwissTargetPrediction_predict` | Predict protein targets for compound | `operation="predict"`, `smiles` |
| `eMolecules_search` | Find commercially available compounds | `query` (name or keyword) |
| `eMolecules_search_smiles` | Structure-based commercial search | `smiles` |
| `eMolecules_get_vendors` | Find vendors for a specific compound | `compound_id` |
| `Enamine_search_catalog` | Search Enamine screening library | `query` |
| `Enamine_search_smiles` | Search Enamine by structure | `smiles` |
| `Enamine_get_libraries` | List Enamine compound libraries | (none required) |

---

## Workflow

### Phase 1: Compound Identification

```
# Step 1: Name -> CID (PubChem canonical identity)
PubChem_get_CID_by_compound_name(compound_name="imatinib")
# -> CID: 5291

# Step 2: Get SMILES and properties (needed for all downstream tools)
PubChem_get_compound_properties_by_CID(
    cid="5291",
    properties="MolecularFormula,MolecularWeight,CanonicalSMILES,InChIKey,IUPACName"
)
# -> canonical SMILES, InChIKey (global identifier)

# Step 3: Get ChEMBL ID (for activity data)
ChEMBL_search_molecules(query="imatinib")
# -> ChEMBL ID (e.g., "CHEMBL941")

# Step 4: Get all synonyms (brand names, INN, etc.)
PubChem_get_compound_synonyms_by_CID(cid="5291")
```

**ID resolution priority**:
1. Start with PubChem CID (most universal)
2. Get ChEMBL ID (for bioactivity data)
3. Use canonical SMILES for structure-based searches and ADMET

### Phase 2: Structure-Based Search

**Similarity search** (find analogs):
```
PubChem_search_compounds_by_similarity(
    smiles="CANONICAL_SMILES",
    threshold=85   # Tanimoto threshold 0-100; 85 = highly similar
)
# Returns: list of CIDs of similar compounds

ChEMBL_search_similar_molecules(query="CHEMBL941")  # Or SMILES
# Returns: ChEMBL entries sorted by similarity
```

**Substructure search** (find compounds containing a scaffold):
```
PubChem_search_compounds_by_substructure(smiles="SCAFFOLD_SMILES")
# Returns: CIDs of compounds containing the scaffold
```

### Phase 3: Bioactivity and Binding Affinity

**Get all activities for a compound** (across all targets):
```
ChEMBL_search_activities(
    molecule_chembl_id="CHEMBL941",
    pchembl_value__gte=6,   # pIC50/Ki >= 6 = IC50/Ki <= 1 µM
    limit=50
)
# Returns: assay_type, target_name, pchembl_value, units
```

**Get all ligands for a target**:
```
# First find target ChEMBL ID
ChEMBL_search_targets(query="EGFR", organism="Homo sapiens")
# -> target_chembl_id, e.g., "CHEMBL203"

ChEMBL_get_target_activities(
    target_chembl_id="CHEMBL203"
)
# Returns: all compounds with binding data against this target
```

**BindingDB** (when available — often times out):
```
BindingDB_get_ligands_by_uniprot(uniprot_id="P00533")  # EGFR
# Returns: Ki, IC50, Kd data with literature references
# Note: BindingDB REST API is frequently unavailable; fall back to ChEMBL
```

**pChEMBL Value interpretation**:
| pChEMBL | IC50 / Ki | Affinity |
|---------|-----------|---------|
| >= 9 | <= 1 nM | Very potent |
| >= 7 | <= 100 nM | Potent |
| >= 6 | <= 1 µM | Moderate |
| >= 5 | <= 10 µM | Weak |
| < 5 | > 10 µM | Inactive |

### Phase 4: Drug-likeness and ADMET

**SwissADME** (comprehensive, requires SMILES string — not list):
```
SwissADME_calculate_adme(
    operation="calculate_adme",
    smiles="CANONICAL_SMILES"
)
# Returns: physicochemical, lipophilicity, water solubility, pharmacokinetics,
#          drug-likeness scores (Lipinski, Veber, Egan, Muegge), PAINS alerts

SwissADME_check_druglikeness(
    operation="check_druglikeness",
    smiles="CANONICAL_SMILES"
)
# Returns: Lipinski/Veber/Egan pass/fail + lead-likeness
```

**ADMET-AI** (ML-based, requires SMILES as list — install tooluniverse[ml]):
```
ADMETAI_predict_physicochemical_properties(smiles=["CANONICAL_SMILES"])
ADMETAI_predict_bioavailability(smiles=["CANONICAL_SMILES"])
ADMETAI_predict_BBB_penetrance(smiles=["CANONICAL_SMILES"])
ADMETAI_predict_toxicity(smiles=["CANONICAL_SMILES"])
ADMETAI_predict_CYP_interactions(smiles=["CANONICAL_SMILES"])
```

**Note**: ADMET-AI requires `pip install tooluniverse[ml]`. If unavailable, use SwissADME as fallback.

**Key drug-likeness rules**:
- **Lipinski Ro5**: MW <= 500, logP <= 5, HBD <= 5, HBA <= 10 (oral drugs)
- **Veber**: TPSA <= 140 Å², rotatable bonds <= 10 (oral bioavailability)
- **Lead-like**: MW <= 350, logP <= 3, HBD <= 3, HBA <= 6 (fragment/lead)

### Phase 5: Target Prediction

When you have a novel compound and want to predict targets:
```
SwissTargetPrediction_predict(
    operation="predict",
    smiles="CANONICAL_SMILES"
)
# Returns: predicted protein targets with probability scores
# Note: SwissTargetPrediction uses structure-similarity to known drug-target pairs
# May time out for complex molecules
```

### Phase 6: Commercial Availability

**eMolecules** (aggregates 200+ suppliers — returns search URL, not direct data):
```
eMolecules_search(query="compound_name")
# -> Returns search_url to visit on eMolecules.com

eMolecules_search_smiles(smiles="CANONICAL_SMILES")
# -> Returns URL for exact/similar structure search
```

**Enamine** (37B+ make-on-demand compounds — returns URL when API unavailable):
```
Enamine_search_catalog(query="compound_name")
# -> If API available: returns catalog entries with catalog_id, price
# -> If API unavailable: returns search_url for manual search

Enamine_search_smiles(smiles="CANONICAL_SMILES")
# -> Exact or similarity structure search

Enamine_get_libraries()
# -> Lists available Enamine screening collections
```

**Note**: eMolecules and Enamine APIs frequently return search URLs rather than live data. Present these to the user as "search here" links.

---

## Tool Parameter Reference

| Tool | Required Params | Notes |
|------|----------------|-------|
| `PubChem_get_CID_by_compound_name` | `compound_name` | Returns list of CIDs; take first or most relevant |
| `PubChem_get_CID_by_SMILES` | `smiles` | Use canonical SMILES |
| `PubChem_get_compound_properties_by_CID` | `cid`, `properties` | `cid` as string; `properties` comma-separated |
| `PubChem_search_compounds_by_similarity` | `smiles` | `threshold` (int 0-100, default 90) |
| `PubChem_search_compounds_by_substructure` | `smiles` | Returns CIDs matching scaffold |
| `ChEMBL_search_molecules` | `query` | Name, ChEMBL ID, or InChIKey |
| `ChEMBL_get_molecule` | `chembl_id` | Full format: "CHEMBL941" not "941" |
| `ChEMBL_search_similar_molecules` | `query` | SMILES or ChEMBL ID |
| `ChEMBL_search_activities` | `molecule_chembl_id` OR `target_chembl_id` | Use `pchembl_value__gte=6` to filter potent |
| `ChEMBL_get_drug_mechanisms` | `drug_chembl_id` or `drug_name` | For approved drugs only |
| `ChEMBL_search_targets` | `query` | Add `organism="Homo sapiens"` to filter human |
| `ChEMBL_get_target_activities` | `target_chembl_id` | Returns all ligands for target |
| `SwissADME_calculate_adme` | `operation="calculate_adme"`, `smiles` | SMILES as string (not list) |
| `SwissADME_check_druglikeness` | `operation="check_druglikeness"`, `smiles` | SMILES as string |
| `ADMETAI_predict_*` | `smiles` | Must be a **list**: `["SMILES"]` not `"SMILES"` |
| `SwissTargetPrediction_predict` | `operation="predict"`, `smiles` | May time out |
| `eMolecules_search` | `query` | Returns search URL (no live data) |
| `eMolecules_search_smiles` | `smiles` | Canonical SMILES |
| `eMolecules_get_vendors` | `compound_id` | eMolecules internal ID |
| `Enamine_search_catalog` | `query` | Returns URL when API unavailable |
| `Enamine_search_smiles` | `smiles` | `search_type`: "exact", "similarity", "substructure" |
| `Enamine_get_compound` | `enamine_id` | Enamine-specific catalog ID |
| `BindingDB_get_ligands_by_uniprot` | `uniprot_id` | Frequently unavailable — use ChEMBL as fallback |
| `BindingDB_get_targets_by_compound` | `smiles` | SMILES-based target lookup |

---

## Common Patterns

### Pattern 1: Full Compound Profile
```
Input: Compound name (e.g., "imatinib")
Flow:
  1. PubChem_get_CID_by_compound_name -> CID + SMILES
  2. ChEMBL_search_molecules -> ChEMBL ID
  3. PubChem_get_compound_properties_by_CID -> physicochemical props
  4. SwissADME_calculate_adme / ADMETAI_predict_* -> ADMET profile
  5. ChEMBL_search_activities(molecule_chembl_id) -> binding data
  6. ChEMBL_get_drug_mechanisms -> MOA (if approved drug)
Output: Complete compound profile with identity, ADMET, and activity data
```

### Pattern 2: Analog Discovery
```
Input: Reference compound SMILES
Flow:
  1. PubChem_search_compounds_by_similarity(smiles, threshold=85) -> similar CIDs
  2. ChEMBL_search_similar_molecules(query=smiles) -> ChEMBL analogs
  3. For each hit: PubChem_get_compound_properties_by_CID -> properties
  4. SwissADME_check_druglikeness -> filter by drug-likeness
Output: Ranked list of analogs with activity data and drug-likeness scores
```

### Pattern 3: Target-Based Compound Search
```
Input: Target name (e.g., "EGFR")
Flow:
  1. ChEMBL_search_targets(query="EGFR", organism="Homo sapiens") -> target_chembl_id
  2. ChEMBL_get_target_activities(target_chembl_id) -> all ligands with Ki/IC50
  3. Filter by pchembl_value >= 7 (potent compounds)
  4. For top hits: SwissADME_check_druglikeness -> assess drug-likeness
  5. eMolecules_search(query=compound_name) -> check commercial availability
Output: Prioritized list of potent, drug-like, commercially available compounds
```

### Pattern 4: ADMET Risk Assessment
```
Input: Novel compound SMILES
Flow:
  1. SwissADME_calculate_adme(operation="calculate_adme", smiles) -> full ADMET
  2. ADMETAI_predict_toxicity(smiles=[smiles]) -> hERG, DILI, mutagenicity
  3. ADMETAI_predict_CYP_interactions(smiles=[smiles]) -> drug-drug interaction risk
  4. ADMETAI_predict_BBB_penetrance(smiles=[smiles]) -> CNS penetration
Output: ADMET risk profile with flagged liabilities
```

---

## Fallback Chains

| Primary | Fallback | When |
|---------|----------|------|
| `BindingDB_get_ligands_by_uniprot` | `ChEMBL_get_target_activities` | BindingDB API unavailable |
| `ADMETAI_predict_*` | `SwissADME_calculate_adme` | ml dependencies not installed |
| `Enamine_search_catalog` | Returns URL only | API returns HTTP 500 (common) |
| `SwissTargetPrediction_predict` | `ChEMBL_search_similar_molecules` + known targets | Prediction times out |
| `PubChem_get_CID_by_compound_name` | `ChEMBL_search_molecules(query=name)` | Name not in PubChem |

---

## Limitations

- **BindingDB**: REST API frequently times out; ChEMBL is the reliable alternative for binding data
- **Enamine API**: Returns HTTP 500 often; tool provides search URL as fallback
- **eMolecules**: No public API; tool generates search URLs only
- **ADMET-AI**: Requires `pip install tooluniverse[ml]`; not always available in base install
- **SwissTargetPrediction**: Web scraping-based; may time out for complex molecules
- **SMILES format**: ADMET-AI requires a **list** `["SMILES"]`; SwissADME requires a **string** `"SMILES"`
- **ChEMBL IDs**: Always use full format `"CHEMBL941"`, never just `"941"`


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
