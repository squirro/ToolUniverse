"""Coverage sweep over the served skills: one probe question each, trace-scored.

Run it from this repo's ``deploy/`` directory, pointed at wherever the skills are
deployed — sr-dev, sempart, anywhere an agent reaches an SMCP:

    cd deploy
    python -m skill_audit.sweep run --agent-id <id> --env-file <path/to/.env>
    python -m skill_audit.sweep rescore --run <run-dir>
    python -m skill_audit.sweep diff --old <run-a> --new <run-b>

Each skill gets one fresh conversation (Squirro binds the MCP tool list per
conversation, so re-using one would leak state between skills), one turn, and a
verdict from `oracle`, which reads only the trace. A `retry` verdict — the
provider's intermittent bio-risk refusal — is re-run once before being recorded.

The run directory holds `results.jsonl` (one line per skill, appended as it
finishes, so an interrupted sweep resumes), `traces/<skill>.json` so a scorer fix
costs a `rescore` instead of another hour of cluster time, `answers/<skill>.md`
for reading the suspicious ones by hand, and `report.md` sorted worst-first.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

import yaml

from skill_audit.oracle import score, verdict
from skill_audit.squirro_chat import SquirroChatClient

DEPLOY = Path(__file__).resolve().parents[1]
CORPUS = Path(__file__).resolve().parent / "questions.yaml"
BODIES = DEPLOY
RUNS = DEPLOY / "skill-audit-runs"

_ORDER = {"fail": 0, "retry": 1, "warn": 2, "pass": 3}


# --- pure helpers (tested) --------------------------------------------------

def rows_to_run(
    corpus: list[dict],
    done: set[str],
    *,
    retryable: set[str] | None = None,
    only: list[str] | None = None,
    tier: int | None = None,
    limit: int | None = None,
) -> list[dict]:
    """The probes still owed, after resume and filters."""
    retryable = retryable or set()
    rows = [r for r in corpus
            if r["skill"] not in done or r["skill"] in retryable]
    if only:
        wanted = set(only)
        rows = [r for r in rows if r["skill"] in wanted]
    if tier is not None:
        rows = [r for r in rows if r.get("tier") == tier]
    return rows[:limit] if limit else rows


def latest_per_skill(results: list[dict]) -> list[dict]:
    """A resumed sweep appends, so one skill can appear twice — keep the last."""
    by_skill: dict[str, dict] = {}
    for r in results:
        by_skill[r["skill"]] = r
    return list(by_skill.values())


def render_report(results: list[dict]) -> str:
    """Worst first: failures, then warnings by weight, then clean runs."""
    results = latest_per_skill(results)
    ordered = sorted(
        results,
        key=lambda r: (_ORDER.get(r["verdict"], 9), -r.get("n_warn", 0),
                       r["skill"]),
    )
    counts: dict[str, int] = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    lines = ["# Skill coverage sweep", ""]
    lines.append(" · ".join(f"**{k}** {v}" for k, v in
                            sorted(counts.items(), key=lambda kv: _ORDER.get(kv[0], 9))))
    lines += ["", "| skill | verdict | codes | calls | answer |",
              "| --- | --- | --- | --- | --- |"]
    for r in ordered:
        codes = ", ".join(sorted({f["code"] for f in r.get("findings", [])}))
        lines.append(
            f"| {r['skill']} | {r['verdict']} | {codes or '—'} | "
            f"{len(r.get('calls', []))} | {r.get('answer_len', 0)} |")
    return "\n".join(lines) + "\n"


MAX_OUTPUT = 8_000


def trim_actions(actions: list[dict]) -> list[dict]:
    """Keep exactly what the oracle reads, with each output capped.

    A raw turn carries megabytes of tool payload; the scorer only looks at the
    tool name, the status, the call's parameters and the output text.
    """
    kept = []
    for action in actions or []:
        content = action.get("content") or {}
        output = content.get("output")
        if not isinstance(output, str):
            output = json.dumps(output) if output is not None else ""
        kept.append({
            "tool_name": action.get("tool_name"),
            "status": action.get("status"),
            "content": {"parameters": content.get("parameters") or {},
                        "output": output[:MAX_OUTPUT]},
        })
    return kept


def rescore_trace(path: Path, body: str | None) -> dict:
    """Re-run the oracle over a saved trace — no cluster, no LLM, no cost."""
    trace = json.loads(Path(path).read_text())
    findings = score(trace["skill"], actions=trace.get("actions") or [],
                     answer=trace.get("answer") or "",
                     error=trace.get("error"), body=body)
    return {
        "skill": trace["skill"],
        "tier": trace.get("tier"),
        "note": trace.get("note"),
        "verdict": verdict(findings),
        "findings": [f.to_dict() for f in findings],
        "n_warn": sum(1 for f in findings if f.severity == "warn"),
        "calls": trace.get("calls") or [],
        "answer_len": len(trace.get("answer") or ""),
        "error": trace.get("error"),
    }


def diff_runs(old: list[dict], new: list[dict]) -> dict:
    """What changed between two sweeps — the regression gate."""
    before = {r["skill"]: r["verdict"] for r in latest_per_skill(old)}
    after = {r["skill"]: r["verdict"] for r in latest_per_skill(new)}
    bad = {"fail"}
    return {
        "regressed": sorted(s for s, v in after.items()
                            if v in bad and before.get(s) not in bad
                            and s in before),
        "fixed": sorted(s for s, v in after.items()
                        if v not in bad and before.get(s) in bad),
        "absent": sorted(s for s in before if s not in after),
        "new": sorted(s for s in after if s not in before),
    }


# --- live sweep -------------------------------------------------------------

def load_corpus() -> list[dict]:
    return yaml.safe_load(CORPUS.read_text())["skills"]


def _body(skill: str) -> str | None:
    path = BODIES / f"persona-{skill}.md"
    return path.read_text(encoding="utf-8") if path.exists() else None


def _probe(client_factory, agent_id: str, row: dict, timeout: int) -> dict:
    """One skill, one fresh conversation. Retries once on a provider refusal."""
    skill, question = row["skill"], row["question"]
    body = _body(skill)
    attempts = []
    for attempt in (1, 2):
        started = time.monotonic()
        turn = client_factory().ask(agent_id, question, timeout=timeout)
        findings = score(skill, actions=turn.actions, answer=turn.answer,
                         error=turn.error, body=body)
        result = {
            "skill": skill,
            "tier": row.get("tier"),
            "note": row.get("note"),
            "attempt": attempt,
            "verdict": verdict(findings),
            "findings": [f.to_dict() for f in findings],
            "n_warn": sum(1 for f in findings if f.severity == "warn"),
            "calls": turn.calls,
            "answer_len": len(turn.answer),
            "answer": turn.answer,
            "error": turn.error,
            "seconds": round(time.monotonic() - started, 1),
            "actions": trim_actions(turn.actions),
        }
        attempts.append(result)
        if result["verdict"] != "retry":
            break
    final = attempts[-1]
    final["attempts"] = len(attempts)
    return final


def _load_dotenv(path: Path | None) -> None:
    """Fill missing SQUIRRO_* vars from a dotenv file.

    Parsed here rather than sourced in the shell: these files hold API keys with
    characters bash tries to execute, and sourcing one prints secrets to stdout.
    Anything already in the environment wins, so CI can inject secrets instead.
    """
    if path is None or not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def run(args) -> int:
    _load_dotenv(Path(args.env_file) if args.env_file else DEPLOY / ".env")
    suffix = {"srdev": "_SRDEV_CLOUD", "srdev-com": "_SRDEV_COM",
              "sempart": ""}[args.target]
    try:
        cluster = os.environ[f"SQUIRRO_CLUSTER{suffix}"].rstrip("/")
        token = os.environ[f"SQUIRRO_TOKEN{suffix}"]
        project = os.environ[f"SQUIRRO_PROJECT{suffix}"]
    except KeyError as missing:
        print(f"ERROR: {missing} not set — export it or pass --env-file",
              file=sys.stderr)
        return 2

    run_dir = Path(args.out) if args.out else (
        RUNS / time.strftime("%Y-%m-%dT%H-%M-%S", time.gmtime()))
    run_dir.mkdir(parents=True, exist_ok=True)
    answers = run_dir / "answers"
    answers.mkdir(exist_ok=True)
    traces = run_dir / "traces"
    traces.mkdir(exist_ok=True)
    jsonl = run_dir / "results.jsonl"

    results: list[dict] = []
    if jsonl.exists():
        results = [json.loads(line) for line in jsonl.read_text().splitlines()
                   if line.strip()]
    latest = latest_per_skill(results)
    done = {r["skill"] for r in latest}
    # A refusal is not an answer: resume owes those skills another turn.
    retryable = {r["skill"] for r in latest if r["verdict"] == "retry"}

    todo = rows_to_run(load_corpus(), done, retryable=retryable, only=args.only,
                       tier=args.tier, limit=args.limit)
    if not todo:
        print(f"nothing to run (resumed {len(done)} from {run_dir})")
    print(f"{len(todo)} skills -> {run_dir}", flush=True)

    def factory():
        return SquirroChatClient(cluster=cluster, refresh_token=token,
                                 project_id=project)

    lock = Lock()
    handle = jsonl.open("a")

    def one(row):
        try:
            return _probe(factory, args.agent_id, row, args.timeout)
        except Exception as exc:                       # noqa: BLE001
            return {"skill": row["skill"], "verdict": "fail", "n_warn": 0,
                    "findings": [{"code": "harness_error", "severity": "fail",
                                  "message": f"{type(exc).__name__}: {exc}",
                                  "evidence": {}}],
                    "calls": [], "answer": "", "answer_len": 0}

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(one, row): row for row in todo}
        for future in as_completed(futures):
            result = future.result()
            answer = result.pop("answer", "")
            actions = result.pop("actions", [])
            (answers / f"{result['skill']}.md").write_text(
                f"# {result['skill']} — {result['verdict']}\n\n"
                f"calls: {result.get('calls')}\n\n---\n\n{answer}\n")
            # The trace is the expensive artefact: keeping it means a scorer fix
            # costs a `rescore`, not another hour of cluster time.
            (traces / f"{result['skill']}.json").write_text(json.dumps({
                "skill": result["skill"], "tier": result.get("tier"),
                "note": result.get("note"), "error": result.get("error"),
                "calls": result.get("calls"), "answer": answer,
                "actions": actions,
            }))
            with lock:
                handle.write(json.dumps(result) + "\n")
                handle.flush()
                results.append(result)
                print(f"  {result['verdict']:5} {result['skill']}", flush=True)
    handle.close()

    (run_dir / "report.md").write_text(render_report(results))
    print(f"\n{run_dir}/report.md")
    return 0


def rescore(args) -> int:
    """Re-run the current oracle over a finished run's saved traces."""
    run_dir = Path(args.run)
    traces = sorted((run_dir / "traces").glob("*.json"))
    if not traces:
        print(f"no traces in {run_dir}/traces — that run predates trace saving",
              file=sys.stderr)
        return 2
    results = [rescore_trace(path, _body(path.stem)) for path in traces]
    with (run_dir / "results.jsonl").open("w") as handle:
        for result in results:
            handle.write(json.dumps(result) + "\n")
    (run_dir / "report.md").write_text(render_report(results))
    print(f"rescored {len(results)} traces -> {run_dir}/report.md")
    return 0


