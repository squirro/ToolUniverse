"""Run a skill's process graph SERVER-SIDE — the Novartis navigator, ported.

The Novartis PoC did not make an LLM obedient; it kept the LLM out of the control
loop. A Python `ProcessNavigator` walked the BBO graph, `SessionState` held the
state, `_gw_*` predicates chose each branch from state the code had computed, and
`_action_*` functions performed the work. Nothing was asked to choose, so nothing
drifted.

Our first port moved the PLAN out of the model and left the RUNTIME with it: the
model had to decide to start, carry `done` and `facts` between calls, report the
values gateways branch on, and choose to make each call. Measured on sr-dev, it
executed that loop faithfully when it entered it (nine steps, in order, four calls
where four were offered) but failed to enter it on two runs of three, and
abandoned it after seven of nine steps on another.

This module closes that gap. It holds the run state, executes each step's calls
itself, extracts the values the next step needs, and evaluates gateways from the
REAL results. The model's remaining jobs are choosing the skill and writing the
report.

`execute` is injected — SMCP passes the in-process ToolUniverse (ExecuteTool is
already constructed with `tooluniverse=self`), and tests pass a stub. State is an
in-memory dict. The step logic — `absorb`, `resolved`, `substitute`, `apply`,
`trim` — is module-level and pure, so a durable host (Temporal, ADR-0016) can
await the calls itself and hand the results to the same functions; this class is
the synchronous driver over them.
"""
from __future__ import annotations

import json
import math
import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .skill_graph import (
    SkillGraphError,
    _fill,
    _produces,
    delegated_calls,
    next_step,
    skipped_gates,
    stalled_steps,
)
from .skill_ontology_placing import place
from .skill_working_record import WorkingRecord

_OPS: dict[str, Callable[[Any, Any], bool]] = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _dig(payload: Any, path: str) -> Any:
    """Follow a dotted path into a result, returning None rather than raising.

    Deliberately not JSONPath: a boring, declarative accessor is what keeps the
    extraction reviewable, and a miss surfaces as a named missing fact at the next
    step rather than a crash.

    One form beyond dots: a segment ending ``[]`` maps over a list, so
    ``result[].term`` turns FAERS's [{term, count}, ...] into the term strings the
    next step must pass back VERBATIM — MedDRA is case- and spelling-strict, and
    the prose body spends five lines asking the model not to retype them.
    """
    current: Any = payload
    mapping = False
    for part in path.split("."):
        mapped = part.endswith("[]")
        key = part[:-2] if mapped else part
        if key:
            current = _step_in(current, key, mapping)
            if current is None:
                return None
        if mapped:
            if mapping:
                return None                    # nested mapping is out of scope
            if not isinstance(current, list):
                return None
            mapping = True
    return current


def _step_in(current: Any, key: str, mapping: bool) -> Any:
    """Take one path segment, over a single value or over every mapped item."""
    if mapping:
        if not isinstance(current, list):
            return None
        out = [_step_in(item, key, False) for item in current]
        return [value for value in out if value is not None]
    if isinstance(current, dict):
        return current.get(key)
    if isinstance(current, list) and key.isdigit():
        return current[int(key)] if int(key) < len(current) else None
    return None


# --- compute: arithmetic over rows the run holds --------------------------------

_PREVALENCE_TIERS = (">1 / 1000", "1-5 / 10 000", "6-9 / 10 000", "1-9 / 100 000",
                     "1-9 / 1 000 000", "<1 / 1 000 000")   # commonest first, Orphanet's classes
_UNKNOWN_TIER_POSITION = 4.5      # below every counted class, above the rarest-of-the-rare


def _prevalence_tier(classes: list[str]) -> tuple[str, float]:
    """The class most of Orphanet's entries agree on, and its position.

    Orphanet lists one estimate per study and region; a single outlier must not
    crown a disease (live: one 1-5/10 000 among five 1-in-a-million entries).
    Ties go to the commoner class; no counted class at all is "unknown".
    """
    known = [c for c in classes or [] if c in _PREVALENCE_TIERS]
    if not known:
        return "unknown", _UNKNOWN_TIER_POSITION
    counts = {c: known.count(c) for c in set(known)}
    best = min(counts, key=lambda c: (-counts[c], _PREVALENCE_TIERS.index(c)))
    return best, float(_PREVALENCE_TIERS.index(best))


def _rank_differential(rule: dict, facts: dict) -> list[dict] | None:
    """Order candidates the way a clinician does: age fit, then how common, then fit.

    Onset: a disease whose every onset class is later than the patient goes below
    every disease that fits; no patient age means onset is not assessed. Prevalence:
    Orphanet's class, commonest first, unknown in the middle. Overlap: last key.
    """
    overlap = facts.get(rule["overlap"])
    if overlap is None:
        return None
    age = facts.get(rule.get("patient_age_years", ""))
    onset_by = {str(r.get("orpha_code")): r.get("average_age_of_onset") or []
                for r in facts.get(rule.get("inheritance", ""), []) or []}
    prev_by = {str(r.get("orpha_code")): r.get("classes") or []
               for r in facts.get(rule.get("epidemiology", ""), []) or []}
    early, late = set(rule.get("early_onset", [])), set(rule.get("late_onset", []))
    # The gate: a candidate must carry the discriminating phenotypes the run
    # computed to rank above candidates that do. Without it the commonest disease
    # matching the NON-discriminating phenotypes floats to the top (Sotos, which
    # Orphanet lists no hepatosplenomegaly for, above every storage disease).
    pair = facts.get(rule.get("must_carry", "")) or []
    ids_by = {str(r.get("orpha_code")): set(r.get("hpo_ids") or [])
              for r in facts.get(rule.get("rows_ids", ""), []) or []}
    hier = _hierarchy(rule, facts)
    out = []
    for row in overlap:
        code = str(row.get("orpha_code"))
        if not pair:
            carried, gate_key = "not assessed (no discriminating pair)", 0
        else:
            n_carried = sum(1 for p in pair if carries(p, ids_by.get(code, set()), hier))
            carried = "both" if n_carried == len(pair) else f"{n_carried} of {len(pair)}"
            gate_key = len(pair) - n_carried
        onsets = onset_by.get(code, [])
        if age is None:
            fit, fit_key = "not assessed (no patient age)", 0
        elif onsets and all(o in late for o in onsets):
            fit, fit_key = "later than patient", 1
        elif onsets and any(o in early for o in onsets):
            fit, fit_key = "fits", 0
        else:
            fit, fit_key = "unknown onset", 0
        tier, tier_key = _prevalence_tier(prev_by.get(code, []))
        pct = float(row.get("overlap_pct") or 0)
        # A candidate that matches nothing goes to the bottom of its onset band:
        # prevalence orders the diseases that fit at all, it does not rescue one.
        out.append({**row, "onset": onsets, "onset_fit": fit, "prevalence_tier": tier,
                    "carries_discriminating": carried,
                    "_key": (fit_key, gate_key, 0 if pct > 0 else 1, tier_key, -pct)})
    out.sort(key=lambda r: (r["_key"], str(r.get("preferred_term"))))
    for i, r in enumerate(out, 1):
        r.pop("_key")
        r["rank"] = i
    return out


