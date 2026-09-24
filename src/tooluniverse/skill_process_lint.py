"""A Skill Process names no entity: the lint a conversion must pass.

Pure: a process in, violations out. It cannot see knowledge tied to a class of drug or
disease that names no entity; only a held-out question from another class shows that.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "skill_process_lint.json"


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def source_maxima() -> dict:
    return _data()["maxima"]


def benchmark_entities(skill: str) -> list[str]:
    return _data()["entities"].get(skill, [])


def known_violations() -> dict:
    return _data()["known_violations"]


_PLACEHOLDER = re.compile(r"\{[^{}]*\}")
_INSTRUCTION = re.compile(r"<[^<>]*>")          # an instruction to the agent, in a delegate
_OPERATOR = re.compile(r"\b(?:AND|OR|NOT)\b")
_TWO_WORDS = re.compile(r"[^\W\d_]\S*\s+\S*[^\W\d_]")


@dataclass(frozen=True)
class Violation:
    kind: str
    step: str
    field: str
    text: str

    @property
    def message(self) -> str:
        return f"{self.step}: {self.field} [{self.kind}] {self.text!r}"


def _is_free_text(value: str) -> bool:
    """More than placeholders, the source's operators, and one constant token."""
    rest = _OPERATOR.sub(" ", _INSTRUCTION.sub(" ", _PLACEHOLDER.sub(" ", value)))
    return bool(_TWO_WORDS.search(rest.strip()))


PROSE_ARGUMENTS = ("task",)      # instructions to the agent's code tool, not a query


def _call_arguments(step: dict):
    for key in ("calls", "delegate"):
        for n, call in enumerate(step.get(key) or []):
            for field in ("arguments", "optional_arguments"):
                for name, value in (call.get(field) or {}).items():
                    yield f"{key}[{n}].{field}.{name}", name, value


def _prose(process: dict):
    """Every text the agent reads as instruction: where it is, and what it says."""
    if process.get("report"):
        yield "(process)", "report", process["report"]
    for step in process.get("steps", []):
        for field in ("label", "notes"):
            if step.get(field):
                yield step["id"], field, step[field]
        for field, name, value in _call_arguments(step):
            if name in PROSE_ARGUMENTS and isinstance(value, str):
                yield step["id"], field, value


def _named(text: str, entities: list[str]) -> list[str]:
    """Entities the text names; a symbol in capitals is matched as written, so IDS is not IDs."""
    return [entity for entity in entities
            if re.search(r"(?<!\w)" + re.escape(entity) + r"(?!\w)", text,
                         0 if entity.isupper() else re.IGNORECASE)]


def _narrowing(step: dict, maxima: dict) -> list[Violation]:
    """A call that takes less than its source gives: by a default, or by hand without a reason."""
    found = []
    for n, call in enumerate(step.get("calls") or []):
        arguments = call.get("arguments") or {}
        for name, most in (maxima.get(call["tool"]) or {}).items():
            field = f"calls[{n}].arguments.{name}"
            if name not in arguments:
                found.append(Violation("source_default", step["id"], field,
                                       f"{name} is not set, the source allows {most}"))
            elif (isinstance(arguments[name], int) and arguments[name] < most
                  and not step.get("narrowed")):
                found.append(Violation("narrowed_without_reason", step["id"], field,
                                       f"{name}={arguments[name]}, the source allows {most}"))
    return found


def violations(process: dict, entities: list[str] | None = None,
               maxima: dict | None = None) -> list[Violation]:
    """`entities`: the drugs, diseases and genes of this skill's benchmark questions.
    `maxima`: tool -> {paging argument: the most the source returns in one call}."""
    found = []
    for step_id, field, text in _prose(process):
        found.extend(Violation("named_entity", step_id, field, entity)
                     for entity in _named(text, entities or []))
    for step in process.get("steps", []):
        for field, name, value in _call_arguments(step):
            if name not in PROSE_ARGUMENTS and isinstance(value, str) and _is_free_text(value):
                found.append(Violation("free_text_argument", step["id"], field, value))
        found.extend(_narrowing(step, maxima or {}))
        for name, rule in (step.get("collect") or {}).items():
            lists = [f for f in (rule.get("fields") or []) if "[]" in f] \
                if isinstance(rule, dict) else []
            if len(lists) > 1:
                found.append(Violation(
                    "parallel_lists", step["id"], f"collect.{name}",
                    f"{len(lists)} lists in one row ({', '.join(lists)}): collect the records "
                    "as rows instead"))
    return found
