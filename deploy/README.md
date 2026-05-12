# SMCP on sempart-demo

Hosts the local ToolUniverse fork (`libs/tooluniverse/`) as an MCP server
on sempart-demo, bound to host loopback `127.0.0.1:8765`. Squirro GenAI
plugins running on the same host (in `sqgenaid`) reach it at
`http://127.0.0.1:8765/mcp`.

> Host port is 8765 (not 8000) because sqgenaid itself binds uvicorn on
> 127.0.0.1:8000. The container internally still listens on 8000; only
> the host-side mapping uses 8765.

This replaces the `_vendor/tooluniverse/` bundling trick used by
`integration/genai/research_pipeline/`: instead of cramming TU into the
plugin sandbox (which crashes `sqgenaid` on optional deps like
`pandas` / `duckdb` / `playwright`), TU runs in its own container with
its own Python env.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | `python:3.12-slim` base, `pip install -e` from `libs/tooluniverse/` |
| `docker-compose.yml` | Service `smcp`, port `127.0.0.1:8765:8000`, named volume, TCP healthcheck, log rotation |
| `.env.template` | Tracked. Lists every env var the server reads. Copy to `.env` and fill. |
| `.env` | **gitignored**. Hand-maintained on sempart. Holds API keys. |
| `deploy.sh` | Pre-flight checks + `docker compose up -d --build` |
| `smoke.sh` | `tools/list` count + one `OpenTargets_search_target` end-to-end call |

## First-time setup on sempart-demo

```bash
# As root (or whoever owns docker on sempart):
cd /opt
git clone <repo-url> swiss-rockets-delivery       # if not already there
cd swiss-rockets-delivery/libs/tooluniverse/deploy

cp .env.template .env
$EDITOR .env                                       # fill in API keys

./deploy.sh
./smoke.sh
```

Expected on first build:
- 4–8 minutes for the initial `docker compose up --build` (pandas, numpy,
  faiss-cpu, lxml, playwright etc. — heavy wheels).
- Up to ~2 minutes after container start for full TU load + initial
  FAISS index build (`--search-enabled`). The `start_period: 90s` in the
  healthcheck accommodates this; bump it if cold-start gets slower in
  practice.

The FAISS index, NCBI cache, HPA bulk TSVs, and any downloaded reference
data live in the named volume `smcp_workspace`. Subsequent restarts skip
the rebuild.

## Routine deploy (after a code change)

```bash
ssh sempart-demo
cd /opt/swiss-rockets-delivery
git pull origin <branch>
cd libs/tooluniverse/deploy
./deploy.sh && ./smoke.sh
```

## Connecting from a Squirro plugin (future PR)

Plugins call the server via the MCP streamable-HTTP transport:

```python
# example sketch — actual wiring will land in a follow-up PR
from fastmcp import Client
async with Client("http://127.0.0.1:8765/mcp") as mcp:
    result = await mcp.call_tool("OpenTargets_search_target",
                                  {"target": "BRAF"})
```

Until that PR lands, the existing `_vendor/`-bundling pattern documented
in `integration/genai/research_pipeline/deploy.sh` remains the live
architecture for plugins that need TU.

## Troubleshooting

| Symptom | Look at |
|---|---|
| `docker compose ps` shows `unhealthy` | `docker compose logs -f smcp` — usually slow tool import or an exception during `--search-enabled` build |
| `smoke.sh` step 1 returns < 300 tools | A TU category failed to import. `docker compose logs smcp 2>&1 \| grep -i 'failed\|error'` |
| `smoke.sh` step 2 returns no result | Either OpenTargets API is unreachable from sempart (egress firewall) or the tool name has drifted (`OpenTargets_search_target` is current as of writing) |
| Disk filling up | The `smcp_workspace` volume has no eviction policy. `docker volume inspect smcp_workspace` to see size; `docker volume rm smcp_workspace` to wipe (forces a rebuild of caches/index on next start) |
| Need to wipe and rebuild from scratch | `docker compose down -v && ./deploy.sh` |

## Out of scope

- TLS / external exposure — server is loopback-only.
- Auth — anyone with shell on sempart can call it. `.env` is the most
  sensitive file in this directory.
- Multi-host (sr-dev, sr-dev-com) — sempart only for now. Generalize
  `deploy.sh` with an `SMCP_TARGET` env var when a second host is in
  scope.
- CI/CD image push — image is built on sempart from the checked-out
  source.
- Plugin migrations — separate PRs per plugin.
