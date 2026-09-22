"""The question corpus must match the set of bodies the image actually serves.

Two ways this drifts, both silent:

* a newly converted skill lands in ``deploy/`` and the sweep never probes it;
* a persona body that is NOT a skill lands in ``deploy/`` and gets served as one,
  so ``find_skill`` ranks it against the real skills. This is exactly what the
  six ``persona-prod-*`` A/B bodies were doing.

The blocklist is read out of the Dockerfile rather than restated here, so the
image and the corpus cannot disagree about what "served" means.

This lives beside the bodies, like the persona-lint guards: the delivery repo
tracks no ``libs/`` entry on any branch, so the same test over there could never
run in CI — it would be reaching across a repo boundary for its own subject.
"""

import re
from pathlib import Path

import pytest
import yaml

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
DOCKERFILE = DEPLOY / "Dockerfile"
CORPUS = DEPLOY / "skill_audit" / "questions.yaml"

pytestmark = pytest.mark.unit


def _blocked_patterns() -> list[str]:
    """The `case "$name" in ...) continue ;;` guard in the served-skills stage."""
    line = next(text for text in DOCKERFILE.read_text().splitlines()
                if 'case "$name" in' in text)
    match = re.search(r'case "\$name" in\s*(.+?)\)\s*continue', line)
    assert match, line
    return [p.strip() for p in match.group(1).split("|")]


def _is_blocked(name: str) -> bool:
    return any(re.fullmatch(p.replace("*", ".*"), name)
               for p in _blocked_patterns())


def served_skills() -> set[str]:
    return {p.stem[len("persona-"):] for p in DEPLOY.glob("persona-*.md")
            if not _is_blocked(p.stem[len("persona-"):])}


def corpus_skills() -> set[str]:
    rows = yaml.safe_load(CORPUS.read_text())["skills"]
    return {r["skill"] for r in rows}


def test_every_served_skill_has_a_probe_question():
    missing = sorted(served_skills() - corpus_skills())
    assert not missing, (
        f"served but never probed: {missing} — add a question to "
        "deploy/skill_audit/questions.yaml, or block the body in the Dockerfile "
        "if it is not a skill")


def test_no_question_names_a_skill_the_image_does_not_serve():
    stale = sorted(corpus_skills() - served_skills())
    assert not stale, f"question for an unserved skill: {stale}"


def test_the_agent_facing_personas_are_not_served_as_skills():
    """A persona is applied to the AGENT; serving one through get_skill puts it
    in the find_skill index competing with real skills."""
    leaked = sorted(n for n in served_skills() if n.startswith("prod"))
    assert not leaked, f"persona bodies served as skills: {leaked}"


def test_no_question_is_reused_for_two_skills():
    """Copy-pasting one question across two skills makes both rows meaningless:
    whichever skill loads, one of the two is scored against a probe that was
    never written for it."""
    rows = yaml.safe_load(CORPUS.read_text())["skills"]
    seen: dict[str, str] = {}
    clashes = []
    for row in rows:
        key = " ".join(row["question"].split()).lower()
        if key in seen:
            clashes.append((seen[key], row["skill"]))
        seen[key] = row["skill"]
    assert not clashes, f"duplicate questions: {clashes}"
