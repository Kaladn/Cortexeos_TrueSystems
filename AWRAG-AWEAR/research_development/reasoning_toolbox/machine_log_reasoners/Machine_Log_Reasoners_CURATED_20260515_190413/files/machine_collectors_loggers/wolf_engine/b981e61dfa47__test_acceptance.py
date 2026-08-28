"""
Wolf Engine - Acceptance Tests (All 6 from the canonical spec)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from wolf_engine.contracts import RawAnchor
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.gnome.gnome_service import GnomeFailure, GnomeService
from wolf_engine.pipeline import ingest_anchor
from wolf_engine.tests.conftest import create_test_anchor


# --------------------------------------------------------------------------- #
# Test 1: Raw Event Written
# --------------------------------------------------------------------------- #
class TestRawEventWritten:
    def test_raw_event_persists_after_ingest(
        self, gnome, sql_writer, sql_reader, forge, session_id
    ):
        raw_anchor = create_test_anchor("test", session_id=session_id)
        ingest_anchor(raw_anchor, gnome, sql_writer, forge)

        raw_events = sql_reader.get_raw_events(session_id)
        event_ids = [e.event_id for e in raw_events]
        assert raw_anchor.event_id in event_ids


# --------------------------------------------------------------------------- #
# Test 2: Symbol Event Written
# --------------------------------------------------------------------------- #
class TestSymbolEventWritten:
    def test_symbol_event_persists_with_valid_symbol_id(
        self, gnome, sql_writer, sql_reader, forge, session_id
    ):
        raw_anchor = create_test_anchor("architecture", session_id=session_id)
        ingest_anchor(raw_anchor, gnome, sql_writer, forge)

        symbol_events = sql_reader.get_symbol_events(session_id)
        event_ids = [e.event_id for e in symbol_events]
        assert raw_anchor.event_id in event_ids

        symbol_event = symbol_events[0]
        assert isinstance(symbol_event.symbol_id, int)
        assert symbol_event.symbol_id > 0


# --------------------------------------------------------------------------- #
# Test 3: Forge Ingestion
# --------------------------------------------------------------------------- #
class TestForgeIngestion:
    def test_forge_contains_symbol_after_ingest(
        self, gnome, sql_writer, forge, session_id
    ):
        raw_anchor = create_test_anchor("data", session_id=session_id)
        ingest_anchor(raw_anchor, gnome, sql_writer, forge)

        # Get the symbol_id that GNOME would produce
        symbol_event = gnome.process_anchor(raw_anchor)
        result = forge.query(symbol_event.symbol_id)

        assert result is not None
        assert result.resonance >= 1.0


# --------------------------------------------------------------------------- #
# Test 4: GNOME Failure Handling
# --------------------------------------------------------------------------- #
class TestGnomeFailureHandling:
    def test_raw_written_but_symbol_and_forge_skipped_on_gnome_failure(
        self, sql_writer, sql_reader, forge, session_id
    ):
        raw_anchor = create_test_anchor("test", session_id=session_id)

        # Create a mock GnomeService that always raises
        gnome_mock = MagicMock(spec=GnomeService)
        gnome_mock.process_anchor.side_effect = GnomeFailure("Test failure")

        ingest_anchor(raw_anchor, gnome_mock, sql_writer, forge)

        # Raw event MUST be written
        raw_events = sql_reader.get_raw_events(session_id)
        event_ids = [e.event_id for e in raw_events]
        assert raw_anchor.event_id in event_ids

        # Symbol event MUST NOT be written
        symbol_events = sql_reader.get_symbol_events(session_id)
        assert len(symbol_events) == 0

        # Forge MUST NOT have ingested
        assert forge.stats().total_symbols == 0


# --------------------------------------------------------------------------- #
# Test 5: Restart Persistence
# --------------------------------------------------------------------------- #
class TestRestartPersistence:
    def test_sql_survives_forge_restart(
        self, gnome, sql_writer, sql_reader, forge, session_id
    ):
        # Ingest 10 events
        for i in range(10):
            raw_anchor = create_test_anchor(
                f"token_{i}", session_id=session_id, pulse_id=i
            )
            ingest_anchor(raw_anchor, gnome, sql_writer, forge)

        # Verify Forge has symbols
        assert forge.stats().total_symbols > 0

        # Simulate restart — new Forge (RAM wiped)
        forge = ForgeMemory()
        assert forge.stats().total_symbols == 0

        # SQL still has all events
        symbol_events = sql_reader.get_symbol_events(session_id)
        assert len(symbol_events) == 10

        # Reload Forge from SQL using reload API
        forge.reload_from_events(symbol_events)

        # Forge restored
        assert forge.stats().total_symbols > 0


# --------------------------------------------------------------------------- #
# Test 6: Collision Detection
# --------------------------------------------------------------------------- #
class TestCollisionDetection:
    def test_gnome_detects_symbol_collision(self, gnome, session_id):
        raw_anchor_1 = create_test_anchor("test", session_id=session_id)
        raw_anchor_2 = create_test_anchor("test", session_id=session_id)

        symbol_event_1 = gnome.process_anchor(raw_anchor_1)
        symbol_event_2 = gnome.process_anchor(raw_anchor_2)

        # Same token -> same symbol_id -> no collision
        assert symbol_event_1.symbol_id == symbol_event_2.symbol_id

        # Now force a collision: different token, same symbol_id
        # We'll manually inject a registry entry to simulate this
        gnome._collision_registry[symbol_event_1.symbol_id] = "completely_different_token"

        # Processing the same anchor again should detect a collision
        collision_detected = gnome._detect_collision(symbol_event_1, raw_anchor_1.token)
        assert collision_detected is True
