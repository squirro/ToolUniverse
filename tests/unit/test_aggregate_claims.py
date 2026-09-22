"""A review queue for descriptions promising an aggregate they do not return (DSR-664).

An agent that reads "returns frequencies" and receives raw per-record rows with no
denominator presents counts as rates. The description is the only surface it reads before
calling, so a promise made there is the whole contract.

**These tests never fail on the queue's contents.** Detection is mechanical; adjudication is
not. Four in five hits turn out truthful under a differently-named field, a nested block, or
a word that is not a statistic at all -- "clade distribution", "publication frequency",
"water flow rate". A gate on that would be red forever and switched off within a week. What
is asserted is that every entry has been ruled on, which is the part that rots.
"""

import pytest

from tooluniverse.tools_sr import aggregate_claims, description_contract

TOOLS = description_contract.load_tools(aggregate_claims.data_dir())


@pytest.mark.unit
def test_every_queue_entry_has_been_adjudicated():
    """The only assertion with teeth. A new tool joining the queue arrives unreviewed and
    turns this red until somebody rules on it -- which is the workflow, not a gate on the
    tools themselves."""
    pending = aggregate_claims.unadjudicated(TOOLS)

    assert not pending, "\n".join(
        f"{c.tool}: promises {c.promised}; declares {c.declared[:6] or '(none)'}"
        for c in pending
    )


@pytest.mark.unit
def test_the_queue_reports_rather_than_blocks():
    """Named for the reader: there is deliberately no assertion on how many entries exist."""
    queue = aggregate_claims.review_queue(TOOLS)

    assert queue, "the queue should not be empty; the population is real"
    for claim in queue:
        assert claim.verdict in {"overclaim", "undeclared-schema", "truthful"}, claim


@pytest.mark.unit
def test_the_canonical_mutations_case_is_in_the_reviewed_set():
    """cBioPortal_get_mutations promises nothing -- "Get mutation data for specific genes"
    -- and returns sampleId/patientId/proteinChange rows with no denominator. The overclaim
    is in the silence, so no returns-clause rule can reach it; it is carried in by name."""
    queue = {claim.tool: claim for claim in aggregate_claims.review_queue(TOOLS)}

    assert "cBioPortal_get_mutations" in queue
    assert queue["cBioPortal_get_mutations"].verdict == "overclaim"


@pytest.mark.unit
def test_a_promise_outside_a_returns_clause_is_still_carried_in():
    """GDC_get_mutation_frequency says 'frequency statistics' in its opening sentence and
    never repeats it, so a returns-clause scan misses it."""
    queue = {claim.tool: claim for claim in aggregate_claims.review_queue(TOOLS)}

    assert queue["GDC_get_mutation_frequency"].verdict == "overclaim"


@pytest.mark.unit
def test_the_genuine_overclaims_have_a_follow_up_path():
    genuine = aggregate_claims.genuine_overclaims(TOOLS)

    assert genuine
    for claim in genuine:
        assert claim.reason.strip(), claim.tool


@pytest.mark.unit
def test_every_adjudication_records_a_reason():
    for tool, (verdict, reason) in aggregate_claims.ADJUDICATED.items():
        assert verdict in {"overclaim", "undeclared-schema", "truthful"}, (tool, verdict)
        assert len(reason.strip()) > 15, (tool, reason)


@pytest.mark.unit
def test_no_adjudication_has_gone_stale():
    """A verdict for a tool that no longer exists is dead weight, and would silently cover
    a different tool if that name ever came back."""
    unknown = [
        tool for tool in aggregate_claims.ADJUDICATED
        if tool not in TOOLS and tool not in aggregate_claims.NAMED_ADDITIONS
    ]

    assert unknown == [], unknown


@pytest.mark.unit
def test_a_schema_field_under_another_name_counts_as_truthful():
    """`obsExp` is an observed/expected ratio; `af` is an allele frequency. Reporting those
    would be reporting tools that are already correct."""
    tools = {
        "R_tool": {"name": "R_tool", "description": "Returns the observed/expected ratio.",
                   "return_schema": {"properties": {"obsExp": {}}}},
        "F_tool": {"name": "F_tool", "description": "Returns allele frequencies.",
                   "return_schema": {"properties": {"af": {}}}},
    }

    assert aggregate_claims.review_queue(tools) == []


@pytest.mark.unit
def test_a_promise_with_no_matching_field_reaches_the_queue():
    tools = {"C_tool": {
        "name": "C_tool",
        "description": "Returns per-sample rows and mutation frequencies.",
        "return_schema": {"properties": {"sample_id": {}, "count": {}}},
    }}

    queue = aggregate_claims.review_queue(tools)

    assert [c.tool for c in queue] == ["C_tool"]
    assert "frequencies" in queue[0].promised


@pytest.mark.unit
def test_the_report_groups_by_verdict_for_a_human_to_work_through():
    text = aggregate_claims.report(TOOLS)

    assert "overclaim" in text and "truthful" in text
    assert "cBioPortal_get_mutations" in text
