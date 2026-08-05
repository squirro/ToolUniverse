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


# --- the gate must also be reproducible ---
# The lint step runs before pytest, so if it fails nothing else in the job executes and
# every guard here is skipped. It installed `version: "latest"`, which means an upstream
# ruff release could switch the gate off without a single commit to this repo: 0.15.18
# reports the tree clean, while 0.16.1 -- with its expanded default rule set -- reports
# 22,270 errors. A gate whose verdict depends on the day it ran is not a gate.


def _lint_step() -> dict:
    jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
    for job in jobs.values():
        for step in job.get("steps", []):
            if str(step.get("uses", "")).startswith("astral-sh/ruff-action"):
                return step
    raise AssertionError("no astral-sh/ruff-action step found in the test workflow")


def test_the_lint_step_pins_an_exact_ruff_version():
    version = str(_lint_step().get("with", {}).get("version", ""))

    assert version and version != "latest", (
        "the lint step must pin an exact ruff version: a floating 'latest' lets an "
        f"upstream release fail the job and skip every guard (got {version!r})"
    )
    assert all(part.isdigit() for part in version.split(".")), (
        f"expected an exact version like '0.15.18', got {version!r}"
    )
