# SMCP on Swiss Rockets Squirro hosts

Hosts the local ToolUniverse fork (`libs/tooluniverse/`) as an MCP server,
bound to host loopback `127.0.0.1:8765`. Squirro GenAI reaches it at
`http://127.0.0.1:8765/mcp` (see per-host reachability below).

Deployed on two hosts. The container config is **identical** on both —
only the SSH alias and the per-host `.env` differ. Everything below is
parameterised by `$HOST`; set it to one of the aliases in the table.

| Host (SSH alias) | Repo path | Host port | GenAI runtime | Reaches SMCP via loopback? |
|---|---|---|---|---|
| `sempart-demo-squirro-cloud` | `/opt/swiss-rockets-delivery` | `8765` | `sqgenaid` **host process** | ✅ shares host loopback |
| `sr-dev-squirro-cloud` | `/opt/swiss-rockets-delivery` | `8765` | `squirro-service-genai` **container** | ⚠️ container loopback ≠ host — see below |

> **Why host port 8765 (not 8000)?** On sempart-demo, `sqgenaid` already
> binds uvicorn on `127.0.0.1:8000`, so SMCP offsets to 8765. On sr-dev
> 8000 is free, but we keep 8765 there too so the compose file, smoke
> default, and any plugin-wiring URL are identical across hosts. The
> container internally always listens on 8000; only the host-side mapping
> is 8765.

