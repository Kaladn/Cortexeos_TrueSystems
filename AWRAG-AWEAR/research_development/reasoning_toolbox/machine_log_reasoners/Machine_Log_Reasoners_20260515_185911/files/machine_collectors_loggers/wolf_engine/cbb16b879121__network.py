"""Network Logger — inter-node ping and packet loss.

Thin WolfModule wrapper around wolf_engine.evidence.workers.NetworkLoggerWorker.
"""

from __future__ import annotations

from typing import Any, Dict

from wolf_engine.modules.base import WolfModule


class NetworkModule(WolfModule):
    """WolfModule wrapper for NetworkLoggerWorker."""

    key = "log_network"
    name = "Network Logger"
    category = "logger"
    description = "Inter-node ping and packet loss"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._worker = None

    def start(self):
        super().start()
        try:
            from wolf_engine.evidence.workers import NetworkLoggerWorker
            self._worker = NetworkLoggerWorker(session_mgr=None, interval_sec=5.0)
        except ImportError:
            pass

    def stop(self):
        super().stop()
        if self._worker:
            try:
                self._worker.stop()
            except Exception:
                pass
            self._worker = None

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
        }
