"""The server reads the draft report before the user does.

Pure: the draft and what the agent received go in, failures come out. "Received" is the
hand-over's facts and the rows the agent fetched -- not the whole Working Record: with
megabytes of abstracts on record, almost any small number occurs somewhere in it.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_report_check import check_report  # noqa: E402

pytestmark = pytest.mark.unit

RECEIVED = {
    "facts": {"prr_table": [
        {"term": "ototoxicity", "prr": 54.76612, "flagged": True,
         "url": "https://api.fda.gov/drug/event.json?search=cisplatin+ototoxicity"}]},
    "fetched": [{"pmid": "31234567", "year": 2019,
                 "abstract": "Hearing loss occurred in 57% with weekly dosing against 82%.",
                 "url": "https://pubmed.ncbi.nlm.nih.gov/31234567/"}],
}


def test_a_number_the_agent_received_passes_in_any_rounding_the_value_admits():
    draft = ("Ototoxicity shows PRR 54.77 [1]. Hearing loss occurred in 57% with weekly dosing "
             "against 82% (2019).\n\n[1]: https://api.fda.gov/drug/event.json?search=cisplatin+ototoxicity")

    assert check_report(draft, RECEIVED) == []


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

    assert failure == {"kind": "unvouched_link",
                       "text": "https://pubmed.ncbi.nlm.nih.gov/99999999/",
                       "context": "[3]: https://pubmed.ncbi.nlm.nih.gov/99999999/"}


def test_a_received_link_passes_with_or_without_the_punctuation_prose_puts_after_it():
    draft = "See (https://pubmed.ncbi.nlm.nih.gov/31234567/). And https://pubmed.ncbi.nlm.nih.gov/31234567."

    assert check_report(draft, RECEIVED) == []


# --- what a strict rule wrongly refused ----------------------------------------------

def test_a_link_cited_without_its_api_key_is_the_link_that_was_received():
    """The agent rightly drops `api_key=REDACTED` before it cites a FAERS query."""
    received = {"url": "https://api.fda.gov/drug/event.json?search=reactionmeddrapt%3A%22ototoxicity%22"
                       "&limit=1&api_key=REDACTED"}
    draft = "[^3^]: https://api.fda.gov/drug/event.json?search=reactionmeddrapt%3A%22ototoxicity%22&limit=1"

    assert check_report(draft, received) == []


def test_a_link_built_from_an_identifier_the_agent_received_passes():
    """The process tells the agent to cite a trial as clinicaltrials.gov/study/<nct_id>."""
    received = {"fetched": [{"nct_id": "NCT00716976", "title": "Sodium thiosulfate"}],
                "facts": {"setid": "508496cb-3441-46b3-a4fe-e0d440e6adc6"}}
    draft = ("[^18^]: https://clinicaltrials.gov/study/NCT00716976\n"
             "[^2^]: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=508496cb-3441-46b3-a4fe-e0d440e6adc6\n"
             "[^19^]: https://clinicaltrials.gov/study/NCT09999999")

    (failure,) = check_report(draft, received)

    assert failure["text"] == "https://clinicaltrials.gov/study/NCT09999999"


def test_the_numbering_of_the_report_itself_is_not_a_claim():
    """Heading numbers, list markers and the size chip the chat adds are not claims."""
    draft = ("## 7. Integrated Assessment\n"
             "Primary completion 2026-01-20; published 2026-07.\n"
             "1) Drug overview\n"
             "2. Labeled safety\n"
             "- code_interpreter_code.py <sub>(2.8 KB)</sub>\n"
             "The PRR is 54.77.")

    assert check_report(draft, RECEIVED) == []


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
    assert failure["text"] == "results.literature, ototoxicity: the source holds 2078; say how many this run holds"
    assert check_report(stated, NARROWED) == []


# --- real reports: one of the production shape, and a web report ------------------------

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _received_from(trace: dict) -> dict:
    """What the agent had in front of it, read off its trace: the hand-over, its own answers
    to the run, and every row a fetch returned."""
    import json
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


def test_a_live_report_of_the_production_shape_is_flagged_only_for_what_is_real():
    import json
    trace = json.loads((FIXTURES / "live_run_cisplatin_2026-09-21.json").read_text())

    failures = check_report(trace["answer"], _received_from(trace))

    kinds = {f["kind"] for f in failures}
    assert "unvouched_number" not in kinds, [f for f in failures if f["kind"] == "unvouched_number"]
    # the run held a slice of each reaction's papers and the report never said so
    assert "narrowing_not_stated" in kinds
    assert all("ontains" not in f["text"] for f in failures)


def test_the_web_report_with_the_sourceless_prr_fails_on_that_number():
    """A number with no source in what the agent received is refused in a real report too."""
    import json
    trace = json.loads((FIXTURES / "web_report_cisplatin_2026-09-19.json").read_text())

    failures = check_report(trace["answer"], _received_from(trace))

    assert "53.44" in {f["text"] for f in failures if f["kind"] == "unvouched_number"}


def test_a_per_item_total_is_required_only_for_the_items_the_report_discusses():
    """A total is required only for the items the report actually discusses."""
    received = {"handover": {"facts": {}, "tables": [
        {"table": "results.literature", "rows": 1935,
         "source_total": {"ototoxicity": 2078, "ANAEMIA": 2464, "NEUTROPENIA": 5827}}]}}
    draft = "Ototoxicity: PubMed holds 2,078 papers; this run holds 1,935 rows. Anaemia was not examined."

    (failure,) = check_report(draft, received)

    assert failure["text"].startswith("results.literature, ANAEMIA:")
    assert "handover.tables" in failure["context"]


# --- a judged mapping is shown -------------------------------------------------------

MAPPED = {"handover": {"facts": {
    "requested_meddra": [
        {"of": "ototoxicity", "term": "DEAFNESS", "reason": "the ototoxic injury", "placing": "placed"},
        {"of": "ototoxicity", "term": "FALL", "reason": "may follow from dizziness", "placing": "not placed"}]},
    "mappings": ["requested_meddra"], "tables": []}}


def test_a_judged_mapping_the_report_does_not_show_is_a_failure_naming_the_hidden_terms():
    """The reader judges the mapping; a term mapped and not shown cannot be judged."""
    hidden = "Ototoxicity shows a strong signal (PRR 54.77), read as DEAFNESS in FAERS."
    shown = ("Ototoxicity, read as: DEAFNESS (placed: the ototoxic injury); FALL (not placed: "
             "may follow from dizziness).")

    (failure,) = [f for f in check_report(hidden, MAPPED) if f["kind"] == "mapping_not_shown"]

    assert failure["text"] == "requested_meddra: FALL"
    assert [f for f in check_report(shown, MAPPED) if f["kind"] == "mapping_not_shown"] == []
