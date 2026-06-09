"""Serve converted skill bodies as ``get_skill`` tool-results (ADR-0005 / DSR-505).

The SMCP ``get_skill(name)`` tool returns a converted skill's hardened SOP body on
demand, so one router persona can drive N ToolUniverse skills. This module holds the
*pure*, dependency-free loader behind that tool so it is unit-testable without
``fastmcp``/``squirro`` (which ``smcp.py`` imports at module top).

The ``name`` argument originates from the LLM, so resolution is strict and fails
closed: charset-restricted, no path separators, resolved path must stay inside the
served directory (no traversal).
"""

from __future__ import annotations

import re
from pathlib import Path

# Skill ids are kebab/snake lowercase (e.g. "disease-research"). Anything else —
# path separators, uppercase, dots beyond a trailing ".md" — is rejected.
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class SkillNotFound(ValueError):
    """Raised when ``get_skill`` is asked for a name with no served body."""


def normalize_skill_name(name: str) -> str:
    """Normalize a requested skill name to its file stem.

    Accepts ``"disease-research"`` or ``"disease-research.md"``. Rejects empties,
    path separators, and out-of-charset names (no traversal, no surprises).
    """
    if not name or not name.strip():
        raise SkillNotFound("empty skill name")
    stem = name.strip()
    if stem.endswith(".md"):
        stem = stem[:-3]
    stem = stem.strip().lower()
    if not _NAME_RE.match(stem):
        raise SkillNotFound(f"invalid skill name: {name!r}")
    return stem


def available_skills(skills_dir: str | Path) -> list[str]:
    """List the served skill ids (``*.md`` stems) in ``skills_dir`` (sorted)."""
    directory = Path(skills_dir)
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.md"))


def load_skill_body(skills_dir: str | Path, name: str) -> str:
    """Return the served body for ``name`` from ``skills_dir``.

    Raises ``SkillNotFound`` if the directory is missing, the name is invalid, or
    no body matches. The error for an unknown-but-valid name lists what *is*
    available, so the agent (and a human reading the transcript) can self-correct.
    """
    directory = Path(skills_dir)
    if not directory.is_dir():
        raise SkillNotFound(f"skills_dir not found: {skills_dir}")
    stem = normalize_skill_name(name)
    path = directory / f"{stem}.md"
    # Defense in depth: even past the charset check, the resolved file must live
    # directly inside the served directory.
    if path.resolve().parent != directory.resolve():
        raise SkillNotFound(f"invalid skill name: {name!r}")
    if not path.is_file():
        raise SkillNotFound(
            f"no served skill {stem!r}; available: {available_skills(directory)}"
        )
    return path.read_text(encoding="utf-8")
