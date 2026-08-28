"""System Perf Logger — CPU/RAM/GPU metrics via psutil.

Thin WolfModule wrapper around wolf_engine.evidence.workers.SystemPerfWorker.
"""

from __future__ import annotations

from typing import Any, Dict

from wolf_engine.modules.base import WolfModule


class SystemPerfModule(WolfModule):
    """WolfModule wrapper for SystemPerfWorker."""

    key = "log_system_perf"
    name = "System Perf"
    category = "logger"
    description = "CPU/RAM/GPU metrics via psutil"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._worker = None

    def start(self):
        super().start()
        try:
            from wolf_engine.evidence.workers import SystemPerfWorker
            self._worker = SystemPerfWorker(session_mgr=None, interval_sec=5.0)
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
            "worker_loaded": self._worker is not None,
        }
