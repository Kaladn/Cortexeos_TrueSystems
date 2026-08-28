"""
Pattern Detector — Identifies pattern breaks, causal chains, and anomalies.

Adapted from unzipped_cleanup/pattern_detector.py. Generalized from
finance-specific metrics to domain-agnostic resonance/consistency scoring.

Three detection modes:
  1. Pattern Breaks: Windows where resonance drops sharply vs neighbors
  2. Causal Chains: Runs of high-consistency windows (sustained patterns)
  3. Anomalies: Windows with very low causal consistency
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from wolf_engine.reasoning.causal_analyzer import CausalResult
from wolf_engine.reasoning.engine import EngineResult, Window

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PatternBreak:
    """A detected break in the expected pattern."""

    anchor_id: int = 0
    anchor_index: int = 0
    break_type: str = ""         # "resonance_drop", "novel_symbol", "context_shift"
    severity: float = 0.0        # 0-1, higher = more anomalous
    resonance_delta: float = 0.0  # Change from local average


@dataclass(slots=True)
class CausalChain:
    """A sequence of high-consistency windows (sustained pattern)."""

    start_index: int = 0
    end_index: int = 0
    length: int = 0
    avg_consistency: float = 0.0
    anchor_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class Anomaly:
    """A window with unusually low causal consistency."""

    anchor_id: int = 0
    anchor_index: int = 0
    consistency: float = 0.0
    reason: str = ""


@dataclass(slots=True)
class DetectionResult:
    """Combined output from all detection modes."""

    pattern_breaks: list[PatternBreak] = field(default_factory=list)
    causal_chains: list[CausalChain] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)


class PatternDetector:
    """
    Domain-agnostic pattern detection on 6-1-6 analysis results.

    Config thresholds:
      - break_threshold: resonance z-score for pattern break (default 2.0)
      - consistency_high: minimum consistency for chain inclusion (default 0.7)
      - consistency_low: maximum consistency for anomaly flag (default 0.3)
      - min_chain_length: minimum windows for a causal chain (default 3)
    """

    def __init__(
        self,
        break_threshold: float = 2.0,
        consistency_high: float = 0.7,
        consistency_low: float = 0.3,
        min_chain_length: int = 3,
    ):
        self.break_threshold = break_threshold
        self.consistency_high = consistency_high
        self.consistency_low = consistency_low
        self.min_chain_length = min_chain_length

    def detect(
        self,
        engine_result: EngineResult,
        causal_results: list[CausalResult],
    ) -> DetectionResult:
        """Run all detection modes on the analysis output."""
        breaks = self._detect_breaks(engine_result)
        chains = self._detect_chains(causal_results)
        anomalies = self._detect_anomalies(causal_results)

        logger.info(
            "PatternDetector: %d breaks, %d chains, %d anomalies",
            len(breaks), len(chains), len(anomalies),
        )
        return DetectionResult(
            pattern_breaks=breaks,
            causal_chains=chains,
            anomalies=anomalies,
        )

    def _detect_breaks(self, result: EngineResult) -> list[PatternBreak]:
        """Detect windows where resonance drops sharply vs local average."""
        if len(result.windows) < 3:
            return []

        breaks = []
        # Compute per-window total resonance
        res_scores = []
        for w in result.windows:
            total_res = sum(w.resonance.values()) if w.resonance else 0.0
            res_scores.append(total_res)

        # Compute mean and std of resonance
        mean_res = sum(res_scores) / len(res_scores)
        variance = sum((r - mean_res) ** 2 for r in res_scores) / len(res_scores)
        std_res = variance ** 0.5 if variance > 0 else 1.0

        for i, (w, score) in enumerate(zip(result.windows, res_scores)):
            if std_res > 0:
                z_score = (mean_res - score) / std_res
            else:
                z_score = 0.0

            if z_score >= self.break_threshold:
                # Determine break type
                if score == 0.0:
                    break_type = "novel_symbol"
                elif z_score >= self.break_threshold * 1.5:
                    break_type = "context_shift"
                else:
                    break_type = "resonance_drop"

                breaks.append(PatternBreak(
                    anchor_id=w.anchor_id,
                    anchor_index=w.anchor_index,
                    break_type=break_type,
                    severity=min(z_score / (self.break_threshold * 2), 1.0),
                    resonance_delta=score - mean_res,
                ))

        return breaks

    def _detect_chains(self, causal_results: list[CausalResult]) -> list[CausalChain]:
        """Find runs of consecutive high-consistency windows."""
        if not causal_results:
            return []

        chains = []
        run_start = None
        run_ids: list[int] = []
        run_scores: list[float] = []

        for cr in causal_results:
            if cr.consistency >= self.consistency_high:
                if run_start is None:
                    run_start = cr.anchor_index
                    run_ids = []
                    run_scores = []
                run_ids.append(cr.anchor_id)
                run_scores.append(cr.consistency)
            else:
                if run_start is not None and len(run_ids) >= self.min_chain_length:
                    chains.append(CausalChain(
                        start_index=run_start,
                        end_index=cr.anchor_index - 1,
                        length=len(run_ids),
                        avg_consistency=sum(run_scores) / len(run_scores),
                        anchor_ids=run_ids,
                    ))
                run_start = None

        # Close trailing run
        if run_start is not None and len(run_ids) >= self.min_chain_length:
            chains.append(CausalChain(
                start_index=run_start,
                end_index=causal_results[-1].anchor_index,
                length=len(run_ids),
                avg_consistency=sum(run_scores) / len(run_scores),
                anchor_ids=run_ids,
            ))

        return chains

    def _detect_anomalies(self, causal_results: list[CausalResult]) -> list[Anomaly]:
        """Flag windows with very low causal consistency."""
        anomalies = []
        for cr in causal_results:
            if cr.consistency < self.consistency_low:
                if cr.context_depth < 2:
                    reason = "insufficient_context"
                elif cr.backward_score < 0.1 and cr.forward_score < 0.1:
                    reason = "isolated_symbol"
                elif cr.backward_score < 0.1:
                    reason = "unexpected_arrival"
                elif cr.forward_score < 0.1:
                    reason = "dead_end"
                else:
                    reason = "low_consistency"

                anomalies.append(Anomaly(
                    anchor_id=cr.anchor_id,
                    anchor_index=cr.anchor_index,
                    consistency=cr.consistency,
                    reason=reason,
                ))

        return anomalies
