"""
Wolf Engine — Core Engine unit tests.

Tests WolfEngine class directly, no HTTP framework dependency.
Migrated from test_dashboard.py (TestWolfEngine class).
"""

from __future__ import annotations

import pytest

from wolf_engine.core.engine import WolfEngine


class TestWolfEngine:
    def test_init(self, tmp_path):
        engine = WolfEngine(db_dir=str(tmp_path))
        assert engine.total_ingested == 0
        assert engine.total_analyses == 0
        engine.close()

    def test_perceive_and_ingest(self, tmp_path):
        engine = WolfEngine(db_dir=str(tmp_path))
        result = engine.perceive_and_ingest("The quick brown fox jumps over the lazy dog")
        assert result["tokens"] > 0
        assert result["anchors_ingested"] > 0
        assert "forge" in result
        assert engine.total_ingested > 0
        engine.close()

    def test_analyze(self, tmp_path):
        engine = WolfEngine(db_dir=str(tmp_path))
        result = engine.analyze(text="The wolf runs through the forest at night")
        assert "verdict" in result
        assert "patterns" in result
        assert "engine" in result
        assert engine.total_analyses == 1
        engine.close()

    def test_query_symbol_not_found(self, tmp_path):
        engine = WolfEngine(db_dir=str(tmp_path))
        result = engine.query_symbol(99999999)
        assert result is None
        engine.close()

    def test_query_symbol_found(self, tmp_path):
        engine = WolfEngine(db_dir=str(tmp_path))
        engine.perceive_and_ingest("hello world")
        if engine.forge.symbols:
            sid = next(iter(engine.forge.symbols))
            result = engine.query_symbol(sid)
            assert result is not None
            assert result["symbol_id"] == sid
            assert "resonance" in result
            assert "neighbors" in result
        engine.close()

    def test_get_top_symbols(self, tmp_path):
        engine = WolfEngine(db_dir=str(tmp_path))
        engine.perceive_and_ingest("alpha beta gamma delta epsilon")
        top = engine.get_top_symbols(limit=5)
        assert isinstance(top, list)
        if top:
            assert "symbol_id" in top[0]
            assert "resonance" in top[0]
        engine.close()

    def test_trace_cascade(self, tmp_path):
        engine = WolfEngine(db_dir=str(tmp_path))
        engine.perceive_and_ingest("cascade test data for symbol tracing")
        if engine.forge.symbols:
            sid = next(iter(engine.forge.symbols))
            result = engine.trace_cascade(sid)
            assert "root" in result
            assert "direction" in result
            assert "total_nodes" in result
            assert "nodes" in result
        engine.close()

    def test_get_system_snapshot(self, tmp_path):
        engine = WolfEngine(db_dir=str(tmp_path))
        snapshot = engine.get_system_snapshot()
        assert "forge" in snapshot
        assert "verdicts" in snapshot
        assert "counters" in snapshot
        assert "activity" in snapshot
        engine.close()

    def test_activity_log(self, tmp_path):
        engine = WolfEngine(db_dir=str(tmp_path))
        engine.perceive_and_ingest("test activity logging")
        snapshot = engine.get_system_snapshot()
        assert len(snapshot["activity"]) >= 1
        assert snapshot["activity"][0]["action"] == "ingest"
        engine.close()
