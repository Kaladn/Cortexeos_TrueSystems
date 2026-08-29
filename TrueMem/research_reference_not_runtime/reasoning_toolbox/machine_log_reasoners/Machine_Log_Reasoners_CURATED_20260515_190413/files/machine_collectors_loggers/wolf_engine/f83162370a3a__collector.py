"""
Metrics Collector — ZMQ SUB aggregator + SQLite time-series store.

Runs on Node 3 (gateway). Subscribes to all node ZMQ PUB exporters,
stores every snapshot to ``metrics.db`` with automatic 7-day retention.

Provides:
  - get_latest(node_id) → most recent snapshot
  - get_history(node_id, minutes) → time-series for charting
  - get_all_latest() → all nodes' latest snapshots
  - summary() → cluster-wide summary
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_RETENTION_DAYS = 7

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    data_json TEXT NOT NULL
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_metrics_node_ts
    ON metrics(node_id, timestamp);
"""


class MetricsCollector:
    """
    Subscribes to ZMQ PUB metrics from all nodes, stores to SQLite.

    Usage:
        collector = MetricsCollector("metrics.db")
        collector.add_source("tcp://192.168.1.10:5020")  # Node 1
        collector.add_source("tcp://192.168.1.11:5020")  # Node 2
        collector.start()
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._sources: list[str] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._prune_thread: threading.Thread | None = None

        # In-memory latest cache for fast dashboard reads
        self._latest: dict[str, dict[str, Any]] = {}
        self._latest_lock = threading.Lock()

        # Initialize SQLite
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(_CREATE_TABLE + _CREATE_INDEX)
        self._conn.commit()

    def add_source(self, zmq_addr: str) -> None:
        """Add a ZMQ PUB address to subscribe to."""
        self._sources.append(zmq_addr)

    def ingest(self, data: dict[str, Any]) -> None:
        """Manually ingest a metrics snapshot (for testing or local use)."""
        node_id = data.get("node_id", "unknown")
        timestamp = data.get("timestamp", time.time())

        # Update in-memory cache
        with self._latest_lock:
            self._latest[node_id] = data

        # Store to SQLite
        self._conn.execute(
            "INSERT INTO metrics (node_id, timestamp, data_json) VALUES (?, ?, ?)",
            (node_id, timestamp, json.dumps(data)),
        )
        self._conn.commit()

    def get_latest(self, node_id: str) -> dict[str, Any] | None:
        """Get the most recent snapshot for a node (from cache)."""
        with self._latest_lock:
            return self._latest.get(node_id)

    def get_all_latest(self) -> dict[str, dict[str, Any]]:
        """Get latest snapshots for all nodes."""
        with self._latest_lock:
            return dict(self._latest)

    def get_history(
        self,
        node_id: str,
        minutes: int = 60,
        limit: int = 720,
    ) -> list[dict[str, Any]]:
        """Get time-series data for a node over the last N minutes."""
        cutoff = time.time() - (minutes * 60)
        cursor = self._conn.execute(
            """SELECT data_json FROM metrics
               WHERE node_id = ? AND timestamp > ?
               ORDER BY timestamp ASC
               LIMIT ?""",
            (node_id, cutoff, limit),
        )
        return [json.loads(row[0]) for row in cursor.fetchall()]

    def get_all_history(self, minutes: int = 60) -> dict[str, list[dict[str, Any]]]:
        """Get time-series data for ALL nodes over the last N minutes."""
        cutoff = time.time() - (minutes * 60)
        cursor = self._conn.execute(
            """SELECT node_id, data_json FROM metrics
               WHERE timestamp > ?
               ORDER BY timestamp ASC""",
            (cutoff,),
        )
        result: dict[str, list[dict[str, Any]]] = {}
        for row in cursor.fetchall():
            node_id = row[0]
            if node_id not in result:
                result[node_id] = []
            result[node_id].append(json.loads(row[1]))
        return result

    def summary(self) -> dict[str, Any]:
        """Cluster-wide summary for the dashboard header."""
        with self._latest_lock:
            nodes = dict(self._latest)

        total_nodes = len(nodes)
        healthy_nodes = sum(
            1 for n in nodes.values()
            if time.time() - n.get("timestamp", 0) < 30  # seen in last 30s
        )

        total_requests = sum(n.get("requests_total", 0) for n in nodes.values())
        total_errors = sum(n.get("requests_error", 0) for n in nodes.values())
        total_verdicts = sum(n.get("verdicts_total", 0) for n in nodes.values())

        # Find the forge node
        forge_node = None
        for n in nodes.values():
            if n.get("forge_total_symbols", 0) > 0:
                forge_node = n
                break

        return {
            "total_nodes": total_nodes,
            "healthy_nodes": healthy_nodes,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(total_errors / max(total_requests, 1) * 100, 2),
            "total_verdicts": total_verdicts,
            "forge_symbols": forge_node.get("forge_total_symbols", 0) if forge_node else 0,
            "forge_resonance": forge_node.get("forge_avg_resonance", 0) if forge_node else 0,
            "timestamp": time.time(),
        }

    def prune(self) -> int:
        """Delete metrics older than retention period. Returns rows deleted."""
        cutoff = time.time() - (_RETENTION_DAYS * 86400)
        cursor = self._conn.execute(
            "DELETE FROM metrics WHERE timestamp < ?", (cutoff,)
        )
        self._conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Pruned %d expired metrics rows", deleted)
        return deleted

    def start(self) -> None:
        """Start the ZMQ subscriber and auto-prune threads."""
        self._running = True
        if self._sources:
            self._thread = threading.Thread(
                target=self._sub_loop, daemon=True, name="metrics-sub"
            )
            self._thread.start()

        self._prune_thread = threading.Thread(
            target=self._prune_loop, daemon=True, name="metrics-prune"
        )
        self._prune_thread.start()
        logger.info(
            "MetricsCollector started: %d sources, db=%s",
            len(self._sources), self.db_path,
        )

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._prune_thread:
            self._prune_thread.join(timeout=5)

    def close(self) -> None:
        self.stop()
        self._conn.close()

    def _sub_loop(self) -> None:
        import zmq

        ctx = zmq.Context.instance()
        sock = ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, b"")
        sock.RCVTIMEO = 2000

        for addr in self._sources:
            sock.connect(addr)
            logger.info("MetricsCollector subscribed to %s", addr)

        try:
            while self._running:
                try:
                    raw = sock.recv()
                    data = json.loads(raw.decode("utf-8"))
                    self.ingest(data)
                except zmq.Again:
                    continue
                except json.JSONDecodeError as exc:
                    logger.warning("Bad metrics JSON: %s", exc)
                except Exception as exc:
                    logger.error("Metrics collector error: %s", exc)
        finally:
            sock.close()

    def _prune_loop(self) -> None:
        """Run prune every hour."""
        while self._running:
            try:
                self.prune()
            except Exception as exc:
                logger.error("Prune error: %s", exc)
            # Sleep 1 hour in 10s increments (so stop() doesn't hang)
            for _ in range(360):
                if not self._running:
                    break
                time.sleep(10)
