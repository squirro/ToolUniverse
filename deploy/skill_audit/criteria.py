"""Five of the eleven benchmark criteria measured by script, the spread between two runs of one
arm, and the pre-flight that must pass before the first run.

A judge's opinion costs a turn and varies between judges; a script over saved traces costs
nothing and gives the same number every time. The spread is the point of the two-run
protocol: for each question and each arm, how far the two runs are apart -- in the judged
total and in every number they both state -- and how often one run states a quantity the
other does not.

Every pre-flight check comes from a failure of 2026-09-21: the two agents on different
models; a web tool "enabled" in the configuration but absent at run time because its key was
missing; a web call that gave no links; a plugin that failed to load and told nobody but the
genai log.

    python -m skill_audit.criteria preflight --env-file ../.env --web-agent <id> --modelled-agent <id>
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
# A module import: `from tooluniverse import x` goes through the package's lazy tool
# lookup and runs a full registry discovery when the name is not a tool.
import tooluniverse.skill_report_check as rc  # noqa: E402

WEB_ARM_LIMIT = ("Limit of the web arm: on sr-dev it has Exa, Perplexity and OpenAI web search; "
                 "it does not have the internal document search of the production web agent.")

_FOOTNOTE_REF = re.compile(r"\[\^(\d+)\^\]")
_FOOTNOTE_DEF = re.compile(r"^\[\^(\d+)\^\]:\s*(?:\[[^\]]*\]\()?(https?://[^\s)\]]+)", re.M)
_TERM = r"[A-Z][A-Z0-9-]+(?: [A-Z][A-Z0-9-]+)*"
_LABEL = r"PRR|ROR|IC|EBGM|n|N"
_TERM_THEN_VALUE = re.compile(rf"({_TERM})\s*\((?:{_LABEL})\s*[=:]?\s*(-?\d[\d,]*(?:\.\d+)?)\)")
_VALUE_FOR_TERM = re.compile(rf"(?:{_LABEL})\s*[=:]?\s*(-?\d[\d,]*(?:\.\d+)?)\s+for\s+({_TERM})")
_LABEL_OF = re.compile(rf"({_LABEL})\s*[=:]?\s*-?\d")
_LINK = re.compile(r"https?://[^\s<>\"')\]]+")
_PLUGIN_FAILED = "Failed to create plugin tool"


def _prose(answer: str) -> str:
    """The report's text without links, footnote ids and markup, thousands folded."""
    text = _FOOTNOTE_REF.sub(" ", rc._URL.sub(" ", rc._DOI.sub(" ", answer or "")))
    return rc._fold_thousands(text)


def stated_numbers(answer: str) -> list[str]:
    out: list[str] = []
    for match in rc._NUMBER.finditer(_prose(answer)):
        if match.group(1) not in out:
            out.append(match.group(1))
    return out


# --- 1. number traceability ----------------------------------------------------------------

def traceability(answer: str, received: Any) -> dict:
    """The share of the numbers a report states that a stored row (or, for the web arm, a
    page the judges can open) vouches for -- in any rounding the stored value admits."""
    stated = stated_numbers(answer)
    vouched_set = rc._vouched_numbers(received)
    vouched = [n for n in stated if n in vouched_set]
    return {"stated": stated, "vouched": vouched,
            "share": round(len(vouched) / len(stated), 4) if stated else None}


# --- 2. the same quantity in two runs -----------------------------------------------------

def quantities(answer: str) -> dict[str, float]:
    """Each stated value keyed by its term and its label: "OTOTOXICITY PRR" -> 54.766."""
    out: dict[str, float] = {}
    text = answer or ""
    for match in _TERM_THEN_VALUE.finditer(text):
        label = _LABEL_OF.search(match.group(0)[len(match.group(1)):]).group(1)
        out.setdefault(f"{match.group(1)} {label}", float(match.group(2).replace(",", "")))
    for match in _VALUE_FOR_TERM.finditer(text):
        label = _LABEL_OF.search(match.group(0)).group(1)
        out.setdefault(f"{match.group(2)} {label}", float(match.group(1).replace(",", "")))
    return out


def spread(run_a: str, run_b: str, judged: tuple[float, float] | None = None) -> dict:
    """How far two runs of one arm are apart: per quantity both state, and what only one states."""
    a, b = quantities(run_a), quantities(run_b)
    shared = sorted(set(a) & set(b), key=list(a).index)
    differences = {key: round(abs(a[key] - b[key]), 6) for key in shared}
    return {
        "differences": differences,
        "median_difference": round(statistics.median(differences.values()), 6) if differences else None,
        "stated_in_one_run_only": sorted(set(a) ^ set(b)),
        "judged_difference": round(abs(judged[0] - judged[1]), 6) if judged else None,
    }


# --- 3. consistency of the conclusion ------------------------------------------------------

def _ranked_terms(answer: str, label: str = "PRR") -> list[str]:
    scored = [(value, key[: -len(label) - 1]) for key, value in quantities(answer).items()
              if key.endswith(" " + label)]
    return [term for _, term in sorted(scored, key=lambda pair: -pair[0])]


