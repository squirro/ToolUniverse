"""The skill oracle scores ONE live turn against ONE served skill body.

It reads only the trace: which skill `get_skill` loaded, which real tools the
`execute_tool` calls dispatched, what those calls returned, and whether the
answer's footnotes carry links. Every rule here has a signature we actually
observed on sr-dev during the 2026-08-20 hand-debugging session.

The asymmetry the design rests on: a trace can FAIL a skill but never PASS one.
So unambiguous defects are `fail`, everything suggestive is `warn`, and the two
known environment artefacts (provider bio-risk refusal, cold container) are
`retry` — they must not be counted as skill defects.
"""

import sys
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))

from skill_audit.oracle import (
    classify_call,
    mentioned_tools,
    required_tools,
    score,
    verdict,
)

BODY = """---
Triggers: outbreak, epidemic, pathogen
---

# Role
Outbreak intelligence.

## Phase 1 — Taxonomy
**Primary**: `BVBRC_search_taxonomy`(keyword="<pathogen name>") -> species name.
**Enrich**: if ambiguous, call `NCBIDatasets_suggest_taxonomy`(taxon_query="<name>").

## Phase 2 — Targets
**Primary**: `UniProt_search`(query="<pathogen name> reviewed:true") -> proteins.
"""

pytestmark = pytest.mark.unit


def _action(tool_name, *, parameters=None, output=None, status="finished"):
    return {
        "tool_name": tool_name,
        "status": status,
        "content": {"parameters": parameters or {}, "output": output},
    }


def _exec(tu_tool, output='{"results": [{"id": 1}]}'):
    return _action("execute_tool",
                   parameters={"tool_name": tu_tool, "arguments": {}},
                   output=output)


def _codes(findings):
    return {f.code for f in findings}


# --- reading the body: the skill declares its own required tools -------------

def test_required_tools_takes_the_primary_calls_only():
    assert required_tools(BODY) == ["BVBRC_search_taxonomy", "UniProt_search"]


def test_mentioned_tools_also_takes_the_enrich_calls():
    assert "NCBIDatasets_suggest_taxonomy" in mentioned_tools(BODY)


# --- hard failures ----------------------------------------------------------

def test_body_tool_coverage_reports_what_the_body_named_and_what_ran():
    """Only 3 of 86 bodies use the **Primary** convention, so required_tools is
    inert across the corpus. Coverage over EVERY tool the body names is the
    signal that actually exists — reported as data, not as a verdict, because
    a body legitimately names gated and alternative tools that should not fire."""
    from skill_audit.oracle import body_tool_coverage
    cov = body_tool_coverage(BODY, fired=["BVBRC_search_taxonomy", "PubMed_search"])
    assert cov["named"] == 3            # BVBRC, NCBIDatasets, UniProt
    assert cov["from_body"] == 1        # only BVBRC was one of them
    assert cov["off_body"] == ["PubMed_search"]


def test_body_tool_coverage_is_empty_when_there_is_no_body():
    from skill_audit.oracle import body_tool_coverage
    assert body_tool_coverage(None, fired=["X"]) == {}


def test_a_turn_with_no_get_skill_call_fails():
    findings = score("infectious-disease",
                     actions=[_action("paragraph_retriever")],
                     answer="Some prose.", error=None, body=BODY)
    assert "no_skill_loaded" in _codes(findings)
    assert verdict(findings) == "fail"


def test_a_skill_that_loads_but_fires_no_tool_fails():
    actions = [_action("get_skill", parameters={"name": "infectious-disease"})]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "skill_without_tools" in _codes(findings)


