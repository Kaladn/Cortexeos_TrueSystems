"""
Evidence Session Manager — Lifecycle for telemetry capture sessions.

A session records identity and lifecycle metadata under one ID.
Sessions are created with start() and finalized with stop().

Adapted from unzipped_cleanup/session_manager.py. Rewired to use
wolf_engine contracts and SQLiteWriter for persistence.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SessionInfo:
    """Active session metadata."""

    session_id: str = ""
    label: str = ""
    start_time: float = 0.0
    end_time: float | None = None
    node_id: str = ""
    session_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "label": self.label,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "node_id": self.node_id,
            "session_dir": self.session_dir,
        }


class EvidenceSessionManager:
    """Manages evidence capture sessions with JSONL output directories."""

    def __init__(self, base_dir: str, node_id: str = "node_0"):
        self.base_dir = Path(base_dir)
        self.node_id = node_id
        self._active: SessionInfo | None = None

    @property
    def active_session(self) -> SessionInfo | None:
        return self._active

    def start(self, label: str = "") -> SessionInfo:
        """Start a new evidence session. Returns SessionInfo."""
        if self._active is not None:
            logger.warning("Session %s still active, finalizing first", self._active.session_id)
            self.stop()

        session_id = str(uuid.uuid4())
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        info = SessionInfo(
            session_id=session_id,
            label=label or f"session_{int(time.time())}",
            start_time=time.time(),
            node_id=self.node_id,
            session_dir=str(session_dir),
        )
        self._active = info

        # Write session manifest
        manifest_path = session_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(info.to_dict(), indent=2), encoding="utf-8"
        )

        logger.info("Evidence session started: %s (%s)", session_id, label)
        return info

    def stop(self) -> SessionInfo | None:
        """Finalize the active session. Returns the completed SessionInfo."""
        if self._active is None:
            return None

        self._active.end_time = time.time()
        info = self._active

        # Update manifest
        manifest_path = Path(info.session_dir) / "manifest.json"
        manifest_path.write_text(
            json.dumps(info.to_dict(), indent=2), encoding="utf-8"
        )

        logger.info("Session %s finalized", info.session_id)

        self._active = None
        return info

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions by reading manifests from base_dir."""
        sessions = []
        if not self.base_dir.exists():
            return sessions
        for entry in sorted(self.base_dir.iterdir()):
            manifest = entry / "manifest.json"
            if manifest.exists():
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    sessions.append(data)
                except (json.JSONDecodeError, OSError):
                    continue
        return sessions
