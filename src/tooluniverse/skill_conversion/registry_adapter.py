"""Grounded, cache-first registry adapter (ADR-0006 / DSR-507).

The LLM converter never *asserts* a tool name — it asks this adapter to ``resolve``
one into a grounded **ToolFact** (exists / signature / availability / id-format
quirk). Resolution is cache-first: a hit returns the cached fact; a miss performs
one live **registry probe** (injected — SMCP ``get_tool_info`` in production, a stub
in tests) and writes the result back. Existence/signature/availability are
probed-and-cached; id-format quirks and key-gated unavailability are **hand-seeded**
from the disease-research learnings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

# A probe takes a tool name and returns {"exists": bool, "signature": dict|None}.
Probe = Callable[[str], dict]


# --- hand-seeded facts from the disease-research learnings -------------------
# id-format quirks are NOT auto-derivable from a registry listing; they are seeded
# here and grown by the verifier.

_EFOID_QUIRK = (
    "OpenTargets efoId args use the UNDERSCORE form (e.g. MONDO_0008315, "
    "EFO_0001663), NOT the colon form (MONDO:0008315) — colon silently returns "
    "an empty result."
)


def default_quirk(tool_name: str) -> Optional[str]:
    """Hand-seeded id-format quirk for a tool, or None."""
    if tool_name.endswith("efoI") or "_dise_efoI" in tool_name:
        return _EFOID_QUIRK
    return None


# Key-gated families with no API key on these clusters → unavailable. The converter
# drops/substitutes them (e.g. OpenTargets for gene-disease in place of DisGeNET);
# that substitution is the converter's concern, not the adapter's.
_UNAVAILABLE_PREFIXES = ("OMIM", "DisGeNET")


def default_unavailable(tool_name: str) -> bool:
    """True if a tool is hand-seeded as unavailable (no API key) on this cluster."""
    return tool_name.startswith(_UNAVAILABLE_PREFIXES)


@dataclass(frozen=True)
class ToolFact:
    """One grounded datum about a TU tool on a given cluster."""

    name: str
    exists: bool
    signature: Optional[dict]
    available: bool
    quirk: Optional[str]


def make_smcp_probe(call: Callable[[str], dict]) -> Probe:
    """Adapt a SMCP ``get_tool_info`` caller into the :data:`Probe` contract.

    ``call(tool_name)`` performs a single-name ``get_tool_info`` and returns its RAW
    result. ⚠️ ``get_tool_info`` is a **batch** meta-tool (its arg is ``tool_names``, a
    list) whose result is ``{"total_found": N, "tools": [{"name","parameter",...}]}``.
    A **not-found** name is NOT an error — it echoes a STUB tool with that name but
    ``total_found == 0``; and a *multi-name* batch **truncates ``tools[]`` to ~16**
    regardless of ``total_found``. So existence MUST key on ``total_found >= 1`` plus an
    exact-name match — never on the mere presence of a ``name`` (which the stub also has),
    and the caller MUST request one name at a time to avoid truncation. The live MCP
    session is injected at ``call``; this parse is pure. (Verified against sr-dev SMCP,
    DSR-508 — the earlier flat ``{name, parameter_schema}`` contract was wrong.)
    """

    def probe(tool_name: str) -> dict:
        result = call(tool_name)
        if not isinstance(result, dict) or result.get("total_found", 0) < 1:
            return {"exists": False, "signature": None}
        match = next(
            (t for t in result.get("tools", []) if t.get("name") == tool_name), None
        )
        if match is None:
            return {"exists": False, "signature": None}
        return {"exists": True, "signature": match.get("parameter")}

    return probe


class RegistryAdapter:
    """Cache-first / live-on-miss resolver of tool names to grounded ToolFacts."""

    def __init__(
        self,
        cluster: str,
        probe: Probe,
        cache: Optional[dict] = None,
        quirk_seed: Callable[[str], Optional[str]] = default_quirk,
        unavailable_seed: Callable[[str], bool] = default_unavailable,
    ):
        self.cluster = cluster
        self.probe = probe
        self.cache = cache if cache is not None else {}
        self.quirk_seed = quirk_seed
        self.unavailable_seed = unavailable_seed

    def resolve(self, tool_ref: str) -> ToolFact:
        key = (self.cluster, tool_ref)  # per-cluster namespacing
        if key in self.cache:
            return self.cache[key]

        # Short-circuit: a seeded-unavailable tool is not probed (the seed wins,
        # saving a live call on a tool the converter will drop/substitute).
        if self.unavailable_seed(tool_ref):
            fact = ToolFact(
                name=tool_ref,
                exists=False,
                signature=None,
                available=False,
                quirk=self.quirk_seed(tool_ref),
            )
        else:
            probed = self.probe(tool_ref)
            exists = probed["exists"]
            fact = ToolFact(
                name=tool_ref,
                exists=exists,
                signature=probed.get("signature"),
                # Invariant: available ⟹ exists. A tool that isn't there can't be
                # used; the seed only ever subtracts availability, never adds it.
                available=exists,
                quirk=self.quirk_seed(tool_ref),
            )

        self.cache[key] = fact
        return fact
