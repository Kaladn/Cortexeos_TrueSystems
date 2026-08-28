"""
Evidence Worker Base — Abstract base for telemetry capture workers.

Each worker runs in its own thread, emits EvidenceEvents as JSONL to a
session-scoped output file. Includes write_safe() retry pattern adapted
from unzipped_cleanup/logger_common.py.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from wolf_engine.evidence.session_manager import EvidenceSessionManager
from wolf_engine.evidence.timebase import EvidenceEvent, Timestamp

logger = logging.getLogger(__name__)

# Max retries for write_safe (from logger_common.py pattern)
_MAX_WRITE_RETRIES = 3
_RETRY_BASE_WAIT = 0.1


def write_safe(path: str, data: dict, max_retries: int = _MAX_WRITE_RETRIES) -> bool:
    """
    Append a JSON line to a file with retry on failure.

    Adapted from unzipped_cleanup/logger_common.py write_safe().
    Returns True on success.
    """
    line = json.dumps(data, default=str) + "\n"
    for attempt in range(max_retries):
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
            return True
        except OSError as exc:
            if attempt < max_retries - 1:
                wait = _RETRY_BASE_WAIT * (2 ** attempt)
                logger.warning("write_safe retry %d for %s: %s", attempt + 1, path, exc)
                time.sleep(wait)
            else:
                logger.error("write_safe failed after %d retries for %s: %s", max_retries, path, exc)
    return False


class WorkerBase(ABC):
    """
    Abstract base class for evidence telemetry workers.

    Subclasses implement collect() which returns data dicts.
    The base handles threading, JSONL output, and lifecycle.
    """

    # Subclasses should set this
    worker_name: str = "unnamed_worker"

    def __init__(
        self,
        session_mgr: EvidenceSessionManager,
        interval_sec: float = 5.0,
    ):
        self.session_mgr = session_mgr
        self.interval_sec = interval_sec
        self._running = False
        self._thread: threading.Thread | None = None
        self._output_path: str = ""
        self._event_count = 0

    @abstractmethod
    def collect(self) -> list[dict[str, Any]]:
        """
        Collect telemetry data points.

        Returns a list of dicts, each becoming one EvidenceEvent.
        Each dict should have at minimum:
            {"event_type": "...", ...other data fields...}
        """
        ...

    def start(self) -> None:
        """Start the worker's collection thread."""
        session = self.session_mgr.active_session
        if session is None:
            raise RuntimeError(f"{self.worker_name}: No active session to attach to")

        self.session_mgr.register_worker(self.worker_name)
        self._output_path = self.session_mgr.get_output_path(self.worker_name)
        self._running = True
        self._event_count = 0
        self._thread = threading.Thread(
            target=self._loop, name=f"worker-{self.worker_name}", daemon=True
        )
        self._thread.start()
        logger.info("%s started, writing to %s", self.worker_name, self._output_path)

    def stop(self) -> int:
        """Stop the worker. Returns total events emitted."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=self.interval_sec + 2)
        logger.info("%s stopped, %d events emitted", self.worker_name, self._event_count)
        return self._event_count

    def _loop(self) -> None:
        while self._running:
            try:
                data_points = self.collect()
                for dp in data_points:
                    event = EvidenceEvent(
                        worker=self.worker_name,
                        event_type=dp.pop("event_type", "unknown"),
                        timestamp=Timestamp(node_id=self.session_mgr.node_id),
                        data=dp,
                        session_id=self.session_mgr.active_session.session_id
                        if self.session_mgr.active_session
                        else "",
                    )
                    if write_safe(self._output_path, event.to_dict()):
                        self._event_count += 1
                        self.session_mgr.record_event()
            except Exception as exc:
                logger.error("%s collection error: %s", self.worker_name, exc)
            time.sleep(self.interval_sec)

    @property
    def event_count(self) -> int:
        return self._event_count

    @property
    def is_running(self) -> bool:
        return self._running
