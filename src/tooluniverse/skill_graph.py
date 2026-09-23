"""A skill's procedure as a process graph, held in data rather than in the model's head.

`next_step` is pure and stateless: given the graph, the step ids already done and the
facts gathered so far, it returns the one step to run now with its tool calls already
filled in. There is no server-side state; the caller passes back what it has done, as
an MCP tool call must.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

# Package data, not deploy/: the image installs only `src`.
GRAPHS_DIR = Path(
    os.environ.get("TU_SKILL_GRAPHS_DIR")
    or Path(__file__).resolve().parent / "data" / "skill_graphs"
)

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class SkillGraphError(RuntimeError):
    """No graph for that skill, or the graph cannot be run with these facts."""


def undeclared_tables(graph: dict) -> list[str]:
    """Collected tables the process does not declare a fact table or an evidence table."""
    declared = graph.get("tables") or {}
    return [name for step in graph.get("steps", []) for name in (step.get("collect") or {})
            if declared.get(name) not in ("fact", "evidence")]


def load_graph(skill: str, graphs_dir: str | Path | None = None) -> dict:
    """Load the process graph for one skill."""
    directory = Path(graphs_dir) if graphs_dir else GRAPHS_DIR
    path = directory / f"{skill}.yaml"
    if not path.is_file():
        available = sorted(p.stem for p in directory.glob("*.yaml")) \
            if directory.is_dir() else []
        raise SkillGraphError(
            f"no process graph for {skill!r}; available: {available}")
    graph = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or not graph.get("steps"):
        raise SkillGraphError(f"graph for {skill!r} has no steps")
    if undeclared := undeclared_tables(graph):
        raise SkillGraphError(
            f"graph for {skill!r} collects {undeclared} without declaring them under `tables:` "
            "as `fact` (the agent gets it whole) or `evidence` (described, then fetched)")
    return graph


def has_graph(skill: str) -> bool:
    return (GRAPHS_DIR / f"{skill}.yaml").is_file()


def graph_directive(skill: str, server_runs: bool = False) -> str:
    """The header prepended to a graphed skill's body, or "" when it has none.

    It states which instructions govern and demotes the prose phases to reference. With
    `server_runs` the server executes the process; the model starts it, answers its
    questions and writes the report.
    """
    if not has_graph(skill):
        return ""
    if server_runs:
        return f"""# THE SERVER RUNS THIS SKILL — do not plan from the phases below
This skill ships its procedure as a Skill Process. The phases further down are
REFERENCE for what each step means; they are not your plan. The server executes
every step and every tool call itself.

1. Bind the inputs from the question and call `run_skill(skill="{skill}",
   inputs={{...}})`. Give EVERY input a value or null: an optional input the
   question names must be bound, and one it does not name is passed as null. If
   it answers `schema_mismatch` or `confirm_inputs`, bind or decline the named
   inputs and call again.
2. While it answers `running` or `waiting`, call `continue_skill(run_id=...)`.
   `running` is progress — tell the user which phase is done. `waiting` carries a
   `question`: answer it with `continue_skill(run_id=..., answer={{...}})` — for a
   `repair`, the named argument mapped to a list of alternative values; for a
   `judge`, each wanted name mapped to your decision; for a `delegate`, make the
   listed `calls` with your own tools (web search, code) and map each wanted name
   to what came back.
3. When it answers `finished`, write the report from `handover` and nothing else.
   `handover.report` is the author's instruction for how to read the evidence and
   `handover.notes` says what each step means: follow both. `handover.facts` is
   what you must cite, whole, each row with its own link. `handover.tables`
   describes what is too wide to hand over; its preview is not the data — read
   the rows you need with `fetch_run_data(run_id=..., table=..., columns=[...])`.
   Every number comes from `handover.facts` or from rows you fetched; state
   `failures`, `blocked`, `unresolved`, `steps_skipped` and `excluded` as gaps.
   Follow the five lines in `handover.write_the_report`.
4. Before you answer the user, hand the whole draft to
   `submit_report(run_id=..., draft=...)`. `accepted`: send it. `revise`: correct
   each named statement and submit once more. `accepted_with_failures`: send it
   with `append_to_report` added at the end.

Do not call `execute_tool` for any step of this skill yourself.

---
"""
    return f"""# RUN THE PROCESS GRAPH — do not plan from the phases below
