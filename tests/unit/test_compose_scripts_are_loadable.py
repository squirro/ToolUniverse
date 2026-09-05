"""A compose script may not use a relative import.

ComposeTool loads these files by path, not as package members:

    spec = importlib.util.spec_from_file_location("compose_module", file_path)
    spec.loader.exec_module(compose_module)

The resulting module is named `compose_module` and has no package, so `from
..utils import x` raises "attempted relative import with no known parent
package" the first time the tool is called. Nothing catches it earlier: pytest
imports the same file as `tooluniverse.compose_scripts.<name>`, where the
relative import resolves perfectly. The unit tests pass, the server fails.

Found live over SMCP against a freshly built image, after a relative import was
added here in good faith.
"""

import ast
import glob
import importlib.util
import os

import pytest

COMPOSE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "compose_scripts"
)
SCRIPTS = sorted(glob.glob(os.path.join(COMPOSE_DIR, "*.py")))


@pytest.mark.unit
def test_the_servers_loader_really_cannot_resolve_a_relative_import(tmp_path):
    """Pin the constraint itself, so the rule below reads as a consequence."""
    script = tmp_path / "compose_script.py"
    script.write_text("from ..utils import get_user_cache_dir\n")

    spec = importlib.util.spec_from_file_location("compose_module", str(script))
    module = importlib.util.module_from_spec(spec)

    with pytest.raises(ImportError, match="relative import"):
        spec.loader.exec_module(module)


@pytest.mark.unit
@pytest.mark.parametrize("path", SCRIPTS, ids=[os.path.basename(p) for p in SCRIPTS])
def test_no_compose_script_uses_a_relative_import(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    relative = [
        f"line {node.lineno}: from {'.' * node.level}{node.module or ''} import "
        + ", ".join(a.name for a in node.names)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level > 0
    ]
    assert not relative, (
        f"{os.path.basename(path)} is loaded by path as `compose_module`, which has "
        f"no parent package, so these fail at call time: {relative}. Import from "
        f"`tooluniverse.<module>` instead."
    )
