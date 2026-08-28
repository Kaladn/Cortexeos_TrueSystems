"""
Wolf Engine — Metrics unit tests.

Tests NodeMetrics, MetricsExporter, and MetricsCollector.
Migrated from test_dashboard.py.
"""

from __future__ import annotations

import json
import time

import pytest

from wolf_engine.metrics.collector import MetricsCollector
from wolf_engine.metrics.exporter import (
    MetricsExporter,
    NodeMetrics,
    _collect_system_metrics,
)


class TestNodeMetrics:
    def test_defaults(self):
        m = NodeMetrics()
        assert m.node_id == ""
        assert m.cpu_percent == 0.0
        assert m.gpu_available is False
        assert m.verdicts_total == 0

    def test_to_dict_round_trip(self):
        m = NodeMetrics(node_id="test-node", cpu_percent=45.2, ram_percent=62.1)
        d = m.to_dict()
        assert d["node_id"] == "test-node"
        assert d["cpu_percent"] == 45.2
        assert d["ram_percent"] == 62.1
        assert isinstance(d, dict)

    def test_all_fields_present(self):
        m = NodeMetrics()
        d = m.to_dict()
        expected_fields = [
            "node_id", "timestamp", "cpu_percent", "ram_percent",
            "ram_used_gb", "ram_total_gb", "disk_percent",
            "gpu_available", "gpu_name", "gpu_util_percent",
            "gpu_mem_used_mb", "gpu_mem_total_mb", "gpu_temp_c",
            "forge_total_symbols", "forge_total_chains", "forge_avg_resonance",
            "forge_window_size", "forge_current_size",
            "requests_total", "requests_ok", "requests_error", "uptime_sec",
            "verdicts_total", "verdicts_approved", "verdicts_adjusted",
            "verdicts_quarantined", "verdicts_penalized",
        ]
        for field in expected_fields:
            assert field in d, f"Missing field: {field}"


class TestMetricsExporter:
    def test_collect_basic(self):
        exp = MetricsExporter(node_id="test-node")
        metrics = exp.collect()
        assert metrics.node_id == "test-node"
        assert metrics.timestamp > 0
        assert metrics.uptime_sec >= 0

    def test_request_counters(self):
        exp = MetricsExporter(node_id="test")
        exp.record_request(ok=True)
        exp.record_request(ok=True)
        exp.record_request(ok=False)
        metrics = exp.collect()
        assert metrics.requests_total == 3
        assert metrics.requests_ok == 2
        assert metrics.requests_error == 1

    def test_forge_stats_provider(self):
        from wolf_engine.contracts import ForgeStats

        stats = ForgeStats(
            total_symbols=42,
            total_chains=10,
            avg_resonance=3.14,
            window_size=10000,
            current_size=500,
        )
        exp = MetricsExporter(node_id="forge-node")
        exp.set_forge_stats_provider(lambda: stats)
        metrics = exp.collect()
        assert metrics.forge_total_symbols == 42
        assert metrics.forge_total_chains == 10
        assert metrics.forge_avg_resonance == 3.14

    def test_verdict_counts_provider(self):
        counts = {"approved": 10, "adjusted": 3, "quarantined": 1, "penalized": 2}
        exp = MetricsExporter(node_id="archon-node")
        exp.set_verdict_counts_provider(lambda: counts)
        metrics = exp.collect()
        assert metrics.verdicts_approved == 10
        assert metrics.verdicts_total == 16

    def test_system_metrics_collected(self):
        """System metrics should return at least some data (psutil available)."""
        sys_m = _collect_system_metrics()
        # psutil may or may not be installed; if it is, we get data
        if sys_m:
            assert "cpu_percent" in sys_m
            assert "ram_percent" in sys_m

    def test_collect_serializable(self):
        exp = MetricsExporter(node_id="json-test")
        metrics = exp.collect()
        # Must be JSON-serializable
        serialized = json.dumps(metrics.to_dict())
        parsed = json.loads(serialized)
        assert parsed["node_id"] == "json-test"


class TestMetricsCollector:
    def test_ingest_and_latest(self, tmp_path):
        col = MetricsCollector(str(tmp_path / "metrics.db"))
        data = {"node_id": "n1", "timestamp": time.time(), "cpu_percent": 55.0}
        col.ingest(data)
        latest = col.get_latest("n1")
        assert latest is not None
        assert latest["cpu_percent"] == 55.0
        col.close()

    def test_get_all_latest(self, tmp_path):
        col = MetricsCollector(str(tmp_path / "metrics.db"))
        col.ingest({"node_id": "n1", "timestamp": time.time(), "cpu_percent": 10})
        col.ingest({"node_id": "n2", "timestamp": time.time(), "cpu_percent": 20})
        all_latest = col.get_all_latest()
        assert "n1" in all_latest
        assert "n2" in all_latest
        col.close()

    def test_history(self, tmp_path):
        col = MetricsCollector(str(tmp_path / "metrics.db"))
        for i in range(5):
            col.ingest({"node_id": "n1", "timestamp": time.time(), "val": i})
        history = col.get_history("n1", minutes=60)
        assert len(history) == 5
        col.close()

    def test_get_all_history(self, tmp_path):
        col = MetricsCollector(str(tmp_path / "metrics.db"))
        col.ingest({"node_id": "n1", "timestamp": time.time(), "v": 1})
        col.ingest({"node_id": "n2", "timestamp": time.time(), "v": 2})
        all_hist = col.get_all_history(minutes=60)
        assert "n1" in all_hist
        assert "n2" in all_hist
        col.close()

    def test_summary_empty(self, tmp_path):
        col = MetricsCollector(str(tmp_path / "metrics.db"))
        s = col.summary()
        assert s["total_nodes"] == 0
        assert s["healthy_nodes"] == 0
        col.close()

    def test_summary_with_data(self, tmp_path):
        col = MetricsCollector(str(tmp_path / "metrics.db"))
        col.ingest({
            "node_id": "n1", "timestamp": time.time(),
            "requests_total": 100, "requests_error": 5,
            "forge_total_symbols": 42,
        })
        s = col.summary()
        assert s["total_nodes"] == 1
        assert s["healthy_nodes"] == 1
        assert s["total_requests"] == 100
        assert s["total_errors"] == 5
        assert s["error_rate"] == 5.0
        col.close()

    def test_prune(self, tmp_path):
        col = MetricsCollector(str(tmp_path / "metrics.db"))
        # Insert old data (8 days ago)
        old_ts = time.time() - (8 * 86400)
        col._conn.execute(
            "INSERT INTO metrics (node_id, timestamp, data_json) VALUES (?, ?, ?)",
            ("old", old_ts, "{}"),
        )
        col._conn.commit()
        # Insert recent data
        col.ingest({"node_id": "new", "timestamp": time.time()})

        deleted = col.prune()
        assert deleted == 1

        # Verify recent data survives
        history = col.get_history("new", minutes=60)
        assert len(history) == 1
        col.close()

    def test_add_source(self, tmp_path):
        col = MetricsCollector(str(tmp_path / "metrics.db"))
        col.add_source("tcp://localhost:5020")
        col.add_source("tcp://localhost:5021")
        assert len(col._sources) == 2
        col.close()