def test_a_tool_that_does_not_exist_fails():
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("find_tools", output="Tool 'find_tools' not found"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "tool_not_found" in _codes(findings)


def test_a_call_rejected_on_its_schema_fails():
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy",
              output="execute_tool() got an unexpected keyword argument 'keyword'"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "schema_rejected" in _codes(findings)


def test_a_tool_that_raised_fails():
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("UniProt_search", output='{"error": "HTTPError 500"}'),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "tool_error" in _codes(findings)


def test_a_successful_envelope_is_never_an_error_however_its_prose_reads():
    """openFDA label text is long free prose — matching /exception|error/ inside
    a `status: success` payload flagged 50 healthy calls in the first sweep."""
    label = ('{"status": "success", "data": {"meta": {"disclaimer": "Do not '
             'rely on openFDA... with the exception of an HTTPError traceback '
             'mentioned in the warnings section"}}}')
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy", output=label),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "tool_error" not in _codes(findings)


def test_a_truncated_success_envelope_is_still_a_success():
    """Squirro caps a tool's output, so a long openFDA label arrives as JSON cut
    mid-string. The parse fails, and scanning the surviving prose finds "with the
    exception of" — which is how a healthy call got flagged twice."""
    from skill_audit.oracle import classify_call
    truncated = ('{"status": "success", "data": {"meta": {"disclaimer": "Do not '
                 'rely on openFDA...", "warnings": "Use with the exception of '
                 'patients with an HTTPError of hepatic impairment')
    assert classify_call(truncated) == "ok"


def test_a_truncated_error_envelope_is_still_an_error():
    truncated = ('{"status": "error", "error": "upstream exploded at line 40 of '
                 'the handler and the rest of this envelope never arrived')
    assert classify_call(truncated) == "error"


def test_a_rejected_parameter_is_a_schema_rejection_not_an_exception():
    """The live envelope says 'Parameter validation failed ... is a required
    property' with type ToolValidationError — the agent called the tool wrong."""
    envelope = ('{"status": "error", "error": "Parameter validation failed for '
                "'root': 'drug_chembl_id' is a required property\", "
                '"error_details": {"type": "ToolValidationError"}}')
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("ChEMBL_get_drug_mechanisms", output=envelope),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "schema_rejected" in _codes(findings)
    assert "tool_error" not in _codes(findings)


def test_a_tool_reporting_no_matches_is_empty_not_broken():
    """CT.gov answers an over-narrow query with an error-status envelope whose
    message is 'No studies found'. The tool worked; the query matched nothing."""
    envelope = ('{"status": "error", "error": "No studies found for the given '
                'query parameters. Please examine your input and try different '
                'parameters.", "source_url": "https://clinicaltrials.gov/x"}')
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy", output=envelope),
        _exec("UniProt_search", output=envelope),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "tool_error" not in _codes(findings)
    assert "zero_rows" in _codes(findings)


def test_a_missing_required_parameter_is_a_schema_rejection():
    """alphafold_get_summary was called with protein_name instead of qualifier."""
    envelope = ('{"status": "error", "error": "Missing required parameter '
                "'qualifier'\", \"query\": {\"protein_name\": \"SSTR2\"}}")
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("alphafold_get_summary", output=envelope),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "schema_rejected" in _codes(findings)


def test_an_entity_the_database_does_not_hold_is_a_lookup_miss_not_a_crash():
    """GPCRdb ran, and answered: that identifier is not one of ours. The tool
    worked; the agent guessed the identifier format. Worth reading, not a fail."""
    envelope = ('{"status": "error", "error": "Protein not found: sstr2_human. '
                'Use GPCRdb entry name (e.g. adrb2_human) or UniProt accession.", '
                '"source_url": "https://gpcrdb.org/services/protein/x"}')
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("GPCRdb_get_protein", output=envelope),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "lookup_miss" in _codes(findings)
    assert "tool_error" not in _codes(findings)
    assert verdict(findings) == "warn"


def test_an_upstream_that_returns_no_data_is_a_lookup_miss():
    envelope = ('{"status": "error", "error": "No data returned from gnomAD '
                'API", "status_code": 200, "data": null}')
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("gnomad_search_variants", output=envelope),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "lookup_miss" in _codes(findings)


def test_a_genuine_error_envelope_still_fails():
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("UniProt_search",
              output='{"status": "error", "error": "HTTPError 500 from upstream"}'),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "tool_error" in _codes(findings)


def test_a_footnote_without_a_link_fails():
    answer = "Claim.[^1^]\n\n[^1^]: BVBRC_search_taxonomy, keyword=H5N1"
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy"),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer=answer, error=None, body=BODY)
    assert "linkless_footnote" in _codes(findings)


def test_a_footnote_that_carries_a_link_is_accepted():
    answer = ("Claim.[^1^]\n\n[^1^]: [BV-BRC taxonomy]"
              "(https://www.bv-brc.org/view/Taxonomy/11320)")
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy"),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer=answer, error=None, body=BODY)
    assert "linkless_footnote" not in _codes(findings)


# --- environment artefacts: retry, never fail -------------------------------

def test_a_provider_refusal_is_a_retry_not_a_failure():
    """Zero actions plus an error at the start of the turn is the OpenAI
    bio-risk refusal — it fired on a plain H5N1 brief and passed on re-run."""
    findings = score("infectious-disease", actions=[], answer="",
                     error="An error has occurred while processing your request",
                     body=BODY)
    assert _codes(findings) == {"provider_refusal"}
    assert verdict(findings) == "retry"


def test_an_error_after_real_work_is_a_genuine_failure():
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy"),
    ]
    findings = score("infectious-disease", actions=actions, answer="",
                     error="upstream timeout", body=BODY)
    assert "turn_error" in _codes(findings)
    assert verdict(findings) == "fail"