> **Reachability differs by host.** SMCP publishes on the *host's*
> loopback. A GenAI **host process** (sempart's `sqgenaid`) shares that
> namespace and reaches `127.0.0.1:8765` directly. A GenAI **container**
> (sr-dev's `squirro-service-genai`) has its own loopback, so it cannot
> reach the host's `127.0.0.1:8765` — wiring Squirro→SMCP there needs a
> shared docker network or the docker bridge-gateway address. Host-side
> `smoke.sh` passes on both hosts regardless; this only affects the
> live Squirro-integration step (see "Connecting from a Squirro plugin").

> **The box deploys from git.** `libs/tooluniverse` on each host is a
> git checkout of the `squirro/ToolUniverse` fork (branch `swiss-rockets`),
> cloned over **anonymous HTTPS** — the box only pulls, so no deploy key
> is needed (pushes happen from a dev machine). The SMCP source is a
> *submodule* and the parent `swiss-rockets-delivery` repo doesn't track
> `libs/`, so you clone the **fork directly** into the `libs/tooluniverse`
> path — not the parent repo. The tree is owned by `htafer`; docker
> daemon ops need `sudo` (`htafer` is not in the `docker` group).

> **Connectivity & trust review:** [`CONNECTIVITY.md`](CONNECTIVITY.md)
> is the IT-facing as-of-DSR-443 document — topology, on-wire sequences,
> egress destinations, loopback-only trust posture. This README covers
> ops; `CONNECTIVITY.md` covers the wire and the trust boundary.

This replaces the `_vendor/tooluniverse/` bundling trick used by
`integration/genai/research_pipeline/`: instead of cramming TU into the
plugin sandbox (which crashes `sqgenaid` on optional deps like
`pandas` / `duckdb` / `playwright`), TU runs in its own container with
its own Python env.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | `python:3.12-slim` base, `pip install -e` from `libs/tooluniverse/`. Runs `tooluniverse-smcp --transport http --compact-mode` — exposes 5 meta-tools, all ~2,278 TU tools reachable via `execute_tool` (see "Tool surface" below). |
| `docker-compose.yml` | Service `smcp`, port `127.0.0.1:8765:8000`, named volume, TCP healthcheck, log rotation |
| `.env.template` | Tracked. Lists every env var the server reads. Copy to `.env` and fill. |
| `.env` | **gitignored**. Hand-maintained per host. Holds API keys. |
| `deploy.sh` | Pre-flight checks + `docker compose up -d --build` |
| `smoke.sh` | `tools/list` count + one `execute_tool → search_clinical_trials` end-to-end call |

## First-time setup on a host

Clone the fork into the `libs/tooluniverse` path, provision `.env`, then
build. All steps run **on the host**.

```bash
HOST=sr-dev-squirro-cloud          # or sempart-demo-squirro-cloud
BRANCH=swiss-rockets               # deployed branch (use a feature branch while iterating)
REPO=https://github.com/squirro/ToolUniverse.git
DEST=/opt/swiss-rockets-delivery/libs/tooluniverse

ssh "$HOST" bash -s <<EOF
set -e
# 0. (first time only) /opt may be root-owned & empty — claim it so you
#    don't need sudo for git/file ops (docker still needs sudo, below):
sudo mkdir -p /opt/swiss-rockets-delivery/libs
sudo chown -R \$USER:\$USER /opt/swiss-rockets-delivery

# 1. clone the fork directly into the libs/tooluniverse path
git clone --branch "$BRANCH" "$REPO" "$DEST"

# 2. provision .env (gitignored — never in the clone). Start from the
#    template and fill keys, or copy from another host (see note below).
cd "$DEST/deploy"
cp .env.template .env
\$EDITOR .env

# 3. build + start (sudo: htafer not in docker group)
sudo ./deploy.sh
EOF

# 4. smoke (retry until warmup finishes — see note under Routine deploy)
ssh "$HOST" "cd $DEST/deploy && until ./smoke.sh; do sleep 20; done"
```

> **Copying `.env` between hosts** instead of hand-filling: the same keys
> work everywhere, and `scp -3` routes host→host via your local machine
> without printing secrets:
> ```bash
> scp -3 sempart-demo-squirro-cloud:$DEST/deploy/.env "$HOST:$DEST/deploy/.env"
> ```

> **Converting a legacy rsync'd host to git:** if a host's tree was
> populated by rsync (no `.git`), turn it into a checkout in place without
> disturbing `.env` (gitignored, so `reset --hard` leaves it alone):
> ```bash
> cd "$DEST" && git init -q && git remote add origin "$REPO" \
>   && git fetch -q origin "$BRANCH" && git reset --hard "origin/$BRANCH" \
>   && git branch -u "origin/$BRANCH" "$BRANCH" 2>/dev/null || git checkout -B "$BRANCH" "origin/$BRANCH"
> ```

Expected on first build:
- 2–4 minutes for the initial `docker compose up --build` (pandas, numpy,
  faiss-cpu, lxml, playwright … — heavy wheels).
- Up to ~3–4 minutes after container start to load all ~2,278 tools in
  background and become healthy. The `start_period: 300s` healthcheck
  accommodates this. Most tools are HTTP wrappers (cheap to import); a
  few model-loading tools (Tool_RAG) are excluded for memory reasons.

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

Push your change to the fork branch from your dev machine, then pull +
rebuild on each host. `.env` is gitignored so `git pull` never touches it.

```bash
# --- from your dev machine: publish the change ---
#   cd libs/tooluniverse && git pull --rebase && git push origin <branch>
#   (the fork auto-merges upstream mims-harvard:main into feature branches,
#    so always `git pull --rebase` before pushing — see repo CLAUDE.md)

# --- on each host: pull + rebuild ---
HOST=sr-dev-squirro-cloud          # or sempart-demo-squirro-cloud
DEST=/opt/swiss-rockets-delivery/libs/tooluniverse

ssh "$HOST" "cd $DEST && git pull --rebase --ff-only \
  && cd deploy && sudo ./deploy.sh && until ./smoke.sh; do sleep 20; done"
```

> `smoke.sh` step 3 calls a background-loaded tool, which isn't ready for
> ~3–4 min after a cold start while compact mode loads all ~2,278 tools.
> On a fresh build, retry `./smoke.sh` until it passes — hence the
> `until … sleep 20` loop above. Steady-state restarts (no `--build`
> changes) reuse the warm volume and pass immediately.

## Tool surface (5 advertised, all ~2,278 reachable)

OpenAI's Chat Completions API caps `tools[]` at 128. Squirro's native MCP
integration is client-side — it pulls the whole `tools/list` from SMCP
and forwards every entry into that `tools[]` array. Full TU load (~2,278
tools) busts the cap. Even staying under it, ~115 tools' worth of
schemas (~86 KB) caused Squirro's per-turn agent timeout in
2026-05-12 testing.

We use TU's built-in **`--compact-mode`** to solve both problems at once.
In compact mode TU loads all tools in the background but only exposes a
small meta-tool surface to MCP:

| Tool | Purpose |
|---|---|
| `find_tools` | LLM-ranked natural-language tool discovery (returns name + description + parameter schema per match) |
| `list_tools` | Plain enumeration of available tools |
| `grep_tools` | Substring search over tool names/descriptions |
| `get_tool_info` | Detailed info for a specific tool by name |
| `execute_tool` | Generic invoker — `{tool_name, arguments}` → dispatches to any of the ~2,278 loaded tools |

The agent flow is: `find_tools(query)` → pick a candidate → `execute_tool(name, args)`.
This bypasses both the 128 hard cap (only 5 entries advertised) and the
~30 soft cap (~2 KB total schema vs ~86 KB previously).

Tool_RAG stays excluded via `--exclude-tools Tool_RAG` because its
embedding-based finder loads a 1.5 B Qwen2 model that OOMs sempart's
4 GB free RAM. `find_tools` (LLM-backed via OpenAI) covers discovery
without local model load.

`smoke.sh` validates the meta-tool surface and runs an end-to-end
`execute_tool` call to a non-statically-loaded tool, proving compact
mode reaches the full TU breadth.

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
| `smoke.sh` step 3 returns no result | Either the CT.gov API is unreachable from the host (egress firewall) or the tool name has drifted (`search_clinical_trials` is current as of writing) |
| Disk filling up | The `smcp_workspace` volume has no eviction policy. `docker volume inspect smcp_workspace` to see size; `docker volume rm smcp_workspace` to wipe (forces a rebuild of caches/index on next start) |
| Need to wipe and rebuild from scratch | `docker compose down -v && ./deploy.sh` |
| Squirro reports `ToolFinderEmbedding requires dependencies` | The `Tool_RAG` MCP tool is being advertised. Check that `--exclude-tools Tool_RAG` is in the Dockerfile CMD and rebuild. The agent should be using `find_tools` (LLM-based) instead. |
| OOM on sempart during deploy | The `[embedding]` extra is enabled and the 1.5 B Tool_RAG model is being loaded. Revert: install plain `.` (no extras) and add `Tool_RAG` to `--exclude-tools`. |

## Out of scope

- TLS / external exposure — server is loopback-only.
- Auth — anyone with shell on the host can call it. `.env` is the most
  sensitive file in this directory.
- Third host (`sr-dev-com`) — not deployed yet. No script change needed
  when it is: the container is host-agnostic, so just add the alias to
  the Hosts table and run the same `$HOST`-parameterised flow. (The
  earlier idea of an `SMCP_TARGET` env var in `deploy.sh` is unnecessary —
  per-host variance lives in `.env` and the SSH alias, not the container.)
- CI/CD image push — image is built on each host from the git checkout.
- Plugin migrations — separate PRs per plugin. On sr-dev specifically,
  the Squirro→SMCP wiring must cross the container boundary (see the
  reachability note at the top), not just hit host loopback.
