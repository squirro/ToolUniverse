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


@dataclass(frozen=True)
class Servability:
    """Whether a skill is servable, with a human-readable reason."""

    servable: bool
    reason: str


def parse_router_analysis_skills(router_md: str) -> frozenset[str]:
    """The analysis-skill set = every ``tooluniverse-<name>`` the master router routes
    to (its STEP-2 list), minus the router's own name."""
    return frozenset(_ROUTER_SKILL_RE.findall(router_md)) - {"tooluniverse"}


def classify(name: str, skill_md: str, analysis_skills: frozenset[str]) -> Servability:
    """Classify a skill as servable or analysis (ADR-0007)."""
    if name in analysis_skills:
        return Servability(False, f"{name} is in the master router's analysis-skill list")
    if _PATHS_FRONTMATTER_RE.search(skill_md):
        return Servability(False, "declares a paths: frontmatter (file-input)")
    if _RULE_ZERO_RE.search(skill_md):
        return Servability(False, "body declares RULE ZERO data-folder precedence")
    return Servability(True, "no analysis signal (router list, paths:, RULE ZERO)")