This skill ships its procedure as a graph. The phases further down are REFERENCE
for what each step means; they are not your plan. Your plan comes one step at a
time from `next_skill_step`, which hands you each call already composed — no tool
names to recall, no arguments to build.

1. `next_skill_step(skill="{skill}", done=[], facts={{...}})` — facts start with
   the entities named in the question (for example the drug).
2. Run EVERY call in `calls` through `execute_tool`, exactly as given.
3. Extract what `produces` names from the results. A name listed under
   `judge` is yours to decide from the case and the facts so far — say it.
4. Call again with that step's `id` appended to `done`, and everything you
   extracted merged into `facts`.
5. Stop when it answers `finished`, then write the report.

Do not skip a step, reorder, or substitute a tool. If a call fails, record the
failure and continue with the next step.

---
"""


def fill(value: Any, facts: dict) -> Any:
    """Substitute {placeholders} from facts; public so a host can compose delegated calls."""
    return _fill(value, facts)


def _fill(value: Any, facts: dict) -> Any:
    """Substitute {placeholders} from facts, naming any that are missing."""
    if isinstance(value, dict):
        return {k: _fill(v, facts) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill(v, facts) for v in value]
    if not isinstance(value, str):
        return value
    missing = [name for name in _PLACEHOLDER.findall(value) if name not in facts]
    if missing:
        raise SkillGraphError(
            f"cannot build the call: missing {', '.join(sorted(set(missing)))}")
    # A lone placeholder keeps its type; embedded ones are string-substituted.
    whole = _PLACEHOLDER.fullmatch(value)
    if whole:
        return facts[whole.group(1)]
    return _PLACEHOLDER.sub(lambda m: str(facts[m.group(1)]), value)


def _vacuous(step: dict, facts: dict) -> bool:
    """A loop over an empty list: nothing to call, and nothing to wait for."""
    loop = step.get("for_each")
    return bool(loop and loop in facts and not facts[loop])


def _nothing_to_loop_over(step: dict, facts: dict) -> bool:
    """A for_each list that never arrived, or arrived empty: no items to call for.

    Broader than `_vacuous` on purpose: unlike the runtime path (`_is_runnable`, which
    must still raise when a loop's list was never produced at all, so the omission is
    not lost), the hand-over has nothing to gain from that distinction -- either way
    there was nothing to loop over, and the report must say so.
    """
    loop = step.get("for_each")
    return bool(loop) and not facts.get(loop)


def _is_runnable(step: dict, done: set[str], facts: dict) -> bool:
    if step["id"] in done:
        return False
    if any(dep not in done for dep in step.get("requires", [])):
        return False
    condition = step.get("when")
    if condition and not facts.get(condition):
        # A gateway: the fact must be present and true.
        return False
    # Nothing to iterate: move on rather than demand a call that cannot be made.
    return not _vacuous(step, facts)


def _expand_calls(step: dict, facts: dict) -> list[dict]:
    """The calls to make now — one per item when the step loops over a list."""
    calls = step.get("calls", [])
    loop = step.get("for_each")
    if not loop:
        return [{"tool": c["tool"], "arguments": _fill(c.get("arguments", {}), facts)}
                for c in calls]
    if loop not in facts:
        raise SkillGraphError(
            f"cannot build the call: missing {loop} (the list this step iterates)")
    variable = step.get("as", "item")
    expanded = []
    for item in facts[loop] or []:
        if item is None:
            continue            # a miss is not an entity: no call is made for it
        scoped = {**facts, variable: item}
        expanded.extend(
            {"tool": c["tool"], "arguments": _fill(c.get("arguments", {}), scoped)}
            for c in calls
        )
    return expanded


def unreadable_items(step: dict, facts: dict) -> int:
    """How many of a loop's items held no value, so no call was made for them."""
    values = facts.get(step.get("for_each")) if step.get("for_each") else None
    return sum(1 for v in values if v is None) if isinstance(values, list) else 0


def delegated_calls(step: dict, facts: dict) -> list[dict]:
    """The calls the agent makes itself for this step, one per item when the step loops.

    Composed exactly like the server's own calls, so nothing is added beyond the filled arguments.
    """
    return _expand_calls({**step, "calls": step.get("delegate") or []}, facts)


_PRODUCING_KEYS = ("extract", "collect", "combine", "compute", "derive")


