"""
Phase 3 Evidence test suite — timebase, session manager, workers, fusion.

All tests run on local filesystem with tmp_path fixtures. No network or
hardware dependencies.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from wolf_engine.evidence.timebase import EvidenceEvent, Timestamp
from wolf_engine.evidence.session_manager import EvidenceSessionManager, SessionInfo
from wolf_engine.evidence.worker_base import WorkerBase, write_safe
from wolf_engine.evidence.fusion import fuse_session, read_fused_events, FusionWatcher
from wolf_engine.evidence.workers import (
    SystemPerfWorker,
    ProcessLoggerWorker,
    InputLoggerWorker,
)


# ===========================================================================
# P3-TMB: Timebase
# ===========================================================================


class TestTimestamp:
    def test_auto_populate(self):
        ts = Timestamp(node_id="node_1")
        assert ts.monotonic_ns > 0
        assert ts.wall_clock > 0
        assert ts.node_id == "node_1"

    def test_ordering(self):
        ts1 = Timestamp(wall_clock=100.0, monotonic_ns=1000, node_id="n1")
        ts2 = Timestamp(wall_clock=200.0, monotonic_ns=500, node_id="n1")
        assert ts1 < ts2

    def test_same_wall_clock_same_node_uses_monotonic(self):
        ts1 = Timestamp(wall_clock=100.0, monotonic_ns=1000, node_id="n1")
        ts2 = Timestamp(wall_clock=100.0, monotonic_ns=2000, node_id="n1")
        assert ts1 < ts2

    def test_round_trip_dict(self):
        ts = Timestamp(monotonic_ns=12345, wall_clock=99.99, node_id="n2")
        d = ts.to_dict()
        ts2 = Timestamp.from_dict(d)
        assert ts2.monotonic_ns == 12345
        assert ts2.wall_clock == 99.99
        assert ts2.node_id == "n2"


class TestEvidenceEvent:
    def test_round_trip(self):
        ev = EvidenceEvent(
            worker="test_worker",
            event_type="metric",
            timestamp=Timestamp(monotonic_ns=1, wall_clock=2.0, node_id="n1"),
            data={"cpu": 50},
            session_id="sess_1",
        )
        d = ev.to_dict()
        ev2 = EvidenceEvent.from_dict(d)
        assert ev2.worker == "test_worker"
        assert ev2.event_type == "metric"
        assert ev2.data == {"cpu": 50}
        assert ev2.session_id == "sess_1"
        assert ev2.timestamp.node_id == "n1"


# ===========================================================================
# P3-SES: Session Manager
# ===========================================================================


class TestSessionManager:
    def test_start_creates_directory_and_manifest(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path), node_id="node_1")
        info = mgr.start("test_session")
        assert info.session_id
        assert info.node_id == "node_1"
        assert Path(info.session_dir).exists()
        manifest = Path(info.session_dir) / "manifest.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert data["label"] == "test_session"

    def test_stop_updates_manifest(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        mgr.start("s1")
        info = mgr.stop()
        assert info is not None
        assert info.end_time is not None
        manifest = json.loads(
            Path(info.session_dir, "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["end_time"] is not None

    def test_register_worker(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        mgr.start()
        mgr.register_worker("perf")
        mgr.register_worker("network")
        assert mgr.active_session.workers == ["perf", "network"]

    def test_get_output_path(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        mgr.start()
        path = mgr.get_output_path("system_perf")
        assert path.endswith("system_perf_events.jsonl")

    def test_no_active_session_raises(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        with pytest.raises(RuntimeError, match="No active session"):
            mgr.register_worker("x")
        with pytest.raises(RuntimeError, match="No active session"):
            mgr.get_output_path("x")

    def test_double_start_finalizes_first(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        info1 = mgr.start("first")
        info2 = mgr.start("second")
        assert info1.session_id != info2.session_id
        # First session directory should have an updated manifest with end_time
        data = json.loads(
            Path(info1.session_dir, "manifest.json").read_text(encoding="utf-8")
        )
        assert data["end_time"] is not None

    def test_list_sessions(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        mgr.start("a")
        mgr.stop()
        mgr.start("b")
        mgr.stop()
        sessions = mgr.list_sessions()
        assert len(sessions) == 2

    def test_record_event_counter(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        mgr.start()
        mgr.record_event()
        mgr.record_event()
        mgr.record_event()
        assert mgr.active_session.event_count == 3


# ===========================================================================
# P3-WRK: Worker Base + write_safe
# ===========================================================================


class TestWriteSafe:
    def test_write_appends_json_line(self, tmp_path):
        path = str(tmp_path / "test.jsonl")
        assert write_safe(path, {"a": 1})
        assert write_safe(path, {"b": 2})
        lines = Path(path).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"a": 1}

    def test_write_safe_bad_path_returns_false(self, tmp_path):
        # Non-existent nested directory
        bad_path = str(tmp_path / "no" / "such" / "dir" / "file.jsonl")
        result = write_safe(bad_path, {"x": 1}, max_retries=1)
        assert result is False


class _DummyWorker(WorkerBase):
    """Test worker that emits a fixed counter."""
    worker_name = "dummy_worker"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._counter = 0

    def collect(self):
        self._counter += 1
        return [{"event_type": "dummy_tick", "count": self._counter}]


class TestWorkerBase:
    def test_worker_lifecycle(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path), node_id="test_node")
        mgr.start("worker_test")

        worker = _DummyWorker(session_mgr=mgr, interval_sec=0.1)
        worker.start()
        assert worker.is_running

        time.sleep(0.5)
        count = worker.stop()
        assert not worker.is_running
        assert count >= 2  # At least 2 events in 0.5s at 0.1s interval

        # Verify JSONL output
        output_path = mgr.get_output_path("dummy_worker")
        lines = Path(output_path).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 2
        first = json.loads(lines[0])
        assert first["worker"] == "dummy_worker"
        assert first["event_type"] == "dummy_tick"
        assert "timestamp" in first
        assert first["timestamp"]["node_id"] == "test_node"

        mgr.stop()

    def test_no_session_raises(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        worker = _DummyWorker(session_mgr=mgr, interval_sec=1.0)
        with pytest.raises(RuntimeError, match="No active session"):
            worker.start()


# ===========================================================================
# Concrete Workers (smoke tests — just verify collect() returns valid data)
# ===========================================================================


class TestConcreteWorkers:
    def test_system_perf_collect(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        mgr.start()
        worker = SystemPerfWorker(session_mgr=mgr, interval_sec=1.0)
        data = worker.collect()
        assert len(data) == 1
        assert data[0]["event_type"] == "system_perf"
        # Should have cpu_percent (may be None if no psutil)
        assert "cpu_percent" in data[0]

    def test_process_logger_collect(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        mgr.start()
        worker = ProcessLoggerWorker(session_mgr=mgr, interval_sec=1.0)
        data = worker.collect()
        assert len(data) == 1
        assert data[0]["event_type"] == "process_snapshot"
        assert "processes" in data[0]

    def test_input_logger_collect(self, tmp_path):
        mgr = EvidenceSessionManager(str(tmp_path))
        mgr.start()
        worker = InputLoggerWorker(session_mgr=mgr, interval_sec=1.0)
        data = worker.collect()
        assert len(data) == 1
        assert data[0]["event_type"] == "input_activity"


# ===========================================================================
# P3-FUS: Fusion
# ===========================================================================


class TestFusion:
    def _write_events(self, session_dir: Path, worker: str, events: list[dict]):
        path = session_dir / f"{worker}_events.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

    def test_fuse_two_workers(self, tmp_path):
        session_dir = tmp_path / "session_1"
        session_dir.mkdir()

        # Worker A: timestamps 1.0, 3.0
        self._write_events(session_dir, "worker_a", [
            EvidenceEvent(
                worker="worker_a", event_type="a1",
                timestamp=Timestamp(monotonic_ns=100, wall_clock=1.0, node_id="n1"),
                data={"val": 1},
            ).to_dict(),
            EvidenceEvent(
                worker="worker_a", event_type="a2",
                timestamp=Timestamp(monotonic_ns=300, wall_clock=3.0, node_id="n1"),
                data={"val": 3},
            ).to_dict(),
        ])

        # Worker B: timestamp 2.0
        self._write_events(session_dir, "worker_b", [
            EvidenceEvent(
                worker="worker_b", event_type="b1",
                timestamp=Timestamp(monotonic_ns=200, wall_clock=2.0, node_id="n1"),
                data={"val": 2},
            ).to_dict(),
        ])

        fused = fuse_session(str(session_dir))
        assert len(fused) == 3
        # Should be sorted: 1.0, 2.0, 3.0
        assert fused[0].data["val"] == 1
        assert fused[1].data["val"] == 2
        assert fused[2].data["val"] == 3

        # Verify fused_events.jsonl was written
        fused_path = session_dir / "fused_events.jsonl"
        assert fused_path.exists()
        read_back = read_fused_events(str(session_dir))
        assert len(read_back) == 3

    def test_fuse_empty_session(self, tmp_path):
        session_dir = tmp_path / "empty_session"
        session_dir.mkdir()
        fused = fuse_session(str(session_dir))
        assert fused == []

    def test_fuse_skips_malformed_lines(self, tmp_path):
        session_dir = tmp_path / "bad_session"
        session_dir.mkdir()
        bad_file = session_dir / "bad_events.jsonl"
        bad_file.write_text(
            '{"worker":"a","event_type":"x","timestamp":{"monotonic_ns":1,"wall_clock":1.0,"node_id":"n1"},"data":{},"session_id":""}\n'
            'NOT VALID JSON\n'
            '{"worker":"b","event_type":"y","timestamp":{"monotonic_ns":2,"wall_clock":2.0,"node_id":"n1"},"data":{},"session_id":""}\n',
            encoding="utf-8",
        )
        fused = fuse_session(str(session_dir))
        assert len(fused) == 2

    def test_fuse_does_not_include_own_output(self, tmp_path):
        """fused_events.jsonl should not be read as an input source."""
        session_dir = tmp_path / "rerun"
        session_dir.mkdir()
        self._write_events(session_dir, "worker_x", [
            EvidenceEvent(
                worker="worker_x", event_type="x1",
                timestamp=Timestamp(monotonic_ns=1, wall_clock=1.0, node_id="n1"),
                data={},
            ).to_dict(),
        ])

        # Fuse once
        fuse_session(str(session_dir))
        # Fuse again — should not double-count
        fused = fuse_session(str(session_dir))
        assert len(fused) == 1

    def test_fusion_watcher_lifecycle(self, tmp_path):
        session_dir = tmp_path / "watch_session"
        session_dir.mkdir()

        self._write_events(session_dir, "worker_w", [
            EvidenceEvent(
                worker="worker_w", event_type="w1",
                timestamp=Timestamp(monotonic_ns=1, wall_clock=1.0, node_id="n1"),
                data={"v": 1},
            ).to_dict(),
        ])

        watcher = FusionWatcher(str(session_dir), interval_sec=0.2)
        watcher.start()
        time.sleep(0.5)
        count = watcher.stop()
        assert count >= 1

    def test_full_pipeline_session_workers_fusion(self, tmp_path):
        """End-to-end: session → workers → fusion."""
        mgr = EvidenceSessionManager(str(tmp_path), node_id="test_node")
        info = mgr.start("integration_test")

        # Run dummy worker
        worker = _DummyWorker(session_mgr=mgr, interval_sec=0.1)
        worker.start()
        time.sleep(0.4)
        worker.stop()

        # Fuse
        fused = fuse_session(info.session_dir)
        assert len(fused) >= 2

        # All events should be sorted
        for i in range(1, len(fused)):
            assert fused[i].timestamp.wall_clock >= fused[i - 1].timestamp.wall_clock

        mgr.stop()
