"""
Causal Alignment Matrix (CAM) — Dormant stub.

Activates when a second reasoning engine is added to the cluster.
Scores cross-engine agreement on the same input to detect divergence
and build consensus.

Currently single-engine: all methods return neutral/pass-through values.
The interface is pre-built so adding a second engine requires only
implementing the comparison logic, not restructuring Archon.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from wolf_engine.archon.schemas import EngineResponse

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AlignmentScore:
    """Cross-engine alignment result (dormant — always returns 1.0)."""

    engine_a: str = "primary"
    engine_b: str = "none"
    agreement: float = 1.0       # 1.0 = perfect agreement (only one engine)
    divergence_points: list[str] = field(default_factory=list)
    active: bool = False         # True when second engine is registered


class CausalAlignmentMatrix:
    """
    Dormant CAM — activates with second engine registration.

    Interface:
        register_engine(name) — Add a second engine
        compare(response_a, response_b) — Score agreement
        is_active — Whether multi-engine mode is on
    """

    def __init__(self):
        self._engines: list[str] = ["primary"]
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def register_engine(self, name: str) -> None:
        """Register a second engine. Activates CAM."""
        if name not in self._engines:
            self._engines.append(name)
            self._active = len(self._engines) > 1
            logger.info("CAM: Engine '%s' registered. Active: %s", name, self._active)

    def compare(
        self,
        response_a: EngineResponse,
        response_b: EngineResponse | None = None,
    ) -> AlignmentScore:
        """
        Compare two engine responses for agreement.

        Single-engine mode: returns perfect agreement (1.0).
        Multi-engine mode: compares confidence, consistency, and pattern counts.
        """
        if not self._active or response_b is None:
            return AlignmentScore(active=False)

        # Multi-engine comparison (activated when second engine exists)
        divergence_points = []
        conf_delta = abs(response_a.confidence - response_b.confidence)
        cons_delta = abs(response_a.avg_consistency - response_b.avg_consistency)

        if conf_delta > 0.3:
            divergence_points.append(
                f"confidence_gap: {conf_delta:.2f}"
            )
        if cons_delta > 0.3:
            divergence_points.append(
                f"consistency_gap: {cons_delta:.2f}"
            )
        if response_a.pattern_breaks != response_b.pattern_breaks:
            divergence_points.append(
                f"break_count: {response_a.pattern_breaks} vs {response_b.pattern_breaks}"
            )

        agreement = 1.0 - (conf_delta + cons_delta) / 2.0
        agreement = max(0.0, min(1.0, agreement))

        return AlignmentScore(
            engine_a=self._engines[0] if self._engines else "primary",
            engine_b=self._engines[1] if len(self._engines) > 1 else "none",
            agreement=agreement,
            divergence_points=divergence_points,
            active=True,
        )
