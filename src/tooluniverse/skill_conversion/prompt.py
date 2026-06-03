"""Assemble the converter prompt (DSR-508).

The prompt is the convert-time artifact: a golden-pair few-shot (the disease-research
SKILL.md → converged persona — the diff *is* the transform spec), an explicit
10-transform checklist, a grounded tool-facts block (available tools w/ signatures +
quirks; unavailable → substitution), and the target SKILL.md. The agent-in-the-loop
``judge`` consumes this string and emits the converted body.
"""

from __future__ import annotations

from .registry_adapter import ToolFact
from .substitution import Substitution

# The ten transforms, classified in ADR-0006. The LLM applies the judgment ones
# (1, 3, 6, 7, 8, 10); the harness has already applied the registry-lookup ones
# (4, 5, 9) into the grounded-facts block and 2 is mechanical.
TRANSFORM_CHECKLIST = """\
Apply these transforms (the golden pair shows each in action):
1. JUDGMENT — strip filesystem/report-file scaffolding → a chat OUTPUT CONTRACT
   (emit ONE GFM-markdown report; PDF-export is the deliverable).
2. MECHANICAL — purge every <...> placeholder; pass REAL resolved ids, never examples.
3. JUDGMENT — restructure to call execute_tool DIRECTLY with the named tool per
   dimension (tight step budget; find_tools only as a fallback).
4. DONE BY HARNESS — tool names are grounded below; use exactly those, assert none.
5. DONE BY HARNESS — unavailable tools are dropped/substituted below.
6. JUDGMENT — convert grading PROSE into deterministic lookup TABLES keyed on data
   already in hand (e.g. OpenTargets score → T1-T4; clinical stage → T1-T4).
7. JUDGMENT — turn permissive wording into hard MUST rules (grade EVERY row; never
   leave a graded column blank when the datum exists).
8. JUDGMENT — sequence breadth-before-depth: one primary call per dimension FIRST,
   enrichment only after every dimension has its primary call.
9. DONE BY HARNESS — per-tool id-format quirks are in the grounded facts (e.g. efoId
   underscore form).
10. JUDGMENT — preserve honest data-limits (mark "No data available"; don't fabricate).
"""


def render_grounded_facts(
    available: list[ToolFact],
    substitutions: list[Substitution],
    unavailable: list[str] = (),
) -> str:
    """Render the grounded tool-facts block injected into the converter prompt."""
    lines: list[str] = ["## AVAILABLE TOOLS (grounded on this cluster — use exactly these names)"]
    for f in available:
        quirk = f"  [QUIRK: {f.quirk}]" if f.quirk else ""
        sig = f" signature={f.signature}" if f.signature else ""
        lines.append(f"- {f.name}{sig}{quirk}")
    if substitutions:
        lines.append("")
        lines.append("## UNAVAILABLE → SUBSTITUTE")
        for s in substitutions:
            if s.escalate:
                lines.append(f"- {s.original}: NO grounded alternative — ESCALATE TO HUMAN. {s.rationale}")
            else:
                lines.append(f"- {s.original}: SUBSTITUTE with {', '.join(s.alternatives)}. {s.rationale}")
    if unavailable:
        lines.append("")
        lines.append("## UNAVAILABLE — DO NOT CALL (referenced by the skill but not on this cluster; no grounded substitute)")
        for name in unavailable:
            lines.append(f"- {name}")
    return "\n".join(lines)


def build_converter_prompt(
    *,
    target_skill_md: str,
    golden_source: str,
    golden_persona: str,
    grounded_facts_block: str,
) -> str:
    """Assemble the full converter prompt from its four parts + the transform checklist."""
    return f"""\
# Task: convert a ToolUniverse SKILL.md into a hardened Squirro persona body

You are converting a TU skill into a Squirro chat persona. Study the GOLDEN PAIR
(a source skill and its converged, live-proven conversion), apply the TRANSFORM
CHECKLIST, use ONLY the GROUNDED TOOLS, and emit the converted body for the TARGET.

{TRANSFORM_CHECKLIST}

# GOLDEN PAIR — SOURCE (tooluniverse-disease-research/SKILL.md)
{golden_source}

# GOLDEN PAIR — CONVERTED (deploy/persona-disease-research.md)
{golden_persona}

# GROUNDED TOOL FACTS (this cluster)
{grounded_facts_block}

# TARGET SKILL TO CONVERT
{target_skill_md}

# OUTPUT
Emit ONLY the converted persona body (markdown), in the style of the golden converted
persona. No commentary.
"""