def carries(term: str, disease_ids: set, hierarchy: dict) -> bool:
    """Does a disease's annotation carry a case phenotype?

    Yes if it lists the term itself, or ALL of the term's parents (HPO composes
    Hepatosplenomegaly from Hepatomegaly and Splenomegaly), or any child (a
    generalized seizure is a seizure). Ontological, from rows the run fetched;
    with no hierarchy row for the term, exact match only.
    """
    if term in disease_ids:
        return True
    h = hierarchy.get(term) or {}
    parents = h.get("parents") or []
    # Two or more parents all present is the conjunction the term names; a lone
    # parent is a broader term and does not stand for it.
    if len(parents) >= 2 and all(p in disease_ids for p in parents):
        return True
    return any(c in disease_ids for c in (h.get("children") or []))


def _hierarchy(rule: dict, facts: dict) -> dict:
    rows = facts.get(rule.get("hierarchy", ""), []) or []
    return {str(r.get("hpo_id")): r for r in rows}


def _overlap(rule: dict, facts: dict) -> list[dict] | None:
    """Per row: how many of the case's ids it carries, and the grade that earns.

    Grades are the author's rubric in the YAML, first match wins; `needs_gene`
    holds a grade back unless a gene row for the same code lists a gene.
    """
    rows, against = facts.get(rule["rows"]), facts.get(rule["against"])
    if rows is None or against is None:
        return None
    case = list(dict.fromkeys(against))
    gene_rows = facts.get(rule.get("gene_rows", ""), []) or []
    has_gene = {str(g.get("orpha_code")) for g in gene_rows if g.get("genes")}
    hier = _hierarchy(rule, facts)
    out = []
    for row in rows:
        ids = set(row.get(rule["row_ids"]) or [])
        matched = [i for i in case if carries(i, ids, hier)]
        pct = round(100 * len(matched) / len(case)) if case else 0
        grade = None
        for g in rule.get("grades", []):
            if pct >= g.get("min_pct", 0) and (not g.get("needs_gene")
                                               or str(row.get("orpha_code")) in has_gene):
                grade = g["grade"]
                break
        out.append({"orpha_code": row.get("orpha_code"), "preferred_term": row.get("preferred_term"),
                    "n": len(matched), "N": len(case), "overlap_pct": pct, "grade": grade,
                    "matched_hpo_ids": matched})
    out.sort(key=lambda r: (-r["overlap_pct"], str(r["preferred_term"])))
    return out


def _fewest(rule: dict, facts: dict) -> list | None:
    """The `take` ids whose count is smallest; None (unresolved) when the cut ties.

    Which phenotypes discriminate is "which are annotated to the fewest
    diseases" — arithmetic. A tie exactly at the cut is the one case left to the
    model, which is asked because the name stays unresolved.
    """
    rows = facts.get(rule["rows"])
    if rows is None:
        return None
    take = int(rule.get("take", 2))
    seen: dict = {}
    for row in rows:
        value = row.get(rule["count"])
        size = len(value) if isinstance(value, (list, dict)) else value
        ident = row.get(rule["id"])
        if size is not None and ident not in seen:        # two symptoms on one term are one phenotype
            seen[ident] = size
    sized = [(size, ident) for ident, size in seen.items()]
    if len(sized) < take:
        return None
    sized.sort(key=lambda t: (t[0], str(t[1])))
    if len(sized) > take and sized[take - 1][0] == sized[take][0]:
        return None                                   # a tie at the cut: the model breaks it
    return [ident for _, ident in sized[:take]]


def loop_items(spec: dict, calls: list[dict]) -> list | None:
    """The loop value each expanded call was made for, in call order."""
    loop, var = spec.get("for_each"), spec.get("as", "item")
    if not loop:
        return None
    marker = "{" + var + "}"
    templates = (spec.get("calls") or [{}])[0].get("arguments", {})
    items = []
    for call in calls:
        # The filled argument whose template was the loop variable carries the item;
        # failing that, the one whose template contained it (PubMed has one `query`,
        # so the reaction rides inside it beside the drug name).
        found = None
        filled = call.get("arguments", {})
        for name, tmpl in templates.items():
            if tmpl == marker:
                found = filled.get(name)
                break
            if isinstance(tmpl, str) and marker in tmpl and isinstance(filled.get(name), str):
                found = _item_in(tmpl, marker, filled[name])
                if found is not None:
                    break
        items.append(found)
    return items


def _item_in(template: str, marker: str, text: str) -> str | None:
    """The loop value inside a filled argument whose template also carried other
    placeholders: the marker becomes the capture, every other placeholder a wildcard."""
    pattern = re.escape(template).replace(re.escape(marker), "(?P<item>.+?)", 1)
    pattern = re.sub(r"\\\{[A-Za-z_][A-Za-z0-9_]*\\\}", ".+?", pattern)
    match = re.fullmatch(pattern, text, flags=re.S)
    return match.group("item") if match else None


def _hierarchy_rows(rule: dict, facts: dict) -> list[dict] | None:
    """Fold the per-call hierarchy rows (parents call, children call, per term) into
    one row per term: {hpo_id, parents, children}."""
    rows = facts.get(rule["rows"])
    if rows is None:
        return None
    by: dict[str, dict] = {}
    for r in rows:
        t = str(r.get("hpo_id"))
        entry = by.setdefault(t, {"hpo_id": t, "parents": [], "children": []})
        key = "parents" if r.get("direction") == "parents" else "children"
        entry[key] = [i for i in (r.get("ids") or []) if i]
    return list(by.values())


def _flag(rule: dict, facts: dict) -> list[dict] | None:
    """The rows ordered by one numeric field, largest first, each marked whether it
    reaches the threshold. A PRR signal table is this and nothing more."""
    rows = facts.get(rule["rows"])
    if rows is None:
        return None
    field, threshold = rule["field"], float(rule.get("threshold", 0))

    def value(row):
        try:
            return float(row.get(field))
        except (TypeError, ValueError):
            return None

    out = [{**row, "flagged": value(row) is not None and value(row) >= threshold} for row in rows]
    out.sort(key=lambda r: (value(r) is None, -(value(r) or 0.0)))
    return out


def _pluck(rule: dict, facts: dict) -> list | None:
    """One field from every row, or only from the rows whose `where` field is true;
    values matching `exclude_pattern` are set aside (see `_pluck_excluded`)."""
    picked = _pluck_all(rule, facts)
    if picked is None:
        return None
    pattern = rule.get("exclude_pattern")
    return [v for v in picked if not (pattern and re.search(pattern, str(v), re.I))]


