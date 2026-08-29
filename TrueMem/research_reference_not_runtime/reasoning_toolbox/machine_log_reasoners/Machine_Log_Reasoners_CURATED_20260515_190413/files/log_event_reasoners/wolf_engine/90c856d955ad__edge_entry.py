"""Edge Entry Operator — detects spawn manipulation at screen edges.

Ported from unzipped_cleanup/edge_entry.py.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from wolf_engine.modules.base import WolfModule
from wolf_engine.modules.truevision import (
    FrameSequence,
    ManipulationFlags,
    OperatorResult,
)

logger = logging.getLogger(__name__)


class EdgeEntryOperator:
    """Tracks enemy entries at screen edges to detect spawn manipulation."""

    def __init__(self, config: Dict[str, Any]):
        op = config.get("operators", {}).get("edge_entry", {})
        self.edge_width = op.get("edge_width", 0.15)
        self.enemy_palette_min = op.get("enemy_palette_min", 5)
        self.enemy_palette_max = op.get("enemy_palette_max", 9)
        self.entry_threshold = op.get("entry_threshold", 0.05)
        self.rear_spawn_threshold = op.get("rear_spawn_threshold", 0.4)

    def _get_edge_regions(self, h: int, w: int) -> Dict[str, List[tuple]]:
        eh = int(h * self.edge_width)
        ew = int(w * self.edge_width)
        return {
            "rear": [(y, x) for y in range(eh) for x in range(w)],
            "front": [(y, x) for y in range(h - eh, h) for x in range(w)],
            "left": [(y, x) for y in range(eh, h - eh) for x in range(ew)],
            "right": [(y, x) for y in range(eh, h - eh) for x in range(w - ew, w)],
        }

    def _count_enemy(self, grid, cells) -> int:
        return sum(
            1 for y, x in cells
            if self.enemy_palette_min <= grid[y][x] <= self.enemy_palette_max
        )

    def analyze(self, seq: FrameSequence) -> Optional[OperatorResult]:
        if len(seq.frames) < 2:
            return None

        h, w = seq.frames[0].h, seq.frames[0].w
        regions = self._get_edge_regions(h, w)

        entries: Dict[str, int] = {"front": 0, "rear": 0, "left": 0, "right": 0}

        for i in range(1, len(seq.frames)):
            prev_grid = seq.frames[i - 1].grid
            curr_grid = seq.frames[i].grid
            for name, cells in regions.items():
                if not cells:
                    continue
                prev_count = self._count_enemy(prev_grid, cells)
                curr_count = self._count_enemy(curr_grid, cells)
                increase = (curr_count - prev_count) / len(cells) if cells else 0
                if increase > self.entry_threshold:
                    entries[name] += 1

        total_entries = sum(entries.values())
        duration = seq.t_end - seq.t_start if seq.t_end > seq.t_start else 1.0
        entry_rate = total_entries / duration
        rear_ratio = entries["rear"] / total_entries if total_entries else 0.0

        flags = []
        if rear_ratio > self.rear_spawn_threshold:
            flags.append(ManipulationFlags.SPAWN_PRESSURE)

        confidence = min(1.0, rear_ratio / self.rear_spawn_threshold) if total_entries > 0 else 0.0

        return OperatorResult(
            operator_name="edge_entry",
            confidence=confidence,
            flags=flags,
            metrics={
                "total_entries": total_entries,
                "entry_rate": round(entry_rate, 2),
                "rear_ratio": round(rear_ratio, 3),
                "entries_by_region": entries,
            },
            metadata={"frames_analyzed": len(seq.frames)},
        )


class EdgeEntryModule(WolfModule):
    """WolfModule wrapper for EdgeEntry operator."""

    key = "op_edge_entry"
    name = "Edge Entry"
    category = "operator"
    description = "Detects enemy spawn/entry patterns at screen edges"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._operator = EdgeEntryOperator(self._config)

    def analyze(self, seq: FrameSequence) -> Optional[OperatorResult]:
        return self._operator.analyze(seq)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "edge_width": self._operator.edge_width,
        }
