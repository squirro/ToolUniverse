# Amazon Linux 2023 base instead of python:3.12-slim (Debian). Rationale:
# python:3.12-slim ships perl-base + ncurses CVEs that Debian has NOT patched
# (CVE-2026-42496/CVE-2026-8376 CRITICAL, CVE-2025-69720 HIGH, all marked
# "affected"/"fix_deferred" with no Fixed Version — unpatchable in place).
# AL2023 is rebuilt ~daily and actively patched: a clean trivy scan of the
# bare base (0 CRITICAL/HIGH). TU only needs Python >=3.10 (pyproject
# requires-python), and AL2023 ships a patched python3.11 (3.11.15) — which
# ALSO matches the cluster's documented Python 3.11 runtime (image/cluster
# parity). See ADR-0011.
FROM public.ecr.aws/amazonlinux/amazonlinux:2023

# Predictable UTF-8 locale (AL2023 defaults to C; some TU tools assume UTF-8).
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Python 3.11 + the runtime libs TU's binary wheels need at runtime
# (epam.indigo → libXrender/libXext/libSM/libX11/expat;
#  faiss-cpu / numpy / scipy → libgomp;
#  build-time → gcc/gcc-c++ + python3.11-devel for any sdist that compiles).
# dnf package names differ from Debian: gcc-c++ (not g++), capitalised libX*,
# expat (not libexpat1), libgomp (not libgomp1). install_weak_deps=False keeps
# the dependency closure (and thus the CVE surface) minimal.
RUN dnf install -y --setopt=install_weak_deps=False \
      python3.11 python3.11-pip python3.11-devel \
      gcc gcc-c++ \
      libXrender libXext libSM libX11 expat \
      libgomp \
    && dnf clean all && rm -rf /var/cache/dnf

WORKDIR /app/tu_src

# Copy only what pip install needs from the local TU fork. The build
# context is libs/tooluniverse/ (see docker-compose.yml `build.context`).
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Editable install so the package metadata + entry points are present
# under /app/tu_src; the source tree is what runs at import time.
# Base TU only — NOT [embedding]. We exclude Tool_RAG (the embedding-
# based tool finder) from the advertised surface because:
#   1. It needs sentence-transformers + torch + ~3 GB Qwen2-1.5B model
#   2. CPU embedding on sempart pushes memory near OOM (sempart has
#      ~4 GB headroom after sqgenaid + ES + temporal + alloy)
#   3. find_tools (via Tool_Finder_LLM) uses OpenAI for tool ranking,
#      no local model needed
# To re-enable Tool_RAG later: change to `.[embedding]` here AND remove
# Tool_RAG from --exclude-tools below.
# Explicit python3.11 (AL2023's default python3 is 3.9). pip stamps the
# tooluniverse-smcp console-script shebang with this interpreter.
RUN python3.11 -m pip install --no-cache-dir -e .

# Optional dependencies that unblock tools the deployment actually wants.
#   zeep      -> BRENDA_* (5 tools; SOAP client. Also needs BRENDA_EMAIL/PASSWORD)
#   py3Dmol   -> visualize_molecule_3d, visualize_protein_structure_3d
#   rdkit     -> DrugProps_* (3), RDKit_* (2), Chem_sa_score,
#                visualize_molecule_2d/_3d          [8 tools]
#   biopython -> BLAST_* (2), Structure_annotate_per_residue
#   freesasa  -> Structure_annotate_per_residue's relative-SASA calculation
#
# rdkit + biopython cost ~170 MB and were previously declined on that basis.
# They are now wanted: cheminformatics is core to the SR use case, and the
# ~170 MB is disk, not the resident memory the OOM constraint is about.
#
# ORDERING MATTERS. freesasa publishes no wheel for this platform (pip
# --only-binary reports "from versions: none"), so it compiles from C source and
# must be installed while gcc is still present -- i.e. HERE, before the dnf
# remove below. Moving this line after that removal fails with
# "command 'gcc' failed: No such file or directory".
#
# Still deliberately NOT installed, and now excluded outright rather than left
# to fail: the ADMETAI (9) and ESM (9) stacks and Tool_Finder need local model
# inference. There is no ML-capable instance to run them on, so the packages
# would add weight for tools that could never answer -- the same reason
# Tool_RAG is excluded above.
RUN python3.11 -m pip install --no-cache-dir zeep py3Dmol rdkit biopython freesasa

