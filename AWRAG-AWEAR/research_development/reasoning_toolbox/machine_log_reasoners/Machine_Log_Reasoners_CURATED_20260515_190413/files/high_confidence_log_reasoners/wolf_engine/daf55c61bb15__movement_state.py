"""Movement State Logger — tracks player movement and stance.

Ported from unzipped_cleanup/movement_state_logger.py.
Requires numpy for velocity and frame analysis.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from wolf_engine.modules.base import WolfModule

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None


class MovementSpeed(Enum):
    STATIONARY = "stationary"
    WALKING = "walking"
    SPRINTING = "sprinting"


class Stance(Enum):
    STANDING = "standing"
    CROUCHING = "crouching"
    PRONE = "prone"


@dataclass
class MovementEvent:
    """Detected movement state."""
    timestamp: str = ""
    epoch: float = 0.0
    movement_state: str = "stationary"
    movement_speed: float = 0.0
    ground_ratio: float = 0.0
    stance: str = "standing"


class MovementStateLogger:
    """Tracks player movement state and stance."""

    def __init__(self, logs_dir: Optional[str] = None):
        self.logs_dir = Path(logs_dir) if logs_dir else Path("logs/movement_state")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.event_count = 0

    def _detect_speed(self, velocity_buffer) -> float:
        """Edge velocity analysis → pixels/frame."""
        if np is None or velocity_buffer is None:
            return 0.0
        vb = np.asarray(velocity_buffer, dtype=float)
        if vb.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(vb ** 2)))

    def _detect_ground_ratio(self, frame) -> float:
        """Estimate how much of the lower frame is ground (for stance)."""
        if np is None or frame is None:
            return 0.5
        arr = np.asarray(frame, dtype=float)
        if arr.ndim < 2:
            return 0.5
        h = arr.shape[0]
        lower_half = arr[h // 2:]
        if lower_half.size == 0:
            return 0.5
        # Darker pixels (ground/terrain) tend to have lower variance
        mean_val = float(np.mean(lower_half))
        return min(1.0, max(0.0, mean_val / 255.0))

    def _classify_speed(self, speed: float) -> MovementSpeed:
        if speed < 5.0:
            return MovementSpeed.STATIONARY
        elif speed < 20.0:
            return MovementSpeed.WALKING
        return MovementSpeed.SPRINTING

    def _classify_stance(self, ground_ratio: float) -> Stance:
        if ground_ratio > 0.75:
            return Stance.PRONE
        elif ground_ratio > 0.6:
            return Stance.CROUCHING
        return Stance.STANDING

    def analyze_frame(self, frame, velocity_buffer,
                      frame_timestamp: float) -> Optional[MovementEvent]:
        if np is None:
            return None

        speed = self._detect_speed(velocity_buffer)
        ground_ratio = self._detect_ground_ratio(frame)
        state = self._classify_speed(speed)
        stance = self._classify_stance(ground_ratio)

        self.event_count += 1
        now = datetime.fromtimestamp(frame_timestamp)
        return MovementEvent(
            timestamp=now.isoformat(),
            epoch=frame_timestamp,
            movement_state=state.value,
            movement_speed=round(speed, 2),
            ground_ratio=round(ground_ratio, 3),
            stance=stance.value,
        )

    def log_event(self, event: MovementEvent) -> None:
        date_str = datetime.fromtimestamp(event.epoch).strftime("%Y%m%d")
        log_file = self.logs_dir / f"movement_state_{date_str}.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event), default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to write movement state log: %s", e)


class MovementStateModule(WolfModule):
    """WolfModule wrapper for Movement State Logger."""

    key = "log_movement_state"
    name = "Movement State"
    category = "logger"
    description = "Velocity, stance, and movement state tracking"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        logs_dir = self._config.get("logs_dir", None)
        self._logger = MovementStateLogger(logs_dir=logs_dir)

    def analyze_frame(self, frame, velocity_buffer, timestamp: float):
        return self._logger.analyze_frame(frame, velocity_buffer, timestamp)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "events": self._logger.event_count,
            "numpy_available": np is not None,
        }
