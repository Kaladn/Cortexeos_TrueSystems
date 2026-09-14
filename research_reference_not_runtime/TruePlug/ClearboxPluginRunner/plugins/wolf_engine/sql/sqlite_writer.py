"""
SQLite Writer
Write raw and symbol events to SQLite database (dual-lane persistence).
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import time
from typing import Optional

from wolf_engine.contracts import RawAnchor, SymbolEvent

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id            TEXT PRIMARY KEY,
    started_at            TEXT NOT NULL,
    ended_at              TEXT,
    symbol_genome_version TEXT NOT NULL,
    config_hash           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_events (
    event_id    TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    pulse_id    INTEGER NOT NULL,
    ts          REAL NOT NULL,
    raw_json    TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_events_session_pulse
    ON raw_events(session_id, pulse_id);

CREATE TABLE IF NOT EXISTS symbol_events (
    event_id        TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    pulse_id        INTEGER NOT NULL,
    ts              REAL NOT NULL,
    symbol_id       INTEGER NOT NULL,
    position        INTEGER NOT NULL,
    context_symbols TEXT NOT NULL,
    category        TEXT NOT NULL,
    priority        INTEGER NOT NULL,
    integrity_hash  TEXT NOT NULL,
    genome_version  TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_symbol_events_session_pulse
    ON symbol_events(session_id, pulse_id);
CREATE INDEX IF NOT EXISTS idx_symbol_events_symbol
    ON symbol_events(symbol_id);
CREATE INDEX IF NOT EXISTS idx_symbol_events_ts
    ON symbol_events(ts);

CREATE TABLE IF NOT EXISTS symbol_collisions (
    collision_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id       INTEGER NOT NULL,
    token           TEXT NOT NULL,
    integrity_hash  TEXT NOT NULL,
    ts              REAL NOT NULL,
    genome_version  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_symbol_collisions_symbol
    ON symbol_collisions(symbol_id);
"""

_DISK_WARN_THRESHOLD_MB = 100


class SQLWriteFailure(Exception):
    """Raised when a SQL write operation fails."""
    pass


def _uint64_to_signed(value: int) -> int:
    """Convert uint64 to signed int64 for SQLite storage."""
    if value >= (1 << 63):
        return value - (1 << 64)
    return value


def _signed_to_uint64(value: int) -> int:
    """Convert signed int64 back to uint64 after SQLite read."""
    if value < 0:
        return value + (1 << 64)
    return value


class SQLiteWriter:
    """Writes raw and symbol events to SQLite with WAL mode."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        self._check_disk_space()

    def write_raw_event(self, raw_anchor: RawAnchor) -> None:
        """Write a raw event to the raw_events table."""
        raw_json = json.dumps({
            "event_id": raw_anchor.event_id,
            "session_id": raw_anchor.session_id,
            "pulse_id": raw_anchor.pulse_id,
            "token": raw_anchor.token,
            "context_before": raw_anchor.context_before,
            "context_after": raw_anchor.context_after,
            "position": raw_anchor.position,
            "timestamp": raw_anchor.timestamp,
        })
        self._execute_with_retry(
            "INSERT INTO raw_events (event_id, session_id, pulse_id, ts, raw_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                raw_anchor.event_id,
                raw_anchor.session_id,
                raw_anchor.pulse_id,
                raw_anchor.timestamp,
                raw_json,
            ),
        )

    def write_symbol_event(self, symbol_event: SymbolEvent) -> None:
        """Write a symbol event to the symbol_events table."""
        context_symbols_json = json.dumps(
            [_uint64_to_signed(s) for s in symbol_event.context_symbols]
        )
        self._execute_with_retry(
            "INSERT INTO symbol_events "
            "(event_id, session_id, pulse_id, ts, symbol_id, position, "
            "context_symbols, category, priority, integrity_hash, genome_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                symbol_event.event_id,
                symbol_event.session_id,
                symbol_event.pulse_id,
                symbol_event.timestamp,
                _uint64_to_signed(symbol_event.symbol_id),
                symbol_event.position,
                context_symbols_json,
                symbol_event.category,
                symbol_event.priority,
                symbol_event.integrity_hash,
                symbol_event.genome_version,
            ),
        )

    def write_symbol_events(self, symbol_events: list[SymbolEvent]) -> None:
        """Batch-write symbol events in a single transaction."""
        rows = []
        for se in symbol_events:
            context_json = json.dumps(
                [_uint64_to_signed(s) for s in se.context_symbols]
            )
            rows.append((
                se.event_id, se.session_id, se.pulse_id, se.timestamp,
                _uint64_to_signed(se.symbol_id), se.position, context_json,
                se.category, se.priority, se.integrity_hash, se.genome_version,
            ))
        sql = (
            "INSERT INTO symbol_events "
            "(event_id, session_id, pulse_id, ts, symbol_id, position, "
            "context_symbols, category, priority, integrity_hash, genome_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        try:
            self._conn.executemany(sql, rows)
            self._conn.commit()
        except sqlite3.Error as exc:
            self._conn.rollback()
            raise SQLWriteFailure(str(exc)) from exc

    def create_session(
        self, session_id: str, genome_version: str, config_hash: str
    ) -> None:
        """Create a new session record."""
        started_at = time.time()
        self._execute_with_retry(
            "INSERT INTO sessions (session_id, started_at, symbol_genome_version, config_hash) "
            "VALUES (?, ?, ?, ?)",
            (session_id, str(started_at), genome_version, config_hash),
        )

    def end_session(self, session_id: str) -> None:
        """Mark a session as ended."""
        ended_at = time.time()
        self._execute_with_retry(
            "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
            (str(ended_at), session_id),
        )

    def write_collision(
        self, symbol_event: SymbolEvent, token: str
    ) -> None:
        """Log a symbol collision for forensic analysis."""
        self._execute_with_retry(
            "INSERT INTO symbol_collisions "
            "(symbol_id, token, integrity_hash, ts, genome_version) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                _uint64_to_signed(symbol_event.symbol_id),
                token,
                symbol_event.integrity_hash,
                symbol_event.timestamp,
                symbol_event.genome_version,
            ),
        )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def _check_disk_space(self) -> None:
        """Log a warning if disk space is below threshold."""
        try:
            usage = shutil.disk_usage(self._db_path)
            free_mb = usage.free / (1024 * 1024)
            if free_mb < _DISK_WARN_THRESHOLD_MB:
                logger.warning(
                    "Low disk space: %.0f MB free (threshold: %d MB)",
                    free_mb, _DISK_WARN_THRESHOLD_MB,
                )
        except OSError:
            pass  # Non-critical — don't block startup

    def _execute_with_retry(
        self, sql: str, params: tuple, max_retries: int = 3
    ) -> None:
        """Execute SQL with exponential backoff on database locked errors."""
        for attempt in range(max_retries):
            try:
                self._conn.execute(sql, params)
                self._conn.commit()
                return
            except sqlite3.OperationalError as exc:
                if "database is locked" in str(exc) and attempt < max_retries - 1:
                    wait = 0.1 * (2 ** attempt)
                    logger.warning("Database locked, retrying in %.1fs", wait)
                    time.sleep(wait)
                else:
                    raise SQLWriteFailure(str(exc)) from exc
            except sqlite3.Error as exc:
                raise SQLWriteFailure(str(exc)) from exc
