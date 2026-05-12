#!/usr/bin/env bash
# Post-deploy smoke test for SMCP on sempart-demo.
#
# Performs the MCP streamable-HTTP session handshake (initialize →
# notifications/initialized) and then verifies (1) tools/list returns
# ≥300 registered tools, (2) one representative tool round-trips
# against its external API. Exits non-zero on any failure.

set -euo pipefail

URL="${SMCP_URL:-http://127.0.0.1:8765/mcp}"
# Hard limits:
#   ≤128 = OpenAI tools[] cap (Squirro's MCP integration forwards
#          tools/list verbatim — exceeding triggers HTTP 400)
# Soft limits (Squirro agent latency):
#   ≤30  = keeps "tool suggestion" first-token latency under
#          Squirro's per-turn timeout. Tighten by trimming
#          --categories in the Dockerfile CMD.
# Lower bound just guards against an empty/broken load.
MIN_TOOLS="${SMCP_MIN_TOOLS:-10}"
MAX_TOOLS="${SMCP_MAX_TOOLS:-128}"

command -v jq >/dev/null || { echo "ERROR: jq required" >&2; exit 1; }
command -v curl >/dev/null || { echo "ERROR: curl required" >&2; exit 1; }

ACCEPT='application/json, text/event-stream'
HDR_TYPE='Content-Type: application/json'

# ---------------------------------------------------------------------
# Helper: extract the `data: …` payload from an SSE response body.
# fastmcp wraps single responses in one `event: message / data: {...}`
# frame, so the first data line is the JSON-RPC envelope.
# ---------------------------------------------------------------------
sse_payload() {
  sed -n 's/^data: //p' | head -n1
}

# ---------------------------------------------------------------------
# Step 1: initialize — captures the session ID returned in headers.
# ---------------------------------------------------------------------
echo "[1/3] initialize against $URL …"
INIT_HDR_FILE=$(mktemp)
trap 'rm -f "$INIT_HDR_FILE"' EXIT

curl -fsS -D "$INIT_HDR_FILE" -X POST "$URL" \
     -H "$HDR_TYPE" -H "Accept: $ACCEPT" \
     -d '{"jsonrpc":"2.0","id":0,"method":"initialize",
          "params":{"protocolVersion":"2024-11-05",
                    "capabilities":{},
                    "clientInfo":{"name":"smoke.sh","version":"1"}}}' \
     >/dev/null

SESSION=$(grep -i '^mcp-session-id:' "$INIT_HDR_FILE" \
            | head -1 | awk '{print $2}' | tr -d '\r\n')
if [[ -z "$SESSION" ]]; then
  echo "ERROR: no mcp-session-id returned by initialize." >&2
  cat "$INIT_HDR_FILE" >&2
  exit 1
fi
echo "      → session $SESSION"

HDR_SESSION="mcp-session-id: $SESSION"

# Send the initialized notification (no response expected).
curl -fsS -X POST "$URL" \
     -H "$HDR_TYPE" -H "Accept: $ACCEPT" -H "$HDR_SESSION" \
     -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
     >/dev/null || true

# ---------------------------------------------------------------------
# Step 2: tools/list — verify ≥ MIN_TOOLS registered.
# ---------------------------------------------------------------------
echo "[2/3] tools/list …"
LIST_RESP=$(curl -fsS -X POST "$URL" \
              -H "$HDR_TYPE" -H "Accept: $ACCEPT" -H "$HDR_SESSION" \
              -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}')

LIST_JSON=$(echo "$LIST_RESP" | sse_payload)
N=$(echo "$LIST_JSON" | jq -r '.result.tools | length // 0')

echo "      → $N tools registered (require $MIN_TOOLS ≤ N ≤ $MAX_TOOLS)"
if (( N < MIN_TOOLS )); then
  echo "ERROR: too few tools registered." >&2
  echo "$LIST_JSON" | head -c 500 >&2
  exit 1
fi
if (( N > MAX_TOOLS )); then
  echo "ERROR: $N tools registered — exceeds OpenAI's 128-tool limit." >&2
  echo "Squirro's native MCP integration will fail with 'array too long'." >&2
  exit 1
fi

# ---------------------------------------------------------------------
# Step 3: tools/call OpenTargets_search_target — verifies external
# network egress + a real tool round-trip.
# ---------------------------------------------------------------------
echo "[3/3] tools/call OpenTargets_search_target BRAF …"
CALL_RESP=$(curl -fsS -X POST "$URL" \
              -H "$HDR_TYPE" -H "Accept: $ACCEPT" -H "$HDR_SESSION" \
              -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
                   "params":{"name":"OpenTargets_search_target",
                             "arguments":{"target":"BRAF"}}}')

CALL_JSON=$(echo "$CALL_RESP" | sse_payload)
if ! echo "$CALL_JSON" | jq -e '.result' >/dev/null; then
  echo "ERROR: OpenTargets_search_target call failed." >&2
  echo "$CALL_JSON" | head -c 500 >&2
  exit 1
fi

echo "OK — server responds, $N tools registered, OpenTargets reachable."
