"""EOMM Compositor — aggregates operator results into unified telemetry.

Ported from unzipped_cleanup/eomm_compositor.py.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from wolf_engine.modules.base import WolfModule
from wolf_engine.modules.truevision import (
    ManipulationFlags,
    OperatorResult,
    TelemetryWindow,
)

logger = logging.getLogger(__name__)


class EommCompositor:
    """Combines all operator results into a unified TelemetryWindow."""

    def __init__(self, config: Dict[str, Any]):
        eomm = config.get("eomm_composite", {})
        self.operator_weights = eomm.get("operator_weights", {
            "crosshair_lock": 0.3,
            "hit_registration": 0.3,
            "death_event": 0.25,
            "edge_entry": 0.15,
        })
        self.manipulation_threshold = eomm.get("manipulation_threshold", 0.5)

    def _composite_score(self, results: List[OperatorResult]) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for r in results:
            w = self.operator_weights.get(r.operator_name, 0.1)
            weighted_sum += r.confidence * w
            total_weight += w
        return weighted_sum / total_weight if total_weight else 0.0

    def _aggregate_flags(self, results: List[OperatorResult]) -> List[ManipulationFlags]:
        seen = set()
        flags = []
        for r in results:
            for f in r.flags:
                if f not in seen:
                    seen.add(f)
                    flags.append(f)
        return flags

    def compose_window(
        self,
        operator_results: List[OperatorResult],
        window_start: float,
        window_end: float,
        session_id: str = "",
        frame_count: int = 0,
    ) -> TelemetryWindow:
        score = self._composite_score(operator_results)
        flags = self._aggregate_flags(operator_results)
        return TelemetryWindow(
            window_start_epoch=window_start,
            window_end_epoch=window_end,
            session_id=session_id,
            frame_count=frame_count,
            composite_score=score,
            operator_results=operator_results,
            flags=flags,
            metadata={
                "manipulation_detected": score >= self.manipulation_threshold,
                "operator_count": len(operator_results),
            },
        )


class EommModule(WolfModule):
    """WolfModule wrapper for EOMM Compositor."""

    key = "op_eomm"
    name = "EOMM Compositor"
    category = "operator"
    description = "Aggregates operator results into unified telemetry window"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._compositor = EommCompositor(self._config)

    def compose_window(self, results, window_start, window_end, **kwargs):
        return self._compositor.compose_window(results, window_start, window_end, **kwargs)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "operator_weights": self._compositor.operator_weights,
        }
