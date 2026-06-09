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
- PharmGKB_search_drugs signature={'properties': {'drug': {'description': 'Alias for query. Drug name to search.', 'required': False, 'type': 'string'}, 'drug_name': {'description': "Alias for query. Drug name to search (e.g., 'warfarin', 'metformin').", 'required': False, 'type': 'string'}, 'name': {'description': 'Alias for query. Drug name to search.', 'required': False, 'type': 'string'}, 'query': {'description': "Drug name or PharmGKB Chemical ID (e.g., 'warfarin', 'PA452637'). Aliases: drug_name, name, drug.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_drug signature={'properties': {'drug_chembl_id': {'description': "ChEMBL drug ID, e.g., 'CHEMBL1201581'", 'required': True, 'type': 'string'}, 'format': {'default': 'json', 'enum': ['json', 'xml', 'yaml'], 'required': False, 'type': 'string'}}, 'required': ['drug_chembl_id'], 'type': 'object'}
- DailyMed_parse_adverse_reactions signature={'properties': {'drug_name': {'description': 'Drug name for automatic Set ID lookup (alternative to setid)', 'required': False, 'type': 'string'}, 'operation': {'const': 'parse_adverse_reactions', 'description': 'Operation type (fixed)', 'required': False}, 'setid': {'description': 'SPL Set ID to parse', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- DailyMed_parse_dosing signature={'properties': {'drug_name': {'description': 'Drug name for automatic Set ID lookup (alternative to setid)', 'required': False, 'type': 'string'}, 'operation': {'const': 'parse_dosing', 'description': 'Operation type (fixed)', 'required': False}, 'setid': {'description': 'SPL Set ID to parse', 'format': 'uuid', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- OpenTargets_get_associated_targets_by_drug_chemblId

# TARGET SKILL TO CONVERT
---
name: tooluniverse-drug-mechanism-research
description: Trace drug mechanism of action — primary target → downstream signaling → pathway perturbation → tissue/organ effect → clinical outcome. Uses DrugBank, ChEMBL, KEGG, Reactome, STRING. Use for understanding how a drug works, identifying off-target effects, mechanism-based combination therapy design, and writing mechanism sections of reports.
triggers:
  - keywords: [mechanism of action, drug target, pharmacology, pathway, pharmacogenomics, drug interaction, DailyMed, CPIC, MOA, off-target]
  - patterns: ["how does .* work", "mechanism of action", "drug target", "pathway context", "clinical pharmacology", "drug-drug interaction", "pharmacogenomic", "off-target effect"]
disable-model-invocation: true
---

# Drug Mechanism of Action Investigation

## Investigation Philosophy

Drug mechanism research follows one core question chain:

**Target -> Downstream Effect -> Pathway -> Organ Effect -> Clinical Outcome**

Start with the drug's primary target. What receptor, enzyme, or transporter does it bind? Then trace forward: what does inhibiting/activating that target do immediately? What pathway is disrupted? What organ-level change results? What does the patient experience?

The LLM already knows drug pharmacology. This skill teaches HOW TO INVESTIGATE using available tools, not what mechanisms exist.

## When to Use

- "What is the mechanism of action of [drug]?"
- "What are the molecular targets of [drug]?"
- "Which pathways are affected by [drug]?"
- "What pharmacogenomic interactions exist for [drug]?"
- "What are the off-targets of [drug]?"
- "Compare mechanisms of [drug A] vs [drug B]"

## NOT for (use other skills)

- Drug safety/adverse events profiling -> `tooluniverse-adverse-event-detection`
- Drug repurposing/new indications -> `tooluniverse-drug-repurposing`
- Target druggability assessment -> `tooluniverse-drug-target-validation`
- Network pharmacology/polypharmacology -> `tooluniverse-network-pharmacology`
- CPIC dosing guidelines specifically -> `tooluniverse-pharmacogenomics`

---

## Step 1: Resolve the Drug

Before investigating mechanism, resolve the drug name to a canonical identifier. You need a ChEMBL ID for most downstream queries.

```python
# Resolve drug name to ChEMBL ID
result = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName="metformin")
# Alternative: OpenTargets_get_drug_chembId_by_generic_name(drugName="metformin")

# Get PharmGKB ID (needed for PGx queries)
result = tu.tools.PharmGKB_search_drugs(query="metformin")
```

**Fallback**: If OpenTargets returns no hits, try `PharmGKB_search_drugs` or `ChEMBL_get_drug` with a known ChEMBL ID.

---

## Step 2: Identify the Primary Target

The first question: what does this drug bind to, and what does it do to that target?

Two complementary sources give you this:

```python
# OpenTargets: quick summary of MOA with target gene symbols
moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId="CHEMBL1431")
for row in moa["data"]["drug"]["mechanismsOfAction"]["rows"]:
    print(f"{row['mechanismOfAction']} ({row['actionType']}) -> {row['targetName']}")
    for t in row.get("targets", []):
        print(f"  Target gene: {t['approvedSymbol']} ({t['id']})")

# ChEMBL: detailed MOA with literature references and direct_interaction flag
mechs = tu.tools.ChEMBL_get_drug_mechanisms(drug_chembl_id__exact="CHEMBL1431")
for m in mechs["data"]["mechanisms"]:
    print(f"MOA: {m['mechanism_of_action']}, Direct: {m['direct_interaction']}")
    print(f"  Refs: {[r['ref_id'] for r in m.get('mechanism_refs', [])]}")
```

**Key fields to extract**: action_type (INHIBITOR, AGONIST, ANTAGONIST, etc.), target gene symbol, direct_interaction (boolean), and literature references.

**Known issue**: `OpenTargets_get_associated_targets_by_drug_chemblId` may fail (GraphQL schema change). Extract targets from the MOA results instead.

---

## Step 3: Assess Off-Target Effects

Most drugs bind more than one target at clinical concentrations. After identifying the primary target, ask: what other proteins does this drug interact with? Off-target binding explains many side effects and drug interactions.

```python
# ChEMBL bioactivity data shows binding affinity across targets
activities = tu.tools.ChEMBL_get_target_activities(target_chembl_id__exact="CHEMBL2364")

# STRING interaction partners reveal the target's protein network
partners = tu.tools.STRING_get_interaction_partners(identifiers="PRKAA1", species=9606)
```

**Reasoning strategy**: If ChEMBL MOA lists multiple targets, compare their action types. Same action type across related targets suggests on-pathway polypharmacology. Different action types suggest true off-target effects. The binding affinity (IC50/Ki from bioactivity data) tells you which targets matter at clinical doses -- nanomolar affinity is primary, micromolar is likely off-target.

---

## Step 4: Map to Pathway Context

A drug target does not work in isolation. Map it to its pathway to understand the breadth of effect.

**Key question**: Is the target upstream (affects many downstream genes, broader effects, more side effects) or downstream (narrow, specific effect)?

```python
# KEGG: find gene ID, then get pathways
genes = tu.tools.kegg_find_genes(keyword="PRKAA1", organism="hsa")
pathways = tu.tools.KEGG_get_gene_pathways(gene_id="hsa:5562")

# Reactome: map protein to pathways (needs UniProt ID)
reactome = tu.tools.Reactome_map_uniprot_to_pathways(uniprot_id="Q13131")

# WikiPathways: search by gene symbol
wp = tu.tools.WikiPathways_find_pathways_by_gene(gene="PRKAA1")

# STRING: functional annotations (GO terms, pathway memberships)
annot = tu.tools.STRING_get_functional_annotations(identifiers="PRKAA1", species=9606)
```

**For multi-target drugs**, run pathway enrichment to find convergent pathways:

```python
# Reactome enrichment (space-separated gene list, NOT array)
enrichment = tu.tools.ReactomeAnalysis_pathway_enrichment(identifiers="PRKAA1 PRKAA2 PRKAB1")

# STRING enrichment
enrichment = tu.tools.STRING_functional_enrichment(identifiers="PRKAA1 PRKAA2", species=9606)
```

**Reasoning strategy**: If multiple drug targets converge on the same pathway, that pathway is the drug's true mechanism. If targets are in different pathways, the drug has genuinely multi-pathway effects -- report each separately.

---

## Step 5: Get the Regulatory View (DailyMed)

Drug labels describe WHAT the drug does. This is the FDA-approved mechanism narrative.

DailyMed requires a two-step process: search for the drug to get a `setid`, then parse specific label sections.

```python
# Step 1: Get setid
spls = tu.tools.DailyMed_search_spls(drug_name="metformin")
setid = spls["data"][0]["setid"]

# Step 2: Parse the clinical pharmacology section (MOA, PK/PD, metabolism)
pharmacology = tu.tools.DailyMed_parse_clinical_pharmacology(
    operation="parse_clinical_pharmacology", setid=setid)

# Drug interactions from the label
interactions = tu.tools.DailyMed_parse_drug_interactions(
    operation="parse_drug_interactions", setid=setid)

# Contraindications
contra = tu.tools.DailyMed_parse_contraindications(
    operation="parse_contraindications", setid=setid)
```

**Other DailyMed parse tools**: `DailyMed_parse_adverse_reactions`, `DailyMed_parse_dosing`.

**Reasoning strategy**: The label's clinical pharmacology section often describes the mechanism differently from database entries. The label emphasizes clinically relevant effects; databases emphasize molecular detail. Both perspectives are needed.

---

## Step 6: Check Pharmacogenomics

Pharmacogenomic variants affect how a patient responds to the drug. This matters for mechanism because PGx genes are often the drug's metabolizing enzymes or targets.

```python
# CPIC gene-drug pairs (gold standard for PGx)
pairs = tu.tools.CPIC_search_gene_drug_pairs(gene_symbol="CYP2C19", cpiclevel="A", limit=20)
# Or search by drug
drug_info = tu.tools.CPIC_get_drug_info(name="clopidogrel")

# FDA PGx biomarkers (what's on the label)
fda_pgx = tu.tools.fda_pharmacogenomic_biomarkers(drug_name="clopidogrel", limit=100)
# Or find all drugs affected by a gene
fda_pgx = tu.tools.fda_pharmacogenomic_biomarkers(biomarker="CYP2D6", limit=100)

# PharmGKB gene details
gene_info = tu.tools.PharmGKB_search_genes(query="CYP2C19")
```

**Reasoning strategy**: CPIC Level A/B pairs have strong evidence and actionable guidelines. If a drug has CPIC Level A interactions, those genes are critical to its mechanism (usually metabolizing enzymes or direct targets). FDA PGx biomarkers tell you what's on the approved label.

---

## Step 7: Gather Literature Evidence

Literature describes WHY the mechanism works. Combine with labels (what) for a complete picture.

```python
# PubMed: returns a plain list of article dicts
articles = tu.tools.PubMed_search_articles(
    query="metformin mechanism of action AMPK mitochondrial", limit=10)

# EuropePMC: returns {status, data, metadata}
articles = tu.tools.EuropePMC_search_articles(
    query="metformin mechanism action mitochondrial", limit=10)

# Follow citation chains for seminal papers
citations = tu.tools.EuropePMC_get_citations(source="MED", identifier="12345678")
```

**Search strategy**: Start with "[drug] mechanism of action [primary target]". If the mechanism is debated, add the competing hypotheses as separate queries. Recent reviews (add "review" to query) give the current consensus.

---

## Step 8: Integrate and Report

### Evidence Hierarchy

- **Tier 1 (Regulatory)**: FDA label (DailyMed), CPIC Level A, FDA PGx biomarker
- **Tier 2 (Experimental)**: ChEMBL mechanisms with literature refs, binding data
- **Tier 3 (Database)**: OpenTargets MOA, pathway databases (KEGG/Reactome/WikiPathways)
- **Tier 4 (Literature)**: PubMed/EuropePMC articles

### Report Structure

```
## Drug Mechanism Report: [Drug Name]

### Drug Identity
- ChEMBL ID, PharmGKB ID, approval status

### Primary Mechanism
- Target: [gene symbol], Action: [INHIBITOR/AGONIST/etc.]
- Mechanism narrative (from DailyMed + databases)
- Direct interaction: yes/no

### Off-Target Effects
- Additional targets with action types and binding affinities
- Which off-targets explain known side effects

### Pathway Context
- Key pathways (from KEGG/Reactome/WikiPathways)
- Upstream vs downstream position of target
- Convergent pathways for multi-target drugs

### Pharmacogenomics
- CPIC gene-drug pairs with levels
- FDA PGx biomarkers

### Drug Interactions
- Mechanism-based interactions (enzyme inhibition/induction)
- Key interactions from DailyMed

### Evidence Summary
| Finding | Source | Tier |
|---------|--------|------|
| Primary MOA | ChEMBL + DailyMed | T1/T2 |
| Off-targets | ChEMBL bioactivity | T2 |
| Pathways | KEGG/Reactome | T3 |
| PGx | CPIC/FDA | T1 |
```

---

## Comparing Two Drugs

When comparing mechanisms, run Steps 2-4 for both drugs, then align:

1. **Same target, different action?** (e.g., agonist vs antagonist at the same receptor)
2. **Different targets, same pathway?** (e.g., both affect insulin signaling but at different nodes)
3. **Different pathways entirely?** (e.g., metformin on AMPK vs pioglitazone on PPAR-gamma)

```python
for drug in [("metformin", "CHEMBL1431"), ("pioglitazone", "CHEMBL595")]:
    moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=drug[1])
    clin = tu.tools.DailyMed_parse_clinical_pharmacology(drug_name=drug[0])
```

---

## Fallback Strategies

| Step | Primary Tool | Fallback |
|------|-------------|----------|
| Drug ID | OpenTargets_get_drug_id_description_by_name | PharmGKB_search_drugs |
| MOA | OpenTargets_get_drug_mechanisms_of_action_by_chemblId | ChEMBL_get_drug_mechanisms |
| Pathways | KEGG_get_gene_pathways | WikiPathways_find_pathways_by_gene, Reactome_map_uniprot_to_pathways |
| PGx | CPIC_search_gene_drug_pairs | fda_pharmacogenomic_biomarkers |
| Clinical info | DailyMed_parse_clinical_pharmacology | OpenTargets_get_drug_description_by_chemblId |
| DDI | DailyMed_parse_drug_interactions | PubMed_search_articles (DDI query) |
| Literature | PubMed_search_articles | EuropePMC_search_articles |

**MetaCyc note**: MetaCyc requires a paid account and is not available. Use KEGG, Reactome, or WikiPathways instead.


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
