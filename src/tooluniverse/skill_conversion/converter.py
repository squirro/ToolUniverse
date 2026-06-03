"""Conversion orchestrator (DSR-508).

Ties the pure pieces together: classify → extract refs → ground via the adapter →
substitute seeded-unavailable families → assemble + SAVE the converter prompt →
call the injected ``judge``. The ``judge`` (the judgment transforms) is filled by
the agent-in-the-loop in v1; a stub in tests. Analysis skills are excluded without
ever invoking the judge.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .prompt import build_converter_prompt, render_grounded_facts
from .registry_adapter import RegistryAdapter
from .servability import classify, parse_router_analysis_skills
from .substitution import is_substitutable, substitute
from .tool_refs import extract_tool_refs

# prompt-string in → converted-body-string out.
Judge = Callable[[str], str]


@dataclass(frozen=True)
class ConvertedSkill:
    """The result of converting one skill."""

    name: str
    servable: bool
    reason: str
    body: str | None
    prompt_path: Path | None
    escalations: tuple[str, ...]


class Converter:
    """Convert a servable TU skill bundle into a Squirro persona body."""

    def __init__(self, *, adapter: RegistryAdapter, judge: Judge,
                 golden_source: str, golden_persona: str):
        self.adapter = adapter
        self.judge = judge
        self.golden_source = golden_source
        self.golden_persona = golden_persona

    def convert(self, skill_dir, *, router_md: str, prompt_out, direction: str = "disease") -> ConvertedSkill:
        skill_dir = Path(skill_dir)
        name = skill_dir.name
        skill_md = (skill_dir / "SKILL.md").read_text()

        analysis = parse_router_analysis_skills(router_md)
        s = classify(name, skill_md, analysis)
        if not s.servable:
            return ConvertedSkill(name, False, s.reason, None, None, ())

        facts = [self.adapter.resolve(r) for r in extract_tool_refs(skill_md)]
        available = [f for f in facts if f.available]
        subs = [substitute(f, self.adapter, direction)
                for f in facts if not f.available and is_substitutable(f.name)]
        unavailable = [f.name for f in facts
                       if not f.available and not is_substitutable(f.name)]
        escalations = tuple(sub.original for sub in subs if sub.escalate)

        block = render_grounded_facts(available, subs, unavailable)
        prompt = build_converter_prompt(
            target_skill_md=skill_md,
            golden_source=self.golden_source,
            golden_persona=self.golden_persona,
            grounded_facts_block=block,
        )
        prompt_out = Path(prompt_out)
        prompt_out.parent.mkdir(parents=True, exist_ok=True)
        prompt_out.write_text(prompt)

        body = self.judge(prompt)
        return ConvertedSkill(name, True, s.reason, body, prompt_out, escalations)
