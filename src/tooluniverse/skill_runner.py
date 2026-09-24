"""Run a skill's process graph server-side, keeping the model out of the control loop.

The runner holds the run state, executes each step's calls, extracts the values the
next step needs and evaluates gateways from the real results; the model only chooses
the skill, answers judgement questions and writes the report. Step logic (`absorb`,
`resolved`, `substitute`, `apply`) is module-level and pure so a durable host can await
the calls itself; `SkillRunner` is the synchronous driver over those functions.
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
    _expand_calls,
    _fill,
    _produces,
    delegated_calls,
    next_step,
    skipped_gates,
    stalled_steps,
)
from .skill_ontology_placing import place
from .skill_working_record import WorkingRecord, payload_rows

_OPS: dict[str, Callable[[Any, Any], bool]] = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class SkillPathError(ValueError):
    """A path that can never be right, whatever the payload holds."""


def _dig(payload: Any, path: str) -> Any:
    """Follow a dotted path into a result; a miss returns None so it surfaces as a missing fact.

    Deliberately not JSONPath, so extraction stays reviewable. One extra form: a segment
    ending ``[]`` maps over a list, giving the values the next step must pass back verbatim.
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
                raise SkillPathError(f"{path}: a path maps over one list, not two")
            if not isinstance(current, list):
                raise SkillPathError(
                    f"{path}: {key or 'the value'} is a {type(current).__name__}, not a list")
            mapping = True
    return current


def _step_in(current: Any, key: str, mapping: bool) -> Any:
    """Take one path segment, over a single value or over every mapped item."""
    if mapping:
        if not isinstance(current, list):
            return None
        # One entry per record, misses included, so two paths over the same records pair up.
        return [_step_in(item, key, False) for item in current]
    if isinstance(current, dict):
        return current.get(key)
    if isinstance(current, list) and key.isdigit():
        return current[int(key)] if int(key) < len(current) else None
    return None


# --- compute: arithmetic over rows the run holds --------------------------------

_PREVALENCE_TIERS = (">1 / 1000", "1-5 / 10 000", "6-9 / 10 000", "1-9 / 100 000",
                     "1-9 / 1 000 000", "<1 / 1 000 000")   # Orphanet's classes, commonest first
_UNKNOWN_TIER_POSITION = 4.5      # below every counted class, above the rarest


def _prevalence_tier(classes: list[str]) -> tuple[str, float]:
    """The class most of Orphanet's entries agree on, and its position.

    Orphanet lists one estimate per study and region, so a single outlier must not decide.
    Ties go to the commoner class; no counted class at all is "unknown".
    """
    known = [c for c in classes or [] if c in _PREVALENCE_TIERS]
    if not known:
        return "unknown", _UNKNOWN_TIER_POSITION
    counts = {c: known.count(c) for c in set(known)}
    best = min(counts, key=lambda c: (-counts[c], _PREVALENCE_TIERS.index(c)))
    return best, float(_PREVALENCE_TIERS.index(best))