# --- warnings: rank the review queue, do not fail the run -------------------

def test_loading_a_different_skill_is_only_a_warning():
    """Another skill sometimes genuinely fits better — record the name and let
    a human judge."""
    actions = [
        _action("get_skill", parameters={"name": "disease-research"}),
        _exec("OpenTargets_get_disease_id_description_by_name"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "wrong_skill" in _codes(findings)
    assert verdict(findings) == "warn"
    got = next(f for f in findings if f.code == "wrong_skill")
    assert got.evidence["loaded"] == "disease-research"


def test_primary_tools_that_never_fired_are_warned_with_the_ratio():
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    got = next(f for f in findings if f.code == "missing_primary_tools")
    assert got.evidence["missing"] == ["UniProt_search"]
    assert got.evidence["fired"] == 1
    assert got.evidence["required"] == 2


def test_every_call_returning_nothing_is_the_starved_warning():
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy", output='{"results": []}'),
        _exec("UniProt_search", output='{"results": []}'),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "zero_rows" in _codes(findings)


def test_a_skill_loaded_after_the_web_batch_is_warned():
    """Loading last means the skill did not govern the turn."""
    actions = [
        _action("exa_web_search"),
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy"),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "skill_after_web" in _codes(findings)


def test_the_platform_retriever_running_first_is_not_the_skill_arriving_late():
    """Squirro fires paragraph_retriever on its own before the agent chooses
    anything — it opened 64 of 76 turns in the first full sweep, so counting it
    as a web batch condemns every skill for the platform's own behaviour."""
    actions = [
        _action("paragraph_retriever"),
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy"),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "skill_after_web" not in _codes(findings)


def test_consulting_the_skill_index_first_counts_as_going_to_skills_first():
    """find_skill IS the skill route. A turn that opens with it has not
    deferred to the web, whatever runs while it decides."""
    actions = [
        _action("find_skill", parameters={"query": "outbreak brief"}),
        _action("exa_web_search"),
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy"),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="Some prose.", error=None, body=BODY)
    assert "skill_after_web" not in _codes(findings)


def test_an_answer_that_declines_is_warned():
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy"),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer="I cannot provide the current situation.",
                     error=None, body=BODY)
    assert "answer_declined" in _codes(findings)


# --- the clean run ----------------------------------------------------------

def test_a_run_that_does_everything_the_body_asks_passes():
    answer = ("Brief.[^1^]\n\n[^1^]: [BV-BRC](https://www.bv-brc.org/x)")
    actions = [
        _action("get_skill", parameters={"name": "infectious-disease"}),
        _exec("BVBRC_search_taxonomy"),
        _exec("UniProt_search"),
    ]
    findings = score("infectious-disease", actions=actions,
                     answer=answer, error=None, body=BODY)
    assert findings == []
    assert verdict(findings) == "pass"


@pytest.mark.parametrize("codes,expected", [
    ([], "pass"),
    (["wrong_skill"], "warn"),
    (["provider_refusal"], "retry"),
    (["wrong_skill", "no_skill_loaded"], "fail"),
])
def test_the_verdict_is_the_worst_finding(codes, expected):
    from skill_audit.oracle import SEVERITY, SkillFinding
    findings = [SkillFinding(code=c, severity=SEVERITY[c], message="", evidence={})
                for c in codes]
    assert verdict(findings) == expected
