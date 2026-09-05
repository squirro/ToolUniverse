"""Find broad exception handlers that hide a failure from the agent (DSR-659).

A tool that catches everything and returns an empty value tells the agent nothing went
wrong. The agent reads zero rows as a real negative -- "no interactions reported" rather
than "the source was unreachable" -- and writes a confident wrong answer. That is the same
defect DSR-666 fixed at the envelope level, seen at its source.

**A log does not count as surfacing the failure.** Server logs are not the agent's channel.
A handler whose whole body is ``logger.warning(...)`` still returns nothing to the caller,
so logging statements are transparent here: they are removed before asking what the body
reduces to.

This is containment, not remediation. The count is frozen; existing debt stays and new code
cannot add to it. Most of the population is upstream, and rewriting it would conflict with
every fork sync.

Measured 2026-08-12: 299 handlers across 117 modules, before the optional-dependency
exemption. The ticket's figure of 245 across 110 does not reproduce -- the corpus has grown,
and treating logging as transparent counts the log-and-fall-through shape that a literal
reading of "reduces to pass" misses.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

__all__ = ["Finding", "PRAGMA", "find_in_source", "scan"]

# Catching these is catching everything. A narrow `except KeyError` is a decision; this is
# an absence of one.
_BROAD = {"Exception", "BaseException"}

# Words that mean the handler passed the failure on rather than hiding it. Checked only in
# returns and assignments -- never in calls, so `logger.warning(...)` cannot rescue a
# handler by containing the word "warning".
_DIAGNOSTIC = ("error", "status", "reason", "detail", "message", "warning", "failure",
               "note", "diagnostic")

# Values that carry no information to the caller.
_EMPTY = (None, "", [], {}, (), 0, False)

_LOG_CALLS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log",
              "print"}

# ``# silent-swallow: <reason>``. The reason is required: a bare pragma is a way to silence
# the guard without thinking, which is how a ratchet stops meaning anything.
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
        return ast.literal_eval(stmt.value) in _EMPTY
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False


def _mentions_diagnostic(stmt: ast.stmt) -> bool:
    try:
        text = ast.unparse(stmt).lower()
    except Exception:
        return False
    return any(word in text for word in _DIAGNOSTIC)


def _probes_an_optional_import(node: ast.Try) -> bool:
    """Whether the guarded block only imports something.

    ``try: import cupy / except Exception: pass`` is correct as written -- the absence of an
    optional dependency is not a failure to report, it is the question being asked. Exempted
    structurally rather than by pragma so that the exemption needs no edit to upstream files,
    which re-sync from ``mims-harvard:main``.
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

    Re-raising is not swallowing. A return or assignment naming the failure is not
    swallowing. Everything else that reduces to pass, continue, an empty return, or a bare
    fall-through is.
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