def consistency(run_a: str, run_b: str) -> dict:
    """The same top answer in the two runs: here the signal with the largest stated PRR."""
    top_a, top_b = _ranked_terms(run_a)[:3], _ranked_terms(run_b)[:3]
    union = set(top_a) | set(top_b)
    return {"top": [top_a[0] if top_a else None, top_b[0] if top_b else None],
            "same": bool(top_a) and top_a[:1] == top_b[:1],
            "top3_overlap": len(set(top_a) & set(top_b)) / len(union) if union else None}


# --- 4. citations resolve -----------------------------------------------------------------

def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def citations_resolve(answer: str, fetch_text: Callable[[str], str | None]) -> list[dict]:
    """For each footnoted link: does it open, and does the page hold the statement's numbers?"""
    definitions = dict(_FOOTNOTE_DEF.findall(answer or ""))
    out, seen = [], set()
    for sentence in _sentences(_FOOTNOTE_DEF.sub("", answer or "")):
        refs = _FOOTNOTE_REF.findall(sentence)
        if not refs:
            continue
        numbers = stated_numbers(sentence)
        for ref in refs:
            url = definitions.get(ref)
            if not url or url in seen:
                continue
            seen.add(url)
            page = fetch_text(url)
            folded = rc._fold_thousands(page) if page else ""
            out.append({"url": url, "opens": page is not None,
                        "numbers": numbers if page is not None else [],
                        "contains_statement": page is not None
                        and all(re.search(rf"(?<![\d.]){re.escape(n)}(?![\d.])", folded) for n in numbers)})
    return out


# --- 5. cost -------------------------------------------------------------------------------

def cost(trace: dict) -> dict:
    """Seconds and tokens for one answer; the streaming API exposes no token count, so say so."""
    tokens = trace.get("tokens")
    return {"seconds": trace.get("seconds"), "tokens": tokens,
            "answer_chars": len(trace.get("answer") or ""),
            "note": None if tokens is not None else
            "tokens are not exposed by the streaming API; answer characters are given instead"}


# --- the aggregation ----------------------------------------------------------------------

def _narrower(rows: list[dict], arm: str, key: str) -> tuple[int, int]:
    by_question: dict[str, dict[str, float]] = {}
    for row in rows:
        value = row["spread"].get(key)
        if value is not None:
            by_question.setdefault(row["question"], {})[row["arm"]] = value
    wins = total = 0
    for arms in by_question.values():
        if arm in arms and len(arms) > 1:
            total += 1
            wins += all(arms[arm] < other for name, other in arms.items() if name != arm)
    return wins, total


def aggregate(rows: list[dict]) -> dict:
    """One line per arm for the judged totals and one for the numbers, and the web arm's limit.

    `rows`: {question, arm, spread} with `spread` as `spread()` returns it.
    """
    arms = sorted({row["arm"] for row in rows})
    totals, numbers = [], []
    for arm in arms:
        mine = [row["spread"] for row in rows if row["arm"] == arm]
        judged = [s["judged_difference"] for s in mine if s.get("judged_difference") is not None]
        medians = [s["median_difference"] for s in mine if s.get("median_difference") is not None]
        once = sum(len(s.get("stated_in_one_run_only") or []) for s in mine)
        wins, total = _narrower(rows, arm, "judged_difference")
        totals.append(f"{arm}: median judged difference {statistics.median(judged) if judged else 'n/a'}; "
                      f"narrower in {wins} of {total} questions")
        wins, total = _narrower(rows, arm, "median_difference")
        numbers.append(f"{arm}: median number difference {statistics.median(medians) if medians else 'n/a'}; "
                       f"narrower in {wins} of {total} questions; {once} quantities stated in one run only")
    return {"totals": totals, "numbers": numbers, "limit": WEB_ARM_LIMIT}


# --- the pre-flight -----------------------------------------------------------------------

_WEB_TOOL = re.compile(r"web|exa|perplexity", re.I)


def model_of(agent: dict) -> str:
    """How an agent picks its model: a config suffix, an allowed list, or the project's default."""
    config = agent.get("extra_runtime_config") or {}
    return str(config.get("sqgpt_config_suffix") or config.get("allowed_models") or config.get("model")
               or "project default")


def web_tools_of(agent: dict) -> list[str]:
    tools = (agent.get("toolkit") or {}).get("tools") or []
    return [t.get("custom_name") or t.get("tool_id") for t in tools
            if t.get("enabled", True) and _WEB_TOOL.search(t.get("custom_name") or t.get("tool_id") or "")]


def _output_text(action: dict) -> str:
    content = action.get("content")
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except ValueError:
            return content
    if isinstance(content, dict):
        output = content.get("output", content)
        return output if isinstance(output, str) else json.dumps(output, default=str)
    return json.dumps(content, default=str)


