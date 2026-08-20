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

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

# The server resolves names with shortening on (smcp.py passes
# enable_name_shortening=True; ToolUniverse.MAX_TOOL_NAME_LENGTH is 45), so a body may
# legitimately name either the registry's original or its shortened form. Validating
# against only one of the two is wrong in both directions -- every shortened reference
# would read as absent, or every long one would.
MAX_TOOL_NAME_LENGTH = 45

_SRC = Path(__file__).resolve().parents[1] / "src"
# The tool definitions, for the checks that need to know what a tool actually declares.
REGISTRY_DATA = _SRC / "tooluniverse" / "data"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tooluniverse.tool_name_utils import shorten_tool_name  # noqa: E402

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
    # "there is NO `ZFIN_search` or `WormBase_search` tool deployed" -- same statement as
    # "not deployed", phrased around the noun instead of the verb.
    "tool deployed",
    # The Dockerfile's own vocabulary: a body saying a tool "is excluded" is relaying
    # the --exclude-tools decision, not instructing a call (DSR-687).
    "excluded",
)


def _marks_unavailable(line: str) -> bool:
    low = line.lower()
    return any(marker in low for marker in _UNAVAILABLE)


def live_unserved_tools(
    text: str, excluded: set[str], *, include_header: bool = False
) -> list[str]:
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

    ``include_header`` selects the surface (DSR-687). Default False models the Studio
    paste, where the human copies the body below the leading HTML comment. True models
    the get_skill surface: ``load_skill_body`` returns the RAW file and the Dockerfile
    stages it with a plain ``cp``, so the agent reads the header too — a header
    claiming a dead tool "IS available" mis-instructs it exactly like body text would.
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


# --- does the referenced name exist at all? (DSR-661) ---

# A backticked token. Bodies quote tool names, ontology ids and field names alike, so the
# shape alone decides nothing -- see _is_tool_shaped.
_BACKTICKED = re.compile(r"`([A-Za-z][A-Za-z0-9_]*)`")
# `MONDO_0008315`, `EFO_0001663`: a prefix followed by digits is an identifier, never a tool.
_ONTOLOGY_ID = re.compile(r"^[A-Za-z]+_\d+$")


# Real, served, and absent from data/**/*.json, so the registry check must be told about
# them explicitly. All three are registered programmatically in smcp.py rather than
# declared in compact_mode_tools.json (which lists only list_tools, grep_tools,
# get_tool_info and execute_tool), which is why the startup banner's tool count undercounts
# and why a naive registry lookup calls them phantoms. `find_tools` comes from
# register_tool_finder; `get_skill` and `find_skill` from the skill-serving block (DSR-505).
PLATFORM_TOOLS = frozenset({"find_tools", "get_skill", "find_skill"})

# The Squirro agent carries tools that are not ToolUniverse's at all -- web search, the
# dedicated connectors, the internal-data retriever. Their names live in the delivery
# repo's config/agents.json, which this submodule cannot read when checked out standalone
# as the squirro/ToolUniverse fork, so they are generated into a committed file beside this
# one. Regenerate with gen_external_tools.py; see that file for why custom_name and never
# display_name.
EXTERNAL_TOOLS_FILE = Path(__file__).resolve().parent / "served_external_tools.json"


def external_tool_names(path: str | Path | None = None) -> set[str]:
    """Non-ToolUniverse tools the agent can call, from the generated manifest.

    Absent or unreadable, this returns the empty set rather than raising: the linter must
    still run inside the fork, where the delivery repo is not present. The cost of the
    empty case is over-reporting, which is visible, rather than under-reporting, which is
    not.
    """
    manifest = Path(path) if path else EXTERNAL_TOOLS_FILE
    try:
        return set(json.loads(manifest.read_text())["tools"])
    except Exception:
        return set()


