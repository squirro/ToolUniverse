"""The agent cited things the run cannot vouch for, and the refusal never said why.

Two shapes of the same gap, measured on the live run `skill-adverse-event-detection-5be65f81`.

**The run's own address.** The agent footnoted
`https://data.swissrockets.com/skills/runs/skill-adverse-event-detection-5be65f81` as though
it were a source document. The check refused it, correctly -- a Run Record address is the
run's own bookkeeping and vouches nothing. The agent then wrote the same citation again on
the second submit, because nothing told it why the first was refused, and the report reached
the reader with the failure stated.

**Anything obtained before the skill loaded.** On the same run the agent called
`openai_web_search` at action 1 and `run_skill` at action 3. Every number and link from that
early call is in neither the hand-over nor the Working Record, so nothing can vouch for it.
The check names them, which is right; the agent was never told that it would.

The failure text names the link but not the reason, so a re-ask has nothing to act on. A
check that reports the same failure every run is a check people learn to skim, and the
genuine findings beside it -- on this run, an invented rubric weight of "30" -- get skimmed
with it. The cost is the credibility of the failure list, not the one citation.
"""

import pytest

from tooluniverse.skill_report_check import check_report, why_refused
from tooluniverse.skill_runner import WRITE_THE_REPORT

pytestmark = pytest.mark.unit

RUN_URL = "https://data.swissrockets.com/skills/runs/skill-adverse-event-detection-5be65f81"

HELD = {"handover": {"facts": {}, "tables": [], "fetched": [
    {"url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=508496cb",
     "reports": 4200}]}}


def _failures(draft, kind=None):
    return [f for f in check_report(draft, HELD) if kind is None or f["kind"] == kind]


# ------------------------------------------------------------- the refusal says why

def test_a_refused_link_says_why_it_was_refused():
    """Naming the link and not the reason is what let the agent repeat it."""
    (failure,) = _failures(f"See the run at {RUN_URL}", "unvouched_link")

    # Not merely "there is a reason": the reason must be this link's own, or the agent is
    # back to guessing, which is what produced the same citation twice.
    assert "bookkeeping" in failure["why"].lower(), failure["why"]


def test_a_link_the_run_never_saw_says_a_different_why():
    """A different refusal needs a different reason, or the text teaches nothing."""
    (failure,) = _failures("See https://example.org/some/page", "unvouched_link")

    assert "bookkeeping" not in failure["why"].lower()
    assert "never received this link" in failure["why"]


def test_the_run_s_own_address_is_named_as_bookkeeping_not_as_an_unknown_source():
    assert "bookkeeping" in why_refused(RUN_URL, saw_domain=False).lower()


def test_a_refused_number_says_why_it_was_refused():
    (failure,) = _failures("The label lists 9999 reports.", "unvouched_number")

    assert failure["why"], failure


# ---------------------------------------------------------- the instruction surface states it

def test_the_report_rules_say_a_run_address_is_not_a_source():
    rules = " ".join(WRITE_THE_REPORT).lower()

    assert "skills/runs" in rules, rules


def test_the_report_rules_say_what_to_cite_instead():
    rules = " ".join(WRITE_THE_REPORT).lower()

    assert "row" in rules and "own link" in rules


def test_the_report_rules_say_a_number_from_before_the_skill_cannot_be_cited():
    """DSR-812: the early call's numbers are in no record, so they cannot be vouched."""
    rules = " ".join(WRITE_THE_REPORT).lower()

    assert "before" in rules and ("run_skill" in rules or "skill" in rules), rules


# --------------------------------------------------------------- what must keep working

def test_a_number_the_run_holds_is_still_accepted():
    assert _failures("The label lists 4200 reports.", "unvouched_number") == []


def test_a_link_the_run_holds_is_still_accepted():
    draft = "See https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=508496cb"

    assert _failures(draft, "unvouched_link") == []
