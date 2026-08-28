"""Input Logger — aggregate input patterns.

Thin WolfModule wrapper around wolf_engine.evidence.workers.InputLoggerWorker.
"""

from __future__ import annotations

from typing import Any, Dict

from wolf_engine.modules.base import WolfModule


class InputModule(WolfModule):
    """WolfModule wrapper for InputLoggerWorker."""

    key = "log_input"
    name = "Input Logger"
    category = "logger"
    description = "Aggregate input patterns"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._worker = None

    def start(self):
        super().start()
        try:
            from wolf_engine.evidence.workers import InputLoggerWorker
            self._worker = InputLoggerWorker(session_mgr=None, interval_sec=5.0)
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
