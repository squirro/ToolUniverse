"""The test workflow must gate the branch that actually ships (DSR-657).

``swiss-rockets`` is the only branch that produces a deployable SMCP image (ADR-0010);
``main`` is an ungated mirror of upstream that must never build one. Until DSR-657 the
workflow triggered on ``main`` alone, so the reviewed ``main -> swiss-rockets`` PR ran no
tests and every registry-wide static guard in ``tests/unit`` gated nothing.

This guard exists because ``.github/workflows/tests.yml`` is an **upstream** file that
re-syncs from ``mims-harvard:main``. A sync that restores upstream's ``on:`` block would
silently switch the gate off again — silently, because a workflow that does not trigger
reports no failure. Asserting the trigger here turns that into a red test.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "tests.yml"

# The branch ADR-0010 designates as the sole build-trust boundary.
SHIPPING_BRANCH = "swiss-rockets"


def _triggers() -> dict:
    """The workflow's ``on:`` mapping.

    YAML 1.1 parses the bare key ``on`` as the boolean ``True``, so a GitHub Actions
    workflow loaded with ``safe_load`` keys its triggers under ``True``, not ``"on"``.
    Accept either rather than depending on which YAML version the loader implements.
    """
    loaded = yaml.safe_load(WORKFLOW.read_text())
    triggers = loaded.get("on", loaded.get(True))
    assert triggers is not None, f"{WORKFLOW} declares no triggers"
    return triggers


def test_workflow_file_exists():
    assert WORKFLOW.is_file(), f"expected the test workflow at {WORKFLOW}"


def test_pushes_to_the_shipping_branch_run_the_tests():
    branches = _triggers()["push"]["branches"]
    assert SHIPPING_BRANCH in branches, (
        f"push to {SHIPPING_BRANCH} does not trigger the test suite; "
        f"declared branches are {branches}"
    )


def test_pull_requests_into_the_shipping_branch_run_the_tests():
    branches = _triggers()["pull_request"]["branches"]
    assert SHIPPING_BRANCH in branches, (
        f"the main -> {SHIPPING_BRANCH} PR does not trigger the test suite; "
        f"declared branches are {branches}"
    )
