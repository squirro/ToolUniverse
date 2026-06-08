"""``find_skill`` catalog search (ADR-0009). Pure + dependency-free."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class SkillDoc:
    """One indexed served skill: distinctive tokens + a short human-readable description."""

    name: str
    tokens: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class SkillHit:
    name: str
    score: float
    description: str

_STOPWORDS = frozenset(
    """
    a an the for of to and or but by with from on in into at as is are be it its this that
    you your given produce producing produces agent assistant biotech holding company team
    report reports profile profiling
    """.split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, stopword- and single-char-filtered."""
    return [w for w in _WORD_RE.findall(text.lower()) if len(w) > 1 and w not in _STOPWORDS]


def role_description(body: str) -> str:
    """The contiguous text block immediately under the ``# Role`` heading (one paragraph)."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "# Role":
            buf: list[str] = []
            for nxt in lines[i + 1:]:
                if not nxt.strip():
                    break
                buf.append(nxt.strip())
            return " ".join(buf)
    return ""


def header_triggers(body: str) -> list[str]:
    """Parse an optional ``Triggers: a, b, c`` line from the leading HTML-comment header.

    Lives in a comment, so adding triggers to a mis-routing skill does NOT change the served
    body. Returns lowercased trigger phrases."""
    m = re.search(r"<!--(.*?)-->", body, re.DOTALL)
    block = m.group(1) if m else body[:800]
    tm = re.search(r"^\s*Triggers?\s*:\s*(.+)$", block, re.IGNORECASE | re.MULTILINE)
    if not tm:
        return []
    return [t.strip().lower() for t in tm.group(1).split(",") if t.strip()]


def _doc_tokens(name: str, body: str) -> tuple[tuple[str, ...], str]:
    """Distinctive token bag for one skill + its short description.

    The skill-id and explicit Triggers are repeated (weighting) because they are the most
    deliberate routing signal; the Role description fills in domain vocabulary."""
    desc = role_description(body)
    name_toks = [t for t in _WORD_RE.findall(name.lower()) if len(t) > 1]
    trigger_toks: list[str] = []
    for phrase in header_triggers(body):
        trigger_toks.extend(_WORD_RE.findall(phrase))
    tokens = name_toks * 3 + trigger_toks * 3 + tokenize(desc)
    short = desc.split(". ")[0][:200] if desc else name.replace("-", " ")
    return tuple(tokens), short


def build_index(skills_dir: str | Path) -> list[SkillDoc]:
    """Index every ``*.md`` in ``skills_dir`` (sorted by name)."""
    directory = Path(skills_dir)
    if not directory.is_dir():
        return []
    docs: list[SkillDoc] = []
    for path in sorted(directory.glob("*.md")):
        tokens, desc = _doc_tokens(path.stem, path.read_text(encoding="utf-8"))
        docs.append(SkillDoc(path.stem, tokens, desc))
    return docs


def search(docs: list[SkillDoc], query: str, limit: int = 5) -> list[SkillHit]:
    """Return up to ``limit`` skills ranked by BM25 over the indexed metadata.

    BM25 (via ``bm25s``) gives tf-saturation + idf, so the shared skill-template phrasing
    (low idf) cannot dominate and the distinctive name/domain tokens decide the ranking.
    Skills with zero overlap are dropped; ties break by name for determinism."""
    import bm25s

    q = tokenize(query)
    if not docs or not q:
        return []
    corpus_tokens = [list(d.tokens) for d in docs]
    retriever = bm25s.BM25()
    retriever.index(corpus_tokens, show_progress=False)
    idxs, scores = retriever.retrieve(
        [q], k=min(limit, len(docs)), show_progress=False
    )
    hits: list[SkillHit] = []
    for i, score in zip(idxs[0], scores[0]):
        if score > 0:
            d = docs[int(i)]
            hits.append(SkillHit(d.name, round(float(score), 4), d.description))
    hits.sort(key=lambda h: (-h.score, h.name))
    return hits
