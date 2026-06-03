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
- PubChemBioAssay_get_assay_summary signature={'properties': {'aid': {'description': 'PubChem BioAssay ID (AID). Examples: 1259393, 504832, 1234.', 'required': True, 'type': 'integer'}}, 'required': ['aid'], 'type': 'object'}
- PubChemTox_get_acute_effects signature={'properties': {'cid': {'description': 'PubChem Compound ID. Examples: 5359596 (arsenic), 887 (methanol), 702 (ethanol), 241 (benzene).', 'required': False, 'type': ['integer', 'null']}, 'compound_name': {'description': "Compound name (used if cid is not provided). Examples: 'arsenic', 'methanol', 'cyanide', 'chlorine'.", 'required': False, 'type': ['string', 'null']}}, 'required': [], 'type': 'object'}
- PubChem_get_compound_2D_image_by_CID signature={'properties': {'cid': {'description': 'Compound ID to get image for, e.g., 2244.', 'required': True, 'type': 'integer'}, 'image_size': {'default': '200x200', 'description': 'Optional parameter, image size, like "200x200" (default).', 'required': True, 'type': 'string'}}, 'required': ['cid', 'image_size'], 'type': 'object'}
- ChEMBL_get_compound_record_activities signature={'properties': {'compound_record_id__exact': {'description': 'ChEMBL compound record ID. To find a compound record ID, use ChEMBL_get_compound_record or search activities.', 'required': True, 'type': 'string'}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}}, 'required': ['compound_record_id__exact'], 'type': 'object'}
- ChEMBL_get_molecule_targets signature={'properties': {'limit': {'default': 500, 'description': 'Maximum number of activity records to fetch for target deduplication (default 500).', 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Alias for molecule_chembl_id__exact. ChEMBL molecule ID.', 'required': False, 'type': 'string'}, 'molecule_chembl_id__exact': {'description': "ChEMBL molecule ID (e.g., 'CHEMBL25' for aspirin). To find a molecule ID, use ChEMBL_search_molecules. Alias: molecule_chembl_id.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_assay_activities signature={'properties': {'assay_chembl_id__exact': {'description': "ChEMBL assay ID (e.g., 'CHEMBL615117'). To find an assay ID, use ChEMBL_search_assays or ChEMBL_get_target_assays.", 'required': True, 'type': 'string'}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}}, 'required': ['assay_chembl_id__exact'], 'type': 'object'}
- PubChem_get_associated_patents_by_CID signature={'properties': {'cid': {'description': 'PubChem compound ID to query, e.g., 2244 (Aspirin).', 'required': True, 'type': 'integer'}}, 'required': ['cid'], 'type': 'object'}
- PubChem_search_compounds_by_similarity signature={'properties': {'max_results': {'default': 10, 'description': 'Maximum number of CIDs to return (default: 10, max: 10000).', 'required': False, 'type': 'integer'}, 'smiles': {'description': 'SMILES expression of target molecule.', 'required': True, 'type': 'string'}, 'threshold': {'default': 0.9, 'description': 'Similarity threshold (between 0 and 1), e.g., 0.9 means 90% similarity.', 'required': True, 'type': 'number'}}, 'required': ['smiles', 'threshold'], 'type': 'object'}
- PubChem_get_CID_by_compound_name signature={'properties': {'compound_name': {'description': 'Alias for name. The compound name to look up.', 'required': False, 'type': 'string'}, 'name': {'description': 'Chemical compound name (e.g., "Aspirin", "Acetaminophen") or IUPAC name. Do not use disease names or medical conditions.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- PubChem_get_CID_by_SMILES signature={'properties': {'smiles': {'description': 'SMILES expression (e.g., "CC(=O)OC1=CC=CC=C1C(=O)O" corresponds to aspirin).', 'required': True, 'type': 'string'}}, 'required': ['smiles'], 'type': 'object'}
- PubChem_search_compounds_by_substructure signature={'properties': {'max_results': {'default': 10, 'description': 'Maximum number of CIDs to return (default: 10, max: 10000).', 'required': False, 'type': 'integer'}, 'smiles': {'description': 'SMILES of substructure (e.g., "c1ccccc1" corresponds to benzene ring).', 'required': True, 'type': 'string'}}, 'required': ['smiles'], 'type': 'object'}
- ChEMBL_search_drugs signature={'properties': {'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'max_phase': {'description': 'Filter by maximum development phase (0-4)', 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Filter by ChEMBL molecule ID (e.g., "CHEMBL1201581" for adalimumab).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'query': {'description': 'Drug name to search for (partial match, case-insensitive). E.g., "sotorasib", "olaparib", "imatinib".', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_molecule signature={'properties': {'chembl_id': {'description': "ChEMBL molecule ID, e.g., 'CHEMBL25'", 'required': False, 'type': 'string'}, 'format': {'default': 'json', 'description': 'Response format', 'enum': ['json', 'xml', 'yaml'], 'required': False, 'type': 'string'}, 'molecule_chembl_id': {'description': 'Alias for chembl_id. ChEMBL molecule ID, e.g., CHEMBL1229517.', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_activity signature={'properties': {'activity_id': {'description': 'ChEMBL activity ID', 'required': True, 'type': 'string'}}, 'required': ['activity_id'], 'type': 'object'}
- ChEMBL_get_target signature={'properties': {'format': {'default': 'json', 'enum': ['json', 'xml', 'yaml'], 'required': False, 'type': 'string'}, 'target_chembl_id': {'description': "ChEMBL target ID (e.g., 'CHEMBL2074'). To find a target ID, use ChEMBL_search_targets with a target name or gene symbol.", 'required': True, 'type': 'string'}}, 'required': ['target_chembl_id'], 'type': 'object'}
- ChEMBL_search_targets signature={'properties': {'fields': {'description': "Optional list of ChEMBL target fields to include in each returned target object (projection). ToolUniverse maps this to ChEMBL's `only` query parameter (comma-separated). Supported fields: target_chembl_id, pref_name, organism, target_type, target_components.", 'items': {'enum': ['target_chembl_id', 'pref_name', 'organism', 'target_type', 'target_components'], 'type': 'string'}, 'required': False, 'type': 'array', 'uniqueItems': True}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'organism': {'description': "Filter by organism (e.g., 'Homo sapiens')", 'required': False, 'type': 'string'}, 'pref_name__contains': {'description': 'Filter by target name (contains)', 'required': False, 'type': 'string'}, 'target_chembl_id': {'description': 'Filter by target ChEMBL ID', 'required': False, 'type': 'string'}, 'target_type': {'description': "Filter by target type (e.g., 'SINGLE PROTEIN', 'PROTEIN COMPLEX')", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_search_assays signature={'properties': {'assay_chembl_id': {'description': 'Filter by assay ChEMBL ID', 'required': False, 'type': 'string'}, 'assay_type': {'description': "Filter by assay type (e.g., 'B', 'F', 'A')", 'required': False, 'type': 'string'}, 'fields': {'description': "Optional list of ChEMBL assay fields to include in each returned assay object (projection). ToolUniverse maps this to ChEMBL's `only` query parameter (comma-separated). Supported fields: assay_chembl_id, description, assay_type, confidence_score, target_chembl_id, assay_organism, bao_label.", 'items': {'enum': ['assay_chembl_id', 'description', 'assay_type', 'confidence_score', 'target_chembl_id', 'assay_organism', 'bao_label'], 'type': 'string'}, 'required': False, 'type': 'array', 'uniqueItems': True}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'target_chembl_id': {'description': 'Filter by target ChEMBL ID', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}

# TARGET SKILL TO CONVERT
---
name: tooluniverse-chemical-compound-retrieval
description: Retrieve chemical compound data from PubChem and ChEMBL with disambiguation, cross-referencing, and stereochemistry handling. Use for resolving compound names to SMILES/InChI/CID/ChEMBL IDs, fetching molecular properties, distinguishing isomers/stereo forms, and cross-validating identity across databases. Always use English compound names; flags ambiguous queries (e.g., Vitamin D has multiple forms).
disable-model-invocation: true
---

# Chemical Compound Information Retrieval

Retrieve comprehensive chemical compound data with proper disambiguation and cross-database validation.

**LOOK UP DON'T GUESS**: Never assume a CID, ChEMBL ID, or molecular property value. Always retrieve from PubChem/ChEMBL.

**English-first**: Always use English compound names in tool calls. Respond in user's language.

## Domain Reasoning: Disambiguation

"Aspirin" = one compound. "Vitamin D" = multiple forms (D2/D3/active metabolite). For generic class names (steroids, vitamins, acids), present candidates and confirm before proceeding.

---

## Workflow

```
Phase 0: Clarify (only if highly ambiguous -- skip for unambiguous names or specific IDs)
Phase 1: Disambiguate → resolve PubChem CID + ChEMBL ID
Phase 2: Retrieve data (silent)
Phase 3: Report compound profile
```

### Phase 1: Disambiguation

```python
# By name
result = tu.tools.PubChem_get_CID_by_compound_name(compound_name=name)
# By SMILES
result = tu.tools.PubChem_get_CID_by_SMILES(smiles=smiles)
# Cross-reference
chembl_result = tu.tools.ChEMBL_search_compounds(query=name, limit=5)
```

Verify: CID + ChEMBL ID + canonical SMILES + stereochemistry + salt forms.

### Phase 2: Data Retrieval

**PubChem**: `PubChem_get_compound_properties_by_CID`, `PubChemBioAssay_get_assay_summary`, `PubChemTox_get_acute_effects`, `PubChem_get_compound_2D_image_by_CID`

**ChEMBL**: `ChEMBL_get_compound_record_activities`, `ChEMBL_get_molecule_targets`, `ChEMBL_get_assay_activities`

**Optional**: `PubChem_get_associated_patents_by_CID`, `PubChem_search_compounds_by_similarity`

### Phase 3: Report

Compound Profile with: Identity (CID, ChEMBL ID, IUPAC, SMILES), Chemical Properties (MW, LogP, HBD, HBA, PSA, Lipinski), Bioactivity (targets, IC50/Ki), Drug Info (if approved), Data Sources.

---

## Fallback Chains

| Primary | Fallback |
|---------|----------|
| PubChem name lookup | ChEMBL search → SMILES → PubChem_get_CID_by_SMILES |
| ChEMBL bioactivity | PubChem bioassay summary |
| Drug label | Note "unavailable" |

---

## Evidence Grading

| Grade | Criteria |
|-------|----------|
| **Confirmed** | CID + ChEMBL cross-match, InChI/SMILES agree |
| **Probable** | CID found, partial ChEMBL match |
| **Uncertain** | Single database only, or multiple CIDs |
| **Unverified** | No cross-reference, single-source |

**Bioactivity**: ChEMBL > PubChem BioAssay for curated data. IC50/Ki < 100nM = potent, 100nM-1uM = moderate, >10uM = weak. Lipinski violations reduce oral bioavailability but don't disqualify.

---

## SMILES Verification

Always verify novel SMILES: `python3 src/tooluniverse/tools/smiles_verifier.py --smiles "SMILES_STRING"`. Invalid SMILES produce wrong results or cryptic errors.

---

## Tool Reference

**PubChem**: `PubChem_get_CID_by_compound_name`, `PubChem_get_CID_by_SMILES`, `PubChem_get_compound_properties_by_CID`, `PubChem_get_compound_2D_image_by_CID`, `PubChemBioAssay_get_assay_summary`, `PubChemTox_get_acute_effects`, `PubChem_get_associated_patents_by_CID`, `PubChem_search_compounds_by_similarity`, `PubChem_search_compounds_by_substructure`

**ChEMBL**: `ChEMBL_search_drugs`, `ChEMBL_get_molecule`, `ChEMBL_get_activity`, `ChEMBL_get_target`, `ChEMBL_search_targets`, `ChEMBL_search_assays`


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
