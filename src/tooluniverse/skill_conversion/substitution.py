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

# Seeded family-prefix → {direction → (candidate alternatives, rationale)}. The
# substitute is DIRECTIONAL: a disease-centric query holds an efoId (so a disease→target
# tool helps); a target/gene-centric query does not, so it needs a gene→variant route or
# escalates. Harvested from the disease-research port + grounded on sr-dev.
_SUBSTITUTIONS: dict[str, dict[str, tuple[tuple[str, ...], str]]] = {
    "OMIM": {
        "disease": (("OpenTargets_get_asso_targ_by_dise_efoI", "ClinVar_search_variants",
                     "gwas_get_variants_for_trait"),
                    "OMIM key-gated; disease→gene via OpenTargets assoc + ClinVar + GWAS."),
        "target": (("ClinVar_search_variants", "gnomad_get_gene_constraints"),
                   "OMIM key-gated; gene→disease via ClinVar pathogenic variants + gnomAD constraint."),
        "drug": ((), "OMIM (gene-disease) has no drug-centric substitute; omit."),
    },
    "DisGeNET": {
        "disease": (("OpenTargets_get_asso_targ_by_dise_efoI",),
                    "DisGeNET key-gated; disease→target via OpenTargets association-targets."),
        "target": (("ClinVar_search_variants",),
                   "DisGeNET key-gated; gene→disease via ClinVar (curated associations unavailable)."),
        "drug": ((), "DisGeNET (gene-disease) has no drug-centric substitute; omit."),
    },
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


def substitute(fact: ToolFact, adapter: RegistryAdapter, direction: str = "disease") -> Substitution:
    """Build a grounded, DIRECTION-appropriate substitution for an unavailable ``fact``.

    ``direction`` is the converted skill's query orientation ('disease' | 'target' | 'drug').
    Candidates are re-grounded through the adapter; escalate if none resolve available."""
    prefix = _family(fact.name)
    if prefix is None:
        return Substitution(fact.name, (), f"No seeded substitute for {fact.name}", True)
    by_dir = _SUBSTITUTIONS[prefix]
    candidates, rationale = by_dir.get(
        direction, ((), f"No {direction}-direction substitute seeded for {fact.name}"))
    grounded = tuple(c for c in candidates if adapter.resolve(c).available)
    return Substitution(fact.name, grounded, rationale, escalate=not grounded)
