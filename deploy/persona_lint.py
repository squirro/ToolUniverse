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


def excluded_tool_names(dockerfile_text: str) -> set[str]:
    """Tool names the shipped image removes, parsed from its ``--exclude-tools``.

    The image is the authority on what is served, so the list is read rather than
    copied — a duplicated list drifts, and a drifted list is how a skill ends up
    naming a tool nobody serves.

    ``--exclude-tools`` takes ``nargs='+'`` and is deliberately the last flag, so
    everything after it is a tool name. Anything before it (``--max-workers 15``)
    is not.
    """
    marker = '"--exclude-tools"'
    start = dockerfile_text.find(marker)
    if start == -1:
        return set()
    tail = dockerfile_text[start + len(marker):]
    end = tail.find("]")
    if end != -1:
        tail = tail[:end]
    return {
        name
        for name in re.findall(r'"([^"]+)"', tail)
        if not name.startswith("--")
    }


def unserved_tools(text: str, excluded: set[str]) -> list[str]:
    """Excluded tool names a skill body tells the agent to call, in sorted order.

    Matched against the excluded SET rather than by identifier shape: prose is full
    of things that look like tool names, and a shape-based matcher would flag them.
    Code spans are NOT stripped here, unlike the inline-link check — a name in
    backticks inside a skill body is still an instruction to call it.
    """
    return sorted(
        name for name in excluded
        if re.search(rf"\b{re.escape(name)}\b", text)
    )


# Wording that marks a tool as unreachable rather than instructing a call. Kept
# narrow and literal: "not optional" and "not recommended" are ordinary emphasis in
# these bodies, so a general "not ..." rule would suppress real instructions.
_UNAVAILABLE = (
    "do not call",
    "never call",
    "not available",
    "not deployed",
    "not served",
    "not functional",
    "non-functional",
    "unavailable",
    "no data available",
)


def _marks_unavailable(line: str) -> bool:
    low = line.lower()
    return any(marker in low for marker in _UNAVAILABLE)


def live_unserved_tools(text: str, excluded: set[str]) -> list[str]:
    """Excluded tools the body actively tells the agent to CALL, in sorted order.

    ``unserved_tools`` counts every mention, which over-reports: a body that already
    warns "DO NOT CALL ``X`` — it errors" is doing the right thing and must not be
    punished for naming X in order to forbid it. This keeps only mentions that would
    actually send the agent at a tool the image does not serve, so the rule can be an
    error rather than a warning.

    A mention is discounted when the line carrying it says the tool is unreachable, or
    when it sits under a block whose opening line is such a directive. Suppression is
    per-mention, never per-body: one caveat about one tool must not clear a whole
    phase, so a tool named positively anywhere still counts.
    """
    live: set[str] = set()
    for block in re.split(r"\n\s*\n", body_text(text)):
        lines = block.splitlines()
        if not lines or _marks_unavailable(lines[0]):
            continue
        for line in lines:
            if _marks_unavailable(line):
                continue
            live.update(
                name for name in excluded
                if re.search(rf"\b{re.escape(name)}\b", line)
            )
    return sorted(live)


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

    # A body that tells the agent to call an unserved tool sends it to
    # "Tool 'X' not found even after loading tools" -- which reads as a registry
    # bug and burns an iteration against a default cap of 10 (DSR-644).
    #
    # This shipped as a warning because 33 of the 76 bodies tripped it on arrival
    # and a linter that is red on arrival gets switched off. All 76 are reconciled
    # now (every dead call substituted or declared a gap), so it holds the line as
    # an error. It counts live_unserved_tools, not unserved_tools: a body that
    # names a tool in order to FORBID it is correct and must still pass.
    dockerfile = Path(deploy_dir) / "Dockerfile"
    if dockerfile.is_file():
        excluded = excluded_tool_names(dockerfile.read_text())
        for name in live_unserved_tools(text, excluded):
            errors.append(f"instructs a call to {name}, which the image does not serve")

    return errors, warnings
