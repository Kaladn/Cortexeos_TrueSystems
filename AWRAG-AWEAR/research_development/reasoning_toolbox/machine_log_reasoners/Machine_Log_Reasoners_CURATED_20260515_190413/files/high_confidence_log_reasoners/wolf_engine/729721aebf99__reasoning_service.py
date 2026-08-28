"""
Reasoning Service — ZMQ REP on :5002 wrapping the reasoning pipeline.

Runs on Node 1 alongside Forge. Accepts requests to:
  - analyze_session: Run full 6-1-6 analysis on events in Forge
  - detect_patterns: Run pattern detection on analysis results
  - trace_cascade: Trace forward/backward cascades from a symbol
  - get_windows: Return raw windows for a session

All reasoning modules (engine, causal analyzer, pattern detector,
cascade engine) are wired together here.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

import zmq

from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.reasoning.cascade_engine import CascadeEngine
from wolf_engine.reasoning.causal_analyzer import CausalAnalyzer
from wolf_engine.reasoning.engine import ReasoningEngine
from wolf_engine.reasoning.pattern_detector import PatternDetector
from wolf_engine.services.protocol import decode_request, encode_response

logger = logging.getLogger(__name__)

DEFAULT_PORT = 5002


class ReasoningServiceRunner:
    """ZMQ REP service for reasoning operations on Node 1."""

    def __init__(
        self,
        forge: ForgeMemory,
        bind_addr: str = f"tcp://*:{DEFAULT_PORT}",
    ):
        self.forge = forge
        self.bind_addr = bind_addr
        self._running = False

        # Wire up reasoning modules
        self.engine = ReasoningEngine()
        self.causal = CausalAnalyzer(forge)
        self.detector = PatternDetector()
        self.cascade = CascadeEngine(forge)

        # Cache last analysis result for follow-up queries
        self._last_result = None
        self._last_causal = None

    def run(self) -> None:
        """Run the service loop (blocking)."""
        ctx = zmq.Context.instance()
        sock = ctx.socket(zmq.REP)
        sock.RCVTIMEO = 1000
        sock.bind(self.bind_addr)
        self._running = True
        logger.info("ReasoningService listening on %s", self.bind_addr)

        while self._running:
            try:
                raw = sock.recv()
            except zmq.Again:
                continue

            try:
                action, payload = decode_request(raw)
                status, result = self._handle(action, payload)
                sock.send(encode_response(status, result))
            except Exception as exc:
                logger.error("ReasoningService error: %s", exc)
                sock.send(encode_response("error", {"message": str(exc)}))

        sock.close()

    def stop(self) -> None:
        self._running = False

    def _handle(self, action: str, payload: dict) -> tuple[str, dict[str, Any]]:
        if action == "analyze_session":
            return self._handle_analyze(payload)
        elif action == "detect_patterns":
            return self._handle_detect(payload)
        elif action == "trace_cascade":
            return self._handle_cascade(payload)
        elif action == "get_windows":
            return self._handle_windows(payload)
        elif action == "health":
            return "ok", {"service": "reasoning", "status": "healthy"}
        else:
            return "error", {"message": f"Unknown action: {action}"}

    def _handle_analyze(self, payload: dict) -> tuple[str, dict]:
        """Run full analysis on events currently in Forge."""
        result = self.engine.analyze_from_forge(self.forge)
        self._last_result = result

        # Run causal analysis
        causal_results = self.causal.analyze_all(result.windows)
        self._last_causal = causal_results

        stats = self.engine.get_statistics(result)
        avg_consistency = (
            sum(cr.consistency for cr in causal_results) / len(causal_results)
            if causal_results else 0.0
        )

        return "ok", {
            "total_events": result.total_events,
            "total_windows": len(result.windows),
            "unique_symbols": stats.get("unique_symbols", 0),
            "avg_consistency": round(avg_consistency, 4),
            "top_resonance": [
                {"symbol_id": sid, "score": round(score, 4)}
                for sid, score in stats.get("top_resonance", [])
            ],
        }

    def _handle_detect(self, payload: dict) -> tuple[str, dict]:
        """Run pattern detection on the last analysis result."""
        if self._last_result is None or self._last_causal is None:
            return "error", {"message": "No analysis result. Call analyze_session first."}

        detection = self.detector.detect(self._last_result, self._last_causal)

        return "ok", {
            "pattern_breaks": [
                {
                    "anchor_id": pb.anchor_id,
                    "break_type": pb.break_type,
                    "severity": round(pb.severity, 4),
                }
                for pb in detection.pattern_breaks
            ],
            "causal_chains": [
                {
                    "start_index": cc.start_index,
                    "end_index": cc.end_index,
                    "length": cc.length,
                    "avg_consistency": round(cc.avg_consistency, 4),
                }
                for cc in detection.causal_chains
            ],
            "anomalies": [
                {
                    "anchor_id": a.anchor_id,
                    "consistency": round(a.consistency, 4),
                    "reason": a.reason,
                }
                for a in detection.anomalies
            ],
        }

    def _handle_cascade(self, payload: dict) -> tuple[str, dict]:
        """Trace cascade from a given symbol."""
        origin_id = payload.get("symbol_id", 0)
        direction = payload.get("direction", "both")

        if origin_id == 0:
            return "error", {"message": "symbol_id required"}

        if direction == "both":
            fwd, bwd = self.cascade.trace_both(origin_id)
            return "ok", {
                "forward": _trace_to_dict(fwd),
                "backward": _trace_to_dict(bwd),
            }
        elif direction == "forward":
            trace = self.cascade.trace_forward(origin_id)
            return "ok", {"forward": _trace_to_dict(trace)}
        elif direction == "backward":
            trace = self.cascade.trace_backward(origin_id)
            return "ok", {"backward": _trace_to_dict(trace)}
        else:
            return "error", {"message": f"Unknown direction: {direction}"}

    def _handle_windows(self, payload: dict) -> tuple[str, dict]:
        """Return raw windows from the last analysis."""
        if self._last_result is None:
            return "error", {"message": "No analysis result. Call analyze_session first."}

        limit = payload.get("limit", 50)
        windows = self._last_result.windows[:limit]

        return "ok", {
            "total_windows": len(self._last_result.windows),
            "returned": len(windows),
            "windows": [
                {
                    "anchor_id": w.anchor_id,
                    "anchor_index": w.anchor_index,
                    "preceding": w.preceding,
                    "following": w.following,
                    "resonance_sum": round(sum(w.resonance.values()), 4) if w.resonance else 0.0,
                }
                for w in windows
            ],
        }


def _trace_to_dict(trace) -> dict:
    return {
        "origin_id": trace.origin_id,
        "direction": trace.direction,
        "max_depth": trace.max_depth_reached,
        "total_explored": trace.total_explored,
        "nodes": [
            {
                "symbol_id": n.symbol_id,
                "depth": n.depth,
                "strength": round(n.co_occurrence_strength, 2),
                "parent_id": n.parent_id,
            }
            for n in trace.nodes
        ],
    }
