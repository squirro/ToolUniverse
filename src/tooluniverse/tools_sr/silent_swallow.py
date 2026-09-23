"""Find broad exception handlers that hide a failure from the agent.

A tool that catches everything and returns an empty value tells the agent nothing went
wrong, and the agent reads zero rows as a real negative. A log does not count as surfacing
the failure, because server logs are not the agent's channel, so logging statements are
transparent here and are removed before asking what the handler body reduces to. This is
containment: the count is frozen, existing debt stays and new code cannot add to it.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any

__all__ = ["Finding", "PRAGMA", "fingerprint", "find_in_source", "scan"]

# Catching these is catching everything: a narrow `except KeyError` is a decision, this is
# the absence of one.
_BROAD = {"Exception", "BaseException"}

# Words that mean the handler passed the failure on. Checked in returns and assignments
# only, so `logger.warning(...)` cannot rescue a handler by containing the word "warning".
_DIAGNOSTIC = ("error", "status", "reason", "detail", "message", "warning", "failure",
               "note", "diagnostic")

# Values that carry no information to the caller.
_EMPTY = (None, "", [], {}, (), 0, False)

# A bare token like this names no failure and no data; it is a success envelope's
# padding, not a diagnostic.
_SUCCESS = {"ok", "success", "true", "done", "none", "n/a"}

_LOG_CALLS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log",
              "print"}

# ``# silent-swallow: <reason>``. The reason is required so the guard cannot be silenced
# without stating why.
PRAGMA = re.compile(r"#\s*silent-swallow\s*:\s*(?P<reason>\S.*?)\s*$")


class Finding:
    """One handler that swallows a failure without telling the caller."""

    def __init__(self, path: Path, line: int, snippet: str):
        self.path = path
        self.line = line
        self.snippet = snippet

    def __repr__(self) -> str:
        return f"<Finding {self.path}:{self.line} {self.snippet!r}>"

    @property
    def message(self) -> str:
        return f"{self.path}:{self.line}: {self.snippet}"


def _is_broad(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    parts = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(isinstance(part, ast.Name) and part.id in _BROAD for part in parts)


def _is_logging(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return False
    func = stmt.value.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
    return name in _LOG_CALLS


def _returns_empty(stmt: ast.Return) -> bool:
    if stmt.value is None:
        return True
    try:
        value = ast.literal_eval(stmt.value)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    return _carries_nothing(value)


def _carries_nothing(value: Any) -> bool:
    """A value the caller learns nothing from, whether it is empty or merely wraps emptiness."""
    if isinstance(value, dict):
        return all(_carries_nothing(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return all(_carries_nothing(v) for v in value)
    if isinstance(value, str) and value.strip().lower() in _SUCCESS:
        return True
    return value in _EMPTY


def _mentions_diagnostic(stmt: ast.stmt) -> bool:
    """Whether the statement passes the failure on, rather than merely naming a key like one."""
    value = getattr(stmt, "value", None)
    if value is None:
        return False
    if isinstance(value, ast.Dict):
        for key, item in zip(value.keys, value.values):
            name = key.value.lower() if isinstance(key, ast.Constant) and isinstance(key.value, str) else ""
            if any(word in name for word in _DIAGNOSTIC) and not _is_empty_node(item):
                return True
        return False
    try:
        text = ast.unparse(value).lower()
    except Exception:
        return False
    return any(word in text for word in _DIAGNOSTIC)


def _is_empty_node(node: ast.expr) -> bool:
    try:
        return _carries_nothing(ast.literal_eval(node))
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False


def _probes_an_optional_import(node: ast.Try) -> bool:
    """Whether the guarded block only imports something.

    The absence of an optional dependency is not a failure to report, it is the question
    being asked. Exempted structurally rather than by pragma, so the exemption needs no
    edit to upstream files.
    """
    statements = [s for s in node.body if not isinstance(s, ast.Expr)]
    return bool(statements) and all(
        isinstance(s, (ast.Import, ast.ImportFrom)) for s in statements
    )


def _waived(lines: list[str], handler: ast.ExceptHandler) -> str | None:
    """The stated reason on a pragma inside this handler, if there is one."""
    start = handler.lineno - 1
    end = getattr(handler, "end_lineno", handler.lineno)
    for raw in lines[start:end]:
        match = PRAGMA.search(raw)
        if match:
            return match.group("reason")
    return None


def _swallows(handler: ast.ExceptHandler) -> bool:
    """Whether the handler ends up telling the caller nothing.

    Re-raising is not swallowing, nor is a return or assignment that names the failure.
    Everything that reduces to pass, continue, an empty return or a bare fall-through is.
    """
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return False

    remaining = []
    for stmt in handler.body:
        if _is_logging(stmt):
            continue  # a log is not the agent's channel
        if isinstance(stmt, (ast.Return, ast.Assign, ast.AnnAssign, ast.AugAssign)):
            if _mentions_diagnostic(stmt):
                return False
        remaining.append(stmt)

    if not remaining:
        return True  # logged, then fell through
    for stmt in remaining:
        if isinstance(stmt, (ast.Pass, ast.Continue)):
            continue
        if isinstance(stmt, ast.Return) and _returns_empty(stmt):
            continue
        return False
    return True


def find_in_source(source: str, path: Path | str = "<source>") -> list[Finding]:
    """Silent swallows in one module, in line order."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    exempt_handlers = {
        id(handler)
        for node in ast.walk(tree)
        if isinstance(node, ast.Try) and _probes_an_optional_import(node)
        for handler in node.handlers
    }

    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or id(node) in exempt_handlers:
            continue
        if not _is_broad(node) or not _swallows(node):
            continue
        if _waived(lines, node):
            continue
        snippet = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
        findings.append(Finding(Path(path), node.lineno, snippet))
    return sorted(findings, key=lambda f: f.line)


def fingerprint(finding: Finding) -> str:
    """One site's identity, stable when the file moves around it."""
    return hashlib.sha256(" ".join(finding.snippet.split()).encode()).hexdigest()[:12]


def scan(root: Path | str) -> list[Finding]:
    """Every silent swallow under ``root``, one pass, sorted by path then line."""
    root = Path(root)
    findings: list[Finding] = []
    for path in sorted(root.rglob("*.py")):
        try:
            source = path.read_text(errors="ignore")
        except OSError:
            continue
        for finding in find_in_source(source, path.relative_to(root)):
            findings.append(finding)
    return findings
