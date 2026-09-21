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
    """Seen in a web report: "a Canadian PRR of about 53.44", cited to a paper that does not give it."""
    draft = "Ototoxicity shows PRR 54.77, against a Canadian PRR of about 53.44 in the same period."

    (failure,) = check_report(draft, RECEIVED)

    assert failure["kind"] == "unvouched_number" and failure["text"] == "53.44"
    assert "Canadian PRR" in failure["context"]


def test_a_link_the_agent_never_received_is_a_failure():
    """In the pointer runs the footnotes "pointed at the wrong thing": a link typed from memory."""
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


# --- from the live reports of 2026-09-21: what a strict rule wrongly refused ---------

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
    """Flagged in a live report: "## 7. Integrated Assessment" and a size chip the chat adds."""
    draft = ("## 7. Integrated Assessment\n"
             "1) Drug overview\n"
             "2. Labeled safety\n"
             "- code_interpreter_code.py <sub>(2.8 KB)</sub>\n"
             "The PRR is 54.77.")

    assert check_report(draft, RECEIVED) == []
