"""Read the agent's draft report against what the agent received, before the user reads it.

Pure: the draft and the received data in, failures out.
"""

from __future__ import annotations

import json
import re
from typing import Any

# A standalone numeric token; HP:0001433, [^3^], v3 and 1.2.3 are names, not numbers.
_NUMBER = re.compile(r"(?<![\w.:/^])(\d{1,12}(?:\.\d{1,4})?)(?![\w^/]|\.\d)")
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
    text = json.dumps(_data_of(received), default=str, ensure_ascii=False)
    vouched: set[str] = set()
    for match in _NUMBER_RECEIVED.finditer(_fold_thousands(text)):
        vouched |= _rounded_forms(match.group(1))
    return vouched


# What a source gave the run back, as against what the run says about itself. An
# allow-list: the run's own prose -- its failures, what it could not decide, the arguments
# it sent, the steps it skipped -- describes the run, not an answer, and must never vouch
# a statement. A hand-over key added later vouches nothing until it is named here.
# "sources" are the links the server stamped on the run's own calls: tool-side, like a row.
_VOUCHING = ("facts", "tables", "mappings", "excluded", "fetched", "sources")

# The key the engine writes into a row to say it could not read a value there. Its content
# is the text the read failed on, so it vouches nothing: a cell marked unreadable cannot
# then certify the number printed in it.
_UNREAD = ("unparseable",)


def _read_only(value: Any) -> Any:
    """The same data with every "I could not read this" marker taken out of it."""
    if isinstance(value, dict):
        return {k: _read_only(v) for k, v in value.items() if k not in _UNREAD}
    if isinstance(value, list):
        return [_read_only(v) for v in value]
    return value


def _data_of(received: Any) -> Any:
    """The hand-over's own data, plus any rows fetched alongside it.

    A "handover" key holds the terminal hand-over; every other top-level key is a sibling
    the caller attached (fetched rows). A flat object with no "handover" key is the
    hand-over itself.
    """
    if not isinstance(received, dict):
        return received
    handover = received.get("handover")
    handover = handover if isinstance(handover, dict) else {}
    sides = {k: v for k, v in received.items() if k != "handover"}
    merged = {**sides, **handover}
    return _read_only({k: v for k, v in merged.items() if k in _VOUCHING})


def _holds_nothing(received: Any) -> bool:
    """Whether the run handed over no data at all.

    The caller always sends the keys, empty or not, so their presence is not the record --
    only what is inside them is.
    """
    data = _data_of(received)
    return not any(data.values()) if isinstance(data, dict) else not data


_LINK = re.compile(r"https?://[^\s<>\"')\]]+")


_CREDENTIAL = re.compile(r"[?&](?:api_?key|token|access_token|key)=[^&#\s]*", re.IGNORECASE)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{5,}")

# What a search engine or a share button adds on the way. These name no page, so two links
# differing only in them are one page and refusing the citation says they are two.
_TRACKING = re.compile(r"[?&](?:utm_[a-z_]+|fbclid|gclid|mc_cid|mc_eid)=[^&#\s]*",
                       re.IGNORECASE)
_WWW = re.compile(r"^(https?://)www\.", re.IGNORECASE)


def _bare(link: str) -> str:
    """A link as cited or as received: without credentials, tracking, ``www.``, trailing
    punctuation or case. One page spelled two ways must reduce to one string."""
    link = _TRACKING.sub("", _CREDENTIAL.sub("", link))
    if "?" not in link and "&" in link:
        link = link.replace("&", "?", 1)  # the query opener went with the parameter it led
    return _WWW.sub(r"\1", link).rstrip(".,;:!?/&").lower()


def _built_from_received(link: str, text: str, domains: set[str]) -> bool:
    """A link the run could have built: when the run saw any domain, this one was among
    them, and its last segment is an identifier the agent received."""
    # Binds only when the run held a link at all -- a process may tell the agent to build one
    # from a bare identifier, with no domain to check the fabricated one against.
    if domains and _domain_of(link) not in domains:
        return False
    tail = re.split(r"[/=]", link.rstrip(".,;:!?/"))[-1]
    return bool(_IDENTIFIER.fullmatch(tail)) and any(c.isdigit() for c in tail) and tail in text


