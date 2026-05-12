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
# compat alias) so we can pass --categories.
#
# === Two separate limits to think about ===
#
# 1. OpenAI's hard cap: tools[] in chat completions ≤ 128 entries.
#    Exceeding triggers 400 invalid_request_error. Full TU load
#    (2,278 tools) busts this immediately.
#
# 2. Squirro's per-turn agent timeout (soft, latency-driven): 115 tools
#    × ~750 bytes each = ~86 KB / ~21k tokens of tool schemas to read
#    BEFORE the LLM picks one. At that size, first-token latency on
#    gpt-4-class models is 5–15 s — long enough that Squirro reports
#    "tool suggestion takes too long". This was observed
#    2026-05-12 on a focal-onset-epilepsy trial query.
#
# So the practical advertised-tool ceiling is well below 128.
# Aim for ≤ 30 tools per persona/use case.
#
# === Current set: clinical-trial workflows (~23 tools) ===
#
#   clinical_trials  (16) ClinicalTrials.gov — primary
#   tool_finder       (4) find_tools / Tool_Finder_LLM / Keyword
#   special_tools     (3) essential utility tools
#
# === Categories temporarily dropped ===
#
#   opentarget, uniprot, hpa, alphamissense, alphafold —
#   re-enable as needed for target-discovery / variant / structure
#   workflows. Add them back one at a time and re-test the
#   "tool suggestion" latency end-to-end before settling.
#
# === Categories permanently excluded (SR standalone plugins cover) ===
#
#   fda_drug_label (156), fda_drug_adverse_event (15+6), ChEMBL (29) —
#   competition_landscape_tool, competitive_radar handle these.
CMD ["tooluniverse-smcp", \
     "--transport", "http", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--categories", \
       "clinical_trials", \
       "tool_finder", \
       "special_tools", \
     "--exclude-tools", "Tool_RAG"]
