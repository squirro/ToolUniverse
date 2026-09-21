"""Puts the required ID namespace into the description the model actually reads (DSR-662).

155 served tools require an identifier in a specific namespace, document that in the
*parameter* description, and never mention it in the *tool* description -- the only surface
a model sees at every call. ``HPA_get_cancer_prognostics_by_gene`` advertises "prognostic
value of a gene" while requiring ``ensembl_id``, which is why two skill bodies call it with
a bare gene symbol and come back empty.

Derived at load time rather than authored (ADR-0014): nothing goes stale, no file under
``data/`` is modified, and tools upstream writes later inherit the behaviour.

**The namespace is read from the parameter's own grammar, not matched against a list.**
Parameter descriptions already say "Ensembl Gene **ID**", "UniProt **accession**", "MONDO
**CURIE**", so the words before that noun name the namespace. A hardcoded list of databases
would be wrong the moment upstream adds one, and this registry gains tools continuously.

The derived phrasing is formulaic, which is fine: discovery here is permanently
keyword-based (DSR-639 closed Won't Do), so what matters is that the namespace token is
present, not that the prose reads well.
"""

from __future__ import annotations

import functools
import re

__all__ = ["apply", "derive_cue", "install", "namespaces"]

# The noun that marks a preceding word as a namespace.
_ID_NOUN = re.compile(r"\b(?:IDs?|CIDs?|accessions?|identifiers?|CURIEs?|codes?)\b")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")
# Words sitting between the namespace and the noun: "Ensembl *Gene* ID".
_QUALIFIERS = {
    "gene", "genes", "protein", "proteins", "compound", "molecule", "disease",
    "target", "drug", "variant", "study", "trial", "pathway", "term", "entry",
    "primary", "unique", "valid", "internal", "external", "numeric", "stable",
}
# Words that end the search backwards -- nothing before them qualifies. The imperative
# verbs matter: these descriptions routinely append guidance like "Find IDs using
# biomodels_search", and "Find" is capitalised only because it starts a sentence.
_STOPWORDS = {
    "the", "a", "an", "this", "that", "its", "their", "or", "and", "of", "for",
    "with", "to", "in", "on", "by", "as", "is", "be", "any", "each", "one", "two",
    "optional", "required", "e.g", "eg", "such", "list", "set", "comma", "separated",
    "find", "get", "search", "use", "using", "provide", "specify", "enter", "obtain",
    "retrieve", "see", "look", "pass", "supply", "accepts", "returns", "lookup",
}
# A parenthetical is a gloss, not the namespace: "The EFO (Experimental Factor Ontology)
# ID" names EFO, and walking back from "ID" would otherwise land on "Ontology".
_PARENTHETICAL = re.compile(r"\([^)]*\)")
# A quoted example value, e.g. 'ENSG00000141510' or 'CHEMBL25'.
_EXAMPLE = re.compile(r"['\"]([A-Za-z]{2,}[:_]?\d[A-Za-z0-9:_.\-]*)['\"]")


def namespaces(param_description: str) -> list[str]:
    """Namespaces the parameter pins, in order of first mention, de-duplicated.

    Walks backwards from each "ID"/"accession"/"CURIE" noun rather than matching one
    regex, because the words in between vary ("Ensembl Gene ID", "The ChEMBL ID", "a
    MONDO CURIE") and a single pattern greedily swallows articles and qualifiers.
    """
    text = param_description or ""
    found: list[str] = []

    for noun in _ID_NOUN.finditer(text):
        # Blank out glosses rather than deleting them, so offsets stay aligned.
        before = _PARENTHETICAL.sub(lambda m: " " * len(m.group()), text[: noun.start()])
        preceding = _WORD.findall(before)
        for word in reversed(preceding[-3:]):
            lowered = word.lower()
            if lowered in _QUALIFIERS:
                continue  # skip "Gene" in "Ensembl Gene ID"
            if lowered in _STOPWORDS:
                break  # "The" in "The ID" -- no namespace here
            # A namespace is a proper noun: capitalised, substantial, and not itself an
            # example accession -- 'P04637 ID' names no database.
            if word[0].isupper() and len(word) >= 3 and not any(c.isdigit() for c in word):
                # Keep the registry's own casing (ChEMBL, UniProt, MONDO).
                if word not in found:
                    found.append(word)
            break

    return found


def _required_params(tool: dict) -> list[tuple[str, dict]]:
    parameter = tool.get("parameter") or {}
    properties = parameter.get("properties") or {}
    required = parameter.get("required") or []
    return [
        (name, properties[name])
        for name in required
        if isinstance(properties.get(name), dict)
    ]


def derive_cue(tool: dict) -> str | None:
    """The sentence to append to this tool's description, or ``None`` if none is needed.

    Only *required* parameters count. An optional namespaced filter is not what a model
    gets wrong when it makes the call.
    """
    found: list[str] = []
    example: str | None = None

    for _, spec in _required_params(tool):
        description = spec.get("description") or ""
        for name in namespaces(description):
            if name not in found:
                found.append(name)
        if example is None and found:
            match = _EXAMPLE.search(description)
            if match:
                example = match.group(1)

    if not found:
        return None

    # Already stated on the surface the model reads -- adding it again is noise.
    served = tool.get("description") or ""
    if all(re.search(rf"\b{re.escape(n)}\b", served, re.IGNORECASE) for n in found):
        return None

    # Phrased so no indefinite article ever precedes the namespace. "a UniProt" and "an
    # NCBI" are both right by sound and both wrong by first letter, and no cheap rule gets
    # them all; putting the namespace after "in the" removes the question entirely.
    cue = f"Requires an identifier in the {' or '.join(found)} namespace"
    if example:
        cue += f" (e.g. {example})"
    return cue + ", not a plain name or symbol."


def apply(tool: dict) -> dict:
    """Return the tool definition with the cue appended to its description.

    Never mutates the input. These definitions are loaded from files under ``data/``, and
    ADR-0014 requires that none of them be modified.
    """
    cue = derive_cue(tool)
    if cue is None:
        return tool

    served = (tool.get("description") or "").rstrip()
    updated = dict(tool)
    updated["description"] = f"{served} {cue}" if served else cue
    return updated


def install(cls) -> None:
    """Rewrite served descriptions after the registry loads. Safe to call repeatedly.

    Wraps ``load_tools`` from outside rather than editing ``execute_function.py``, which
    re-syncs from upstream (ADR-0014). The rewrite lands on the in-memory
    ``all_tool_dict`` only -- nothing under ``data/`` is written.
    """
    original = cls.load_tools
    if getattr(original, "_sr_id_cue", False):
        return

    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        served = getattr(self, "all_tool_dict", None)
        if isinstance(served, dict):
            for name, tool in served.items():
                if isinstance(tool, dict):
                    served[name] = apply(tool)
        return result

    wrapper._sr_id_cue = True
    cls.load_tools = wrapper