# Trim build-only toolchain; runtime libs stay. Shrinks the trivy-visible
# package set (gcc / -devel carry their own advisories) now that wheels are in.
RUN dnf remove -y gcc gcc-c++ python3.11-devel \
    && dnf clean all && rm -rf /var/cache/dnf

ENV TOOLUNIVERSE_LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Serve EVERY converted skill SOP body via the get_skill tool (ADR-0005 /
# DSR-505/510). Glob-copy persona-<name>.md → /app/served-skills/<name>.md so a
# newly gated body is served by ADDING THE FILE — not by editing this Dockerfile.
# This closes the DSR-510 "only ~13 served" gap: the served set is now every
# converted research body in deploy/, single source of truth (the served body
# cannot drift from the persona-direct baseline it is benchmarked against).
# EXCLUDED (not get_skill-served): router / router-spike (the dispatcher persona,
# applied to the AGENT), doriano / smcp-only (non-skill personas). Placed after
# pip install so editing a body does not bust the install layer cache.
COPY deploy/persona-*.md /tmp/served/
RUN mkdir -p /app/served-skills \
 && for f in /tmp/served/persona-*.md; do \
      name="$(basename "$f" .md)"; name="${name#persona-}"; \
      case "$name" in router|router-spike|doriano|smcp-only) continue ;; esac; \
      cp "$f" "/app/served-skills/$name.md"; \
    done \
 && rm -rf /tmp/served \
 && echo "[served-skills] $(ls -1 /app/served-skills | wc -l) bodies:" \
 && ls -1 /app/served-skills | sed 's/\.md$//' | sort

# Non-root hardening. Placed AFTER every root-owned build step (pip install,
# served-skills COPY/RUN write to /app). Nothing in the CMD needs privilege:
# port 8000 is unprivileged (no CAP_NET_BIND_SERVICE) and the only runtime
# writes go to TU_DATA_DIR / $HOME/.tooluniverse. AL2023's minimal base ships
# no shadow-utils (no useradd), so create the account by appending to
# /etc/passwd directly — zero added packages, keeping the CVE surface minimal
# (the point of the AL2023 rebase, ADR-0011). Relocate the TU workspace out of
# /root (mode 0700, root-only) into the app HOME so the non-root process — and
# a K8s PVC mounted there with fsGroup 10001 — can write it. /app/served-skills
# is cp'd mode 644 (world-readable), so uid 10001 reads it fine — no chown.
# Numeric uid 10001 satisfies the restricted PodSecurity Standard (runAsNonRoot
# / mustRunAsNonRoot reject a USER that doesn't resolve to a non-zero uid).
RUN printf 'app:x:10001:10001::/home/app:/sbin/nologin\n' >> /etc/passwd \
 && printf 'app:x:10001:\n' >> /etc/group \
 && mkdir -p /home/app/.tooluniverse \
 && chown -R 10001:10001 /home/app
ENV HOME=/home/app \
    TU_DATA_DIR=/home/app/.tooluniverse/cache
USER 10001

