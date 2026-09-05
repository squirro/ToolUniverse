"""Which tool definitions the loader can actually reach (DSR-663).

A definition sitting under ``data/`` is not the same thing as a tool the server can serve.
The loader reads a configured set of category files -- ``default_tool_files`` -- plus a
directory scan of ``data/remote_tools``. Anything else on disk is inert.

That gap is invisible exactly where it matters. The name is in the registry files, so a
name check passes. It is not in the image's ``--exclude-tools``, so the exclusion check
passes too. And the agent still gets "Tool 'X' not found even after loading tools", which
reads as a registry bug rather than a mistake in the body and burns an iteration. This is
the population the persona linter structurally could not see.

Reachability is computed from the loader's own configuration rather than from a copied
list, for the same reason ``excluded_tool_names`` parses the Dockerfile: a duplicated list
drifts, and a drifted list is how a skill ends up naming a tool nobody serves.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = [
    "DECLARED_UNWIRED",
    "data_dir",
    "definitions_by_file",
    "is_declared",
    "reachable_files",
    "unwired_definitions",
]

# Collections that are on disk, unreachable, and meant to be. Each says why, because an
# undeclared exception and a forgotten wiring bug look identical six months later.
DECLARED_UNWIRED: dict[str, str] = {
    # Not tools. 39 records whose `type` is `endpoint` or `secret` -- the generated
    # catalogue of which API keys each tool family needs. They carry a `name`, which is the
    # only reason a definition scan sees them at all.
    "api_keys_catalog.json": (
        "catalogue of API-key records, not tool definitions (type: endpoint/secret)"
    ),
    # A holding area for APIs that stopped working. default_config.py already records an
    # "Archived at: ..." comment at each removed entry, so the wiring was removed on
    # purpose and the definitions were kept for the day the API returns.
    "broken_apis/": (
        "archived definitions for APIs that no longer respond; default_config.py records "
        "an 'Archived at:' comment where each was unwired"
    ),
}


def data_dir() -> Path:
    """The registry's data directory."""
    return Path(__file__).resolve().parents[1] / "data"


def reachable_files(data: Path | None = None) -> set[Path]:
    """Every file the loader reads, resolved.

    Two sources, matching ``ToolUniverse._read_all_tools``: the configured category files,
    and every ``*.json`` in ``data/remote_tools`` (that one is a directory scan, so a new
    file there is wired by being put there).
    """
    from ..default_config import default_tool_files

    data = data or data_dir()
    files = {Path(path).resolve() for path in default_tool_files.values()}
    files |= {path.resolve() for path in (data / "remote_tools").glob("*.json")}
    return files


def definitions_by_file(data: Path | None = None) -> dict[Path, list[str]]:
    """Tool names per file, for every file under ``data`` that holds tool definitions.

    A definition is an object with both a ``name`` and a ``type``. Files that are not a
    JSON list, and lists holding anything else, are skipped rather than guessed at.
    Unparseable files are skipped too: a malformed file is a different guard's problem
    (``test_no_duplicate_json_keys``) and this one must not fail for it.
    """
    data = data or data_dir()
    found: dict[Path, list[str]] = {}
    for path in sorted(data.rglob("*.json")):
        try:
            defs = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(defs, list):
            continue
        names = [
            tool["name"]
            for tool in defs
            if isinstance(tool, dict)
            and isinstance(tool.get("name"), str)
            and tool.get("type")
        ]
        if names:
            found[path] = names
    return found


def is_declared(relative: str) -> bool:
    """Whether this path is a declared-unwired file or sits under a declared directory."""
    normalised = relative.replace("\\", "/")
    for key in DECLARED_UNWIRED:
        if key.endswith("/"):
            if normalised.startswith(key):
                return True
        elif normalised == key:
            return True
    return False


def unwired_definitions(data: Path | None = None) -> dict[str, list[str]]:
    """Tool names the loader cannot reach, keyed by path relative to ``data``.

    Declared collections are omitted. What is left is a wiring bug: a definition that can
    be referenced by name and can never be served.
    """
    data = data or data_dir()
    reachable = reachable_files(data)
    unwired: dict[str, list[str]] = {}
    for path, names in definitions_by_file(data).items():
        if path.resolve() in reachable:
            continue
        relative = str(path.relative_to(data))
        if is_declared(relative):
            continue
        unwired[relative] = names
    return unwired


def servable_definition_names(data: Path | None = None) -> set[str]:
    """Every tool name the loader can actually reach.

    The complement of ``unwired_definitions``, and the set a name check should validate
    against. Reading every JSON under ``data`` instead -- which is the obvious thing to do
    -- accepts the archived and catalogue names as though they were servable.
    """
    data = data or data_dir()
    reachable = reachable_files(data)
    return {
        name
        for path, names in definitions_by_file(data).items()
        if path.resolve() in reachable
        for name in names
    }
