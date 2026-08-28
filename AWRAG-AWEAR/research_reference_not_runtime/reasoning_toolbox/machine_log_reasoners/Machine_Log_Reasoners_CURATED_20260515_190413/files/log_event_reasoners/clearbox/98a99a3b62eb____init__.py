"""
visual_io operators — VectorOperator and EntropyOperator.

Both extend wolf_engine WolfModule (category="operator").
They receive a ScreenVectorState dict and return a detection dict or None.
"""

from __future__ import annotations

from typing import Any

from wolf_engine.modules.base import WolfModule
from visual_io.config import (
    ENTROPY_SPIKE_THRESHOLD, SYMMETRY_BREAK_THRESHOLD, VECTOR_ANOMALY_MIN_DIRS,
)


class VectorOperator(WolfModule):
    """Detects directional anomalies from ScreenVectorState ray data."""

    key = "op_vector_anomaly"
    name = "Vector Anomaly Operator"
    category = "operator"
    description = "Flags frames where multiple ray directions show high gradient change"

    def analyze(self, state: dict[str, Any]) -> dict[str, Any] | None:
        rays = state.get("rays", {})
        high_dirs = [d for d, v in rays.items() if v.get("gradient_change", 0) > 0.5]
        if len(high_dirs) >= VECTOR_ANOMALY_MIN_DIRS:
            return {
                "operator": self.key,
                "frame_id": state.get("frame_id"),
                "t_sec":    state.get("t_sec"),
                "anomaly":  "VECTOR_ANOMALY",
                "high_gradient_directions": high_dirs,
                "count": len(high_dirs),
                "confidence": min(len(high_dirs) / 8.0, 1.0),
            }
        return None

    def info(self) -> dict[str, Any]:
        return {"key": self.key, "name": self.name,
                "category": self.category, "description": self.description}


class EntropyOperator(WolfModule):
    """Flags entropy spikes and symmetry breaks in the visual field."""

    key = "op_entropy_spike"
    name = "Entropy Spike Operator"
    category = "operator"
    description = "Detects sudden entropy spikes or symmetry breaks — visual chaos events"

    def analyze(self, state: dict[str, Any]) -> dict[str, Any] | None:
        metrics = state.get("anomaly_metrics", {})
        flags = metrics.get("anomaly_flags", [])
        if not flags:
            return None
        return {
            "operator":    self.key,
            "frame_id":    state.get("frame_id"),
            "t_sec":       state.get("t_sec"),
            "anomaly":     "ENTROPY_OR_SYMMETRY_EVENT",
            "flags":       flags,
            "entropy":     metrics.get("global_entropy"),
            "h_symmetry":  metrics.get("h_symmetry"),
            "v_symmetry":  metrics.get("v_symmetry"),
            "confidence":  len(flags) / 3.0,
        }

    def info(self) -> dict[str, Any]:
        return {"key": self.key, "name": self.name,
                "category": self.category, "description": self.description}
