#!/usr/bin/env bash
# Post-deploy smoke test for SMCP on sempart-demo.
#
# Performs the MCP streamable-HTTP session handshake (initialize →
# notifications/initialized) and then verifies (1) tools/list returns
# the compact-mode meta-tool surface (~5 tools), (2) execute_tool can
# dispatch to a non-statically-loaded tool (proves background-loaded
# breadth is reachable). Exits non-zero on any failure.

set -euo pipefail

URL="${SMCP_URL:-http://127.0.0.1:8765/mcp}"
# Compact mode advertises ~5 meta-tools: find_tools, list_tools,
# grep_tools, get_tool_info, execute_tool. Bounds give some slack
# (e.g. a sixth tool registered by an extension) but will catch a
# reverted --compact-mode flag (which would push count to 23+ or 2278).
MIN_TOOLS="${SMCP_MIN_TOOLS:-4}"
MAX_TOOLS="${SMCP_MAX_TOOLS:-20}"

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
  echo "ERROR: too few tools registered — compact mode should expose ~5 meta-tools." >&2
  echo "$LIST_JSON" | head -c 500 >&2
  exit 1
fi
if (( N > MAX_TOOLS )); then
  echo "ERROR: $N tools registered — compact mode appears disabled." >&2
  echo "Check that --compact-mode is in the Dockerfile CMD." >&2
  exit 1
fi

# Confirm execute_tool is one of them (the load-bearing primitive).
if ! echo "$LIST_JSON" | jq -e '.result.tools[] | select(.name=="execute_tool")' >/dev/null; then
  echo "ERROR: execute_tool not in tools/list — compact mode misconfigured." >&2
  exit 1
fi

# Confirm get_skill is ADVERTISED (ADR-0005 / DSR-505 serving spike). The router
# can only invoke it if it appears in tools/list — "advertised" is the thing that
# silently breaks. Absence ⇒ --skills-dir missing from the Dockerfile CMD.
if ! echo "$LIST_JSON" | jq -e '.result.tools[] | select(.name=="get_skill")' >/dev/null; then
  echo "ERROR: get_skill not in tools/list — check --skills-dir in the Dockerfile CMD." >&2
  exit 1
fi

# ---------------------------------------------------------------------
# Step 2b: tools/call get_skill → disease-research. Proves the body is
# SERVED at the MCP layer (distinct from the LLM OBEYING it). Catches a
# missing/empty served-skills dir before any live agent run.
# ---------------------------------------------------------------------
echo "[2b] tools/call get_skill → disease-research …"
SKILL_RESP=$(curl -fsS -X POST "$URL" \
              -H "$HDR_TYPE" -H "Accept: $ACCEPT" -H "$HDR_SESSION" \
              -d '{"jsonrpc":"2.0","id":3,"method":"tools/call",
                   "params":{"name":"get_skill",
                             "arguments":{"name":"disease-research"}}}')
SKILL_JSON=$(echo "$SKILL_RESP" | sse_payload)
SKILL_TEXT=$(echo "$SKILL_JSON" | jq -r '.result.content[0].text // ""')
case "$SKILL_TEXT" in
  ERROR:*) echo "ERROR: get_skill returned: $SKILL_TEXT" >&2; exit 1 ;;
esac
# The served body is the converted disease-research SOP — assert a stable marker.
if ! echo "$SKILL_TEXT" | grep -q "OUTPUT CONTRACT"; then
  echo "ERROR: get_skill body missing expected SOP marker (OUTPUT CONTRACT)." >&2
  echo "$SKILL_TEXT" | head -c 300 >&2
  exit 1
fi
echo "      → served disease-research body (${#SKILL_TEXT} chars)"

# ---------------------------------------------------------------------
# Step 3: execute_tool → search_clinical_trials. Proves the agent flow:
#   tools/call(execute_tool) → TU dispatches to a background-loaded tool
#   → external API round-trip works. If this passes, the LLM can reach
#   any of TU's ~2,278 tools through the meta-tool surface.
# ---------------------------------------------------------------------
echo "[3/3] tools/call execute_tool → search_clinical_trials focal-onset-epilepsy …"
CALL_RESP=$(curl -fsS -X POST "$URL" \
              -H "$HDR_TYPE" -H "Accept: $ACCEPT" -H "$HDR_SESSION" \
              -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
                   "params":{"name":"execute_tool",
                             "arguments":{"tool_name":"search_clinical_trials",
                                          "arguments":{"query_term":"focal onset epilepsy","limit":3}}}}')

CALL_JSON=$(echo "$CALL_RESP" | sse_payload)
if ! echo "$CALL_JSON" | jq -e '.result and (.result.isError | not)' >/dev/null; then
  echo "ERROR: execute_tool dispatch failed." >&2
  echo "$CALL_JSON" | head -c 500 >&2
  exit 1
fi

echo "OK — server responds, $N meta-tools registered, execute_tool reaches CT.gov."
