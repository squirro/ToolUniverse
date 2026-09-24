"""Which tool definitions the loader can actually reach.

A definition sitting under ``data/`` is not the same thing as a tool the server can serve:
the loader reads a configured set of category files plus a directory scan of
``data/remote_tools``, and anything else on disk is inert. Reachability is computed from the
loader's own configuration rather than from a copied list, because a duplicated list drifts
and a drifted list is how a skill ends up naming a tool nobody serves.
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
    "unreadable_definition_files",
    "unwired_definitions",
]

# Collections that are on disk, unreachable, and meant to be. Each says why, because an
# undeclared exception and a forgotten wiring bug look identical six months later.
DECLARED_UNWIRED: dict[str, str] = {
    # Not tools: records whose `type` is `endpoint` or `secret`. They carry a `name`, which
    # is the only reason a definition scan sees them at all.
    "api_keys_catalog.json": (
        "catalogue of API-key records, not tool definitions (type: endpoint/secret)"
    ),
    # A holding area for APIs that stopped working. default_config.py records an
    # "Archived at: ..." comment at each removed entry, so the removal was deliberate.
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
    and every ``*.json`` in ``data/remote_tools``, which is a directory scan, so a new file
    there is wired by being put there.
    """
    from ..default_config import default_tool_files

    data = data or data_dir()
    files = {Path(path).resolve() for path in default_tool_files.values()}
    files |= {path.resolve() for path in (data / "remote_tools").glob("*.json")}
    return files


def definitions_by_file(data: Path | None = None) -> dict[Path, list[str]]:
    """Tool names per file, for every file under ``data`` that holds tool definitions.

    A definition is an object with both a ``name`` and a ``type``. Files that are not a JSON
    list, and files that will not parse, are skipped rather than guessed at;
    ``unreadable_definition_files`` is where a broken one is reported.
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


def _is_definition(value) -> bool:
    return isinstance(value, dict) and isinstance(value.get("name"), str) and bool(value.get("type"))


def _holds_definitions(value: dict) -> bool:
    """An object that is a definition, or wraps a list of them: a definition file gone wrong,
    not one of the settings, schemas or indexes that also live under ``data/``."""
    return _is_definition(value) or any(
        isinstance(member, list) and any(_is_definition(item) for item in member)
        for member in value.values()
    )


def unreadable_definition_files(data: Path | None = None) -> dict[str, str]:
    """Definition files every scan skips, keyed by path relative to ``data``, with why.

    A file that will not parse is reported, because nothing can say what it held. An object
    at the top level is reported only when it holds a definition. Declared collections are
    omitted: the archive keeps half-written records on purpose.
    """
    data = data or data_dir()
    unreadable: dict[str, str] = {}
    for path in sorted(data.rglob("*.json")):
        relative = str(path.relative_to(data))
        if is_declared(relative):
            continue
        try:
            value = json.loads(path.read_text())
        except ValueError as exc:
            unreadable[relative] = f"not valid JSON: {exc}"
            continue
        if isinstance(value, dict) and _holds_definitions(value):
            unreadable[relative] = "holds tool definitions but is not a list; the loader reads lists"
    return unreadable


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

    Declared collections are omitted. What is left is a wiring bug: a definition that can be
    referenced by name and can never be served.
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
    against. Reading every JSON under ``data`` instead accepts the archived and catalogue
    names as though they were servable.
    """
    data = data or data_dir()
    reachable = reachable_files(data)
    return {
        name
        for path, names in definitions_by_file(data).items()
        if path.resolve() in reachable
        for name in names
    }