def _pluck_excluded(rule: dict, facts: dict) -> list:
    """The values `_pluck` set aside — recorded so the report can say so."""
    picked = _pluck_all(rule, facts) or []
    pattern = rule.get("exclude_pattern")
    return [v for v in picked if pattern and re.search(pattern, str(v), re.I)]


def _pluck_all(rule: dict, facts: dict) -> list | None:
    rows = facts.get(rule["rows"])
    if rows is None:
        return None
    where = rule.get("where")
    return [row.get(rule["field"]) for row in rows
            if (row.get(where) if where else True) and row.get(rule["field"]) is not None]


_COMPUTE_OPS: dict[str, Callable[[dict, dict], Any]] = {"rank_differential": _rank_differential,
                                                       "overlap": _overlap, "fewest": _fewest,
                                                       "hierarchy": _hierarchy_rows,
                                                       "flag": _flag, "pluck": _pluck}


def _compute(rule: dict, facts: dict) -> Any:
    """One named operation over facts; None when a source fact never arrived."""
    op = _COMPUTE_OPS.get(rule.get("op"))
    if op is None:
        raise SkillGraphError(f"unknown compute op {rule.get('op')!r}")
    return op(rule, facts)


def _derive(spec: dict, facts: dict) -> bool | None:
    """A gateway condition computed from data, not asserted by the model.

    None means UNKNOWN: the source fact never arrived, so there is nothing to
    decide on. Live on enzalutamide the `signals` extraction missed, the rule
    derived over an empty list, and the branch was skipped as though the data had
    said "no strong signal" — a silent wrong answer. A genuine empty result is
    still False; only an ABSENT fact is unknown.
    """
    if spec["from"] not in facts:
        return None
    rows = facts.get(spec["from"]) or []
    field, op, value = spec.get("field"), spec.get("op", "=="), spec.get("value")
    compare = _OPS[op]
    hits = []
    for row in rows:
        seen = row.get(field) if isinstance(row, dict) else row
        if seen is None:
            continue
        try:
            hits.append(compare(seen, value))
        except TypeError:
            continue
    return all(hits) if spec.get("mode") == "all" else any(hits)



MAX_PAYLOAD = 12_000   # per fact in a question's context; the question stays readable


def new_run(inputs: dict) -> dict:
    """Fresh run state: the whole of it is (done, facts) plus what went wrong."""
    return {"facts": dict(inputs), "done": [], "failures": [], "blocked": [],
            "skipped": [], "calls": {}, "calls_made": {},
            "questions": [], "unresolved": [], "excluded": {}}


_SERVER_ERROR_TYPES = ("ServerError", "UpstreamServiceError", "Timeout", "ConnectionError")


def is_upstream_failure(result: Any) -> bool:
    """A result that reports the SOURCE failed, not that it had nothing to say.

    A `status: error` is an answer when the source says "not found"; it is a failure when
    the source was unreachable, refused, or broke -- a retriable error, a server error type,
    or an HTTP status of 5xx/408/429 carried in the envelope.
    """
    if not isinstance(result, dict) or result.get("status") != "error":
        return False
    details = result.get("error_details") or {}
    status = result.get("upstream_status")
    return bool(details.get("retriable") or result.get("retryable")
                or any(t in str(details.get("type", "")) for t in _SERVER_ERROR_TYPES)
                or (isinstance(status, int) and (status >= 500 or status in (408, 429))))


def upstream_failure_text(result: dict) -> str:
    error = result.get("error")
    return f"UpstreamFailure: {error if isinstance(error, str) else json.dumps(error, default=str)}"


def apply(run: dict, step_id: str, failures: list, outcome: dict,
          calls: list[dict] | None = None) -> None:
    """Record a finished step on the run. Pure over its arguments; mutates `run`.

    Results are not among them: they are in the Working Record.
    """
    # The tools this step ran, retries included: the agent's own trace never
    # shows them, so the bundle carries the record itself.
    run["calls"][step_id] = [c["tool"] for c in (calls or [])]
    # …and with their arguments, for the Run Record: which reaction, which code.
    run["calls_made"][step_id] = [{"tool": c["tool"], "arguments": c.get("arguments", {})}
                                  for c in (calls or [])]
    run["done"].append(step_id)
    run["failures"].extend({**f, "step": f.get("step", step_id)} for f in failures)
    run["facts"].update(outcome["facts"])
    run["blocked"].extend(outcome["blocked"])
    if outcome.get("excluded"):
        run["excluded"][step_id] = outcome["excluded"]
    run["unresolved"].extend({"step": step_id, "fact": name}
                             for name in outcome["unresolved"])


_MISSING = re.compile(r"missing (\w+)")


def _with_cause(graph: dict, run: dict, reason: str) -> str:
    """A step blocked on a missing fact names the failed call that should have produced it."""
    match = _MISSING.search(reason)
    if not match:
        return reason
    producers = {s["id"] for s in graph["steps"] if _produces(s, match.group(1))}
    causes = [f"{f['tool']}: {f['error']}" for f in run.get("failures", [])
              if f.get("step") in producers]
    if not causes:
        return reason
    return f"{reason} -- {', '.join(sorted(producers))} failed: {'; '.join(causes)}"


def next_runnable(graph: dict, run: dict) -> dict | None:
    """The step to run now, marking any step that cannot be built as blocked.

    Loops, because skipping one blocked step can reveal another. A step we
    cannot build is BLOCKED, not fatal: live, a missed FAERS extraction killed a
    ten-step run at step four, and the other four sources did not depend on it.
    """
    while True:
        try:
            return next_step(graph, done=run["done"] + run["skipped"],
                             facts=run["facts"])
        except SkillGraphError as exc:
            blocked = getattr(exc, "step", None) or next(
                (s["id"] for s in graph["steps"]
                 if s["id"] not in run["done"] and s["id"] not in run["skipped"]
                 and all(d in run["done"] for d in s.get("requires", []))),
                None)
            if blocked is None:
                return None
            run["skipped"].append(blocked)
            run["blocked"].append({"step": blocked, "reason": _with_cause(graph, run, str(exc))})


# The same five lines for every skill. The report's structure is the skill's; this is not.
WRITE_THE_REPORT = [
    "Take every number from its row and cite it with that row's own link.",
    "State a finding only from a source you read: an abstract, a page, a row -- never from a "
    "title alone.",
    "Wherever this run holds less than the source, say both numbers: how much the source holds "
    "(source_total) and how much you read of it.",
    "A number published in a paper or a page stands beside a number this run computed, each "
    "with its source and period; never merge the two.",
    "State what failed, what was not found and what was set aside, from failures, blocked, "
    "unresolved and excluded.",
]


