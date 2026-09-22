"""What a finished Skill Run hands to the agent, and what stays in the Working Record.

Tool results go around the run's state: the Working Record keeps them whole, and the
hand-over carries the facts and the tables the process declares (ADR-0017). The executor is
injected, so these tests need no ToolUniverse and no network.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_runner import SkillRunner
from tooluniverse.skill_working_record import WorkingRecord

pytestmark = pytest.mark.unit

PROCESS = {
    "skill": "demo",
    "inputs": ["drug_name"],
    "steps": [
        {"id": "resolve",
         "calls": [{"tool": "resolve_drug", "arguments": {"name": "{drug_name}"}}],
         "extract": {"chembl_id": "data.id"}},
        {"id": "signals", "requires": ["resolve"],
         "calls": [{"tool": "disproportionality",
                    "arguments": {"chembl_id": "{chembl_id}"}}],
         "collect": {"prr_rows": {"path": "data.rows", "flatten": True,
                                  "fields": ["term", "prr", "url"]}}},
    ],
}

RESPONSES = {
    "resolve_drug": {"data": {"id": "CHEMBL88"}},
    "disproportionality": {"data": {"rows": [
        {"term": "DEAFNESS", "prr": 17.7, "url": "https://example.org/deafness"},
        {"term": "NAUSEA", "prr": 1.2, "url": "https://example.org/nausea"}]}},
}


def _finished_run(tmp_path, process=PROCESS, responses=RESPONSES):
    runner = SkillRunner(process, execute=lambda tool, arguments: responses[tool],
                         records=tmp_path)
    run_id = runner.start({"drug_name": "cisplatin"})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass
    return runner, run_id


def test_a_finished_run_keeps_every_tool_result_in_the_working_record_not_in_the_handover(tmp_path):
    runner, run_id = _finished_run(tmp_path)

    handover = runner.handover(run_id)
    record = WorkingRecord(tmp_path, run_id)

    assert "results" not in handover
    assert handover["facts"]["chembl_id"] == "CHEMBL88"
    assert record.results("resolve") == [RESPONSES["resolve_drug"]]
    assert record.results("signals") == [RESPONSES["disproportionality"]]


ABSTRACT = "Weekly dosing gave hearing loss in 57% of patients against 82% for three-weekly dosing. " * 6

WITH_TABLES = {
    **PROCESS,
    "tables": {"prr_rows": "fact", "papers": "evidence"},
    "steps": PROCESS["steps"] + [
        {"id": "literature", "requires": ["signals"],
         "calls": [{"tool": "search_papers", "arguments": {"query": "{drug_name}"}}],
         "collect": {"papers": {"path": "data.articles", "flatten": True,
                                "fields": ["pmid", "title", "abstract", "url"]}}},
    ],
}

WITH_PAPERS = {
    **RESPONSES,
    "search_papers": {"data": {"articles": [
        {"pmid": str(n), "title": f"Paper {n}", "abstract": ABSTRACT,
         "url": f"https://pubmed.ncbi.nlm.nih.gov/{n}/"} for n in (101, 102, 103)]}},
}


def test_a_fact_table_arrives_whole_and_an_evidence_table_arrives_as_a_description(tmp_path):
    runner, run_id = _finished_run(tmp_path, WITH_TABLES, WITH_PAPERS)

    handover = runner.handover(run_id)

    assert handover["facts"]["prr_rows"] == RESPONSES["disproportionality"]["data"]["rows"]
    assert "papers" not in handover["facts"]
    described = next(t for t in handover["tables"] if t["table"] == "papers")
    assert described["rows"] == 3
    assert described["columns"] == ["pmid", "title", "abstract", "url"]
    assert ABSTRACT not in str(handover)


def test_the_agent_fetches_the_rows_and_columns_it_asks_for(tmp_path):
    _, run_id = _finished_run(tmp_path, WITH_TABLES, WITH_PAPERS)
    record = WorkingRecord(tmp_path, run_id)

    out = record.fetch("papers", columns=["pmid", "url"], limit=2, offset=1)

    assert out["status"] == "ok"
    assert out["total_rows"] == 3
    assert out["rows"] == [
        {"pmid": "102", "url": "https://pubmed.ncbi.nlm.nih.gov/102/"},
        {"pmid": "103", "url": "https://pubmed.ncbi.nlm.nih.gov/103/"}]


def test_a_fetch_that_names_what_does_not_exist_is_told_what_does(tmp_path):
    _, run_id = _finished_run(tmp_path, WITH_TABLES, WITH_PAPERS)
    record = WorkingRecord(tmp_path, run_id)

    no_table = record.fetch("trials")
    no_column = record.fetch("papers", columns=["pmid", "doi"])

    assert no_table["status"] == "unknown_table"
    assert no_table["tables"] == ["papers", "results.literature", "results.resolve",
                                  "results.signals"]
    assert no_column["status"] == "unknown_columns"
    assert no_column["unknown"] == ["doi"]
    assert no_column["columns"] == ["pmid", "title", "abstract", "url"]


def test_what_a_step_fetched_and_did_not_collect_is_still_there_to_fetch(tmp_path):
    """The label text, the trial list: not in front of the agent, and never out of its reach."""
    runner, run_id = _finished_run(tmp_path)
    record = WorkingRecord(tmp_path, run_id)

    described = {t["table"]: t for t in runner.handover(run_id)["tables"]}
    out = record.fetch("results.signals", columns=["term", "prr"])

    assert described["results.signals"]["rows"] == 2
    assert out["rows"] == [{"term": "DEAFNESS", "prr": 17.7}, {"term": "NAUSEA", "prr": 1.2}]


# --- how much the source holds, beside how much the run holds ---------------------

WIDE = {
    "skill": "wide", "inputs": ["drug_name", "reactions"],
    "steps": [
        {"id": "trials", "total": "total_count",
         "calls": [{"tool": "search_trials", "arguments": {"query": "{drug_name}"}}]},
        {"id": "literature", "for_each": "reactions", "as": "reaction", "total": "total",
         "calls": [{"tool": "search_papers", "arguments": {"query": "{reaction}"}}]},
        {"id": "label",
         "calls": [{"tool": "get_label", "arguments": {"drug": "{drug_name}"}}]},
    ],
}


def test_a_table_description_says_how_much_the_source_holds_or_that_it_is_unknown(tmp_path):
    """A few rows read as "this is all there is" until the source's total stands beside them."""
    def execute(tool, arguments):
        if tool == "search_trials":
            return {"total_count": 866, "studies": [{"nct": "NCT1"}, {"nct": "NCT2"}]}
        if tool == "search_papers":
            return {"total": {"DEAFNESS": 4120, "TINNITUS": 77}[arguments["query"]],
                    "data": [{"pmid": "1"}]}
        return {"data": {"setid": "s1"}}

    runner = SkillRunner(WIDE, execute=execute, records=tmp_path)
    run_id = runner.start({"drug_name": "x", "reactions": ["DEAFNESS", "TINNITUS"]})["run_id"]
    while not runner.advance(run_id)["finished"]:
        pass

    described = {t["table"]: t for t in runner.handover(run_id)["tables"]}

    assert (described["results.trials"]["rows"], described["results.trials"]["source_total"]) == (2, 866)
    assert described["results.literature"]["source_total"] == {"DEAFNESS": 4120, "TINNITUS": 77}
    assert described["results.label"]["source_total"] == "unknown"


