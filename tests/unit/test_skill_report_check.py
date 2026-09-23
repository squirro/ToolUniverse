"""The server reads the draft report before the user does.

Pure: the draft and what the agent received go in, failures come out. "Received" is the
hand-over's facts and the rows the agent fetched -- not the whole Working Record: with
megabytes of abstracts on record, almost any small number occurs somewhere in it.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_report_check import check_report, _domain_of  # noqa: E402

pytestmark = pytest.mark.unit

RECEIVED = {
    "facts": {"prr_table": [
        {"term": "ototoxicity", "prr": 54.76612, "flagged": True,
         "url": "https://api.fda.gov/drug/event.json?search=cisplatin+ototoxicity"}]},
    "fetched": [{"pmid": "31234567", "year": 2019,
                 "abstract": "Hearing loss occurred in 57% with weekly dosing against 82%.",
                 "url": "https://pubmed.ncbi.nlm.nih.gov/31234567/"}],
}
FAERS_KEYED = {"facts": {"url": "https://api.fda.gov/drug/event.json?search=reactionmeddrapt"
                                "%3A%22ototoxicity%22&limit=1&api_key=REDACTED"}}


@pytest.mark.parametrize("draft,received", [
    # A number the agent received passes in any rounding the value admits.
    ("Ototoxicity shows PRR 54.77 [1]. Hearing loss occurred in 57% with weekly dosing "
     "against 82% (2019).\n\n"
     "[1]: https://api.fda.gov/drug/event.json?search=cisplatin+ototoxicity", RECEIVED),
    # A received link passes with or without the punctuation prose puts after it.
    ("See (https://pubmed.ncbi.nlm.nih.gov/31234567/). "
     "And https://pubmed.ncbi.nlm.nih.gov/31234567.", RECEIVED),
    # The agent rightly drops `api_key=REDACTED` before it cites a FAERS query.
    ("[^3^]: https://api.fda.gov/drug/event.json?search=reactionmeddrapt%3A%22ototoxicity%22"
     "&limit=1", FAERS_KEYED),
    # Heading numbers, list markers and the size chip the chat adds are not claims.
    ("## 7. Integrated Assessment\n"
     "Primary completion 2026-01-20; published 2026-07.\n"
     "1) Drug overview\n"
     "2. Labeled safety\n"
     "- code_interpreter_code.py <sub>(2.8 KB)</sub>\n"
     "The PRR is 54.77.", RECEIVED),
])
def test_a_draft_backed_by_what_the_agent_received_has_no_failures(draft, received):
    assert check_report(draft, received) == []


def test_a_number_nothing_vouches_for_is_a_failure_that_quotes_it_in_context():
    """A number cited to a source that never gave it must be caught and quoted back."""
    draft = "Ototoxicity shows PRR 54.77, against a Canadian PRR of about 53.44 in the same period."

    (failure,) = check_report(draft, RECEIVED)

    assert failure["kind"] == "unvouched_number" and failure["text"] == "53.44"
    assert "Canadian PRR" in failure["context"]


def test_a_link_the_agent_never_received_is_a_failure():
    """A footnote link typed from memory points at something the agent never received."""
    draft = ("PRR 54.77 [1]; weekly dosing [2]; a guideline [3].\n"
             "[1]: https://api.fda.gov/drug/event.json?search=cisplatin+ototoxicity\n"
             "[2]: https://pubmed.ncbi.nlm.nih.gov/31234567/\n"
             "[3]: https://pubmed.ncbi.nlm.nih.gov/99999999/")

    (failure,) = check_report(draft, RECEIVED)

    assert {k: failure[k] for k in ("kind", "text", "context")} == {
        "kind": "unvouched_link",
        "text": "https://pubmed.ncbi.nlm.nih.gov/99999999/",
        "context": "[3]: https://pubmed.ncbi.nlm.nih.gov/99999999/"}
    # The refusal says why, so a re-ask can act on it: the run saw PubMed, not this page.
    assert "site but not this page" in failure["why"]


def test_a_link_built_from_an_identifier_the_agent_received_passes():
    """The process tells the agent to cite a trial as clinicaltrials.gov/study/<nct_id>."""
    received = {"fetched": [{"nct_id": "NCT00716976", "title": "Sodium thiosulfate"}],
                "facts": {"setid": "508496cb-3441-46b3-a4fe-e0d440e6adc6"}}
    draft = ("[^18^]: https://clinicaltrials.gov/study/NCT00716976\n"
             "[^2^]: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid="
             "508496cb-3441-46b3-a4fe-e0d440e6adc6\n"
             "[^19^]: https://clinicaltrials.gov/study/NCT09999999")

    (failure,) = check_report(draft, received)

    assert failure["text"] == "https://clinicaltrials.gov/study/NCT09999999"


def test_a_figure_of_a_million_or_more_is_checked():
    received = {"handover": {"facts": {"reports": 2078456}}}

    good = check_report("The database holds 2,078,456 reports.", received)
    bad = check_report("The database holds 9,000,000 reports.", received)

    assert [f for f in good if f["kind"] == "unvouched_number"] == []
    assert [f["text"] for f in bad if f["kind"] == "unvouched_number"] == ["9000000"]


def test_a_run_identifier_does_not_vouch_a_number():
    """This pins that run_id is excluded, not a substring match: _NUMBER_RECEIVED is unbounded
    and already matches the whole run id as one token, never a shorter prefix of it -- so this
    case alone would pass even serialising the whole received object, un-stripped."""
    received = {"run_id": "run-4815162342", "handover": {"facts": {"drug_name": "cisplatin"}}}

    failures = check_report("There were 4815 cases.", received)

    assert [f["text"] for f in failures if f["kind"] == "unvouched_number"] == ["4815"]


def test_a_tool_call_argument_in_the_run_record_does_not_vouch_a_number():
    """handover["record"]["skeleton"] carries every tool call's arguments -- numbers the run
    sent out, never data it got back. Serialising the whole hand-over would vouch them."""
    received = {"handover": {"facts": {"drug_name": "cisplatin"}, "record": {
        "status": "written", "iri": "https://data.example/runs/skill-1",
        "skeleton": {"steps": [{"id": "faers_counts", "calls": [
            {"tool": "FAERS_count_reactions_by_drug_event",
             "arguments": {"limit": 5000}}]}]}}}}

    failures = check_report("The query used a limit of 5000 results.", received)

    assert [f["text"] for f in failures if f["kind"] == "unvouched_number"] == ["5000"]


def test_a_link_inside_the_run_record_does_not_vouch_a_citation():
    """record["iri"] is a URL too -- the run's own bookkeeping vouches no link, same as no
    number. Citing that address back is not citing a source."""
    received = {"handover": {"facts": {"drug_name": "cisplatin"}, "record": {
        "status": "written", "iri": "https://data.example/runs/skill-1",
        "skeleton": {"steps": []}}}}

    failures = check_report("See [the run](https://data.example/runs/skill-1).", received)

    assert [f["kind"] for f in failures if f["kind"] == "unvouched_link"] == ["unvouched_link"]


# --- only what a source gave back vouches: an allow-list, never a deny-list ------------
#
# The run's own prose about itself -- what failed, what it could not decide, the arguments
# it sent -- is not an answer. A deny-list was extended twice and still let six keys
# through; a key added after this line is written must vouch nothing until it is named.


def test_a_failed_calls_own_arguments_do_not_vouch_a_number():
    """`failures` carries the arguments the run sent out, and it sent them precisely
    because nothing came back."""
    received = {"handover": {"facts": {"drug_name": "cisplatin"}, "failures": [
        {"tool": "FAERS_count_reactions_by_drug_event",
         "arguments": {"limit": 5000}, "error": "HTTPError: 503"}]}}

    failures = check_report("The analysis covered 5000 reports.", received)

    assert [f["text"] for f in failures if f["kind"] == "unvouched_number"] == ["5000"]


def test_a_cell_the_engine_marked_unreadable_does_not_vouch_the_number_in_it():
    """The engine says it could not read this text; the checker must not then use it to
    certify the number as read."""
    received = {"handover": {"facts": {"prr_table": [
        {"term": "NEPHROTOXICITY", "flagged": None, "unparseable": "3.1 (0.8-9.4)"}]}}}

    failures = check_report("Nephrotoxicity showed a PRR of 3.1.", received)

    assert "3.1" in {f["text"] for f in failures if f["kind"] == "unvouched_number"}


def test_a_blocked_reason_does_not_vouch_the_count_inside_it():
    received = {"handover": {"facts": {"drug_name": "cisplatin"}, "blocked": [
        {"step": "lookup",
         "reason": "name='Rett\\'s' could not be resolved after 2 suggested alternatives"}]}}

    failures = check_report("2 comparator drugs were screened.", received)

    assert [f["text"] for f in failures if f["kind"] == "unvouched_number"] == ["2"]


def test_a_hand_over_key_nobody_has_named_yet_vouches_nothing():
    """The allow-list's whole point: next year's key defaults to vouching nothing."""
    received = {"handover": {"facts": {"drug_name": "cisplatin"},
                             "a_key_invented_later": {"count": 77}}}

    failures = check_report("There were 77 of them.", received)

    assert [f["text"] for f in failures if f["kind"] == "unvouched_number"] == ["77"]


@pytest.mark.parametrize("link,expected", [
    ("https://", ""),                        # _bare strips the scheme down to nothing
    ("clinicaltrials.gov", ""),               # a bare domain, no scheme
    ("example.com/path", ""),                 # a schemeless path
    ("//example.com/path", "example.com"),    # protocol-relative: a real domain, no crash
    ("10.1038/nature12373", ""),              # a DOI
])
def test_domain_of_handles_every_link_shape_without_raising(link, expected):
    assert _domain_of(link) == expected


def test_a_link_whose_domain_the_run_never_saw_is_refused():
    received = {"handover": {"facts": {"rows": [
        {"id": "NCT04875806", "url": "https://clinicaltrials.gov/study/NCT04875806"}]}}}

    failures = check_report(
        "See [the trial](https://example.invalid/study/NCT04875806).", received)

    assert [f["kind"] for f in failures if f["kind"] == "unvouched_link"] == ["unvouched_link"]


@pytest.mark.parametrize("received", [
    {},
    # The shape `submit_report` really sends: the keys are always there, empty or not,
    # so their presence is not the record -- only what is inside them is.
    {"handover": {}, "fetched": {}},
    {"handover": {"skill": "adverse-event-detection", "facts": {}, "unresolved": ["top_aes"],
                  "write_the_report": ["Take every number from its row."]},
     "fetched": {}},
])
def test_a_missing_working_record_is_reported_as_a_missing_record(received):
    failures = check_report("Cisplatin had 1234 reports and a PRR of 5.6.", received)

    assert [f["kind"] for f in failures] == ["no_working_record"]


# --- narrowing must be stated ------------------------------------------------------

NARROWED = {"handover": {"facts": {}, "tables": [
    {"table": "results.literature", "rows": 200, "source_total": {"ototoxicity": 2078}},
    {"table": "results.trials", "rows": 866, "source_total": 866},
    {"table": "results.label", "rows": 36, "source_total": "unknown"}]}}


def test_a_table_the_run_holds_less_of_than_the_source_must_be_stated_with_its_total():
    """A report that says how much it read must say what it read out of."""
    silent = "Literature on ototoxicity: the most relevant abstracts were read."
    stated = "Literature on ototoxicity: PubMed holds 2,078 papers; this run holds 200 of them."

    (failure,) = check_report(silent, NARROWED)

    assert failure["kind"] == "narrowing_not_stated"
    assert failure["text"] == ("results.literature, ototoxicity: the source holds 2078; "
                               "say how many this run holds")
    assert check_report(stated, NARROWED) == []


def test_a_per_item_total_is_required_only_for_the_items_the_report_discusses():
    received = {"handover": {"facts": {}, "tables": [
        {"table": "results.literature", "rows": 1935,
         "source_total": {"ototoxicity": 2078, "ANAEMIA": 2464, "NEUTROPENIA": 5827}}]}}
    draft = ("Ototoxicity: PubMed holds 2,078 papers; this run holds 1,935 rows. "
             "Anaemia was not examined.")

    (failure,) = check_report(draft, received)

    assert failure["text"].startswith("results.literature, ANAEMIA:")
    assert "handover.tables" in failure["context"]


# --- real reports: one of the production shape, and a web report ------------------------

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _received_from(trace: dict) -> dict:
    """What the agent had in front of it, read off its trace: the hand-over, its own answers
    to the run, and every row a fetch returned."""
    received = {"handover": {}, "fetched": [], "answers": []}
    for action in trace["actions"]:
        content = action.get("content")
        content = content if isinstance(content, str) else json.dumps(content)
        try:
            body = json.loads(content)
            out = body.get("output")
            out = json.loads(out) if isinstance(out, str) else out
        except (TypeError, ValueError):
            continue
        answer = (body.get("parameters") or {}).get("answer")
        if answer:
            received["answers"].append(answer)
        if isinstance(out, dict) and out.get("status") == "finished":
            received["handover"] = out.get("handover") or {}
        elif isinstance(out, dict) and action.get("tool_name") == "fetch_run_data":
            received["fetched"].extend(out.get("rows") or [])
    return received


def _failures_for(fixture: str) -> list:
    trace = json.loads((FIXTURES / fixture).read_text())
    return check_report(trace["answer"], _received_from(trace))


def test_a_live_report_of_the_production_shape_is_flagged_only_for_what_is_real():
    failures = _failures_for("live_run_cisplatin_2026-09-21.json")

    kinds = {f["kind"] for f in failures}
    assert "unvouched_number" not in kinds, [f for f in failures
                                             if f["kind"] == "unvouched_number"]
    # the run held a slice of each reaction's papers and the report never said so
    assert "narrowing_not_stated" in kinds
    assert all("ontains" not in f["text"] for f in failures)


def test_the_web_report_with_the_sourceless_prr_fails_on_that_number():
    """A number with no source in what the agent received is refused in a real report too.

    The web arm ran no skill, so its own trace holds nothing to check against; that draft
    is read here against the production run's record, which is what refusing a sourceless
    number means.
    """
    web = json.loads((FIXTURES / "web_report_cisplatin_2026-09-19.json").read_text())
    live = json.loads((FIXTURES / "live_run_cisplatin_2026-09-21.json").read_text())

    failures = check_report(web["answer"], _received_from(live))

    assert "53.44" in {f["text"] for f in failures if f["kind"] == "unvouched_number"}


def test_a_report_written_with_no_run_at_all_gets_one_true_statement_not_a_page_of_them():
    """The web arm's trace holds no hand-over and no fetched row. One true sentence about
    the missing record beats a failure for every number in the draft."""
    failures = _failures_for("web_report_cisplatin_2026-09-19.json")

    assert [f["kind"] for f in failures] == ["no_working_record"]


# --- a judged mapping is shown -------------------------------------------------------

MAPPED = {"handover": {"facts": {
    "requested_meddra": [
        {"of": "ototoxicity", "term": "DEAFNESS", "reason": "the ototoxic injury",
         "placing": "placed"},
        {"of": "ototoxicity", "term": "FALL", "reason": "may follow from dizziness",
         "placing": "not placed"}]},
    "mappings": ["requested_meddra"], "tables": []}}


def test_a_judged_mapping_the_report_does_not_show_is_a_failure_naming_the_hidden_terms():
    """The reader judges the mapping; a term mapped and not shown cannot be judged."""
    hidden = "Ototoxicity shows a strong signal (PRR 54.77), read as DEAFNESS in FAERS."
    shown = ("Ototoxicity, read as: DEAFNESS (placed: the ototoxic injury); FALL (not placed: "
             "may follow from dizziness).")

    (failure,) = [f for f in check_report(hidden, MAPPED) if f["kind"] == "mapping_not_shown"]

    assert failure["text"] == "requested_meddra: FALL"
    assert [f for f in check_report(shown, MAPPED) if f["kind"] == "mapping_not_shown"] == []


# --- the same page, spelled differently, is the same page -------------------------------
#
# A report-check error is not symmetric in its cost. A missed fabrication is invisible until
# somebody opens the source. A false accusation is visible on every run, the agent is told to
# rewrite in response to it, and on the live run measured for DSR-808 the agent answered a
# refused citation by deleting it -- so the report the reader got was worse sourced than the
# draft. A check that refuses correct citations spends the trust that makes it worth having.

HELD_BARE = {"handover": {"facts": {}, "tables": [], "fetched": [
    {"url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=508496cb"}]}}

HELD_TRACKED = {"handover": {"facts": {}, "tables": [], "fetched": [
    {"url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm"
            "?setid=508496cb&utm_source=openai"}]}}


def _links_refused(draft, received):
    return {f["text"] for f in check_report(draft, received) if f["kind"] == "unvouched_link"}


def test_a_citation_that_only_adds_www_to_the_held_link_is_vouched():
    """`www.host` and `host` are one page; refusing the citation says they are two."""
    draft = ("The label is at "
             "https://www.dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=508496cb")

    assert _links_refused(draft, HELD_BARE) == set()


def test_a_citation_that_only_adds_a_tracking_parameter_is_vouched():
    draft = ("The label is at https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm"
             "?setid=508496cb&utm_source=openai")

    assert _links_refused(draft, HELD_BARE) == set()


def test_a_held_link_carrying_a_tracking_parameter_vouches_the_clean_citation():
    """The parameter can arrive on either side; a search engine adds it to what it returns."""
    draft = "The label is at https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=508496cb"

    assert _links_refused(draft, HELD_TRACKED) == set()


def test_a_different_page_on_a_held_host_is_still_refused():
    """Folding the spelling must not fold the page: the setid is the page."""
    draft = ("The label is at "
             "https://www.dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=deadbeef")

    assert _links_refused(draft, HELD_BARE) != set()


def test_a_tracking_parameter_in_front_of_the_real_one_still_folds():
    """Stripping the first parameter takes the `?` with it; both sides must land the same."""
    draft = ("The label is at https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm"
             "?utm_source=openai&setid=508496cb")

    assert _links_refused(draft, HELD_BARE) == set()


def test_a_query_parameter_that_is_not_tracking_still_identifies_the_page():
    """Only analytics parameters are noise. Dropping a real one would fold two pages into one."""
    draft = ("The label is at https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm"
             "?setid=508496cb&page=2")

    assert _links_refused(draft, HELD_BARE) != set()


def test_a_heading_s_own_numbering_is_not_collected_as_a_stated_figure():
    """A guard, not a pin: `_NUMBERING` already strips these, and the live report of
    2026-09-21 carries headings 1 to 7 with no `unvouched_number` against any of them.
    The test exists so a change to the numeric scan cannot quietly undo that."""
    draft = ("## 1. Drug overview\nNothing numeric here.\n"
             "## 2. Labeled safety\nNor here.\n"
             "3) Post-market signals\nNor here.\n")

    numbers = {f["text"] for f in check_report(draft, HELD_BARE)
               if f["kind"] == "unvouched_number"}

    assert numbers == set(), numbers