def handover_of(graph: dict, run: dict) -> dict:
    """What the agent is handed ONCE at the end: the facts, and a description of each table
    that is too wide to hand over. Tool results are in the Working Record, fetched by table."""
    handed = {
        "skill": graph["skill"],
        "facts": run["facts"],
        "steps_done": run["done"],
        "steps_skipped": skipped_gates(graph, run["done"] + run["skipped"], run["facts"]),
        "calls": run.get("calls", {}),
        # The author's judgement, with the data: what each step means and how the
        # report must read the evidence. Blind-judged 2026-09-03, the reports that
        # lacked this printed FAERS coding noise as signals.
        "notes": {s["id"]: s["notes"] for s in graph["steps"]
                  if s.get("notes") and s["id"] in run["done"]},
        "report": graph.get("report"),
        "write_the_report": WRITE_THE_REPORT,
        "excluded": run.get("excluded", {}),
        "failures": run["failures"],
        "blocked": run["blocked"],
        "unresolved": run["unresolved"],
    }
    if run.get("evidence"):
        handed["tables"] = run["evidence"]
    mappings = [name for step in graph["steps"] for name in (step.get("mapping") or {})
                if name in run["facts"]]
    if mappings:
        handed["mappings"] = mappings
    if stalled := stalled_steps(graph, run["done"] + run["skipped"], run["facts"]):
        handed["stalled"] = stalled
    return handed


# --- mapping: the user's words onto the source's own vocabulary, judged, checked, placed ----
#
# The check proves membership, not meaning: live, "ototoxicity" was mapped onto DIZZINESS and
# FALL and both were accepted because both are FAERS terms. So the mapping is a fact table the
# report must show, each row with the agent's reason and a placing from an ontology.

def mapping_choices(spec: dict, facts: dict) -> dict | None:
    """The source's terms a mapping may use, whole: the agent copies from this list, so it
    travels in the question even when the rows it comes from are too wide to show."""
    choices = {name: _picked(rule["onto"], facts) for name, rule in (spec.get("mapping") or {}).items()}
    choices = {name: terms for name, terms in choices.items() if terms}
    return choices or None


def mapping_problem(spec: dict, outcome: dict, facts: dict) -> str | None:
    """A mapped term the source does not list, or a row without the shape asked for."""
    for name, rule in (spec.get("mapping") or {}).items():
        rows = outcome["facts"].get(name)
        if rows is None:
            continue
        if not isinstance(rows, list) or not all(isinstance(r, dict) and "term" in r for r in rows):
            return (f"{name} must be a list of rows {{of, term, reason, concept}}, one per mapped "
                    f"term; got {json.dumps(rows, default=str)[:120]}")
        allowed = _picked(rule["onto"], {**facts, **outcome["facts"]})
        if allowed is None:
            return f"{rule['onto']['rows']} is not a list of rows"
        stray = [r["term"] for r in rows if not any(_same(r["term"], a) for a in allowed)]
        if stray:
            return (f"{name}: not in {rule['onto']['rows']}.{rule['onto']['field']}: {stray} -- "
                    "copy each term exactly as the source lists it, or leave it out")
    return None


def placed_mapping(spec: dict, outcome: dict, lookup: Callable[[str], dict] | None) -> dict:
    """Each mapped row gets its placing; the flat list of terms is kept for the steps that loop."""
    facts = dict(outcome["facts"])
    for name in (spec.get("mapping") or {}):
        rows = facts.get(name)
        if not isinstance(rows, list):
            continue
        placed = []
        for row in rows:
            verdict = (place(lookup(row["term"]), row.get("concept") or []) if lookup
                       else {"placing": "unknown", "ontology": None, "term": None,
                             "label": None, "under": None})
            placed.append({**row, **{k: verdict.get(k) for k in
                                     ("placing", "ontology", "under")},
                           "ontology_term": verdict.get("term"), "ontology_label": verdict.get("label")})
        facts[name] = placed
        facts[f"{name}_terms"] = list(dict.fromkeys(r["term"] for r in placed))
    return {**outcome, "facts": facts}


def keep_evidence(record: WorkingRecord, tables: dict | None, outcome: dict) -> list[dict]:
    """Move what the process declares an evidence table out of the facts, into the record."""
    described = []
    for name in [n for n in outcome["facts"] if (tables or {}).get(n) == "evidence"]:
        record.put_table(name, outcome["facts"].pop(name))
        described.append(record.describe(name))
    return described


def source_total(spec: dict, results: list, items: list | None) -> Any:
    """How much the source holds for this step's calls, by the path the step declares.

    One number for a single call, one per loop item for a loop; "unknown" when the step
    declares no `total` or the source gave none. The reader sees the narrowing either way.
    """
    path = spec.get("total")
    if not path:
        return "unknown"
    found = [_dig(payload, path) for payload in results]
    if items and len(items) == len(found):
        return {str(item): (total if total is not None else "unknown")
                for item, total in zip(items, found)}
    return found[0] if found and found[0] is not None else "unknown"


def absorb_recorded(record: WorkingRecord, tables: dict | None, spec: dict,
                    calls: list[dict], facts: dict) -> dict:
    """`absorb` over the step's recorded results, so no result has to travel to the caller."""
    results = record.results(spec["id"])
    outcome = absorb(spec, results, facts, items=loop_items(spec, calls), calls=calls)
    outcome["evidence"] = keep_evidence(record, tables, outcome)
    if results:
        described = record.describe(f"results.{spec['id']}")
        described["source_total"] = source_total(spec, results, loop_items(spec, calls))
        outcome["evidence"].append(described)
    repair = spec.get("repair")
    outcome["resolved"] = resolved(spec, repair, results) if repair else True
    return outcome


def resolved(spec: dict, repair: dict, results: list) -> bool:
    """Did the value this step exists to produce actually arrive?"""
    wanted = repair["when_missing"]
    rule = (spec.get("extract") or {}).get(wanted)
    path = rule["path"] if isinstance(rule, dict) else rule
    return any(_dig(payload, path) is not None for payload in results)


def substitute(calls: list[dict], argument: str, candidate: Any) -> list[dict]:
    """The same calls with one argument swapped, wherever a call carries it."""
    out = []
    for call in calls:
        arguments = dict(call["arguments"])
        if argument in arguments:
            arguments[argument] = candidate
        out.append({**call, "arguments": arguments})
    return out


def question_for(step_id: str, kind: str, wants: list[str], context: dict, **detail) -> dict:
    """The one question shape the model is asked mid-run: repair, judgement or delegation.

    The step's notes ride along when it has any — they say what shape the answer
    should take, and an agent that never saw them answered a web search with bare
    URLs where the author had asked for title, url and snippet.
    """
    return {"kind": kind, "step": step_id, "wants": list(wants),
            "context": _readable(context, detail.get("calls") or []),
            **{k: v for k, v in detail.items() if v is not None}}