def _rank_differential(rule: dict, facts: dict) -> list[dict] | None:
    """Order candidates by onset fit, then discriminating phenotypes, then prevalence, then overlap.

    A disease whose every onset class is later than the patient goes below every disease
    that fits; no patient age means onset is not assessed.
    """
    overlap = facts.get(rule["overlap"])
    if overlap is None:
        return None
    overlap = _records(overlap)
    age = facts.get(rule.get("patient_age_years", ""))
    onset_by = {str(r.get("orpha_code")): r.get("average_age_of_onset") or []
                for r in _records(facts.get(rule.get("inheritance", "")))}
    prev_by = {str(r.get("orpha_code")): r.get("classes") or []
               for r in _records(facts.get(rule.get("epidemiology", "")))}
    early, late = set(rule.get("early_onset", [])), set(rule.get("late_onset", []))
    # A candidate missing the discriminating phenotypes ranks below one that carries them,
    # else the commonest disease matching only the common phenotypes floats to the top.
    pair = facts.get(rule.get("must_carry", "")) or []
    ids_by = {str(r.get("orpha_code")): set(r.get("hpo_ids") or [])
              for r in _records(facts.get(rule.get("rows_ids", "")))}
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
        # A candidate matching nothing goes to the bottom of its band; prevalence does not rescue it.
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

    Yes if it lists the term itself, all of the term's parents, or any child. With no
    hierarchy row for the term, exact match only.
    """
    if term in disease_ids:
        return True
    h = hierarchy.get(term) or {}
    parents = h.get("parents") or []
    # A lone parent is a broader term, not the conjunction the term names.
    if len(parents) >= 2 and all(p in disease_ids for p in parents):
        return True
    return any(c in disease_ids for c in (h.get("children") or []))


def _hierarchy(rule: dict, facts: dict) -> dict:
    rows = _records(facts.get(rule.get("hierarchy", "")))
    return {str(r.get("hpo_id")): r for r in rows}


def _overlap(rule: dict, facts: dict) -> list[dict] | None:
    """Per row: how many of the case's ids it carries, and the grade that earns.

    Grades are the author's rubric, first match wins; `needs_gene` holds a grade back
    unless a gene row for the same code lists a gene.
    """
    rows, against = facts.get(rule["rows"]), facts.get(rule["against"])
    if rows is None or against is None:
        return None
    rows = _records(rows)
    case = list(dict.fromkeys(against))
    gene_rows = _records(facts.get(rule.get("gene_rows", "")))
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
    """The `take` ids whose count is smallest; None when the cut ties, so the model is asked."""
    rows = facts.get(rule["rows"])
    if rows is None:
        return None
    rows = _records(rows)
    take = int(rule.get("take", 2))
    seen: dict = {}
    for row in rows:
        value = row.get(rule["count"])
        size = len(value) if isinstance(value, (list, dict)) else value
        ident = row.get(rule["id"])
        if size is not None and ident not in seen:        # one term counts once
            seen[ident] = size
    sized = [(size, ident) for ident, size in seen.items()]
    if len(sized) < take:
        return None
    sized.sort(key=lambda t: (t[0], str(t[1])))
    if len(sized) > take and sized[take - 1][0] == sized[take][0]:
        return None                                   # tie at the cut
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
        # The argument whose template was the loop variable carries the item;
        # failing that, the one whose template contained it.
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
    """The loop value inside a filled argument: the marker captures, other placeholders match anything."""
    pattern = re.escape(template).replace(re.escape(marker), "(?P<item>.+?)", 1)
    pattern = re.sub(r"\\\{[A-Za-z_][A-Za-z0-9_]*\\\}", ".+?", pattern)
    match = re.fullmatch(pattern, text, flags=re.S)
    return match.group("item") if match else None


def _records(rows: Any) -> list[dict]:
    """The record entries of a rows fact.

    An entry that is not a record is not a row: a mapped path keeps a miss in place, and
    reading one as a crash tells the agent nothing at all.
    """
    return [row for row in rows or [] if isinstance(row, dict)]


def _rows_of(rule: dict, facts: dict) -> list[dict] | None:
    """The named rows a compute reads, or None when the fact never arrived.

    None is the fact never arriving; an empty list is a fact that arrived holding no record.
    """
    rows = facts.get(rule["rows"])
    return None if rows is None else _records(rows)


def _hierarchy_rows(rule: dict, facts: dict) -> list[dict] | None:
    """Fold the per-call hierarchy rows into one row per term: {hpo_id, parents, children}."""
    rows = _rows_of(rule, facts)
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
    """The rows ordered by one numeric field, largest first, each marked whether it reaches the threshold."""
    rows = _rows_of(rule, facts)
    if rows is None:
        return None
    field, threshold = rule["field"], float(rule.get("threshold", 0))

    def value(row):
        try:
            return float(row.get(field))
        except (TypeError, ValueError):
            return None

    out = []
    for row in rows:
        seen = value(row)
        marked = {**row, "flagged": None if seen is None else seen >= threshold}
        if seen is None and row.get(field) is not None:
            marked["unparseable"] = row[field]
        out.append(marked)
    out.sort(key=lambda r: (value(r) is None, -(value(r) or 0.0)))
    return out


def _pluck(rule: dict, facts: dict) -> list | None:
    """One field from every row (or the rows whose `where` field is true), minus `exclude_pattern` matches."""
    picked = _pluck_all(rule, facts)
    if picked is None:
        return None
    pattern = rule.get("exclude_pattern")
    return [v for v in picked if not (pattern and re.search(pattern, str(v), re.I))]


def _pluck_excluded(rule: dict, facts: dict) -> list:
    """The values `_pluck` set aside, recorded so the report can say so."""
    picked = _pluck_all(rule, facts) or []
    pattern = rule.get("exclude_pattern")
    return [v for v in picked if pattern and re.search(pattern, str(v), re.I)]


def _pluck_all(rule: dict, facts: dict) -> list | None:
    rows = _rows_of(rule, facts)
    if rows is None:
        return None
    where = rule.get("where")
    return [row.get(rule["field"]) for row in rows
            if (row.get(where) if where else True) and row.get(rule["field"]) is not None]


_ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7",
          "viii": "8", "ix": "9", "x": "10"}
_NAME_FILLER = {"type", "syndrome", "disease"}


def _name_words(name: Any) -> list[str]:
    words = re.split(r"[^0-9a-z]+", str(name or "").lower())
    return sorted(_ROMAN.get(w, w) for w in words if w and w not in _NAME_FILLER)


def same_name(asked: Any, returned: Any) -> bool:
    """Two names name the same thing when, lower-cased, with punctuation read as spaces,
    Roman numerals read as numbers and the words "type", "syndrome" and "disease"
    dropped, they hold the same words in any order."""
    words = _name_words(asked)
    return bool(words) and words == _name_words(returned)


def _same_name_split(rule: dict, facts: dict) -> tuple[list[dict], list[dict]] | None:
    rows = _rows_of(rule, facts)
    if rows is None:
        return None
    kept, aside = [], []
    for row in rows:
        if same_name(row.get(rule["asked"]), row.get(rule["field"])):
            kept.append(row)
        else:
            aside.append({**row, "not_resolved": True})
    return kept, aside


def _same_name(rule: dict, facts: dict) -> list[dict] | None:
    """The rows whose `field` names what their `asked` field asked for (see `same_name`)."""
    split = _same_name_split(rule, facts)
    return None if split is None else split[0]


def _same_name_excluded(rule: dict, facts: dict) -> list[dict]:
    """The rows whose source name is another thing: not resolved, each with both names."""
    split = _same_name_split(rule, facts)
    return [] if split is None else split[1]


class _Refused:
    """A compute that cannot proceed on what it was given, with the reason."""

    def __init__(self, reason: str):
        self.reason = reason


def _number(value: Any) -> float | None:
    try:
        return None if value is None or isinstance(value, bool) else float(value)
    except (TypeError, ValueError):
        return None


def _band(rule: dict, facts: dict) -> Any:
    """Points from a number by the first threshold it reaches."""
    value = _number(_dig(facts, rule["from"]))
    if value is None:
        return None
    for threshold, points in rule["bands"]:
        if value >= float(threshold):
            return points
    return None


def _map(rule: dict, facts: dict) -> Any:
    """Points from a judged option out of a closed list; an option off the list is refused by name."""
    option = facts.get(rule["from"])
    if option is None:
        return None
    table = rule["table"]
    if option in table:
        return table[option]
    return _Refused(f"{rule['from']} is {option!r}, not one of {sorted(table)}")


def _sum(rule: dict, facts: dict) -> Any:
    """The named parts added, capped when the rule says so; a missing part is not a zero."""
    parts = [_number(facts.get(name)) for name in rule["of"]]
    if any(p is None for p in parts):
        return None
    total = sum(parts)
    if rule.get("cap") is not None:
        total = min(total, float(rule["cap"]))
    return int(total) if float(total).is_integer() else total


def _first(rule: dict, facts: dict) -> Any:
    """The first value of a list fact."""
    values = facts.get(rule["of"])
    if values is None:
        return None
    return values[0] if isinstance(values, list) and values else (None if isinstance(values, list) else values)


def _lookup(rule: dict, facts: dict) -> Any:
    """One row's value from a fact table, by the key another fact names."""
    rows, wanted = facts.get(rule["rows"]), facts.get(rule["equals"])
    if isinstance(wanted, list):
        wanted = wanted[0] if wanted else None      # a list key means its first id
    if rows is None or wanted is None:
        return None
    for row in rows:
        if isinstance(row, dict) and _same(row.get(rule["key"]), wanted):
            return row.get(rule["field"])
    return _Refused(f"no row of {rule['rows']} has {rule['key']} = {wanted!r}")