def diff(args) -> int:
    def load(path):
        return [json.loads(line) for line in
                (Path(path) / "results.jsonl").read_text().splitlines()
                if line.strip()]
    delta = diff_runs(load(args.old), load(args.new))
    print(json.dumps(delta, indent=2))
    return 1 if delta["regressed"] else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="skill_audit.sweep")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run")
    r.add_argument("--agent-id", required=True)
    r.add_argument("--target", default="srdev",
                   choices=["srdev", "srdev-com", "sempart"])
    r.add_argument("--concurrency", type=int, default=4)
    r.add_argument("--timeout", type=int, default=600)
    r.add_argument("--only", nargs="*", default=None)
    r.add_argument("--tier", type=int, default=None)
    r.add_argument("--limit", type=int, default=None)
    r.add_argument("--out", default=None,
                   help="run directory; an existing one is resumed")
    r.add_argument("--env-file", default=None,
                   help="dotenv holding SQUIRRO_CLUSTER/TOKEN/PROJECT for the "
                        "target (default: deploy/.env). Existing environment "
                        "variables always win.")
    r.set_defaults(func=run)

    s = sub.add_parser("rescore",
                       help="re-run the oracle over a run's saved traces")
    s.add_argument("--run", required=True)
    s.set_defaults(func=rescore)

    d = sub.add_parser("diff")
    d.add_argument("--old", required=True)
    d.add_argument("--new", required=True)
    d.set_defaults(func=diff)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
