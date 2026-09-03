"""The three-arm comparison DSR-706 exists for (ADR-0016, DSR-713).

One question, three ways, N runs each, on one deployment and one agent:

    prose     the skill body served plain; the agent follows the phases itself
    bare      no skill at all; the agent finds and calls tools on its own
    modelled  the Skill Process, run server-side on Temporal via run_skill

Scored the way the original 12/12 measurement was scored: how many
disproportionality (PRR) values the report states, how many of those can be
found in a tool result the same turn produced, and how many cannot (a value the
model made up). A trace can fail an arm; nothing here passes one on style.

    python -m skill_audit.three_arms --agent-id <id> --env-file ../.env --runs 3
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from .squirro_chat import SquirroChatClient
from .sweep import _load_dotenv, trim_actions

DEPLOY = Path(__file__).resolve().parents[1]
OUT = DEPLOY.parents[2] / "reports" / "skill_sweep"

QUESTION = (
    "What is the safety picture for Lutathera (lutetium Lu-177 dotatate), especially "
    "myelodysplastic syndrome and renal impairment? Give the FAERS disproportionality "
    "(PRR) value for each main reported reaction, with the label, pharmacogenomic, "
    "trial and literature context."
)

ARMS = {
    "prose": (
        "Load the clinical-data-integration skill with get_skill(name=\"clinical-data-"
        "integration\", plain=true) and follow its phases yourself, calling every tool "
        "through execute_tool. Do not call run_skill or continue_skill. "
    ),
    "bare": (
        "Do not load any skill (no get_skill, find_skill, run_skill or "
        "continue_skill). Use find_tools and execute_tool as you see fit. "
    ),
    "modelled": (
        "Use the clinical-data-integration skill. "
    ),
}

_NUMBER = re.compile(r"(?<![\w.])(\d{1,4}(?:\.\d{1,3})?)(?![\w.])")


def numbers_in(text: str) -> set[str]:
    """Decimal values as written; integers too small to be a PRR are ignored."""
    out = set()
    for m in _NUMBER.finditer(text or ""):
        value = m.group(1)
        if "." in value or int(value) >= 10:
            out.add(value)
    return out


def _rounded_forms(value: str) -> set[str]:
    f = float(value)
    return {value, f"{f:.0f}", f"{f:.1f}", f"{f:.2f}", f"{f:.3f}"}


def prr_values(answer: str) -> list[str]:
    """Values the report presents as PRR: a decimal within a line that says PRR."""
    found = []
    for line in (answer or "").splitlines():
        if "PRR" in line.upper():
            for m in _NUMBER.finditer(line):
                if "." in m.group(1):
                    found.append(m.group(1))
    return found


def score(turn_actions: list[dict], answer: str) -> dict:
    evidence: set[str] = set()
    for action in turn_actions:
        output = (action.get("content") or {}).get("output") or ""
        for value in numbers_in(output):
            evidence |= _rounded_forms(value)
    stated = prr_values(answer)
    traceable = [v for v in stated if _rounded_forms(v) & evidence]
    return {
        "prr_values_stated": len(stated),
        "prr_values_traceable": len(traceable),
        "prr_values_untraceable": sorted(set(stated) - set(traceable)),
        "tools_called": [a.get("tool_name") for a in turn_actions],
        "used_run_skill": any(a.get("tool_name") == "run_skill" for a in turn_actions),
        "used_get_skill": any(a.get("tool_name") == "get_skill" for a in turn_actions),
        "execute_tool_calls": sum(1 for a in turn_actions if a.get("tool_name") == "execute_tool"),
        "answer_len": len(answer or ""),
    }


def run(args) -> int:
    _load_dotenv(Path(args.env_file) if args.env_file else None)
    import os
    suffix = {"srdev": "_SRDEV_CLOUD", "srdev-com": "_SRDEV_COM", "sempart": ""}[args.target]
    cluster = os.environ[f"SQUIRRO_CLUSTER{suffix}"].rstrip("/")
    token = os.environ[f"SQUIRRO_TOKEN{suffix}"]
    project = os.environ[f"SQUIRRO_PROJECT{suffix}"]
    out_dir = Path(args.out) if args.out else OUT / f"three-arms-{time.strftime('%Y-%m-%d')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    arms = args.arms.split(",") if args.arms else list(ARMS)
    rows = []
    for arm in arms:
        for n in range(1, args.runs + 1):
            path = out_dir / f"{arm}-r{n}.json"
            if path.exists() and not args.redo:
                rows.append(json.loads(path.read_text()))
                print(f"{arm} r{n}: cached")
                continue
            started = time.monotonic()
            turn = SquirroChatClient(cluster, token, project).ask(
                args.agent_id, ARMS[arm] + QUESTION, timeout=args.timeout)
            actions = trim_actions(turn.actions)
            row = {"arm": arm, "run": n, "error": turn.error,
                   "seconds": round(time.monotonic() - started, 1),
                   **score(actions, turn.answer),
                   "answer": turn.answer, "actions": actions}
            path.write_text(json.dumps(row, indent=1, ensure_ascii=False))
            rows.append(row)
            print(f"{arm} r{n}: {row['seconds']}s  PRR stated={row['prr_values_stated']} "
                  f"traceable={row['prr_values_traceable']} "
                  f"untraceable={row['prr_values_untraceable']}  "
                  f"run_skill={row['used_run_skill']} get_skill={row['used_get_skill']} "
                  f"execute_tool={row['execute_tool_calls']} error={row['error']}")

    lines = ["| arm | run | s | PRR stated | traceable | untraceable | run_skill | execute_tool | error |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['arm']} | {r['run']} | {r['seconds']} | {r['prr_values_stated']} | "
                     f"{r['prr_values_traceable']} | {len(r['prr_values_untraceable'])} | "
                     f"{'yes' if r['used_run_skill'] else 'no'} | {r['execute_tool_calls']} | "
                     f"{r['error'] or ''} |")
    (out_dir / "table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-id", required=True)
    ap.add_argument("--target", default="srdev", choices=["srdev", "srdev-com", "sempart"])
    ap.add_argument("--env-file")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--arms", help="comma-separated subset of prose,bare,modelled")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out")
    ap.add_argument("--redo", action="store_true")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
