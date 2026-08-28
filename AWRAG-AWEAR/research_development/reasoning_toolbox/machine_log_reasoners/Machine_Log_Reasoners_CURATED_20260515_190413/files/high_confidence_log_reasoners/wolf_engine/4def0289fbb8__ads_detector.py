"""ADS Detector Logger — detects aim-down-sights via FOV and scope analysis.

Ported from unzipped_cleanup/ads_detector_logger.py.
Requires numpy for frame analysis.
"""

from __future__ import annotations

import json
import logging
import time
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
class ADSEvent:
    """Detected ADS event."""
    timestamp: str = ""
    epoch: float = 0.0
    ads_active: bool = False
    detection_method: str = ""
    confidence: float = 0.0
    fov_ratio: float = 0.0
    scope_pixels: int = 0


class ADSDetectorLogger:
    """Detects ADS using FOV change and scope overlay detection."""

    def __init__(self, logs_dir: Optional[str] = None):
        self.logs_dir = Path(logs_dir) if logs_dir else Path("logs/ads_detection")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._prev_fov_ratio: Optional[float] = None
        self.event_count = 0

    def _detect_fov_change(self, frame) -> Tuple[bool, float]:
        """Detect FOV narrowing by comparing edge vs center variance."""
        if np is None or frame is None:
            return False, 0.0

        arr = np.asarray(frame, dtype=float)
        if arr.ndim < 2:
            return False, 0.0

        h, w = arr.shape[:2]
        edge_size = max(1, min(h, w) // 8)

        # Edge region variance
        edges = np.concatenate([
            arr[:edge_size].flatten(),
            arr[-edge_size:].flatten(),
            arr[edge_size:-edge_size, :edge_size].flatten(),
            arr[edge_size:-edge_size, -edge_size:].flatten(),
        ])
        center = arr[h // 4: 3 * h // 4, w // 4: 3 * w // 4].flatten()

        edge_var = float(np.var(edges)) if edges.size else 1.0
        center_var = float(np.var(center)) if center.size else 1.0
        ratio = edge_var / center_var if center_var > 0 else 1.0

        # Low edge/center ratio = ADS (edges dark, center detailed)
        ads_detected = ratio < 0.3
        return ads_detected, round(ratio, 4)

    def _detect_scope_overlay(self, frame) -> Tuple[bool, int]:
        """Detect scope vignette (black pixels in corners)."""
        if np is None or frame is None:
            return False, 0

        arr = np.asarray(frame, dtype=float)
        if arr.ndim < 2:
            return False, 0

        h, w = arr.shape[:2]
        corner = max(1, min(h, w) // 10)

        corners = np.concatenate([
            arr[:corner, :corner].flatten(),
            arr[:corner, -corner:].flatten(),
            arr[-corner:, :corner].flatten(),
            arr[-corner:, -corner:].flatten(),
        ])

        black_thresh = 10.0
        black_count = int(np.sum(corners < black_thresh))
        total = corners.size
        scope_detected = (black_count / total) > 0.5 if total else False
        return scope_detected, black_count

    def analyze_frame(self, frame, frame_timestamp: float) -> Optional[ADSEvent]:
        if np is None or frame is None:
            return None

        fov_detected, fov_ratio = self._detect_fov_change(frame)
        scope_detected, scope_pixels = self._detect_scope_overlay(frame)

        if not fov_detected and not scope_detected:
            return None

        method = "both" if fov_detected and scope_detected else ("fov_change" if fov_detected else "scope_overlay")
        confidence = 0.9 if method == "both" else 0.6

        self.event_count += 1
        now = datetime.fromtimestamp(frame_timestamp)
        return ADSEvent(
            timestamp=now.isoformat(),
            epoch=frame_timestamp,
            ads_active=True,
            detection_method=method,
            confidence=confidence,
            fov_ratio=fov_ratio,
            scope_pixels=scope_pixels,
        )

    def log_event(self, event: ADSEvent) -> None:
        date_str = datetime.fromtimestamp(event.epoch).strftime("%Y%m%d")
        log_file = self.logs_dir / f"ads_detection_{date_str}.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event), default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to write ADS log: %s", e)


class AdsDetectorModule(WolfModule):
    """WolfModule wrapper for ADS Detector Logger."""

    key = "log_ads_detector"
    name = "ADS Detector"
    category = "logger"
    description = "FOV ratio and scope state tracking"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        logs_dir = self._config.get("logs_dir", None)
        self._detector = ADSDetectorLogger(logs_dir=logs_dir)

    def analyze_frame(self, frame, timestamp: float):
        return self._detector.analyze_frame(frame, timestamp)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "events": self._detector.event_count,
            "numpy_available": np is not None,
        }
