"""A tool definition may not declare the same key twice.

`json.load` keeps the LAST occurrence and says nothing, so a duplicate key is a
silent data loss in a file that is edited by hand across ~2,200 tools. Found the
hard way: a `test_examples` block added to
`HPA_get_rna_expression_in_specific_tissues` sat above an existing
`"test_examples": []` a few lines below, and the tool went on reporting that it
had no examples while the file plainly contained one.

Nothing about that is visible in a diff, in `json.load`, or in the tool's
behaviour — only in the gap between what the file says and what the registry
holds. Hence a test.
"""

import glob
import json
import os

import pytest

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "data")
FILES = sorted(glob.glob(os.path.join(DATA, "**", "*.json"), recursive=True))


def _duplicate_keys(pairs):
    """object_pairs_hook that records any key seen more than once."""
    seen, dupes = set(), []
    for key, _ in pairs:
        if key in seen:
            dupes.append(key)
        seen.add(key)
    if dupes:
        _duplicate_keys.found.append(dupes)
    return dict(pairs)


@pytest.mark.unit
@pytest.mark.parametrize("path", FILES, ids=[os.path.basename(p) for p in FILES])
def test_no_object_declares_the_same_key_twice(path):
    _duplicate_keys.found = []
    try:
        json.load(open(path, encoding="utf-8"), object_pairs_hook=_duplicate_keys)
    except json.JSONDecodeError:
        pytest.skip("not valid JSON; a different test's problem")

    assert not _duplicate_keys.found, (
        f"{os.path.basename(path)} declares duplicate keys "
        f"{_duplicate_keys.found}; json.load silently keeps the last one"
    )
