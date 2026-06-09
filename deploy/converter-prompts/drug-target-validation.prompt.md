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
- MyGene_query_genes signature={'properties': {'fields': {'default': 'symbol,name,entrezgene,ensembl.gene,summary', 'description': 'Comma-separated list of fields to return. Common fields: symbol, name, entrezgene, ensembl.gene, summary, go, pathway, interpro.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query. Can be gene symbol (e.g., 'CDK2'), name ('cyclin dependent kinase'), Entrez ID ('1017'), or Ensembl ID ('ENSG00000123374'). Supports wildcards (*) and boolean operators (AND, OR, NOT).", 'required': True, 'type': 'string'}, 'size': {'default': 10, 'description': 'Maximum number of results to return (1-100).', 'required': False, 'type': 'integer'}, 'species': {'default': 'human', 'description': "Species filter. Use common name or NCBI taxonomy ID. Examples: 'human', 'mouse', '9606' (human), 'all'.", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- ensembl_lookup_gene signature={'properties': {'gene_id': {'description': "Ensembl gene ID or symbol (e.g., 'ENSG00000139618' or 'BRCA1'). If using a stable ID, the tool will automatically route to /lookup/id endpoint.", 'required': True, 'type': 'string'}, 'species': {'description': "Species name required for gene symbols (default 'homo_sapiens'). Examples: 'homo_sapiens', 'mus_musculus', 'rattus_norvegicus'", 'required': False, 'type': 'string'}}, 'required': ['gene_id'], 'type': 'object'}
- ensembl_get_xrefs signature={'properties': {'external_db': {'description': "Filter by external database name (optional, e.g., 'UniProt', 'RefSeq', 'HGNC')", 'required': False, 'type': 'string'}, 'id': {'description': "Ensembl ID (gene, transcript, or protein ID, e.g., 'ENSG00000139618', 'ENST00000380152', 'ENSP00000369497')", 'required': True, 'type': 'string'}, 'object_type': {'description': "Object type filter (optional, e.g., 'gene', 'transcript', 'translation')", 'required': False, 'type': 'string'}}, 'required': ['id'], 'type': 'object'}
- OpenTargets_get_target_id_description_by_name signature={'properties': {'targetName': {'description': 'The name of the target for which the ID is required.', 'required': True, 'type': 'string'}}, 'required': ['targetName'], 'type': 'object'}
- ChEMBL_search_targets signature={'properties': {'fields': {'description': "Optional list of ChEMBL target fields to include in each returned target object (projection). ToolUniverse maps this to ChEMBL's `only` query parameter (comma-separated). Supported fields: target_chembl_id, pref_name, organism, target_type, target_components.", 'items': {'enum': ['target_chembl_id', 'pref_name', 'organism', 'target_type', 'target_components'], 'type': 'string'}, 'required': False, 'type': 'array', 'uniqueItems': True}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'organism': {'description': "Filter by organism (e.g., 'Homo sapiens')", 'required': False, 'type': 'string'}, 'pref_name__contains': {'description': 'Filter by target name (contains)', 'required': False, 'type': 'string'}, 'target_chembl_id': {'description': 'Filter by target ChEMBL ID', 'required': False, 'type': 'string'}, 'target_type': {'description': "Filter by target type (e.g., 'SINGLE PROTEIN', 'PROTEIN COMPLEX')", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- UniProt_get_function_by_accession signature={'properties': {'accession': {'description': 'UniProtKB accession, e.g., P05067.', 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- UniProt_get_alternative_names_by_accession signature={'properties': {'accession': {'description': 'UniProtKB accession, e.g., P05067.', 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- OpenTargets_target_disease_evidence signature={'properties': {'disease_name': {'description': "Disease or phenotype name (e.g., 'Crohn disease', 'breast carcinoma'). Auto-resolved to efoId.", 'required': False, 'type': 'string'}, 'efoId': {'description': 'EFO/MONDO disease ID (e.g., EFO_0000384). Alternative to disease_name.', 'required': False, 'type': 'string'}, 'ensemblId': {'description': 'Ensembl gene ID (e.g., ENSG00000141510). Alternative to gene_symbol.', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "HGNC gene symbol (e.g., 'TP53', 'BRCA1'). Auto-resolved to ensemblId.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- OpenTargets_get_evidence_by_datasource signature={'properties': {'datasourceIds': {'description': "List of datasource IDs to filter evidence. Examples: ['chembl', 'europepmc'], ['eva', 'clinvar'], ['intogen', 'cancer_gene_census']. Omit or pass empty array for all sources.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'disease_name': {'description': "Disease or phenotype name (e.g., 'Crohn disease'). Auto-resolved to efoId.", 'required': False, 'type': 'string'}, 'efoId': {'description': "Disease EFO ID (e.g., 'EFO_0000384' for Crohn's disease). Alternative to disease_name.", 'required': False, 'type': 'string'}, 'ensemblId': {'description': "Target Ensembl gene ID (e.g., 'ENSG00000141510' for TP53). Alternative to gene_symbol.", 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "HGNC gene symbol (e.g., 'TP53', 'BRCA1'). Auto-resolved to ensemblId.", 'required': False, 'type': 'string'}, 'size': {'default': 50, 'description': 'Maximum evidence rows to return (default: 50)', 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- gwas_get_snps_for_gene signature={'properties': {'gene': {'description': 'Alias for gene_symbol', 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "Gene name or symbol (e.g., 'BRCA1', 'TP53', 'GBA')", 'required': False, 'type': 'string'}, 'mapped_gene': {'description': 'Alias for gene_symbol', 'required': False, 'type': 'string'}, 'page': {'description': 'Page number for pagination', 'required': False, 'type': 'integer'}, 'size': {'description': 'Number of results to return per page', 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- gwas_search_studies signature={'properties': {'cohort': {'description': "Cohort name (e.g., 'UKB' for UK Biobank)", 'required': False, 'type': 'string'}, 'disease_trait': {'description': "Disease or trait name for text-based search (e.g., 'diabetes', 'breast cancer')", 'required': False, 'type': 'string'}, 'efo_id': {'description': "EFO/OBA term ID (e.g., 'EFO_0001645', 'OBA_2050062'). Recommended for reliable trait filtering.", 'required': False, 'type': 'string'}, 'efo_trait': {'description': 'Exact EFO trait label. Use when you know the canonical trait string.', 'required': False, 'type': 'string'}, 'efo_uri': {'description': "Full EFO ontology URI (e.g., 'http://www.ebi.ac.uk/efo/EFO_0001645')", 'required': False, 'type': 'string'}, 'full_pvalue_set': {'description': 'Filter for studies with full summary statistics', 'required': False, 'type': 'boolean'}, 'gxe': {'description': 'Filter for Gene-by-Environment interaction studies', 'required': False, 'type': 'boolean'}, 'page': {'description': 'Page number for pagination', 'required': False, 'type': 'integer'}, 'size': {'description': 'Number of results to return', 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- gnomad_get_gene_constraints signature={'properties': {'gene_symbol': {'description': "Gene symbol (e.g., 'BRCA1', 'TP53')", 'required': True, 'type': 'string'}, 'reference_genome': {'default': 'GRCh38', 'description': 'Reference genome.', 'enum': ['GRCh37', 'GRCh38'], 'required': False, 'type': 'string'}}, 'required': ['gene_symbol'], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- OpenTargets_get_target_classes_by_ensemblID signature={'properties': {'ensemblId': {'description': 'The Ensembl ID of the target.', 'required': True, 'type': 'string'}}, 'required': ['ensemblId'], 'type': 'object'}
- Pharos_get_target signature={'properties': {'gene': {'description': "Gene symbol (e.g., 'EGFR', 'TP53', 'BRCA1'). Use either gene or uniprot.", 'required': False, 'type': 'string'}, 'uniprot': {'description': "UniProt accession (e.g., 'P00533'). Use either gene or uniprot.", 'required': False, 'type': 'string'}}, 'type': 'object'}
- DGIdb_get_gene_druggability signature={'properties': {'gene': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'genes': {'description': 'List of gene symbols to check druggability. Aliases: gene_name, gene.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- alphafold_get_prediction signature={'properties': {'qualifier': {'description': "UniProt ACCESSION (e.g., 'P69905'). Do NOT use entry names like 'HBA_HUMAN'. Aliases: uniprot_id, uniprot_accession.", 'required': False, 'type': 'string'}, 'sequence_checksum': {'description': 'Optional CRC64 checksum of the UniProt sequence.', 'required': False, 'type': 'string'}, 'uniprot_accession': {'description': "Alias for qualifier: UniProt accession (e.g., 'P69905').", 'required': False, 'type': 'string'}, 'uniprot_id': {'description': "Alias for qualifier: UniProt accession (e.g., 'P69905').", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- alphafold_get_summary signature={'properties': {'qualifier': {'description': "Protein identifier: UniProt ACCESSION (e.g., 'Q5SWX9'). Aliases: uniprot_id, uniprot_accession.", 'required': False, 'type': 'string'}, 'uniprot_accession': {'description': "Alias for qualifier. UniProt accession (e.g., 'P04637').", 'required': False, 'type': 'string'}, 'uniprot_id': {'description': "Alias for qualifier. UniProt accession (e.g., 'P04637').", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ProteinsPlus_predict_binding_sites signature={'properties': {'chain': {'description': "Specific chain to analyze (e.g., 'A'). Optional - if not provided, all chains analyzed.", 'required': False, 'type': 'string'}, 'pdb_content': {'description': "Raw PDB file content as string (multi-line text starting with 'HEADER'). Use either pdb_id or pdb_content, not both. Example: Upload custom structures not in PDB.", 'required': False, 'type': 'string'}, 'pdb_id': {'description': "PDB identifier (e.g., '1A2B', '4HHB'). Use either pdb_id or pdb_content, not both.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- TCDB_get_transporter
- TCDB_search_by_substrate
- ChEMBL_get_target_activities signature={'oneOf': [{'required': ['target_chembl_id__exact']}, {'required': ['target_chembl_id']}], 'properties': {'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'target_chembl_id': {'description': 'Alias for target_chembl_id__exact. ChEMBL target ID (e.g., CHEMBL213).', 'required': False, 'type': 'string'}, 'target_chembl_id__exact': {'description': "ChEMBL target ID (e.g., 'CHEMBL2074'). To find a target ID, use ChEMBL_search_targets with a target name or gene symbol.", 'required': False, 'type': 'string'}}, 'type': 'object'}
- BindingDB_get_ligands_by_uniprot signature={'properties': {'affinity_cutoff': {'default': 10000, 'description': 'Maximum affinity in nM (default: 10000)', 'required': False, 'type': 'integer'}, 'uniprot_id': {'description': 'UniProt accession ID (e.g., P00533 for EGFR)', 'required': True, 'type': 'string'}}, 'required': ['uniprot_id'], 'type': 'object'}
- PubChem_search_assays_by_target_gene signature={'properties': {'gene_symbol': {'description': 'Gene symbol to search (e.g., EGFR, USP2, TP53)', 'required': True, 'type': 'string'}}, 'required': ['gene_symbol'], 'type': 'object'}
- PubChem_get_assay_active_compounds signature={'properties': {'aid': {'description': 'PubChem BioAssay ID', 'required': True, 'type': 'integer'}}, 'required': ['aid'], 'type': 'object'}
- ChEMBL_search_mechanisms signature={'properties': {'drug_chembl_id': {'description': 'Filter by drug ChEMBL ID', 'required': False, 'type': 'string'}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'mechanism_of_action__contains': {'description': 'Filter by mechanism description (contains)', 'required': False, 'type': 'string'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'target_chembl_id': {'description': 'Filter by target ChEMBL ID', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- DGIdb_get_gene_info signature={'properties': {'gene': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'genes': {'description': 'List of gene symbols. Aliases: gene_name, gene.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- ADMETAI_predict_physicochemical_properties signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_toxicity signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_BBB_penetrance signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_CYP_interactions signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_bioavailability signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_clearance_distribution signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_nuclear_receptor_activity signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- ADMETAI_predict_stress_response signature={'properties': {'smiles': {'description': 'SMILES string(s) for the molecule(s). Accepts a single string or list of strings.', 'oneOf': [{'description': 'List of SMILES strings.', 'items': {'type': 'string'}, 'type': 'array'}, {'description': 'Single SMILES string (will be wrapped in a list).', 'type': 'string'}], 'required': True}}, 'required': ['smiles'], 'type': 'object'}
- FDA_get_mechanism_of_action_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FDA_get_indications_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- search_clinical_trials signature={'properties': {'condition': {'description': 'Query for condition or disease using Essie expression syntax (e.g., \'lung cancer\', \'(head OR neck) AND pain AND NOT "back pain"\'). ', 'required': False, 'type': 'string'}, 'intervention': {'description': "Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').", 'required': False, 'type': 'string'}, 'keyword': {'description': 'Alias for query_term. Free-text keyword search across all trial fields (e.g., drug name, condition, investigator).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Alias for max_results: maximum number of studies to return (default 10, max 1000).', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Maximum number of studies to return (alias for pageSize, default 10, max 1000).', 'required': False, 'type': 'integer'}, 'overall_status': {'description': "Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUITING', 'NOT_YET_RECRUITING']). Valid values: RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED, WITHDRAWN.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'pageSize': {'description': 'Maximum number of studies to return per page (default 10, max 1000).', 'required': False, 'type': 'integer'}, 'pageToken': {'description': "Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.", 'required': False, 'type': 'string'}, 'query_term': {'description': "Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.", 'required': False, 'type': 'string'}, 'status': {'description': 'Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLETED".', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': False}}, 'required': [], 'type': 'object'}
- OpenTargets_get_drug_warnings_by_chemblId signature={'properties': {'chemblId': {'description': 'The ChEMBL ID of the drug.', 'required': True, 'type': 'string'}}, 'required': ['chemblId'], 'type': 'object'}
- GTEx_get_median_gene_expression signature={'properties': {'dataset_id': {'default': 'gtex_v8', 'description': 'GTEx dataset version (default: gtex_v8; v10 returns empty for most endpoints)', 'enum': ['gtex_v8', 'gtex_v10', 'gtex_snrnaseq_pilot'], 'required': False, 'type': 'string'}, 'gencode_id': {'description': "Gene identifier(s): gene symbol (e.g. 'TP53'), unversioned Ensembl ID (e.g. 'ENSG00000141510'), or versioned GENCODE ID (e.g. 'ENSG00000141510.18'). Auto-resolved to versioned GENCODE ID. Can be single string or array.", 'items': {'type': 'string'}, 'required': False, 'type': ['string', 'array']}, 'gene_symbol': {'description': 'Gene symbol alias for gencode_id (e.g., "TP53", "COL5A1")', 'required': False, 'type': 'string'}, 'items_per_page': {'default': 250, 'description': 'Results per page', 'maximum': 100000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'description': 'Operation type', 'enum': ['get_median_gene_expression'], 'required': False, 'type': 'string'}, 'page': {'default': 0, 'description': 'Page number for pagination (0-based)', 'minimum': 0, 'required': False, 'type': 'integer'}, 'tissue_site_detail_id': {'description': "Optional: Tissue IDs to filter (e.g. ['Liver', 'Brain_Cortex']). Omit for all tissues. See GTEx_get_tissue_sites for valid IDs", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- HPA_search_genes_by_query signature={'properties': {'search_query': {'description': "Gene name, alias, keyword, or cell line name to search for, e.g., 'EGFR', 'TP53', or 'MCF7'.", 'required': True, 'type': 'string'}}, 'required': ['search_query'], 'type': 'object'}
- FDA_get_adverse_reactions_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- FDA_get_boxed_warning_info_by_drug_name signature={'properties': {'drug_name': {'description': 'The name of the drug.', 'required': True, 'type': 'string'}, 'limit': {'description': 'The number of records to return.', 'required': False, 'type': 'integer'}, 'skip': {'description': 'The number of records to skip.', 'required': False, 'type': 'integer'}}, 'required': ['drug_name'], 'type': 'object'}
- Reactome_map_uniprot_to_pathways signature={'properties': {'uniprot_id': {'description': "UniProt protein accession (e.g., 'P04637' for TP53, 'P00533' for EGFR)", 'required': True, 'type': 'string'}}, 'required': ['uniprot_id'], 'type': 'object'}
- STRING_get_protein_interactions signature={'properties': {'confidence_score': {'default': 0.4, 'description': 'Minimum confidence score (0-1, default: 0.4)', 'maximum': 1, 'minimum': 0, 'required': False, 'type': 'number'}, 'limit': {'default': 50, 'description': 'Maximum number of interactions to return (default: 50)', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'network_type': {'default': 'full', 'description': "Type of network ('full', 'physical', 'functional')", 'enum': ['full', 'physical', 'functional'], 'required': False, 'type': 'string'}, 'protein_ids': {'description': 'List of protein identifiers (UniProt IDs, gene names, etc.)', 'items': {'type': 'string'}, 'minItems': 1, 'required': True, 'type': 'array'}, 'species': {'default': 9606, 'description': 'NCBI taxonomy ID (default: 9606 for human)', 'required': False, 'type': 'integer'}}, 'required': ['protein_ids'], 'type': 'object'}
- intact_get_interactions signature={'properties': {'format': {'default': 'json', 'enum': ['json', 'xml'], 'required': False, 'type': 'string'}, 'identifier': {'description': 'IntAct identifier, UniProt ID, or gene name', 'required': True, 'type': 'string'}}, 'required': ['identifier'], 'type': 'object'}
- STRING_functional_enrichment signature={'properties': {'category': {'default': 'Process', 'description': "Enrichment category: 'Process' (GO Biological Process), 'Component' (GO Cellular Component), 'Function' (GO Molecular Function), 'KEGG', 'Reactome', 'WikiPathways', 'COMPARTMENTS', 'TISSUES', 'DISEASES'", 'enum': ['Process', 'Component', 'Function', 'KEGG', 'Reactome', 'WikiPathways', 'COMPARTMENTS', 'TISSUES', 'DISEASES'], 'required': False, 'type': 'string'}, 'protein_ids': {'description': 'List of protein identifiers (UniProt IDs, gene names, Ensembl IDs). Minimum 3 proteins recommended for meaningful enrichment.', 'items': {'type': 'string'}, 'minItems': 2, 'required': True, 'type': 'array'}, 'species': {'default': 9606, 'description': 'NCBI taxonomy ID (default: 9606 for human)', 'required': False, 'type': 'integer'}}, 'required': ['protein_ids'], 'type': 'object'}
- DepMap_get_gene_dependencies signature={'properties': {'gene_symbol': {'description': "Gene symbol (e.g., 'EGFR', 'KRAS', 'TP53')", 'required': True, 'type': 'string'}, 'model_id': {'description': 'Optional: Filter by specific cell line', 'required': False, 'type': 'string'}}, 'required': ['gene_symbol'], 'type': 'object'}
- CTD_get_gene_diseases signature={'properties': {'gene_symbol': {'description': 'Gene symbol (alias for input_terms, e.g. TP53)', 'required': False, 'type': 'string'}, 'input_terms': {'description': "Gene symbol or NCBI Gene ID. Examples: 'TP53', 'BRCA1', 'CYP1A1', '7157' (Gene ID for TP53).", 'required': False, 'type': 'string'}, 'query': {'description': 'Gene symbol or name to search (alias for input_terms, e.g. TP53)', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ESMFold_predict_structure signature={'properties': {'sequence': {'description': "Protein amino acid sequence in single-letter code. Example: 'MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH'. FASTA headers and whitespace are stripped. Max ~400 residues recommended for fast results.", 'required': True, 'type': 'string'}}, 'required': ['sequence'], 'type': 'object'}
- UniProt_get_entry_by_accession signature={'properties': {'accession': {'description': 'UniProtKB entry accession, e.g., P05067.', 'required': True, 'type': 'string'}, 'compact': {'default': True, 'description': 'Return a bounded summary instead of the complete UniProtKB JSON entry. Defaults to true to avoid oversized LLM outputs. Set compact=false only when you explicitly need the raw UniProtKB JSON.', 'required': False, 'type': 'boolean'}}, 'required': ['accession'], 'type': 'object'}
- get_protein_metadata_by_pdb_id signature={'properties': {'pdb_id': {'description': '4-character RCSB PDB ID of the protein', 'required': True, 'type': 'string'}}, 'required': ['pdb_id'], 'type': 'object'}
- pdbe_get_entry_summary signature={'properties': {'pdb_id': {'description': "PDB entry ID (e.g., '1A2B', '1CRN'). Will be converted to lowercase automatically.", 'required': True, 'type': 'string'}}, 'required': ['pdb_id'], 'type': 'object'}
- pdbe_get_entry_quality signature={'properties': {'pdb_id': {'description': "PDB entry ID (e.g., '1A2B', '1CRN'). Will be converted to lowercase automatically.", 'required': True, 'type': 'string'}}, 'required': ['pdb_id'], 'type': 'object'}
- InterPro_get_protein_domains signature={'properties': {'protein_id': {'description': 'UniProt protein ID (e.g., P05067, Q9Y6K9)', 'required': True, 'type': 'string'}}, 'required': ['protein_id'], 'type': 'object'}
- InterPro_get_domain_details signature={'properties': {'accession': {'description': 'InterPro accession ID (e.g., IPR000719)', 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- openalex_search_works signature={'anyOf': [{'required': ['search']}, {'required': ['query']}], 'properties': {'filter': {'description': 'OpenAlex filter string (comma-separated). Example: "from_publication_date:2020-01-01,is_oa:true".', 'required': False, 'type': 'string'}, 'fulltext_terms': {'description': 'Optional list of terms to match in OpenAlex full-text index. Adds one or more fulltext.search:<term> filters and implicitly enables require_has_fulltext.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'description': 'Alias for `per_page` (OpenAlex max 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'mailto': {'description': 'Optional contact email for OpenAlex polite pool. If omitted, ToolUniverse uses a default.', 'required': False, 'type': 'string'}, 'page': {'default': 1, 'description': 'Page number (1-indexed).', 'minimum': 1, 'required': False, 'type': 'integer'}, 'per_page': {'default': 10, 'description': 'Results per page (OpenAlex max 200).', 'maximum': 200, 'minimum': 1, 'required': False, 'type': 'integer'}, 'query': {'description': 'Alias for `search` (recommended when you standardize on `query` across multiple paper-search tools).', 'required': False, 'type': 'string'}, 'require_has_fulltext': {'default': False, 'description': 'If true, appends OpenAlex filter has_fulltext:true (keeps only works with full-text index available).', 'required': False, 'type': 'boolean'}, 'search': {'description': 'Search query for works. Use filter + fulltext_terms/require_has_fulltext when you need full-text-index-only matching.', 'required': False, 'type': 'string'}, 'sort': {'description': 'Sort order string, e.g. "cited_by_count:desc".', 'required': False, 'type': 'string'}}, 'type': 'object'}
- EuropePMC_search_articles signature={'properties': {'enrich_missing_abstract': {'default': False, 'description': 'If true, best-effort fills missing abstracts by fetching Europe PMC fullTextXML (bounded to a few results).', 'required': False, 'type': 'boolean'}, 'extract_terms_from_fulltext': {'description': "Optional list of terms to extract from full text (open access only). When provided, automatically fetches fullTextXML for open-access articles and returns snippets around these terms. Terms are processed in batches of 5 internally, so any number of terms is accepted. Bounded to first 3 OA articles to avoid latency. Returns snippets in a 'fulltext_snippets' field for each article.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'fulltext_terms': {'description': 'Optional list of terms that must occur in the indexed full text (Europe PMC BODY field). When provided, the tool adds a BODY:"..." clause and automatically enables `require_has_ft`.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'default': 5, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from Europe PMC.', 'required': False, 'type': 'integer'}, 'page_size': {'description': 'Alias for limit â\x80\x94 number of results to return', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Europe PMC. Supports Lucene-like fielded syntax (e.g., BODY:"term", INTRO:"term", METHODS:"term").', 'required': True, 'type': 'string'}, 'require_has_ft': {'default': False, 'description': 'If true, appends `HAS_FT:Y` to the query to restrict results to records where Europe PMC has full text indexed. This is NOT the same as having a link to free full text elsewhere (e.g., PMC) and is often the key reason body-only keywords cannot be found via Europe PMC search.', 'required': False, 'type': 'boolean'}}, 'required': ['query'], 'type': 'object'}

## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)
- OpenTargets_get_diseases_phenotypes_by_target_ensembl
- OpenTargets_get_publications_by_target_ensemblID
- OpenTargets_get_target_tractability_by_ensemblID
- OpenTargets_get_chemical_probes_by_target_ensemblID
- OpenTargets_get_target_enabling_packages_by_ensemblID
- uniprot_accession
- substrate_name
- OpenTargets_get_associated_drugs_by_target_ensemblID
- ADMETAI_predict_solubility_lipophilicity_hydration
- drugbank_get_targets_by_drug_name_or_drugbank_id
- case_sensitive
- exact_match
- query_term
- OpenTargets_get_drug_adverse_events_by_chemblId
- OpenTargets_get_target_safety_profile_by_ensemblID
- HPA_get_comprehensive_gene_details_by_ensembl_id
- OpenTargets_get_biological_mouse_models_by_ensemblID
- OpenTargets_get_target_homologues_by_ensemblID
- uniprot_id
- protein_ids
- OpenTargets_get_target_gene_ontology_by_ensemblID

# TARGET SKILL TO CONVERT
---
name: tooluniverse-drug-target-validation
description: Quantitative drug-target validation pipeline. Scores druggability, selectivity, safety profile, ADMET feasibility, and structural tractability with a composite Target Validation Score (0-100) and GO/NO-GO recommendation. Use for go/no-go decisions on a target before commit-to-medchem, target prioritization across a list, and target-deselection rationale.
disable-model-invocation: true
---

# Drug Target Validation Pipeline

Validate drug target hypotheses using multi-dimensional computational evidence before committing to wet-lab work. Produces a quantitative Target Validation Score (0-100) with priority tier classification and GO/NO-GO recommendation.

## Reasoning Before Searching

A valid drug target must pass 4 gates in order. Failing an early gate makes later gates irrelevant:

1. **Genetic evidence linking it to disease**: Does human genetic data (GWAS, rare variant studies, Mendelian genetics) support this target's role? Genetic evidence is the strongest predictor of clinical success. Use OpenTargets and GWAS catalog before anything else. If no genetic link exists, the hypothesis is speculative — document this clearly.
2. **Druggability**: Can a molecule reach and modulate the target? Check structure availability (PDB, AlphaFold), binding pocket prediction (ProteinsPlus), target class (kinase, GPCR, nuclear receptor = favorable; transcription factor, scaffold protein = difficult), and existing chemical probes.
3. **Safety — essentiality in normal tissue**: Is the target expressed in critical tissues (heart, liver, bone marrow)? Is knockout lethal in mice? High expression in essential tissue or lethality in mouse models is a strong safety red flag even before any clinical data.
4. **Competitive landscape**: Are other drugs already approved or in late-stage trials for this target? If so, the bar is differentiation, not first-in-class. Check ChEMBL, DrugBank, and ClinicalTrials.gov early.

Do not proceed to Phase 3 (Chemical Matter) before completing Phase 1 (Disease Association). Gate 1 failures should prompt a NO-GO or pivot recommendation.

**LOOK UP DON'T GUESS**: Never assume a target is druggable based on its protein family alone, never assume expression is low in a tissue without checking GTEx or HPA, never assume no competitors without searching ClinicalTrials.gov.

**RUN THE ML MODELS, DON'T SKIP THEM**: When deep-learning predictors are available (ADMET-AI, ESMFold, AlphaFold, DoGSite, DynaMut2, DeepGO), **run them even when database lookups or experimental data already cover the same property**. The ML predictions provide an orthogonal, mechanistically-grounded estimate that's a first-class output of this skill — not a fallback. A target-validation report missing ML predictions is incomplete regardless of how much database evidence is present.

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Key Principles

1. **Report-first** - Create report file FIRST, then populate progressively
2. **Target disambiguation FIRST** - Resolve all identifiers before analysis
3. **Evidence grading** - Grade all evidence as T1 (experimental) to T4 (computational)
4. **Disease-specific** - Tailor analysis to disease context when provided
5. **Modality-aware** - Consider small molecule vs biologics tractability
6. **Safety-first** - Prominently flag safety concerns early
7. **Quantitative scoring** - Every dimension scored numerically (0-100 composite)
8. **Negative results documented** - "No data" is data; empty sections are failures
9. **Source references** - Every statement must cite tool/database
10. **English-first queries** - Always use English terms in tool calls; respond in user's language

## When to Use

Apply when users ask about:
- "Is [target] a good drug target for [disease]?"
- Target validation, druggability assessment, or target prioritization
- Safety risks of modulating a target
- Chemical starting points for target validation
- GO/NO-GO recommendation for a target

**Not for** (use other skills): general target biology (`tooluniverse-target-research`), drug compound profiling (`tooluniverse-drug-research`), variant interpretation (`tooluniverse-variant-interpretation`), disease research (`tooluniverse-disease-research`).

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **target** | Yes | Gene symbol, protein name, or UniProt ID | `EGFR`, `P00533` |
| **disease** | No | Disease/indication for context | `Non-small cell lung cancer` |
| **modality** | No | Preferred therapeutic modality | `small molecule`, `antibody`, `PROTAC` |

## Reference Files

- **SCORING_CRITERIA.md** - Detailed scoring matrices, evidence grading, priority tiers, score calculation
- **REPORT_TEMPLATE.md** - Full report template, completeness checklist, section format examples
- **TOOL_REFERENCE.md** - Verified tool parameters, known corrections, fallback chains, modality-specific guidance, phase-by-phase tool lists
- **QUICK_START.md** - Quick start guide

---

## Scoring Overview

**Total: 0-100 points** across 5 dimensions (details in SCORING_CRITERIA.md):

| Dimension | Max | Sub-dimensions |
|-----------|-----|----------------|
| Disease Association | 30 | Genetic (10) + Literature (10) + Pathway (10) |
| Druggability | 25 | Structure (10) + Chemical matter (10) + Target class (5) |
| Safety Profile | 20 | Expression (5) + Genetic validation (10) + ADRs (5) |
| Clinical Precedent | 15 | Based on highest clinical stage achieved |
| Validation Evidence | 10 | Functional studies (5) + Disease models (5) |

**Priority Tiers**: 80-100 = Tier 1 (GO) | 60-79 = Tier 2 (CONDITIONAL GO) | 40-59 = Tier 3 (CAUTION) | 0-39 = Tier 4 (NO-GO)

**Evidence Grades**: T1 (clinical proof) > T2 (functional studies) > T3 (associations) > T4 (predictions)

---

## Pipeline Phases

### Phase 0: Target Disambiguation (ALWAYS FIRST)

Resolve target to ALL identifiers before any analysis.

**Steps**:
1. `MyGene_query_genes` - Get initial IDs (Ensembl, UniProt, Entrez)
2. `ensembl_lookup_gene` - Get versioned Ensembl ID (species="homo_sapiens" REQUIRED)
3. `ensembl_get_xrefs` - Cross-references (HGNC, etc.)
4. `OpenTargets_get_target_id_description_by_name` - Verify OT target
5. `ChEMBL_search_targets` - Get ChEMBL target ID
6. `UniProt_get_function_by_accession` - Function summary (returns list of strings)
7. `UniProt_get_alternative_names_by_accession` - Collision detection

**Output**: Table of verified identifiers (Gene Symbol, Ensembl, UniProt, Entrez, ChEMBL, HGNC) plus protein function and target class.

### Phase 1: Disease Association (0-30 pts)

Quantify target-disease association from genetic, literature, and pathway evidence.

**Key tools**:
- `OpenTargets_get_diseases_phenotypes_by_target_ensembl` - Disease associations
- `OpenTargets_target_disease_evidence` - Detailed evidence (needs `efoId` + `ensemblId`)
- `OpenTargets_get_evidence_by_datasource` - Evidence by data source
- `gwas_get_snps_for_gene` / `gwas_search_studies` - GWAS evidence
- `gnomad_get_gene_constraints` - Genetic constraint (pLI, LOEUF)
- `PubMed_search_articles` - Literature (returns plain list of dicts)
- `OpenTargets_get_publications_by_target_ensemblID` - OT publications (uses `entityId`)

### Phase 2: Druggability (0-25 pts)

Assess whether the target is amenable to therapeutic intervention.

**Key tools**:
- `OpenTargets_get_target_tractability_by_ensemblID` - Tractability (SM, AB, PR, OC)
- `OpenTargets_get_target_classes_by_ensemblID` - Target classification
- `Pharos_get_target` - TDL: Tclin > Tchem > Tbio > Tdark
- `DGIdb_get_gene_druggability` - Druggability categories
- `alphafold_get_prediction` (param: `qualifier`) / `alphafold_get_summary`
- `ProteinsPlus_predict_binding_sites` - Pocket detection
- `OpenTargets_get_chemical_probes_by_target_ensemblID` - Chemical probes
- `OpenTargets_get_target_enabling_packages_by_ensemblID` - TEPs
- `TCDB_get_transporter` - For SLC/ABC transporter targets: TC classification, family, PDB structures (param: `uniprot_accession`)
- `TCDB_search_by_substrate` - Find transporters by substrate (param: `substrate_name`)

### Phase 3: Chemical Matter (feeds Phase 2 scoring)

Identify existing chemical starting points for target validation.

**Key tools**:
- `ChEMBL_search_targets` + `ChEMBL_get_target_activities` - Bioactivity data (note: `target_chembl_id__exact` with double underscore)
- `BindingDB_get_ligands_by_uniprot` - Binding data (affinity in nM)
- `PubChem_search_assays_by_target_gene` + `PubChem_get_assay_active_compounds` - HTS data
- `OpenTargets_get_associated_drugs_by_target_ensemblID` - Known drugs (`size` REQUIRED)
- `ChEMBL_search_mechanisms` - Drug mechanisms
- `DGIdb_get_gene_info` - Drug-gene interactions

#### Phase 3b: ADMET-AI Deep-Learning Profile (REQUIRED)

For each lead / approved compound identified above, run **all ten ADMET-AI Chemprop-GNN endpoints**. This is a required deliverable of the skill, not optional:

| Endpoint | Tool |
|---|---|
| Physicochemical (MW, logP, HBA/HBD, TPSA) | `ADMETAI_predict_physicochemical_properties` |
| Toxicity (AMES, DILI, LD50, carcinogens, skin sensitizers, ClinTox) | `ADMETAI_predict_toxicity` |
| BBB penetrance | `ADMETAI_predict_BBB_penetrance` |
| CYP interactions (1A2, 2C9, 2C19, 2D6, 3A4) | `ADMETAI_predict_CYP_interactions` |
| Bioavailability (HIA, PAMPA, Caco-2, F20/F30) | `ADMETAI_predict_bioavailability` |
| Clearance & distribution (hepatocyte, microsome, VDss, PPB) | `ADMETAI_predict_clearance_distribution` |
| Nuclear receptor activity (NR-AR, NR-AhR, NR-Aromatase, NR-ER, NR-PPAR-γ) | `ADMETAI_predict_nuclear_receptor_activity` |
| Stress response (SR-ARE, SR-ATAD5, SR-HSE, SR-MMP, SR-p53) | `ADMETAI_predict_stress_response` |
| Solubility, lipophilicity, hydration | `ADMETAI_predict_solubility_lipophilicity_hydration` |
| Metabolism (CYP-mediated) | `ADMETAI_predict_CYP_interactions` |

**Required output — ADMET head-to-head table**: when two or more candidate drugs exist (approved or late-stage), produce a side-by-side comparison table with every endpoint in the same row and a "Winner" column flagging which drug is safer. This table is the primary visual of the report and must not be abbreviated or summarized into prose.

**ADMET-AI fallback (IMPORTANT)**: If MCP calls to `ADMETAI_predict_*` fail, return empty, or timeout, run them via Bash + Python SDK instead:
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
for endpoint in ['physicochemical_properties','toxicity','BBB_penetrance','CYP_interactions',
                 'bioavailability','clearance_distribution','nuclear_receptor_activity',
                 'stress_response','solubility_lipophilicity_hydration']:
    r = tu.run_one_function({'name': f'ADMETAI_predict_{endpoint}',
                              'arguments': {'smiles_list': [SMILES_DRUG_A, SMILES_DRUG_B]}})
    print(f'{endpoint}: {r}')
```
This SDK path bypasses the CLI subprocess and avoids segfault issues with torch. Always try MCP first; use this fallback if MCP returns no data.

### Phase 4: Clinical Precedent (0-15 pts)

Assess clinical validation from approved drugs and clinical trials.

**Key tools**:
- `FDA_get_mechanism_of_action_by_drug_name` / `FDA_get_indications_by_drug_name`
- `drugbank_get_targets_by_drug_name_or_drugbank_id` (ALL params required: `query`, `case_sensitive`, `exact_match`, `limit`)
- `search_clinical_trials` (`query_term` REQUIRED)
- `OpenTargets_get_drug_warnings_by_chemblId` / `OpenTargets_get_drug_adverse_events_by_chemblId`

### Phase 5: Safety (0-20 pts)

Identify safety risks from expression, genetics, and known adverse events.

**Key tools**:
- `OpenTargets_get_target_safety_profile_by_ensemblID` - Safety liabilities
- `GTEx_get_median_gene_expression` - Tissue expression (`operation="median"` REQUIRED)
- `HPA_search_genes_by_query` / `HPA_get_comprehensive_gene_details_by_ensembl_id`
- `OpenTargets_get_biological_mouse_models_by_ensemblID` - KO phenotypes
- `FDA_get_adverse_reactions_by_drug_name` / `FDA_get_boxed_warning_info_by_drug_name`
- `OpenTargets_get_target_homologues_by_ensemblID` - Paralog risks

**Critical tissues to check**: heart, liver, kidney, brain, bone marrow.

### Phase 6: Pathway Context

Understand the target's role in biological networks and disease pathways.

**Key tools**:
- `Reactome_map_uniprot_to_pathways` (param: `id`, NOT `uniprot_id`)
- `STRING_get_protein_interactions` (param: `protein_ids` as array, `species=9606`)
- `intact_get_interactions` - Experimental PPI
- `OpenTargets_get_target_gene_ontology_by_ensemblID` - GO terms
- `STRING_functional_enrichment` - Enrichment analysis

**Assess**: pathway redundancy, compensation risk, feedback loops.

### Phase 7: Validation Evidence (0-10 pts)

Assess existing functional validation data.

**Key tools**:
- `DepMap_get_gene_dependencies` - Essentiality (score < -0.5 = essential)
- `PubMed_search_articles` - Search for CRISPR/siRNA/knockout studies
- `CTD_get_gene_diseases` - Gene-disease associations

### Phase 8: Structural Insights

Leverage structural biology for druggability and mechanism understanding. **ALWAYS run both the deep-learning predictors (ESMFold, DoGSite) AND retrieve experimental structures**, even when high-resolution PDB entries already exist. The ML models give an independent pLDDT/druggability score that is a required output of this phase.

**Required tool calls (every run)**:
- `ESMFold_predict_structure` — Meta ESM-2 language-model structure prediction from the UniProt sequence. Report: model pLDDT, worst-residue confidence, RMSD vs. reference PDB if available.
- `alphafold_get_prediction` / `alphafold_get_summary` — DeepMind AlphaFold model + per-residue pLDDT.
- `ProteinsPlus_predict_binding_sites` — DoGSite deep-learning pocket scoring. Report: top 3 pockets with volume, druggability score, residue composition.

**Supporting tools**:
- `UniProt_get_entry_by_accession` - Extract PDB cross-references
- `get_protein_metadata_by_pdb_id` / `pdbe_get_entry_summary` / `pdbe_get_entry_quality`
- `InterPro_get_protein_domains` / `InterPro_get_domain_details` - Domain architecture

### Phase 9: Literature Deep Dive

Comprehensive collision-aware literature analysis.

**Steps**:
1. **Collision detection**: Search `"{gene_symbol}"[Title]` in PubMed; if >20% off-topic, add filters (AND protein OR gene OR receptor)
2. **Publication metrics**: Total count, 5-year trend, drug-focused subset
3. **Key reviews**: `review[pt]` filter in PubMed
4. **Citation metrics**: `openalex_search_works` for impact data
5. **Broader coverage**: `EuropePMC_search_articles`

### Phase 10: Validation Roadmap (Synthesis)

Synthesize all phases into actionable output:
1. **Target Validation Score** (0-100) with component breakdown
2. **Priority Tier** (1-4) assignment
3. **GO/NO-GO Recommendation** with justification
4. **Recommended Validation Experiments**
5. **Tool Compounds for Testing**
6. **Biomarker Strategy**
7. **Key Risks and Mitigations**
8. **Deep-Learning Models Contributing** — explicit attribution table listing every ML predictor invoked during the run and what each produced. Example format:

| Model | Architecture | Contributed |
|---|---|---|
| AlphaFold | DeepMind iterative SE(3)-equivariant Transformer | Full-length 3D model; per-residue pLDDT 91.5 |
| ESMFold | Meta ESM-2 protein language model | Sequence→structure baseline; confidence vs. AlphaFold |
| DoGSite3 | CNN pocket scorer (ProteinsPlus) | Top-3 druggable pockets with volume and drug-score |
| ADMET-AI | Chemprop GNN ensemble (TDC) | 10 endpoints for sotorasib / adagrasib (table above) |
| DynaMut2 | Graph-based mutation stability predictor | ΔΔG for G12C vs. WT |
| DeepGO | Hierarchical GO-term classifier | Molecular-function predictions |

Only list models actually called during the run. This section makes the ML content first-class for a scientific or investor audience.

---

## Report Output

Create file: `[TARGET]_[DISEASE]_validation_report.md`

Use the full template from **REPORT_TEMPLATE.md**. Key sections:
- Executive Summary (score, tier, recommendation, key findings, critical risks)
- Validation Scorecard (all 12 sub-scores with evidence)
- Sections 1-14 covering each phase
- Completeness Checklist (mandatory before finalizing)

Complete the **Completeness Checklist** (in REPORT_TEMPLATE.md) before finalizing to verify all phases were covered, all scores justified, and negative results documented.


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
