"""The find_tools guidance must say KEYWORDS, not a description (DSR-630).

Measured on the live server: this deployment's finder is lexical (the LLM finder needs
an unset key and silently returns [], DSR-639), so intent-shaped queries fail where
keyword-shaped ones work — "is SSTR2 structurally tractable for a small molecule"
surfaces 1 relevant structural tool in its top 5, "protein structure" surfaces 5/5.
Every surface that tells the agent how to phrase a find_tools query must therefore say
keywords-that-appear-in-tool-names-and-descriptions, never "describe what you need".

Static text guards, in the style of the other registry-wide checks in this directory:
importing smcp pulls in fastmcp, so the docstring is read from source instead.
"""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "smcp.py"
DEPLOY = Path(__file__).resolve().parents[2] / "deploy"


def _find_tools_docstring() -> str:
    source = SRC.read_text()
    start = source.index("async def find_tools(")
    body = source[start:]
    match = re.search(r'"""(.*?)"""', body, re.DOTALL)
    assert match, "find_tools has no docstring"
    return match.group(1)


def test_find_tools_docstring_tells_the_agent_to_use_keywords():
    doc = _find_tools_docstring()
    assert "keyword" in doc.lower(), doc


def test_find_tools_docstring_does_not_ask_for_a_description_of_what_you_need():
    """The old wording — 'description of what you need' — is exactly the intent-shaped
    phrasing the lexical matcher cannot serve."""
    doc = _find_tools_docstring()
    assert "description of what you need" not in doc, doc


def test_the_prod_persona_phrases_the_find_tools_fallback_as_keywords():
    body = (DEPLOY / "persona-prod-base.md").read_text()
    line = next(l for l in body.splitlines() if "find_tools(" in l)
    assert "keyword" in line.lower(), line