def web_arm_limit(tools: list[str]) -> str:
    """The limit sentence for the report, from the web tools the arm actually has."""
    families = []
    for family, pattern in (("Exa", r"exa"), ("Perplexity", r"perplexity"), ("OpenAI web search", r"openai")):
        if any(re.search(pattern, t, re.I) for t in tools):
            families.append(family)
    if not families:
        named = "no web tool"
    elif len(families) == 1:
        named = families[0]
    else:
        named = ", ".join(families[:-1]) + " and " + families[-1]
    return (f"Limit of the web arm: on sr-dev it has {named}; "
            "it does not have the internal document search of the production web agent.")


def preflight(agents: dict[str, dict], probe_turns: dict | list[dict],
              log_lines: list[str] | None) -> list[str]:
    """Everything that must hold before the first run; an empty list means go.

    `agents`: {"web": agent, "modelled": agent} as the genai agents list returns them.
    `probe_turns`: live turns of the web agent -- one per enabled web tool, each asked by name,
    since one question cannot make an agent use every tool; a single turn is accepted.
    `log_lines`: the genai service log since the probes; None when it could not be read.
    """
    failures = []
    web, modelled = agents["web"], agents["modelled"]
    if model_of(web) != model_of(modelled):
        failures.append(f"model: {web.get('name')} runs {model_of(web)!r}, {modelled.get('name')} runs "
                        f"{model_of(modelled)!r}; the two agents must use the same model")
    turns = [probe_turns] if isinstance(probe_turns, dict) else list(probe_turns)
    actions = [a for turn in turns for a in (turn.get("actions") or [])]
    called = {a.get("tool_name") for a in actions}
    for tool in web_tools_of(web):
        if tool not in called:
            failures.append(f"web tool {tool}: enabled in the agent configuration but not called in a live "
                            "turn that named it -- a tool without its key is absent at run time and nobody sees it")
    for action in actions:
        name = action.get("tool_name") or ""
        if _WEB_TOOL.search(name) and not _LINK.search(_output_text(action)):
            failures.append(f"web tool {name}: the call gave no link; its pages cannot be opened by a judge")
    if log_lines is None:
        failures.append("genai log: could not be read, so a plugin that failed to load would go unseen")
    for line in log_lines or []:
        if _PLUGIN_FAILED in line:
            failures.append(f"genai log: {line.strip()[:200]}")
    return failures


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os
    import subprocess

    from .squirro_chat import SquirroChatClient, get_access_token
    from .sweep import _load_dotenv

    parser = argparse.ArgumentParser(description="the pre-flight of the two-arm comparison")
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("--env-file", required=True)
    pre.add_argument("--suffix", default="_SRDEV_CLOUD", help="the .env suffix of the cluster's settings")
    pre.add_argument("--web-agent", required=True)
    pre.add_argument("--modelled-agent", required=True)
    pre.add_argument("--probe", default="Use the tool {tool} to search the web for the FDA approval of sodium "
                                        "thiosulfate against cisplatin ototoxicity, and give the links you used.",
                     help="asked once per enabled web tool; {tool} is the tool's name")
    pre.add_argument("--log-cmd", default="ssh sr-dev-squirro-cloud 'sudo docker logs --since 30m "
                                          "squirro-service-genai 2>&1'")
    args = parser.parse_args(argv)

    _load_dotenv(Path(args.env_file))
    cluster = os.environ["SQUIRRO_CLUSTER" + args.suffix].rstrip("/")
    project = os.environ["SQUIRRO_PROJECT" + args.suffix]
    token = os.environ["SQUIRRO_TOKEN" + args.suffix]
    import requests
    listed = requests.get(f"{cluster}/service/genai/v0/projects/{project}/agents/",
                          headers={"Authorization": f"Bearer {get_access_token(cluster, token)}"},
                          timeout=30).json()
    by_id = {a["id"]: a for a in listed}
    agents = {"web": by_id[args.web_agent], "modelled": by_id[args.modelled_agent]}
    print(f"web agent {agents['web']['name']!r} runs {model_of(agents['web'])!r}; "
          f"modelled agent {agents['modelled']['name']!r} runs {model_of(agents['modelled'])!r}")
    tools = web_tools_of(agents["web"])
    print(f"web tools enabled: {tools}")
    client = SquirroChatClient(cluster, token, project)
    turns = []
    for tool in tools:
        turn = client.ask(args.web_agent, args.probe.format(tool=tool), timeout=600)
        print(f"probe for {tool}: error={turn.error} tools called={sorted(set(turn.calls))}")
        turns.append({"actions": turn.actions})
    import shlex
    log = subprocess.run(shlex.split(args.log_cmd), capture_output=True, text=True, timeout=120)
    log_lines = log.stdout.splitlines() if log.returncode == 0 and log.stdout.strip() else None
    print(f"genai log: {'unreadable' if log_lines is None else f'{len(log_lines)} lines read'}")
    failures = preflight(agents, turns, log_lines)
    for failure in failures:
        print("FAIL:", re.sub(r"[A-Za-z0-9_\-]{32,}", "REDACTED", failure))
    print("pre-flight:", "PASS" if not failures else f"{len(failures)} failures")
    print(web_arm_limit(tools))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
