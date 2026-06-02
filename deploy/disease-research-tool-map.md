# disease-research → SR TU registry tool map

Per-dimension tool routing for the disease-research persona. Every name below is
confirmed present in libs/tooluniverse/src/tooluniverse/data/*.json. The chat agent
reaches these via SMCP compact mode: find_tools(<description>) to resolve, then
execute_tool(name, args). Verified-good names are quoted exactly; if a name 404s at
runtime, find_tools by the description in the right-hand column.

| Dim | Section | Tools (exact registry names) |
|-----|---------|------------------------------|
| 1 | Identity & Classification | OSL_get_efo_id_by_disease_name (casing is registry-exact — do not normalize), ols_search_efo_terms, ols_get_efo_term, ols_get_efo_term_children, umls_search_concepts, umls_get_concept_details, icd_search_codes, snomed_search_concepts, OpenTargets_get_disease_id_description_by_name |
| 2 | Clinical Presentation | get_HPO_ID_by_phenotype, get_phenotype_by_HPO_ID, MedlinePlus_get_genetics_condition_by_name, MedlinePlus_search_topics_by_keyword |
| 3 | Genetic & Molecular Basis | OpenTargets_get_associated_targets_by_disease_efoId, OpenTargets_target_disease_evidence, ClinVar_search_variants, ClinVar_get_clinical_significance, ClinVar_get_variant_details, gwas_search_associations (casing is registry-exact — do not normalize), GWAS_search_associations_by_gene, gnomad_get_variant, gnomad_search_variants |
| 4 | Treatment Landscape | OpenTargets_get_associated_drugs_by_disease_efoId (disease-keyed; use first when agent holds EFO ID), OpenTargets_get_associated_drugs_by_target_ensemblID (target-keyed; use after Dim 3 yields Ensembl IDs), OpenTargets_get_drug_chembId_by_generic_name, resolve via find_tools("GtoPdb disease lookup") for GtoPdb disease-level entry |
| 5 | Biological Pathways | Reactome_get_pathway, Reactome_get_pathway_reactions, Reactome_map_uniprot_to_pathways, humanbase_ppi_analysis, GTEx_get_expression_summary, HPA_get_rna_expression_by_source |
| 6 | Epidemiology & Literature | PubMed_search_articles, EuropePMC_search_articles, openalex_search_works, SemanticScholar_search_papers |
| 7 | Similar Diseases | OpenTargets_get_disease_id_description_by_name (resolve seed EFO ID), OpenTargets_get_similar_entities_by_disease_efoId (fetch similar diseases once EFO ID is known) |
| 8 | Cancer-Specific (if applicable) | civic_search_genes, civic_get_variants_by_gene, civic_search_molecular_profiles, civic_search_therapies |
| 9 | Pharmacology | GtoPdb_search_targets, GtoPdb_get_interactions, GtoPdb_search_ligands |
| 10 | Drug Safety | FAERS_count_reactions_by_drug_event, OpenTargets_get_drug_warnings_by_chemblId |

## Name corrections applied (vs. plan draft)

The following names from the plan draft were absent from the registry and were corrected:

| Plan draft name | Status | Corrected to |
|-----------------|--------|--------------|
| `gnomad_get_variant_frequency` | MISSING | `gnomad_get_variant`, `gnomad_search_variants` |
| `GtoPdb_get_disease` | MISSING — no equivalent | resolve via `find_tools("GtoPdb disease lookup")` |
| `GtoPdb_get_target` | MISSING | `GtoPdb_search_targets` |
| `GtoPdb_get_targets` | MISSING | `GtoPdb_search_targets` |
| `GtoPdb_get_target_interactions` | MISSING | `GtoPdb_get_interactions` |
| `GtoPdb_list_ligands` | MISSING | `GtoPdb_search_ligands` |
| `clinvar_get_clinical_significance` | MISSING (wrong case) | `ClinVar_get_clinical_significance` |
