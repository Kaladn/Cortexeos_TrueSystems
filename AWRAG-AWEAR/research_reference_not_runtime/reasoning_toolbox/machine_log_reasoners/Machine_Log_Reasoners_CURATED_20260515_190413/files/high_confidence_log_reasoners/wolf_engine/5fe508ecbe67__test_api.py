"""
Wolf Engine — FastAPI Router endpoint tests.

Tests every /api/wolf/* endpoint using FastAPI TestClient.
Migrated from test_dashboard.py Flask tests → FastAPI httpx client.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import wolf_engine.api.router as router_module
from wolf_engine.api.router import router
from wolf_engine.core.engine import WolfEngine


@pytest.fixture
def wolf_client(tmp_path):
    """Create a FastAPI TestClient with a fresh WolfEngine instance."""
    engine = WolfEngine(db_dir=str(tmp_path))
    router_module._engine = engine
    router_module._registry = None  # Reset registry

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    yield client, engine

    engine.close()
    router_module._engine = None
    router_module._registry = None


# ===========================================================================
# Core Actions: /ingest, /analyze, /query, /cascade, /symbols/top
# ===========================================================================


class TestCoreEndpoints:
    def test_ingest(self, wolf_client):
        client, engine = wolf_client
        resp = client.post("/api/wolf/ingest", json={"text": "hello world test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["tokens"] > 0
        assert data["anchors_ingested"] > 0

    def test_ingest_missing_text_field(self, wolf_client):
        """Missing 'text' field entirely → 422 (Pydantic validation)."""
        client, engine = wolf_client
        resp = client.post("/api/wolf/ingest", json={})
        assert resp.status_code == 422

    def test_ingest_empty_text(self, wolf_client):
        """Empty text string → 400 (router check)."""
        client, engine = wolf_client
        resp = client.post("/api/wolf/ingest", json={"text": ""})
        assert resp.status_code == 400
        assert "text" in resp.json()["error"].lower()

    def test_analyze(self, wolf_client):
        client, engine = wolf_client
        resp = client.post("/api/wolf/analyze", json={"text": "analyze this text"})
        assert resp.status_code == 200
        data = resp.json()
        # Handoff contract shape
        assert "summary" in data
        assert "answer_frame" in data
        assert "trace" in data
        assert "citations" in data
        assert data["source"] == "wolf_engine"

    def test_analyze_empty(self, wolf_client):
        """Analyze without text still works (runs on existing forge data)."""
        client, engine = wolf_client
        resp = client.post("/api/wolf/analyze", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "answer_frame" in data

    def test_query_not_found(self, wolf_client):
        client, engine = wolf_client
        resp = client.get("/api/wolf/query/99999999")
        assert resp.status_code == 404

    def test_query_found(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/ingest", json={"text": "query test data"})
        if engine.forge.symbols:
            sid = next(iter(engine.forge.symbols))
            resp = client.get(f"/api/wolf/query/{sid}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["symbol_id"] == sid

    def test_cascade(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/ingest", json={"text": "cascade data for testing"})
        if engine.forge.symbols:
            sid = next(iter(engine.forge.symbols))
            resp = client.post("/api/wolf/cascade", json={
                "symbol_id": sid,
                "direction": "forward",
                "max_depth": 3,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "root" in data
            assert "nodes" in data

    def test_cascade_missing_id(self, wolf_client):
        """Missing symbol_id → 422 (Pydantic validation)."""
        client, engine = wolf_client
        resp = client.post("/api/wolf/cascade", json={})
        assert resp.status_code == 422

    def test_top_symbols(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/ingest", json={"text": "top symbols test data alpha beta"})
        resp = client.get("/api/wolf/symbols/top?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ===========================================================================
# Monitoring: /snapshot, /verdicts/*, /sessions, /status
# ===========================================================================


class TestMonitoring:
    def test_snapshot(self, wolf_client):
        client, engine = wolf_client
        resp = client.get("/api/wolf/snapshot")
        assert resp.status_code == 200
        data = resp.json()
        assert "forge" in data
        assert "verdicts" in data
        assert "counters" in data
        assert "activity" in data

    def test_verdicts_recent(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/analyze", json={"text": "verdict test"})
        resp = client.get("/api/wolf/verdicts/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_verdicts_counts(self, wolf_client):
        client, engine = wolf_client
        resp = client.get("/api/wolf/verdicts/counts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_sessions(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/analyze", json={
            "text": "session test",
            "session_id": "test-session",
        })
        resp = client.get("/api/wolf/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_status_endpoint(self, wolf_client):
        client, engine = wolf_client
        resp = client.get("/api/wolf/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert data["enabled"] is True
        assert "modules" in data


# ===========================================================================
# Debug Push
# ===========================================================================


class TestDebugPush:
    def test_debug_push_creates_verdict(self, wolf_client):
        client, engine = wolf_client
        resp = client.post("/api/wolf/debug/push")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "verdict_id" in data
        assert "session_id" in data
        # Verdict should appear in store
        recent = engine.verdict_store.get_recent(limit=1)
        assert len(recent) == 1
        assert recent[0]["verdict_id"] == data["verdict_id"]

    def test_debug_push_appears_in_activity(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/debug/push")
        resp = client.get("/api/wolf/snapshot")
        snap = resp.json()
        actions = [a["action"] for a in snap["activity"]]
        assert "debug" in actions

    def test_debug_push_multiple(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/debug/push")
        client.post("/api/wolf/debug/push")
        counts = engine.verdict_store.count_by_status()
        assert counts.get("approved", 0) >= 2


# ===========================================================================
# Session Recording
# ===========================================================================


class TestSessionRecording:
    def test_start_recording(self, wolf_client):
        client, engine = wolf_client
        resp = client.post("/api/wolf/session/start", json={"label": "test-rec"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["session"]["label"] == "test-rec"

    def test_stop_recording(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/session/start", json={"label": "stop-test"})
        resp = client.post("/api/wolf/session/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "stopped"
        assert data["session"]["end_time"] is not None

    def test_stop_without_start(self, wolf_client):
        client, engine = wolf_client
        resp = client.post("/api/wolf/session/stop")
        assert resp.status_code == 404

    def test_double_start(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/session/start", json={"label": "first"})
        resp = client.post("/api/wolf/session/start", json={"label": "second"})
        assert resp.status_code == 409

    def test_session_status(self, wolf_client):
        client, engine = wolf_client
        # Not recording
        resp = client.get("/api/wolf/session/status")
        assert resp.json()["recording"] is False
        # Start recording
        client.post("/api/wolf/session/start", json={"label": "status-test"})
        resp = client.get("/api/wolf/session/status")
        data = resp.json()
        assert data["recording"] is True
        assert "session" in data

    def test_recording_activity_log(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/session/start", json={"label": "log-test"})
        client.post("/api/wolf/session/stop")
        resp = client.get("/api/wolf/snapshot")
        snap = resp.json()
        actions = [a["action"] for a in snap["activity"]]
        assert "record_start" in actions
        assert "record_stop" in actions


# ===========================================================================
# Evidence Workers
# ===========================================================================


class TestEvidenceWorkers:
    def test_start_without_session(self, wolf_client):
        client, engine = wolf_client
        resp = client.post("/api/wolf/evidence/start", json={"workers": ["system_perf"]})
        assert resp.status_code == 400

    def test_start_with_session(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/session/start", json={"label": "worker-test"})
        resp = client.post("/api/wolf/evidence/start", json={"workers": ["system_perf"]})
        assert resp.status_code == 200
        data = resp.json()
        assert "system_perf" in data["started"]
        assert "system_perf" in data["running"]
        # Cleanup
        client.post("/api/wolf/evidence/stop")

    def test_stop_workers(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/session/start", json={})
        client.post("/api/wolf/evidence/start", json={"workers": ["system_perf"]})
        resp = client.post("/api/wolf/evidence/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert "system_perf" in data["stopped"]
        assert data["running"] == []

    def test_unknown_worker(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/session/start", json={})
        resp = client.post("/api/wolf/evidence/start", json={"workers": ["nonexistent"]})
        data = resp.json()
        assert any("unknown" in e for e in data["errors"])

    def test_evidence_status(self, wolf_client):
        client, engine = wolf_client
        resp = client.get("/api/wolf/evidence/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "available" in data
        assert "system_perf" in data["available"]
        assert data["recording"] is False

    def test_duplicate_start(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/session/start", json={})
        client.post("/api/wolf/evidence/start", json={"workers": ["system_perf"]})
        resp = client.post("/api/wolf/evidence/start", json={"workers": ["system_perf"]})
        data = resp.json()
        assert any("already running" in e for e in data["errors"])
        client.post("/api/wolf/evidence/stop")


# ===========================================================================
# Export + Reset
# ===========================================================================


class TestExportReset:
    def test_export_verdicts(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/analyze", json={"text": "export test data"})
        resp = client.get("/api/wolf/export?what=verdicts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_export_forge(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/ingest", json={"text": "forge export test"})
        resp = client.get("/api/wolf/export?what=forge")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "symbol_id" in data[0]

    def test_export_snapshot(self, wolf_client):
        client, engine = wolf_client
        resp = client.get("/api/wolf/export?what=snapshot")
        assert resp.status_code == 200
        data = resp.json()
        assert "forge" in data
        assert "counters" in data

    def test_export_unknown(self, wolf_client):
        client, engine = wolf_client
        resp = client.get("/api/wolf/export?what=nonexistent")
        assert resp.status_code == 400

    def test_reset_clears_forge(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/ingest", json={"text": "data to be reset"})
        assert engine.forge.stats().total_symbols > 0
        resp = client.post("/api/wolf/reset")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert engine.forge.stats().total_symbols == 0
        assert engine.total_ingested == 0

    def test_reset_preserves_verdicts(self, wolf_client):
        client, engine = wolf_client
        client.post("/api/wolf/analyze", json={"text": "pre-reset analysis"})
        pre_count = engine.verdict_store.count_by_status()
        client.post("/api/wolf/reset")
        post_count = engine.verdict_store.count_by_status()
        assert pre_count == post_count

    def test_export_sessions(self, wolf_client):
        client, engine = wolf_client
        resp = client.get("/api/wolf/export?what=sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ===========================================================================
# Module Registry
# ===========================================================================


class TestModules:
    def test_list_modules(self, wolf_client):
        client, engine = wolf_client
        resp = client.get("/api/wolf/modules")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "key" in data[0]
        assert "enabled" in data[0]
        assert "category" in data[0]

    def test_toggle_module(self, wolf_client):
        client, engine = wolf_client
        resp = client.post("/api/wolf/modules/toggle", json={
            "key": "op_crosshair_lock",
            "enabled": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "op_crosshair_lock"
        assert data["enabled"] is True

    def test_toggle_unknown_module(self, wolf_client):
        client, engine = wolf_client
        resp = client.post("/api/wolf/modules/toggle", json={
            "key": "nonexistent_module",
            "enabled": True,
        })
        assert resp.status_code == 404


# ===========================================================================
# End-to-End Pipeline
# ===========================================================================


class TestFullPipeline:
    def test_full_pipeline(self, wolf_client):
        """End-to-end: ingest -> analyze -> query symbol -> cascade."""
        client, engine = wolf_client

        # 1. Ingest
        resp = client.post("/api/wolf/ingest", json={
            "text": "The wolf engine processes symbols through forge memory",
            "session_id": "e2e-test",
        })
        assert resp.status_code == 200
        assert resp.json()["anchors_ingested"] > 0

        # 2. Analyze (handoff contract shape)
        resp = client.post("/api/wolf/analyze", json={
            "text": "Symbols cascade through resonance chains",
            "session_id": "e2e-test",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "answer_frame" in data
        assert data["answer_frame"] is not None
        assert "status" in data["answer_frame"]

        # 3. Top symbols
        resp = client.get("/api/wolf/symbols/top?limit=5")
        assert resp.status_code == 200
        top = resp.json()
        assert len(top) > 0

        # 4. Query a symbol
        sid = top[0]["symbol_id"]
        resp = client.get(f"/api/wolf/query/{sid}")
        assert resp.status_code == 200
        assert resp.json()["symbol_id"] == sid

        # 5. Cascade trace
        resp = client.post("/api/wolf/cascade", json={
            "symbol_id": sid,
            "direction": "both",
            "max_depth": 3,
        })
        assert resp.status_code == 200
        assert resp.json()["root"] == sid

        # 6. Snapshot
        resp = client.get("/api/wolf/snapshot")
        assert resp.status_code == 200
        snap = resp.json()
        assert snap["counters"]["total_ingested"] > 0
        assert snap["counters"]["total_analyses"] > 0
        assert len(snap["activity"]) >= 2
