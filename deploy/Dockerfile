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

# Compact mode: TU loads all ~2,278 tools in the background but only exposes
# 5 in tools/list — list_tools, grep_tools, get_tool_info, execute_tool,
# find_tools. The LLM discovers via find_tools/grep_tools/list_tools and
# invokes via execute_tool(tool_name, arguments). This keeps OpenAI's
# tools[] (capped at 128) tiny without losing any TU breadth.
#
# Tool_RAG stays excluded — its embedding-based finder needs a 1.5 B Qwen2
# model that OOMs sempart. find_tools (LLM-backed) is the discovery path.
#
# DisGeNET_* excluded — no DISGENET_API_KEY provisioned, so these tools
# would only error at call time. Excluding them by name keeps them out of
# the registry entirely (unreachable via execute_tool, invisible to
# find_tools). Use OpenTargets for gene-disease associations instead.
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
     "--exclude-tools", "Tool_RAG", \
     "DisGeNET_search_gene", "DisGeNET_search_disease", "DisGeNET_get_gda", \
     "DisGeNET_get_vda", "DisGeNET_get_disease_genes"]
