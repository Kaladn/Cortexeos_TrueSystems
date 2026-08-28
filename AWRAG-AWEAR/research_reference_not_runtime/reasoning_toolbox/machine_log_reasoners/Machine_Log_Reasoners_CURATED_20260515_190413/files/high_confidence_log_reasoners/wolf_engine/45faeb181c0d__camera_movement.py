"""Camera Movement Logger — detects camera turns via velocity buffer.

Ported from unzipped_cleanup/camera_movement_logger.py.
Requires numpy for velocity analysis.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from wolf_engine.modules.base import WolfModule

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None


@dataclass
class CameraMovement:
    """Detected camera movement event."""
    timestamp: str = ""
    epoch: float = 0.0
    camera_angle: float = 0.0
    camera_speed: float = 0.0
    angle_change: float = 0.0
    movement_detected: bool = False


class CameraMovementLogger:
    """Detects camera movement toward threats using velocity buffer analysis."""

    def __init__(self, logs_dir: Optional[str] = None):
        self.logs_dir = Path(logs_dir) if logs_dir else Path("logs/camera_movement")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._prev_angle: Optional[float] = None
        self.event_count = 0

    def analyze_frame(self, velocity_buffer, frame_timestamp: float,
                      frame_h: int = 0, frame_w: int = 0) -> Optional[CameraMovement]:
        if np is None or velocity_buffer is None:
            return None

        vb = np.asarray(velocity_buffer, dtype=float)
        if vb.size == 0:
            return None

        # Camera angle from mean horizontal velocity
        h_vel = float(np.mean(vb[:, 0])) if vb.ndim >= 2 and vb.shape[1] >= 1 else float(np.mean(vb))
        v_vel = float(np.mean(vb[:, 1])) if vb.ndim >= 2 and vb.shape[1] >= 2 else 0.0

        angle = float(np.degrees(np.arctan2(v_vel, h_vel))) % 360
        speed = float(np.sqrt(h_vel ** 2 + v_vel ** 2))
        angle_change = 0.0
        if self._prev_angle is not None:
            delta = angle - self._prev_angle
            angle_change = (delta + 180) % 360 - 180
        self._prev_angle = angle

        detected = abs(angle_change) > 5.0 and speed > 2.0
        if detected:
            self.event_count += 1

        now = datetime.fromtimestamp(frame_timestamp)
        return CameraMovement(
            timestamp=now.isoformat(),
            epoch=frame_timestamp,
            camera_angle=round(angle, 2),
            camera_speed=round(speed, 2),
            angle_change=round(angle_change, 2),
            movement_detected=detected,
        )

    def log_event(self, movement: CameraMovement) -> None:
        date_str = datetime.fromtimestamp(movement.epoch).strftime("%Y%m%d")
        log_file = self.logs_dir / f"camera_movement_{date_str}.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(movement), default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to write camera movement log: %s", e)


class CameraMovementModule(WolfModule):
    """WolfModule wrapper for Camera Movement Logger."""

    key = "log_camera_movement"
    name = "Camera Movement"
    category = "logger"
    description = "Camera direction, speed, snap detection"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        logs_dir = self._config.get("logs_dir", None)
        self._logger = CameraMovementLogger(logs_dir=logs_dir)

    def analyze_frame(self, velocity_buffer, timestamp: float, **kwargs):
        return self._logger.analyze_frame(velocity_buffer, timestamp, **kwargs)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "events": self._logger.event_count,
            "numpy_available": np is not None,
        }
