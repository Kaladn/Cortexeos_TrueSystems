"""Thermal Hitbox Analyzer — detects hitbox manipulation via thermal buffer.

Ported from unzipped_cleanup/thermal_hitbox_analyzer.py.
Requires numpy for thermal data processing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from wolf_engine.modules.base import WolfModule
from wolf_engine.modules.truevision import (
    FrameGrid,
    FrameSequence,
    ManipulationFlags,
    OperatorResult,
)

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None


@dataclass
class ThermalBlob:
    """Detected thermal signature blob."""
    center_x: int = 0
    center_y: int = 0
    pixel_count: int = 0
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0)
    max_intensity: float = 0.0
    avg_intensity: float = 0.0
    distance_meters: Optional[float] = None
    normalized_diameter: Optional[float] = None


class ThermalHitboxAnalyzer:
    """Analyzes thermal buffer to measure enemy hitbox sizes."""

    def __init__(self, config: Dict[str, Any]):
        op = config.get("operators", {}).get("thermal_hitbox_analyzer", {})
        self.thermal_threshold = op.get("thermal_threshold", 0.3)
        self.min_blob_size = op.get("min_blob_size", 100)
        self.max_blob_size = op.get("max_blob_size", 50000)
        self.reference_distance = op.get("reference_distance", 50.0)
        self.expected_hitbox_size = op.get("expected_hitbox_size", 2000)
        self.manipulation_threshold = op.get("manipulation_threshold", 1.5)
        self.crosshair_region_radius = op.get("crosshair_region_radius", 200)

    def _detect_blobs(self, thermal: Any, depth: Any,
                      cx: int, cy: int) -> List[ThermalBlob]:
        if np is None or thermal is None:
            return []

        h, w = thermal.shape
        visited = np.zeros((h, w), dtype=bool)
        hot = thermal > self.thermal_threshold
        blobs = []

        def flood(sy, sx):
            stack = [(sy, sx)]
            pixels = []
            intensities = []
            while stack:
                y, x = stack.pop()
                if y < 0 or y >= h or x < 0 or x >= w:
                    continue
                if visited[y, x] or not hot[y, x]:
                    continue
                visited[y, x] = True
                pixels.append((y, x))
                intensities.append(float(thermal[y, x]))
                stack.extend([(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)])

            if len(pixels) < self.min_blob_size or len(pixels) > self.max_blob_size:
                return None
            ys, xs = zip(*pixels)
            bcx, bcy = int(np.mean(xs)), int(np.mean(ys))
            if np.sqrt((bcx - cx) ** 2 + (bcy - cy) ** 2) > self.crosshair_region_radius:
                return None
            dist = float(depth[bcy, bcx]) if depth is not None else None
            norm = len(pixels) * (dist / self.reference_distance) ** 2 if dist and dist > 0 else None
            return ThermalBlob(
                center_x=bcx, center_y=bcy, pixel_count=len(pixels),
                bounding_box=(min(xs), min(ys), max(xs), max(ys)),
                max_intensity=max(intensities), avg_intensity=float(np.mean(intensities)),
                distance_meters=dist, normalized_diameter=norm,
            )

        for y in range(h):
            for x in range(w):
                if not visited[y, x] and hot[y, x]:
                    blob = flood(y, x)
                    if blob is not None:
                        blobs.append(blob)
        return blobs

    def _manipulation_score(self, blob: ThermalBlob) -> float:
        size = blob.normalized_diameter if blob.normalized_diameter else blob.pixel_count
        ratio = size / self.expected_hitbox_size
        if ratio > 1.0:
            score = (ratio - 1.0) / (self.manipulation_threshold - 1.0)
        else:
            score = (1.0 - ratio) / (1.0 - (1.0 / self.manipulation_threshold))
        return min(1.0, score)

    def analyze(self, seq: FrameSequence) -> Optional[OperatorResult]:
        if not seq.frames or np is None:
            return None

        h, w = seq.frames[0].h, seq.frames[0].w
        cx, cy = w // 2, h // 2
        all_blobs: List[ThermalBlob] = []

        for frame in seq.frames:
            thermal = getattr(frame, "thermal_buffer", None)
            depth = getattr(frame, "depth_buffer", None)
            if thermal is not None:
                all_blobs.extend(self._detect_blobs(thermal, depth, cx, cy))

        if not all_blobs:
            return None

        scores = [self._manipulation_score(b) for b in all_blobs]
        raw_sizes = [b.pixel_count for b in all_blobs]

        flags = []
        norm_sizes = [b.normalized_diameter for b in all_blobs if b.normalized_diameter]
        if norm_sizes:
            avg_norm = float(np.mean(norm_sizes))
            if avg_norm > self.expected_hitbox_size * self.manipulation_threshold:
                flags.append(ManipulationFlags.HITBOX_DRIFT)
            if avg_norm < self.expected_hitbox_size / self.manipulation_threshold:
                flags.append(ManipulationFlags.HITBOX_DRIFT)

        return OperatorResult(
            operator_name="thermal_hitbox",
            confidence=min(1.0, max(scores)),
            flags=flags,
            metrics={
                "total_signatures": len(all_blobs),
                "avg_raw_size": float(np.mean(raw_sizes)),
                "avg_manipulation_score": float(np.mean(scores)),
                "max_manipulation_score": float(max(scores)),
            },
            metadata={"frames_analyzed": len(seq.frames)},
        )


class ThermalHitboxModule(WolfModule):
    """WolfModule wrapper for ThermalHitbox operator."""

    key = "op_thermal_hitbox"
    name = "Thermal Hitbox"
    category = "operator"
    description = "Analyzes thermal buffer for hitbox manipulation"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._analyzer = ThermalHitboxAnalyzer(self._config)

    def analyze(self, seq: FrameSequence) -> Optional[OperatorResult]:
        return self._analyzer.analyze(seq)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "numpy_available": np is not None,
        }
