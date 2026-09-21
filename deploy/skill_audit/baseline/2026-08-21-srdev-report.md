# Skill coverage sweep

**fail** 61 · **retry** 4 · **warn** 10 · **pass** 1

| skill | verdict | codes | calls | answer |
| --- | --- | --- | --- | --- |
| protein-structure-prediction | fail | lookup_miss, schema_rejected, skill_after_web, wrong_skill | 20 | 3434 |
| binder-discovery | fail | linkless_footnote, skill_after_web, skill_without_tools, wrong_skill | 7 | 6179 |
| protein-lof-mechanism | fail | schema_rejected, skill_after_web, tool_error, wrong_skill | 21 | 3370 |
| small-molecule-discovery | fail | linkless_footnote, missing_primary_tools, skill_after_web | 10 | 3871 |
| variant-functional-annotation | fail | linkless_footnote, skill_after_web, wrong_skill | 11 | 3294 |
| variant-interpretation | fail | lookup_miss, tool_error, wrong_skill | 19 | 6413 |
| cell-line-profiling | fail | linkless_footnote, skill_after_web | 13 | 10379 |
| clinical-data-integration | fail | linkless_footnote, wrong_skill | 16 | 13695 |
| clinical-guidelines | fail | skill_after_web, tool_error | 12 | 3044 |
| clinical-trial-design | fail | linkless_footnote, skill_after_web, skill_without_tools | 10 | 4999 |
| comparative-genomics | fail | schema_rejected, skill_after_web | 20 | 10370 |
| disease-research | fail | linkless_footnote, skill_without_tools, wrong_skill | 8 | 11103 |
| drug-drug-interaction | fail | schema_rejected, skill_after_web | 17 | 2673 |
| drug-mechanism-research | fail | answer_declined, no_skill_loaded | 9 | 3784 |
| drug-regulatory | fail | skill_after_web, tool_error | 18 | 7608 |
| drug-repurposing | fail | answer_declined, linkless_footnote, no_skill_loaded | 5 | 7714 |
| drug-research | fail | skill_after_web, tool_not_found | 30 | 14949 |
| expression-data-retrieval | fail | linkless_footnote, skill_after_web | 6 | 3402 |
| gwas-study-explorer | fail | linkless_footnote, schema_rejected, skill_after_web | 17 | 7088 |
| gwas-trait-to-gene | fail | schema_rejected, skill_after_web | 10 | 2110 |
| hla-immunogenomics | fail | skill_after_web, tool_error | 11 | 7824 |
| immunotherapy-response-prediction | fail | schema_rejected, skill_after_web, tool_error | 15 | 9584 |
| model-organism-genetics | fail | schema_rejected, skill_after_web, tool_error | 16 | 5479 |
| network-pharmacology | fail | answer_declined, linkless_footnote, no_skill_loaded | 6 | 6144 |
| neuroscience | fail | skill_after_web, skill_without_tools | 9 | 6558 |
| pathway-disease-genetics | fail | linkless_footnote, skill_without_tools, wrong_skill | 7 | 2626 |
| protein-structure-retrieval | fail | lookup_miss, schema_rejected | 20 | 7856 |
| regulatory-variant-analysis | fail | linkless_footnote, skill_after_web | 11 | 9498 |
| structural-variant-analysis | fail | skill_after_web, tool_not_found | 11 | 3697 |
| systems-biology | fail | linkless_footnote, skill_after_web, tool_error | 11 | 6026 |
| target-research | fail | skill_without_tools, wrong_skill | 9 | 5981 |
| variant-analysis | fail | tool_error, wrong_skill | 15 | 5813 |
| acmg-variant-classification | fail | tool_error | 15 | 5409 |
| adverse-event-detection | fail | tool_error | 9 | 2785 |
| aging-senescence | fail | linkless_footnote, no_skill_loaded | 5 | 6821 |
| antibody-engineering | fail | linkless_footnote, no_skill_loaded | 6 | 8537 |
| cancer-classification | fail | no_skill_loaded | 4 | 243 |
| cancer-genomics-tcga | fail | no_skill_loaded | 4 | 837 |
| cancer-variant-interpretation | fail | skill_without_tools | 8 | 4530 |
| chemical-compound-retrieval | fail | tool_error | 15 | 1677 |
| chemical-safety | fail | linkless_footnote, no_skill_loaded | 5 | 2517 |
| clinical-trial-matching | fail | no_skill_loaded | 4 | 5674 |
| crispr-screen-analysis | fail | no_skill_loaded | 4 | 3865 |
| drug-target-validation | fail | linkless_footnote | 18 | 12074 |
| functional-genomics-screens | fail | linkless_footnote, no_skill_loaded | 8 | 4309 |
| gene-disease-association | fail | linkless_footnote, no_skill_loaded | 5 | 3575 |
| gene-regulatory-networks | fail | no_skill_loaded | 3 | 4046 |
| gwas-drug-discovery | fail | linkless_footnote, no_skill_loaded | 6 | 6280 |
| gwas-finemapping | fail | no_skill_loaded | 6 | 2832 |
| gwas-snp-interpretation | fail | linkless_footnote, no_skill_loaded | 5 | 1848 |
| immunology | fail | linkless_footnote, no_skill_loaded | 7 | 6437 |
| literature-deep-research | fail | linkless_footnote, no_skill_loaded | 5 | 3051 |
| precision-medicine-stratification | fail | no_skill_loaded | 5 | 4702 |
| precision-oncology | fail | linkless_footnote, no_skill_loaded | 5 | 5491 |
| protein-interactions | fail | no_skill_loaded | 5 | 3468 |
| protein-modification-analysis | fail | linkless_footnote, no_skill_loaded | 3 | 2152 |
| protein-therapeutic-design | fail | linkless_footnote, no_skill_loaded | 8 | 6112 |
| rare-disease-genomics | fail | linkless_footnote | 16 | 12335 |
| regulatory-genomics | fail | no_skill_loaded | 4 | 3901 |
| vaccine-design | fail | no_skill_loaded | 4 | 2509 |
| variant-to-mechanism | fail | linkless_footnote, no_skill_loaded | 6 | 6389 |
| infectious-disease | retry | provider_refusal | 0 | 0 |
| protein-structural-annotation-pdb | retry | provider_refusal | 0 | 0 |
| sequence-analysis | retry | provider_refusal | 0 | 0 |
| sequence-retrieval | retry | provider_refusal | 0 | 0 |
| gpcr-structural-pharmacology | warn | lookup_miss, skill_after_web | 21 | 7432 |
| structural-proteomics | warn | answer_declined, lookup_miss, skill_after_web, wrong_skill | 10 | 2448 |
| noncoding-rna | warn | skill_after_web, wrong_skill | 14 | 6170 |
| adverse-outcome-pathway | warn | skill_after_web | 19 | 9318 |
| gene-enrichment | warn | skill_after_web | 9 | 10003 |
| kegg-disease-drug | warn | skill_after_web | 21 | 8201 |
| pharmacogenomics | warn | wrong_skill | 23 | 4876 |
| proteomics-data-retrieval | warn | skill_after_web | 9 | 2651 |
| rare-disease-diagnosis | warn | skill_after_web | 11 | 8154 |
| toxicology | warn | wrong_skill | 13 | 5177 |
| pharmacovigilance | pass | — | 15 | 10756 |
