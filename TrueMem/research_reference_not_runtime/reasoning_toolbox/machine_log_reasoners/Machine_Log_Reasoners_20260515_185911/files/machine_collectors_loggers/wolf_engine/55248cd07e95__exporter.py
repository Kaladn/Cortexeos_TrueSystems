"""
Metrics Exporter — ZMQ PUB on each node, publishes system metrics.

Every node runs a MetricsExporter that broadcasts a JSON metrics
snapshot every ``interval_sec`` seconds on a ZMQ PUB socket.
The collector on Node 3 subscribes to all exporters.

Metrics include: CPU %, RAM %, disk %, GPU (if available), Forge stats,
request counters, error counters, and uptime.
"""

from __future__ import annotations

import logging
import os
import platform
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NodeMetrics:
    """Snapshot of a single node's metrics at a point in time."""

    node_id: str = ""
    timestamp: float = 0.0

    # System
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    disk_percent: float = 0.0

    # GPU (Node 1 only)
    gpu_available: bool = False
    gpu_name: str = ""
    gpu_util_percent: float = 0.0
    gpu_mem_used_mb: float = 0.0
    gpu_mem_total_mb: float = 0.0
    gpu_temp_c: float = 0.0

    # Forge (Node 1 only)
    forge_total_symbols: int = 0
    forge_total_chains: int = 0
    forge_avg_resonance: float = 0.0
    forge_window_size: int = 0
    forge_current_size: int = 0

    # Service counters
    requests_total: int = 0
    requests_ok: int = 0
    requests_error: int = 0
    uptime_sec: float = 0.0

    # Archon (Node 3 only)
    verdicts_total: int = 0
    verdicts_approved: int = 0
    verdicts_adjusted: int = 0
    verdicts_quarantined: int = 0
    verdicts_penalized: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _collect_system_metrics() -> dict[str, Any]:
    """Collect CPU, RAM, disk via psutil (graceful fallback)."""
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent": cpu,
            "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used / (1024 ** 3), 2),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "disk_percent": disk.percent,
        }
    except ImportError:
        return {}


def _collect_gpu_metrics() -> dict[str, Any]:
    """Collect GPU metrics via PyTorch (CUDA or ROCm) + smi tool."""
    try:
        import torch

        # torch.cuda.* works for both NVIDIA CUDA and AMD ROCm builds
        if not torch.cuda.is_available():
            return {"gpu_available": False}

        props = torch.cuda.get_device_properties(0)
        mem_alloc = torch.cuda.memory_allocated(0) / (1024 ** 2)
        mem_total = getattr(props, "total_memory", getattr(props, "total_mem", 0)) / (1024 ** 2)

        result = {
            "gpu_available": True,
            "gpu_name": props.name,
            "gpu_mem_used_mb": round(mem_alloc, 1),
            "gpu_mem_total_mb": round(mem_total, 1),
        }

        # Augment with utilization + temperature via rocm-smi or nvidia-smi
        try:
            from bridges.gpu_backend import query_gpu_json
            stats = query_gpu_json()
            if stats:
                if "util_pct" in stats:
                    result["gpu_util_percent"] = stats["util_pct"]
                if "temp_c" in stats:
                    result["gpu_temp_c"] = stats["temp_c"]
        except Exception:
            pass

        return result
    except ImportError:
        return {"gpu_available": False}


class MetricsExporter:
    """
    ZMQ PUB metrics broadcaster.

    Publishes a JSON-encoded NodeMetrics snapshot every ``interval_sec``
    seconds on the given bind address.
    """

    def __init__(
        self,
        node_id: str = "",
        bind_addr: str = "tcp://*:5020",
        interval_sec: float = 5.0,
    ):
        self.node_id = node_id or platform.node()
        self.bind_addr = bind_addr
        self.interval_sec = interval_sec

        # Counters updated externally
        self._requests_total = 0
        self._requests_ok = 0
        self._requests_error = 0
        self._start_time = time.time()

        # External providers
        self._forge_stats_fn = None
        self._verdict_counts_fn = None

        self._running = False
        self._thread: threading.Thread | None = None

    def set_forge_stats_provider(self, fn) -> None:
        """Register a callable that returns ForgeStats."""
        self._forge_stats_fn = fn

    def set_verdict_counts_provider(self, fn) -> None:
        """Register a callable that returns dict[str, int] verdict counts."""
        self._verdict_counts_fn = fn

    def record_request(self, ok: bool = True) -> None:
        """Increment request counters (thread-safe via GIL for ints)."""
        self._requests_total += 1
        if ok:
            self._requests_ok += 1
        else:
            self._requests_error += 1

    def collect(self) -> NodeMetrics:
        """Collect a full metrics snapshot."""
        m = NodeMetrics(
            node_id=self.node_id,
            timestamp=time.time(),
            requests_total=self._requests_total,
            requests_ok=self._requests_ok,
            requests_error=self._requests_error,
            uptime_sec=round(time.time() - self._start_time, 1),
        )

        # System metrics
        sys_m = _collect_system_metrics()
        for k, v in sys_m.items():
            if hasattr(m, k):
                object.__setattr__(m, k, v)

        # GPU metrics
        gpu_m = _collect_gpu_metrics()
        for k, v in gpu_m.items():
            if hasattr(m, k):
                object.__setattr__(m, k, v)

        # Forge stats
        if self._forge_stats_fn:
            try:
                stats = self._forge_stats_fn()
                m.forge_total_symbols = stats.total_symbols
                m.forge_total_chains = stats.total_chains
                m.forge_avg_resonance = round(stats.avg_resonance, 4)
                m.forge_window_size = stats.window_size
                m.forge_current_size = stats.current_size
            except Exception as exc:
                logger.warning("Forge stats collection failed: %s", exc)

        # Verdict counts
        if self._verdict_counts_fn:
            try:
                counts = self._verdict_counts_fn()
                m.verdicts_approved = counts.get("approved", 0)
                m.verdicts_adjusted = counts.get("adjusted", 0)
                m.verdicts_quarantined = counts.get("quarantined", 0)
                m.verdicts_penalized = counts.get("penalized", 0)
                m.verdicts_total = sum(counts.values())
            except Exception as exc:
                logger.warning("Verdict counts collection failed: %s", exc)

        return m

    def start(self) -> None:
        """Start publishing metrics in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="metrics-pub")
        self._thread.start()
        logger.info("MetricsExporter started: %s (node=%s)", self.bind_addr, self.node_id)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.interval_sec + 2)

    def _loop(self) -> None:
        import json
        import zmq

        ctx = zmq.Context.instance()
        sock = ctx.socket(zmq.PUB)
        sock.setsockopt(zmq.LINGER, 0)
        sock.bind(self.bind_addr)

        # PUB needs a small warmup for subscribers to connect
        time.sleep(0.2)

        try:
            while self._running:
                try:
                    metrics = self.collect()
                    payload = json.dumps(metrics.to_dict()).encode("utf-8")
                    sock.send(payload)
                except Exception as exc:
                    logger.error("Metrics publish error: %s", exc)
                time.sleep(self.interval_sec)
        finally:
            sock.close()
