"""A capped result must never be presented as a complete one.

Two paired guards. The first reads the source: a function that takes the first N of a
collection and never mentions a total, a truncation, or what is available hands the agent a
partial list that looks whole. The second reads the registry: a tool that accepts a limit
and declares no companion total in its return schema cannot tell the agent it was capped
even if it wanted to. A full page is evidence of truncation, not of completeness.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

__all__ = [
    "DISCLOSURE_TERMS",
    "LIMIT_INPUTS",
    "SliceFinding",
    "ToolFinding",
    "undisclosed_slices",
    "tools_without_a_total",
]

# Observed in the complying half of the corpus, as substrings, so `total_count` and
# `truncation_warning` both match. `remaining` is absent because no slicing function here
# uses it, so including it would be guessing.
DISCLOSURE_TERMS = ("total", "truncat", "available", "incomplete", "overflow",
                    "has_more", "next")

# Input names that cap a result set. A short list then has two possible causes, the cap or
# the data, and the caller cannot tell them apart without a companion field.
LIMIT_INPUTS = ("limit", "max_results", "maxresults", "page_size", "size", "top_n",
                "n_results", "max_records", "num_results", "retmax")


class SliceFinding:
    """A function that caps a collection and never says so."""

    def __init__(self, path: Path, line: int, function: str):
        self.path = path
        self.line = line
        self.function = function

    @property
    def message(self) -> str:
        return f"{self.path}:{self.line}: {self.function}() caps a result and discloses nothing"

    def __repr__(self) -> str:
        return f"<SliceFinding {self.path}:{self.line} {self.function}>"


class ToolFinding:
    """A tool that accepts a limit and declares no companion total."""

    def __init__(self, name: str, source: str, limits: list[str]):
        self.name = name
        self.source = source
        self.limits = limits

    @property
    def message(self) -> str:
        return (f"{self.source}: {self.name} accepts {', '.join(self.limits)} "
                f"but its return_schema declares no total or truncated field")

    def __repr__(self) -> str:
        return f"<ToolFinding {self.name}>"


def _takes_first_n(node: ast.AST) -> bool:
    """``x[:N]`` -- a post-hoc cap. Not ``x[a:b]``, not ``x[::2]``, not ``x[:]``."""
    if not isinstance(node, ast.Subscript) or not isinstance(node.slice, ast.Slice):
        return False
    sl = node.slice
    return sl.lower is None and sl.step is None and sl.upper is not None


def _discloses(func: ast.AST) -> bool:
    try:
        text = ast.unparse(func).lower()
    except Exception:
        return True  # cannot read it, do not accuse it
    return any(term in text for term in DISCLOSURE_TERMS)


def undisclosed_slices(root: Path | str) -> list[SliceFinding]:
    """Functions that cap a collection without disclosing it, one pass over the tree.

    Judged per function rather than per slice: a function that caps three lists and reports
    one total has disclosed, and demanding a note beside every slice would report code that
    is already right.
    """
    root = Path(root)
    findings: list[SliceFinding] = []
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except (SyntaxError, OSError):
            continue
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not any(_takes_first_n(n) for n in ast.walk(func)):
                continue
            if _discloses(func):
                continue
            findings.append(
                SliceFinding(path.relative_to(root), func.lineno, func.name)
            )
    return findings


def _limit_inputs(properties: dict) -> list[str]:
    found = []
    for key in properties:
        low = str(key).lower()
        if any(low == name or low.endswith("_" + name) for name in LIMIT_INPUTS):
            found.append(str(key))
    return sorted(found)


def tools_without_a_total(data_dir: Path | str) -> list[ToolFinding]:
    """Tools that accept a limit and declare no companion total, in name order.

    The return schema is searched as text rather than walked: the shapes vary, and any of
    them tells the agent what it needs.
    """
    data_dir = Path(data_dir)
    findings: list[ToolFinding] = []
    for path in sorted(data_dir.rglob("*.json")):
        try:
            defs = json.loads(path.read_text())
        except Exception:
            # silent-swallow: a malformed file is another guard's problem; report what can be read.
            continue
        if not isinstance(defs, list):
            continue
        for tool in defs:
            if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
                continue
            properties = (tool.get("parameter") or {}).get("properties") or {}
            if not isinstance(properties, dict):
                continue
            limits = _limit_inputs(properties)
            if not limits:
                continue
            schema = json.dumps(tool.get("return_schema") or {}).lower()
            if any(term in schema for term in DISCLOSURE_TERMS):
                continue
            findings.append(
                ToolFinding(tool["name"], str(path.relative_to(data_dir)), limits)
            )
    return sorted(findings, key=lambda f: f.name)
