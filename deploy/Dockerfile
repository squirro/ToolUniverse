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

# We use the richer `tooluniverse-smcp` entry (not the `tooluniverse-smcp-server`
# compat alias) so we can pass --categories.  The reason is Squirro's
# native MCP integration: it pulls the entire tools/list from SMCP and
# forwards every entry as an OpenAI tool.  OpenAI Chat Completions caps
# `tools[]` at 128 entries, so full TU load (2,278 tools) triggers a
# 400 invalid_request_error.  We curate to ~115.
#
# Categories included (~115 tools total):
#   opentarget       (55) target-disease associations
#   uniprot          (17) protein sequences/metadata
#   hpa              (14) Human Protein Atlas tissue expression
#   clinical_trials  (16) ClinicalTrials.gov
#   alphamissense     (3) variant pathogenicity
#   alphafold         (3) predicted structures
#   tool_finder       (4) find_tools / Tool_Finder_LLM / Tool_RAG / Keyword
#   special_tools     (3) essential utility tools
#
# Categories deliberately excluded:
#   fda_drug_label (156), fda_drug_adverse_event (15+6), ChEMBL (29) —
#   already covered by SR's standalone Squirro plugins
#   (competition_landscape_tool, competitive_radar). Re-add here only if
#   a single-tool view through SMCP is needed.
CMD ["tooluniverse-smcp", \
     "--transport", "http", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--categories", \
       "opentarget", \
       "uniprot", \
       "hpa", \
       "clinical_trials", \
       "alphamissense", \
       "alphafold", \
       "tool_finder", \
       "special_tools", \
     "--exclude-tools", "Tool_RAG"]
