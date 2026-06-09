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
- get_tool_info signature={'properties': {'detail_level': {'default': 'full', 'description': "Detail level: 'description' returns only the description field (complete, not truncated), 'full' returns complete tool definition including parameter schema", 'enum': ['description', 'full'], 'required': False, 'type': 'string'}, 'tool_names': {'description': 'Single tool name (string) or list of tool names', 'oneOf': [{'type': 'string'}, {'items': {'type': 'string'}, 'type': 'array'}], 'required': True}}, 'required': ['tool_names'], 'type': 'object'}
- Reactome_map_uniprot_to_pathways signature={'properties': {'uniprot_id': {'description': "UniProt protein accession (e.g., 'P04637' for TP53, 'P00533' for EGFR)", 'required': True, 'type': 'string'}}, 'required': ['uniprot_id'], 'type': 'object'}
- ensembl_get_xrefs signature={'properties': {'external_db': {'description': "Filter by external database name (optional, e.g., 'UniProt', 'RefSeq', 'HGNC')", 'required': False, 'type': 'string'}, 'id': {'description': "Ensembl ID (gene, transcript, or protein ID, e.g., 'ENSG00000139618', 'ENST00000380152', 'ENSP00000369497')", 'required': True, 'type': 'string'}, 'object_type': {'description': "Object type filter (optional, e.g., 'gene', 'transcript', 'translation')", 'required': False, 'type': 'string'}}, 'required': ['id'], 'type': 'object'}
- GTEx_get_median_gene_expression signature={'properties': {'dataset_id': {'default': 'gtex_v8', 'description': 'GTEx dataset version (default: gtex_v8; v10 returns empty for most endpoints)', 'enum': ['gtex_v8', 'gtex_v10', 'gtex_snrnaseq_pilot'], 'required': False, 'type': 'string'}, 'gencode_id': {'description': "Gene identifier(s): gene symbol (e.g. 'TP53'), unversioned Ensembl ID (e.g. 'ENSG00000141510'), or versioned GENCODE ID (e.g. 'ENSG00000141510.18'). Auto-resolved to versioned GENCODE ID. Can be single string or array.", 'items': {'type': 'string'}, 'required': False, 'type': ['string', 'array']}, 'gene_symbol': {'description': 'Gene symbol alias for gencode_id (e.g., "TP53", "COL5A1")', 'required': False, 'type': 'string'}, 'items_per_page': {'default': 250, 'description': 'Results per page', 'maximum': 100000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'operation': {'description': 'Operation type', 'enum': ['get_median_gene_expression'], 'required': False, 'type': 'string'}, 'page': {'default': 0, 'description': 'Page number for pagination (0-based)', 'minimum': 0, 'required': False, 'type': 'integer'}, 'tissue_site_detail_id': {'description': "Optional: Tissue IDs to filter (e.g. ['Liver', 'Brain_Cortex']). Omit for all tissues. See GTEx_get_tissue_sites for valid IDs", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- STRING_get_protein_interactions signature={'properties': {'confidence_score': {'default': 0.4, 'description': 'Minimum confidence score (0-1, default: 0.4)', 'maximum': 1, 'minimum': 0, 'required': False, 'type': 'number'}, 'limit': {'default': 50, 'description': 'Maximum number of interactions to return (default: 50)', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'network_type': {'default': 'full', 'description': "Type of network ('full', 'physical', 'functional')", 'enum': ['full', 'physical', 'functional'], 'required': False, 'type': 'string'}, 'protein_ids': {'description': 'List of protein identifiers (UniProt IDs, gene names, etc.)', 'items': {'type': 'string'}, 'minItems': 1, 'required': True, 'type': 'array'}, 'species': {'default': 9606, 'description': 'NCBI taxonomy ID (default: 9606 for human)', 'required': False, 'type': 'integer'}}, 'required': ['protein_ids'], 'type': 'object'}
- intact_get_interactions signature={'properties': {'format': {'default': 'json', 'enum': ['json', 'xml'], 'required': False, 'type': 'string'}, 'identifier': {'description': 'IntAct identifier, UniProt ID, or gene name', 'required': True, 'type': 'string'}}, 'required': ['identifier'], 'type': 'object'}
- GPCRdb_get_protein signature={'properties': {'operation': {'const': 'get_protein', 'description': 'Operation type (fixed: get_protein)', 'required': False, 'type': 'string'}, 'protein': {'description': 'Protein entry name (e.g., adrb2_human for beta-2 adrenergic receptor) or UniProt accession (e.g., P07550)', 'required': False, 'type': 'string'}, 'protein_id': {'description': 'Alias for protein parameter', 'required': False, 'type': 'string'}, 'protein_name': {'description': 'Alias for protein. GPCRdb entry name (e.g., adrb2_human).', 'required': False, 'type': 'string'}, 'receptor_name': {'description': 'Alias for protein. GPCRdb entry name (e.g., adrb2_human).', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- UniProt_get_entry_by_accession signature={'properties': {'accession': {'description': 'UniProtKB entry accession, e.g., P05067.', 'required': True, 'type': 'string'}, 'compact': {'default': True, 'description': 'Return a bounded summary instead of the complete UniProtKB JSON entry. Defaults to true to avoid oversized LLM outputs. Set compact=false only when you explicitly need the raw UniProtKB JSON.', 'required': False, 'type': 'boolean'}}, 'required': ['accession'], 'type': 'object'}
- UniProt_get_function_by_accession signature={'properties': {'accession': {'description': 'UniProtKB accession, e.g., P05067.', 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- UniProt_get_recommended_name_by_accession signature={'properties': {'accession': {'description': 'UniProtKB accession, e.g., P05067.', 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- UniProt_get_alternative_names_by_accession signature={'properties': {'accession': {'description': 'UniProtKB accession, e.g., P05067.', 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- UniProt_get_subcellular_location_by_accession signature={'properties': {'accession': {'description': 'UniProtKB accession, e.g., P05067.', 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- MyGene_get_gene_annotation signature={'properties': {'fields': {'default': 'symbol,name,entrezgene,ensembl,summary,go,pathway,interpro', 'description': 'Comma-separated list of fields to return. Available fields include: symbol, name, summary, go (gene ontology), pathway (KEGG/Reactome), interpro (protein domains), generif (gene references), pdb, uniprot.', 'required': False, 'type': 'string'}, 'gene_id': {'description': "Gene ID to query. Can be Entrez Gene ID (e.g., '1017' for CDK2) or Ensembl ID (e.g., 'ENSG00000123374').", 'required': True, 'type': 'string'}}, 'required': ['gene_id'], 'type': 'object'}
- RCSBData_get_entry signature={'properties': {'pdb_id': {'description': "PDB entry ID (4 characters). Examples: '4HHB' (hemoglobin), '1TUP' (p53-DNA complex), '1M17' (EGFR kinase), '6LU7' (SARS-CoV-2 main protease).", 'required': True, 'type': 'string'}}, 'required': ['pdb_id'], 'type': 'object'}
- PDB_search_similar_structures signature={'properties': {'max_results': {'default': 20, 'description': 'Maximum number of results to return (1-100). Values outside this range will be clamped.', 'required': False, 'type': 'integer'}, 'query': {'description': "PDB ID (e.g., '1ABC'), protein sequence (amino acids), or search text (e.g., drug name, protein name, keyword). For structure search, provide PDB ID. For sequence search, provide amino acid sequence. For text search, provide drug name, protein name, or keyword.", 'required': True, 'type': 'string'}, 'search_type': {'default': 'sequence', 'description': "Type of search: 'sequence' for sequence-based similarity search, 'structure' for structure-based similarity search using PDB ID, 'text' for text-based search by name or keyword", 'enum': ['sequence', 'structure', 'text'], 'required': False, 'type': 'string'}, 'similarity_threshold': {'default': 0.7, 'description': 'Similarity threshold (0-1). Higher values return more similar structures. Values outside 0-1 will be clamped. For sequence search, this is the identity cutoff. For structure search, this is the structure similarity threshold. Not used for text search.', 'required': False, 'type': 'number'}}, 'required': ['query'], 'type': 'object'}
- alphafold_get_prediction signature={'properties': {'qualifier': {'description': "UniProt ACCESSION (e.g., 'P69905'). Do NOT use entry names like 'HBA_HUMAN'. Aliases: uniprot_id, uniprot_accession.", 'required': False, 'type': 'string'}, 'sequence_checksum': {'description': 'Optional CRC64 checksum of the UniProt sequence.', 'required': False, 'type': 'string'}, 'uniprot_accession': {'description': "Alias for qualifier: UniProt accession (e.g., 'P69905').", 'required': False, 'type': 'string'}, 'uniprot_id': {'description': "Alias for qualifier: UniProt accession (e.g., 'P69905').", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- InterPro_get_protein_domains signature={'properties': {'protein_id': {'description': 'UniProt protein ID (e.g., P05067, Q9Y6K9)', 'required': True, 'type': 'string'}}, 'required': ['protein_id'], 'type': 'object'}
- UniProt_get_ptm_processing_by_accession signature={'properties': {'accession': {'description': 'UniProtKB accession, e.g., P05067.', 'required': True, 'type': 'string'}}, 'required': ['accession'], 'type': 'object'}
- GO_get_annotations_for_gene signature={'properties': {'gene_id': {'description': "A gene identifier such as gene symbol (e.g., 'TP53') or database ID.", 'required': True, 'type': 'string'}, 'rows': {'default': 100, 'description': 'Maximum number of annotations to return. Default: 100. Use a lower value (e.g., 25) for genes with many annotations like TP53.', 'required': False, 'type': 'integer'}}, 'required': ['gene_id'], 'type': 'object'}
- kegg_get_gene_info signature={'properties': {'gene_id': {'description': "KEGG gene identifier (e.g., 'hsa:348', 'hsa:3480')", 'required': True, 'type': 'string'}}, 'required': ['gene_id'], 'type': 'object'}
- WikiPathways_search signature={'properties': {'organism': {'description': "Organism filter (scientific name), e.g., 'Homo sapiens'.", 'required': False, 'type': 'string'}, 'query': {'description': "Free-text query (keywords, gene symbols, processes), e.g., 'p53', 'glycolysis'.", 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- enrichr_gene_enrichment_analysis signature={'properties': {'gene_list': {'description': 'List of gene names or symbols to analyze. At least 2 genes are required for path ranking analysis.', 'items': {'type': 'string'}, 'minItems': 2, 'required': True, 'type': 'array'}, 'libs': {'default': ['WikiPathways_2024_Human', 'Reactome_Pathways_2024', 'MSigDB_Hallmark_2020', 'GO_Molecular_Function_2023', 'GO_Biological_Process_2023'], 'description': 'List of enrichment libraries to use for analysis.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': ['gene_list'], 'type': 'object'}
- intact_get_complex_details signature={'properties': {'complex_ac': {'description': "Complex AC (Complex Accession) in format 'CPX-XXXXX' (e.g., 'CPX-915', 'CPX-10081'). Get complex ACs from intact_get_interactions_by_complex search results.", 'required': True, 'type': 'string'}, 'format': {'default': 'json', 'enum': ['json', 'xml'], 'required': False, 'type': 'string'}}, 'required': ['complex_ac'], 'type': 'object'}
- BioGRID_get_interactions signature={'properties': {'evidence_types': {'description': "Filter by evidence types (e.g., ['Affinity Capture-MS', 'Two-hybrid'] for physical, ['Synthetic Lethality', 'Dosage Rescue'] for genetic). Leave empty for all evidence types.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'gene_name': {'description': "Alias for gene_names: single gene symbol (e.g., 'TP53'). Converted to gene_names list automatically.", 'required': False, 'type': 'string'}, 'gene_names': {'description': "List of gene names or protein identifiers (e.g., ['TP53', 'BRCA1', 'MYC']). Accepts official gene symbols.", 'items': {'type': 'string'}, 'minItems': 1, 'required': False, 'type': 'array'}, 'interaction_type': {'default': 'both', 'description': "Type of interaction: 'physical' (protein-protein), 'genetic' (epistasis, synthetic lethality), 'both' (all interactions)", 'enum': ['physical', 'genetic', 'both'], 'required': False, 'type': 'string'}, 'limit': {'default': 100, 'description': 'Maximum number of interactions to return (default: 100, max: 10000)', 'maximum': 10000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'organism': {'default': '9606', 'description': "Organism name (e.g., 'Homo sapiens', 'Mus musculus') or NCBI taxonomy ID (e.g., '9606' for human, '10090' for mouse). Default: 9606 (human)", 'required': False, 'type': 'string'}, 'throughput': {'description': "Filter by throughput: 'low' (low-throughput studies), 'high' (high-throughput screens), or leave empty for all", 'enum': ['low', 'high', ''], 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- HPA_get_protein_interactions_by_gene signature={'properties': {'gene_name': {'description': "Official gene symbol, e.g., 'EGFR', 'TP53', 'BRCA1', etc.", 'required': True, 'type': 'string'}}, 'required': ['gene_name'], 'type': 'object'}
- HPA_get_rna_expression_by_source signature={'properties': {'gene_name': {'description': "Gene name or gene symbol, e.g., 'GFAP', 'TP53', 'BRCA1', etc.", 'required': True, 'type': 'string'}, 'source_name': {'description': "The specific name of the biological source, e.g., 'liver', 'heart_muscle', 't_cell', 'hepatocytes', 'cerebellum'. Must be a valid name from the comprehensive HPA columns mapping.", 'required': True, 'type': 'string'}, 'source_type': {'description': "The type of biological source. Choose from: 'tissue', 'blood', 'brain', 'single_cell'.", 'required': True, 'type': 'string'}}, 'required': ['gene_name', 'source_type', 'source_name'], 'type': 'object'}
- HPA_get_subcellular_location signature={'properties': {'gene_name': {'description': "Gene name or gene symbol, e.g., 'CCNB1', 'TP53', 'EGFR', etc.", 'required': True, 'type': 'string'}}, 'required': ['gene_name'], 'type': 'object'}
- HPA_get_cancer_prognostics_by_gene signature={'properties': {'ensembl_id': {'description': "Ensembl Gene ID of the gene to check, e.g., 'ENSG00000141510' for TP53, 'ENSG00000012048' for BRCA1.", 'required': True, 'type': 'string'}}, 'required': ['ensembl_id'], 'type': 'object'}
- gnomad_get_gene_constraints signature={'properties': {'gene_symbol': {'description': "Gene symbol (e.g., 'BRCA1', 'TP53')", 'required': True, 'type': 'string'}, 'reference_genome': {'default': 'GRCh38', 'description': 'Reference genome.', 'enum': ['GRCh37', 'GRCh38'], 'required': False, 'type': 'string'}}, 'required': ['gene_symbol'], 'type': 'object'}
- ClinVar_search_variants signature={'properties': {'clinical_significance': {'description': "Filter by clinical significance (e.g., 'Pathogenic', 'Likely pathogenic', 'Benign', 'Uncertain significance', 'VUS'). Applied client-side after retrieval.", 'required': False, 'type': 'string'}, 'condition': {'description': "Disease or condition name (e.g., 'breast cancer', 'diabetes') At least one of gene, condition, or variant_id must be provided.", 'required': False, 'type': 'string'}, 'gene': {'description': "Gene name or symbol (e.g., 'BRCA1', 'BRCA2') At least one of gene, condition, or variant_id must be provided.", 'required': False, 'type': 'string'}, 'gene_symbol': {'description': 'Alias for gene. HGNC gene symbol (e.g., "DPYD", "CYP2C19").', 'required': False, 'type': ['string', 'null']}, 'limit': {'description': 'Alias for max_results: maximum number of results to return.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'max_results': {'default': 20, 'description': 'Maximum number of results to return (default: 20). Alias: limit.', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'query': {'description': 'Alias for condition. Free-text search mapped to condition/disease field.', 'required': False, 'type': ['string', 'null']}, 'significance': {'description': 'Alias for clinical_significance (e.g., "pathogenic", "benign", "uncertain_significance").', 'required': False, 'type': ['string', 'null']}, 'variant_id': {'description': "ClinVar variant ID (e.g., '12345') At least one of gene, condition, or variant_id must be provided.", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- civic_get_variants_by_gene signature={'properties': {'gene': {'description': "Alias for gene_name. Gene symbol (e.g., 'EGFR', 'KRAS').", 'required': False, 'type': 'string'}, 'gene_id': {'description': 'CIViC gene ID (e.g., 19 for EGFR, 12 for BRAF). Find gene IDs using civic_search_genes.', 'required': False, 'type': 'integer'}, 'gene_name': {'description': "Gene symbol (e.g., 'EGFR', 'BRAF', 'TP53'). Will be looked up automatically. Aliases: gene, gene_symbol, query.", 'required': False, 'type': 'string'}, 'gene_symbol': {'description': "Alias for gene_name. Standard gene symbol (e.g., 'KRAS', 'BRCA1', 'EGFR').", 'required': False, 'type': 'string'}, 'limit': {'default': 500, 'description': "Maximum number of variants to return (default: 500, uses cursor pagination to bypass CIViC's 100/page server cap)", 'required': False, 'type': 'integer'}}, 'required': [], 'type': 'object'}
- cBioPortal_get_mutations signature={'properties': {'gene_list': {'description': "Comma-separated gene symbols (e.g., 'BRCA1,BRCA2')", 'required': True, 'type': 'string'}, 'sample_list_id': {'description': 'Optional sample list ID. If not provided, uses all samples in the study.', 'required': False, 'type': 'string'}, 'study_id': {'description': "Cancer study ID (e.g., 'brca_tcga')", 'required': True, 'type': 'string'}}, 'required': ['study_id', 'gene_list'], 'type': 'object'}
- DGIdb_get_gene_druggability signature={'properties': {'gene': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'genes': {'description': 'List of gene symbols to check druggability. Aliases: gene_name, gene.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- DGIdb_get_drug_gene_interactions signature={'properties': {'gene': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'gene_name': {'description': "Alias for genes. Single gene symbol (e.g., 'EGFR').", 'required': False, 'type': 'string'}, 'genes': {'description': "List of gene symbols (e.g., ['EGFR', 'BRAF']). Also accepts a single gene as string. Aliases: gene_name, gene.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_sources': {'description': "Optional filter by data sources (e.g., ['DrugBank', 'ChEMBL']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'interaction_types': {'description': "Optional filter by interaction types (e.g., ['inhibitor', 'antagonist']).", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}}, 'required': [], 'type': 'object'}
- ChEMBL_search_targets signature={'properties': {'fields': {'description': "Optional list of ChEMBL target fields to include in each returned target object (projection). ToolUniverse maps this to ChEMBL's `only` query parameter (comma-separated). Supported fields: target_chembl_id, pref_name, organism, target_type, target_components.", 'items': {'enum': ['target_chembl_id', 'pref_name', 'organism', 'target_type', 'target_components'], 'type': 'string'}, 'required': False, 'type': 'array', 'uniqueItems': True}, 'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'organism': {'description': "Filter by organism (e.g., 'Homo sapiens')", 'required': False, 'type': 'string'}, 'pref_name__contains': {'description': 'Filter by target name (contains)', 'required': False, 'type': 'string'}, 'target_chembl_id': {'description': 'Filter by target ChEMBL ID', 'required': False, 'type': 'string'}, 'target_type': {'description': "Filter by target type (e.g., 'SINGLE PROTEIN', 'PROTEIN COMPLEX')", 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- ChEMBL_get_target_activities signature={'oneOf': [{'required': ['target_chembl_id__exact']}, {'required': ['target_chembl_id']}], 'properties': {'limit': {'default': 20, 'maximum': 1000, 'required': False, 'type': 'integer'}, 'offset': {'default': 0, 'required': False, 'type': 'integer'}, 'target_chembl_id': {'description': 'Alias for target_chembl_id__exact. ChEMBL target ID (e.g., CHEMBL213).', 'required': False, 'type': 'string'}, 'target_chembl_id__exact': {'description': "ChEMBL target ID (e.g., 'CHEMBL2074'). To find a target ID, use ChEMBL_search_targets with a target name or gene symbol.", 'required': False, 'type': 'string'}}, 'type': 'object'}
- Pharos_get_target signature={'properties': {'gene': {'description': "Gene symbol (e.g., 'EGFR', 'TP53', 'BRCA1'). Use either gene or uniprot.", 'required': False, 'type': 'string'}, 'uniprot': {'description': "UniProt accession (e.g., 'P00533'). Use either gene or uniprot.", 'required': False, 'type': 'string'}}, 'type': 'object'}
- BindingDB_get_ligands_by_uniprot signature={'properties': {'affinity_cutoff': {'default': 10000, 'description': 'Maximum affinity in nM (default: 10000)', 'required': False, 'type': 'integer'}, 'uniprot_id': {'description': 'UniProt accession ID (e.g., P00533 for EGFR)', 'required': True, 'type': 'string'}}, 'required': ['uniprot_id'], 'type': 'object'}
- PubChem_search_assays_by_target_gene signature={'properties': {'gene_symbol': {'description': 'Gene symbol to search (e.g., EGFR, USP2, TP53)', 'required': True, 'type': 'string'}}, 'required': ['gene_symbol'], 'type': 'object'}
- DepMap_get_gene_dependencies signature={'properties': {'gene_symbol': {'description': "Gene symbol (e.g., 'EGFR', 'KRAS', 'TP53')", 'required': True, 'type': 'string'}, 'model_id': {'description': 'Optional: Filter by specific cell line', 'required': False, 'type': 'string'}}, 'required': ['gene_symbol'], 'type': 'object'}
- GPCRdb_get_ligands signature={'properties': {'ligand_type': {'description': 'Alias for type. Ligand class filter (e.g., small molecule, peptide).', 'required': False, 'type': 'string'}, 'limit': {'description': 'Maximum number of ligands to return (default: all). Use to cap large result sets.', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit. Maximum number of ligands to return.', 'required': False, 'type': 'integer'}, 'operation': {'const': 'get_ligands', 'description': 'Operation type (fixed: get_ligands)', 'required': False, 'type': 'string'}, 'protein': {'description': 'Protein entry name (e.g., adrb2_human)', 'required': False, 'type': 'string'}, 'protein_id': {'description': 'Alias for protein parameter', 'required': False, 'type': 'string'}, 'protein_name': {'description': 'Alias for protein. GPCRdb entry name (e.g., adrb2_human).', 'required': False, 'type': 'string'}, 'receptor_name': {'description': 'Alias for protein. GPCRdb entry name (e.g., adrb2_human).', 'required': False, 'type': 'string'}, 'type': {'description': 'Ligand class filter (e.g., small molecule, peptide, antibody).', 'required': False, 'type': 'string'}}, 'required': [], 'type': 'object'}
- PubMed_search_articles signature={'properties': {'datetype': {'default': 'pdat', 'description': "Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), or 'mdat' (modification date). Required when using mindate/maxdate.", 'required': False, 'type': 'string'}, 'include_abstract': {'default': False, 'description': 'If true, best-effort fetches abstracts via efetch (adds abstract/abstract_source fields).', 'required': False, 'type': 'boolean'}, 'limit': {'default': 10, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from PubMed (max: 200).', 'required': False, 'type': 'integer'}, 'max_results': {'description': 'Alias for limit â\x80\x94 maximum number of results to return', 'required': False, 'type': 'integer'}, 'maxdate': {'description': 'Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'mindate': {'description': 'Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to be set.', 'required': False, 'type': 'string'}, 'query': {'description': "Search query for PubMed articles. Use keywords, author names, journal names, or MeSH terms. Examples: 'cancer immunotherapy', 'Smith J[Author]', 'Nature[Journal]', 'diabetes[MeSH]'. Use AND/OR/NOT for complex queries.", 'required': True, 'type': 'string'}, 'sort': {'description': "Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (alphabetical by first author), 'JournalName' (alphabetical by journal), 'relevance' (default PubMed ranking).", 'required': False, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- PubMed_get_related signature={'properties': {'limit': {'default': 20, 'description': 'Maximum number of related articles to return (default: 20, max: 100).', 'maximum': 100, 'minimum': 1, 'required': False, 'type': 'integer'}, 'pmid': {'description': "PubMed ID (PMID) for which to find related articles (e.g., '20210808', '19879512'). Find PMIDs using PubMed_search_articles.", 'required': True, 'type': 'string'}}, 'required': ['pmid'], 'type': 'object'}
- EuropePMC_search_articles signature={'properties': {'enrich_missing_abstract': {'default': False, 'description': 'If true, best-effort fills missing abstracts by fetching Europe PMC fullTextXML (bounded to a few results).', 'required': False, 'type': 'boolean'}, 'extract_terms_from_fulltext': {'description': "Optional list of terms to extract from full text (open access only). When provided, automatically fetches fullTextXML for open-access articles and returns snippets around these terms. Terms are processed in batches of 5 internally, so any number of terms is accepted. Bounded to first 3 OA articles to avoid latency. Returns snippets in a 'fulltext_snippets' field for each article.", 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'fulltext_terms': {'description': 'Optional list of terms that must occur in the indexed full text (Europe PMC BODY field). When provided, the tool adds a BODY:"..." clause and automatically enables `require_has_ft`.', 'items': {'type': 'string'}, 'required': False, 'type': 'array'}, 'limit': {'default': 5, 'description': 'Number of articles to return. This sets the maximum number of articles retrieved from Europe PMC.', 'required': False, 'type': 'integer'}, 'page_size': {'description': 'Alias for limit â\x80\x94 number of results to return', 'required': False, 'type': 'integer'}, 'query': {'description': 'Search query for Europe PMC. Supports Lucene-like fielded syntax (e.g., BODY:"term", INTRO:"term", METHODS:"term").', 'required': True, 'type': 'string'}, 'require_has_ft': {'default': False, 'description': 'If true, appends `HAS_FT:Y` to the query to restrict results to records where Europe PMC has full text indexed. This is NOT the same as having a link to free full text elsewhere (e.g., PMC) and is often the key reason body-only keywords cannot be found via Europe PMC search.', 'required': False, 'type': 'boolean'}}, 'required': ['query'], 'type': 'object'}
- EuropePMC_get_citations signature={'properties': {'article_id': {'description': 'Article ID from the source database (e.g., PMID for MED source)', 'required': True, 'type': 'string'}, 'page': {'default': 1, 'description': 'Page number for pagination (default: 1)', 'minimum': 1, 'required': False, 'type': 'integer'}, 'page_size': {'default': 25, 'description': 'Number of citations to retrieve (default: 25, max: 1000)', 'maximum': 1000, 'minimum': 1, 'required': False, 'type': 'integer'}, 'source': {'default': 'MED', 'description': "Source database (e.g., 'MED' for PubMed, 'PMC' for PMC). Usually 'MED' for most articles.", 'required': False, 'type': 'string'}}, 'required': ['article_id'], 'type': 'object'}
- PubTator3_LiteratureSearch signature={'properties': {'limit': {'description': 'Maximum number of results to return (applied client-side). The PubTator3 API returns 10 results per page; this parameter truncates the results to the requested count.', 'required': False, 'type': 'integer'}, 'page': {'default': 0, 'description': 'Zero-based results page (optional; default = 0).', 'required': False, 'type': 'integer'}, 'page_size': {'default': 10, 'description': 'How many PMIDs to return per page (optional; default = 10; note: the PubTator3 API always returns 10 per page regardless of this value).', 'required': False, 'type': 'integer'}, 'query': {'description': 'What you want to search for. This can be plain keywords, a single PubTator ID, or the special relation syntax shown above.', 'required': True, 'type': 'string'}}, 'required': ['query'], 'type': 'object'}
- GtoPdb_search_ligands signature={'properties': {'approved': {'description': 'Filter to approved drugs only (true) or all ligands (false/omit)', 'required': False, 'type': ['boolean', 'null']}, 'name': {'description': "Ligand name or INN to search. Examples: 'aspirin', 'morphine', 'dopamine', 'caffeine', 'insulin'", 'required': False, 'type': ['string', 'null']}, 'query': {'description': 'Name/keyword to search for. Alias for the "name" parameter.', 'required': False, 'type': ['string', 'null']}, 'type': {'description': "Ligand type filter. Values: 'Approved', 'Synthetic organic', 'Natural product', 'Endogenous peptide', 'Antibody', 'Inorganic'", 'required': False, 'type': ['string', 'null']}}, 'required': [], 'type': 'object'}

## UNAVAILABLE → SUBSTITUTE
- DisGeNET_search_gene: SUBSTITUTE with OpenTargets_get_asso_targ_by_dise_efoI. DisGeNET has no API key; OpenTargets association-targets covers the gene-disease links DisGeNET would have text-mined.

# TARGET SKILL TO CONVERT
---
name: tooluniverse-target-research
description: Comprehensive drug-target intelligence — tissue expression (GTEx, HPA), pathways, protein interactions (STRING), variant landscape (ClinVar, gnomAD), druggability (DGIdb, ChEMBL approved drugs). 9 parallel research paths with citations. Use for full target profile reports, target characterization for drug discovery, and 'tell me about target X' queries.
disable-model-invocation: true
---

# Comprehensive Target Intelligence Gatherer

Gather complete target intelligence by exploring 9 parallel research paths. Supports targets identified by gene symbol, UniProt accession, Ensembl ID, or gene name.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Tool parameter verification** - Verify params via `get_tool_info` before calling unfamiliar tools
3. **Evidence grading** - Grade all claims by evidence strength (T1-T4)
4. **Citation requirements** - Every fact must have inline source attribution
5. **Mandatory completeness** - All sections must exist with data minimums or explicit "No data" notes
6. **Disambiguation first** - Resolve all identifiers before research
7. **Negative results documented** - "No drugs found" is data; empty sections are failures
8. **Collision-aware literature search** - Detect and filter naming collisions
9. **English-first queries** - Always use English terms in tool calls, even if the user writes in another language. Translate gene names, disease names, and search terms to English. Only try original-language terms as a fallback if English returns no results. Respond in the user's language

---

## LOOK UP, DON'T GUESS

When asked about a specific protein or gene target, look it up in UniProt/Ensembl/OpenTargets BEFORE reasoning about it. Verify the gene name, function, and disease associations from databases. When you're not sure about a fact, your first instinct should be to SEARCH for it using tools, not to reason harder from memory.

---

## When to Use This Skill

Apply when users:
- Ask about a drug target, protein, or gene
- Need target validation or assessment
- Request druggability analysis
- Want comprehensive target profiling
- Ask "what do we know about [target]?"
- Need target-disease associations
- Request safety profile for a target

**When NOT to use**: Simple protein lookup, drug-only queries, disease-centric queries, sequence retrieval, structure download — use specialized skills instead.

---

## Target Evaluation Reasoning Framework

Evaluating a drug target requires reasoning across four interconnected questions. Answer all four before forming a recommendation.

**1. Is there genetic evidence linking this target to the disease?**
Genetic evidence is the strongest predictor of drug success — targets with human genetic support have approximately twice the clinical success rate as those without (Nelson et al. 2015). Ask: Are there GWAS associations connecting this gene to the disease? Do rare loss-of-function or gain-of-function variants cause or protect against the disease? Does the mouse knockout phenotype match the human disease (from OpenTargets mouse models)? OpenTargets assigns genetic evidence scores; a score > 0.7 indicates strong support. ClinVar rare variant evidence and DisGeNET curated gene-disease association scores add complementary layers. A target with no genetic link to the disease of interest carries a fundamental validation risk that cannot be resolved by downstream data.

**2. Is the target druggable?**
Druggability has two components: structural accessibility and prior chemical matter. Structural accessibility means the target has a binding pocket where a small molecule or biologic can engage — surface-exposed receptors, enzymes with well-defined active sites, and protein-protein interaction interfaces with hot spots are tractable. Intrinsically disordered proteins and transcription factors with flat, featureless binding surfaces are typically harder. Pharos TDL classification provides a tiered assessment: Tclin (approved drug), Tchem (known active compounds), Tbio (biological function known but no drugs), Tdark (poorly characterized). If ChEMBL or BindingDB have compounds with IC50 < 1μM, the target is chemically tractable. Chemical probes (from OpenTargets chemical probes endpoint) confirm a target can be modulated, which is distinct from drug-like compounds. For GPCRs, check GPCRdb for curated agonists and antagonists.

**3. Is the target safe to modulate?**
Safety concerns arise from two sources. First, on-target effects: if the target is essential in normal tissues (mouse KO is lethal, or gnomAD pLI is high / LOEUF is low), full inhibition will produce toxicity — the question becomes whether a partial agonist or tissue-targeted delivery can provide a therapeutic window. Second, off-target effects: does the gene have family members that could be inadvertently hit? The OpenTargets safety profile aggregates known toxicity annotations, and DepMap essentiality scores tell you which cancer cell lines require this gene for survival (useful but not directly translatable to normal tissues). Expression specificity matters: a target expressed only in the disease-relevant tissue is far safer than one expressed ubiquitously in critical organs (heart, kidney, brain).

**4. What is the competitive landscape?**
A target with approved drugs may already be validated but competitive; a target with clinical-stage programs from competitors establishes feasibility while creating IP barriers. An entirely novel target with no drug history requires more extensive internal validation. Assess: number of ChEMBL bioactivity records (chemical matter depth), approved drugs from OpenTargets drug associations, and literature activity trends (recent paper count and key research groups). A dark target (Tdark) with strong genetic evidence but no chemical matter is a high-risk, high-reward opportunity.

**Synthesizing the four dimensions**: The ideal target has strong genetic evidence (GWAS + rare variant), a tractable binding site (Tclin or Tchem), acceptable safety profile (tissue-specific expression, non-lethal KO), and manageable competition. Gaps in any dimension represent validation tasks, not disqualifiers — but they must be acknowledged. A target with perfect druggability but no genetic link to disease is a tractability exercise, not a validated therapeutic hypothesis.

---

## Phase 0: Tool Parameter Verification (CRITICAL)

**BEFORE calling ANY tool for the first time**, verify its parameters:

```python
tool_info = tu.tools.get_tool_info(tool_name="Reactome_map_uniprot_to_pathways")
# Reveals: takes `id` not `uniprot_id`
```

Known parameter corrections:
- `Reactome_map_uniprot_to_pathways`: param is `id` (not `uniprot_id`)
- `ensembl_get_xrefs`: param is `id` (not `gene_id`)
- `GTEx_get_median_gene_expression`: requires `gencode_id` + `operation="median"`; try versioned Ensembl ID if empty
- `OpenTargets_*`: param is `ensemblId` (camelCase, not `ensemblID`)
- `STRING_get_protein_interactions`: takes `protein_ids` (list) + `species`
- `intact_get_interactions`: takes `identifier` (UniProt accession, not gene symbol)

---

## Critical Workflow Requirements

**Report-First (MANDATORY)**: Create `[TARGET]_target_report.md` with all section headers and `[Researching...]` placeholders before starting research. Update progressively. Do not show raw tool outputs to the user.

**Evidence Grading (MANDATORY)**: Grade every claim T1-T4. T1 = clinical/genetic data; T2 = curated databases or multiple studies; T3 = computational or single study; T4 = annotation or catalog entry.

---

## Core Strategy: 9 Research Paths

```
Target Query (e.g., "EGFR" or "P00533")
|
+- IDENTIFIER RESOLUTION (always first)
|   +- Check if GPCR -> GPCRdb_get_protein
|
+- PATH 0: Open Targets Foundation (ALWAYS FIRST - fills gaps in all other paths)
|
+- PATH 1: Core Identity (names, IDs, sequence, organism)
|   +- InterProScan_scan_sequence for novel domain prediction
+- PATH 2: Structure & Domains (3D structure, domains, binding sites)
|   +- If GPCR: GPCRdb_get_structures (active/inactive states)
+- PATH 3: Function & Pathways (GO terms, pathways, biological role)
+- PATH 4: Protein Interactions (PPI network, complexes)
+- PATH 5: Expression Profile (tissue expression, single-cell)
+- PATH 6: Variants & Disease (mutations, clinical significance)
|   +- DisGeNET_search_gene for curated gene-disease associations
+- PATH 7: Drug Interactions (known drugs, druggability, safety)
|   +- Pharos_get_target for TDL classification (Tclin/Tchem/Tbio/Tdark)
|   +- BindingDB_get_ligands_by_uniprot for known ligands
|   +- PubChem_search_assays_by_target_gene for HTS data
|   +- If GPCR: GPCRdb_get_ligands (curated agonists/antagonists)
|   +- DepMap_get_gene_dependencies for target essentiality
+- PATH 8: Literature & Research (publications, trends)
```

For detailed code implementations of each path, see [IMPLEMENTATION.md](IMPLEMENTATION.md).

---

## Identifier Resolution (Phase 1)

Resolve ALL identifiers before any research path. Required IDs:
- **UniProt accession** (for protein data, structure, interactions)
- **Ensembl gene ID** + versioned ID (for Open Targets, GTEx)
- **Gene symbol** (for DGIdb, gnomAD, literature)
- **Entrez gene ID** (for KEGG, MyGene)
- **ChEMBL target ID** (for bioactivity)
- **Synonyms/full name** (for collision-aware literature search)

After resolution, check if target is a GPCR via `GPCRdb_get_protein`. See [IMPLEMENTATION.md](IMPLEMENTATION.md) for resolution and GPCR detection code.

---

## PATH 0: Open Targets Foundation (ALWAYS FIRST)

Run OpenTargets endpoints first to populate baseline data before specialized queries:
- `OpenTargets_get_diseases_phenotypes_by_target_ensembl` → disease associations (Section 8)
- `OpenTargets_get_target_tractability_by_ensemblID` → druggability assessment (Section 9)
- `OpenTargets_get_target_safety_profile_by_ensemblID` → safety liabilities (Section 10)
- `OpenTargets_get_target_interactions_by_ensemblID` → PPI network (Section 6)
- `OpenTargets_get_target_gene_ontology_by_ensemblID` → GO annotations (Section 5)
- `OpenTargets_get_publications_by_target_ensemblID` → literature (Section 11)
- `OpenTargets_get_biological_mouse_models_by_ensemblID` → mouse KO phenotypes (Sections 8/10)
- `OpenTargets_get_chemical_probes_by_target_ensemblID` → chemical probes (Section 9)
- `OpenTargets_get_associated_drugs_by_target_ensemblID` → known drugs (Section 9)

---

## PATH 1: Core Identity

**Tools**: `UniProt_get_entry_by_accession`, `UniProt_get_function_by_accession`, `UniProt_get_recommended_name_by_accession`, `UniProt_get_alternative_names_by_accession`, `UniProt_get_subcellular_location_by_accession`, `MyGene_get_gene_annotation`

**Populates**: Sections 2 (Identifiers), 3 (Basic Information)

---

## PATH 2: Structure & Domains

Use 3-step structure search chain (do NOT rely solely on PDB text search):
1. **UniProt PDB cross-references** (most reliable)
2. **Sequence-based PDB search** (catches missing annotations)
3. **Domain-based search** (for multi-domain proteins)
4. **AlphaFold** (always check)

**Tools**: `UniProt_get_entry_by_accession` (PDB xrefs), `RCSBData_get_entry`, `PDB_search_similar_structures`, `alphafold_get_prediction`, `InterPro_get_protein_domains`, `UniProt_get_ptm_processing_by_accession`

**GPCR targets**: Also query `GPCRdb_get_structures` for active/inactive state data.

**Populates**: Section 4 (Structural Biology)

---

## PATH 3: Function & Pathways

**Tools**: `GO_get_annotations_for_gene`, `Reactome_map_uniprot_to_pathways`, `kegg_get_gene_info`, `WikiPathways_search`, `enrichr_gene_enrichment_analysis`

**Populates**: Section 5 (Function & Pathways)

---

## PATH 4: Protein Interactions

**Tools**: `STRING_get_protein_interactions`, `intact_get_interactions`, `intact_get_complex_details`, `BioGRID_get_interactions`, `HPA_get_protein_interactions_by_gene`

**Minimum**: 20 interactors OR documented explanation.

**Populates**: Section 6 (Protein-Protein Interactions)

---

## PATH 5: Expression Profile

GTEx with versioned ID fallback + HPA as backup.

**Tools**: `GTEx_get_median_gene_expression`, `HPA_get_rna_expression_by_source`, `HPA_get_comprehensive_gene_details_by_ensembl_id`, `HPA_get_subcellular_location`, `HPA_get_cancer_prognostics_by_gene`, `HPA_get_comparative_expression_by_gene_and_cellline`, `CELLxGENE_get_expression_data`

**Reasoning**: Expression specificity directly informs safety. Note whether expression is enriched in the disease-relevant tissue vs. critical organs. Ubiquitous essential expression narrows the therapeutic window.

**Populates**: Section 7 (Expression Profile)

---

## PATH 6: Variants & Disease

Separate SNVs from CNVs in ClinVar results. Integrate DisGeNET for curated gene-disease association scores.

**Tools**: `gnomad_get_gene_constraints`, `ClinVar_search_variants`, `OpenTargets_get_diseases_phenotypes_by_target_ensembl`, `DisGeNET_search_gene`, `civic_get_variants_by_gene`, `cBioPortal_get_mutations`

**Required constraint scores**: pLI (probability of loss-of-function intolerance), LOEUF (loss-of-function observed/expected upper bound), missense Z-score, pRec (recessive probability). High pLI (> 0.9) or low LOEUF (< 0.35) indicates the gene is intolerant to loss-of-function — a major safety flag for inhibitory therapeutic strategies.

**Populates**: Section 8 (Genetic Variation & Disease)

---

## PATH 7: Druggability & Target Validation

**Tools**: `OpenTargets_get_target_tractability_by_ensemblID`, `DGIdb_get_gene_druggability`, `DGIdb_get_drug_gene_interactions`, `ChEMBL_search_targets`, `ChEMBL_get_target_activities`, `Pharos_get_target`, `BindingDB_get_ligands_by_uniprot`, `PubChem_search_assays_by_target_gene`, `DepMap_get_gene_dependencies`, `OpenTargets_get_target_safety_profile_by_ensemblID`, `OpenTargets_get_biological_mouse_models_by_ensemblID`

**GPCR targets**: Also query `GPCRdb_get_ligands`.

**Reasoning**: Pharos TDL tells you where the target sits in the knowledge landscape. BindingDB Ki/IC50/Kd values tell you whether the target has been demonstrated tractable experimentally. DepMap essentiality tells you whether cancer cells require this gene (proxy for toxicity risk, not a definitive answer).

**Populates**: Sections 9 (Druggability), 10 (Safety), 12 (Competitive Landscape)

---

## PATH 8: Literature & Research (Collision-Aware)

1. **Detect collisions** - Check if gene symbol has non-biological meanings
2. **Build seed queries** - Symbol in title with bio context, full name, UniProt accession
3. **Apply collision filter** - Add NOT terms for off-topic meanings
4. **Expand via citations** - For sparse targets (<30 papers), use citation network
5. **Classify by evidence tier** - T1-T4 based on title/abstract keywords

**Tools**: `PubMed_search_articles`, `PubMed_get_related`, `EuropePMC_search_articles`, `EuropePMC_get_citations`, `PubTator3_LiteratureSearch`, `OpenTargets_get_publications_by_target_ensemblID`

**Populates**: Section 11 (Literature & Research Landscape)

---

## Retry Logic & Fallback Chains

- `ChEMBL_get_target_activities` fails → `GtoPdb_search_ligands` → `OpenTargets drugs`
- `intact_get_interactions` fails → `STRING_get_protein_interactions` → `OpenTargets interactions`
- `GO_get_annotations_for_gene` fails → `OpenTargets GO` → `MyGene GO`
- `GTEx_get_median_gene_expression` fails → `HPA_get_rna_expression_by_source` → document as unavailable
- `gnomad_get_gene_constraints` fails → `OpenTargets constraint` endpoint
- `DGIdb_get_drug_gene_interactions` fails → `OpenTargets drugs` → `GtoPdb_search_ligands`

**NEVER silently skip failed tools.** Always document failures and fallbacks in the report.

---

## Completeness Audit (REQUIRED before finalizing)

Before finalizing any report:
- Data minimums met for PPIs, expression, diseases, constraints, druggability
- Negative results documented explicitly
- T1-T4 grades in Executive Summary, Disease Associations, Key Papers, Recommendations
- Every data point has source attribution

---

## Report Template

Create `[TARGET]_target_report.md` with all 15 sections initialized. See [REPORT_FORMAT.md](REPORT_FORMAT.md) for the full template.

```
## 1. Executive Summary          ## 9. Druggability & Pharmacology
## 2. Target Identifiers         ## 10. Safety Profile
## 3. Basic Information          ## 11. Literature & Research
## 4. Structural Biology         ## 12. Competitive Landscape
## 5. Function & Pathways        ## 13. Summary & Recommendations
## 6. Protein-Protein Interactions ## 14. Data Sources & Methodology
## 7. Expression Profile         ## 15. Data Gaps & Limitations
## 8. Genetic Variation & Disease
```

---

## Synthesis: Target Assessment Framework

After completing all 9 PATHs, synthesize findings into a GO/NO-GO recommendation in the Executive Summary. Score each dimension:

- **Genetic evidence**: Strong (GWAS + rare variant + functional) / Moderate (GWAS or rare variant only) / Weak (expression change only) / None
- **Disease association**: Based on OpenTargets score (> 0.7 strong, 0.3-0.7 moderate, < 0.3 weak)
- **Druggability**: Approved drug exists / Tractable (known binding site, chemical probes) / Predicted tractable (structural pocket) / Undruggable
- **Safety**: Non-essential gene (viable KO, low pLI) / Essential with phenotype / Lethal KO or high pLI / Known toxicity target
- **Selectivity**: Disease-specific or enriched expression / Ubiquitous / Expressed in critical organs
- **Structural data**: High-res crystal with ligand / AlphaFold confident (pLDDT > 80) / Homology model / No structural info

Total score guides recommendation: strong target (all dimensions favorable), promising with defined validation tasks (2-3 gaps), speculative (multiple critical gaps), or deprioritize (no genetic link and poor druggability).

---

## Reference Files

| File | Contents |
|------|----------|
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | Detailed code for identifier resolution, GPCR detection, each PATH implementation, retry logic |
| [EVIDENCE_GRADING.md](EVIDENCE_GRADING.md) | T1-T4 tier definitions, citation format, completeness audit checklist, data minimums |
| [REPORT_FORMAT.md](REPORT_FORMAT.md) | Full report template with all 15 sections, table formats, section-specific guidance |
| [REFERENCE.md](REFERENCE.md) | Complete tool reference (225+ tools) organized by category with parameters |
| [EXAMPLES.md](EXAMPLES.md) | Worked examples: EGFR full profile, KRAS druggability, target comparison, CDK4 validation, Alzheimer's targets |


# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