# --- what the agent received, so the report can be read against it ------------------

def test_the_record_keeps_what_it_served_so_the_report_can_be_checked_against_it(tmp_path):
    """"Cite only what you read" needs the server to know what was read."""
    runner, run_id = _finished_run(tmp_path, WITH_TABLES, WITH_PAPERS)
    record = WorkingRecord(tmp_path, run_id)

    record.fetch("papers", columns=["pmid", "url"], limit=2)
    record.fetch("results.signals", columns=["term", "prr"], limit=1)
    served = record.served()

    assert [row["pmid"] for row in served["papers"]] == ["101", "102"]
    assert served["results.signals"] == [{"term": "DEAFNESS", "prr": 17.7}]
    assert "abstract" not in served["papers"][0], "only the columns the agent asked for were served"


def test_the_handover_carries_the_same_lines_of_discipline_for_every_skill(tmp_path):
    runner, run_id = _finished_run(tmp_path)

    lines = runner.handover(run_id)["write_the_report"]

    assert isinstance(lines, list) and len(lines) == 5
    assert all(isinstance(line, str) and line for line in lines)


def test_the_counts_a_fetch_reply_carries_count_as_received(tmp_path):
    """A count the fetch reply gave the agent must count as received, not as invented."""
    _, run_id = _finished_run(tmp_path, WITH_TABLES, WITH_PAPERS)
    record = WorkingRecord(tmp_path, run_id)

    reply = record.fetch("papers", columns=["pmid"], limit=1, rank_by="hearing loss dosing")
    served = record.served()

    assert reply["matched"] == 3
    assert served["papers.reply"] == [{"total_rows": 3, "matched": 3, "returned": 1, "offset": 0}]
