#!/usr/bin/env bash
# Run on sempart-demo. Assumes /opt/swiss-rockets-delivery is checked out
# and up to date (run `git pull` yourself before invoking).
#
# Builds the SMCP container from the local TU fork and brings it up bound
# to host loopback 127.0.0.1:8000. Plugins running in sqgenaid on the
# same host reach it via http://127.0.0.1:8000/mcp.

set -euo pipefail
cd "$(dirname "$0")"

# Pre-flight: .env must exist (gitignored, hand-maintained on sempart).
if [[ ! -f .env ]]; then
  echo "ERROR: .env missing. Copy .env.template to .env and fill in keys." >&2
  exit 1
fi

# Pre-flight: docker compose v2 must be available.
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: 'docker compose' (v2) not found on PATH." >&2
  exit 1
fi

echo "[deploy] building and starting smcp …"
docker compose up -d --build

echo
docker compose ps

echo
echo "[deploy] tail logs with:  docker compose logs -f smcp"
echo "[deploy] smoke-test with: ./smoke.sh"
