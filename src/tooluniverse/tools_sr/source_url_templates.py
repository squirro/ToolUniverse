"""Declarative source-URL templates for tools that share one POST endpoint (DSR-671).

DSR-667 cites the call that produced an answer by reading the intercepted request URL.
That works for a GET, whose parameters are in the URL, and says nothing for a POST, whose
parameters are in the body. All 56 OpenTargets tools POST to a single GraphQL endpoint, so
the intercepted URL is byte-identical whatever was asked; citing it would render a footnote
that looks checked and lands nowhere, which DSR-631 rates as worse than no citation.

The fix is to stop deriving the link from the transport and declare it instead. A template
names the human-readable record the answer describes -- the target page, the disease page,
the evidence page -- and is rendered from the call's own arguments, so each tool produces a
distinct, openable link.

Templates live here rather than in ``data/opentarget_tools.json`` because that file
re-syncs from upstream and an edit to 56 entries would conflict on every sync (ADR-0014,
the same reasoning that keeps ``install`` outside ``execute_function.py``). A tool that
declares ``source_url_template`` in its own definition still wins over anything here, so an
upstream tool can carry its own without this module knowing about it.

**A template that cannot be fully rendered produces no URL at all.** Emitting
``/target/None`` would be a link a researcher opens once and never trusts again.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import quote

__all__ = ["FAMILY_TEMPLATES", "TOOL_TEMPLATES", "candidates", "declared_url", "render"]

_OT = "https://platform.opentargets.org"

# Keyed by tool name, and checked before the family rules. These are the tools whose
# parameters do not say what kind of thing an identifier is: `entityId` is an Ensembl,
# EFO or ChEMBL id depending only on which tool was called, so the entity page it belongs
# to cannot be inferred from the arguments.
TOOL_TEMPLATES: dict[str, str] = {
    "OpenTargets_get_publications_by_target_ensemblID": f"{_OT}/target/{{entityId}}",
    "OpenTargets_get_publications_by_disease_efoId": f"{_OT}/disease/{{entityId}}",
    "OpenTargets_get_publications_by_drug_chemblId": f"{_OT}/drug/{{entityId}}",
    # Free-text lookups have no entity page until the lookup resolves, so they cite the
    # search that was actually run.
    "OpenTargets_search_category_counts_by_query_string": f"{_OT}/search?q={{queryString}}",
    "OpenTargets_multi_entity_search_by_query_string": f"{_OT}/search?q={{queryString}}",
    "OpenTargets_get_disease_id_description_by_name": f"{_OT}/search?q={{diseaseName}}",
    "OpenTargets_get_target_id_description_by_name": f"{_OT}/search?q={{targetName}}",
    "OpenTargets_get_drug_id_description_by_name": f"{_OT}/search?q={{drugName}}",
    "OpenTargets_get_drug_chembId_by_generic_name": f"{_OT}/search?q={{drugName}}",
    # Off-domain on purpose: a GO term has no OpenTargets page, and the citation should
    # point where the claim can be checked rather than where the call happened to go.
    "OpenTargets_get_gene_ontology_terms_by_goID": (
        "https://www.ebi.ac.uk/QuickGO/term/{goIds}"
    ),
}

# Keyed by the tool definition's ``type``, and tried in order: the first template whose
# placeholders are all satisfied by the call wins. Most specific first, so a call carrying
# both a target and a disease cites the evidence page for that pair rather than the target
# page alone.
FAMILY_TEMPLATES: dict[str, tuple[str, ...]] = {
    "OpenTarget": (
        f"{_OT}/evidence/{{ensemblId}}/{{efoId}}",
        f"{_OT}/target/{{ensemblId}}",
        f"{_OT}/disease/{{efoId}}",
        f"{_OT}/drug/{{chemblId}}",
    ),
    "OpentargetToolDrugNameMatch": (f"{_OT}/search?q={{drugName}}",),
}

_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def render(template: str, arguments: Mapping | None) -> str | None:
    """The template with every ``{name}`` replaced by that argument, or ``None``.

    Pure: template plus arguments in, string or nothing out, no network and no registry.

    ``None`` whenever a placeholder has no usable value. A partly-rendered URL is the one
    outcome worth avoiding -- it is indistinguishable from a real citation until someone
    follows it. Values are percent-encoded, since a search term may carry spaces
    ("BRAF V600E") and an identifier may not be one this module has seen.
    """
    if not template:
        return None

    values: dict[str, str] = {}
    for name in _PLACEHOLDER.findall(template):
        value = arguments.get(name) if isinstance(arguments, Mapping) else None
        # A list argument cites its first element: the page is per-entity, and a call for
        # several entities has no single record to point at.
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        if value is None:
            return None
        rendered = str(value).strip()
        if not rendered:
            return None
        values[name] = quote(rendered, safe="")

    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)


def candidates(tool_name: str | None, config: Mapping | None) -> tuple[str, ...]:
    """Templates to try for this tool, most specific first.

    Precedence is definition, then per-tool table, then family. A tool that declares its
    own ``source_url_template`` is the authority on where its answer can be read, and this
    module must not override it.
    """
    declared = (config or {}).get("source_url_template") if isinstance(config, Mapping) else None
    if isinstance(declared, str) and declared:
        return (declared,)
    if isinstance(declared, (list, tuple)):
        return tuple(t for t in declared if isinstance(t, str) and t)
    if tool_name and tool_name in TOOL_TEMPLATES:
        return (TOOL_TEMPLATES[tool_name],)
    family = (config or {}).get("type") if isinstance(config, Mapping) else None
    return FAMILY_TEMPLATES.get(family, ())


def declared_url(
    tool_name: str | None, arguments: Mapping | None, config: Mapping | None
) -> str | None:
    """The first template for this tool that the call's arguments fully satisfy."""
    for template in candidates(tool_name, config):
        url = render(template, arguments)
        if url is not None:
            return url
    return None