# Tokens that survive every structural rule and are still not tool names. Each is listed
# with the reason, because an unexplained allowlist is how a rule quietly stops checking.
# Keep it small: an entry here is a confession that the rules could not tell, so a growing
# list is a signal to improve a rule rather than to add another line.
PHANTOM_ALLOWLIST = frozenset({
    # Response fields of tools whose definition carries no return_schema, so
    # registry_return_field_names cannot see them. Named in prose with no wording that
    # marks them as results -- "Key decode: `age_at_diagnosis` is in DAYS".
    "aa_change", "age_at_diagnosis", "mutation_type",      # GDC / TCGA case records
    "active_site", "binding_site",                         # UniProt sequence features
    "best_structures",                                     # PDBe best-structures endpoint
    "cellular_component",                                  # GO aspect name
    "chr_pos_ref_alt", "chr_pos_ref_alt_example",          # OpenTargets variant key
    "combined_score",                                      # STRING edge score
    "highest_clinical_trial_phase",                        # OpenTargets indication edge
    "source_antigen_name",                                 # IEDB epitope key
    "splice_region_variant",                               # Sequence Ontology term
    # Family shorthand rather than a callable name: the bodies write "the per-organism
    # `get_gene` / `get_phenotypes` tools" to mean Xenbase_get_gene, ZFIN_get_gene and the
    # rest. No single tool is called either name.
    "get_gene", "get_phenotypes",
})


def shorten(name: str) -> str:
    """The name the server would serve this tool under."""
    return shorten_tool_name(name, max_length=MAX_TOOL_NAME_LENGTH)


# Cached: check_body needs all four, and a corpus run would otherwise walk the
# 2,428 definition files four times per body. Callers treat the result as read-only.
@lru_cache(maxsize=None)
def registry_tool_names(data_dir: str | Path) -> set[str]:
    """Every tool name declared in the registry's JSON, read without loading ToolUniverse.

    A full load takes minutes and pulls in every dependency; the linter only needs the
    names, and they are all sitting in ``data/**/*.json``. Unparseable files are skipped
    rather than fatal -- a malformed file is a different guard's problem
    (``test_no_duplicate_json_keys``), and this one must not fail for it.
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


# Cached: check_body needs all four, and a corpus run would otherwise walk the
# 2,428 definition files four times per body. Callers treat the result as read-only.
@lru_cache(maxsize=None)
def registry_parameter_names(data_dir: str | Path) -> set[str]:
    """Every parameter name any tool declares.

    This is what makes the absent-tool check usable. Tool names and field names are
    shape-identical here -- ``BiGG_search`` is a tool, ``chembl_id`` is a field, and 117
    real tools have only two segments -- so no pattern can tell them apart. Asking the
    registry which tokens are parameters replaces that guess with a lookup.
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