_COMPUTE_OPS: dict[str, Callable[[dict, dict], Any]] = {"rank_differential": _rank_differential,
                                                       "overlap": _overlap, "fewest": _fewest,
                                                       "hierarchy": _hierarchy_rows,
                                                       "flag": _flag, "pluck": _pluck,
                                                       "band": _band, "map": _map, "sum": _sum,
                                                       "lookup": _lookup, "first": _first,
                                                       "same_name": _same_name}

# What an op set aside, recorded under `excluded` so the report can say so.
_SET_ASIDE: dict[str, Callable[[dict, dict], list]] = {"pluck": _pluck_excluded,
                                                      "same_name": _same_name_excluded}


def _compute(rule: dict, facts: dict) -> Any:
    """One named operation over facts; None when a source fact never arrived."""
    op = _COMPUTE_OPS.get(rule.get("op"))
    if op is None:
        raise SkillGraphError(f"unknown compute op {rule.get('op')!r}")
    return op(rule, facts)


def _computed(spec: dict, pending: dict, facts: dict, extracted: dict,
              excluded: dict) -> tuple[list[dict], list[str], dict]:
    """Apply `pending` rules to a fixpoint, adding what resolves to `extracted`.

    Returns (blocked, refused, still pending). A rule may read what another rule produces,
    so passes repeat until nothing new settles.
    """
    blocked: list[dict] = []
    refused: list[str] = []
    while pending:
        settled = []
        for name, rule in pending.items():
            try:
                value = _compute(rule, {**facts, **extracted})
            except SkillPathError as error:
                blocked.append({"step": spec["id"], "reason": f"cannot compute {name}: {error}"})
                refused.append(name)
                settled.append(name)
                continue
            if isinstance(value, _Refused):
                blocked.append({"step": spec["id"], "reason": f"cannot compute {name}: {value.reason}"})
                refused.append(name)
                settled.append(name)
            elif value is not None:
                extracted[name] = value
                settled.append(name)
                set_aside = _SET_ASIDE.get(rule.get("op"))
                if set_aside:
                    dropped = set_aside(rule, {**facts, **extracted})
                    if dropped:
                        excluded[name] = dropped
        if not settled:
            break
        for name in settled:
            pending.pop(name)
    return blocked, refused, pending


def recomputed(spec: dict, outcome: dict, facts: dict) -> dict:
    """Apply the compute rules a judgement left waiting, now that the judged facts are in.

    Pure. Only the rules still unresolved run; what resolves leaves `unresolved`.
    """
    waiting = {name: rule for name, rule in (spec.get("compute") or {}).items()
               if name in outcome["unresolved"]}
    if not waiting:
        return outcome
    values: dict = {}
    excluded = dict(outcome.get("excluded") or {})
    blocked, _, _ = _computed(spec, waiting, {**facts, **outcome["facts"]}, values, excluded)
    return {**outcome, "facts": {**outcome["facts"], **values},
            "unresolved": [n for n in outcome["unresolved"] if n not in values],
            "blocked": list(outcome.get("blocked") or []) + blocked, "excluded": excluded}


def _derive(spec: dict, facts: dict) -> bool | None:
    """A gateway condition computed from data, not asserted by the model.

    None means unknown: the source fact never arrived. A genuine empty result is
    still False; only an absent fact is unknown, so a miss cannot pass as "no".
    """
    if spec["from"] not in facts:
        return None
    rows = facts.get(spec["from"]) or []
    field, op, value = spec.get("field"), spec.get("op", "=="), spec.get("value")
    compare = _OPS[op]
    hits, unusable = [], 0
    for row in rows:
        seen = row.get(field) if isinstance(row, dict) else row
        if seen is None:
            unusable += 1
            continue
        try:
            hits.append(compare(seen, value))
        except TypeError:
            unusable += 1
            continue
    if not hits and unusable:
        return None          # rows arrived but none could be read: unknown, not "no"
    return all(hits) if spec.get("mode") == "all" else any(hits)



MAX_PAYLOAD = 12_000   # per fact in a question's context


def new_run(inputs: dict) -> dict:
    """Fresh run state: (done, facts) plus what went wrong."""
    return {"facts": dict(inputs), "done": [], "failures": [], "blocked": [],
            "skipped": [], "calls": {}, "calls_made": {},
            "questions": [], "unresolved": [], "excluded": {}}


_SERVER_ERROR_TYPES = ("ServerError", "UpstreamServiceError", "Timeout", "ConnectionError",
                       "ToolUnavailableError")


