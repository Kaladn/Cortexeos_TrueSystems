"""
Wolf Engine - Dual-Write Ingest Pipeline (Critical Path)

Failure Guarantees:
  1. Raw event ALWAYS written (unless SQL completely down)
  2. Symbol event written ONLY if GNOME succeeds
  3. Forge ingests ONLY if both SQL writes succeed
  4. No silent failures (all errors logged explicitly)
"""

from __future__ import annotations

import logging

from wolf_engine.contracts import RawAnchor
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.gnome.gnome_service import GnomeFailure, GnomeService
from wolf_engine.sql.sqlite_writer import SQLWriteFailure, SQLiteWriter

logger = logging.getLogger(__name__)


def ingest_anchor(
    raw_anchor: RawAnchor,
    gnome: GnomeService,
    sql_writer: SQLiteWriter,
    forge: ForgeMemory,
) -> None:
    """
    Dual-write ingest pipeline.

    STEP 1: Write raw event (ALWAYS, even if GNOME fails)
    STEP 2: Symbolize (may fail)
    STEP 3: Write symbol event
    STEP 4: Ingest into Forge (only if both SQL writes succeeded)
    """

    # STEP 1: Write raw event (ALWAYS, even if GNOME fails)
    try:
        sql_writer.write_raw_event(raw_anchor)
    except SQLWriteFailure as exc:
        logger.error("Raw write failed: %s", exc)
        raise

    # STEP 2: Symbolize (may fail)
    try:
        symbol_event = gnome.process_anchor(raw_anchor)
    except GnomeFailure as exc:
        logger.error("GNOME failed: %s", exc)
        # Raw is already written. Symbol path fails, Forge does NOT ingest.
        return

    # STEP 3: Write symbol event
    try:
        sql_writer.write_symbol_event(symbol_event)
    except SQLWriteFailure as exc:
        logger.error("Symbol write failed: %s", exc)
        # Raw is written, symbol failed. Forge does NOT ingest.
        return

    # STEP 4: Ingest into Forge (only if both SQL writes succeeded)
    forge.ingest(symbol_event)
