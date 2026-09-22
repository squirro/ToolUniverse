#!/usr/bin/env python3
"""Generate the list of non-ToolUniverse tools the agent can call (DSR-661).

The persona linter has to answer "does this name resolve to anything the agent can call".
ToolUniverse's own ``data/**/*.json`` answers only part of that: the Squirro agent also
carries web search, the dedicated connectors and the internal-data retriever, none of
which appear in the registry. Their names live in ``config/agents.json`` in the delivery
repo, which this submodule cannot read when it is checked out standalone as the
``squirro/ToolUniverse`` fork -- so the names are generated into a JSON file beside the
linter and committed.

**The name the model sees is ``custom_name``, with spaces turned into underscores** (an
OpenAI function name cannot contain a space). It is never ``display_name``, which is only
the Studio UI label. That distinction is the whole point of this file: the five broken
names found in 2026-08 -- ``Exa_Web_Search``, ``Brave_Search``, ``Perplexity_Search_Llm``,
``Web_Search``, ``internal_data`` -- are all underscored display labels, and accepting
``display_name`` here would hide every one of them.

Usage::

    python3 gen_external_tools.py [path/to/config/agents.json]

Missing either required agent is a hard error rather than an empty list. A silently short
list would mark real tools as phantoms and the linter would be switched off within a day.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# libs/tooluniverse/deploy -> repo root
DEFAULT_SOURCE = HERE.parents[2] / "config" / "agents.json"
OUTPUT = HERE / "served_external_tools.json"

# The agents whose toolkits define the surface, named by the maintainer 2026-08-11. Other
# agents in the file (regulatory retrievers, the avatar agent) carry tools these personas
# never address, and folding them in would clear names that are genuinely wrong.
AGENTS = (
    "General Research",
    "[DEV/TEST] General Research and TU emphasis",
)


def collect(agents: list) -> dict[str, list[str]]:
    """custom_name (and its underscored form) per agent, for the two agents that matter."""
    by_agent: dict[str, list[str]] = {}
    for agent in agents:
        name = agent.get("name")
        if name not in AGENTS:
            continue
        names: set[str] = set()
        for tool in agent.get("toolkit", {}).get("tools") or []:
            if tool.get("enabled") is False:
                continue
            custom = tool.get("custom_name")
            if not custom:
                continue
            names.add(custom)
            names.add(custom.replace(" ", "_"))
        by_agent[name] = sorted(names)
    return by_agent


def main(argv: list[str]) -> int:
    source = Path(argv[1]) if len(argv) > 1 else DEFAULT_SOURCE
    if not source.is_file():
        print(f"no such file: {source}", file=sys.stderr)
        return 2

    by_agent = collect(json.loads(source.read_text()))

    missing = [name for name in AGENTS if name not in by_agent]
    if missing:
        # The delivery repo's dev branch carries these; a feature branch may be pinned to an
        # older export listing entirely different agents. Generating from that would produce
        # a plausible but wrong list, so refuse.
        print(
            "agents.json does not contain " + ", ".join(repr(m) for m in missing)
            + f"\n  read: {source}"
            + "\n  it holds: " + ", ".join(sorted(by_agent)) or "(none of them)",
            file=sys.stderr,
        )
        print("  take config/agents.json from the delivery repo's dev branch.",
              file=sys.stderr)
        return 1

    union = sorted({n for names in by_agent.values() for n in names})
    OUTPUT.write_text(json.dumps({
        "_source": "config/agents.json (delivery repo, dev branch)",
        "_field": "custom_name, plus its spaces-to-underscores form; never display_name",
        "_agents": list(AGENTS),
        "_regenerate": "python3 deploy/gen_external_tools.py [path/to/agents.json]",
        "per_agent": by_agent,
        "tools": union,
    }, indent=2) + "\n")
    print(f"{len(union)} external tool names -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