def is_upstream_failure(result: Any) -> bool:
    """A result that reports the source failed, not that it had nothing to say.

    "Not found" is an answer; a retriable error, a server error type or a 5xx/408/429
    status in the envelope is a failure.
    """
    if not isinstance(result, dict) or result.get("status") != "error":
        return False
    details = result.get("error_details") or {}
    status = result.get("upstream_status")
    # Some tools carry the exception type only in text.
    typed = " ".join(str(result.get(k, "")) for k in ("detail", "error")) + str(details.get("type", ""))
    return bool(details.get("retriable") or result.get("retryable")
                or any(t in typed for t in _SERVER_ERROR_TYPES)
                or (isinstance(status, int) and (status >= 500 or status in (408, 429))))


def upstream_failure_text(result: dict) -> str:
    error = result.get("error")
    return f"UpstreamFailure: {error if isinstance(error, str) else json.dumps(error, default=str)}"


def apply(run: dict, step_id: str, failures: list, outcome: dict,
          calls: list[dict] | None = None) -> None:
    """Record a finished step on the run; mutates `run`. Results live in the Working Record."""
    # The tools this step ran, retries included: the agent's own trace never shows them.
    run["calls"][step_id] = [c["tool"] for c in (calls or [])]
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
    """The step to run now, marking any step that cannot be built as blocked, not fatal.

    Loops, because skipping one blocked step can reveal another.
    """
    while True:
        try:
            step = next_step(graph, done=run["done"] + run["skipped"],
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
            continue
        unreadable = step.pop("unreadable_items", 0) if step else 0
        if unreadable:
            # A loop item that is a miss makes no call. Said once, however often the
            # step is peeked: both drivers come through here.
            note = {"step": step["id"],
                    "reason": f"{step['id']}: {unreadable} of the items this step loops "
                              "over could not be read, so no call was made for them"}
            if note not in run["blocked"]:
                run["blocked"].append(note)
        return step


# The same rules for every skill; the report's structure is the skill's own.
WRITE_THE_REPORT = [
    "Take every number from its row and cite it with that row's own link.",
    "State a finding only from a source you read: an abstract, a page, a row -- never from a "
    "title alone.",
    "Wherever this run holds less than the source, say both numbers: how much the source holds "
    "(source_total) and how much this run holds of it (held).",
    "A number published in a paper or a page stands beside a number this run computed, each "
    "with its source and period; never merge the two.",
    "Cite only what this run received. A tool you called before run_skill left no record "
    "here, so its numbers and links cannot be vouched for: take the fact from a row of this "
    "run and cite that row, or leave it out.",
    "The run's own address is not a source. A /skills/runs/ URL is this run's bookkeeping, "
    "so never footnote it -- cite the row's own link instead, from the table the number "
    "came from.",
    "State what failed, what was not found, what never ran and what was set aside, from "
    "failures, blocked, unresolved, steps_skipped and excluded. A skipped step with "
    "decided: false was never decided, not decided against; a row's `unparseable` holds "
    "the text a number could not be read from, so that row's verdict is unknown, not no; "
    "a mapped row's `note` says why its placing is uncertain.",
]


def report_rules(record: dict | None) -> list[str]:
    """The rules for this run's report: the shared ones, and the Run Record's absence."""
    if not record or record.get("status") != "failed":
        return list(WRITE_THE_REPORT)
    return WRITE_THE_REPORT + [
        "This run was not recorded: its permanent Run Record could not be written "
        f"({record.get('error') or 'no reason given'}). Say so in the report, in one line, "
        "so the reader knows there is no lasting record of what this run read and decided."]


def handover_of(graph: dict, run: dict) -> dict:
    """What the agent is handed once at the end: the facts, and a description of each wide table.

    Tool results stay in the Working Record, fetched by table.
    """
    handed = {
        "skill": graph["skill"],
        "facts": run["facts"],
        "steps_done": run["done"],
        "steps_skipped": skipped_gates(graph, run["done"] + run["skipped"], run["facts"]),
        "calls": run.get("calls", {}),
        # The author's notes on what each step means and how the report must read it.
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
# The check proves membership, not meaning, so the mapping is a fact table the report must
# show, each row with the agent's reason and a placing from an ontology.

def mapping_choices(spec: dict, facts: dict) -> dict | None:
    """The source's terms a mapping may use, whole, so they travel in the question even when the rows are too wide."""
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
    """Each mapped row gets its placing; a flat `<name>_terms` list is kept for the steps that loop."""
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
                           "ontology_term": verdict.get("term"),
                           "ontology_label": verdict.get("label"),
                           **({"note": verdict["note"]} if verdict.get("note") else {})})
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


def _per_total_call(results: list, items: list | None, measure: Callable[[Any], Any]) -> Any:
    """`measure` of the call(s) a step's total comes from: one per loop item, else the first call."""
    if items and len(items) == len(results):
        return {str(item): measure(payload) for item, payload in zip(items, results)}
    return measure(results[0]) if results else None


def source_total(spec: dict, results: list, items: list | None) -> Any:
    """How much the source holds for this step's calls, by the path the step declares.

    One number for a single call, one per loop item for a loop; "unknown" when the step
    declares no `total` or the source gave none.
    """
    path = spec.get("total")
    if not path:
        return "unknown"

    def total(payload: Any) -> Any:
        try:
            return _dig(payload, path)
        except SkillPathError:
            return None                      # a bad path holds no total, same as a source that gave none
    found = _per_total_call(results, items, total)
    if isinstance(found, dict):
        return {item: (t if t is not None else "unknown") for item, t in found.items()}
    return found if found is not None else "unknown"


