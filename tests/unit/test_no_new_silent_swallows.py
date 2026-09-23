"""New code may not hide a failure from the agent (DSR-659).

A tool that catches everything and returns an empty value tells the agent nothing went
wrong, so zero rows read as a real negative rather than an unreachable source. The
baseline names the accepted sites, not a count, so a new swallow cannot pass by hiding
behind one that was removed elsewhere: almost all of the population is upstream code
that re-syncs from mims-harvard:main.
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


def _sites(findings):
    return {f"{f.path}:{silent_swallow.fingerprint(f)}" for f in findings}


def test_no_site_swallows_that_the_baseline_does_not_already_accept():
    new = _sites(silent_swallow.scan(ROOT)) - set(BASELINE["sites"])

    assert not new, (
        "new silent swallows:\n" + "\n".join(sorted(new))
        + "\nMake the handler tell the caller what failed, or waive it with a stated reason.")


def test_the_baseline_does_not_accept_sites_that_are_gone():
    """A baseline that outlives its sites is slack a new swallow can hide in."""
    stale = set(BASELINE["sites"]) - _sites(silent_swallow.scan(ROOT))

    assert not stale, (
        "the baseline accepts sites that no longer exist:\n" + "\n".join(sorted(stale))
        + "\nRemove them from silent_swallow_baseline.json.")


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
    # the live openFDA and OpenTargets shape: a success envelope with nothing inside
    "returns_a_success_envelope_with_an_empty_collection": (_src(
        "def fetch(url):",
        "    try:",
        "        return call(url)",
        "    except Exception:",
        "        return {'status': 'ok', 'results': []}"), [4]),
    # a key merely named like a diagnostic must not rescue a handler that says nothing
    "returns_a_key_named_like_a_note_but_says_nothing": (_src(
        "def fetch(url):",
        "    try:",
        "        return call(url)",
        "    except Exception:",
        "        return {'notes': []}"), [4]),
    # a handler that genuinely names the failure is still not a swallow
    "returns_the_error_text": (_src(
        "def fetch(url):",
        "    try:",
        "        return call(url)",
        "    except Exception as exc:",
        "        return {'error': str(exc)}"), []),
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
