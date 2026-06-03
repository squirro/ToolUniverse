"""Substitute grounded alternatives for unavailable tools (DSR-512).

When the registry adapter reports ``available=False`` for a seeded-unavailable family
(OMIM, DisGeNET — no API key on these clusters), the converter must not drop the
section: it substitutes a grounded alternative (the disease-research learnings —
OpenTargets genetic_association + ClinVar + GWAS for OMIM; OpenTargets association-
targets for DisGeNET). Each candidate is **re-grounded through the adapter** — a
fallback can also be dead, in which case we escalate to a human (Option A), never
silently drop.
"""

from __future__ import annotations

from dataclasses import dataclass

from .registry_adapter import RegistryAdapter, ToolFact

# Seeded family-prefix → (candidate alternatives, rationale). Harvested from the
# disease-research port + each skill's "Fallback Chains" table.
_SUBSTITUTIONS: dict[str, tuple[tuple[str, ...], str]] = {
    "OMIM": (
        ("OpenTargets_get_asso_targ_by_dise_efoI", "ClinVar_search_variants",
         "gwas_get_variants_for_trait"),
        "OMIM has no API key on this cluster; cover gene-disease with OpenTargets "
        "genetic_association scores + ClinVar pathogenic variants + GWAS hits.",
    ),
    "DisGeNET": (
        ("OpenTargets_get_asso_targ_by_dise_efoI",),
        "DisGeNET has no API key; OpenTargets association-targets covers the "
        "gene-disease links DisGeNET would have text-mined.",
    ),
}


@dataclass(frozen=True)
class Substitution:
    """A grounded replacement plan for one unavailable tool."""

    original: str
    alternatives: tuple[str, ...]
    rationale: str
    escalate: bool  # True → no grounded alternative resolved; a human must intervene


def _family(tool_name: str) -> str | None:
    for prefix in _SUBSTITUTIONS:
        if tool_name.startswith(prefix):
            return prefix
    return None


def is_substitutable(tool_name: str) -> bool:
    """True iff ``tool_name`` belongs to a seeded-unavailable family with a substitute."""
    return _family(tool_name) is not None


def substitute(fact: ToolFact, adapter: RegistryAdapter) -> Substitution:
    """Build a grounded substitution for an unavailable ``fact`` (must be substitutable)."""
    prefix = _family(fact.name)
    if prefix is None:
        return Substitution(fact.name, (), f"No seeded substitute for {fact.name}", True)
    candidates, rationale = _SUBSTITUTIONS[prefix]
    grounded = tuple(c for c in candidates if adapter.resolve(c).available)
    return Substitution(fact.name, grounded, rationale, escalate=not grounded)
