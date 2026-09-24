"""Saved Analyses: a user's saved conversation, replayed on new Inputs (ADR-0019).

A Saved Analysis has the shape of a Skill Process and runs on the same interpreter, but a
user makes it by saving, and nobody reviews it in a PR. Its only copy is a named graph under
`analyses/<prompt id>` in the `skill-processes` repository. SMCP is its only writer: the
Studio plugin forwards a confirmed save, and `save` checks that the definition can run
before anything is written, since no PR or round-trip test will ever see it.
"""

from __future__ import annotations

import re

from .skill_graph import graph_problems, undeclared_tables

ANALYSES_PREFIX = "analyses/"

# Squirro ids are URL-safe base64 tokens; anything else would be spliced into an IRI.
_PROMPT_ID = re.compile(r"[A-Za-z0-9_-]{8,64}")


class SavedAnalysisRefused(ValueError):
    """The save cannot be stored as it stands; the message says why."""


def analysis_skill(prompt_id: str) -> str:
    """The process id of the Saved Analysis for one Prompt Library entry."""
    if not isinstance(prompt_id, str) or not _PROMPT_ID.fullmatch(prompt_id):
        raise SavedAnalysisRefused(f"{prompt_id!r} is not a Prompt Library id")
    return ANALYSES_PREFIX + prompt_id


def problems(definition: dict) -> list[str]:
    """Why a definition could not run as a replay; empty when it can."""
    if not isinstance(definition, dict) or not definition.get("steps"):
        return ["it has no steps"]
    found = []
    if undeclared := undeclared_tables(definition):
        found.append(f"it collects {undeclared} without declaring them under `tables:`")
    return found + graph_problems(definition)


def save(store, prompt_id: str, definition: dict, author: str) -> str:
    """Check the definition, then write it as the prompt's Saved Analysis. Returns the IRI.

    The process id always comes from the prompt id, never from the body, so a save cannot
    overwrite a Skill Process or another prompt's analysis.
    """
    process = {**definition, "skill": analysis_skill(prompt_id)}
    if found := problems(process):
        raise SavedAnalysisRefused(f"the analysis cannot be replayed: {'; '.join(found)}")
    return store.publish(process, author=author, prompt_id=prompt_id)


def handle_save(body, token: str | None, expected_token: str, store) -> tuple[int, dict]:
    """The SMCP save route's logic: the shared token, then the body, then `save`.

    Only the Studio plugin holds the token, and it takes the author from the caller's
    authenticated Squirro client, so the author here is trusted because of the token.
    Returns the HTTP status and the JSON body.
    """
    import hmac

    if not token or not hmac.compare_digest(token.encode(), expected_token.encode()):
        return 401, {"error": "missing or wrong save token"}
    if not isinstance(body, dict):
        return 400, {"error": "the body must be a JSON object"}
    prompt_id, author, definition = (body.get(k) for k in ("prompt_id", "author", "definition"))
    if not author or not isinstance(author, str):
        return 400, {"error": "`author` is required"}
    if not isinstance(definition, dict):
        return 400, {"error": "`definition` must be an object"}
    try:
        iri = save(store, prompt_id, definition, author)
    except SavedAnalysisRefused as exc:
        return 422, {"error": str(exc)}
    return 200, {"iri": iri, "prompt_id": prompt_id}


async def replay(client, store, prompt_id: str, inputs: dict) -> dict:
    """Start a Replay of the prompt's Saved Analysis: the same start as a Skill Run."""
    from .skill_run_client import start

    try:
        skill = analysis_skill(prompt_id)
    except SavedAnalysisRefused as exc:
        return {"status": "error", "error": str(exc)}
    return await start(client, store, skill, inputs or {})
