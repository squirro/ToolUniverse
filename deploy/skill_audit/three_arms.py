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
import os
import re
import sys
import time
from pathlib import Path

from .squirro_chat import SquirroChatClient, StudioProxyChatClient
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
    # A different agent, possibly on a different cluster: the General Research agent
    # with web search, code interpreter, trials and patents — no ToolUniverse, no
    # skills. The one arm where persona and toolset differ: the baseline, not a variant.
    "web": "",
}

_TARGET = {"srdev": "_SRDEV_CLOUD", "srdev-com": "_SRDEV_COM", "sempart": ""}


def _client_factory(target: str):
    suffix = _TARGET[target]
    cluster = os.environ[f"SQUIRRO_CLUSTER{suffix}"].rstrip("/")
    token = os.environ[f"SQUIRRO_TOKEN{suffix}"]
    project = os.environ[f"SQUIRRO_PROJECT{suffix}"]
    cls = StudioProxyChatClient if target == "srdev-com" else SquirroChatClient
    return lambda: cls(cluster, token, project)

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


# Not a PRR: "95% CI", "COVID-19", the footnote marker [^3^], the isotope ^{177}Lu.
_PRR = re.compile(r"PRR[^0-9\n]{0,24}?(?<![-{^\[])(\d{1,4}(?:\.\d{1,3})?)(?![\d.^])(?!\s*\\?%)")
_CELL_NUMBER = re.compile(r"(\d{1,4}(?:\.\d{1,3})?)")


def prr_values(answer: str) -> list[str]:
    """Values the report presents AS the PRR.

    Two ways a report says it: the number right after "PRR" in prose ("PRR
    95.953 (CI …)" states one value, not three; "95% CI" states none), and a
    markdown table whose header names a PRR column, one value per row.
    """
    found = [m.group(1) for m in _PRR.finditer(answer or "")]
    column = None
    for line in (answer or "").splitlines():
        if not line.strip().startswith("|"):
            column = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if column is None:
            hits = [i for i, c in enumerate(cells) if "PRR" in c.upper()]
            column = hits[0] if hits else -1
            continue
        if column >= 0 and column < len(cells) and not set(cells[column]) <= set("-: "):
            m = _CELL_NUMBER.search(cells[column])
            if m:
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
    reached = set()
    for a in turn_actions:
        if a.get("tool_name") == "execute_tool":
            reached.add(((a.get("content") or {}).get("parameters") or {}).get("tool_name"))
        elif a.get("tool_name") in ("run_skill", "continue_skill"):
            # The server made the calls; the finished bundle names them per step.
            m = re.search(r'"calls": (\{.*?\})', (a.get("content") or {}).get("output") or "", re.S)
            if m:
                try:
                    for tools in json.loads(m.group(1)).values():
                        reached.update(tools)
                except ValueError:
                    pass
    return {
        "prr_values_stated": len(stated),
        "prr_values_traceable": len(traceable),
        "prr_values_untraceable": sorted(set(stated) - set(traceable)),
        "prr_value_set": sorted({f"{float(v):.1f}" for v in stated}),
        "distinct_tools_reached": sorted(x for x in reached if x),
        "tools_called": [a.get("tool_name") for a in turn_actions],
        "used_run_skill": any(a.get("tool_name") == "run_skill" for a in turn_actions),
        "used_get_skill": any(a.get("tool_name") == "get_skill" for a in turn_actions),
        "delegated_questions": sum(
            1 for a in turn_actions if a.get("tool_name") in ("run_skill", "continue_skill")
            and '"kind": "delegate"' in ((a.get("content") or {}).get("output") or "")),
        "execute_tool_calls": sum(1 for a in turn_actions if a.get("tool_name") == "execute_tool"),
        "answer_len": len(answer or ""),
    }


def run(args) -> int:
    _load_dotenv(Path(args.env_file) if args.env_file else None)
    out_dir = Path(args.out) if args.out else OUT / f"three-arms-{time.strftime('%Y-%m-%d')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    arms = args.arms.split(",") if args.arms else list(ARMS)
    agent_for = {arm: args.agent_id for arm in ARMS}
    client_for = {arm: _client_factory(args.target) for arm in ARMS}
    if args.web_agent_id:
        agent_for["web"] = args.web_agent_id
        client_for["web"] = _client_factory(args.web_target or args.target)
    elif "web" in arms:
        print("ERROR: --web-agent-id is required for the web arm", file=sys.stderr)
        return 2
    rows = []
    for arm in arms:
        for n in range(1, args.runs + 1):
            path = out_dir / f"{arm}-r{n}.json"
            if path.exists() and not args.redo:
                rows.append(json.loads(path.read_text()))
                print(f"{arm} r{n}: cached")
                continue
            started = time.monotonic()
            turn = client_for[arm]().ask(agent_for[arm], ARMS[arm] + QUESTION,
                                          timeout=args.timeout)
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

    print(render(rows))
    (out_dir / "table.md").write_text(render(rows))
    return 0


def render(rows: list[dict]) -> str:
    """Per run, then per arm: the value set shared by every repeat over the union."""
    lines = ["| arm | run | s | PRR stated | traceable | invented | model tool calls | distinct tools | error |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        model_calls = len(r["tools_called"])
        lines.append(f"| {r['arm']} | {r['run']} | {r['seconds']:.0f} | {r['prr_values_stated']} | "
                     f"{r['prr_values_traceable']} | {len(r['prr_values_untraceable'])} | "
                     f"{model_calls} | {len(r.get('distinct_tools_reached', []))} | {r['error'] or ''} |")
    lines += ["", "| arm | runs | PRR values in every run | in any run | consistency | invented total |",
              "|---|---|---|---|---|---|"]
    by_arm: dict[str, list[dict]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], []).append(r)
    for arm, rs in by_arm.items():
        sets = [set(r.get("prr_value_set", [])) for r in rs]
        every = set.intersection(*sets) if sets else set()
        any_ = set.union(*sets) if sets else set()
        ratio = f"{len(every)/len(any_):.0%}" if any_ else "-"
        invented = sum(len(r["prr_values_untraceable"]) for r in rs)
        lines.append(f"| {arm} | {len(rs)} | {len(every)} | {len(any_)} | {ratio} | {invented} |")
    return "\n".join(lines) + "\n"


def rescore(args) -> int:
    """Re-grade saved runs after a scorer change; nothing is re-run."""
    out_dir = Path(args.out)
    rows = []
    for path in sorted(out_dir.glob("*-r*.json")):
        r = json.loads(path.read_text())
        r.update(score(r["actions"], r["answer"]))
        if r.get("server_activities"):
            # Annotated from the Temporal history for runs whose bundle predates `calls`.
            r["distinct_tools_reached"] = sorted(r["server_activities"])
        path.write_text(json.dumps(r, indent=1, ensure_ascii=False))
        rows.append(r)
    rows.sort(key=lambda r: (list(ARMS).index(r["arm"]), r["run"]))
    print(render(rows))
    (out_dir / "table.md").write_text(render(rows))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-id")
    ap.add_argument("--web-agent-id", help="the baseline agent for the `web` arm")
    ap.add_argument("--web-target", choices=list(_TARGET),
                    help="cluster of the web arm's agent, if not --target")
    ap.add_argument("--target", default="srdev", choices=["srdev", "srdev-com", "sempart"])
    ap.add_argument("--env-file")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--arms", help="comma-separated subset of prose,bare,modelled")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--rescore", action="store_true", help="re-grade the saved runs in --out")
    args = ap.parse_args(argv)
    return rescore(args) if args.rescore else run(args)


if __name__ == "__main__":
    sys.exit(main())
