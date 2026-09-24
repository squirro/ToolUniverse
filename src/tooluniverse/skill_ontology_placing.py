"""Where an ontology puts a mapped term: evidence beside the agent's reason for it.

Membership in the source's list proves a term exists, not that it belongs, so the Ontology
Lookup Service (OLS) placing adds placed, not placed or unknown and never refuses a term.
The pure half reads recorded responses; the live half fetches them.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

ONTOLOGIES = ("hp", "mondo", "efo", "snomed", "mesh", "ncit", "chebi", "go")
OLS = "https://www.ebi.ac.uk/ols4/api"


_WORD = re.compile(r"[a-z]+")


def _words_of(concept: Any) -> list[str]:
    """The concept as words, whether the agent wrote a list or one phrase."""
    parts = [concept] if isinstance(concept, str) else list(concept or [])
    return [w for part in parts for w in _WORD.findall(str(part).lower())]


def place(responses: dict[str, dict], concept: Any) -> dict:
    """The verdict for one term from its recorded OLS responses, one entry per ontology.

    `concept`: words that name the branch the user meant. Placed when an ancestor label holds
    one of them; not placed when an ontology knows the term but no ancestor does; obsolete
    when the ontology retired the term and names no replacement it could place instead;
    unknown when no ontology knows it or the service failed. A retired term with a
    replacement is placed on the replacement, and the verdict names both.
    """
    words = _words_of(concept)
    known, retired, errors = [], [], []
    for ontology, response in responses.items():
        if "error" in response:
            errors.append(f"{ontology}: {response['error']}")
            continue
        hits = response.get("search") or []
        if not hits:
            continue
        hit = hits[0]
        if hit.get("is_obsolete"):
            retired.append((ontology, hit))
            continue
        replaced = _replaced(response.get("replaces"), hit)
        for ancestor in response.get("ancestors") or []:
            label = (ancestor.get("label") or "").lower()
            if any(word in label for word in words):
                return {"placing": "placed", "ontology": ontology, "term": hit.get("obo_id"),
                        "label": hit.get("label"), "under": ancestor.get("label"), **replaced}
        known.append((ontology, hit, replaced))
    if known:
        ontology, hit, replaced = known[0]
        return {"placing": "not placed", "ontology": ontology, "term": hit.get("obo_id"),
                "label": hit.get("label"), "under": None, **replaced}
    if retired:
        ontology, hit = retired[0]
        successor = hit.get("term_replaced_by")
        return {"placing": "obsolete", "ontology": ontology, "term": hit.get("obo_id"),
                "label": hit.get("label"), "under": None, "obsolete_term": hit.get("obo_id"),
                "replaced_by": successor,
                "note": (f"{hit.get('obo_id')} is obsolete in {ontology}; "
                         + (f"its replacement {successor} could not be looked up, so it is not placed"
                            if successor else "the ontology names no replacement, so it is not placed"))}
    verdict: dict[str, Any] = {"placing": "unknown", "ontology": None, "term": None,
                               "label": None, "under": None}
    if errors:
        verdict["note"] = "the lookup service failed: " + "; ".join(errors)
    return verdict


def _replaced(retired: dict | None, successor: dict) -> dict:
    """The fields that say a verdict stands on the replacement of a retired term."""
    if not retired:
        return {}
    return {"obsolete_term": retired.get("obo_id"), "replaced_by": successor.get("obo_id"),
            "note": (f"{retired.get('obo_id')} is obsolete in {retired.get('ontology_name')}; "
                     f"placed on its replacement {successor.get('obo_id')}")}


# Prefixes the processes' sources hand over as ids, with the ontology that defines them and
# the IRI stem OLS files them under. An unlisted prefix is read as a label.
_ID_PREFIXES = {
    "MONDO": ("mondo", "http://purl.obolibrary.org/obo/MONDO_"),
    "HP": ("hp", "http://purl.obolibrary.org/obo/HP_"),
    "EFO": ("efo", "http://www.ebi.ac.uk/efo/EFO_"),
    "ORPHANET": ("ordo", "http://www.orpha.net/ORDO/Orphanet_"),
    "DOID": ("doid", "http://purl.obolibrary.org/obo/DOID_"),
    "NCIT": ("ncit", "http://purl.obolibrary.org/obo/NCIT_"),
}
_ID = re.compile(r"^(?:https?://\S+/)?([A-Za-z]+)[_:](\d+)$")


def ontology_id(term: str) -> tuple[str, str] | None:
    """(ontology, IRI) when the term is an id: PREFIX_0001, PREFIX:0001 or its IRI; else None."""
    match = _ID.match(term.strip())
    if not match or match.group(1).upper() not in _ID_PREFIXES:
        return None
    ontology, stem = _ID_PREFIXES[match.group(1).upper()]
    return ontology, stem + match.group(2)


def _get(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "tooluniverse-skills",
                                                   "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        # OLS term pages carry raw control characters inside definitions.
        return json.loads(response.read(), strict=False)


def _hit(doc: dict) -> dict:
    hit = {k: doc.get(k) for k in ("iri", "obo_id", "label", "ontology_name")}
    if doc.get("is_obsolete"):
        # OLS4 lifts IAO_0100001 into term_replaced_by; older pages keep only the annotation.
        successor = doc.get("term_replaced_by") or \
            ((doc.get("annotation") or {}).get("term replaced by") or [None])[0]
        hit.update(is_obsolete=True, term_replaced_by=successor)
    return hit


def _ancestors(ontology: str, iri: str) -> list[dict]:
    quoted = urllib.parse.quote(urllib.parse.quote(iri, safe=""), safe="")
    above = _get(f"{OLS}/ontologies/{ontology}/terms/{quoted}/hierarchicalAncestors?size=200")
    return [{"iri": t["iri"], "label": t["label"]}
            for t in above.get("_embedded", {}).get("terms", [])]


def _by_id(ontology: str, iri: str, follow: bool = True) -> dict[str, dict]:
    """The term the id names, in its own ontology; an id OLS does not know is found nowhere.
    A retired term with a replacement it can look up answers with the replacement, once."""
    try:
        page = _get(f"{OLS}/ontologies/{ontology}/terms?" + urllib.parse.urlencode({"iri": iri}))
        hits = [_hit(doc) for doc in page.get("_embedded", {}).get("terms", [])]
        if hits and hits[0].get("is_obsolete"):
            successor = ontology_id(hits[0].get("term_replaced_by") or "")
            if follow and successor:
                answer = _by_id(*successor, follow=False)
                found = answer.get(successor[0], {})
                if found.get("search") and not found["search"][0].get("is_obsolete"):
                    return {successor[0]: {**found, "replaces": hits[0]}}
            return {ontology: {"search": hits, "ancestors": []}}
        ancestors = _ancestors(ontology, hits[0]["iri"]) if hits else []
        return {ontology: {"search": hits, "ancestors": ancestors}}
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {ontology: {"search": [], "ancestors": []}}
        return {ontology: {"error": f"HTTPError: {exc.code}"}}
    except Exception as exc:                              # noqa: BLE001 — evidence, never a gate
        return {ontology: {"error": f"{type(exc).__name__}: {str(exc)[:80]}"}}


def lookup(term: str, ontologies: tuple[str, ...] = ONTOLOGIES) -> dict[str, dict]:
    """The recorded shape `place` reads, fetched live: an id by its IRI, else exact label or
    synonym; then ancestors."""
    named = ontology_id(term)
    if named:
        return _by_id(*named)
    responses: dict[str, dict] = {}
    for ontology in ontologies:
        try:
            found = _get(f"{OLS}/search?" + urllib.parse.urlencode(
                {"q": term.lower(), "ontology": ontology, "rows": 1,
                 "queryFields": "label,synonym", "exact": "true"}))
            hits = [_hit(doc) for doc in found["response"]["docs"]]
            ancestors = _ancestors(ontology, hits[0]["iri"]) if hits else []
            responses[ontology] = {"search": hits, "ancestors": ancestors}
        except Exception as exc:                          # noqa: BLE001 — evidence, never a gate
            responses[ontology] = {"error": f"{type(exc).__name__}: {str(exc)[:80]}"}
    return responses
