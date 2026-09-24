"""The Working Record of one Skill Run: every tool result, kept whole, beside the run.

One SQLite file per run. Results go here instead of into the run's state, so their size is
bounded by the disk and not by what a workflow history or a model turn can carry.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


def records_dir() -> Path:
    """Where the server keeps Working Records: beside it, for as long as the container lives."""
    return Path(os.environ.get("SKILL_WORKING_RECORDS")
                or Path(tempfile.gettempdir()) / "skill-working-records")


PREVIEW_ROWS = 2
PREVIEW_CHARS = 160
VALUE_LIST_MAX = 12         # more distinct values than this is free text, not a closed list
VALUE_CHARS_MAX = 40        # a closed-list value is a code or a label, never a paragraph


def _closed_list_value(value: Any) -> bool:
    """A code or a label: something a closed list can hold, never a paragraph or a structure."""
    return (isinstance(value, (int, bool)) or value is None
            or (isinstance(value, str) and len(value) <= VALUE_CHARS_MAX))


def _cut(value: Any) -> Any:
    """A preview cell; a longer one is truncated and ends in an ellipsis."""
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return value if len(text) <= PREVIEW_CHARS else text[:PREVIEW_CHARS] + "…"


def _rows_of(payload: Any) -> list[dict]:
    """The rows inside one tool result: its list of records, else the result as one row."""
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, list) and data and all(isinstance(r, dict) for r in data):
        return data
    if isinstance(data, dict):
        lists = [v for v in data.values()
                 if isinstance(v, list) and v and all(isinstance(r, dict) for r in v)]
        return lists[0] if len(lists) == 1 else [data]
    return [{"value": data}]


RESULTS = "results."

_WORD = re.compile(r"[a-z0-9]+")
K1, B = 1.5, 0.75


def _words(value: Any) -> list[str]:
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    return _WORD.findall(text.lower())


def ranked_rows(rows: list[dict], query: str) -> list[tuple[float, int]]:
    """BM25 of each row's text against the query: (score, row index), best first.

    Only rows that share a word with the query are returned. Ties keep the table's order, so
    the same query always gives the same sequence and an offset continues it.
    """
    documents = [_words(list(row.values())) for row in rows]
    terms = set(_words(query))
    average = (sum(len(d) for d in documents) / len(documents)) or 1.0
    holding = {t: sum(1 for d in documents if t in d) for t in terms}
    scored = []
    for n, words in enumerate(documents):
        score = 0.0
        for term in terms:
            frequency = words.count(term)
            if frequency:
                idf = math.log(1 + (len(documents) - holding[term] + 0.5) / (holding[term] + 0.5))
                score += idf * frequency * (K1 + 1) / (
                    frequency + K1 * (1 - B + B * len(words) / average))
        if score > 0:
            scored.append((score, n))
    return sorted(scored, key=lambda pair: (-pair[0], pair[1]))


class WorkingRecord:
    def __init__(self, directory: str | Path, run_id: str):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self._path = directory / (re.sub(r"[^A-Za-z0-9_.-]", "_", run_id) + ".sqlite")

    @classmethod
    def existing(cls, directory: str | Path, run_id: str) -> "WorkingRecord | None":
        """The record of a run that has one; opening a record must not invent a run."""
        path = Path(directory) / (re.sub(r"[^A-Za-z0-9_.-]", "_", run_id) + ".sqlite")
        return cls(directory, run_id) if path.is_file() else None

    def _open(self) -> sqlite3.Connection:
        db = sqlite3.connect(self._path, timeout=60)
        db.execute("CREATE TABLE IF NOT EXISTS result (step TEXT, attempt INT, call_n INT, "
                   "tool TEXT, arguments TEXT, payload TEXT, "
                   "PRIMARY KEY (step, attempt, call_n))")
        db.execute("CREATE TABLE IF NOT EXISTS row (name TEXT, row_n INT, json TEXT, "
                   "PRIMARY KEY (name, row_n))")
        db.execute("CREATE TABLE IF NOT EXISTS served (n INTEGER PRIMARY KEY, name TEXT, json TEXT)")
        return db

    def put_result(self, step: str, call_n: int, tool: str, arguments: dict,
                   payload: Any, attempt: int = 0) -> None:
        db = self._open()
        try:
            db.execute("INSERT OR REPLACE INTO result VALUES (?,?,?,?,?,?)",
                       (step, attempt, call_n, tool, json.dumps(arguments or {}, default=str),
                        json.dumps(payload, default=str, ensure_ascii=False)))
            db.commit()
        finally:
            db.close()

    def results(self, step: str) -> list:
        """The step's results, whole and in call order; a repaired step gives its last attempt."""
        db = self._open()
        try:
            rows = db.execute(
                "SELECT payload FROM result WHERE step = ?1 AND attempt = "
                "(SELECT MAX(attempt) FROM result WHERE step = ?1) ORDER BY call_n",
                (step,)).fetchall()
        finally:
            db.close()
        return [json.loads(payload) for (payload,) in rows]

    def put_table(self, name: str, rows: list) -> None:
        rows = [r if isinstance(r, dict) else {"value": r} for r in rows]
        db = self._open()
        try:
            db.execute("DELETE FROM row WHERE name = ?", (name,))
            db.executemany("INSERT INTO row VALUES (?,?,?)",
                           [(name, n, json.dumps(r, default=str, ensure_ascii=False))
                            for n, r in enumerate(rows)])
            db.commit()
        finally:
            db.close()

    def _rows(self, name: str) -> list[dict]:
        if name.startswith(RESULTS):
            return [row for payload in self.results(name[len(RESULTS):])
                    for row in _rows_of(payload)]
        db = self._open()
        try:
            found = db.execute("SELECT json FROM row WHERE name = ? ORDER BY row_n",
                               (name,)).fetchall()
        finally:
            db.close()
        return [json.loads(text) for (text,) in found]

    def rows(self, name: str) -> list[dict]:
        """A table's rows, whole -- for a server check, never for the question."""
        return self._rows(name)

    def describe(self, name: str) -> dict:
        """What a table holds, without its rows: the agent reads this before it fetches.

        A column with few distinct values is a closed list (a phase, a status): its values
        and their counts are listed, for reading -- the selection is the code tool's.
        `rows` is the table's total, so the capped preview is never read as the table.
        """
        rows = self._rows(name)
        columns = list(dict.fromkeys(column for row in rows for column in row))
        values: dict[str, dict] = {}
        for column in columns:
            counts: dict = {}
            for row in rows:
                value = row.get(column)
                # A list-valued cell (a trial's phases) is a closed list too: each element counts.
                members = value if isinstance(value, list) else [value]
                if all(_closed_list_value(m) for m in members):
                    for member in members:
                        counts[member] = counts.get(member, 0) + 1
                else:
                    counts = {}          # free text or a structure: not a closed list
                    break
                if len(counts) > VALUE_LIST_MAX:
                    counts = {}
                    break
            if counts and (len(counts) < len(rows) or any(isinstance(r.get(column), list) for r in rows)):
                values[column] = {str(k): n for k, n in counts.items()}
        return {"table": name, "rows": len(rows), "columns": columns, "values": values,
                "preview": [{k: _cut(v) for k, v in row.items()}
                            for row in rows[:PREVIEW_ROWS]]}

    def tables(self) -> list[str]:
        db = self._open()
        try:
            kept = [name for (name,) in
                    db.execute("SELECT DISTINCT name FROM row ORDER BY name").fetchall()]
            steps = [RESULTS + step for (step,) in
                     db.execute("SELECT DISTINCT step FROM result ORDER BY step").fetchall()]
        finally:
            db.close()
        return kept + steps

    def fetch(self, table: str, columns: list[str] | None = None,
              limit: int | None = None, offset: int = 0, rank_by: str | None = None) -> dict:
        """Rows of one table. A wrong name is answered with the right ones, never with nothing.

        `rank_by` is plain words: the rows that share a word with it come back best first,
        each with its `_score`. Text in, ranked rows out; it is not a query language.
        """
        rows = self._rows(table)
        if not rows:
            return {"status": "unknown_table", "table": table, "tables": self.tables()}
        known = list(dict.fromkeys(column for row in rows for column in row))
        unknown = [c for c in (columns or []) if c not in known]
        if unknown:
            return {"status": "unknown_columns", "table": table, "unknown": unknown,
                    "columns": known}
        if rank_by and limit is None:
            return {"status": "limit_required", "table": table, "total_rows": len(rows),
                    "hint": "give `limit` with `rank_by`: say how many of the best rows you "
                            "will read; ask for the next ones with `offset` if they are not enough"}
        out = {"status": "ok", "table": table, "total_rows": len(rows), "offset": offset}
        scores: dict[int, float] = {}
        if rank_by:
            # One record can arrive under several calls (one paper, many reaction searches):
            # rows equal in the columns asked for are one record, and its best copy is kept.
            ranked, seen = [], set()
            for score, n in ranked_rows(rows, rank_by):
                same = json.dumps({c: rows[n].get(c) for c in (columns or known)},
                                  sort_keys=True, default=str)
                if same not in seen:
                    seen.add(same)
                    ranked.append((score, n))
            scores = {id(rows[n]): score for score, n in ranked}
            rows = [rows[n] for _, n in ranked]
            out["matched"] = len(rows)
        chosen = rows[offset:] if limit is None else rows[offset:offset + limit]
        projected = [{c: row.get(c) for c in columns} if columns else dict(row) for row in chosen]
        if rank_by:
            for row, source in zip(projected, chosen):
                row["_score"] = round(scores[id(source)], 4)
        reply = {**out, "returned": len(projected), "rows": projected}
        self._note_served(table, projected)
        # The counts the reply carries are told to the agent too; a report may state them.
        self._note_served(f"{table}.reply", [{k: reply[k] for k in ("total_rows", "matched",
                                                                    "returned", "offset")
                                              if k in reply}])
        return reply

    def _note_served(self, table: str, rows: list[dict]) -> None:
        """What the agent was given, as it was given: the report is read against this."""
        db = self._open()
        try:
            db.executemany("INSERT INTO served (name, json) VALUES (?, ?)",
                           [(table, json.dumps(row, default=str, ensure_ascii=False))
                            for row in rows])
            db.commit()
        finally:
            db.close()

    def count(self, event: str) -> int:
        """How often something happened to this run -- a report submitted, for one."""
        db = self._open()
        try:
            db.execute("INSERT INTO served (name, json) VALUES (?, ?)", (f"@{event}", "{}"))
            db.commit()
            return db.execute("SELECT COUNT(*) FROM served WHERE name = ?",
                              (f"@{event}",)).fetchone()[0]
        finally:
            db.close()

    def served(self) -> dict[str, list[dict]]:
        """Every row the agent fetched, by table, in the order it was served."""
        db = self._open()
        try:
            found = db.execute("SELECT name, json FROM served ORDER BY n").fetchall()
        finally:
            db.close()
        out: dict[str, list[dict]] = {}
        for name, text in found:
            if not name.startswith("@"):
                out.setdefault(name, []).append(json.loads(text))
        return out
