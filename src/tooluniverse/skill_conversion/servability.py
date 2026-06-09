"""Servability classifier (ADR-0007 / DSR-508).

A TU skill is *servable* through the Squirro router + get_skill architecture iff it
needs only API/DB tools — no local file/compute input. The authoritative *analysis*
(file-input) set is the master router's enumerated STEP-2 routing list; per-skill
``paths:`` frontmatter / RULE-ZERO body language corroborate analysis skills the
router omits. The router-list parser does double duty for DSR-510 router-trim.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ROUTER_SKILL_RE = re.compile(r"tooluniverse-[a-z0-9-]+")
_PATHS_FRONTMATTER_RE = re.compile(r"^paths\s*:", re.M)
_RULE_ZERO_RE = re.compile(r"rule\s*zero", re.I)
# The master router enumerates its data-file ANALYSIS skills in a STEP-2 clause:
# "...pick a sub-skill name from this exact list (never invent): tooluniverse-X (..),
# tooluniverse-Y (..). Use for CSV/...". Only those are analysis. The router's BODY is a
# full routing table that ALSO names research/clinical/discovery skills (which ARE
# servable) — so scope to the enumerated clause, NOT the whole document.
_ANALYSIS_LIST_RE = re.compile(r"this exact list[^:]*:(.*?)(?:\bUse for\b|\bSTEP\b|\")", re.S | re.I)


@dataclass(frozen=True)
class Servability:
    """Whether a skill is servable, with a human-readable reason."""

    servable: bool
    reason: str


def parse_router_analysis_skills(router_md: str) -> frozenset[str]:
    """The analysis-skill set = the ``tooluniverse-<name>`` skills enumerated in the
    master router's STEP-2 "this exact list (never invent): … Use for …" clause, minus
    the router's own name. Scoped to that clause so the router body's full routing table
    (which names servable research skills too) is not swept in. Empty if no clause."""
    m = _ANALYSIS_LIST_RE.search(router_md)
    region = m.group(1) if m else ""
    return frozenset(_ROUTER_SKILL_RE.findall(region)) - {"tooluniverse"}


def classify(name: str, skill_md: str, analysis_skills: frozenset[str]) -> Servability:
    """Classify a skill as servable or analysis (ADR-0007)."""
    if name in analysis_skills:
        return Servability(False, f"{name} is in the master router's analysis-skill list")
    if _PATHS_FRONTMATTER_RE.search(skill_md):
        return Servability(False, "declares a paths: frontmatter (file-input)")
    if _RULE_ZERO_RE.search(skill_md):
        return Servability(False, "body declares RULE ZERO data-folder precedence")
    return Servability(True, "no analysis signal (router list, paths:, RULE ZERO)")