def held_rows(results: list, items: list | None) -> Any:
    """The rows the run holds from the call(s) `source_total` reads, in its shape.

    A step's other tools add rows to its table, never to what its total is read against.
    """
    return _per_total_call(results, items,
                           lambda payload: 0 if payload is None else len(payload_rows(payload)))


def absorb_recorded(record: WorkingRecord, tables: dict | None, spec: dict,
                    calls: list[dict], facts: dict) -> dict:
    """`absorb` over the step's recorded results, so no result has to travel to the caller."""
    results = record.results(spec["id"], expected=len(calls))
    outcome = absorb(spec, results, facts, items=loop_items(spec, calls), calls=calls)
    outcome["evidence"] = keep_evidence(record, tables, outcome)
    if results:
        described = record.describe(f"results.{spec['id']}")
        items = loop_items(spec, calls)
        described["source_total"] = source_total(spec, results, items)
        if spec.get("total"):
            described["held"] = held_rows(results, items)
        outcome["evidence"].append(described)
    repair = spec.get("repair")
    problem = repair_problem(spec, repair, results, repair_value(repair, calls, facts)) \
        if repair else None
    outcome["resolved"], outcome["repair_problem"] = problem is None, problem
    return outcome


def repair_value(repair: dict, calls: list[dict], facts: dict) -> Any:
    """The value a repair replaces: a call argument of that name, else the fact the calls are built from."""
    argument = repair["argument"]
    for call in calls:
        if argument in call["arguments"]:
            return call["arguments"][argument]
    return facts.get(argument)


def _names(payload: Any, paths: list[str]) -> list[str]:
    """The names a hit lists at the given paths, in order; a path that is absent gives none."""
    names = []
    for path in paths:
        try:
            found = _dig(payload, path)
        except SkillPathError:
            continue                         # a hit without that field lists no name there
        names.extend(n for n in (found if isinstance(found, list) else [found]) if isinstance(n, str))
    return names


def _hit(spec: dict, repair: dict, payload: Any) -> bool:
    """The payload carries the value the repair watches for."""
    rule = (spec.get("extract") or {}).get(repair["when_missing"])
    try:
        return _dig(payload, rule["path"] if isinstance(rule, dict) else rule) is not None
    except SkillPathError:
        return False                         # a malformed path has not resolved anything either


def _wrong_hit(spec: dict, repair: dict | None, payload: Any, value: Any) -> bool:
    """A hit whose names, where `named_by` says to read them, do not include the value asked.

    The value matches when it is one of those names, ignoring case.
    """
    if not (repair or {}).get("named_by") or not _hit(spec, repair, payload):
        return False
    return str(value).casefold() not in {n.casefold() for n in _names(payload, repair["named_by"])}


def repair_problem(spec: dict, repair: dict, results: list, value: Any) -> str | None:
    """Why the value this step exists to produce did not arrive; None when it did.

    With `named_by`, a hit counts only when it names the value asked for: a source may
    answer a near miss with the wrong entity rather than with nothing.
    """
    hits = [p for p in results if _hit(spec, repair, p)]
    if any(not _wrong_hit(spec, repair, p, value) for p in hits):
        return None
    if hits:
        names = _names(hits[0], repair["named_by"])
        wrong = names[0] if names else "a hit that lists no name"
        return f"returned {wrong!r} for {value!r}, and {value!r} is none of the names that hit lists"
    return f"returned nothing for {value!r}"


def resolved(spec: dict, repair: dict, results: list, value: Any = None) -> bool:
    """Did the value this step exists to produce actually arrive, for the value asked?"""
    return repair_problem(spec, repair, results, value) is None


def repair_calls(spec: dict, calls: list[dict], argument: str, candidate: Any,
                 facts: dict) -> list[dict]:
    """The step's calls again with the candidate: swapped where a call carries the
    argument, else composed afresh from the fact of that name."""
    if any(argument in call["arguments"] for call in calls):
        return substitute(calls, argument, candidate)
    return _expand_calls(spec, {**facts, argument: candidate})


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

    The step's notes ride along when it has any; they say what shape the answer should take.
    """
    return {"kind": kind, "step": step_id, "wants": list(wants),
            "context": _readable(context, detail.get("calls") or []),
            **{k: v for k, v in detail.items() if v is not None}}


def _readable(facts: dict, calls: list[dict]) -> dict:
    """The facts a question shows the model; a fact over the payload cap is replaced by a stub.

    The stub says where the value is, so the model does not transcribe an empty value.
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
    """Remember a question and its answer, never its context, which is payload."""
    run["questions"].append({"step": question["step"], "kind": question["kind"],
                             "wants": list(question["wants"]), "answer": answer})


def judged(outcome: dict, wants: list[str], answer: dict | None) -> dict:
    """Fold the model's answer to a judgement into a step outcome.

    Only the names the step declared are taken; a declared name the model did not
    answer is unresolved. A name already carried as unresolved -- declared under
    `produces` as well as `judge` -- is not counted twice.
    """
    answer = answer or {}
    facts = {**outcome["facts"],
             **{name: answer[name] for name in wants if name in answer}}
    # A name a compute left unresolved and the model then supplied is resolved.
    carried = [n for n in outcome["unresolved"] if n not in answer]
    unresolved = carried + [n for n in wants if n not in answer and n not in carried]
    return {**outcome, "facts": facts, "unresolved": unresolved}


# --- check: a model answer is verified against the rows before it becomes a fact ---
#
# The server cannot make the agent use a tool; it can refuse an answer that does
# not hold against the data the run already has.

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


def _rows_by_key(rule: dict, keys: list, table: list) -> tuple[list, str | None]:
    """The table's own rows for a selection answered as keys; a key the table lacks is named."""
    key = rule["key"]
    by_key = {row.get(key): row for row in table if isinstance(row, dict)}
    rows, seen = [], set()
    for k in keys:
        if k not in by_key:
            return [], f"key not in {rule['table']}.{key}: {k!r}"
        if k not in seen:
            seen.add(k)
            rows.append(by_key[k])
    return rows, None


