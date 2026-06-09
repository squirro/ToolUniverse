"""File-backed, JSON-serialized cache for the registry adapter (DSR-508).

DSR-507 left cache persistence to its consumer via the injectable ``cache``
MutableMapping seam. This drops in so tool facts saturate across the 508 walking
skeleton and the 509 batch. Keys are ``(cluster, tool_ref)`` tuples; on-disk they
are tab-joined strings mapping to ``ToolFact`` dicts. Every mutation write-throughs.
"""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from dataclasses import asdict
from pathlib import Path

from .registry_adapter import ToolFact

_SEP = "\t"


class JsonFileCache(MutableMapping):
    """A ``(cluster, tool_ref)`` → ``ToolFact`` mapping persisted to one JSON file."""

    def __init__(self, path):
        self.path = Path(path)
        self._data: dict[tuple[str, str], ToolFact] = self._load()

    def _load(self) -> dict[tuple[str, str], ToolFact]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text())
        return {tuple(k.split(_SEP)): ToolFact(**v) for k, v in raw.items()}

    def _flush(self) -> None:
        raw = {_SEP.join(k): asdict(v) for k, v in self._data.items()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(raw, indent=2, sort_keys=True))

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self._flush()

    def __delitem__(self, key):
        del self._data[key]
        self._flush()

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)
