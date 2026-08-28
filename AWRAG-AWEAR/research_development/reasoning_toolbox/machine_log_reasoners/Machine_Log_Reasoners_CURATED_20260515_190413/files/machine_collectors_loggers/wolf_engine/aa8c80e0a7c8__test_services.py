"""
Wolf Engine — Phase 1 Service Integration Tests

Tests run services on localhost with ephemeral ports, verifying:
  1. Protocol serialization round-trip
  2. Perception tokenization + 6-1-6 context
  3. Forge service ingest/query/stats/health
  4. Gateway end-to-end /think + /health
  5. Health monitor detects DOWN service
  6. Graceful degradation when a service is down
"""

from __future__ import annotations

import json
import threading
import time
import uuid

import pytest
import zmq

from wolf_engine.contracts import ForgeStats, RawAnchor, SymbolEvent
from wolf_engine.services.forge_service import ForgeServiceRunner
from wolf_engine.services.gateway import create_app
from wolf_engine.services.health import HealthMonitor
from wolf_engine.services.perception_service import (
    PerceptionServiceRunner,
    build_anchors,
    tokenize,
)
from wolf_engine.services.protocol import (
    decode_request,
    decode_response,
    dict_to_raw_anchor,
    encode_request,
    encode_response,
    forge_stats_to_dict,
    raw_anchor_to_dict,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _find_free_port() -> int:
    """Find a free TCP port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_service_thread(runner, name="service") -> threading.Thread:
    """Start a service runner in a daemon thread."""
    t = threading.Thread(target=runner.run, name=name, daemon=True)
    t.start()
    time.sleep(0.3)  # Give ZMQ time to bind
    return t


def _zmq_call(addr: str, action: str, payload: dict = None) -> tuple[str, any]:
    """Send a single ZMQ REQ/REP round-trip."""
    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.REQ)
    sock.RCVTIMEO = 5000
    sock.SNDTIMEO = 5000
    sock.setsockopt(zmq.LINGER, 0)
    try:
        sock.connect(addr)
        sock.send(encode_request(action, payload))
        reply = sock.recv()
        return decode_response(reply)
    finally:
        sock.close()


# --------------------------------------------------------------------------- #
# Test 1: Protocol Serialization Round-Trip
# --------------------------------------------------------------------------- #
class TestProtocol:
    def test_request_round_trip(self):
        data = encode_request("ingest", {"token": "test"})
        action, payload = decode_request(data)
        assert action == "ingest"
        assert payload["token"] == "test"

    def test_response_round_trip(self):
        data = encode_response("ok", {"count": 42})
        status, payload = decode_response(data)
        assert status == "ok"
        assert payload["count"] == 42

    def test_raw_anchor_serialization(self):
        anchor = RawAnchor(
            event_id="e1", session_id="s1", pulse_id=1,
            token="hello", context_before=["a"], context_after=["b"],
            position=0,
        )
        d = raw_anchor_to_dict(anchor)
        restored = dict_to_raw_anchor(d)
        assert restored.event_id == "e1"
        assert restored.token == "hello"
        assert restored.context_before == ["a"]


# --------------------------------------------------------------------------- #
# Test 2: Perception Tokenization + 6-1-6 Context
# --------------------------------------------------------------------------- #
class TestPerception:
    def test_tokenize_basic(self):
        tokens = tokenize("The quick brown fox jumps over the lazy dog")
        assert tokens == ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"]

    def test_build_anchors_context_windows(self):
        tokens = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m"]
        anchors = build_anchors(tokens, session_id="s1", window_size=6)
        # 13 tokens = 13 anchors
        assert len(anchors) == 13
        # Middle token "g" (index 6) has 6 before and 6 after
        g_anchor = anchors[6]
        assert g_anchor.token == "g"
        assert g_anchor.context_before == ["a", "b", "c", "d", "e", "f"]
        assert g_anchor.context_after == ["h", "i", "j", "k", "l", "m"]
        # First token has 0 before, up to 6 after
        assert anchors[0].context_before == []
        assert len(anchors[0].context_after) == 6

    def test_perception_service_zmq(self):
        port = _find_free_port()
        runner = PerceptionServiceRunner(bind_addr=f"tcp://127.0.0.1:{port}")
        t = _start_service_thread(runner, "perception")

        try:
            addr = f"tcp://127.0.0.1:{port}"
            status, data = _zmq_call(addr, "perceive", {
                "text": "the wolf engine processes symbols",
                "session_id": "test-session",
            })
            assert status == "ok"
            assert data["token_count"] == 5
            assert len(data["anchors"]) == 5
            # Verify first anchor
            first = data["anchors"][0]
            assert first["token"] == "the"
            assert first["context_before"] == []
            assert len(first["context_after"]) == 4
        finally:
            runner.stop()


# --------------------------------------------------------------------------- #
# Test 3: Forge Service — Ingest/Query/Stats/Health
# --------------------------------------------------------------------------- #
class TestForgeService:
    def test_forge_ingest_query_stats(self, genome_path, tmp_path):
        db_path = str(tmp_path / "forge_test.db")
        port = _find_free_port()
        runner = ForgeServiceRunner(
            db_path=db_path,
            genome_path=genome_path,
            bind_addr=f"tcp://127.0.0.1:{port}",
        )
        # Create a session first
        sid = str(uuid.uuid4())
        runner.sql_writer.create_session(sid, "v1.0", "test_hash")

        t = _start_service_thread(runner, "forge")
        addr = f"tcp://127.0.0.1:{port}"

        try:
            # Ingest
            anchor = RawAnchor(
                event_id=str(uuid.uuid4()),
                session_id=sid,
                pulse_id=1,
                token="architecture",
                context_before=["the"],
                context_after=["of"],
                position=0,
            )
            status, data = _zmq_call(addr, "ingest", raw_anchor_to_dict(anchor))
            assert status == "ok"
            assert data["event_id"] == anchor.event_id

            # Stats
            status, data = _zmq_call(addr, "stats")
            assert status == "ok"
            assert data["total_symbols"] >= 1

            # Health
            status, data = _zmq_call(addr, "health")
            assert status == "ok"
            assert data["service"] == "forge"
            assert data["status"] == "healthy"
        finally:
            runner.stop()
            runner.close()


# --------------------------------------------------------------------------- #
# Test 4: Gateway End-to-End /think + /health
# --------------------------------------------------------------------------- #
class TestGateway:
    def test_think_end_to_end(self, genome_path, tmp_path):
        db_path = str(tmp_path / "gw_test.db")
        forge_port = _find_free_port()
        perc_port = _find_free_port()

        # Start services
        forge_runner = ForgeServiceRunner(
            db_path=db_path,
            genome_path=genome_path,
            bind_addr=f"tcp://127.0.0.1:{forge_port}",
        )
        sid = str(uuid.uuid4())
        forge_runner.sql_writer.create_session(sid, "v1.0", "test_hash")

        perc_runner = PerceptionServiceRunner(
            bind_addr=f"tcp://127.0.0.1:{perc_port}"
        )

        ft = _start_service_thread(forge_runner, "forge")
        pt = _start_service_thread(perc_runner, "perception")

        # Create Flask test client
        app = create_app(
            forge_addr=f"tcp://127.0.0.1:{forge_port}",
            perception_addr=f"tcp://127.0.0.1:{perc_port}",
        )

        try:
            with app.test_client() as client:
                # /think
                resp = client.post("/think", json={
                    "text": "architecture data test",
                    "session_id": sid,
                })
                assert resp.status_code == 200
                body = resp.get_json()
                assert body["status"] == "ok"
                assert body["tokens_perceived"] == 3
                assert body["anchors_ingested"] == 3

                # /stats
                resp = client.get("/stats")
                assert resp.status_code == 200
                stats = resp.get_json()
                assert stats["total_symbols"] >= 1

                # /health
                resp = client.get("/health")
                assert resp.status_code == 200
                health = resp.get_json()
                assert health["forge"]["status"] == "healthy"
                assert health["perception"]["status"] == "healthy"
                assert health["gateway"]["status"] == "healthy"
        finally:
            forge_runner.stop()
            perc_runner.stop()
            forge_runner.close()


# --------------------------------------------------------------------------- #
# Test 5: Health Monitor Detects DOWN Service
# --------------------------------------------------------------------------- #
class TestHealthMonitor:
    def test_healthy_then_down(self, genome_path, tmp_path):
        db_path = str(tmp_path / "health_test.db")
        port = _find_free_port()

        runner = ForgeServiceRunner(
            db_path=db_path,
            genome_path=genome_path,
            bind_addr=f"tcp://127.0.0.1:{port}",
        )
        t = _start_service_thread(runner, "forge")

        monitor = HealthMonitor(interval_sec=1.0, miss_threshold=2)
        monitor.register("forge", f"tcp://127.0.0.1:{port}")

        try:
            # Should be healthy
            assert monitor.check_one("forge") is True
            assert monitor.services["forge"].healthy is True

            # Stop the service
            runner.stop()
            time.sleep(1.5)  # Wait for service to actually stop

            # Should detect failure after miss_threshold misses
            monitor.check_one("forge")
            monitor.check_one("forge")
            assert monitor.services["forge"].healthy is False
        finally:
            runner.stop()
            runner.close()


# --------------------------------------------------------------------------- #
# Test 6: Gateway Graceful Degradation
# --------------------------------------------------------------------------- #
class TestGracefulDegradation:
    def test_gateway_returns_502_when_forge_down(self):
        """Gateway returns 502 when Forge is unreachable."""
        dead_port = _find_free_port()
        app = create_app(
            forge_addr=f"tcp://127.0.0.1:{dead_port}",
            perception_addr=f"tcp://127.0.0.1:{dead_port}",
        )
        with app.test_client() as client:
            resp = client.get("/stats")
            assert resp.status_code == 502

    def test_health_shows_down_services(self):
        """Health endpoint shows services as down when unreachable."""
        dead_port = _find_free_port()
        app = create_app(
            forge_addr=f"tcp://127.0.0.1:{dead_port}",
            perception_addr=f"tcp://127.0.0.1:{dead_port}",
        )
        with app.test_client() as client:
            resp = client.get("/health")
            assert resp.status_code == 503
            health = resp.get_json()
            assert health["gateway"]["status"] == "healthy"
