"""Crosshair Lock Operator — detects aim manipulation via center-region analysis.

Ported from unzipped_cleanup/crosshair_lock_simple.py.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from wolf_engine.modules.base import WolfModule
from wolf_engine.modules.truevision import (
    FrameGrid,
    FrameSequence,
    ManipulationFlags,
    OperatorResult,
)

logger = logging.getLogger(__name__)


class CrosshairLockOperator:
    """Tracks crosshair-to-enemy physics using center 20x20 pixel region."""

    def __init__(self, config: Dict[str, Any]):
        op = config.get("operators", {}).get("crosshair_lock", {})
        self.center_region_size = 20
        self.enemy_palette_min = op.get("enemy_palette_min", 7)
        self.enemy_palette_max = op.get("enemy_palette_max", 9)
        self.hit_marker_palette = op.get("hit_marker_palette", 9)
        self.enemy_threshold = op.get("enemy_threshold", 0.05)

    def _get_center_pixels(self, h: int, w: int) -> List[tuple]:
        half = self.center_region_size // 2
        cy, cx = h // 2, w // 2
        return [
            (y, x)
            for y in range(cy - half, cy + half)
            for x in range(cx - half, cx + half)
            if 0 <= y < h and 0 <= x < w
        ]

    def _detect_enemy(self, grid, pixels) -> tuple:
        count = sum(
            1 for y, x in pixels
            if self.enemy_palette_min <= grid[y][x] <= self.enemy_palette_max
        )
        ratio = count / len(pixels) if pixels else 0.0
        return ratio >= self.enemy_threshold, ratio

    def _detect_hit_marker(self, grid, pixels) -> bool:
        count = sum(1 for y, x in pixels if grid[y][x] == self.hit_marker_palette)
        return (count / len(pixels) if pixels else 0.0) >= 0.10

    def analyze(self, seq: FrameSequence) -> Optional[OperatorResult]:
        if not seq.frames:
            return None

        h, w = seq.frames[0].h, seq.frames[0].w
        center_pixels = self._get_center_pixels(h, w)

        on_target = []
        hit_markers = []
        enemy_ratios = []

        for frame in seq.frames:
            detected, ratio = self._detect_enemy(frame.grid, center_pixels)
            on_target.append(detected)
            enemy_ratios.append(ratio)
            hit_markers.append(self._detect_hit_marker(frame.grid, center_pixels))

        total = len(seq.frames)
        on_count = sum(on_target)
        hit_count = sum(hit_markers)
        intersection = on_count / total if total else 0.0
        efficiency = hit_count / on_count if on_count else 0.0

        anomaly = 0.0
        if on_count >= 3:
            if efficiency < 0.2:
                anomaly = (0.2 - efficiency) / 0.2
            elif efficiency > 0.6:
                anomaly = (efficiency - 0.6) / 0.4

        flags = []
        if anomaly > 0.5:
            flags.append(ManipulationFlags.HITBOX_DRIFT)

        return OperatorResult(
            operator_name="crosshair_lock",
            confidence=min(1.0, anomaly),
            flags=flags,
            metrics={
                "on_target_frames": on_count,
                "hit_marker_frames": hit_count,
                "intersection_ratio": intersection,
                "hit_efficiency": efficiency,
                "avg_enemy_ratio": sum(enemy_ratios) / len(enemy_ratios) if enemy_ratios else 0.0,
            },
            metadata={"frames_analyzed": total},
        )


class CrosshairLockModule(WolfModule):
    """WolfModule wrapper for CrosshairLock operator."""

    key = "op_crosshair_lock"
    name = "Crosshair Lock"
    category = "operator"
    description = "Detects crosshair lock-on patterns in frame sequences"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._operator = CrosshairLockOperator(self._config)

    def analyze(self, seq: FrameSequence) -> Optional[OperatorResult]:
        return self._operator.analyze(seq)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "center_region": self._operator.center_region_size,
        }
