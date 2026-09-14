"""
Verdict Store — SQLite audit trail for all Archon verdicts.

Every verdict produced by the Judge is persisted to an append-only
SQLite table. This provides a full audit trail for post-hoc analysis
of governance decisions.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from pathlib import Path
from typing import Any

from wolf_engine.archon.schemas import Verdict

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS verdicts (
    verdict_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL,
    original_confidence REAL NOT NULL,
    adjusted_confidence REAL NOT NULL,
    flags_json TEXT NOT NULL,
    timestamp REAL NOT NULL
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_verdicts_session ON verdicts(session_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_status ON verdicts(status);
CREATE INDEX IF NOT EXISTS idx_verdicts_timestamp ON verdicts(timestamp);
"""

_INSERT = """
INSERT OR REPLACE INTO verdicts
    (verdict_id, request_id, session_id, status, original_confidence,
     adjusted_confidence, flags_json, timestamp)
VALUES (?, ?, ?, ?, ?, ?, ?, ?);
"""


class VerdictStore:
    """Append-only SQLite store for Archon verdicts."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(_CREATE_TABLE + _CREATE_INDEX)
        self._conn.commit()

    def record(self, verdict: Verdict) -> None:
        """Persist a verdict to the audit trail."""
        flags_json = json.dumps([
            {
                "module": f.module,
                "severity": f.severity.value,
                "code": f.code,
                "message": f.message,
                "adjustment": f.adjustment,
            }
            for f in verdict.flags
        ])
        # Sanitize NaN/Inf — SQLite REAL NOT NULL rejects them
        orig_conf = verdict.original_confidence
        adj_conf = verdict.adjusted_confidence
        if math.isnan(orig_conf) or math.isinf(orig_conf):
            orig_conf = -1.0  # Sentinel for "invalid"
        if math.isnan(adj_conf) or math.isinf(adj_conf):
            adj_conf = -1.0

        self._conn.execute(_INSERT, (
            verdict.verdict_id,
            verdict.request_id,
            verdict.session_id,
            verdict.status.value,
            orig_conf,
            adj_conf,
            flags_json,
            verdict.timestamp,
        ))
        self._conn.commit()

    def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve all verdicts for a session, ordered by timestamp."""
        cursor = self._conn.execute(
            "SELECT * FROM verdicts WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_by_status(self, status: str, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve verdicts by status (approved, adjusted, quarantined, penalized)."""
        cursor = self._conn.execute(
            "SELECT * FROM verdicts WHERE status = ? ORDER BY timestamp DESC LIMIT ?",
            (status, limit),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get the most recent verdicts."""
        cursor = self._conn.execute(
            "SELECT * FROM verdicts ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def count_by_status(self) -> dict[str, int]:
        """Count verdicts grouped by status."""
        cursor = self._conn.execute(
            "SELECT status, COUNT(*) FROM verdicts GROUP BY status"
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_dict(row: tuple) -> dict[str, Any]:
        return {
            "verdict_id": row[0],
            "request_id": row[1],
            "session_id": row[2],
            "status": row[3],
            "original_confidence": row[4],
            "adjusted_confidence": row[5],
            "flags": json.loads(row[6]),
            "timestamp": row[7],
        }
