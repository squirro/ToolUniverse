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
- ChEMBL_get_drug_mechanisms signature={'properties': {'chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL ID (e.g., "CHEMBL3301622").', 'required': False, 'type': 'string'}, 'drug_chembl_id': {'description': 'ChEMBL drug/molecule ID (e.g., "CHEMBL1201581" for adalimumab, "CHEMBL4535757" for sotorasib).', 'required': False, 'type': 'string'}, 'drug_name': {'description': 'Drug name for automatic ChEMBL ID lookup (e.g., "trastuzumab", "lapatinib", "aspirin"). Case-insensitive. Triggers internal ChEMBL molecule search â\x80\x94 use drug_chembl_id if you already know the ID.', 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'molecule_chembl_id': {'description': 'Alias for drug_chembl_id. ChEMBL molecule ID (e.g., "CHEMBL25" for aspirin).', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- KEGG_get_drug signature={'properties': {'drug_id': {'description': "KEGG drug ID in D##### format (e.g., 'D00109' for aspirin, 'D01441' for imatinib, 'D04966' for metformin).", 'required': True, 'type': 'string'}}, 'required': ['drug_id'], 'type': 'object'}
- DailyMed_get_spl_by_setid signature={'properties': {'format': {'default': 'xml', 'description': "Return format, only supports 'xml'.", 'enum': ['xml'], 'required': False, 'type': 'string'}, 'setid': {'description': 'SPL Set ID to query.', 'format': 'uuid', 'required': True, 'type': 'string'}}, 'required': ['setid'], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- drugbank_get_drug_interactions_by_drug_name_or_id

# TARGET SKILL TO CONVERT
---
name: tooluniverse-drug-drug-interaction
description: Assess drug-drug interactions — CYP metabolic interactions (substrate/inhibitor/inducer), transporter (P-gp, BCRP, OATP) effects, pharmacodynamic synergy/antagonism, clinical significance scoring, and management recommendations. Use for polypharmacy review, prescribing decision support, and safety analysis when adding or switching drugs.
disable-model-invocation: true
---

# Drug-Drug Interaction Prediction & Risk Assessment

Systematic analysis of drug-drug interactions with evidence-based risk scoring, mechanism identification, and clinical management recommendations.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create DDI_risk_report.md FIRST, then populate progressively
2. **Bidirectional analysis** - Always analyze A→B and B→A interactions (effects may differ)
3. **Evidence grading** - Grade all DDI claims by evidence quality (★★★ FDA label, ★★☆ clinical study, ★☆☆ theoretical)
4. **Risk scoring** - Multi-dimensional scoring (0-100) combining mechanism + severity + clinical evidence
5. **Patient safety focus** - Provide actionable clinical guidance, not just theoretical interactions
6. **Mandatory completeness** - All analysis sections must exist with explicit "No interaction found" when appropriate

---

## LOCAL PHARMACOLOGY REFERENCE (USE FIRST)

Before querying any external database, consult the local reference script for instant answers on CYP/UGT roles and known critical interactions:

```
scripts/pharmacology_ref.py   (no external dependencies, runs offline)

# Q927 pattern — valproate + lamotrigine:
python scripts/pharmacology_ref.py --type interaction --drug1 "valproate" --drug2 "lamotrigine"

# What does a drug do to UGT enzymes?
python scripts/pharmacology_ref.py --type ugt_inhibitor --drug "valproate"

# What enzymes metabolise a drug?
python scripts/pharmacology_ref.py --type ugt_substrate --drug "lamotrigine"
python scripts/pharmacology_ref.py --type cyp_substrate --drug "warfarin"

# Which drugs inhibit / induce a specific CYP?
python scripts/pharmacology_ref.py --type cyp_inhibitor --enzyme "CYP3A4"
python scripts/pharmacology_ref.py --type cyp_inducer  --enzyme "CYP2C9"

# Narrow therapeutic index checklist:
python scripts/pharmacology_ref.py --type narrow_ti

# All known interactions for one drug:
python scripts/pharmacology_ref.py --type all_interactions --drug "lamotrigine"
```

**Covered interactions include** (severity / mechanism):
| Pair | Severity | Key mechanism |
|------|----------|---------------|
| valproate + lamotrigine | **Major** | UGT1A4 inhibition → 2× lamotrigine levels + SJS risk |
| carbamazepine + lamotrigine | Major | UGT1A4 induction → 50% ↓ lamotrigine |
| oral contraceptives + lamotrigine | Major | UGT1A4 induction → 50% ↓ lamotrigine |
| valproate + phenytoin | Major | CYP2C9 inhibition + protein displacement |
| carbamazepine + valproate | Moderate | Epoxide hydrolase inhibition → toxic metabolite ↑ |
| simvastatin + ketoconazole | **Contraindicated** | CYP3A4 inhibition → rhabdomyolysis |
| simvastatin + clarithromycin | Contraindicated | CYP3A4 inhibition → rhabdomyolysis |
| rifampin + warfarin | Major | CYP2C9 induction → INR collapse |
| amiodarone + warfarin | Major | CYP2C9 inhibition → INR rise |
| clopidogrel + omeprazole | Moderate | CYP2C19 inhibition → reduced antiplatelet activation |
| quinidine + digoxin | Major | P-gp inhibition → 2× digoxin levels |
| lithium + NSAIDs | Major | Reduced renal clearance → lithium toxicity |
| fluoxetine + MAOIs | Contraindicated | Serotonin syndrome |

The script also covers UGT2B7 substrates (morphine, zidovudine) inhibited by valproate, UGT1A1 induction by rifampin, and the complete narrow therapeutic index list with monitoring parameters.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

## New Symptom After New Medication: First-Line Reasoning

When a patient develops NEW symptoms after starting a new medication, the FIRST question is: could the new drug be interacting with an existing medication? Specifically check: (1) Does the new drug inhibit metabolism of an existing drug? (2) Does the new drug have additive pharmacodynamic effects?

---

## When to Use This Skill

Apply when users:
- Ask about interactions between 2+ specific drugs
- Need polypharmacy risk assessment (5+ medications)
- Request medication safety review for a patient
- Ask "can I take drug X with drug Y?"
- Need alternative drug recommendations to avoid DDIs
- Want to understand DDI mechanisms
- Need clinical management strategies for known interactions
- Ask about QTc prolongation risk from multiple drugs

---

## Clinical Reasoning Framework

Before querying any database, apply this reasoning framework to predict interactions mechanistically.

### The Perpetrator-Victim Model

In every drug interaction, identify two roles:
- **PERPETRATOR**: the drug causing the change (the inhibitor, inducer, or pharmacodynamic amplifier)
- **VICTIM**: the drug being affected (the one whose levels or effects change)

For each drug pair, ask these questions in order:

1. **Does the perpetrator change how the victim is absorbed, distributed, metabolized, or eliminated?** If yes, this is a pharmacokinetic interaction. Determine which enzyme or transporter is involved (CYP450, UGT, P-gp, OATP, etc.).
2. **Is the perpetrator an inhibitor or an inducer of that pathway?**
   - Inhibitor → victim levels go UP → predict increased efficacy or toxicity
   - Inducer → victim levels go DOWN → predict reduced efficacy or therapeutic failure
3. **What happens clinically when the victim's level changes?** Predict the downstream consequence: toxicity from supratherapeutic levels, or treatment failure from subtherapeutic levels.
4. **Always check the reverse direction.** Analyze B→A as well as A→B. The perpetrator-victim relationship may be asymmetric or bidirectional.

Special case -- **Prodrugs**: If the victim is a prodrug that requires metabolic activation, inhibiting its activating enzyme reduces efficacy (not toxicity). Inducing its activating enzyme may increase efficacy or toxicity of the active metabolite.

---

### Phase II Metabolism: Glucuronidation Interactions (UGT Enzymes)

Most DDI reasoning focuses on CYP450 (Phase I metabolism), but **Phase II conjugation reactions — especially glucuronidation via UGT enzymes — cause some of the most dangerous drug interactions**. These are frequently missed because agents default to CYP-centric reasoning.

**Core principle**: UGT enzymes (UGT1A4, UGT2B7, UGT1A1, etc.) conjugate drugs with glucuronic acid for renal elimination. When a UGT inhibitor is co-administered with a UGT substrate, the substrate accumulates because its primary elimination pathway is blocked.

**The valproate + lamotrigine paradigm (IDX 927 pattern):**
1. Lamotrigine is primarily metabolized by **UGT1A4** glucuronidation (>90% of elimination).
2. Valproate is a potent **UGT1A4 inhibitor**.
3. Co-administration doubles lamotrigine levels (t1/2 increases from ~25h to ~60h).
4. Clinical consequence: **Stevens-Johnson syndrome (SJS) / toxic epidermal necrolysis (TEN)** — a life-threatening dermatologic emergency.
5. Mechanism: **inhibition of lamotrigine glucuronidation** — NOT a CYP interaction.
6. Management: When adding valproate to lamotrigine, HALVE the lamotrigine dose. Titrate slowly.

**Other critical UGT interactions:**
- **Valproate + morphine/zidovudine**: Valproate inhibits UGT2B7 → increased morphine/zidovudine levels
- **Valproate + phenytoin**: Dual mechanism — CYP2C9 inhibition + protein binding displacement → unpredictable phenytoin levels
- **Carbamazepine + lamotrigine**: Carbamazepine INDUCES UGT1A4 → lamotrigine levels DROP by ~50% (opposite direction from valproate)
- **Oral contraceptives + lamotrigine**: Ethinylestradiol induces UGT1A4 → lamotrigine levels drop; when OCP stopped (pill-free week), lamotrigine rebounds
- **Rifampin + many UGT substrates**: Rifampin induces UGT1A1, UGT2B7 → decreased levels of morphine, bilirubin conjugation increased

**Reasoning algorithm for UGT interactions:**
1. Is the victim drug primarily cleared by glucuronidation? (Check: lamotrigine, morphine, lorazepam, zidovudine, bilirubin)
2. Is the perpetrator a UGT inhibitor (valproate, probenecid, atazanavir) or inducer (carbamazepine, rifampin, phenytoin, OCP)?
3. Predict direction: inhibitor → victim levels UP; inducer → victim levels DOWN
4. Assess clinical significance: narrow therapeutic index victims (lamotrigine, morphine) are HIGH risk

Use `scripts/pharmacology_ref.py --type ugt_inhibitor --drug "[drug]"` and `--type ugt_substrate --drug "[drug]"` for rapid UGT lookup.

### Enzyme Induction and Inhibition: Cascading Effects

When a patient is on 3+ drugs, interactions can cascade. A common pattern:

**Scenario**: Patient on Drug A (CYP3A4 substrate) + Drug B (CYP3A4 inducer) at steady state. Drug C (CYP3A4 inhibitor) is added.
- Drug B was keeping Drug A levels LOW (via induction).
- Drug C now inhibits CYP3A4 → Drug A levels RISE, but the magnitude depends on whether Drug C overcomes Drug B's induction.
- If Drug B is later STOPPED, Drug A levels rise FURTHER (induction wears off over 1-2 weeks while inhibition persists).

**Key reasoning principles for cascading effects:**
1. **Induction takes days to weeks to develop** (requires new enzyme protein synthesis) and **days to weeks to resolve** (enzyme protein must degrade). Plan dose adjustments PROSPECTIVELY.
2. **Inhibition is typically immediate** (competitive binding at enzyme active site). Dose adjustment needed at the time of co-administration.
3. **When an inducer is stopped**, all drugs that were dose-adjusted upward to compensate for the induction now become SUPRATHERAPEUTIC. This is when toxicity appears — often 1-2 weeks after stopping the inducer.
4. **Multiple inhibitors of the same enzyme are NOT simply additive** — the strongest inhibitor dominates. But multiple inhibitors of DIFFERENT enzymes affecting the same victim drug can be synergistic.

### ADR Attribution: Which Mechanism Caused the Problem?

When a patient on multiple medications develops an adverse drug reaction:

1. **Timeline**: When did the ADR appear relative to the newest medication change? (hours = PK inhibition or PD; weeks = induction offset)
2. **Which drug is the likely VICTIM?** The victim is the drug whose toxicity profile matches the ADR. Seizures → check anticonvulsant levels. Bleeding → check anticoagulant levels.
3. **Which drug is the likely PERPETRATOR?** The perpetrator is the most recently added/changed drug, OR a recently STOPPED inducer.
4. **What is the mechanism?** Look up the victim's metabolic pathway (CYP? UGT? renal?). Then check if the perpetrator affects that pathway.
5. **Validate**: Does the predicted mechanism match the clinical magnitude? A moderate CYP inhibitor should cause a 2-3x level increase; a strong inhibitor 5x+. If the observed effect is much larger or smaller, reconsider the mechanism.

**Example (IDX 927)**: Elderly patient on lamotrigine develops seizures and rash after adding valproate.
- Victim = lamotrigine (the drug causing toxicity — SJS/rash, and paradoxical seizures from toxicity)
- Perpetrator = valproate (the newly added drug)
- Mechanism = UGT1A4 inhibition → lamotrigine glucuronidation blocked → 2x lamotrigine levels → SJS
- Answer: "Inhibition of lamotrigine glucuronidation" — NOT phenytoin hypersensitivity or CYP interaction

### Timeline Reasoning

Use the temporal pattern of symptoms to narrow the mechanism:

- **Symptoms within hours of adding the new drug** → Think pharmacokinetic inhibition (competitive, immediate onset) or direct pharmacodynamic interaction (additive receptor effects)
- **Symptoms emerging over 1-2 weeks** → Think enzyme induction (requires new protein synthesis, slow onset, slow offset)
- **Symptoms that appear regardless of timing** → Think pharmacodynamic interaction (both drugs independently act on the same receptor, pathway, or organ system)
- **Symptoms appearing days after stopping a drug** → Think inducer offset (enzyme levels returning to baseline, victim drug levels rising)

---

### The Three Questions

For any suspected drug interaction, classify it by asking:

**1. Is this pharmacokinetic?** (One drug changes the LEVEL of another)
- Mechanism: absorption changes, enzyme inhibition/induction, transporter competition, protein binding displacement, altered renal elimination
- Clue: measurable change in drug plasma concentration
- Action: check which metabolic enzymes and transporters are involved

**2. Is this pharmacodynamic?** (Both drugs act on the SAME SYSTEM)
- Additive/synergistic: both drugs push the same physiological effect in the same direction (e.g., sedation, bleeding, QTc prolongation, serotonin activity, hypoglycemia)
- Antagonistic: drugs push in opposite directions on the same target (e.g., a blocker vs. an agonist at the same receptor)
- Synergistic toxicity: different mechanisms converging on the same organ (e.g., one drug raises levels via PK while another damages the same tissue via PD)
- Electrolyte-mediated: one drug shifts electrolyte balance, sensitizing the patient to another drug's toxicity
- Clue: no change in plasma levels, but exaggerated or blunted clinical effect

**3. Is this pharmaceutical?** (Drugs interact BEFORE reaching the body)
- IV line incompatibility, chelation in the GI tract, pH-dependent degradation
- Clue: problem occurs at the point of administration, not after absorption

Most clinically significant interactions are pharmacokinetic, pharmacodynamic, or both simultaneously. Always consider mixed PK+PD interactions, which tend to be the most dangerous.

---

### Severity Reasoning

Assess severity by reasoning about the victim drug's properties, not by memorizing lists:

**Therapeutic index determines risk tolerance:**
- Narrow therapeutic index drugs (e.g., warfarin, lithium, digoxin, phenytoin, theophylline, cyclosporine, aminoglycosides) → even small level changes are clinically dangerous. Any PK interaction with these drugs is at least moderate severity.
- Wide therapeutic index drugs → moderate level changes (2-3x) are often tolerable. Severity depends on the magnitude of the change and the specific toxicity profile.

**Prodrug logic inverts the prediction:**
- Inhibiting activation of a prodrug = loss of efficacy, not toxicity. This is dangerous when the prodrug treats a life-threatening condition (e.g., antiplatelet therapy, cancer treatment).

**Severity classification process:**
- **Contraindicated**: Documented life-threatening toxicity. The combination should not be used.
- **Major**: High risk of serious harm or permanent damage. Avoid when alternatives exist; if unavoidable, requires intensive monitoring and dose adjustment with documented rationale.
- **Moderate**: May worsen the patient's condition or require additional treatment. Manageable with dose adjustment and increased monitoring frequency.
- **Minor**: Nuisance-level effects with limited clinical significance. Usually no dose change required.

**Management follows directly from the mechanism:**
- If the perpetrator is an inhibitor → reduce the victim's dose proportionally to inhibition strength, or substitute the perpetrator with a non-inhibiting alternative
- If the perpetrator is an inducer → increase the victim's dose (guided by therapeutic drug monitoring), or substitute the perpetrator; remember to readjust when the inducer is stopped
- If the interaction is pharmacodynamic → neither drug's dose fixes the problem; substitute one drug or add protective monitoring (e.g., ECG for QTc, INR for bleeding)

---

## Critical Workflow Requirements

### 1. Report-First Approach (MANDATORY)

**DO NOT** show intermediate tool outputs or search processes. Instead:

1. **Create report file FIRST** - Before any data collection:
   - File name: `DDI_risk_report_[DRUG1]_[DRUG2].md` (or `_polypharmacy.md` for 3+)
   - Initialize with all section headers
   - Add placeholder: `[Analyzing...]` in each section

2. **Apply clinical reasoning FIRST** - Before running tools, reason through:
   - CYP roles of each drug (substrate/inhibitor/inducer)
   - PD overlap (same receptor, same organ toxicity)
   - Flag high-risk combinations from the reference table

3. **Progressively update** - As database data is gathered:
   - Replace `[Analyzing...]` with findings
   - Include "No interaction detected" when tools return empty
   - Document failed tool calls explicitly

4. **Final deliverable** - Complete markdown report with recommendations

---

## Tool Workflow

### Phase 1: Drug Identification

1. Resolve generic names, ChEMBL IDs, DrugBank IDs
2. Identify drug class and mechanism of action for each drug
3. Apply CYP450 reasoning framework above BEFORE database queries

### Phase 2: PK Interaction Analysis

Query tools in this order:
1. `ChEMBL_get_drug_mechanisms` or `KEGG_get_drug` for CYP substrate/inhibitor/inducer data
2. `drugbank_get_drug_interactions_by_drug_name_or_id` for known transporter interactions (P-gp, OATP, OAT, OCT)
3. Cross-reference with PharmGKB for pharmacogenomic context

**Transporter interactions** (check when CYP analysis incomplete):
- P-glycoprotein (P-gp / ABCB1): substrates (digoxin, dabigatran, fexofenadine); inhibitors (amiodarone, cyclosporine, quinidine, verapamil); inducers (rifampin)
- OATP1B1: substrates (statins, methotrexate); inhibitors (cyclosporine, gemfibrozil)

### Phase 3: PD Interaction Analysis

1. Identify receptor targets for each drug
2. Check for overlapping receptor activity (additive/synergistic)
3. Check for opposing receptor activity (antagonistic)
4. Assess shared organ toxicity pathways

### Phase 4: Clinical Evidence Assessment

1. FDA label review via `DailyMed_get_spl_by_setid` - highest evidence tier
2. Clinical study data via `PubMed_search_articles` - second tier
3. Theoretical/mechanistic - flag clearly as ★☆☆

### Phase 5: Risk Scoring

Risk Score (0-100):
- Base score from severity: Major=60, Moderate=35, Minor=10
- Evidence modifier: FDA label +20, clinical study +10, theoretical +0
- Frequency modifier: Common (>10%) +10, Uncommon (1-10%) +5, Rare (<1%) +0
- Patient factor modifier: +5 per applicable high-risk factor

### Phase 6: Alternatives and Monitoring

For each Major/Contraindicated interaction:
1. Suggest specific alternative drugs that avoid the interaction mechanism
2. Provide dose adjustment recommendations if substitution not possible
3. Define monitoring parameters: which labs, which symptoms, how often

---

## Output Report Structure

1. Executive Summary (interaction severity, key risk)
2. Drug Profiles (class, mechanism, CYP roles)
3. PK Interactions (CYP, transporters, mechanisms)
4. PD Interactions (additive, synergistic, antagonistic)
5. Clinical Evidence (FDA label, studies, case reports)
6. Risk Score (0-100 with breakdown)
7. Management Recommendations (avoid / dose adjust / monitor)
8. Monitoring Plan (labs, timeline, thresholds)
9. Alternative Drugs (mechanism-free alternatives)
10. Patient Counseling Points

---

## Success Criteria

Before finalizing DDI report:

- All drug names resolved to standard identifiers
- CYP450 reasoning applied before database queries
- Bidirectional analysis completed (A→B and B→A)
- All mechanism types assessed (CYP, transporters, PD)
- FDA label warnings extracted
- Clinical literature searched
- Evidence grades assigned (★★★, ★★☆, ★☆☆)
- Risk score calculated (0-100)
- Severity classified (Contraindicated/Major/Moderate/Minor)
- Primary management recommendation provided
- Alternative drugs suggested
- Monitoring parameters defined
- Patient counseling points included
- All sections completed (no [Analyzing...] placeholders)
- Data sources cited throughout


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
