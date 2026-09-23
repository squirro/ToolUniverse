"""New code may not hide a failure from the agent (DSR-659).

A tool that catches everything and returns an empty value tells the agent nothing went
wrong, so zero rows read as a real negative rather than an unreachable source. The
baseline names each accepted site and how many instances of it are accepted, so a new
swallow cannot pass by hiding behind one that was removed elsewhere, nor behind another
instance of itself in a file that already holds one: almost all of the population is
upstream code that re-syncs from mims-harvard:main.
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
#
# A site key is path + fingerprint, and the fingerprint hashes the enclosing scope, the
# opening line and the handler body -- but two handlers can still land on an identical key
# (same function, same body, e.g. two copy-pasted `except Exception: return {}` blocks), so
# the baseline holds a count per key, not just the key's presence. The guard fails a key
# that is new, a key whose observed count exceeds what is accepted, or -- checked in
# aggregate, which is what actually closes the hole a per-key check alone leaves open -- a
# baseline whose total accepted count does not equal every swallow the scan finds.


def _site_counts(findings):
    counts: dict[str, int] = {}
    for f in findings:
        key = f"{f.path}:{silent_swallow.fingerprint(f)}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def test_no_site_has_more_instances_than_the_baseline_accepts():
    observed = _site_counts(silent_swallow.scan(ROOT))
    accepted = {key: entry["count"] for key, entry in BASELINE["sites"].items()}

    new = sorted(key for key in observed if key not in accepted)
    over = sorted(
        f"{key}: {observed[key]} found, {accepted[key]} accepted"
        for key in observed
        if key in accepted and observed[key] > accepted[key]
    )

    assert not new and not over, (
        "new silent swallows:\n" + "\n".join(new)
        + "\nsites with more instances than the baseline accepts:\n" + "\n".join(over)
        + "\nMake the handler tell the caller what failed, or waive it with a stated reason.")


def test_the_baseline_does_not_accept_more_than_the_current_population_at_any_site():
    """A key with room to spare is slack a new swallow at that same site can hide in."""
    observed = _site_counts(silent_swallow.scan(ROOT))
    accepted = {key: entry["count"] for key, entry in BASELINE["sites"].items()}

    slack = sorted(
        f"{key}: accepts {accepted[key]}, only {observed.get(key, 0)} found"
        for key in accepted
        if accepted[key] > observed.get(key, 0)
    )

    assert not slack, (
        "the baseline accepts more instances than exist at these sites:\n" + "\n".join(slack)
        + "\nLower the accepted count in silent_swallow_baseline.json.")


def test_the_baseline_accounts_for_every_finding():
    """The sum of accepted counts must equal every swallow the scan finds, not a sample.

    This is the load-bearing check: the two per-key tests above only rule out a *known*
    site holding more than it should. This rules out the baseline holding accepted room
    that no key currently occupies -- the same hole a frozen total count had, in a new
    shape, closed by requiring the total to be exact rather than merely non-decreasing.
    """
    findings = silent_swallow.scan(ROOT)
    accepted_total = sum(entry["count"] for entry in BASELINE["sites"].values())

    assert accepted_total == len(findings), (
        f"baseline accepts {accepted_total} across its sites, scan finds {len(findings)}. "
        "Re-freeze the baseline in silent_swallow_baseline.json."
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
