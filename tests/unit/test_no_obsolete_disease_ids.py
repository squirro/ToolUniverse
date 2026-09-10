"""No tool may document a disease id that its ontology has retired.

Twenty-two tools carried `test_examples` built on EFO ids that EFO itself marks
obsolete. OpenTargets has migrated its disease index to MONDO, so those ids now
resolve to nothing and every one of those tools fails on its own documented
example.

The mapping below is not inferred -- it is EFO's own `term_replaced_by`:

    EFO_0000384  obsolete_Crohn's disease               -> MONDO_0005011
    EFO_0000339  obsolete_chronic myelogenous leukemia  -> MONDO_0011996
    EFO_0000685  obsolete_rheumatoid arthritis          -> MONDO_0008383

Verified live against api.platform.opentargets.org: the replacements return
6,289 / 4,479 / 8,184 associated targets respectively, while the originals
return `disease: null`.

This matters beyond the audit. `test_examples` is what a human copies and what
the audit calls, so a stale example teaches the wrong id to everyone who reads
it.
"""

import glob
import json
import os

import pytest

DATA = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "data"
)

# EFO id -> the MONDO id EFO records as its replacement.
RETIRED_DISEASE_IDS = {
    "EFO_0000384": "MONDO_0005011",
    "EFO_0000339": "MONDO_0011996",
    "EFO_0000685": "MONDO_0008383",
}


def _tools_with_examples():
    for path in glob.glob(os.path.join(DATA, "**", "*.json"), recursive=True):
        try:
            defs = json.load(open(path))
        except Exception:
            continue
        if not isinstance(defs, list):
            continue
        for tool in defs:
            if isinstance(tool, dict) and tool.get("test_examples"):
                yield os.path.basename(path), tool


@pytest.mark.unit
@pytest.mark.parametrize("retired,replacement", sorted(RETIRED_DISEASE_IDS.items()))
def test_no_tool_documents_a_retired_disease_id(retired, replacement):
    offenders = [
        f"{fname}::{tool['name']}"
        for fname, tool in _tools_with_examples()
        if retired in json.dumps(tool["test_examples"])
    ]
    assert not offenders, (
        f"{retired} is obsolete in EFO (replaced by {replacement}) and resolves "
        f"to nothing in OpenTargets, but {len(offenders)} tools still document "
        f"it: {offenders[:6]}"
    )