# Cached: check_body needs all four, and a corpus run would otherwise walk the
# 2,428 definition files four times per body. Callers treat the result as read-only.
@lru_cache(maxsize=None)
def registry_return_field_names(data_dir: str | Path) -> set[str]:
    """Every field name any tool declares it RETURNS, plus its ``fields`` list.

    This is the other half of ``registry_parameter_names``, and it is the larger half:
    2,373 of the 2,428 definitions carry a ``return_schema``, yielding some 20,000 names
    against 1,687 input parameters. Without it a body that documents what comes back --
    ``→ `mean_plddt`, `pdb_text``` -- reads as a body inventing two tools, which was the
    single biggest source of false reports.
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
    """Tool names the loader can actually reach, not merely names present on disk.

    ``registry_tool_names`` reads every JSON under ``data/``, which accepts 44 names the
    server never serves: the archived ``broken_apis`` definitions and the API-key
    catalogue, whose records carry a ``name`` and so look like tools to a file scan. A body
    naming one of those passes a disk-based check and still fails at run time with "Tool
    'X' not found", which is the blind spot DSR-663 exists to close.

    Falls back to the disk scan if the wiring module cannot be imported, so the linter
    still runs where the package is not importable. The fallback over-accepts, which is the
    behaviour it has always had.
    """
    try:
        from tooluniverse.tools_sr.wiring import servable_definition_names

        return frozenset(servable_definition_names())
    except Exception:
        return frozenset(registry_tool_names(REGISTRY_DATA))


def servable_names(registry_names: set[str]) -> set[str]:
    """Names the server answers to: each registry name plus its shortened form.

    Idempotent -- shortening an already-short name returns it unchanged -- so it is safe
    to apply to a set that has already been expanded.
    """
    servable = set(registry_names)
    servable.update(shorten(name) for name in registry_names)
    return servable


def _is_tool_shaped(token: str) -> bool:
    if _ONTOLOGY_ID.match(token):
        return False
    # `MONDO_`, `NM_`, `XM_`: a bare prefix naming an accession family, not a call. No name
    # in the registry ends in an underscore.
    if token.endswith("_"):
        return False
    # `TAX_ID_HERE`, `ENSEMBL_ID`, `ANNOT_TYPE_ID_PANTHER_PATHWAY`: SCREAMING_CASE marks a
    # placeholder, a constant or an enum value. No registry tool is named in upper case --
    # the 39 all-caps entries the name scan picks up are API-key records, not tools.
    if token.isupper():
        return False
    # Underscore-free CamelCase agentic tools (CallAgent) are real, but so is most prose
    # in backticks, so requiring an underscore keeps this check conservative. It
    # under-reports rather than crying wolf, which is what keeps a linter switched on.
    return "_" in token


# Wording that puts a backticked token in a RESULT position rather than a call position.
# Shape cannot separate the two -- 117 real tools have only two segments -- but position
# can: a tool being called heads its clause, while a field being read follows a result
# arrow, an enumeration verb, or wording that introduces an example. Every term here was
# taken from the corpus, not invented; between them they account for the field names
# (`total_count`, `mean_plddt`), the Ensembl species slugs and the placeholder text that
# a shape-only extractor reports as invented tools.
_RESULT_POSITION = re.compile(
    r"(?:→|->|\breturns?\b|\bincludes?\b|\bread\b|\bcarries\b|\breport\b|\bcheck\b"
    r"|\bfields?\b|\bflag\b|\bvalues?\b|\bslugs?\b|\bplaceholder\b|\be\.g\."
    r"|\bpass(?:es|ed|ing)?\b)",
    re.IGNORECASE,
)
# Uppercase NOT, which these bodies use for emphasis, always introduces a contrast rather
# than an instruction: "NOT `ClinicalTrials_search` (errors)", "NOT `epitope_name` (which
# matches epitope names)". Case-sensitive on purpose -- lower-case "not" is ordinary prose
# and would suppress real instructions.
_CONTRAST = re.compile(r"\bNOT\b")
# Two pipes before the token means at least the second cell of a markdown table row. The
# bodies tabulate `tool | arguments | operation-value`, so only the first backticked cell
# can name a tool; the later columns hold argument names and enum values that are shaped
# identically.
_TABLE_TAIL_PIPES = 2
# How far back to read when a value list wraps across lines. Bounded so that a marker in
# an unrelated earlier sentence cannot reach forward and silence a real instruction.
_PAREN_LOOKBACK = 80


def _context_before(block: str, start: int) -> str:
    """The text a token's position should be judged against.

    Normally the current line up to the token. When the token sits inside a parenthesis
    opened earlier, the window extends back through that parenthesis: the bodies wrap long
    value lists -- the Ensembl species slugs run over two lines -- and the wording that
    makes them values sits before the opening bracket, not on the continuation line.
    """
    line_start = block.rfind("\n", 0, start) + 1
    prefix = block[:start]
    if prefix.count("(") > prefix.count(")"):
        opened = prefix.rfind("(")
        return block[max(0, opened - _PAREN_LOOKBACK):start]
    return block[line_start:start]


def referenced_tool_names(text: str, exclude: set[str] | None = None) -> list[str]:
    """Backticked tokens the body tells the agent to CALL, in order.

    Three things disqualify a token. It sits in a result position (see ``_RESULT_POSITION``).
    It sits in a table row's second or later cell. Or its line -- or the line opening its
    block -- says the tool is unreachable, which is the same per-mention suppression
    ``live_unserved_tools`` applies: a body that names a tool in order to FORBID it is
    doing the right thing and must not be reported for it.
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

    Distinct from ``live_unserved_tools``, which reports names that exist but are excluded
    from the image. A name reported here exists nowhere, so the agent gets "Tool 'X' not
    found even after loading tools" -- which reads as a registry bug rather than a mistake
    in the body, and burns an iteration.

    ``servable`` is expanded through the resolver here rather than by the caller. Passing
    raw registry names would otherwise flag every shortened reference in the corpus, and
    the exemplar body names its tools in shortened form -- so leaving that step to the
    caller makes the common mistake the silent one. Expansion is idempotent.
    """
    allowed = (allowlist or set()) | (field_names or set())
    resolved = servable_names(servable)
    return sorted(
        name
        for name in referenced_tool_names(text, exclude=allowed)
        if name not in resolved
    )


# --- does the call pass arguments the tool declares? (DSR-668) ---
# For the 241-tool REST family, query parameters are built from the *declared* properties,
# so an undeclared keyword is silently DROPPED rather than rejected. organism="human"
# vanishes and the agent reports mouse+human data as human -- a wrong answer, not a failed
# call, which is why this is worth an error rather than a warning.
#
# Precision comes from anchoring on tools that exist. A body contains prose like
# "tally (Supporting=1, Moderate=2)" that is shaped exactly like a call; because "tally"
# resolves to no registry tool, it is discarded before any judgement is required. That is
# the difference between this rule and the phantom-name rule.

# A call: an identifier followed by a parenthesised argument list. One level of nesting is
# allowed because argument values contain parentheses -- filter="(a OR b)", size=len(x) --
# and a flat pattern stops at the inner ")" and silently drops the rest of the call.
_CALL_SITE = re.compile(
    r"\b([A-Za-z][A-Za-z0-9_]{2,})\s*\(((?:[^()]|\([^()]*\)){0,600}?)\)(?!\s*\()"
)
# A keyword: `name=` not preceded by a comparison operator, and outside any quoted value.
_KEYWORD = re.compile(r"(?<![=!<>])\b([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)")
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
# Bodies annotate multi-line JSON argument blocks with `//` comments, and one of them
# reads "RSA below this = buried/core" -- prose that a naive scan turns into a keyword
# named `this`. Comments are commentary, never arguments.
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


# Cached: check_body needs all four, and a corpus run would otherwise walk the
# 2,428 definition files four times per body. Callers treat the result as read-only.
@lru_cache(maxsize=None)
def registry_properties(data_dir: str | Path) -> dict[str, set[str]]:
    """Tool name -> declared parameter names, keyed by original *and* shortened name.

    Both keys, because a body may legitimately call either form and the arguments belong
    to the same tool regardless.
    """
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
    """Keyword names in an argument list, ignoring anything inside quotes.

    Quoted values and ``//`` comments are blanked first, so neither a query string like
    "score >= 0.5" nor an annotation like "// RSA below this = buried/core" can contribute
    a keyword. Blanking preserves length so reported line numbers stay correct.
    """
    unquoted = _QUOTED.sub(lambda m: " " * len(m.group()), arguments)
    uncommented = _LINE_COMMENT.sub(lambda m: " " * len(m.group()), unquoted)
    return _KEYWORD.findall(uncommented)


def _with_shortened_aliases(properties: dict[str, set[str]]) -> dict[str, set[str]]:
    """Ensure every tool is reachable by its shortened name too.

    Resolved here rather than trusting the caller, for the same reason ``absent_tools``
    expands its own name set: bodies name tools in shortened form, so a caller who forgets
    would silently stop checking most of the corpus rather than fail loudly. Idempotent.
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

    # An undeclared keyword is worse than a rejected one: for the REST family the query is
    # built from the DECLARED properties, so the argument is silently dropped and the call
    # succeeds with the wrong scope. This shipped report-only while 18 call-sites tripped
    # it -- a linter that is red on arrival gets switched off -- and holds the line as an
    # error now they are corrected (DSR-673).
    if REGISTRY_DATA.is_dir():
        for problem in undeclared_keywords(text, registry_properties(REGISTRY_DATA)):
            errors.append(problem.message)

        # A name that resolves nowhere is worse than one that is merely excluded: the agent
        # gets "Tool 'X' not found even after loading tools", which reads as a registry bug
        # rather than a mistake in the body, and burns an iteration.
        #
        # "Exists" spans three sources, and using only the first is what let five wrong
        # web-tool names sit in nine bodies unnoticed: the ToolUniverse registry, the
        # meta-tools smcp.py registers in code, and the Squirro agent's own tools from
        # served_external_tools.json.
        #
        # This ships as an error on arrival, which the dead-call and keyword rules could not
        # -- they had 33 and 18 live violations respectively and a red linter gets switched
        # off. Here the corpus is already clean: the rule reported 145 mentions when the
        # session began, the nine bodies naming unreachable web tools were corrected, and
        # what the structural rules could not classify is named in PHANTOM_ALLOWLIST.
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
