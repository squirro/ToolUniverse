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
| `Dockerfile` | `python:3.12-slim` base, `pip install -e` from `libs/tooluniverse/`. Runs `tooluniverse-smcp --transport http --categories <list>` — curated to ≤128 tools (see "Tool surface" below). |
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
- 2–4 minutes for the initial `docker compose up --build` (pandas, numpy,
  faiss-cpu, lxml, playwright … — heavy wheels).
- Up to ~30 s after container start to load the 115 curated tools and
  become healthy. The `start_period: 90s` healthcheck accommodates this.

State persistence:

| Volume | Mount point | Contents |
|---|---|---|
| `smcp_workspace` | `/root/.tooluniverse` | TU workspace, HPA bulk TSVs, NCBI cache |

Subsequent `docker compose up -d` (without `-v`) re-uses the volume.

> Tool_RAG (the embedding-based tool finder) is **excluded by design** —
> it would need `sentence-transformers` + `torch` + a ~3 GB Qwen2-1.5B
> model loaded into CPU RAM, and sempart-demo has only ~4 GB free after
> sqgenaid + Elasticsearch + temporal + alloy. `find_tools` uses
> `Tool_Finder_LLM` (OpenAI-based, cheap, no local model) instead. To
> turn Tool_RAG back on: switch the Dockerfile to install with
> `.[embedding]` and drop `--exclude-tools Tool_RAG` from CMD.

## Routine deploy (after a code change)

```bash
ssh sempart-demo
cd /opt/swiss-rockets-delivery
git pull origin <branch>
cd libs/tooluniverse/deploy
./deploy.sh && ./smoke.sh
```

## Tool surface (~115 advertised)

OpenAI's Chat Completions API caps `tools[]` at 128. Squirro's native MCP
integration is client-side — it pulls the whole `tools/list` from SMCP
and forwards every entry into that `tools[]` array. Full TU load (~2,278
tools) busts the cap and returns:

```
openai.BadRequestError: 400 - Invalid 'tools': array too long.
Expected an array with maximum length 128, but got an array with length 2278.
```

So we curate at the SMCP side via `--categories`:

| Category | Tools | Why kept |
|---|---|---|
| `clinical_trials` | 16 | CT.gov — current demo focus (focal-onset epilepsy trial extraction) |
| `tool_finder` | 4 | `find_tools`, Tool_Finder_LLM, Tool_Finder_Keyword (Tool_RAG excluded) |
| `special_tools` | 3 | Essential utility tools |

> **Tool count is now ~23, not 115.** Squirro's LLM-side "tool suggestion"
> step times out when ~86 KB of tool schemas hit the model. Keeping the
> advertised surface tight (≤ ~30 tools) keeps the agent decision latency
> within Squirro's timeout. Add categories back to the CMD as new demo
> workflows need them — and re-test latency end-to-end after each add.

Temporarily dropped (re-enable per use case):
- `opentarget` (55), `uniprot` (17), `hpa` (14), `alphamissense` (3),
  `alphafold` (3) — covered by SR's `target_discovery` / standalone
  plugins for now; re-add to the SMCP CMD individually when an SMCP-only
  demo workflow needs them and re-measure agent-decision latency.

Permanently excluded (already covered by SR standalone plugins):
- `fda_drug_label` (156), `fda_drug_adverse_event` (15+6), `ChEMBL` (29)
  — `competition_landscape_tool` / `competitive_radar` handle these.

`smoke.sh` enforces `tool_count ≤ 128` (OpenAI's hard cap). The looser
"keep ≤ 30 for Squirro latency" constraint is enforced by Dockerfile
comments rather than smoke.sh, since the right value depends on
Squirro's agent timeout.

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
| Squirro reports `ToolFinderEmbedding requires dependencies` | The `Tool_RAG` MCP tool is being advertised. Check that `--exclude-tools Tool_RAG` is in the Dockerfile CMD and rebuild. The agent should be using `find_tools` (LLM-based) instead. |
| OOM on sempart during deploy | The `[embedding]` extra is enabled and the 1.5 B Tool_RAG model is being loaded. Revert: install plain `.` (no extras) and add `Tool_RAG` to `--exclude-tools`. |

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
