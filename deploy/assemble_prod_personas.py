#!/usr/bin/env python3
"""Assemble + lint the single prod persona body (DSR-543).

Single source of truth: one ``persona-prod-base.md`` body (the High-Order Strategic
Research Agent, lifted verbatim from prod and enriched with non-routing guidance + the
neutral ToolUniverse pointer, binding rule, and Tool Balance) — supersedes the retired
neutral/weighted A/B (DSR-544/DSR-545).

Emits one paste-ready Studio body, prefixed with a documentation header (an HTML
comment, which does not count toward the 10 000-char cap), then lints it. Exits nonzero
on any hard failure so the assembler doubles as the static seam.

    python assemble_prod_personas.py          # assemble + lint, report char budget
"""

from __future__ import annotations

import sys
from pathlib import Path

import persona_lint

HERE = Path(__file__).resolve().parent
BASE = HERE / "persona-prod-base.md"
PROD_OUT = HERE / "persona-prod.md"

PROD_HEADER = """\
<!--
Production persona for the General Research Agent on swiss-rockets.squirro.com
(single persona; supersedes the neutral/weighted A/B — DSR-543/544/545 retired).
Assembled by assemble_prod_personas.py from persona-prod-base.md — DO NOT edit this
file by hand; edit the base and re-run. Apply on swiss-rockets.squirro.com
(10 000-char cap) via Studio -> Persona: paste the body BELOW this comment.
-->
"""


def assemble() -> list[tuple[Path, str]]:
    base = BASE.read_text()
    return [(PROD_OUT, PROD_HEADER + "\n" + base)]


def main() -> int:
    failed = False
    for path, text in assemble():
        path.write_text(text)
        errors, warnings = persona_lint.check_body(text, HERE)
        n = persona_lint.body_len(text)
        status = "FAIL" if errors else "ok"
        print(f"[{status}] {path.name}: body {n}/{persona_lint.PROD_CHAR_CAP} chars")
        for w in warnings:
            print(f"    warn: {w}")
        for e in errors:
            print(f"    error: {e}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
