"""Durable cursor store for sensor readers."""

from __future__ import annotations

import json
import os
from pathlib import Path

from truecore.time import utc_now


class CursorStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def get(self, source_id: str) -> dict:
        return dict(self._data.get(source_id, {}))

    def update(self, source_id: str, cursor: dict) -> None:
        row = dict(cursor)
        row["updated_at_utc"] = utc_now()
        self._data[source_id] = row
        self._write()

    def _write(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)
