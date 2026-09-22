"""Where an ontology puts a mapped term: evidence beside the agent's reason for it.

Membership in the source's list proves a term exists, not that it belongs, so the Ontology
Lookup Service (OLS) placing adds placed, not placed or unknown and never refuses a term.
The pure half reads recorded responses; the live half fetches them.
"""

from __future__ import annotations

import json
import re
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
    one of them; not placed when an ontology knows the term but no ancestor does; unknown
    when no ontology knows it or the service failed.
    """
    words = _words_of(concept)
    known, errors = [], []
    for ontology, response in responses.items():
        if "error" in response:
            errors.append(f"{ontology}: {response['error']}")
            continue
        hits = response.get("search") or []
        if not hits:
            continue
        hit = hits[0]
        for ancestor in response.get("ancestors") or []:
            label = (ancestor.get("label") or "").lower()
            if any(word in label for word in words):
                return {"placing": "placed", "ontology": ontology, "term": hit.get("obo_id"),
                        "label": hit.get("label"), "under": ancestor.get("label")}
        known.append((ontology, hit))
    if known:
        ontology, hit = known[0]
        return {"placing": "not placed", "ontology": ontology, "term": hit.get("obo_id"),
                "label": hit.get("label"), "under": None}
    verdict: dict[str, Any] = {"placing": "unknown", "ontology": None, "term": None,
                               "label": None, "under": None}
    if errors:
        verdict["note"] = "the lookup service failed: " + "; ".join(errors)
    return verdict


def _get(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "tooluniverse-skills",
                                                   "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def lookup(term: str, ontologies: tuple[str, ...] = ONTOLOGIES) -> dict[str, dict]:
    """The recorded shape `place` reads, fetched live: exact label or synonym, then ancestors."""
    responses: dict[str, dict] = {}
    for ontology in ontologies:
        try:
            found = _get(f"{OLS}/search?" + urllib.parse.urlencode(
                {"q": term.lower(), "ontology": ontology, "rows": 1,
                 "queryFields": "label,synonym", "exact": "true"}))
            hits = [{k: doc.get(k) for k in ("iri", "obo_id", "label", "ontology_name")}
                    for doc in found["response"]["docs"]]
            ancestors = []
            if hits:
                iri = urllib.parse.quote(urllib.parse.quote(hits[0]["iri"], safe=""), safe="")
                above = _get(f"{OLS}/ontologies/{ontology}/terms/{iri}/hierarchicalAncestors?size=200")
                ancestors = [{"iri": t["iri"], "label": t["label"]}
                             for t in above.get("_embedded", {}).get("terms", [])]
            responses[ontology] = {"search": hits, "ancestors": ancestors}
        except Exception as exc:                          # noqa: BLE001 — evidence, never a gate
            responses[ontology] = {"error": f"{type(exc).__name__}: {str(exc)[:80]}"}
    return responses
