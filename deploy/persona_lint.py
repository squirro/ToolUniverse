"""Static linter for the prod persona bodies.

Pure functions over persona text, with no live agent or network: they guard the Studio
char cap, the footnote-only link rule, and that every tool or skill a body names is one
the server serves. The cap measures the pasted body, so ``body_text`` strips a leading
HTML comment header before measuring.
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

# The server resolves names with shortening on, so a body may name either form.
MAX_TOOL_NAME_LENGTH = 45

_SRC = Path(__file__).resolve().parents[1] / "src"
REGISTRY_DATA = _SRC / "tooluniverse" / "data"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tooluniverse.tool_name_utils import shorten_tool_name  # noqa: E402

# Production Studio persona cap.
PROD_CHAR_CAP = 10_000
# Below this we only warn; a body is never padded to the cap.
BUDGET_WARN_FLOOR = 6_000

_LEADING_COMMENT = re.compile(r"^\s*<!--.*?-->\s*", re.DOTALL)
# Inline links, which the chat renderer drops. Footnote refs [^1] must not match.
_INLINE_LINK = re.compile(r"(?<!\!)\[[^\]^][^\]]*\]\([^)]+\)")
_GET_SKILL = re.compile(r"""get_skill\(\s*["']([a-z0-9-]+)["']\s*\)""")
# Code spans render literally, so a link inside one is not a link.
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
    """Tool names the shipped image removes, read from its ``--exclude-tools`` flag.

    Read rather than copied so the list cannot drift. The flag is deliberately last,
    so everything after it is a tool name.
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
    """Excluded tool names mentioned anywhere in a skill body, in sorted order.

    Matched against the excluded set, not by shape, so prose that looks like a tool
    name is not flagged. Code spans are not stripped: a backticked name is still a call.
    """
    return sorted(
        name for name in excluded
        if re.search(rf"\b{re.escape(name)}\b", text)
    )


# Wording that marks a tool as unreachable; kept literal so "not optional" cannot match.
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
    # "there is NO X tool deployed": the noun form of "not deployed".
    "tool deployed",
    # A body saying a tool "is excluded" relays the Dockerfile, not an instruction.
    "excluded",
)


def _marks_unavailable(line: str) -> bool:
    low = line.lower()
    return any(marker in low for marker in _UNAVAILABLE)


def live_unserved_tools(
    text: str, excluded: set[str], *, include_header: bool = False
) -> list[str]:
    """Excluded tools the body actively tells the agent to call, in sorted order.

    A mention on a line that says the tool is unreachable is discounted, so a body that
    forbids a tool still passes. ``include_header`` also scans the header, which
    get_skill serves raw.
    """
    live: set[str] = set()
    scanned = text if include_header else body_text(text)
    for block in re.split(r"\n\s*\n", scanned):
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


# --- does the referenced name exist at all? ---

# A backticked token; shape alone decides nothing, see _is_tool_shaped.
_BACKTICKED = re.compile(r"`([A-Za-z][A-Za-z0-9_]*)`")
# A prefix followed by digits is an ontology id, never a tool.
_ONTOLOGY_ID = re.compile(r"^[A-Za-z]+_\d+$")


# Registered programmatically in smcp.py, so absent from data/**/*.json.
PLATFORM_TOOLS = frozenset({"find_tools", "get_skill", "find_skill"})

# Squirro-side tools (web search, connectors), generated by gen_external_tools.py.
EXTERNAL_TOOLS_FILE = Path(__file__).resolve().parent / "served_external_tools.json"


def external_tool_names(path: str | Path | None = None) -> set[str]:
    """Non-ToolUniverse tools the agent can call, from the generated manifest.

    A missing or unreadable manifest gives the empty set, so the linter still runs in the fork.
    """
    manifest = Path(path) if path else EXTERNAL_TOOLS_FILE
    try:
        return set(json.loads(manifest.read_text())["tools"])
    except Exception:
        return set()


# Tokens the structural rules cannot classify that are still not tool names. Keep it small.
PHANTOM_ALLOWLIST = frozenset({
    # Response fields of tools with no return_schema, so the registry cannot see them.
    "aa_change", "age_at_diagnosis", "mutation_type",      # GDC / TCGA case records
    "active_site", "binding_site",                         # UniProt sequence features
    "best_structures",                                     # PDBe best-structures endpoint
    "cellular_component",                                  # GO aspect name
    "chr_pos_ref_alt", "chr_pos_ref_alt_example",          # OpenTargets variant key
    "combined_score",                                      # STRING edge score
    "highest_clinical_trial_phase",                        # OpenTargets indication edge
    "source_antigen_name",                                 # IEDB epitope key
    "splice_region_variant",                               # Sequence Ontology term
    # Family shorthand for the per-organism tools; no single tool has either name.
    "get_gene", "get_phenotypes",
})


def shorten(name: str) -> str:
    """The name the server would serve this tool under."""
    return shorten_tool_name(name, max_length=MAX_TOOL_NAME_LENGTH)


# Cached so a corpus run reads the definition files once, not once per body.
@lru_cache(maxsize=None)
def registry_tool_names(data_dir: str | Path) -> set[str]:
    """Every tool name declared in the registry's JSON, read without loading ToolUniverse.

    A full load takes minutes; the names are all in ``data/**/*.json``. Unparseable
    files are skipped, since a malformed file is another guard's problem.
    """
    names: set[str] = set()
    for path in Path(data_dir).rglob("*.json"):
        try:
            defs = json.loads(path.read_text())
        except Exception:
            continue
        if isinstance(defs, list):
            names.update(
                tool["name"]
                for tool in defs
                if isinstance(tool, dict) and tool.get("name")
            )
    return names


# Cached so a corpus run reads the definition files once, not once per body.
@lru_cache(maxsize=None)
def registry_parameter_names(data_dir: str | Path) -> set[str]:
    """Every parameter name any tool declares.

    Tool names and field names are shape-identical, so the absent-tool check asks the
    registry which tokens are parameters instead of guessing.
    """
    names: set[str] = set()
    for path in Path(data_dir).rglob("*.json"):
        try:
            defs = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(defs, list):
            continue
        for tool in defs:
            if not isinstance(tool, dict):
                continue
            params = (tool.get("parameter") or {}).get("properties") or {}
            if isinstance(params, dict):
                names.update(str(key) for key in params)
    return names


def _schema_property_names(node, out: set[str]) -> None:
    """Collect every ``properties`` key anywhere in a schema, at any depth."""
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            out.update(str(key) for key in props)
        for key, value in node.items():
            if key != "properties":
                _schema_property_names(value, out)
            elif isinstance(value, dict):
                for sub in value.values():
                    _schema_property_names(sub, out)
    elif isinstance(node, list):
        for item in node:
            _schema_property_names(item, out)


# Cached so a corpus run reads the definition files once, not once per body.
@lru_cache(maxsize=None)
def registry_return_field_names(data_dir: str | Path) -> set[str]:
    """Every field name any tool declares it returns, plus its ``fields`` list.

    Without it a body that documents what comes back reads as a body inventing tools.
    """
    names: set[str] = set()
    for path in Path(data_dir).rglob("*.json"):
        try:
            defs = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(defs, list):
            continue
        for tool in defs:
            if not isinstance(tool, dict):
                continue
            _schema_property_names(tool.get("return_schema"), names)
            declared = tool.get("fields")
            if isinstance(declared, dict):
                names.update(str(key) for key in declared)
            elif isinstance(declared, list):
                names.update(str(x) for x in declared if isinstance(x, str))
    return names


@lru_cache(maxsize=None)
def loader_reachable_names() -> frozenset[str]:
    """Tool names the loader can reach, not merely names present on disk.

    The disk scan also accepts archived and API-key records that carry a ``name``.
    Falls back to that scan if the wiring module cannot be imported.
    """
    try:
        from tooluniverse.tools_sr.wiring import servable_definition_names

        return frozenset(servable_definition_names())
    except Exception:
        return frozenset(registry_tool_names(REGISTRY_DATA))


def servable_names(registry_names: set[str]) -> set[str]:
    """Names the server answers to: each registry name plus its shortened form. Idempotent."""
    servable = set(registry_names)
    servable.update(shorten(name) for name in registry_names)
    return servable


def _is_tool_shaped(token: str) -> bool:
    if _ONTOLOGY_ID.match(token):
        return False
    # A bare prefix naming an accession family (`MONDO_`, `NM_`), not a call.
    if token.endswith("_"):
        return False
    # SCREAMING_CASE marks a placeholder, a constant or an enum value, never a tool.
    if token.isupper():
        return False
    # Requiring an underscore keeps the check conservative; CamelCase in backticks is mostly prose.
    return "_" in token


# Wording that puts a backticked token in a result position rather than a call position.
# Every term was taken from the corpus, not invented.
_RESULT_POSITION = re.compile(
    r"(?:→|->|\breturns?\b|\bincludes?\b|\bread\b|\bcarries\b|\breport\b|\bcheck\b"
    r"|\bfields?\b|\bflag\b|\bvalues?\b|\bslugs?\b|\bplaceholder\b|\be\.g\."
    r"|\bpass(?:es|ed|ing)?\b)",
    re.IGNORECASE,
)
# Uppercase NOT introduces a contrast, not an instruction. Case-sensitive on purpose.
_CONTRAST = re.compile(r"\bNOT\b")
# Two pipes before the token: a later table cell, which holds arguments and enum values.
_TABLE_TAIL_PIPES = 2
# Bounded so a marker in an unrelated earlier sentence cannot silence a real instruction.
_PAREN_LOOKBACK = 80


def _context_before(block: str, start: int) -> str:
    """The text a token's position is judged against: its line, or the parenthesis it sits in.

    Value lists wrap across lines, and the wording that makes them values sits before
    the opening bracket.
    """
    line_start = block.rfind("\n", 0, start) + 1
    prefix = block[:start]
    if prefix.count("(") > prefix.count(")"):
        opened = prefix.rfind("(")
        return block[max(0, opened - _PAREN_LOOKBACK):start]
    return block[line_start:start]


def referenced_tool_names(text: str, exclude: set[str] | None = None) -> list[str]:
    """Backticked tokens the body tells the agent to call, in order.

    A token is skipped when it sits in a result position, in a later table cell, or on
    a line that says the tool is unreachable.
    """
    exclude = exclude or set()
    seen: list[str] = []
    for block in re.split(r"\n\s*\n", body_text(text)):
        lines = block.splitlines()
        if not lines or _marks_unavailable(lines[0]):
            continue
        for match in _BACKTICKED.finditer(block):
            token = match.group(1)
            if not _is_tool_shaped(token) or token in exclude or token in seen:
                continue
            line_start = block.rfind("\n", 0, match.start()) + 1
            line_end = block.find("\n", match.start())
            line = block[line_start:line_end if line_end != -1 else len(block)]
            if _marks_unavailable(line):
                continue
            if block[line_start:match.start()].count("|") >= _TABLE_TAIL_PIPES:
                continue
            before = _context_before(block, match.start())
            if _RESULT_POSITION.search(before) or _CONTRAST.search(before):
                continue
            seen.append(token)
    return seen


def absent_tools(
    text: str,
    servable: set[str],
    allowlist: set[str] | None = None,
    field_names: set[str] | None = None,
) -> list[str]:
    """Referenced names that resolve to no served tool, in sorted order.

    Unlike ``live_unserved_tools``, a name reported here exists nowhere. ``servable`` is
    expanded through the resolver here so a caller passing raw names cannot silently miss.
    """
    allowed = (allowlist or set()) | (field_names or set())
    resolved = servable_names(servable)
    return sorted(
        name
        for name in referenced_tool_names(text, exclude=allowed)
        if name not in resolved
    )


# --- does the call pass arguments the tool declares? ---
# The REST family builds its query from the declared properties, so an undeclared keyword
# is silently dropped rather than rejected. Only names that resolve to a tool are judged.

# A call: an identifier and a parenthesised argument list. One level of nesting is allowed
# because argument values contain parentheses. The code mark may close before the bracket.
_CALL_SITE = re.compile(
    r"\b([A-Za-z][A-Za-z0-9_]{2,})`?\s*\(((?:[^()]|\([^()]*\)){0,600}?)\)(?!\s*\()"
)
# A keyword: `name=` not preceded by a comparison operator, and outside any quoted value.
_KEYWORD = re.compile(r"(?<![=!<>])\b([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)")
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
# Bodies annotate JSON argument blocks with `//` comments; those are never arguments.
_LINE_COMMENT = re.compile(r"//[^\n]*")


class BadKeyword:
    """One call site passing an argument its tool does not declare."""

    def __init__(self, tool: str, keyword: str, line: int, declared: set[str]):
        self.tool = tool
        self.keyword = keyword
        self.line = line
        self.declared = declared

    @property
    def message(self) -> str:
        alternatives = ", ".join(sorted(self.declared)) or "(none declared)"
        return (
            f"line {self.line}: {self.tool}({self.keyword}=...) is not a declared "
            f"parameter; declared: {alternatives}"
        )

    def __repr__(self) -> str:
        return f"<BadKeyword {self.tool}.{self.keyword} line {self.line}>"


# Cached so a corpus run reads the definition files once, not once per body.
@lru_cache(maxsize=None)
def registry_properties(data_dir: str | Path) -> dict[str, set[str]]:
    """Tool name -> declared parameter names, keyed by original and shortened name."""
    properties: dict[str, set[str]] = {}
    for path in Path(data_dir).rglob("*.json"):
        try:
            defs = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(defs, list):
            continue
        for tool in defs:
            if not isinstance(tool, dict) or not tool.get("name"):
                continue
            declared = (tool.get("parameter") or {}).get("properties") or {}
            if not isinstance(declared, dict):
                continue
            names = {str(key) for key in declared}
            properties[tool["name"]] = names
            properties.setdefault(shorten(tool["name"]), names)
    return properties


def _keywords_in(arguments: str) -> list[str]:
    """Keyword names in an argument list, ignoring quoted values and ``//`` comments.

    Blanking preserves length so reported line numbers stay correct.
    """
    unquoted = _QUOTED.sub(lambda m: " " * len(m.group()), arguments)
    uncommented = _LINE_COMMENT.sub(lambda m: " " * len(m.group()), unquoted)
    return _KEYWORD.findall(uncommented)


def _with_shortened_aliases(properties: dict[str, set[str]]) -> dict[str, set[str]]:
    """Make every tool reachable by its shortened name too. Idempotent.

    Resolved here so a caller who forgets cannot silently stop checking most of the corpus.
    """
    resolved = dict(properties)
    for name, declared in properties.items():
        resolved.setdefault(shorten(name), declared)
    return resolved


def undeclared_keywords(
    text: str, properties: dict[str, set[str]]
) -> list[BadKeyword]:
    """Call sites passing arguments their tool does not declare, in document order."""
    body = body_text(text)
    properties = _with_shortened_aliases(properties)
    problems: list[BadKeyword] = []

    for match in _CALL_SITE.finditer(body):
        tool = match.group(1)
        declared = properties.get(tool)
        if declared is None:
            continue  # not a known tool: prose, or a phantom for the other rule
        line = body.count("\n", 0, match.start()) + 1
        for keyword in _keywords_in(match.group(2)):
            if keyword not in declared:
                problems.append(BadKeyword(tool, keyword, line, declared))

    return problems


def check_body(text: str, deploy_dir: str | Path) -> tuple[list[str], list[str]]:
    """Return ``(errors, warnings)`` for one persona body.

    A short body is only a warning; never pad to the cap.
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

    # A call to an unserved tool fails at run time and burns an iteration. Counts
    # live_unserved_tools, not unserved_tools: a body that forbids a tool must still pass.
    dockerfile = Path(deploy_dir) / "Dockerfile"
    if dockerfile.is_file():
        excluded = excluded_tool_names(dockerfile.read_text())
        for name in live_unserved_tools(text, excluded):
            errors.append(f"instructs a call to {name}, which the image does not serve")

    # The REST family silently drops an undeclared keyword, so the call succeeds with
    # the wrong scope; that is why it is an error.
    if REGISTRY_DATA.is_dir():
        for problem in undeclared_keywords(text, registry_properties(REGISTRY_DATA)):
            errors.append(problem.message)

        # "Exists" spans three sources: the ToolUniverse registry, the meta-tools smcp.py
        # registers in code, and the Squirro agent's own tools.
        known_fields = (registry_parameter_names(REGISTRY_DATA)
                        | registry_return_field_names(REGISTRY_DATA))
        allowed = set(PLATFORM_TOOLS) | external_tool_names() | PHANTOM_ALLOWLIST
        for name in absent_tools(
            text,
            set(loader_reachable_names()),
            allowlist=allowed,
            field_names=known_fields,
        ):
            errors.append(f"instructs a call to {name}, which resolves to no served tool")

    return errors, warnings
