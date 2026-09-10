"""How many calls a Skill Run may have in flight per tool source.

A rate limit belongs to the source (openFDA, ChEMBL, PubMed), not to the skill,
so the table is data beside the worker and a process author never writes it.
Ceilings start conservative and are raised only after a measured run.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

TABLE_PATH = Path(__file__).parent / "data" / "skill_ceilings.json"
DEFAULT_CEILING = 2


@lru_cache(maxsize=1)
def _table() -> dict:
    return json.loads(TABLE_PATH.read_text())


def source_of(tool: str) -> str:
    """The source family of a tool name: longest known prefix, else its first word."""
    prefixes = _table()["prefixes"]
    hits = [p for p in prefixes if tool.startswith(p)]
    if hits:
        return prefixes[max(hits, key=len)]
    return tool.split("_", 1)[0].lower()


def ceiling_for(tool: str) -> int:
    return int(_table()["ceilings"].get(source_of(tool), DEFAULT_CEILING))