def _readable(facts: dict, calls: list[dict]) -> dict:
    """The facts a question shows the model: a fact larger than one payload cap
    is stubbed — twenty Open Targets rows are in the bundle, not for judging.

    The stub says where the value is. Live 2026-09-07 a stub that only said
    "in the bundle" made the model transcribe an empty list into its code,
    though the same rows travelled whole in the question's own calls.
    """
    carried = json.dumps([c.get("arguments") for c in calls], default=str)
    out = {}
    for name, value in facts.items():
        text = json.dumps(value, default=str)
        if len(text) > MAX_PAYLOAD:
            what = f"{len(value)} items" if isinstance(value, (list, dict)) else f"{len(str(value))} chars"
            where = ("passed whole in this question's calls, and in the bundle"
                     if text in carried else "in the bundle")
            out[name] = {"omitted": f"{what} — {where}"}
        else:
            out[name] = value
    return out


def asked(run: dict, question: dict, answer: dict | None) -> None:
    """Remember a question and its answer — never its context, which is payload."""
    run["questions"].append({"step": question["step"], "kind": question["kind"],
                             "wants": list(question["wants"]), "answer": answer})


def judged(outcome: dict, wants: list[str], answer: dict | None) -> dict:
    """Fold the model's answer to a judgement into a step outcome.

    Only the names the step declared are taken; a declared name the model did
    not answer is unresolved, like an extraction that never arrived.
    """
    answer = answer or {}
    facts = {**outcome["facts"],
             **{name: answer[name] for name in wants if name in answer}}
    # A name a compute left unresolved (a tie at the cut) and the model then
    # supplied is resolved; only names nobody answered stay on the list.
    unresolved = ([n for n in outcome["unresolved"] if n not in answer]
                  + [n for n in wants if n not in answer])
    return {**outcome, "facts": facts, "unresolved": unresolved}


# --- check: a model answer is verified against the rows before it becomes a fact ---
#
# The server cannot make the agent use a tool; it can refuse an answer that does
# not hold against the data the run already has. Seven closed kinds, each over a
# produced fact: rows_of, sorted_by, flag, subset_of, covers, excludes, only.

def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    return a == b


def _check_rows_of(source_name: str, value: Any, facts: dict) -> str | None:
    """Every row came from the source, with its fields untouched; none dropped."""
    source = facts.get(source_name)
    if not isinstance(source, list):
        return f"{source_name} is not a list of rows"
    if not isinstance(value, list) or not all(isinstance(r, dict) for r in value):
        return "not a list of rows"
    if len(value) != len(source):
        return f"{len(value)} rows against {len(source)} in {source_name}"
    pool = [r for r in source if isinstance(r, dict)]
    for row in value:
        hit = next((i for i, src in enumerate(pool)
                    if all(k in row and _same(row[k], src[k]) for k in src)), None)
        if hit is None:
            return f"row not in {source_name}: {json.dumps(row, default=str)[:160]}"
        pool.pop(hit)
    return None


def _check_sorted_by(rule: dict, value: Any, facts: dict) -> str | None:
    field, order = rule["field"], rule.get("order", "desc")
    previous, seen_missing = None, False
    for row in value if isinstance(value, list) else []:
        n = _num(row.get(field)) if isinstance(row, dict) else None
        if n is None:
            seen_missing = True
            continue
        if seen_missing:
            return f"a row with {field} follows a row without it"
        if previous is not None and (n > previous if order == "desc" else n < previous):
            return f"{field} not in {order} order: {n} after {previous}"
        previous = n
    return None


def _check_flag(rule: dict, value: Any, facts: dict) -> str | None:
    field, on, compare, threshold = rule["field"], rule["from"], _OPS[rule.get("op", ">=")], rule["value"]
    for row in value if isinstance(value, list) else []:
        if not isinstance(row, dict):
            return f"a row is not an object: {json.dumps(row, default=str)[:80]}"
        n = _num(row.get(on))
        expected = n is not None and compare(n, threshold)
        if bool(row.get(field)) != expected:
            return f"{field}={row.get(field)} with {on}={row.get(on)} in {json.dumps(row, default=str)[:120]}"
    return None


def _picked(rule: dict, facts: dict) -> list | None:
    rows = facts.get(rule["rows"])
    if not isinstance(rows, list):
        return None
    where = rule.get("where")
    return [r.get(rule["field"]) for r in rows if isinstance(r, dict)
            and (not where or r.get(where)) and r.get(rule["field"]) is not None]


def _check_subset_of(rule: dict, value: Any, facts: dict) -> str | None:
    allowed = _picked(rule, facts)
    if allowed is None:
        return f"{rule['rows']} is not a list of rows"
    stray = [v for v in (value if isinstance(value, list) else [value])
             if not any(_same(v, a) for a in allowed)]
    return f"not in {rule['rows']}.{rule['field']}: {stray}" if stray else None


def _check_covers(rule: dict, value: Any, facts: dict) -> str | None:
    """Together with the named lists, the value accounts for every picked row."""
    wanted = _picked(rule, facts)
    if wanted is None:
        return f"{rule['rows']} is not a list of rows"
    have = list(value if isinstance(value, list) else [])
    for name in rule.get("together_with", []):
        have.extend(facts.get(name) or [])
    missing = [w for w in wanted if not any(_same(w, h) for h in have)]
    return f"missing from {rule['rows']}.{rule['field']}: {missing}" if missing else None


def _check_excludes(pattern: str, value: Any, facts: dict) -> str | None:
    hits = [v for v in (value if isinstance(value, list) else [value]) if re.search(pattern, str(v), re.I)]
    return f"matches {pattern}: {hits}" if hits else None


def _check_only(pattern: str, value: Any, facts: dict) -> str | None:
    misses = [v for v in (value if isinstance(value, list) else [value]) if not re.search(pattern, str(v), re.I)]
    return f"does not match {pattern}: {misses}" if misses else None


def _check_not_in(name: str, value: Any, facts: dict) -> str | None:
    """No item of the value is in the named list of terms (a judged mapping's `_terms`)."""
    listed = facts.get(name) or []
    hits = [v for v in (value if isinstance(value, list) else [value])
            if any(_same(v, t) for t in listed)]
    return f"in {name}: {hits}" if hits else None


def _check_only_in(name: str, value: Any, facts: dict) -> str | None:
    """Every item of the value is in the named list of terms."""
    listed = facts.get(name) or []
    misses = [v for v in (value if isinstance(value, list) else [value])
              if not any(_same(v, t) for t in listed)]
    return f"not in {name}: {misses}" if misses else None


