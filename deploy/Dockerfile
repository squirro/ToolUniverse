FROM python:3.12-slim

# Runtime libs that TU's binary wheels need at runtime
# (epam.indigo → libxrender/libxext/libsm/libx11/libexpat;
#  faiss-cpu / numpy / scipy → libgomp;
#  build-time → gcc/g++ for anything that needs to compile)
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ \
      libxrender1 libxext6 libsm6 libx11-6 libexpat1 \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

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
RUN pip install --no-cache-dir -e .

# Trim build-only toolchain; runtime libs stay.
RUN apt-get purge -y gcc g++ && apt-get autoremove -y

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
# The 10 *_disease_target_score tools (DiseaseTargetScoreTool) are NOT
# excluded: they were briefly excluded because an invalid efoId crashed them
# with KeyError: 'disease', now fixed in graphql_tool.py (they return a clean
# "resolve the name to an id first" error). The persona still steers
# "most associated" queries to OpenTargets_get_associated_targets_by_disease_efoId.
#
# --exclude-tools takes nargs='+', and being the last flag it consumes
# every trailing name.
CMD ["tooluniverse-smcp", \
     "--transport", "http", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--compact-mode", \
     "--skills-dir", "/app/served-skills", \
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
     "Addgene_search_plasmids", "Addgene_get_plasmid", "Addgene_search_depositors"]
