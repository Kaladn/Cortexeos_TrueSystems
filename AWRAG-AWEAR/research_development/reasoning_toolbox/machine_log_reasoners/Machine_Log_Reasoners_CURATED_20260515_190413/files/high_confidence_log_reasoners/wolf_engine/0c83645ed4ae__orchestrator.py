"""
Archon Orchestrator — Dispatches to reasoning engine, applies governance,
persists verdicts.

Flow:
  1. Receive analysis request
  2. Run reasoning engine (analyze_from_forge or analyze events)
  3. Build EngineResponse from results
  4. Run Judge governance pipeline (Citadel → Confidence → Temporal)
  5. Persist verdict to audit trail
  6. Return verdict

Single-engine for now. When a second engine is added, the orchestrator
will fan out to both and pass results through CAM before the Judge.
"""

from __future__ import annotations

import logging
from typing import Any

from wolf_engine.archon.cam_stub import CausalAlignmentMatrix
from wolf_engine.archon.judge import Judge
from wolf_engine.archon.schemas import EngineResponse, Verdict
from wolf_engine.archon.verdict import VerdictStore
from wolf_engine.contracts import SymbolEvent
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.reasoning.causal_analyzer import CausalAnalyzer
from wolf_engine.reasoning.engine import ReasoningEngine
from wolf_engine.reasoning.pattern_detector import PatternDetector

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Archon orchestrator — single entry point for governed analysis.

    Wires together: ReasoningEngine → Judge → VerdictStore.
    """

    def __init__(
        self,
        forge: ForgeMemory,
        verdict_db_path: str,
    ):
        self.forge = forge
        self.engine = ReasoningEngine()
        self.causal = CausalAnalyzer(forge)
        self.detector = PatternDetector()
        self.judge = Judge()
        self.verdict_store = VerdictStore(verdict_db_path)
        self.cam = CausalAlignmentMatrix()

    def analyze(
        self,
        events: list[SymbolEvent] | None = None,
        session_id: str = "",
        confidence: float | None = None,
    ) -> Verdict:
        """
        Run full governed analysis.

        Args:
            events: SymbolEvents to analyze. If None, reads from Forge.
            session_id: Session identifier for temporal tracking.
            confidence: Override confidence (if engine provides its own).
                        If None, derived from avg_consistency.

        Returns:
            Verdict with governance flags and adjusted confidence.
        """
        # Step 1: Run reasoning engine
        if events is not None:
            result = self.engine.analyze(events)
        else:
            result = self.engine.analyze_from_forge(self.forge)

        # Step 2: Run causal analysis
        causal_results = self.causal.analyze_all(result.windows)

        # Step 3: Run pattern detection
        detection = self.detector.detect(result, causal_results)

        # Step 4: Build EngineResponse
        avg_consistency = (
            sum(cr.consistency for cr in causal_results) / len(causal_results)
            if causal_results else 0.0
        )

        engine_response = EngineResponse(
            session_id=session_id,
            confidence=confidence if confidence is not None else avg_consistency,
            total_windows=len(result.windows),
            avg_consistency=avg_consistency,
            pattern_breaks=len(detection.pattern_breaks),
            causal_chains=len(detection.causal_chains),
            anomalies=len(detection.anomalies),
        )

        # Step 5: Judge governance pipeline
        verdict = self.judge.evaluate(engine_response)

        # Step 6: Persist to audit trail
        self.verdict_store.record(verdict)

        logger.info(
            "Archon verdict: %s (%.3f → %.3f) [%d flags]",
            verdict.status.value,
            verdict.original_confidence,
            verdict.adjusted_confidence,
            len(verdict.flags),
        )

        return verdict

    def get_audit_trail(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve all verdicts for a session from the audit trail."""
        return self.verdict_store.get_by_session(session_id)

    def get_status_counts(self) -> dict[str, int]:
        """Get verdict counts by status."""
        return self.verdict_store.count_by_status()

    def close(self) -> None:
        """Close the verdict store."""
        self.verdict_store.close()
