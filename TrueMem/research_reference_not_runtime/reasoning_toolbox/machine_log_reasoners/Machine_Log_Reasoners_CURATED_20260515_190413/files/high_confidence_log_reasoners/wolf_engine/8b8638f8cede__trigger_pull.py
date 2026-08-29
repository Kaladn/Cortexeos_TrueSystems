"""Trigger Pull Logger — detects weapon firing via muzzle flash and recoil.

Ported from unzipped_cleanup/trigger_pull_logger.py.
Requires numpy for frame and velocity analysis.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from wolf_engine.modules.base import WolfModule

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None


@dataclass
class ShotEvent:
    """Detected shot/trigger pull event."""
    timestamp: str = ""
    epoch: float = 0.0
    shot_detected: bool = False
    detection_method: str = ""
    confidence: float = 0.0
    flash_intensity: float = 0.0
    shake_magnitude: float = 0.0


class TriggerPullLogger:
    """Detects weapon firing using muzzle flash and screen shake."""

    def __init__(self, logs_dir: Optional[str] = None):
        self.logs_dir = Path(logs_dir) if logs_dir else Path("logs/trigger_pull")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.event_count = 0

    def _detect_muzzle_flash(self, frame) -> Tuple[bool, float]:
        """Detect brightness spike in center-bottom of frame."""
        if np is None or frame is None:
            return False, 0.0

        arr = np.asarray(frame, dtype=float)
        if arr.ndim < 2:
            return False, 0.0

        h, w = arr.shape[:2]
        # Center-bottom region (bottom 20%, center 40%)
        region = arr[int(h * 0.8):, int(w * 0.3): int(w * 0.7)]
        if region.size == 0:
            return False, 0.0

        intensity = float(np.mean(region))
        flash = intensity > 200.0  # Brightness threshold
        return flash, round(intensity, 2)

    def _detect_screen_shake(self, velocity_buffer) -> Tuple[bool, float]:
        """Detect velocity spike from recoil."""
        if np is None or velocity_buffer is None:
            return False, 0.0

        vb = np.asarray(velocity_buffer, dtype=float)
        if vb.size == 0:
            return False, 0.0

        magnitude = float(np.sqrt(np.mean(vb ** 2)))
        shake = magnitude > 15.0  # Recoil threshold
        return shake, round(magnitude, 2)

    def analyze_frame(self, frame, velocity_buffer,
                      frame_timestamp: float) -> Optional[ShotEvent]:
        if np is None:
            return None

        flash_detected, flash_intensity = self._detect_muzzle_flash(frame)
        shake_detected, shake_magnitude = self._detect_screen_shake(velocity_buffer)

        if not flash_detected and not shake_detected:
            return None

        method = "both" if flash_detected and shake_detected else ("muzzle_flash" if flash_detected else "screen_shake")
        confidence = 0.95 if method == "both" else 0.6

        self.event_count += 1
        now = datetime.fromtimestamp(frame_timestamp)
        return ShotEvent(
            timestamp=now.isoformat(),
            epoch=frame_timestamp,
            shot_detected=True,
            detection_method=method,
            confidence=confidence,
            flash_intensity=flash_intensity,
            shake_magnitude=shake_magnitude,
        )

    def log_event(self, event: ShotEvent) -> None:
        date_str = datetime.fromtimestamp(event.epoch).strftime("%Y%m%d")
        log_file = self.logs_dir / f"trigger_pull_{date_str}.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event), default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to write trigger pull log: %s", e)


class TriggerPullModule(WolfModule):
    """WolfModule wrapper for Trigger Pull Logger."""

    key = "log_trigger_pull"
    name = "Trigger Pull"
    category = "logger"
    description = "Muzzle flash and trigger event logging"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        logs_dir = self._config.get("logs_dir", None)
        self._logger = TriggerPullLogger(logs_dir=logs_dir)

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
