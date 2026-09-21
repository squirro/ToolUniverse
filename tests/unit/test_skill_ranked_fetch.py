"""Ranked fetch: the agent reads the most relevant rows of an evidence table, and can get more.

Before it, "the first five papers" were the five newest, and no agent had read an abstract.
Text in, ranked rows out: not a query language.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_working_record import WorkingRecord  # noqa: E402

pytestmark = pytest.mark.unit

PAPERS = [
    {"pmid": "1", "reaction": "ACUTE KIDNEY INJURY", "title": "Adrenocortical carcinoma case report",
     "abstract": "A patient with adrenocortical carcinoma received mitotane."},
    {"pmid": "2", "reaction": "ACUTE KIDNEY INJURY", "title": "Hydration and magnesium in cisplatin nephrotoxicity",
     "abstract": "Magnesium supplementation with hydration lowered acute kidney injury after cisplatin."},
    {"pmid": "3", "reaction": "DEAFNESS", "title": "Weekly versus three-weekly cisplatin and hearing loss",
     "abstract": "Hearing loss occurred in 57% with weekly dosing against 82%."},
    {"pmid": "4", "reaction": "ACUTE KIDNEY INJURY", "title": "Mannitol and kidney injury",
     "abstract": "Mannitol gave no benefit against acute kidney injury in a cohort on cisplatin."},
    {"pmid": "5", "reaction": "DEAFNESS", "title": "A herbal formula in mice",
     "abstract": "A herbal formula was studied in mice."},
]


def _record(tmp_path, rows=PAPERS):
    record = WorkingRecord(tmp_path, "run-1")
    record.put_table("literature_rows", rows)
    return record


def test_a_ranked_fetch_returns_the_most_relevant_rows_first_with_their_scores(tmp_path):
    out = _record(tmp_path).fetch("literature_rows", columns=["pmid"], limit=2,
                                  rank_by="cisplatin acute kidney injury magnesium hydration")

    assert out["status"] == "ok"
    assert [row["pmid"] for row in out["rows"]] == ["2", "4"]
    assert out["rows"][0]["_score"] > out["rows"][1]["_score"] > 0
    assert out["matched"] == 4, "only paper 5 shares no word; paper 1 matches through its reaction"
    assert out["total_rows"] == 5


def test_the_same_query_with_an_offset_continues_the_ranking_without_repeating_a_row(tmp_path):
    """The first rows were not enough: the agent asks for the next ones."""
    record = _record(tmp_path)
    query = "cisplatin acute kidney injury"

    first = record.fetch("literature_rows", columns=["pmid"], limit=2, rank_by=query)
    again = record.fetch("literature_rows", columns=["pmid"], limit=2, rank_by=query)
    more = record.fetch("literature_rows", columns=["pmid"], limit=2, offset=2, rank_by=query)

    assert [r["pmid"] for r in first["rows"]] == [r["pmid"] for r in again["rows"]]
    seen = [r["pmid"] for r in first["rows"] + more["rows"]]
    assert len(seen) == len(set(seen)) == 4
    assert more["offset"] == 2 and more["matched"] == first["matched"]


def test_ranking_without_a_limit_is_refused_and_says_why(tmp_path):
    out = _record(tmp_path).fetch("literature_rows", rank_by="cisplatin kidney")

    assert out["status"] == "limit_required"
    assert "limit" in out["hint"]


def test_one_paper_found_under_two_reactions_is_read_once(tmp_path):
    """Equal in the columns asked for means the same record; its best-scoring copy is kept."""
    twice = PAPERS + [{**PAPERS[1], "reaction": "RENAL FAILURE"}]
    record = _record(tmp_path, twice)
    query = "magnesium hydration kidney injury"

    papers = record.fetch("literature_rows", columns=["pmid", "title"], limit=5, rank_by=query)
    by_reaction = record.fetch("literature_rows", columns=["pmid", "reaction"], limit=5,
                               rank_by=query)

    assert [r["pmid"] for r in papers["rows"]].count("2") == 1
    assert [r["pmid"] for r in by_reaction["rows"]].count("2") == 2
    assert papers["matched"] == by_reaction["matched"] - 1


def test_three_thousand_abstracts_are_ranked_in_the_time_of_a_tool_call(tmp_path):
    import time

    filler = ("cisplatin was given to patients in a cohort and outcomes were recorded over "
              "several cycles of treatment with supportive care ") * 12
    rows = [{"pmid": str(n), "abstract": filler + ("magnesium hydration" if n % 97 == 0 else "")}
            for n in range(3000)]
    record = _record(tmp_path, rows)

    started = time.perf_counter()
    out = record.fetch("literature_rows", columns=["pmid"], limit=5, rank_by="magnesium hydration")
    elapsed = time.perf_counter() - started

    assert out["matched"] == 31 and int(out["rows"][0]["pmid"]) % 97 == 0
    assert elapsed < 3.0, f"ranking took {elapsed:.2f} s"
