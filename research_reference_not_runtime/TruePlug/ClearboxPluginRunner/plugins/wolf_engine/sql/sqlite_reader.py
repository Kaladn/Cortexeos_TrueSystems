"""
SQLite Reader
Read raw and symbol events from SQLite database.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Optional

from wolf_engine.contracts import RawAnchor, SessionData, SymbolEvent
from wolf_engine.sql.sqlite_writer import _signed_to_uint64


class SQLiteReader:
    """Read-only access to the Wolf Engine SQLite database."""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def get_symbol_events(
        self,
        session_id: str,
        pulse_range: Optional[tuple[int, int]] = None,
    ) -> list[SymbolEvent]:
        """Retrieve symbol events for a session, optionally filtered by pulse range."""
        if pulse_range is not None:
            cursor = self._conn.execute(
                "SELECT * FROM symbol_events "
                "WHERE session_id = ? AND pulse_id BETWEEN ? AND ? "
                "ORDER BY pulse_id, position",
                (session_id, pulse_range[0], pulse_range[1]),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM symbol_events "
                "WHERE session_id = ? "
                "ORDER BY pulse_id, position",
                (session_id,),
            )

        results = []
        for row in cursor:
            raw_context = json.loads(row["context_symbols"])
            symbol_event = SymbolEvent(
                event_id=row["event_id"],
                session_id=row["session_id"],
                pulse_id=row["pulse_id"],
                symbol_id=_signed_to_uint64(row["symbol_id"]),
                context_symbols=[_signed_to_uint64(s) for s in raw_context],
                category=row["category"],
                priority=row["priority"],
                integrity_hash=row["integrity_hash"],
                genome_version=row["genome_version"],
                position=row["position"],
                timestamp=row["ts"],
            )
            results.append(symbol_event)
        return results

    def get_raw_events(
        self,
        session_id: str,
        pulse_range: Optional[tuple[int, int]] = None,
    ) -> list[RawAnchor]:
        """Retrieve raw events for a session."""
        if pulse_range is not None:
            cursor = self._conn.execute(
                "SELECT * FROM raw_events "
                "WHERE session_id = ? AND pulse_id BETWEEN ? AND ? "
                "ORDER BY pulse_id",
                (session_id, pulse_range[0], pulse_range[1]),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM raw_events "
                "WHERE session_id = ? ORDER BY pulse_id",
                (session_id,),
            )

        results = []
        for row in cursor:
            raw_data = json.loads(row["raw_json"])
            raw_anchor = RawAnchor(
                event_id=raw_data["event_id"],
                session_id=raw_data["session_id"],
                pulse_id=raw_data["pulse_id"],
                token=raw_data["token"],
                context_before=raw_data.get("context_before", []),
                context_after=raw_data.get("context_after", []),
                position=raw_data.get("position", 0),
                timestamp=raw_data.get("timestamp", 0.0),
            )
            results.append(raw_anchor)
        return results

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session metadata."""
        cursor = self._conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return SessionData(
            session_id=row["session_id"],
            started_at=float(row["started_at"]),
            ended_at=float(row["ended_at"]) if row["ended_at"] else None,
            symbol_genome_version=row["symbol_genome_version"],
            config_hash=row["config_hash"],
        )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