def _domain_of(link: str) -> str:
    """The link's bare domain; "" for a link with none -- a DOI, a path with no scheme, or
    a scheme with nothing after it."""
    bare = _bare(link)
    parts = bare.split("/")
    return parts[2] if "//" in bare and len(parts) > 2 else ""


# A Run Record's own address. The run's bookkeeping, never a document: citing it points a
# reader at the machinery that produced the claim rather than at what the claim rests on.
_RUN_ADDRESS = re.compile(r"/skills?/runs?/", re.IGNORECASE)


def why_refused(link: str, *, saw_domain: bool) -> str:
    """Why this link is not vouched, in the words a re-ask can act on.

    Naming the link and not the reason is what let the agent write the same citation twice.
    """
    if _RUN_ADDRESS.search(link):
        return ("this is the Skill Run's own address -- the run's bookkeeping, not a source. "
                "Cite the row's own link instead, from the table the number came from.")
    if saw_domain:
        return ("the run saw this site but not this page, so nothing it holds says this page "
                "exists. Cite the page the row itself gives.")
    return ("the run never received this link, so nothing it holds vouches for it. If it came "
            "from a tool you called before run_skill, the run has no record of it: fetch the "
            "same fact inside the run and cite that, or drop the citation.")


def _unvouched_links(draft: str, received: Any) -> list[dict]:
    text = json.dumps(_data_of(received), default=str, ensure_ascii=False)
    known = {_bare(link) for link in _LINK.findall(text)}
    domains = {_domain_of(link) for link in _LINK.findall(text)}
    failures, seen = [], set()
    for line in (draft or "").splitlines():
        for link in _LINK.findall(line):
            if (_bare(link) in known or _bare(link) in seen
                    or _built_from_received(link, text, domains)):
                continue
            seen.add(_bare(link))
            failures.append({"kind": "unvouched_link", "text": link.rstrip(".,;:!?"),
                             "why": why_refused(link, saw_domain=_domain_of(link) in domains),
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
        # `held` counts only the call(s) behind each total; `rows` also counts the step's other tools.
        held = table.get("held", table.get("rows", 0))
        for item, total in totals.items():
            have = held.get(item, 0) if isinstance(held, dict) else held
            if not isinstance(total, (int, float)) or total <= have:
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
                                            "the rows held in handover.tables[].held: state both"})
    return failures


def _unshown_mappings(draft: str, received: Any) -> list[dict]:
    """A mapped term the report never names: the reader cannot judge a mapping it does not see."""
    handover = received.get("handover") if isinstance(received, dict) else None
    handover = handover or {}
    failures = []
    for name in handover.get("mappings") or []:
        for row in (handover.get("facts") or {}).get(name) or []:
            term = str(row.get("term", ""))
            if term and not re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", draft or "", re.I):
                failures.append({"kind": "mapping_not_shown", "text": f"{name}: {term}",
                                 "context": f"show how {row.get('of', 'the question')!r} was read: "
                                            "each term with its reason and its placing"})
    return failures


def check_report(draft: str, received: Any) -> list[dict]:
    """Every statement in the draft that what the agent received does not vouch for."""
    if _holds_nothing(received):
        return [{"kind": "no_working_record",
                 "text": "the run's record is missing, so nothing in the draft could be checked",
                 "context": "tell the reader the run was not recorded; do not restate the draft"}]
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
                         "why": ("no fact, row or table the run holds carries this number. If "
                                 "it came from a tool you called before run_skill, the run has "
                                 "no record of it and cannot vouch for it: take the number from "
                                 "a row of this run, or drop it."),
                         "context": " ".join(prose[start:end].split())})
    return (failures + _unvouched_links(draft, received) + _unstated_narrowing(draft, received)
            + _unshown_mappings(draft, received))
