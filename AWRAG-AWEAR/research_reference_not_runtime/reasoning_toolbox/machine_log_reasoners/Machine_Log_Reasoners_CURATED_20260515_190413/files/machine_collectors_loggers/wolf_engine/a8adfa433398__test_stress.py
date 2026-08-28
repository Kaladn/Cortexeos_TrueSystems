"""
Wolf Engine - Stress Tests (Phase 0)

Validates:
  1. 100K sequential ingests complete without error
  2. 10 concurrent writer threads cause no corruption
  3. Config env var override works
"""

from __future__ import annotations

import os
import threading
import time
import uuid

import pytest

from wolf_engine.contracts import SymbolEvent
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.gnome.gnome_service import GnomeService
from wolf_engine.pipeline import ingest_anchor
from wolf_engine.sql.sqlite_writer import SQLiteWriter
from wolf_engine.tests.conftest import create_test_anchor


# --------------------------------------------------------------------------- #
# Stress 1: 100K Sequential Forge Ingests
# --------------------------------------------------------------------------- #
class TestSequentialIngest:
    def test_100k_forge_ingests(self):
        """100K symbol events ingested into ForgeMemory without error."""
        forge = ForgeMemory(window_size=50000)
        for i in range(100_000):
            event = SymbolEvent(
                event_id=str(i),
                session_id="stress-session",
                pulse_id=i,
                symbol_id=i % 10000,  # 10K unique symbols
                context_symbols=[(i + 1) % 10000, (i + 2) % 10000],
                category="core",
                priority=1,
                integrity_hash="stress",
                genome_version="v1.0",
                position=0,
                timestamp=float(i),
            )
            forge.ingest(event)

        stats = forge.stats()
        # Window is 50K, so current_size should be capped
        assert stats.current_size == 50000
        # Resonance accumulates across evictions (Forge thinking, not forgetting)
        # 10K unique symbols × 10 occurrences each = avg_resonance ≈ 10.0
        assert stats.avg_resonance >= 10.0
        # co_occurrence survives eviction — verify via resonance dict size
        assert len(forge.resonance) == 10000


# --------------------------------------------------------------------------- #
# Stress 2: 10 Concurrent Writer Threads
# --------------------------------------------------------------------------- #
class TestConcurrentForgeIngests:
    def test_10_threads_no_corruption(self):
        """10 threads × 1000 ingests → no RuntimeError, consistent stats."""
        forge = ForgeMemory(window_size=50000)
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            try:
                for i in range(1000):
                    event = SymbolEvent(
                        event_id=f"{thread_id}-{i}",
                        session_id="concurrent-stress",
                        pulse_id=thread_id * 1000 + i,
                        symbol_id=(thread_id * 1000 + i) % 5000,
                        context_symbols=[i % 5000],
                        category="core",
                        priority=1,
                        integrity_hash="concurrent",
                        genome_version="v1.0",
                        position=0,
                        timestamp=float(i),
                    )
                    forge.ingest(event)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Thread errors: {errors}"
        stats = forge.stats()
        # 10 threads × 1000 ingests = 10000 total events in queue
        assert stats.current_size == 10000
        assert stats.total_symbols > 0


# --------------------------------------------------------------------------- #
# Stress 3: Full Pipeline Stress (SQL + GNOME + Forge)
# --------------------------------------------------------------------------- #
class TestPipelineStress:
    def test_1000_full_pipeline_ingests(
        self, gnome, sql_writer, sql_reader, forge, session_id
    ):
        """1000 events through the full dual-write pipeline."""
        tokens = ["architecture", "data", "test"]
        for i in range(1000):
            raw_anchor = create_test_anchor(
                tokens[i % 3], session_id=session_id, pulse_id=i
            )
            ingest_anchor(raw_anchor, gnome, sql_writer, forge)

        # Verify SQL persistence
        symbol_events = sql_reader.get_symbol_events(session_id)
        assert len(symbol_events) == 1000

        raw_events = sql_reader.get_raw_events(session_id)
        assert len(raw_events) == 1000

        # Verify Forge state
        stats = forge.stats()
        assert stats.total_symbols > 0
        assert stats.current_size == 1000


# --------------------------------------------------------------------------- #
# Stress 4: Batch Write
# --------------------------------------------------------------------------- #
class TestBatchWrite:
    def test_batch_write_1000_symbol_events(self, sql_writer, sql_reader, session_id):
        """Batch-write 1000 symbol events in a single transaction."""
        events = []
        for i in range(1000):
            events.append(SymbolEvent(
                event_id=str(uuid.uuid4()),
                session_id=session_id,
                pulse_id=i,
                symbol_id=i + 1,
                context_symbols=[i + 2, i + 3],
                category="core",
                priority=1,
                integrity_hash="batch_test",
                genome_version="v1.0",
                position=0,
                timestamp=float(i),
            ))

        sql_writer.write_symbol_events(events)

        # Verify all 1000 persisted
        stored = sql_reader.get_symbol_events(session_id)
        assert len(stored) == 1000


# --------------------------------------------------------------------------- #
# Stress 5: Reload from Events
# --------------------------------------------------------------------------- #
class TestReloadStress:
    def test_reload_from_1000_events(self):
        """Reload 1000 events produces consistent state."""
        forge = ForgeMemory(window_size=5000)

        # Build initial state
        events = []
        for i in range(1000):
            event = SymbolEvent(
                event_id=str(i),
                session_id="reload-stress",
                pulse_id=i,
                symbol_id=i % 100,
                context_symbols=[(i + 1) % 100],
                category="core",
                priority=1,
                integrity_hash="reload",
                genome_version="v1.0",
                position=0,
                timestamp=float(i),
            )
            forge.ingest(event)
            events.append(event)

        stats_before = forge.stats()

        # Reload
        forge.reload_from_events(events)
        stats_after = forge.stats()

        assert stats_after.current_size == stats_before.current_size
        assert stats_after.total_symbols == stats_before.total_symbols
        assert abs(stats_after.avg_resonance - stats_before.avg_resonance) < 0.01


# --------------------------------------------------------------------------- #
# Stress 6: Config Env Var Override
# --------------------------------------------------------------------------- #
class TestConfigEnvOverride:
    def test_wolf_config_reads_env_vars(self, monkeypatch):
        """Environment variables override wolf_engine.config defaults."""
        monkeypatch.setenv("WOLF_FORGE_WINDOW_SIZE", "42")
        monkeypatch.setenv("WOLF_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("WOLF_GENOME_VERSION", "v99.0")

        # Force reimport to pick up env vars
        import importlib
        import wolf_engine.config
        importlib.reload(wolf_engine.config)

        assert wolf_engine.config.FORGE_WINDOW_SIZE == 42
        assert wolf_engine.config.LOG_LEVEL == "DEBUG"
        assert wolf_engine.config.GENOME_VERSION == "v99.0"

        # Restore defaults
        monkeypatch.delenv("WOLF_FORGE_WINDOW_SIZE")
        monkeypatch.delenv("WOLF_LOG_LEVEL")
        monkeypatch.delenv("WOLF_GENOME_VERSION")
        importlib.reload(wolf_engine.config)