def _check_selected_from(rule: dict, value: Any, facts: dict) -> str | None:
    """A selection the code tool made: every row from the table, every row meeting the
    condition, and no row of the table that meets it left out. The first breach is named."""
    table = facts.get(rule["table"])
    if not isinstance(table, list):
        return f"{rule['table']} is not a list of rows"
    if not isinstance(value, list) or not all(isinstance(r, dict) for r in value):
        return "not a list of rows"
    where = rule.get("where") or {}
    meets = lambda row: all(_same(row.get(k), v) for k, v in where.items())  # noqa: E731
    pool = [r for r in table if isinstance(r, dict)]
    for row in value:
        hit = next((i for i, src in enumerate(pool)
                    if all(k in row and _same(row[k], src[k]) for k in src)), None)
        if hit is None:
            return f"row not in {rule['table']}: {json.dumps(row, default=str)[:160]}"
        pool.pop(hit)
        if not meets(row):
            off = {k: row.get(k) for k in where if not _same(row.get(k), where[k])}
            return f"row does not meet {json.dumps(off, default=str)}: {json.dumps(row, default=str)[:160]}"
    dropped = [r for r in pool if meets(r)]
    if dropped:
        return (f"{len(dropped)} row(s) that meet the condition were dropped, first: "
                f"{json.dumps(dropped[0], default=str)[:160]}")
    return None


_CHECKS: dict[str, Callable[[Any, Any, dict], str | None]] = {
    "rows_of": _check_rows_of, "sorted_by": _check_sorted_by, "flag": _check_flag,
    "subset_of": _check_subset_of, "covers": _check_covers,
    "excludes": _check_excludes, "only": _check_only,
    "not_in": _check_not_in, "only_in": _check_only_in,
    "selected_from": _check_selected_from,
}


def tables_checked(rules: dict | None) -> list[str]:
    """The Evidence tables a step's checks read: the host loads them for the check alone."""
    names = []
    for spec in (rules or {}).values():
        for rule in (spec if isinstance(spec, list) else [spec]):
            if isinstance(rule, dict) and "selected_from" in rule:
                names.append(rule["selected_from"]["table"])
    return list(dict.fromkeys(names))


def check_facts(rules: dict, produced: dict, facts: dict,
                tables: Callable[[str], list] | None = None) -> list[dict]:
    """The checks a produced fact fails, as {fact, check, reason}. Pure.

    A name the answer did not supply is skipped: it is already unresolved. Rules
    may name other produced facts; both are visible to a check. A rule that reads an
    Evidence table gets its rows from `tables`, for the check alone.
    """
    known = {**facts, **produced}
    for name in tables_checked(rules):
        if name not in known and tables is not None:
            known[name] = tables(name)
    failures = []
    for name, spec in (rules or {}).items():
        if name not in produced:
            continue
        for rule in (spec if isinstance(spec, list) else [spec]):
            if not isinstance(rule, dict) or len(rule) != 1:
                raise SkillGraphError(f"a check on {name} must be one {{kind: rule}}: {rule!r}")
            (kind, arg), = rule.items()
            check = _CHECKS.get(kind)
            if check is None:
                raise SkillGraphError(f"unknown check {kind!r} on {name}")
            reason = check(arg, produced[name], known)
            if reason:
                failures.append({"fact": name, "check": kind, "reason": reason})
    return failures


def check_problem(failures: list[dict]) -> str:
    return "the answer failed checks: " + "; ".join(
        f"{f['fact']} {f['check']} - {f['reason']}" for f in failures)


def without_failed(outcome: dict, failures: list[dict], step_id: str) -> dict:
    """Drop the facts that failed; they are unresolved, and the step says why."""
    names = {f["fact"] for f in failures}
    return {**outcome,
            "facts": {k: v for k, v in outcome["facts"].items() if k not in names},
            "unresolved": outcome["unresolved"] + [n for n in names if n not in outcome["unresolved"]],
            "blocked": outcome["blocked"] + [{"step": step_id, "reason": check_problem(failures)}]}


def checked(spec: dict, step_id: str, wants: list[str], outcome: dict, facts: dict,
            answered: bool, tables: Callable[[str], list] | None = None,
            failures: list[dict] | None = None) -> tuple[dict, str | None]:
    """Apply the step's checks to what the answer supplied.

    Returns the outcome and, when a re-ask is warranted, the problem to name in
    it; the host asks once more and calls again with `answered=False` to close.
    A host that ran the checks elsewhere (an activity, so a table's rows stay out
    of the history) passes their `failures` in.
    """
    rules = spec.get("check")
    if not rules:
        return outcome, None
    produced = {n: outcome["facts"][n] for n in wants if n in outcome["facts"]}
    if failures is None:
        failures = check_facts(rules, produced, facts, tables=tables)
    if not failures:
        return outcome, None
    if answered:
        return outcome, check_problem(failures)
    return without_failed(outcome, failures, step_id), None


