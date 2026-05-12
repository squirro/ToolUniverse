#!/usr/bin/env bash
# Post-deploy smoke test for SMCP on sempart-demo.
#
# Verifies (1) the MCP protocol responds and ≥300 tools are registered,
# (2) one representative tool round-trips against its external API.
# Exit non-zero on any failure.

set -euo pipefail

URL="${SMCP_URL:-http://127.0.0.1:8000/mcp}"
MIN_TOOLS="${SMCP_MIN_TOOLS:-300}"

command -v jq >/dev/null || { echo "ERROR: jq required" >&2; exit 1; }
command -v curl >/dev/null || { echo "ERROR: curl required" >&2; exit 1; }

echo "[1/2] tools/list against $URL …"
N=$(curl -fsS -X POST "$URL" \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
    | jq -r '.result.tools | length // 0')

echo "      → $N tools registered (require ≥ $MIN_TOOLS)"
if (( N < MIN_TOOLS )); then
  echo "ERROR: too few tools registered." >&2
  exit 1
fi

echo "[2/2] tools/call OpenTargets_search_target BRAF …"
RESULT=$(curl -fsS -X POST "$URL" \
           -H 'Content-Type: application/json' \
           -H 'Accept: application/json, text/event-stream' \
           -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
                "params":{"name":"OpenTargets_search_target",
                          "arguments":{"target":"BRAF"}}}')

if ! echo "$RESULT" | jq -e '.result' >/dev/null; then
  echo "ERROR: OpenTargets_search_target call failed." >&2
  echo "$RESULT" | head -c 500 >&2
  exit 1
fi

echo "OK — server responds, tools registered, OpenTargets reachable."
