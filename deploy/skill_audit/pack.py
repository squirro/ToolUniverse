"""The pack two blinded judges score: the reports of one question, one arm each, with the
abstract of every cited paper, and no word that says which arm wrote which.

The agent's leading "Research Plan" quoteblock names its tools, so it is stripped and kept
beside the blinded text. Everything is pure over an injected `fetch(url) -> str`: the tests
replay recorded responses, the command line uses the network.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

try:                                   # XML from the network: no entity expansion
    import defusedxml.ElementTree as ET
except ImportError:                    # pragma: no cover
    import xml.etree.ElementTree as ET

PLAN_MARK = "Research Plan"

# Words that would tell a judge which arm wrote the report.
ARM_WORDS = ("Research Plan", "Step A", "first-batch calls", "run_skill", "continue_skill",
             "fetch_run_data", "submit_report", "get_skill", "find_skill", "execute_tool",
             "exa_web_search", "openai_web_search", "perplexity", "ToolUniverse", "OptimusKG",
             "Skill Process", "hand-over", "handover", "Working Record")

IDCONV = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


@dataclass(frozen=True)
class Citation:
    kind: str       # pmid | pmc | doi
    ident: str


# --- blinding ------------------------------------------------------------------------------

def strip_plan(text: str) -> tuple[str, str | None]:
    """Remove the leading quoteblock that names the plan; blank lines inside the run belong to it."""
    lines = text.splitlines()
    if not lines or not lines[0].startswith(">"):
        return text, None
    end = next((n for n, line in enumerate(lines) if n and not line.startswith(">") and line.strip()),
               len(lines))
    plan = "\n".join(line for line in lines[:end] if line)
    if PLAN_MARK not in plan:
        return text, None
    return "\n".join(lines[end:]), plan


# --- citations -----------------------------------------------------------------------------

_LINKS = [
    ("pmid", re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)")),
    ("pmc", re.compile(r"(?:pmc\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov/pmc)/articles/(PMC\d+)")),
    ("doi", re.compile(r"doi\.org/(10\.\d{4,9}/[^\s)\]\"'>]+)")),
]


def citations(text: str) -> list[Citation]:
    """Every paper the text links, in order of first appearance, each once."""
    found: list[tuple[int, Citation]] = []
    for kind, pattern in _LINKS:
        for match in pattern.finditer(text):
            found.append((match.start(), Citation(kind, match.group(1).rstrip(".,;"))))
    out: list[Citation] = []
    for _, citation in sorted(found, key=lambda pair: pair[0]):
        if citation not in out:
            out.append(citation)
    return out


def _get(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "tooluniverse-skills pack builder"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _pubmed_record(pmid: str, fetch: Callable[[str], str]) -> dict | None:
    root = ET.fromstring(fetch(f"{EFETCH}?db=pubmed&id={pmid}&retmode=xml"))
    article = root.find(".//Article")
    if article is None:
        return None
    parts = []
    for node in article.findall(".//Abstract/AbstractText"):
        label = node.get("Label")
        body = "".join(node.itertext()).strip()
        parts.append(f"{label}: {body}" if label else body)
    return {"pmid": pmid, "title": "".join(article.find("ArticleTitle").itertext()).strip()
            if article.find("ArticleTitle") is not None else "",
            "abstract": "\n".join(parts), "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}


def resolve(citation: Citation, fetch: Callable[[str], str] = _get) -> dict | None:
    """The paper behind a link: pmid, title, the whole abstract, and its PubMed url.
    A PMC id goes through NCBI's id converter; a DOI is looked up in Europe PMC."""
    if citation.kind == "pmid":
        return _pubmed_record(citation.ident, fetch)
    if citation.kind == "pmc":
        converted = json.loads(fetch(f"{IDCONV}?" + urllib.parse.urlencode(
            {"ids": citation.ident, "format": "json", "tool": "tooluniverse"})))
        records = [r for r in converted.get("records", []) if r.get("pmid")]
        return _pubmed_record(str(records[0]["pmid"]), fetch) if records else None
    if citation.kind == "doi":
        found = json.loads(fetch(f"{EUROPEPMC}?" + urllib.parse.urlencode(
            {"query": f'DOI:"{citation.ident}"', "format": "json", "resultType": "core"})))
        hits = found.get("resultList", {}).get("result", [])
        if not hits:
            return None
        hit = hits[0]
        pmid = str(hit.get("pmid") or "")
        return {"pmid": pmid, "title": hit.get("title", ""), "abstract": hit.get("abstractText", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid
                else f"https://doi.org/{citation.ident}"}
    raise ValueError(f"unknown citation kind {citation.kind!r}")


# --- the pack ------------------------------------------------------------------------------

def build_pack(question: str, reports: dict[str, str], fetch: Callable[[str], str] = _get) -> dict:
    """One question, the reports under neutral labels, each with its resolved abstracts."""
    entries = []
    for label, original in reports.items():
        text, plan = strip_plan(original)
        resolved = []
        for citation in citations(text):
            try:
                found = resolve(citation, fetch)
            except Exception as exc:                          # noqa: BLE001 -- recorded, not fatal
                found = None
                resolved.append({"citation": citation.__dict__, "error": f"{type(exc).__name__}: {exc}"})
                continue
            if found:
                resolved.append({"citation": citation.__dict__, **found, "complete": True})
            else:
                resolved.append({"citation": citation.__dict__, "error": "not found"})
        entries.append({"label": label, "text": text, "original": original, "plan": plan,
                        "citations": resolved})
    return {"question": question, "reports": entries}


def render(pack: dict) -> str:
    """The pack as the judges read it: the question, then each report and its abstracts, whole."""
    out = [f"# Pack\n\nQuestion: {pack['question']}\n"]
    for entry in pack["reports"]:
        out.append(f"\n---\n\n## Report {entry['label']}\n\n{entry['text']}\n")
        if entry["citations"]:
            out.append(f"\n### Cited papers, report {entry['label']}\n")
        for found in entry["citations"]:
            if "error" in found:
                out.append(f"- {found['citation']['kind']} {found['citation']['ident']}: {found['error']}\n")
                continue
            out.append(f"\n**{found['title']}** (PMID {found['pmid']}, {found['url']})\n\n{found['abstract']}\n")
    return "\n".join(out)


def check_pack(pack: dict, question: str, arm_words: tuple[str, ...] = ARM_WORDS,
               fetch: Callable[[str], str] | None = None) -> list[str]:
    """Everything wrong with a pack before the judges see it; an empty list means it may go.
    With a `fetch`, each abstract is checked against the source again."""
    problems = []
    if pack.get("question") != question:
        problems.append(f"question: the header holds {pack.get('question')!r}, not the question asked")
    for entry in pack["reports"]:
        for word in arm_words:
            if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", entry["text"], re.I):
                problems.append(f"report {entry['label']}: the word {word!r} identifies an arm")
        for found in entry["citations"]:
            if "error" in found:
                problems.append(f"report {entry['label']}: {found['citation']['kind']} "
                                f"{found['citation']['ident']} did not resolve ({found['error']})")
                continue
            if found["abstract"].endswith("…") or found["abstract"].endswith("...") \
                    or not found.get("complete"):
                problems.append(f"report {entry['label']}: the abstract of PMID {found['pmid']} is cut; "
                                "the pack must hold it complete")
            elif fetch is not None:
                again = resolve(Citation(**found["citation"]), fetch)
                if again and again["abstract"] != found["abstract"]:
                    problems.append(f"report {entry['label']}: the abstract of PMID {found['pmid']} "
                                    "differs from the source; the pack must hold it complete")
    return problems


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--question", required=True)
    parser.add_argument("--report", action="append", required=True, metavar="LABEL=PATH",
                        help="a report file under a neutral label, e.g. A=web.md")
    parser.add_argument("--out", required=True, help="directory for pack.md, pack.json and the originals")
    args = parser.parse_args(argv)
    reports = {}
    for spec in args.report:
        label, path = spec.split("=", 1)
        reports[label] = Path(path).read_text()
    pack = build_pack(args.question, reports)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pack.md").write_text(render(pack))
    (out / "pack.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False))
    for entry in pack["reports"]:
        (out / f"original_{entry['label']}.md").write_text(entry["original"])
    problems = check_pack(pack, args.question)
    for problem in problems:
        print("PROBLEM:", problem, file=sys.stderr)
    print(f"pack written to {out} ({len(pack['reports'])} reports); "
          f"{'ready for the judges' if not problems else f'{len(problems)} problems'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