def absorb(spec: dict, results: list, facts: dict, items: list | None = None,
           calls: list[dict] | None = None) -> dict:
    """What a step's results yield: facts, what never arrived, what cannot be decided.

    Pure. `extract` takes the first match, `collect` the lot, `combine` merges
    with facts the question supplied, `derive` decides a gateway from data. A
    derive over a source that never arrived is UNKNOWN and lands in `blocked`,
    never in facts — `when` reads a missing key as falsy and would skip the
    branch silently.
    """
    extracted: dict[str, Any] = {}
    excluded: dict[str, list] = {}
    for name, rule in (spec.get("extract") or {}).items():
        rule = rule if isinstance(rule, dict) else {"path": rule}
        for payload in results:
            found = _dig(payload, rule["path"])
            if found is None:
                continue
            if rule.get("regex") and isinstance(found, str):
                # Some values only exist inside a returned string: DailyMed
                # puts the BRAND at the head of its SPL title, and FAERS
                # indexes this drug family by brand (LUTATHERA returns 100
                # reaction terms where the generic name returns 3).
                match = re.search(rule["regex"], found)
                if not match:
                    continue
                found = match.group(1) if match.groups() else match.group(0)
            if rule.get("exclude") and isinstance(found, list):
                # The author knows which returned values are noise — FAERS coding
                # terms such as ILL-DEFINED DISORDER — and says so in the process,
                # before any cap, so the cap trims real terms only.
                dropped = [v for v in found if v in rule["exclude"]]
                if dropped:
                    excluded[name] = dropped
                    found = [v for v in found if v not in rule["exclude"]]
            if rule.get("limit") and isinstance(found, list):
                found = found[: rule["limit"]]
            extracted[name] = found
            break
        if name not in extracted and rule.get("default_from"):
            fallback = facts.get(rule["default_from"])
            if fallback is not None:
                extracted[name] = fallback
    # `collect` gathers a value from EVERY call, which is what a loop step
    # needs: FAERS answers one metrics object per reaction, and the gateway
    # has to see them all.
    for name, rule in (spec.get("collect") or {}).items():
        rule = rule if isinstance(rule, dict) else {"path": rule}
        gathered = []
        for index, payload in enumerate(results):
            found = _dig(payload, rule["path"])
            if found is None:
                continue
            def row_of(record: dict, index: int = index) -> dict:
                # Keep the few fields the run needs from a large payload, as one row.
                # "$item" is the loop value this call was made for — a tool that does
                # not echo its input (HPO's disease list) still yields a paired row.
                row = {}
                for spec_field in rule["fields"]:
                    src, _, alias = spec_field.partition(" as ")
                    if src == "$item":
                        value = items[index] if items and index < len(items) else None
                    elif src.startswith("$call."):
                        # a filled argument of the call this payload answered
                        arg = src[len("$call."):]
                        value = (calls[index].get("arguments") or {}).get(arg) if calls and index < len(calls) else None
                    else:
                        value = _dig(record, src)
                    if value is not None:
                        row[alias or src.split(".")[-1].rstrip("[]").lstrip("$")] = value
                return row

            if rule.get("fields") and isinstance(found, dict):
                found = row_of(found)
            elif (rule.get("fields") and isinstance(found, list)
                  and all(isinstance(record, dict) for record in found)):
                # One row for each record: a record that lacks a field is a row without
                # it, so nothing after it moves up a place.
                found = [row_of(record) for record in found]
            if rule.get("match"):
                # The first item that matches, per call: an HPO lookup answers
                # UPHENO:, MP:, then HP:, and only the HP id is a human phenotype.
                candidates = found if isinstance(found, list) else [found]
                found = next((c for c in candidates
                              if isinstance(c, str) and re.search(rule["match"], c)),
                             None)
                if found is None:
                    continue
            if rule.get("flatten") and isinstance(found, list):
                # One list per call folded into one list: Orphanet answers a
                # gene list per disease, and the gene panel loops over genes.
                gathered.extend(found)
            else:
                gathered.append(found)
        if rule.get("unique"):
            gathered = list(dict.fromkeys(gathered))
        if gathered:
            extracted[name] = gathered
    # `combine` merges facts the question supplied with facts the data
    # produced. Requested terms lead and the cap trims the frequency-ranked
    # tail, never the ask.
    for name, rule in (spec.get("combine") or {}).items():
        merged: list = []
        for source in rule.get("union", []):
            value = facts.get(source) or extracted.get(source) or []
            for item in (value if isinstance(value, list) else [value]):
                if item not in merged:
                    merged.append(item)
        if rule.get("limit"):
            merged = merged[: rule["limit"]]
        extracted[name] = merged

    # `compute` is arithmetic over rows the run already holds — ranking a
    # differential by onset, prevalence and overlap is not a judgement, so the
    # server does it, with the author's rule. Delegated to the agent's code tool,
    # the same arithmetic ran on a retyped input once (DSR-729, GM1 4/4).
    # Resolved in passes: a rule may read what another rule in the same step
    # produces, and a store hands the rules back in its own order, not the
    # author's (GraphDB: alphabetical, and the literature loop lost its list).
    pending = dict(spec.get("compute") or {})
    while pending:
        settled = []
        for name, rule in pending.items():
            value = _compute(rule, {**facts, **extracted})
            if value is not None:
                extracted[name] = value
                settled.append(name)
                if rule.get("exclude_pattern"):
                    dropped = _pluck_excluded(rule, {**facts, **extracted})
                    if dropped:
                        excluded[name] = dropped
        if not settled:
            break
        for name in settled:
            pending.pop(name)
    computed_missing = list(pending)

    blocked, undecided = [], []
    known = {**facts, **extracted}
    for name, rule in (spec.get("derive") or {}).items():
        decided = _derive(rule, known)
        if decided is None:
            undecided.append(name)
            blocked.append({
                "step": spec["id"],
                "reason": (f"cannot decide {name}: {rule['from']} was never "
                           "extracted, so the branch was not taken"),
            })
        else:
            extracted[name] = decided

    # A value the step SAYS it produces and did not is recorded, always.
    unresolved = [name for name in (spec.get("extract") or {})
                  if name not in extracted] + computed_missing
    return {"facts": extracted, "unresolved": unresolved, "blocked": blocked,
            "undecided": undecided, "excluded": excluded}


