"""The Working Record of one Skill Run: every tool result, kept whole, beside the run.

One SQLite file per run. Results go here instead of into the run's state, so their size is
bounded by the disk and not by what a workflow history or a model turn can carry.
"""

from __future__ import annotations

import json
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


def _cut(value: Any) -> Any:
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

    def describe(self, name: str) -> dict:
        """What a table holds, without its rows: the agent reads this before it fetches."""
        rows = self._rows(name)
        columns = list(dict.fromkeys(column for row in rows for column in row))
        return {"table": name, "rows": len(rows), "columns": columns,
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
              limit: int | None = None, offset: int = 0) -> dict:
        """Rows of one table. A wrong name is answered with the right ones, never with nothing."""
        rows = self._rows(table)
        if not rows:
            return {"status": "unknown_table", "table": table, "tables": self.tables()}
        known = list(dict.fromkeys(column for row in rows for column in row))
        unknown = [c for c in (columns or []) if c not in known]
        if unknown:
            return {"status": "unknown_columns", "table": table, "unknown": unknown,
                    "columns": known}
        chosen = rows[offset:] if limit is None else rows[offset:offset + limit]
        if columns:
            chosen = [{c: row.get(c) for c in columns} for row in chosen]
        return {"status": "ok", "table": table, "total_rows": len(rows), "offset": offset,
                "returned": len(chosen), "rows": chosen}
