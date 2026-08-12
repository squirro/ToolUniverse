"""A description may not name a parameter its own schema does not declare (DSR-665).

A narrow form of this rule already holds the line on Django-style ``field__operator``
filters. This widens it to parameter names generally, so the class stays closed as new
tools arrive. The defect is the same in both: the prose is ahead of the contract, and a
model reading the description constructs a call it has no way to validate.

**Widening naively is unusable.** Every backticked snake_case token in the prose gives 62
hits, and reading them shows why: most name something real that simply is not an input to
this tool. Four subtractions, each earned by inspecting the hits rather than guessed at:

* the tool's own **return-schema** fields -- describing what comes back is not an
  instruction to pass it;
* **registry tool names** -- prose naming another tool is a cross-reference;
* the **base of a declared filter** -- ``pref_name`` beside a declared
  ``pref_name__contains`` is the underlying field being explained, not a second parameter;
* a token whose **sentence also names another tool** -- "use ``gnomad_get_gene`` to find a
  gene's ``canonical_transcript_id``" is pointing at that tool's field and says so.

The fourth is the one the ticket's acceptance criteria turn on. A description naming
another tool's parameter *without* saying which tool is a genuine defect and still reports;
one that names the tool is a legitimate hand-off.

That takes 62 to 4. All four remaining were read by hand and are enumerated *values* of a
declared parameter -- ``dataset`` "defaults to ``gnomad_r3``", ``field`` has "common
choices". They are waived by name rather than cleared by a fifth heuristic, because
inventing one more rule to clear the last finding is how a guard stops describing anything.

**The finding is that this corpus has no true positive of this class today.** All 62 hits
resolve to legitimate prose. The rule therefore ships blocking at zero, and its value is
entirely in what it stops arriving.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

__all__ = ["WAIVED", "Finding", "load_tools", "undeclared_parameters"]

# Backticked snake_case. The bare (un-backticked) phrasing was measured too and is not
# usable: 946 hits naively, 686 after the same subtractions, because ordinary prose is full
# of species slugs, dataset ids and external field names that no filter can tell from a
# parameter. Requiring the backticks is what makes the token a citation rather than a word.
_TOKEN = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]*)*)`")

# A single word in backticks is usually prose -- measured, allowing them adds `only`,
# `null`, `df`, `result` and `params`. But a parameter may legitimately be one word
# (`organism`, `species`, `format`), and excluding those leaves a real gap. The registry
# decides rather than a stopword list: a one-word token counts only if some tool declares a
# parameter by that name. `organism` is declared somewhere and `null` is not.
_UNDERSCORED = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")


def declared_parameter_vocabulary(tools: dict[str, dict]) -> set[str]:
    """Every parameter name any tool in the registry declares."""
    vocabulary: set[str] = set()
    for tool in tools.values():
        properties = (tool.get("parameter") or {}).get("properties") or {}
        if isinstance(properties, dict):
            vocabulary.update(str(key) for key in properties)
    return vocabulary

# Hand-verified false positives that survive every subtraction above. Each is a value the
# prose offers for a parameter the tool does declare.
WAIVED: dict[str, dict[str, str]] = {
    "FDA_get_drug_label_info_by_field_value": {
        "id": "a 'common choices' value for the declared `field` parameter",
        "set_id": "a 'common choices' value for the declared `field` parameter",
        "indications_and_usage": "a 'common choices' value for the declared `field`",
        "dosage_and_administration": "a 'common choices' value for the declared `field`",
    },
    "gnomad_get_variant": {
        "gnomad_r3": "the documented default value of the declared `dataset` parameter",
    },
}


class Finding:
    """One description naming an input its schema does not declare."""

    def __init__(self, tool: str, token: str, sentence: str):
        self.tool = tool
        self.token = token
        self.sentence = sentence

    @property
    def message(self) -> str:
        return f"{self.tool}: describes `{self.token}`, which it does not declare"

    def __repr__(self) -> str:
        return f"<Finding {self.tool}.{self.token}>"


def load_tools(data_dir: Path | str) -> dict[str, dict]:
    """Every tool definition under ``data_dir``, keyed by name."""
    tools: dict[str, dict] = {}
    for path in sorted(Path(data_dir).rglob("*.json")):
        try:
            defs = json.loads(path.read_text())
        except Exception:
            # silent-swallow: a malformed definition file is test_no_duplicate_json_keys'
            # problem; this guard reports what it can read rather than failing for a file
            # it cannot.
            continue
        if not isinstance(defs, list):
            continue
        for tool in defs:
            if isinstance(tool, dict) and isinstance(tool.get("name"), str):
                tools[tool["name"]] = tool
    return tools


def _return_fields(tool: dict) -> set[str]:
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, dict):
                found.update(str(key) for key in props)
            for key, value in node.items():
                if key != "properties":
                    walk(value)
                elif isinstance(value, dict):
                    for sub in value.values():
                        walk(sub)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(tool.get("return_schema"))
    return found


def _prose(tool: dict) -> str:
    """Everything the model reads before calling: the tool description and each param's."""
    properties = (tool.get("parameter") or {}).get("properties") or {}
    parts = [tool.get("description") or ""]
    parts += [
        (spec or {}).get("description", "")
        for spec in properties.values()
        if isinstance(spec, dict)
    ]
    return " ".join(parts)


def _sentence_around(text: str, start: int, end: int) -> str:
    opens = text.rfind(".", 0, start) + 1
    closes = text.find(".", end)
    return text[opens: closes if closes != -1 else len(text)]


def undeclared_parameters(tools: dict[str, dict]) -> list[Finding]:
    """Descriptions naming an input the tool does not declare, in tool-name order."""
    names = set(tools)
    vocabulary = declared_parameter_vocabulary(tools)
    findings: list[Finding] = []

    for tool_name, tool in sorted(tools.items()):
        properties = (tool.get("parameter") or {}).get("properties") or {}
        if not isinstance(properties, dict) or not properties:
            continue

        declared = set(properties)
        # `pref_name` beside a declared `pref_name__contains` is the field the filter runs
        # on, being explained. Not a second parameter.
        filter_bases = {key.split("__")[0] for key in declared if "__" in key}
        returns = _return_fields(tool)
        waived = WAIVED.get(tool_name, {})
        prose = _prose(tool)

        seen: set[str] = set()
        for match in _TOKEN.finditer(prose):
            token = match.group(1)
            if not _UNDERSCORED.match(token) and token not in vocabulary:
                continue  # a backticked English word, not a parameter reference
            if token in seen or token in declared or token in filter_bases:
                continue
            if token in returns or token in names or token in waived:
                continue
            sentence = _sentence_around(prose, match.start(), match.end())
            # Naming another tool in the same sentence makes this its field, not ours.
            if any(other in sentence for other in names if other != tool_name):
                continue
            seen.add(token)
            findings.append(Finding(tool_name, token, sentence.strip()))

    return findings
