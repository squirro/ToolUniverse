"""Read the agent's draft report against what the agent received, before the user reads it.

Pure: the draft and the received data in, failures out. The rules are the ones the benchmark
harness proved on judged reports; here they run in production, on every report.
"""

from __future__ import annotations

import json
import re
from typing import Any

# A standalone numeric token: not glued to a word or a dot on either side, so HP:0001433,
# ORPHA:580, [^3^], v3 and 1.2.3 are names, not numbers.
_NUMBER = re.compile(r"(?<![\w.:/^])(\d{1,6}(?:\.\d{1,4})?)(?![\w^/]|\.\d)")
_NUMBER_RECEIVED = re.compile(r"(?<![\w.:/^])(\d+(?:\.\d+)?)(?![\w^/]|\.\d)")
_URL = re.compile(r"\(?https?://\S+\)?")
_DOI = re.compile(r"\b10\.\d{4,9}/\S+")
_DATE = re.compile(r"\b\d{4}-\d{2}(?:-\d{2})?\b")             # 2026-01-20 is a date, not three numbers
_FOOTNOTE = re.compile(r"\[\^?\d+\^?\]:?")
_CHIP = re.compile(r"<sub>.*?</sub>", re.S)                     # the chat's attachment-size chips
_NUMBERING = re.compile(r"(?m)^\s*(?:#+\s*|[-*]\s*)?\d{1,2}[.)]\s")    # headings and list items


_THOUSANDS = re.compile(r"(?<=\d)[,\u202f\u2009 ](?=\d{3}\b)")


def _fold_thousands(text: str) -> str:
    """2,078 and 2 078 read as 2078, so a separator never makes two numbers of one."""
    return _THOUSANDS.sub("", text)


def _rounded_forms(value: str) -> set[str]:
    f = float(value)
    return {value, f"{f:.0f}", f"{f:.1f}", f"{f:.2f}", f"{f:.3f}", f"{f:.4f}"}


def _vouched_numbers(received: Any) -> set[str]:
    text = json.dumps(received, default=str, ensure_ascii=False)
    vouched: set[str] = set()
    for match in _NUMBER_RECEIVED.finditer(text):
        vouched |= _rounded_forms(match.group(1))
    return vouched


_LINK = re.compile(r"https?://[^\s<>\"')\]]+")


_CREDENTIAL = re.compile(r"[?&](?:api_?key|token|access_token|key)=[^&#\s]*", re.IGNORECASE)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{5,}")


def _bare(link: str) -> str:
    """A link as cited or as received: without credentials, trailing punctuation or case."""
    link = _CREDENTIAL.sub("", link)
    return link.rstrip(".,;:!?/&").lower()


def _built_from_received(link: str, text: str) -> bool:
    """A link whose last segment is an identifier the agent received: a trial by its NCT id,
    a label by its setid. The process tells the agent to cite these by building the link."""
    tail = re.split(r"[/=]", link.rstrip(".,;:!?/"))[-1]
    return bool(_IDENTIFIER.fullmatch(tail)) and any(c.isdigit() for c in tail) and tail in text


def _unvouched_links(draft: str, received: Any) -> list[dict]:
    text = json.dumps(received, default=str, ensure_ascii=False)
    known = {_bare(link) for link in _LINK.findall(text)}
    failures, seen = [], set()
    for line in (draft or "").splitlines():
        for link in _LINK.findall(line):
            if _bare(link) in known or _bare(link) in seen or _built_from_received(link, text):
                continue
            seen.add(_bare(link))
            failures.append({"kind": "unvouched_link", "text": link.rstrip(".,;:!?"),
                             "context": " ".join(line.split())[:160]})
    return failures


def _unstated_narrowing(draft: str, received: Any) -> list[dict]:
    """Every table the run holds less of than its source, whose total the draft never gives."""
    handover = received.get("handover") if isinstance(received, dict) else None
    tables = (handover or {}).get("tables") or []
    plain = _fold_thousands(draft or "")
    failures = []
    for table in tables:
        totals = table.get("source_total")
        totals = totals if isinstance(totals, dict) else {"": totals}
        for item, total in totals.items():
            if not isinstance(total, (int, float)) or total <= table.get("rows", 0):
                continue
            # A loop's total is owed for the items the report discusses, not for every item.
            if item and not re.search(r"(?<!\w)" + re.escape(item) + r"(?!\w)", draft or "", re.I):
                continue
            if not re.search(rf"(?<!\d){int(total)}(?!\d)", plain):
                where = f", {item}" if item else ""
                failures.append({"kind": "narrowing_not_stated",
                                 "text": f"{table['table']}{where}: the source holds {int(total)}; "
                                         "say how many this run holds",
                                 "context": "the totals are in handover.tables[].source_total, "
                                            "the rows held in handover.tables[].rows: state both"})
    return failures


def check_report(draft: str, received: Any) -> list[dict]:
    """Every statement in the draft that what the agent received does not vouch for."""
    vouched = _vouched_numbers(received)
    prose = _FOOTNOTE.sub(" ", _DOI.sub(" ", _URL.sub(" ", draft or "")))
    prose = _fold_thousands(_NUMBERING.sub("\n", _CHIP.sub(" ", _DATE.sub(" ", prose))))
    failures, seen = [], set()
    for match in _NUMBER.finditer(prose):
        number = match.group(1)
        if number in vouched or number in seen:
            continue
        seen.add(number)
        start, end = max(0, match.start() - 50), min(len(prose), match.end() + 50)
        failures.append({"kind": "unvouched_number", "text": number,
                         "context": " ".join(prose[start:end].split())})
    return failures + _unvouched_links(draft, received) + _unstated_narrowing(draft, received)
