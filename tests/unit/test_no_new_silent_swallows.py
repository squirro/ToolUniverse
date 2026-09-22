"""New code may not hide a failure from the agent (DSR-659).

A tool that catches everything and returns an empty value tells the agent nothing went
wrong. The agent reads zero rows as a real negative -- "no interactions reported" rather
than "the source was unreachable" -- and writes a confident wrong answer. DSR-666 fixed
that at the envelope; this holds the line at the source.

Containment, not remediation. The count is frozen and may fall, never rise. Almost all of
the population is upstream code that re-syncs from mims-harvard:main, so rewriting it would
conflict on every sync -- which is also why the optional-dependency exemption is structural
rather than a pragma sprinkled through upstream files.
"""

import json
from pathlib import Path

from tooluniverse.tools_sr import silent_swallow

ROOT = Path(silent_swallow.__file__).resolve().parents[1]
BASELINE = json.loads(
    (ROOT / "tools_sr" / "silent_swallow_baseline.json").read_text()
)


# --- the ratchet ---


def test_the_count_has_not_risen_above_the_frozen_baseline():
    findings = silent_swallow.scan(ROOT)

    assert len(findings) <= BASELINE["count"], (
        f"{len(findings)} silent swallows, baseline {BASELINE['count']}. New ones:\n"
        + "\n".join(f.message for f in findings[-12:])
    )


def test_the_baseline_is_not_stale_by_a_wide_margin():
    """If the real count drops well below the frozen one, the ratchet has slack in it and
    a new swallow can be added without failing anything. Re-freeze when this trips."""
    findings = silent_swallow.scan(ROOT)

    assert len(findings) >= BASELINE["count"] - 20, (
        f"{len(findings)} found against a baseline of {BASELINE['count']}; "
        "lower the baseline in silent_swallow_baseline.json"
    )


# --- proof the guard can fail ---


def test_a_newly_introduced_silent_swallow_is_found():
    source = "\n".join([
        "def fetch(url):",
        "    try:",
        "        return call(url)",
        "    except Exception:",
        "        return {}",
    ])

    findings = silent_swallow.find_in_source(source, "new_tool.py")

    assert len(findings) == 1, findings
    assert findings[0].line == 4


def test_a_bare_except_that_passes_is_found():
    source = "try:\n    risky()\nexcept:\n    pass\n"

    assert len(silent_swallow.find_in_source(source)) == 1


def test_a_handler_that_falls_through_after_logging_is_found():
    """The whole point of the rule. Server logs are not the agent's channel, so a handler
    whose only act is to log still returns nothing to the caller."""
    source = "\n".join([
        "try:",
        "    risky()",
        "except Exception as exc:",
        "    logger.warning('it failed: %s', exc)",
    ])

    assert len(silent_swallow.find_in_source(source)) == 1


def test_logging_does_not_rescue_a_handler_that_returns_empty():
    source = "\n".join([
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception as exc:",
        "        logger.error('bad: %s', exc)",
        "        return None",
    ])

    assert len(silent_swallow.find_in_source(source)) == 1


# --- what must NOT be reported ---


def test_a_handler_that_re_raises_is_not_a_swallow():
    source = "try:\n    risky()\nexcept Exception:\n    raise\n"

    assert silent_swallow.find_in_source(source) == []


def test_a_handler_that_returns_the_reason_is_not_a_swallow():
    source = "\n".join([
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception as exc:",
        "        return {'error': str(exc)}",
    ])

    assert silent_swallow.find_in_source(source) == []


def test_a_narrow_handler_is_a_decision_not_an_absence_of_one():
    source = "\n".join([
        "def f():",
        "    try:",
        "        return d[k]",
        "    except KeyError:",
        "        return None",
    ])

    assert silent_swallow.find_in_source(source) == []


def test_a_word_like_warning_inside_a_log_call_cannot_rescue_a_handler():
    """The diagnostic words are checked in returns and assignments only. Searching the
    whole body would let logger.warning() suppress the finding by containing 'warning'."""
    source = "\n".join([
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception as exc:",
        "        logger.warning('failure detail: %s', exc)",
        "        return []",
    ])

    assert len(silent_swallow.find_in_source(source)) == 1


def test_an_optional_dependency_probe_is_exempt_without_a_pragma():
    """`try: import cupy / except Exception: pass` is correct as written -- a missing
    optional dependency is the question being asked, not a failure to report. Exempted
    structurally so upstream files need no edit."""
    source = "try:\n    import cupy\nexcept Exception:\n    cupy = None\n"

    assert silent_swallow.find_in_source(source) == []


# --- waivers ---


def test_a_pragma_with_a_reason_suppresses_one_site():
    source = "\n".join([
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception:",
        "        # silent-swallow: the caller treats absence as the answer, see DSR-000",
        "        return {}",
    ])

    assert silent_swallow.find_in_source(source) == []


def test_a_pragma_without_a_reason_does_not_suppress():
    """A bare pragma is a way to silence the guard without thinking, which is how a
    ratchet stops meaning anything."""
    source = "\n".join([
        "def f():",
        "    try:",
        "        return call()",
        "    except Exception:",
        "        # silent-swallow:",
        "        return {}",
    ])

    assert len(silent_swallow.find_in_source(source)) == 1


def test_a_pragma_suppresses_only_the_handler_it_sits_in():
    source = "\n".join([
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
        "        return {}",
    ])

    findings = silent_swallow.find_in_source(source)

    assert len(findings) == 1
    assert findings[0].line == 11


# --- the report itself ---


def test_each_finding_names_its_file_and_line():
    """A count alone does not tell you what to fix."""
    findings = silent_swallow.scan(ROOT)

    assert findings
    sample = findings[0]
    assert str(sample.path).endswith(".py")
    assert sample.line > 0
    assert ":" in sample.message
