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


# Appended to EVERY served body (DSR-631). The citation contract is a property of the
# serving surface — the Squirro chat renderer promotes only LINK-bearing footnotes —
# not of any one skill, so it rides here rather than being copied into 76 bodies where
# it drifts. A loaded body is BINDING for the turn, which is exactly why this trailer
# must supersede any older References convention a body still carries.
CITATION_CONTRACT = """

---
# Citation contract (serving surface — SUPERSEDES any References format stated above)
Cite with markdown footnotes `[^n^]`, and every footnote definition MUST carry a link —
the chat renderer promotes only link-bearing footnotes; a bare tool-name reference
renders broken. Link preference: (1) the `source_url` field in the tool's result
envelope, (2) a link built from a returned ID (record page or API query URL). A result
with neither is attributed INLINE as `(via tool_name)` — never as a footnote and never
a "tool + parameters" log entry. The report's References section is ONLY the numbered
footnote definitions, each `[^n^]: [description](url)`.

BEFORE YOU EMIT the References section, check every footnote: the target must begin
`https://` or `http://`. A bare domain (`clinicaltrials.gov`), an internal handle
(`squirro_source#...`), a tool name, or a `(#)` placeholder all render BROKEN — the
reader sees nothing. A footnote you cannot give a real URL becomes an inline
`(via tool_name)` instead. Drop it from References; do not leave it linkless.

# Tool-call form (how EVERY database tool above is reached)
Call `execute_tool(tool_name="<exact tool name>", arguments={...})` — exactly those two
parameters. NEVER pass a tool's own parameters at the top level of the call. If a call
is rejected with "unexpected keyword argument", that is what happened — retry with the
two-parameter form, the stray parameters wrapped inside `arguments`.

Give every parameter the type its schema declares — some tools want a list of terms,
others want those same terms in one string, and you cannot tell by looking at the
value. "is not of type 'array'" and "is not of type 'string'" are both common. On
either, call `get_tool_info(["<tool name>"])`, read the declared type, and send that
shape. Do not swap the shape and retry blind.

# Tool names: use, don't guess
The tool names written in this skill are the tool names. NEVER guess or invent a tool
name that looks plausible — an unregistered name fails the whole step. If you need a
tool this skill does not name, find the real one with `grep_tools("<substring>")` or
`find_tools("<keywords that appear in tool names and descriptions>")`, then call what
they return, spelled exactly as returned.

# Identifiers: resolve before you query
Database tools match identifiers EXACTLY and each database has its own format. Do not
guess one, do not reshape the user's, and do not assume one database's identifier works
in another. Resolve it first with the lookup/search tool for that database, then pass
back what it returned. A reply like "not found: <id>. Use <format>" means you guessed —
resolve it properly rather than trying another guess.
"""


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
    return path.read_text(encoding="utf-8") + CITATION_CONTRACT
