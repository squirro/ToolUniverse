"""Static linter for the A/B prod persona bodies (DSR-544 / DSR-545).

Pure functions over persona text — no live agent, no network, no fixtures. This is the
only automatable seam for the persona work: it guards the Studio char cap, the
footnote-only link rule, and (the highest-value check) that every ``get_skill("name")``
named in a body resolves to a served skill body. The complement — does the routing
actually work — is judged by hand in Squirro chat.

The Studio cap measures the *pasted body*, not the documentation header: the existing
``persona.md`` records "body below the comment is 3,997 chars", so ``body_text`` strips a
leading ``<!-- ... -->`` HTML comment before measuring.
"""

from __future__ import annotations

import re
from pathlib import Path

# Production Studio persona cap on swiss-rockets.squirro.com.
PROD_CHAR_CAP = 10_000
# Below this we only *warn* (an arm under-using its budget) — padding to the cap would
# confound the A/B, so it is never a hard failure. See DSR-544.
BUDGET_WARN_FLOOR = 6_000

_LEADING_COMMENT = re.compile(r"^\s*<!--.*?-->\s*", re.DOTALL)
# Inline markdown links [text](url) — forbidden; Squirro's react-markdown drops them.
# Footnote refs [^1] and footnote defs [^1]: ... are fine and must not match.
_INLINE_LINK = re.compile(r"(?<!\!)\[[^\]^][^\]]*\]\([^)]+\)")
_GET_SKILL = re.compile(r"""get_skill\(\s*["']([a-z0-9-]+)["']\s*\)""")
# Code spans/blocks render literally, so a [x](y) inside them is NOT a link. Strip
# fenced ```...``` blocks and inline `...` spans before hunting links.
_CODE = re.compile(r"```.*?```|`[^`]*`", re.DOTALL)


def body_text(text: str) -> str:
    """Persona body as the Studio cap sees it: a leading HTML comment header stripped."""
    return _LEADING_COMMENT.sub("", text, count=1)


def body_len(text: str) -> int:
    return len(body_text(text))


def inline_links(text: str) -> list[str]:
    """Inline ``[text](url)`` links in the body (footnote refs and code spans excluded)."""
    return _INLINE_LINK.findall(_CODE.sub(" ", body_text(text)))


def get_skill_names(text: str) -> list[str]:
    """Skill names referenced via ``get_skill("name")`` in the body, in order."""
    return _GET_SKILL.findall(body_text(text))


def served_skill_names(deploy_dir: str | Path) -> set[str]:
    """Names served via get_skill: ``persona-<name>.md`` minus the dispatcher personas."""
    deploy = Path(deploy_dir)
    excluded = {"router", "router-spike", "smcp-only", "prod-base", "prod",
                "prod-demo-4k", "prod-demo-10k", "prod-neutral-4k",
                "prod-weighted-4k", "doriano"}
    names = set()
    for p in deploy.glob("persona-*.md"):
        name = p.stem[len("persona-"):]
        if name not in excluded:
            names.add(name)
    return names


def check_body(text: str, deploy_dir: str | Path) -> tuple[list[str], list[str]]:
    """Return ``(errors, warnings)`` for one persona body.

    Errors are hard failures (over cap, inline links, unknown skill name). A short body
    is only a warning — never pad to the cap.
    """
    errors: list[str] = []
    warnings: list[str] = []

    n = body_len(text)
    if n > PROD_CHAR_CAP:
        errors.append(f"body is {n} chars, over the {PROD_CHAR_CAP} Studio cap")
    elif n < BUDGET_WARN_FLOOR:
        warnings.append(f"body is {n} chars, under-using the {PROD_CHAR_CAP} budget")

    for link in inline_links(text):
        errors.append(f"inline markdown link (use footnotes): {link}")

    served = served_skill_names(deploy_dir)
    for name in get_skill_names(text):
        if name not in served:
            errors.append(f'get_skill("{name}") names no served persona-{name}.md')

    return errors, warnings