def _check_selected_from(rule: dict, value: Any, facts: dict) -> str | None:
    """Every row is from the table, meets the condition, and no qualifying row is left out.

    Answered as keys (when the rule names a `key`), the rows are the table's own; answered
    as rows, each must be a row of the table unchanged. The first breach is named.
    """
    table = facts.get(rule["table"])
    if not isinstance(table, list):
        return f"{rule['table']} is not a list of rows"
    if not isinstance(value, list):
        return "not a list"
    if rule.get("key") and all(not isinstance(v, dict) for v in value):
        value, problem = _rows_by_key(rule, value, table)
        if problem:
            return problem
    if not all(isinstance(r, dict) for r in value):
        return "not a list of rows" + (f" or of {rule['key']} keys" if rule.get("key") else "")
    where = rule.get("where") or {}

    def holds(cell: Any, wanted: Any) -> bool:
        # A list-valued cell meets the condition when it holds the value.
        return any(_same(m, wanted) for m in cell) if isinstance(cell, list) else _same(cell, wanted)

    meets = lambda row: all(holds(row.get(k), v) for k, v in where.items())  # noqa: E731
    pool = [r for r in table if isinstance(r, dict)]
    for row in value:
        hit = next((i for i, src in enumerate(pool)
                    if all(k in row and _same(row[k], src[k]) for k in src)), None)
        if hit is None:
            return f"row not in {rule['table']}: {json.dumps(row, default=str)[:160]}"
        pool.pop(hit)
        if not meets(row):
            off = {k: row.get(k) for k in where if not holds(row.get(k), where[k])}
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
    """The evidence tables a step's checks read; the host loads them for the check alone."""
    names = []
    for spec in (rules or {}).values():
        for rule in (spec if isinstance(spec, list) else [spec]):
            if isinstance(rule, dict) and "selected_from" in rule:
                names.append(rule["selected_from"]["table"])
    return list(dict.fromkeys(names))


def materialised(rules: dict, produced: dict, facts: dict,
                 tables: Callable[[str], list] | None = None) -> dict:
    """The produced facts answered as keys, as the table's own rows, which is what the run keeps."""
    known = dict(facts)
    for name in tables_checked(rules):
        if name not in known and tables is not None:
            known[name] = tables(name)
    out = {}
    for name, spec in (rules or {}).items():
        value = produced.get(name)
        for rule in (spec if isinstance(spec, list) else [spec]):
            selected = rule.get("selected_from") if isinstance(rule, dict) else None
            if (selected and selected.get("key") and isinstance(value, list)
                    and all(not isinstance(v, dict) for v in value)):
                rows, problem = _rows_by_key(selected, value, known.get(selected["table"]) or [])
                if not problem:
                    out[name] = rows
    return out


