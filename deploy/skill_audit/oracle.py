"""Score one live agent turn against one served skill body, from the trace alone.

A trace can FAIL a skill but never PASS one: if the skill never loaded, fired no
tool, or every call died, the run is broken however well the prose reads — but a
clean trace says nothing about whether the answer is any good. So the codes here
split three ways.

* ``fail``  — an unambiguous defect. Every one of these was observed by hand on
  sr-dev in August 2026 and has an exact signature.
* ``warn``  — suspicious, and worth a human's eyes, but a legitimate run can
  produce it. Warnings rank the review queue; they do not fail anything.
* ``retry`` — an environment artefact, not a skill defect. The provider's
  intermittent bio-risk refusal is the only one so far: zero tool calls plus an
  error at the very start of the turn.

Ground truth for "which tools should have fired" is the skill body itself: every
phase names its tools in backticks, and the mandatory ones sit on a ``**Primary**``
line. The body is the spec, so no expectation has to be hand-written per question.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

SEVERITY: dict[str, str] = {
    # unambiguous defects
    "turn_error": "fail",
    "no_skill_loaded": "fail",
    "skill_without_tools": "fail",
    "tool_not_found": "fail",
    "schema_rejected": "fail",
    "tool_error": "fail",
    "linkless_footnote": "fail",
    # suspicious, ranks the review queue
    "wrong_skill": "warn",
    "missing_primary_tools": "warn",
    "zero_rows": "warn",
    "skill_after_web": "warn",
    "answer_declined": "warn",
    "lookup_miss": "warn",
    # environment artefact
    "provider_refusal": "retry",
}

_RANK = {"pass": 0, "warn": 1, "retry": 2, "fail": 3}

# The seven meta-tools are plumbing, never a skill's subject-matter requirement.
META_TOOLS = frozenset({
    "execute_tool", "get_skill", "find_skill", "find_tools",
    "list_tools", "grep_tools", "get_tool_info",
})

# Genuine outward searches. `paragraph_retriever` is deliberately NOT here: it is
# Squirro's own retrieval step, fired before the agent chooses anything (it opened
# 64 of 76 turns in the first full sweep), so treating it as a web batch would
# condemn every skill for the platform's behaviour.
WEB_TOOLS = frozenset({
    "exa_web_search", "exa_web_content_fetch", "perplexity_web_search_api",
    "openai web search", "openai_web_search", "web_search",
})

# Reaching for either of these IS taking the skill route.
SKILL_TOOLS = ("find_skill", "get_skill")

_ENVELOPE_HEAD = re.compile(r'\s*\{\s*"status"\s*:\s*"(success|error)"')
_TOOL_CALL = re.compile(r"`([A-Za-z][A-Za-z0-9_]{2,})`\s*\(")
_FOOTNOTE_DEF = re.compile(r"^\[\^[^\]]+\]:\s*(.*)$", re.MULTILINE)
_NOT_FOUND = re.compile(r"tool\s+'[^']+'\s+not found|not a registered tool|"
                        r"unknown tool", re.IGNORECASE)
_SCHEMA_REJECT = re.compile(
    r"unexpected keyword argument|validation error|validation failed|"
    r"field required|is a required property|input should be a valid|"
    r"toolvalidationerror|missing required (parameter|argument)",
    re.IGNORECASE,
)
# The tool ran and answered: I do not hold that entity, or that identifier is not
# in my format. The call is wrong, but nothing is broken — usually the agent
# guessed an identifier (`sstr2_human`, PDB `7t11` for a question about 7T10).
_LOOKUP_MISS = re.compile(
    r"not found:|entry not found|no data returned|not in (our|the) database|"
    r"unknown (accession|identifier|entry)|invalid (accession|identifier)",
    re.IGNORECASE,
)
_RAISED = re.compile(r"traceback \(most recent call last\)|httperror|"
                     r"connectionerror|\bexception\b", re.IGNORECASE)
# A tool that answers "nothing matched your query" worked; the query was narrow.
_NO_MATCHES = re.compile(
    r"no studies found|no results?\b|no records?\b|no matches|returned no |"
    r"not found for the given|no data (found|available)|empty result",
    re.IGNORECASE,
)
_DECLINE = re.compile(
    r"\bi cannot\b|\bi can't\b|\bi'm unable\b|\bi am unable\b|"
    r"\bdon't have enough\b|\bdo not have enough\b|\bno tools? available\b",
    re.IGNORECASE,
)
_EMPTY_CONTAINERS = ("results", "hits", "data", "items", "records", "rows")


@dataclass
class SkillFinding:
    code: str
    severity: str
    message: str
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"code": self.code, "severity": self.severity,
                "message": self.message, "evidence": self.evidence}


def required_tools(body: str) -> list[str]:
    """The tools a body marks **Primary** — the calls it says must happen."""
    out: list[str] = []
    for line in body.splitlines():
        if "**Primary" not in line:
            continue
        for name in _TOOL_CALL.findall(line):
            if name not in META_TOOLS and name not in out:
                out.append(name)
    return out


def mentioned_tools(body: str) -> set[str]:
    """Every tool the body names anywhere — Primary, Enrich, gated or optional."""
    return {n for n in _TOOL_CALL.findall(body) if n not in META_TOOLS}


def body_tool_coverage(body: str | None, fired: list[str]) -> dict:
    """How much of what the body names actually ran — data, not a verdict.

    `required_tools` only sees bodies that mark their mandatory calls
    ``**Primary**``, and just 3 of 86 do, so it says nothing about the corpus.
    Every body does name its tools in backticks, though, and comparing that set
    against what ran locates a skill that quietly went its own way. It is NOT a
    finding: a body legitimately names gated alternatives ("pick the first
    applicable, then STOP"), so a low ratio is a reason to read the trace, not
    evidence of a defect.
    """
    if not body:
        return {}
    named = mentioned_tools(body)
    ran = set(fired)
    return {
        "named": len(named),
        "from_body": len(named & ran),
        "off_body": sorted(ran - named),
    }


def _output_text(action: dict) -> str:
    content = action.get("content") or {}
    output = content.get("output")
    if output is None:
        return ""
    return output if isinstance(output, str) else json.dumps(output)


def _parameters(action: dict) -> dict:
    content = action.get("content") or {}
    params = content.get("parameters")
    return params if isinstance(params, dict) else {}


def _dispatched_tool(action: dict) -> str | None:
    """The real TU tool behind an execute_tool call."""
    params = _parameters(action)
    name = params.get("tool_name") or params.get("name")
    return name if isinstance(name, str) else None


def _loaded_skill(action: dict) -> str | None:
    params = _parameters(action)
    name = params.get("name") or params.get("skill_name")
    return name if isinstance(name, str) else None


def _is_empty_result(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    try:
        parsed = json.loads(stripped)
    except (ValueError, TypeError):
        return len(stripped) < 20
    if isinstance(parsed, list):
        return not parsed
    if isinstance(parsed, dict):
        if parsed.get("total") == 0:
            return True
        containers = [v for k, v in parsed.items()
                      if k.lower() in _EMPTY_CONTAINERS]
        if containers:
            return all(not c for c in containers)
        return not parsed
    return False


def classify_call(text: str, status: str | None = None) -> str:
    """One of: not_found | schema | error | empty | ok.

    Trust the result envelope when there is one. ToolUniverse wraps results as
    ``{"status": "success"|"error", ...}``, and a success payload can be pages of
    free prose — drug-label text mentioning an exception or an HTTP error is not
    a failed call. Only fall back to scanning raw text when no envelope exists.
    """
    if status == "failed":
        return "error"
    stripped = (text or "").strip()
    try:
        envelope = json.loads(stripped) if stripped else None
    except (ValueError, TypeError):
        envelope = None
        # Squirro caps a tool's output, so a long result arrives as JSON cut
        # mid-string. The head still says what happened; scanning the surviving
        # prose does not (drug labels say "with the exception of").
        head = _ENVELOPE_HEAD.match(stripped)
        if head:
            if head.group(1) == "success":
                return "ok"
            message = stripped[:2000]
            for pattern, outcome in ((_NOT_FOUND, "not_found"),
                                     (_SCHEMA_REJECT, "schema"),
                                     (_NO_MATCHES, "empty"),
                                     (_LOOKUP_MISS, "miss")):
                if pattern.search(message):
                    return outcome
            return "error"

    if isinstance(envelope, dict):
        state = envelope.get("status")
        message = " ".join(str(envelope.get(k, "")) for k in
                           ("error", "message", "detail"))
        details = envelope.get("error_details")
        if isinstance(details, dict):
            message += " " + str(details.get("type", ""))
        if state == "error" or (state is None and envelope.get("error")):
            if _NOT_FOUND.search(message):
                return "not_found"
            if _SCHEMA_REJECT.search(message):
                return "schema"
            if _NO_MATCHES.search(message):
                return "empty"
            if _LOOKUP_MISS.search(message):
                return "miss"
            return "error"
        payload = envelope.get("data", envelope)
        return "empty" if _is_empty_result(json.dumps(payload)) else "ok"

    if _NOT_FOUND.search(stripped):
        return "not_found"
    if _SCHEMA_REJECT.search(stripped):
        return "schema"
    if _RAISED.search(stripped):
        return "error"
    return "empty" if _is_empty_result(stripped) else "ok"


def _finding(code: str, message: str, **evidence) -> SkillFinding:
    return SkillFinding(code=code, severity=SEVERITY[code],
                        message=message, evidence=evidence)


def score(
    expected_skill: str,
    actions: list[dict],
    answer: str,
    error: str | None,
    body: str | None = None,
) -> list[SkillFinding]:
    """Findings for one turn. Empty list means nothing structural went wrong."""
    actions = actions or []
    answer = answer or ""

    if error and not actions:
        return [_finding("provider_refusal",
                         "turn died before any tool ran — provider refusal or "
                         "cold container; re-run before diagnosing",
                         error=error)]

    findings: list[SkillFinding] = []
    if error:
        findings.append(_finding("turn_error",
                                 f"turn errored after {len(actions)} actions",
                                 error=error))

    names = [a.get("tool_name") or "" for a in actions]
    skill_idx = next((i for i, n in enumerate(names) if n == "get_skill"), None)

    if skill_idx is None:
        findings.append(_finding("no_skill_loaded",
                                 "no get_skill call in the turn",
                                 called=names))
        loaded = None
    else:
        loaded = _loaded_skill(actions[skill_idx])
        if loaded != expected_skill:
            findings.append(_finding(
                "wrong_skill",
                f"loaded {loaded!r}, expected {expected_skill!r}",
                loaded=loaded, expected=expected_skill))
        route_idx = next((i for i, n in enumerate(names) if n in SKILL_TOOLS),
                         skill_idx)
        web_before = [n for n in names[:route_idx] if n.lower() in WEB_TOOLS]
        if web_before:
            findings.append(_finding(
                "skill_after_web",
                "skill loaded after the web batch, so it did not govern the turn",
                web_first=web_before))

    execs = [a for i, a in enumerate(actions)
             if names[i] == "execute_tool"
             and (skill_idx is None or i > skill_idx)]

    if skill_idx is not None and not execs:
        findings.append(_finding(
            "skill_without_tools",
            "skill loaded but no execute_tool followed it",
            called=names))

    fired: list[str] = []
    empty = 0
    for action in execs:
        tool = _dispatched_tool(action)
        if tool:
            fired.append(tool)
        text = _output_text(action)
        outcome = classify_call(text, action.get("status"))
        if outcome == "not_found":
            findings.append(_finding("tool_not_found",
                                     f"{tool}: not a registered tool",
                                     tool=tool, output=text[:300]))
        elif outcome == "schema":
            findings.append(_finding("schema_rejected",
                                     f"{tool}: call rejected on its schema",
                                     tool=tool, output=text[:300]))
        elif outcome == "error":
            findings.append(_finding("tool_error",
                                     f"{tool}: call failed",
                                     tool=tool, output=text[:300]))
        elif outcome == "miss":
            findings.append(_finding(
                "lookup_miss",
                f"{tool}: the database does not hold that entity or identifier",
                tool=tool, output=text[:300]))
            empty += 1
        elif outcome == "empty":
            empty += 1

    if execs and empty == len(execs):
        findings.append(_finding(
            "zero_rows",
            "every tool call succeeded and returned nothing — the skill ran starved",
            calls=fired))

    if body and execs and loaded == expected_skill:
        required = required_tools(body)
        missing = [t for t in required if t not in fired]
        if missing:
            findings.append(_finding(
                "missing_primary_tools",
                f"{len(required) - len(missing)}/{len(required)} Primary tools fired",
                missing=missing, fired=len(required) - len(missing),
                required=len(required)))

    findings.extend(_answer_findings(answer))
    return findings


def _answer_findings(answer: str) -> list[SkillFinding]:
    out: list[SkillFinding] = []
    linkless = [d.strip() for d in _FOOTNOTE_DEF.findall(answer)
                if "http" not in d]
    if linkless:
        out.append(_finding(
            "linkless_footnote",
            "footnote definitions carry no link, so the chat renderer drops them",
            examples=linkless[:3]))
    if _DECLINE.search(answer[:800]):
        out.append(_finding("answer_declined",
                            "answer declines or hedges on availability",
                            head=answer[:200]))
    return out


def verdict(findings: list[SkillFinding]) -> str:
    worst = "pass"
    for f in findings:
        if _RANK[f.severity] > _RANK[worst]:
            worst = f.severity
    return worst
