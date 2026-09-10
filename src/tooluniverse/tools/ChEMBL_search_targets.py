"""
ChEMBL_search_targets

Search targets by name, organism, target type, or other criteria. Use this tool to find target Ch...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_targets(
    target_chembl_id: Optional[str] = None,
    pref_name__contains: Optional[str] = None,
    pref_name__icontains: Optional[str] = None,
    target_synonym__icontains: Optional[str] = None,
    target_components__accession: Optional[str] = None,
    organism: Optional[str] = None,
    target_type: Optional[str] = None,
    fields: Optional[list[str]] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search targets by gene symbol, UniProt accession, name, organism or target type.

    Resolution order when looking up a protein:

    1. **Gene symbol** (``CCKBR``, ``KRAS``, ``SSTR2``) -> ``target_synonym__icontains``.
       ChEMBL stores gene symbols as component synonyms, *not* in ``pref_name``.
    2. **UniProt accession** (``P32239``) -> ``target_components__accession``. Most precise.
    3. **Human-readable protein name** -> ``pref_name__icontains``.

    ``pref_name__contains`` will silently return zero results for a gene symbol - that is a
    property of the ChEMBL data model, not an error, so it cannot be diagnosed by retrying.

    Parameters
    ----------
    target_chembl_id : str
        Filter by target ChEMBL ID
    pref_name__contains : str
        Filter by target preferred name, case-sensitive substring. Does NOT match gene symbols.
    pref_name__icontains : str
        Filter by target preferred name, case-insensitive substring.
    target_synonym__icontains : str
        Filter by any target synonym, case-insensitive. The correct field for a GENE SYMBOL.
    target_components__accession : str
        Filter by UniProt accession of a target component (e.g. 'P32239').
    organism : str
        Filter by organism (e.g., 'Homo sapiens')
    target_type : str
        Filter by target type (e.g., 'SINGLE PROTEIN', 'PROTEIN COMPLEX')
    fields : list[str]
        Optional list of ChEMBL target fields to include in each returned target obje...
    limit : int

    offset : int

    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "target_chembl_id": target_chembl_id,
            "pref_name__contains": pref_name__contains,
            "pref_name__icontains": pref_name__icontains,
            "target_synonym__icontains": target_synonym__icontains,
            "target_components__accession": target_components__accession,
            "organism": organism,
            "target_type": target_type,
            "fields": fields,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_targets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_targets"]