def check_facts(rules: dict, produced: dict, facts: dict,
                tables: Callable[[str], list] | None = None) -> list[dict]:
    """The checks a produced fact fails, as {fact, check, reason}. Pure.

    A name the answer did not supply is skipped: it is already unresolved. A rule that
    reads an evidence table gets its rows from `tables`.
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
            failures: list[dict] | None = None,
            rows_by_key: dict | None = None) -> tuple[dict, str | None]:
    """Apply the step's checks to what the answer supplied.

    Returns the outcome and, when a re-ask is warranted, the problem to name in it;
    the host asks once more and calls again with `answered=False` to close. A host
    that ran the checks elsewhere passes their `failures` in.
    """
    rules = spec.get("check")
    if not rules:
        return outcome, None
    produced = {n: outcome["facts"][n] for n in wants if n in outcome["facts"]}
    # A check may name a list this same step extracted, not only one held before it.
    facts = {**facts, **outcome["facts"]}
    if failures is None:
        failures = check_facts(rules, produced, facts, tables=tables)
        rows_by_key = materialised(rules, produced, facts, tables=tables)
    if not failures:
        # A selection answered as keys is kept as the table's own rows.
        return {**outcome, "facts": {**outcome["facts"], **(rows_by_key or {})}}, None
    if answered:
        return outcome, check_problem(failures)
    return without_failed(outcome, failures, step_id), None


def _values_read(values: list) -> tuple[list, int]:
    """The entries of a mapped list that were read, and how many were misses.

    A mapped path keeps one entry per record so two paths over the same records pair up;
    a rule that consumes the list as things to act on takes only what was read.
    """
    kept = [v for v in values if v is not None]
    return kept, len(values) - len(kept)


def _unread(step_id: str, name: str, dropped: int) -> dict:
    """What a rule left out because it could not be read; dropping it silently is the
    same defect as keeping it."""
    return {"step": step_id,
            "reason": f"{name}: {dropped} of its values could not be read, so they were left out"}


def absorb(spec: dict, results: list, facts: dict, items: list | None = None,
           calls: list[dict] | None = None) -> dict:
    """What a step's results yield: facts, what never arrived, what cannot be decided.

    Pure. `extract` takes the first match, `collect` one per call, `combine` merges with
    facts the question supplied, `compute` is arithmetic over rows, `derive` decides a
    gateway from data. A derive over an absent source lands in `blocked`, never in facts,
    because `when` would read a missing key as falsy and skip the branch silently.
    """
    extracted: dict[str, Any] = {}
    excluded: dict[str, list] = {}
    blocked: list[dict] = []
    if (repair := spec.get("repair")) and repair.get("named_by"):
        # A hit that names something other than what was asked is not the thing asked for.
        value = repair_value(repair, calls or [], facts)
        results = [None if _wrong_hit(spec, repair, p, value) else p for p in results]
    for name, rule in (spec.get("extract") or {}).items():
        rule = rule if isinstance(rule, dict) else {"path": rule}
        path_blocked = False
        for payload in results:
            try:
                found = _dig(payload, rule["path"])
            except SkillPathError as error:
                # A syntax error in the path is the same for every payload; a mapped segment over
                # something that is not a list depends on what this one payload gave back. Either
                # way, one bad call costs only that call -- the next payload still gets a try.
                if not path_blocked:
                    blocked.append({"step": spec["id"], "reason": f"cannot extract {name}: {error}"})
                    path_blocked = True
                continue
            if found is None:
                continue
            if rule.get("regex") and isinstance(found, str):
                # Some values only exist inside a returned string.
                match = re.search(rule["regex"], found)
                if not match:
                    continue
                found = match.group(1) if match.groups() else match.group(0)
            if rule.get("exclude") and isinstance(found, list):
                # The author's noise list applies before the cap, so the cap trims real values only.
                dropped = [v for v in found if v in rule["exclude"]]
                if dropped:
                    excluded[name] = dropped
                    found = [v for v in found if v not in rule["exclude"]]
            if rule.get("limit") and isinstance(found, list):
                # A miss goes before the cap too, so the cap trims real values only.
                found, missed = _values_read(found)
                if missed:
                    blocked.append(_unread(spec["id"], name, missed))
                found = found[: rule["limit"]]
            # The first payload that yields a value wins, so a path error already recorded
            # for an earlier call stays recorded even though the name did resolve.
            extracted[name] = found
            break
        if name not in extracted and rule.get("default_from"):
            fallback = facts.get(rule["default_from"])
            if fallback is not None:
                extracted[name] = fallback
    # `collect` gathers a value from every call, which is what a loop step needs.
    for name, rule in (spec.get("collect") or {}).items():
        rule = rule if isinstance(rule, dict) else {"path": rule}
        gathered = []
        path_blocked = False
        unread = 0
        for index, payload in enumerate(results):
            try:
                found = _dig(payload, rule["path"])
                if found is None:
                    continue
                def row_of(record: dict, index: int = index) -> dict:
                    # Keep the few fields the run needs, as one row. "$item" is the loop
                    # value this call was made for, so a tool that does not echo its input still pairs.
                    row = {}
                    for spec_field in rule["fields"]:
                        src, _, alias = spec_field.partition(" as ")
                        if src == "$item":
                            value = items[index] if items and index < len(items) else None
                        elif src.startswith("$call."):
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
                    # A record that lacks a field is a row without it, so positions are kept.
                    found = [row_of(record) for record in found]
                if rule.get("match"):
                    # The first item that matches, per call.
                    candidates = found if isinstance(found, list) else [found]
                    found = next((c for c in candidates
                                  if isinstance(c, str) and re.search(rule["match"], c)),
                                 None)
                    if found is None:
                        continue
                if isinstance(found, list) and (rule.get("flatten") or not found):
                    # A call whose list-of-records reshaped to nothing contributes no
                    # row, flatten or not -- an empty list is never a row of its own.
                    # A flattened list is acted on item by item, so a miss is no item.
                    kept, missed = _values_read(found)
                    unread += missed
                    gathered.extend(kept)
                else:
                    gathered.append(found)
            except SkillPathError as error:
                # Same reasoning as the extract loop: one bad call is skipped, not the whole rule.
                if not path_blocked:
                    blocked.append({"step": spec["id"], "reason": f"cannot collect {name}: {error}"})
                    path_blocked = True
                continue
        if unread:
            blocked.append(_unread(spec["id"], name, unread))
        if rule.get("unique"):
            gathered = list(dict.fromkeys(gathered))
        if gathered:
            extracted[name] = gathered
    # `combine` merges in union order, so the cap trims the tail, never the ask.
    for name, rule in (spec.get("combine") or {}).items():
        merged: list = []
        unread = 0
        for source in rule.get("union", []):
            value = facts.get(source) or extracted.get(source) or []
            for item in (value if isinstance(value, list) else [value]):
                if item is None:
                    # A union is acted on item by item; a miss holds no place in it.
                    unread += 1
                elif item not in merged:
                    merged.append(item)
        if unread:
            blocked.append(_unread(spec["id"], name, unread))
        if rule.get("limit"):
            merged = merged[: rule["limit"]]
        # A union of nothing is nothing gathered, not an answer of "empty".
        if merged:
            extracted[name] = merged

    # `compute` runs on the server, in passes: a rule may read what another rule in the
    # same step produces, and a store may hand the rules back in its own order.
    computed_blocked, refused, pending = _computed(spec, dict(spec.get("compute") or {}), facts, extracted, excluded)
    blocked.extend(computed_blocked)
    computed_missing = list(pending) + refused

    undecided = []
    known = {**facts, **extracted}
    for name, rule in (spec.get("derive") or {}).items():
        decided = _derive(rule, known)
        if decided is None:
            undecided.append(name)
            if rule["from"] in known:
                # The source arrived, but every row was unusable -- a read failure,
                # not an absence.
                reason = (f"cannot decide {name}: {rule['from']} arrived but no row "
                          "could be read, so the branch was not taken")
            else:
                reason = (f"cannot decide {name}: {rule['from']} was never "
                          "extracted, so the branch was not taken")
            blocked.append({"step": spec["id"], "reason": reason})
        else:
            extracted[name] = decided

    # A value the step says it produces and did not is always recorded, whichever rule
    # was meant to make it. A `produces` name that is also a `compute` name left in
    # `computed_missing` is one gap, not two, so the merge dedupes across both parts.
    promised = (list(spec.get("extract") or {}) + list(spec.get("collect") or {})
                + list(spec.get("combine") or {}) + list(spec.get("produces") or []))
    unresolved = list(dict.fromkeys(
        [name for name in dict.fromkeys(promised) if name not in extracted] + computed_missing))
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
        # Where a mapped term sits in an ontology; injected so tests can stub it.
        self.lookup = lookup
        # Where each run's Working Record is kept; without it results stay in memory only.
        self.records = records
        # `ask` puts the model in the loop as an oracle, never as the scheduler: the
        # server frames each question, validates the answer and stops after MAX_REPAIRS.
        self.ask = ask
        self._runs: dict[str, dict] = {}

    def start(self, inputs: dict, run_id: str | None = None) -> dict:
        # A host that already names its runs passes the id in.
        run_id = run_id or uuid.uuid4().hex
        # The graph's constants are facts from the first step; no step has to produce them.
        self._runs[run_id] = {**new_run({**(self.graph.get("constants") or {}), **inputs}),
                              "run_id": run_id}
        return {"run_id": run_id, "step": self._peek(run_id)}

    def state(self, run_id: str) -> dict:
        return self._runs[run_id]

    def _peek(self, run_id: str) -> dict | None:
        run = self._runs[run_id]
        return next_step(self.graph, done=run["done"] + run["skipped"],
                         facts=run["facts"])

    def _repair(self, spec, step, repair, results, failures, run, made):
        """Ask for a better argument value and retry, at most MAX_REPAIRS times.

        Returns the calls that actually produced the results handed back, so a
        caller passing them to absorb or the Working Record reads the repaired
        arguments instead of the ones that failed.
        """
        original = repair_value(repair, step["calls"], run["facts"])
        problem = repair_problem(spec, repair, results, original)
        if problem is None:
            return results, failures, step["calls"]
        argument = repair["argument"]
        question = question_for(
            step["id"], "repair", [argument], dict(run["facts"]),
            tool=step["calls"][0]["tool"], argument=argument, value=original,
            problem=problem,
        )
        answer = self.ask(question)
        asked(run, question, answer)
        # The answer maps the wanted name to a list of alternatives; a bare list is also taken.
        suggestions = answer.get(argument) if isinstance(answer, dict) else answer
        # A repair always starts from a call that returned nothing usable, even when
        # that was not an error; a successful repair must still be able to say so.
        pre_repair = failures or [{"tool": step["calls"][0]["tool"],
                                   "arguments": step["calls"][0]["arguments"],
                                   "error": problem}]
        retry_calls = step["calls"]
        retry_failures: list[dict] = []
        for candidate in (suggestions or [])[: self.MAX_REPAIRS]:
            retried, retry_failures = [], []
            retry_calls = repair_calls(spec, step["calls"], argument, candidate, run["facts"])
            made.extend(retry_calls)
            for call in retry_calls:
                try:
                    retried.append(self.execute(call["tool"], call["arguments"]))
                except Exception as exc:                   # noqa: BLE001
                    # Its empty slot stays, so the calls after it in this batch keep
                    # their own loop item -- same reasoning as the main call loop.
                    retry_failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                           "error": f"{type(exc).__name__}: {exc}"})
                    retried.append(None)
            if resolved(spec, repair, retried, candidate):
                run["facts"][argument] = candidate
                kept = [{**f, "repaired_by": candidate} for f in pre_repair]
                return retried, kept + retry_failures, retry_calls
            results = retried
        run["blocked"].append({
            "step": step["id"],
            "reason": (f"{argument}={original!r} could not be resolved after "
                       f"{self.MAX_REPAIRS} suggested alternatives"),
        })
        # The failure the repair started from is kept, so a source outage never reads
        # to the reader as a wrong identifier.
        return results, pre_repair + retry_failures, retry_calls

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
        return recomputed(spec, placed_mapping(spec, outcome, self.lookup), run["facts"])

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
                # A broken tool must not end the run, and its empty slot stays, so the
                # calls after it keep their own loop item.
                failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                 "error": f"{type(exc).__name__}: {exc}"})
                results.append(None)
                continue
            results.append(result)
            if is_upstream_failure(result):
                # A source failure reported inside the answer is a failed call, not an empty extraction.
                failures.append({"tool": call["tool"], "arguments": call["arguments"],
                                 "error": upstream_failure_text(result)})

        repair = spec.get("repair")
        # The calls that produced `results`: the step's own calls, unless a repair
        # substituted a candidate argument, in which case downstream reads must see
        # the repaired arguments too.
        effective_calls = step["calls"]
        if repair and self.ask:
            results, failures, effective_calls = self._repair(
                spec, step, repair, results, failures, run, made)

        if self.records is not None:
            record = WorkingRecord(self.records, run_id)
            for n, (call, payload) in enumerate(zip(effective_calls, results)):
                record.put_result(step["id"], n, call["tool"], call["arguments"], payload)
            outcome = absorb_recorded(record, self.graph.get("tables"), spec, effective_calls,
                                      run["facts"])
            run.setdefault("evidence", []).extend(outcome.pop("evidence"))
            outcome.pop("resolved")
            outcome.pop("repair_problem")
        else:
            outcome = absorb(spec, results, run["facts"],
                             items=loop_items(spec, effective_calls), calls=effective_calls)
        delegated = spec.get("delegate") or []
        if delegated:
            # Web search and code live on the agent, so the run asks it to make these
            # calls with its own tools and hand back the named facts.
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
        # A name an extraction or compute already supplied is never put to the model.
        wants = [n for n in (spec.get("judge") or []) if n not in outcome["facts"]]
        if wants:
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
    """Wrap ToolUniverse's dispatch so the runner sees what the agent sees.

    `execute_tool` JSON-decodes a string return and wraps any non-dict as {"result": ...};
    doing the same here means extraction paths written against a trace work in the runner.
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