def _produces(step: dict, name: str) -> bool:
    return (name in (step.get("produces") or []) or name in (step.get("judge") or [])
            or any(name in (step.get(key) or {}) for key in _PRODUCING_KEYS))


def _gate_is_closed(graph: dict, step: dict, done: set[str], facts: dict) -> bool:
    """A gateway that will not open: its fact is false, or nothing is left that could set it."""
    name = step.get("when")
    if not name:
        return False
    if name in facts:
        return not facts[name]
    return all(s["id"] in done for s in graph["steps"] if _produces(s, name))


def _settled(graph: dict, done: set[str], facts: dict) -> set[str]:
    """`done`, plus every step behind a closed gateway whose requirements are met.

    Closing one gate can meet another step's requirements, so this runs to a fixpoint.
    """
    done = set(done)
    while True:
        closed = {s["id"] for s in graph["steps"]
                  if s["id"] not in done
                  and all(dep in done for dep in s.get("requires", []))
                  and _gate_is_closed(graph, s, done, facts)}
        if not closed:
            return done
        done |= closed


def skipped_gates(graph: dict, done: list[str], facts: dict) -> list[dict]:
    """Steps that did not run: a closed gateway, or a for_each with nothing to loop over.

    `decided` is a gate-skip key only: True when the gate's fact arrived and was
    rejected, False when it never arrived at all -- the gate was never decided, not
    closed on evidence. An empty loop had no condition to decide, so it is reported
    with `reason` instead, never `decided`, and that reason separates a list that came
    back empty from one that never arrived. A step that is both gated and looping is
    reported for its gate -- the gate is the reason nothing ran, the empty loop only
    a symptom of the same closed gate.
    """
    ran = set(done or [])
    facts = facts or {}
    gate_settled = _settled(graph, ran, facts)
    empty_loops = {s["id"] for s in graph["steps"] if _nothing_to_loop_over(s, facts)}
    settled = _settled(graph, ran | empty_loops, facts)
    out = []
    for s in graph["steps"]:
        sid = s["id"]
        if sid in ran or sid not in settled:
            continue
        if sid in empty_loops and sid not in gate_settled:
            loop = s["for_each"]
            # "The list came back empty" and "the list never arrived" are different gaps;
            # saying "empty" for both asserts a read that never happened.
            out.append({"step": sid, "reason": f"nothing to loop over: {loop} was empty"
                        if loop in facts else
                        f"nothing to loop over: {loop} was never produced"})
        elif s.get("when"):
            out.append({"step": sid, "gate": s["when"], "decided": s["when"] in facts})
    return out


def stalled_steps(graph: dict, done: list[str], facts: dict) -> list[dict]:
    """Steps that never ran and were not skipped, each with the requirements it still waited for."""
    facts = facts or {}
    settled = _settled(graph, set(done or []) | {
        s["id"] for s in graph["steps"] if _nothing_to_loop_over(s, facts)}, facts)
    return [{"step": s["id"],
             "waiting_for": [dep for dep in s.get("requires", []) if dep not in settled]}
            for s in graph["steps"] if s["id"] not in settled]


def next_step(graph: dict, done: list[str], facts: dict) -> dict | None:
    """The one step to run now, or None when the procedure is finished.

    Steps are offered in declaration order, so the graph reads top to bottom like the
    body it replaces. Skipping a closed gateway must never stall the procedure.
    """
    facts = facts or {}
    # A loop with nothing to iterate counts as done, so its dependants are not left waiting.
    done_set = _settled(graph, set(done or []) | {
        s["id"] for s in graph["steps"] if _vacuous(s, facts)}, facts)
    for step in graph["steps"]:
        if not _is_runnable(step, done_set, facts):
            continue
        try:
            calls = _expand_calls(step, facts)
        except SkillGraphError as exc:
            exc.step = step["id"]   # the step that cannot be built is the one to blame
            raise
        unreadable = unreadable_items(step, facts)
        return {
            "id": step["id"],
            "label": step.get("label", step["id"]),
            "calls": calls,
            **({"unreadable_items": unreadable} if unreadable else {}),
            "produces": step.get("produces", []),
            "judge": step.get("judge", []),
            "notes": step.get("notes"),
            "remaining": sum(
                1 for s in graph["steps"]
                if s["id"] not in done_set and s["id"] != step["id"]
                and (not s.get("when") or facts.get(s.get("when")))
            ),
        }
    return None