class SkillRunner:
    """Server-side execution of one skill graph, one run at a time."""

    MAX_REPAIRS = 2

    def __init__(self, graph: dict, execute: Callable[[str, dict], Any],
                 ask: Callable[[dict], list[str]] | None = None,
                 records: str | Path | None = None,
                 lookup: Callable[[str], dict] | None = None):
        self.graph = graph
        self.execute = execute
        # Where a mapped term sits in an ontology; injected so tests read recorded responses.
        self.lookup = lookup
        # Where each run's Working Record is kept; without it results stay in memory only.
        self.records = records
        # `ask` puts the model back in the loop as an ORACLE, never as the
        # scheduler: the server decides a lookup failed, frames the question,
        # validates the answer by re-querying, and stops after MAX_REPAIRS.
        # It exists because the agent knows things the data does not — that
        # "Lu-177" and "lu 177" are one isotope — and DailyMed returns nothing
        # for the form the agent correctly binds from the question.
        self.ask = ask
        self._runs: dict[str, dict] = {}

    def start(self, inputs: dict, run_id: str | None = None) -> dict:
        # A host that already names its runs (Temporal) passes the id in; the
        # in-memory host is the only one that mints its own.
        run_id = run_id or uuid.uuid4().hex
        self._runs[run_id] = {**new_run(inputs), "run_id": run_id}
        return {"run_id": run_id, "step": self._peek(run_id)}

    def state(self, run_id: str) -> dict:
        return self._runs[run_id]

    def _peek(self, run_id: str) -> dict | None:
        run = self._runs[run_id]
        return next_step(self.graph, done=run["done"] + run["skipped"],
                         facts=run["facts"])

    def _repair(self, spec, step, repair, results, failures, run, made):
        """Ask for a better argument value and retry, at most MAX_REPAIRS times."""
        if resolved(spec, repair, results):
            return results, failures
        argument = repair["argument"]
        original = step["calls"][0]["arguments"].get(argument)
        question = question_for(
            step["id"], "repair", [argument], dict(run["facts"]),
            tool=step["calls"][0]["tool"], argument=argument, value=original,
            problem=f"returned nothing for {original!r}",
        )
        answer = self.ask(question)
        asked(run, question, answer)
        # One answer shape for every question: the wanted name mapped to its
        # value — here a list of alternatives. A bare list is still taken.
        suggestions = answer.get(argument) if isinstance(answer, dict) else answer
        for candidate in (suggestions or [])[: self.MAX_REPAIRS]:
            retried, retry_failures = [], []
            retry_calls = substitute(step["calls"], argument, candidate)
            made.extend(retry_calls)
            for call in retry_calls:
                try:
                    retried.append(self.execute(call["tool"], call["arguments"]))
                except Exception as exc:                   # noqa: BLE001
                    retry_failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                           "error": f"{type(exc).__name__}: {exc}"})
            if resolved(spec, repair, retried):
                run["facts"][argument] = candidate
                return retried, retry_failures
            results, failures = retried, retry_failures
        run["blocked"].append({
            "step": step["id"],
            "reason": (f"{argument}={original!r} could not be resolved after "
                       f"{self.MAX_REPAIRS} suggested alternatives"),
        })
        return results, failures

    def _keep_evidence(self, run_id: str, run: dict, outcome: dict) -> None:
        if self.records is not None:
            run.setdefault("evidence", []).extend(keep_evidence(
                WorkingRecord(self.records, run_id), self.graph.get("tables"), outcome))

    def handover(self, run_id: str) -> dict:
        return handover_of(self.graph, self._runs[run_id])

    def _answered(self, spec, step, wants, outcome, run, question) -> dict:
        """Ask, fold the answer in, check it; a failing check is asked once more."""
        tables = (WorkingRecord(self.records, run["run_id"]).rows
                  if self.records is not None and "run_id" in run else None)
        answer = self.ask(question) if self.ask else None
        asked(run, question, answer)
        outcome = judged(outcome, wants, answer)
        outcome, problem = checked(spec, step["id"], wants, outcome, run["facts"],
                                   answered=answer is not None, tables=tables)
        problem = problem or mapping_problem(spec, outcome, run["facts"])
        if problem:
            retry = {**question, "problem": problem}
            answer = self.ask(retry)
            asked(run, retry, answer)
            outcome = judged(outcome, wants, answer)
            outcome, _ = checked(spec, step["id"], wants, outcome, run["facts"], answered=False,
                                 tables=tables)
            if mapping_problem(spec, outcome, run["facts"]):
                for name in spec.get("mapping") or {}:
                    outcome["facts"].pop(name, None)
                    outcome["unresolved"].append(name)
        return placed_mapping(spec, outcome, self.lookup)

    def _peek_safe(self, run_id: str):
        return next_runnable(self.graph, self._runs[run_id])

    def advance(self, run_id: str) -> dict:
        """Run the current step's calls, extract what follows, and move on."""
        run = self._runs[run_id]
        step = self._peek_safe(run_id)
        if step is None:
            return {"finished": True, "next_step": None, "extracted": {},
                    "failures": run["failures"], "blocked": run["blocked"],
                    "unresolved": run["unresolved"]}

        spec = next(s for s in self.graph["steps"] if s["id"] == step["id"])
        results, failures, made = [], [], list(step["calls"])
        for call in step["calls"]:
            try:
                result = self.execute(call["tool"], call["arguments"])
            except Exception as exc:                       # noqa: BLE001
                # A broken tool must not end the procedure: one bot-blocked FDA
                # endpoint ended a whole run under the model-driven loop.
                failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                 "error": f"{type(exc).__name__}: {exc}"})
                continue
            results.append(result)
            if is_upstream_failure(result):
                # The source failed and said so inside its answer: a failed call, on record
                # with the upstream status, never an empty extraction.
                failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                 "error": upstream_failure_text(result)})

        repair = spec.get("repair")
        if repair and self.ask:
            results, failures = self._repair(
                spec, step, repair, results, failures, run, made)

        if self.records is not None:
            record = WorkingRecord(self.records, run_id)
            for n, (call, payload) in enumerate(zip(step["calls"], results)):
                record.put_result(step["id"], n, call["tool"], call["arguments"], payload)
            outcome = absorb_recorded(record, self.graph.get("tables"), spec, step["calls"],
                                      run["facts"])
            run.setdefault("evidence", []).extend(outcome.pop("evidence"))
            outcome.pop("resolved")
        else:
            outcome = absorb(spec, results, run["facts"],
                             items=loop_items(spec, step["calls"]), calls=step["calls"])
        delegated = spec.get("delegate") or []
        if delegated:
            # Web search and code live on the agent, not in the registry. The run
            # asks the agent to make these calls with its own tools and hands
            # back the named facts — same pause as a judgement, results on record.
            wanted = spec.get("produces") or []
            try:
                calls = delegated_calls(spec, run["facts"])
            except SkillGraphError as exc:
                run["blocked"].append({"step": step["id"], "reason": str(exc)})
                outcome = judged(outcome, wanted, None)
            else:
                made.extend(calls)
                question = question_for(step["id"], "delegate", wanted, dict(run["facts"]),
                                        calls=calls, notes=spec.get("notes"))
                outcome = self._answered(spec, step, wanted, outcome, run, question)
        # A judgement is for what the step could not resolve itself: a name an
        # extraction or compute already supplied is never put to the model.
        wants = [n for n in (spec.get("judge") or []) if n not in outcome["facts"]]
        if wants:
            # A judgement fact is asked for by name, after the step's own calls,
            # with everything known so far — never inferred from what an
            # extraction happened to miss.
            question = question_for(
                step["id"], "judge", wants, {**run["facts"], **outcome["facts"]},
                notes=spec.get("notes"),
                choices=mapping_choices(spec, {**run["facts"], **outcome["facts"]}),
            )
            outcome = self._answered(spec, step, wants, outcome, run, question)
        self._keep_evidence(run_id, run, outcome)
        apply(run, step["id"], failures, outcome, calls=made)
        # The caller sees an unknown as an explicit None; facts never hold one.
        extracted = {**outcome["facts"], **{n: None for n in outcome["undecided"]}}
        missed = [{"step": step["id"], "fact": name} for name in outcome["unresolved"]]
        following = self._peek_safe(run_id)
        return {
            "step_id": step["id"],
            "blocked": run["blocked"],
            "unresolved": missed,
            "extracted": extracted,
            "failures": failures,
            "next_step": following,
            "finished": following is None,
        }


def normalised_executor(dispatch: Callable[[dict], Any]) -> Callable[[str, dict], Any]:
    """Wrap ToolUniverse's dispatch so the runner sees what the AGENT sees.

    `execute_tool` is not a second implementation — its class calls
    `run_one_function` and then normalises: JSON-decode a string return, and wrap
    any non-dict as {"result": ...}. Calling `run_one_function` directly skips
    that, so the runner saw a bare list where every saved trace shows
    {"result": [...]}, and an extraction path written from a trace missed.

    One door. Extraction paths written against a trace work in the runner, and
    vice versa.
    """
    def execute(tool: str, arguments: dict) -> Any:
        result = dispatch({"name": tool, "arguments": arguments})
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, ValueError):
                return {"result": result}
        return result if isinstance(result, dict) else {"result": result}
    return execute


def compose(graph: dict, facts: dict) -> dict:
    """Expose the graph's own templating, so callers need not reimplement it."""
    return _fill(graph, facts)
