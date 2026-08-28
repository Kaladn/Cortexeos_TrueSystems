"""
Causal Analyzer — Bidirectional validation of symbol sequences.

Generalized from unzipped_cleanup/causal_analyzer.py (finance-specific).
This version is domain-agnostic: it validates whether a center symbol
follows from its preceding context (backward) and whether the following
context follows from the center (forward).

Scoring uses ForgeMemory co-occurrence frequencies as the "expectation"
baseline. High consistency = the sequence matches established patterns.
Low consistency = potential pattern break or anomaly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.reasoning.engine import Window

logger = logging.getLogger(__name__)

_MIN_CONTEXT = 2  # Minimum context length for meaningful validation


@dataclass(slots=True)
class CausalResult:
    """Causal analysis result for a single window."""

    anchor_id: int = 0
    anchor_index: int = 0
    backward_score: float = 0.0   # How well anchor follows from preceding
    forward_score: float = 0.0    # How well following follows from anchor
    consistency: float = 0.0      # Combined bidirectional score (0-1)
    context_depth: int = 0        # How many context symbols were evaluated


class CausalAnalyzer:
    """
    Bidirectional causal validation using ForgeMemory co-occurrence.

    For each window:
      - Backward: Does the anchor symbol have strong co-occurrence
        with the preceding 6 symbols?
      - Forward: Do the following 6 symbols have strong co-occurrence
        with the anchor?
      - Consistency: Average of backward and forward scores.
    """

    def __init__(self, forge: ForgeMemory):
        self.forge = forge

    def analyze_window(self, window: Window) -> CausalResult:
        """Analyze a single 6-1-6 window for causal consistency."""
        backward = self._backward_score(window)
        forward = self._forward_score(window)

        context_depth = len(window.preceding) + len(window.following)
        if context_depth < _MIN_CONTEXT:
            consistency = 0.5  # Neutral when insufficient context
        else:
            consistency = (backward + forward) / 2.0

        return CausalResult(
            anchor_id=window.anchor_id,
            anchor_index=window.anchor_index,
            backward_score=backward,
            forward_score=forward,
            consistency=consistency,
            context_depth=context_depth,
        )

    def analyze_all(self, windows: list[Window]) -> list[CausalResult]:
        """Analyze all windows. Returns list of CausalResults in order."""
        return [self.analyze_window(w) for w in windows]

    def _backward_score(self, window: Window) -> float:
        """
        How well does the anchor follow from its preceding context?

        Score = average co-occurrence of (preceding[i], anchor) normalized
        by the maximum co-occurrence the anchor has with any symbol.
        """
        if not window.preceding:
            return 0.5

        anchor_neighbors = self.forge.co_occurrence.get(window.anchor_id, {})
        if not anchor_neighbors:
            return 0.0

        max_co = max(anchor_neighbors.values()) if anchor_neighbors else 1
        scores = []
        for sid in window.preceding:
            co_count = anchor_neighbors.get(sid, 0)
            scores.append(co_count / max_co if max_co > 0 else 0.0)

        return sum(scores) / len(scores)

    def _forward_score(self, window: Window) -> float:
        """
        How well does the following context follow from the anchor?

        Score = average co-occurrence of (anchor, following[i]) normalized
        by the maximum co-occurrence the anchor has with any symbol.
        """
        if not window.following:
            return 0.5

        anchor_neighbors = self.forge.co_occurrence.get(window.anchor_id, {})
        if not anchor_neighbors:
            return 0.0

        max_co = max(anchor_neighbors.values()) if anchor_neighbors else 1
        scores = []
        for sid in window.following:
            co_count = anchor_neighbors.get(sid, 0)
            scores.append(co_count / max_co if max_co > 0 else 0.0)

        return sum(scores) / len(scores)
