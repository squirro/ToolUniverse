"""New code may not hide a failure from the agent (DSR-659).

A tool that catches everything and returns an empty value tells the agent nothing went
wrong, so zero rows read as a real negative rather than an unreachable source. The count
is frozen and may fall, never rise: almost all of the population is upstream code that
re-syncs from mims-harvard:main.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.tools_sr import silent_swallow

ROOT = Path(silent_swallow.__file__).resolve().parents[1]
BASELINE = json.loads(
    (ROOT / "tools_sr" / "silent_swallow_baseline.json").read_text()
)


def _src(*lines):
    return "\n".join(lines)


# --- the ratchet ---


def test_the_count_has_not_risen_above_the_frozen_baseline():
    findings = silent_swallow.scan(ROOT)

    assert len(findings) <= BASELINE["count"], (
        f"{len(findings)} silent swallows, baseline {BASELINE['count']}. New ones:\n"
        + "\n".join(f.message for f in findings[-12:])
    )


def test_the_baseline_is_not_stale_by_a_wide_margin():
    """Slack in the ratchet lets a new swallow in. Re-freeze when this trips."""
    findings = silent_swallow.scan(ROOT)

    assert len(findings) >= BASELINE["count"] - 20, (
        f"{len(findings)} found against a baseline of {BASELINE['count']}; "
        "lower the baseline in silent_swallow_baseline.json"
    )


# --- what is and is not a swallow; the expected value is the lines reported ---

CASES = {
    # a handler that returns an empty value is the defect being guarded
    "returns_empty_dict": (_src(
        "def fetch(url):",
        "    try:",
        "        return call(url)",
        "    except Exception:",
        "        return {}"), [4]),
    "bare_except_pass": (_src("try:", "    risky()", "except:", "    pass"), [3]),
    # server logs are not the agent's channel: logging alone still returns nothing
    "falls_through_after_logging": (_src(
        "try:",
        "    risky()",
        "except Exception as exc:",
        "    logger.warning('it failed: %s', exc)"), [3]),
    "logs_then_returns_none": (_src(
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception as exc:",
        "        logger.error('bad: %s', exc)",
        "        return None"), [4]),
    # diagnostic words count in returns and assignments only, or logger.warning()
    # would suppress the finding by containing 'warning'
    "warning_word_inside_a_log_call": (_src(
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception as exc:",
        "        logger.warning('failure detail: %s', exc)",
        "        return []"), [4]),
    "re_raises": (_src("try:", "    risky()", "except Exception:", "    raise"), []),
    "returns_the_reason": (_src(
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception as exc:",
        "        return {'error': str(exc)}"), []),
    # a narrow handler is a decision, not an absence of one
    "narrow_handler": (_src(
        "def f():",
        "    try:",
        "        return d[k]",
        "    except KeyError:",
        "        return None"), []),
    # `try: import cupy` asks whether an optional dependency is there; exempted
    # structurally so upstream files need no pragma
    "optional_dependency_probe": (
        _src("try:", "    import cupy", "except Exception:", "    cupy = None"), []),
    "pragma_with_a_reason": (_src(
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception:",
        "        # silent-swallow: the caller treats absence as the answer, see DSR-000",
        "        return {}"), []),
    # a bare pragma silences the guard without thinking
    "pragma_without_a_reason": (_src(
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception:",
        "        # silent-swallow:",
        "        return {}"), [4]),
    "pragma_covers_only_its_own_handler": (_src(
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception:",
        "        # silent-swallow: deliberate, the probe is the point",
        "        return {}",
        "",
        "def g():",
        "    try:",
        "        return call()",
        "    except Exception:",
        "        return {}"), [11]),
}


@pytest.mark.parametrize("name", list(CASES))
def test_a_handler_is_reported_exactly_where_it_should_be(name):
    source, expected = CASES[name]

    findings = silent_swallow.find_in_source(source)

    assert [f.line for f in findings] == expected, [f.message for f in findings]


# --- the report itself ---


def test_each_finding_names_its_file_and_line():
    """A count alone does not tell you what to fix."""
    findings = silent_swallow.scan(ROOT)

    assert findings
    sample = findings[0]
    assert str(sample.path).endswith(".py")
    assert sample.line > 0
    assert ":" in sample.message
