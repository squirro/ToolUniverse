"""Extract candidate ToolUniverse tool names from a SKILL.md (DSR-508).

Permissive by design: matches backtick-quoted identifiers containing an underscore
(TU tool names: ``OpenTargets_get_…``, lowercase ``gwas_get_…``). The grounding
step (RegistryAdapter) filters non-existent matches via ``exists`` — so a little
over-capture is harmless; the converter prompt surfaces only resolved-available tools.
"""

from __future__ import annotations

import re

# Backtick-quoted identifier with ≥1 underscore, starting with a letter.
_TOOL_REF_RE = re.compile(r"`([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)`")


def extract_tool_refs(skill_md: str) -> list[str]:
    """Ordered, de-duplicated candidate tool names quoted in ``skill_md``."""
    seen: dict[str, None] = {}
    for m in _TOOL_REF_RE.finditer(skill_md):
        seen.setdefault(m.group(1), None)
    return list(seen)