# Compact mode: TU loads all ~2,278 tools in the background but only exposes
# 5 in tools/list — list_tools, grep_tools, get_tool_info, execute_tool,
# find_tools. The LLM discovers via find_tools/grep_tools/list_tools and
# invokes via execute_tool(tool_name, arguments). This keeps OpenAI's
# tools[] (capped at 128) tiny without losing any TU breadth.
#
# Tool_RAG stays excluded — its embedding-based finder needs a 1.5 B Qwen2
# model that OOMs sempart. find_tools (LLM-backed) is the discovery path.
#
# Key-gated tools excluded — their API keys are not provisioned in .env, so
# they would only error at call time. Excluding them by name keeps them out
# of the registry entirely (unreachable via execute_tool, invisible to
# find_tools). The .env key that gates each family:
#   DISGENET_API_KEY  -> DisGeNET_*   (use OpenTargets for gene-disease instead)
#   OMIM_API_KEY      -> OMIM_*
#   ONCOKB_API_TOKEN  -> OncoKB_*
#   CLUE_API_KEY      -> CLUE_*
#   MCULE_API_KEY     -> Mcule_*
#   USPTO_API_KEY     -> get_patent_* / get_associated_documents_metadata
#   ADDGENE_API_KEY   -> Addgene_*
# Semantic Scholar is deliberately NOT excluded: its key is optional (raises
# the rate limit only), so SemanticScholar_* work key-less.
#
# The five UMLS-gated tools (umls_*, snomed_*, loinc_*, icd_search_codes) were
# excluded here and have been RE-ADMITTED. The key was never unavailable: the
# env file holds a valid 36-character key followed by an inline comment, and
# `--env-file` keeps the comment (a shell would have dropped it), so what
# reached the service was key-plus-prose. Comments now sit on their own line in
# .env/.env.template, and all five return real payloads.
#
# Second wave (2026-08-02), same rule applied to the families the audit found
# still reaching the registry with no credential behind them. Squirro confirmed
# which keys are provisioned; these are not among them:
#   IUCN_API_KEY      -> IUCN_*        (conservation status; no biomedical use)
#   PHARMVAR_API_KEY  -> PharmVar_*
#   OPENGWAS_TOKEN    -> OpenGWAS_*
#   LDLINK_TOKEN      -> LDlink_*
#   (no key defined)  -> SynBioHub_* / MetaCyc_* / USCensus_*
# CELLxGENE_* is excluded for a different reason wearing the same clothes: its
# "API key" is a synthetic gate you set to '1' after `pip install
# cellxgene-census`. It is a missing package, not a missing credential, and the
# package is a heavy one.
#
# DrugBank (all 19) is excluded on LICENSING, not on behaviour: the dataset is
# not licensed for commercial use, and Swiss Rockets is a commercial user. This
# supersedes the narrower DSR-635 exclusion, which covered only the 15 XMLTools
# (each parses its own ~11 GB copy of drugbank_full_database.xml and OOMs the
# server) and lived in the audit harness -- a workaround in the harness cannot
# keep a licence, because the harness is not what ships. The four DatasetTools
# were never in that list and three of them return data, so this removes
# working tools by intent: expect the count to fall by three.
# The same rule already applies upstream of us in OptimusKG, whose atlas is
# licence-filtered (its DrugBank-derived DDI edges went from 1.35M to 1.6K).
#
# Third wave: a credential that is CONFIGURED but REJECTED buys nothing over one
# that is absent -- the tool can still only error, so the same rule applies.
#   BioGRID_*  SETTLED 2026-08-03: excluded permanently. Two different keys are
#              refused 401 "Your Access Key is Not Valid" across every request
#              form (accessKey/accesskey, trailing slash, http, several
#              endpoints), and this is NOT the env-file comment bug — BioGRID
#              was never among the affected variables. The client has confirmed
#              no webservice key will be available. Do not re-investigate.
#   ICD11_*    ICD_CLIENT_SECRET is set; the WHO OAuth token endpoint answers
#              400 invalid_client, so the paired ICD_CLIENT_ID looks stale.
#              Re-admit once the pair authenticates.
# Both are one line to undo: delete the names below and rebuild.
#
# Fourth wave: all 50 AgenticTools. Each is a `prompt` with {placeholder} slots
# and nothing else -- no data access, and not one of the 50 can call another
# tool. TU fills the template and sends it to a SECOND LLM, so they are gated on
# an LLM API key this deployment does not set, and every call has been answering
# "not found even after loading tools". They are blocked rather than revived:
# 18 of them only exist to author TU tools, and the rest would answer biomedical
# questions generatively with no grounding, which is the failure mode the
# persona exists to prevent. Recording them here also stops 50 definitions the
# server never loads from counting as probe failures -- they were 50 of the 64
# `error_probe_arg` in the 2026-08-02 baseline.
#
# Fifth wave: seven tools no argument can rescue.
#   python_script_runner / phykit_batch_analysis / run_deseq2_analysis
#     need a file on this container's filesystem, and nothing can put one there.
#     python_code_executor already runs code from an inline string and works.
#   FlyBase_get_gene_expression / ZFIN_get_gene_expression
#     read an Alliance endpoint that was withdrawn: /alleles and /phenotypes
#     still answer 200 for the same gene, every expression path 404s. Use
#     Bgee_* or ExpressionAtlas_* for cross-species expression instead.
#   Finish            agent-loop control; its SpecialTool type is not registered.
#   ToolDescriptionOptimizer
#     authors TU tools and needs the same LLM key the AgenticTools needed.
#   ToolDiscover
#     same reason, one step removed: its generation stage calls
#     UnifiedToolGenerator (tool_discover.py:444), an AgenticTool already
#     excluded above, and verified unreachable on the served image. Its
#     "string indices must be integers" crash is the composition script
#     subscripting that error string as a dict, so fixing the crash only moves
#     the failure one line later. Excluding it turns a misleading `error` row
#     into an honest `excluded` one.
#
# Sixth wave: 29 tools whose upstream gives nothing usable, each having failed
# IDENTICALLY in two sweeps a day apart. One reading is not evidence -- on
# 2026-08-02 USGSWater, RNAcentral, UniChem and SwissTargetPrediction looked
# just as dead and all four recovered by 2026-08-03.
#   Pharos_*      502 for two days.   TargetMine_*  503.
#   POWO_* T3DB_* CellMarker_*        403, bot-blocked.
#   ZINC_*        HTTP 200 with an HTML challenge page on every route, which is
#                 why the wrapper reports "Invalid JSON" and not a status code.
#   CTD_*         the RENCI Automat mirror has no registered backends at all,
#                 and ctdbase.org redirects a batch query to an interactive page.
#   NvidiaNIM_    alphafold2, alphafold2_multimer, boltz2, maisi — 504. NAMED
#                 INDIVIDUALLY: the other 12 NvidiaNIM tools return data
#                 (esmfold, openfold2/3, rfdiffusion, proteinmpnn, diffdock …)
#                 and a family-wide block would have removed them.
#   HPA_get_protein_interactions_by_gene — upstream withdrew the `ppi` column.
#
# NOT excluded, and no longer suspected: the Bgee_*/LOVD_*/Rfam_*/
# MetabolomicsWorkbench_* group turned out to be wrapper bugs, all now fixed
# and measured as ok_data. Each answered a direct request and failed only
# through us, and in each case the error text named something other than the
# cause: Bgee wanted a trailing slash (403 from a Cloudflare interstitial, next
# to a docstring correctly saying no auth was needed), LOVD wanted a
# lovd_cookie_check cookie (an HTML bot-check page served as 200, surfacing as
# a JSON parse error), and Rfam's /structures route wants the format as a query
# parameter rather than an Accept header (500 on a live route returning 149 KB).
# MetabolomicsWorkbench needed nothing: its failure was a transport error.
# BindingDB was the first of this group, sending `pdbs=…;…` where the API wants
# `pdb=…,…` — the service answers 500 to the wrong parameter name, which is
# indistinguishable from being down.
#
# The 10 *_disease_target_score tools (DiseaseTargetScoreTool) are NOT
# excluded: they were briefly excluded because an invalid efoId crashed them
# with KeyError: 'disease', now fixed in graphql_tool.py (they return a clean
# "resolve the name to an id first" error). The persona still steers
# "most associated" queries to OpenTargets_get_associated_targets_by_disease_efoId.
#
# Seventh wave: 21 tools that need compute or credentials this deployment will
# not have, plus 8 whose upstream does not answer. Previously they sat as
# `needs_package` and `error`, which reads as "someone should get to this" --
# they are decisions, so they are recorded as decisions.
#
#   ADMETAI_* (9), ESM_* (9), Tool_Finder
#     local model inference. There is NO ML-capable instance in the estate, so
#     these are out of scope rather than pending an install: admet-ai, the esm
#     protein language model, and Tool_Finder's torch embedding stack would all
#     load models the host cannot hold. Tool_Finder specifically duplicates
#     find_tools, which reaches the same breadth via Tool_Finder_LLM over
#     OpenAI and needs no local model. Same reason as Tool_RAG.
#   advanced_literature_search_agent, open_deep_research_agent
#     need `smolagents` AND an Azure OpenAI credential. Even installed they
#     would answer biomedical questions generatively through a second LLM,
#     which is what the 50 AgenticTools are excluded for.
#
# Eighth wave: 8 tools whose upstream gives nothing usable, each verified by an
# independent request at 2026-08-03, not inferred from a sweep:
#   PathwayCommons_get_neighborhood / _get_pathway   no response within 100s.
#   SGD_get_interactions                             no response within 100s.
#   NvidiaNIM_openfold3   HTTP 500 "Internal server error". NAMED INDIVIDUALLY:
#                         12 other NvidiaNIM tools return data.
#   SwissDock_dock_ligand submits, then the docking job fails server-side.
#   SwissTargetPrediction_predict  200 with no job URL to poll.
#   UniChem_search_compound        timeout. THE WEAKEST OF THESE: it answered in
#                         an earlier sweep, so re-probe before believing it is
#                         gone -- excluded because it has now failed twice.
#   get_webpage_text_from_url      needs Playwright browsers (~400 MB of
#                         Chromium) that the image does not install; the web
#                         search tools cover this ground. DSR-640.
#
# Ninth wave: 3 tools that answer an empty list instead of failing, each for a
# reason no argument can fix. They were the last unexplained `ok_empty` rows.
#   Tool_Finder_LLM
#     needs an LLM key this deployment does not set. It logs the failure and
#     RETURNS [], so an agent calling it via execute_tool gets a confident
#     nothing. Excluding it does NOT weaken discovery: find_tools was already
#     answering from its keyword path, and returns the identical results with
#     this excluded (measured, not assumed -- `search_method=llm` returns 0
#     tools while auto/keyword/embedding return the same 3). Note that a
#     `find_tools` docstring elsewhere still credits the LLM finder; the honest
#     description is keyword matching. If an LLM key is ever provisioned
#     (DSR-639), remove this entry to get the ranked search back.
#   ESM_describe_sae_feature
#     runs SAE inference over a protein panel, and that inference is
#     ESM_get_sae_features -- excluded above with the rest of the ESM stack. Each
#     panel protein fails and is skipped by a bare `continue`, so every feature
#     id reports 0 activations across 10 proteins. Verified on four different
#     ids; sparse features would not all be empty. Same shape as ToolDiscover:
#     a composed tool whose dependency cannot run here.
#   BGPT_search_paper_evidence
#     bgpt.pro is FREEMIUM. The response carries `free_results_remaining`, and
#     once it hits zero the endpoint answers **HTTP 402 Payment Required**. It
#     will work for a couple of calls and then never again, which is worse than
#     not shipping it. Needs a paid subscription, not a fix.
#   ten of the eleven ComposeTools -- DrugSafetyAnalyzer is kept
#     A ComposeTool auto-loads a missing dependency, and before ea01ffad that
#     load emptied the shared registry -- every tool gone, for every client, until
#     the container restarted. That specific bug is fixed, and a sweep of the
#     fixed build calls BiomarkerDiscoveryWorkflow without harm. They are excluded
#     anyway, as a product decision: SR does not use them, and the registry is
#     process-wide shared state that one call should not be able to empty. The
#     hazard lives in load_tools, not in ComposeTool -- three callers in
#     output_hook.py still take the clearing branch, dormant only because
#     hooks_enabled defaults to False and this CMD never turns hooks on. Removing
#     the reachable callers shrinks what can reach it while that stays true.
#     ToolDescriptionOptimizer and ToolDiscover were already excluded above, for
#     their own reasons.
#
#     What is excluded here is chosen on measured output, not on the type. A
#     sweep of the fixed build probed all eleven. DrugSafetyAnalyzer returned a
#     complete ranked adverse-event table from openFDA with no embedded failure,
#     so it stays served. The other ten answer with nothing:
#       LiteratureSearchTool, MultiAgentLiteratureSearch and
#       BiomarkerDiscoveryWorkflow report "Invalid function call: Function name
#         <X> not found in loaded tools" -- they need agentic helpers that want an
#         LLM key this deployment does not set, the same cause as Tool_Finder_LLM
#         (DSR-639). A key would not fix the three below.
#       ComprehensiveDrugDiscoveryPipeline returns only
#         "string indices must be integers, not 'str'".
#       ToolMetadataGenerationPipeline returns one record whose every field is an
#         empty string; ToolGraphGenerationPipeline a graph of one node named
#         "ExampleTool"; ToolGraphComposer 2,050 nodes and ZERO edges. All three
#         report success, so only reading the payload catches them.
#       OutputSummarizationComposer is an internal hook helper, and its "summary"
#         was 134 characters from a 134-character input over 0 chunks.
#
# --max-workers 15: SMCP's default is 5 (smcp.py:402), so a skill that fires a
# dozen tool calls queues them five at a time — pure added latency on exactly the
# turns that already look slow (DSR-627 saw 13 calls precede a user-visible
# timeout). It must sit BEFORE --exclude-tools, which takes nargs='+' and would
# otherwise swallow it as a tool name.
#
# --exclude-tools takes nargs='+', and being the last flag it consumes
# every trailing name.
# Entered via tools_sr.smcp_entry rather than the tooluniverse-smcp console script, so
# transport-status interception (DSR-666) is installed before the server accepts a call.
# It delegates straight to run_smcp_server, which parses sys.argv itself -- every flag
# below still reaches the same place. Editing smcp_server.py instead would put a permanent
# edit on a file that re-syncs from upstream.
CMD ["python3.11", "-m", "tooluniverse.tools_sr.smcp_entry", \
     "--transport", "http", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--compact-mode", \
     "--skills-dir", "/app/served-skills", \
     "--max-workers", "15", \
     "--exclude-tools", "Tool_RAG", \
     "DisGeNET_search_gene", "DisGeNET_search_disease", "DisGeNET_get_gda", \
     "DisGeNET_get_vda", "DisGeNET_get_disease_genes", \
     "OMIM_search", "OMIM_get_entry", "OMIM_get_gene_map", "OMIM_get_clinical_synopsis", \
     "OncoKB_annotate_mutations", "OncoKB_annotate_variant", "OncoKB_annotate_copy_number", \
     "OncoKB_get_cancer_genes", "OncoKB_get_gene_info", "OncoKB_get_levels", \
     "CLUE_search_compounds", "CLUE_search_signatures", "CLUE_get_cell_lines", \
     "CLUE_get_gene_expression", "CLUE_get_perturbation", \
     "Mcule_get_compound", "Mcule_lookup_compound", "Mcule_get_database", "Mcule_list_databases", \
     "get_patent_overview_by_text_query", "get_patent_application_metadata", \
     "get_associated_documents_metadata", "get_patent_continuity_data", \
     "get_patent_foreign_priority_data", "get_patent_term_adjustment_data", \
     "Addgene_search_plasmids", "Addgene_get_plasmid", "Addgene_search_depositors", \
     "CELLxGENE_download_h5ad", "CELLxGENE_get_cell_metadata", "CELLxGENE_get_census_versions", \
     "CELLxGENE_get_embeddings", "CELLxGENE_get_expression_data", \
     "CELLxGENE_get_gene_metadata", "CELLxGENE_get_presence_matrix", \
     "MetaCyc_get_compound", "MetaCyc_get_pathway", "MetaCyc_get_reaction", \
     "MetaCyc_search_pathways", \
     "SynBioHub_search_parts", "SynBioHub_get_collections", "SynBioHub_get_part", \
     "PharmVar_get_alleles", "PharmVar_list_genes", \
     "OpenGWAS_get_mr_instruments", "USCensus_get_population", \
     "IUCN_get_conservation_status", "LDlink_get_proxies", \
     "get_abstract_from_patent_app_number", \
     "get_claims_from_patent_app_number", \
     "get_full_text_from_patent_app_number", \
     "drugbank_filter_drugs_by_name", \
     "drugbank_get_drug_basic_info_by_drug_name_or_id", \
     "drugbank_get_drug_chemistry_by_drug_name_or_drugbank_id", \
     "drugbank_get_drug_desc_pharmacology_by_moa", \
     "drugbank_get_drug_interactions_by_drug_name_or_id", \
     "drugbank_get_drug_name_and_description_by_indication", \
     "drugbank_get_drug_name_and_description_by_pathway_name", \
     "drugbank_get_drug_name_and_description_by_target_name", \
     "drugbank_get_drug_products_by_name_or_drugbank_id", \
     "drugbank_get_drug_references_by_drug_name_or_id", \
     "drugbank_get_indications_by_drug_name_or_drugbank_id", \
     "drugbank_get_pathways_reactions_by_drug_or_id", \
     "drugbank_get_pharmacology_by_drug_name_or_drugbank_id", \
     "drugbank_get_safety_by_drug_name_or_drugbank_id", \
     "drugbank_get_targets_by_drug_name_or_drugbank_id", \
     "drugbank_full_search", "drugbank_links_search", \
     "drugbank_vocab_filter", "drugbank_vocab_search", \
     "BioGRID_get_interactions", "BioGRID_get_chemical_interactions", \
     "BioGRID_get_ptms", "BioGRID_search_by_pubmed", \
     "ICD11_search_diseases", "ICD11_get_entity", "ICD11_browse_hierarchy", \
     "ADMETAnalyzerAgent", "AdvancedCodeQualityAnalyzer", "AdverseEventICDMapper", \
     "AdverseEventPredictionQuestionGenerator", \
     "AdverseEventPredictionQuestionGeneratorWithContext", "ArgumentDescriptionOptimizer", \
     "ClinicalTrialDesignAgent", "CodeQualityAnalyzer", "CompoundDiscoveryAgent", \
     "DataAnalysisValidityReviewer", "DescriptionAnalyzer", "DescriptionQualityEvaluator", \
     "DiseaseAnalyzerAgent", "DomainExpertValidator", "DrugInteractionAnalyzerAgent", \
     "DrugOptimizationAgent", "EthicalComplianceReviewer", "ExperimentalDesignScorer", \
     "HypothesisGenerator", "IntentAnalyzerAgent", "KeywordExtractorAgent", \
     "LabelGenerator", "LiteratureContextReviewer", "LiteratureSynthesisAgent", \
     "MedicalLiteratureReviewer", "MedicalTermNormalizer", "MethodologyRigorReviewer", \
     "NoveltySignificanceReviewer", "OverallSummaryAgent", "PackageAnalyzer", \
     "ProtocolOptimizer", "QualityCheckerAgent", "QuestionRephraser", \
     "ReferenceInfoAnalyzer", "ReproducibilityTransparencyReviewer", "ResultSummarizerAgent", \
     "ResultsInterpretationReviewer", "ScientificTextSummarizer", "TestCaseGenerator", \
     "TestResultsAnalyzer", "ToolCompatibilityAnalyzer", "ToolMetadataGenerator", \
     "ToolMetadataStandardizer", "ToolOutputSummarizer", "ToolQualityEvaluator", \
     "ToolRelationshipDetector", "UnifiedToolGenerator", "WritingPresentationReviewer", \
     "XMLToolOptimizer", "call_agentic_human", \
     "python_script_runner", "phykit_batch_analysis", "run_deseq2_analysis", \
     "FlyBase_get_gene_expression", "ZFIN_get_gene_expression", \
     "Finish", "ToolDescriptionOptimizer", "ToolDiscover", \
     "Pharos_get_disease_targets", "Pharos_get_target", "Pharos_get_tdl_summary", \
     "Pharos_search_targets", \
     "CellMarker_list_cell_types", "CellMarker_search_by_cell_type", \
     "CellMarker_search_by_gene", "CellMarker_search_cancer_markers", \
     "ZINC_get_compound", "ZINC_get_purchasable", "ZINC_search_by_properties", \
     "ZINC_search_by_smiles", "ZINC_search_compounds", \
     "CTD_get_chemical_diseases", "CTD_get_chemical_gene_interactions", \
     "CTD_get_disease_chemicals", "CTD_get_gene_chemicals", "CTD_get_gene_diseases", \
     "TargetMine_search", "TargetMine_search_genes", \
     "POWO_get_taxon", "POWO_search_plants", "T3DB_get_toxin", "T3DB_search_toxins", \
     "NvidiaNIM_alphafold2", "NvidiaNIM_alphafold2_multimer", "NvidiaNIM_boltz2", \
     "NvidiaNIM_maisi", "HPA_get_protein_interactions_by_gene", \
     "ADMETAI_predict_BBB_penetrance", "ADMETAI_predict_CYP_interactions", \
     "ADMETAI_predict_bioavailability", "ADMETAI_predict_clearance_distribution", \
     "ADMETAI_predict_nuclear_receptor_activity", \
     "ADMETAI_predict_physicochemical_properties", \
     "ADMETAI_predict_solubility_lipophilicity_hydration", \
     "ADMETAI_predict_stress_response", "ADMETAI_predict_toxicity", \
     "ESM_explain_variant_mechanism", "ESM_fold_protein", \
     "ESM_generate_protein_sequence", "ESM_get_protein_embedding", \
     "ESM_get_region_sae_features", "ESM_get_sae_features", "ESM_score_sequence", \
     "ESM_score_variant_sae_batch", "ESM_score_variant_sae_disruption", \
     "Tool_Finder", "advanced_literature_search_agent", "open_deep_research_agent", \
     "PathwayCommons_get_neighborhood", "PathwayCommons_get_pathway", \
     "SGD_get_interactions", "NvidiaNIM_openfold3", "SwissDock_dock_ligand", \
     "SwissTargetPrediction_predict", "UniChem_search_compound", \
     "get_webpage_text_from_url", \
     "Tool_Finder_LLM", "ESM_describe_sae_feature", "BGPT_search_paper_evidence", \
     "BiomarkerDiscoveryWorkflow", "ComprehensiveDrugDiscoveryPipeline", \
     "LiteratureSearchTool", "MultiAgentLiteratureSearch", \
     "OutputSummarizationComposer", "ToolGraphComposer", \
     "ToolGraphGenerationPipeline", "ToolMetadataGenerationPipeline"]
