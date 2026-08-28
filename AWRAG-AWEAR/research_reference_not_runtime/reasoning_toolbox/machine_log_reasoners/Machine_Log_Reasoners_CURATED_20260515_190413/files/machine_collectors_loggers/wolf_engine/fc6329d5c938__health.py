"""
Health Monitor — Tracks service liveness via ZMQ health checks.

Runs on the gateway node. Pings each service every `interval_sec` seconds.
After `miss_threshold` consecutive misses, marks the service as DOWN.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any

from wolf_engine.services.protocol import decode_response, encode_request

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "cluster_config.json")


def load_cluster_config(path: str = _CONFIG_PATH) -> dict[str, Any]:
    """Load cluster config from JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class ServiceStatus:
    """Tracks health state for a single service."""

    def __init__(self, name: str, addr: str, miss_threshold: int = 3):
        self.name = name
        self.addr = addr
        self.miss_threshold = miss_threshold
        self.consecutive_misses = 0
        self.last_seen: float | None = None
        self.healthy = False

    def record_success(self) -> None:
        self.consecutive_misses = 0
        self.last_seen = time.time()
        self.healthy = True

    def record_failure(self) -> None:
        self.consecutive_misses += 1
        if self.consecutive_misses >= self.miss_threshold:
            self.healthy = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "addr": self.addr,
            "healthy": self.healthy,
            "consecutive_misses": self.consecutive_misses,
            "last_seen": self.last_seen,
        }


class HealthMonitor:
    """Periodically checks service health over ZMQ."""

    def __init__(self, interval_sec: float = 5.0, miss_threshold: int = 3):
        self.interval_sec = interval_sec
        self.miss_threshold = miss_threshold
        self.services: dict[str, ServiceStatus] = {}
        self._running = False
        self._thread: threading.Thread | None = None

    def register(self, name: str, zmq_addr: str) -> None:
        """Register a service to monitor."""
        self.services[name] = ServiceStatus(name, zmq_addr, self.miss_threshold)

    def check_one(self, name: str) -> bool:
        """Check a single service health. Returns True if healthy."""
        import zmq

        svc = self.services.get(name)
        if svc is None:
            return False

        ctx = zmq.Context.instance()
        sock = ctx.socket(zmq.REQ)
        sock.RCVTIMEO = 2000
        sock.SNDTIMEO = 2000
        sock.setsockopt(zmq.LINGER, 0)
        try:
            sock.connect(svc.addr)
            sock.send(encode_request("health"))
            reply = sock.recv()
            status, _ = decode_response(reply)
            if status == "ok":
                svc.record_success()
                return True
            else:
                svc.record_failure()
                return False
        except Exception:
            svc.record_failure()
            return False
        finally:
            sock.close()

    def check_all(self) -> dict[str, dict]:
        """Check all registered services. Returns status dict."""
        results = {}
        for name in self.services:
            self.check_one(name)
            results[name] = self.services[name].to_dict()
        return results

    def start(self) -> None:
        """Start background health monitoring thread."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.interval_sec + 1)

    def _loop(self) -> None:
        while self._running:
            try:
                self.check_all()
            except Exception as exc:
                logger.error("Health check error: %s", exc)
            time.sleep(self.interval_sec)
