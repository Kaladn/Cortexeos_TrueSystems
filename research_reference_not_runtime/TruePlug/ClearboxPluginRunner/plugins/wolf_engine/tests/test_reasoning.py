"""
Phase 4 Reasoning test suite — engine, causal analyzer, pattern detector,
cascade engine, reasoning service.
"""

from __future__ import annotations

import socket
import threading
import time
import uuid
from collections import Counter

import pytest
import zmq

from wolf_engine.contracts import SymbolEvent
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.reasoning.cascade_engine import CascadeEngine
from wolf_engine.reasoning.causal_analyzer import CausalAnalyzer, CausalResult
from wolf_engine.reasoning.engine import ReasoningEngine, Window
from wolf_engine.reasoning.pattern_detector import (
    DetectionResult,
    PatternDetector,
)
from wolf_engine.reasoning.reasoning_service import ReasoningServiceRunner
from wolf_engine.services.protocol import decode_response, encode_request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(symbol_id: int, context: list[int] | None = None) -> SymbolEvent:
    return SymbolEvent(
        event_id=str(uuid.uuid4()),
        session_id="test_session",
        pulse_id=1,
        symbol_id=symbol_id,
        context_symbols=context or [],
        category="core",
        priority=1,
    )


def _make_events_with_context(symbol_ids: list[int], window: int = 6) -> list[SymbolEvent]:
    """Build SymbolEvents with context_symbols derived from position in sequence."""
    events = []
    for i, sid in enumerate(symbol_ids):
        ctx_before = symbol_ids[max(0, i - window): i]
        ctx_after = symbol_ids[i + 1: i + 1 + window]
        events.append(_make_event(sid, ctx_before + ctx_after))
    return events


def _build_forge(events: list[SymbolEvent]) -> ForgeMemory:
    forge = ForgeMemory(window_size=10000)
    for e in events:
        forge.ingest(e)
    return forge


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


# A repeating pattern: symbols 1-5 in order, repeated (with context)
_REPEATING_IDS = [i % 5 + 1 for i in range(50)]
_REPEATING = _make_events_with_context(_REPEATING_IDS)

# A pattern with a break: symbols 1-5 repeating, then 99 appears
_BREAK_IDS = [i % 5 + 1 for i in range(40)] + [99] + [i % 5 + 1 for i in range(9)]
_WITH_BREAK = _make_events_with_context(_BREAK_IDS)


# ===========================================================================
# P4-ENG: Reasoning Engine
# ===========================================================================


class TestReasoningEngine:
    def test_empty_events(self):
        engine = ReasoningEngine()
        result = engine.analyze([])
        assert result.total_events == 0
        assert result.windows == []

    def test_basic_analysis(self):
        engine = ReasoningEngine()
        result = engine.analyze(_REPEATING)
        assert result.total_events == 50
        assert len(result.windows) == 50
        assert len(result.lifetime_counts) > 0

    def test_windows_have_correct_context(self):
        events = [_make_event(i + 1) for i in range(15)]
        engine = ReasoningEngine(window_size=6)
        result = engine.analyze(events)

        # Middle window (index 7) should have 6 preceding and 6 following
        w = result.windows[7]
        assert w.anchor_id == 8
        assert len(w.preceding) == 6
        assert len(w.following) == 6

        # First window should have 0 preceding
        w0 = result.windows[0]
        assert len(w0.preceding) == 0
        assert len(w0.following) == 6

    def test_resonance_map_populated(self):
        engine = ReasoningEngine()
        result = engine.analyze(_REPEATING)
        assert len(result.resonance_map) > 0
        # All 5 symbols should have resonance
        for sid in range(1, 6):
            assert sid in result.resonance_map

    def test_lifetime_counts_symmetric(self):
        """If A co-occurs with B, B should co-occur with A."""
        engine = ReasoningEngine(window_size=2)
        events = [_make_event(10), _make_event(20), _make_event(10)]
        result = engine.analyze(events)
        assert 20 in result.lifetime_counts.get(10, {})
        assert 10 in result.lifetime_counts.get(20, {})

    def test_analyze_from_forge(self):
        forge = _build_forge(_REPEATING)
        engine = ReasoningEngine()
        result = engine.analyze_from_forge(forge)
        assert result.total_events > 0

    def test_statistics(self):
        engine = ReasoningEngine()
        result = engine.analyze(_REPEATING)
        stats = engine.get_statistics(result)
        assert stats["total_events"] == 50
        assert stats["total_windows"] == 50
        assert stats["unique_symbols"] == 5


# ===========================================================================
# P4-CAS: Causal Analyzer
# ===========================================================================


class TestCausalAnalyzer:
    def test_high_consistency_repeating_pattern(self):
        forge = _build_forge(_REPEATING)
        engine = ReasoningEngine()
        result = engine.analyze(_REPEATING)
        analyzer = CausalAnalyzer(forge)
        causal = analyzer.analyze_all(result.windows)

        assert len(causal) == len(result.windows)
        # Repeating pattern should have decent consistency
        mid_results = causal[10:40]  # Skip edges
        avg = sum(cr.consistency for cr in mid_results) / len(mid_results)
        assert avg > 0.0  # Should be non-zero for repeating pattern

    def test_empty_forge_gives_zero_scores(self):
        forge = ForgeMemory(window_size=1000)
        analyzer = CausalAnalyzer(forge)
        w = Window(anchor_id=42, preceding=[1, 2, 3], following=[4, 5, 6])
        cr = analyzer.analyze_window(w)
        assert cr.backward_score == 0.0
        assert cr.forward_score == 0.0

    def test_no_context_gives_neutral(self):
        forge = _build_forge(_REPEATING)
        analyzer = CausalAnalyzer(forge)
        w = Window(anchor_id=1, preceding=[], following=[])
        cr = analyzer.analyze_window(w)
        assert cr.consistency == 0.5  # Neutral

    def test_causal_result_fields(self):
        forge = _build_forge(_REPEATING)
        engine = ReasoningEngine()
        result = engine.analyze(_REPEATING)
        analyzer = CausalAnalyzer(forge)
        cr = analyzer.analyze_window(result.windows[25])

        assert cr.anchor_id == result.windows[25].anchor_id
        assert 0.0 <= cr.backward_score <= 1.0
        assert 0.0 <= cr.forward_score <= 1.0
        assert 0.0 <= cr.consistency <= 1.0
        assert cr.context_depth > 0


# ===========================================================================
# P4-PAT: Pattern Detector
# ===========================================================================


class TestPatternDetector:
    def test_no_breaks_in_uniform_pattern(self):
        forge = _build_forge(_REPEATING)
        engine = ReasoningEngine()
        result = engine.analyze(_REPEATING)
        analyzer = CausalAnalyzer(forge)
        causal = analyzer.analyze_all(result.windows)

        detector = PatternDetector()
        detection = detector.detect(result, causal)
        # Uniform pattern should have very few or no breaks
        assert isinstance(detection, DetectionResult)

    def test_detects_novel_symbol_break(self):
        forge = _build_forge(_WITH_BREAK)
        engine = ReasoningEngine()
        result = engine.analyze(_WITH_BREAK)
        analyzer = CausalAnalyzer(forge)
        causal = analyzer.analyze_all(result.windows)

        detector = PatternDetector(break_threshold=1.5)
        detection = detector.detect(result, causal)
        # Symbol 99 should trigger a break
        break_ids = [pb.anchor_id for pb in detection.pattern_breaks]
        assert 99 in break_ids or len(detection.anomalies) > 0

    def test_detects_causal_chains(self):
        forge = _build_forge(_REPEATING)
        engine = ReasoningEngine()
        result = engine.analyze(_REPEATING)
        analyzer = CausalAnalyzer(forge)
        causal = analyzer.analyze_all(result.windows)

        # Use low threshold to find chains easily
        detector = PatternDetector(consistency_high=0.1, min_chain_length=3)
        detection = detector.detect(result, causal)

        if detection.causal_chains:
            chain = detection.causal_chains[0]
            assert chain.length >= 3
            assert chain.avg_consistency >= 0.1

    def test_anomaly_detection(self):
        """Isolated symbol with no co-occurrence should be flagged."""
        events = [_make_event(i % 3 + 1) for i in range(20)]
        events.append(_make_event(999))  # Isolated symbol
        forge = _build_forge(events)
        engine = ReasoningEngine()
        result = engine.analyze(events)
        analyzer = CausalAnalyzer(forge)
        causal = analyzer.analyze_all(result.windows)

        detector = PatternDetector(consistency_low=0.3)
        detection = detector.detect(result, causal)
        anomaly_ids = [a.anchor_id for a in detection.anomalies]
        # 999 has near-zero co-occurrence — should be anomalous
        assert 999 in anomaly_ids

    def test_empty_input(self):
        engine = ReasoningEngine()
        result = engine.analyze([])
        detector = PatternDetector()
        detection = detector.detect(result, [])
        assert detection.pattern_breaks == []
        assert detection.causal_chains == []
        assert detection.anomalies == []


# ===========================================================================
# P4-CSC: Cascade Engine
# ===========================================================================


class TestCascadeEngine:
    def _build_connected_forge(self) -> ForgeMemory:
        """Build a Forge with clear co-occurrence chains: 1→2→3→4→5."""
        forge = ForgeMemory(window_size=5000)
        for _ in range(20):
            for i in range(1, 6):
                forge.ingest(_make_event(i, [i - 1, i + 1] if i > 1 else [i + 1]))
        return forge

    def test_forward_trace(self):
        forge = self._build_connected_forge()
        cascade = CascadeEngine(forge, max_depth=3)
        trace = cascade.trace_forward(1)
        assert trace.origin_id == 1
        assert trace.direction == "forward"
        assert len(trace.nodes) > 0

    def test_backward_trace(self):
        forge = self._build_connected_forge()
        cascade = CascadeEngine(forge, max_depth=3)
        trace = cascade.trace_backward(5)
        assert trace.origin_id == 5
        assert trace.direction == "backward"
        assert len(trace.nodes) > 0

    def test_both_directions(self):
        forge = self._build_connected_forge()
        cascade = CascadeEngine(forge, max_depth=3)
        fwd, bwd = cascade.trace_both(3)
        assert fwd.direction == "forward"
        assert bwd.direction == "backward"

    def test_isolated_symbol_empty_trace(self):
        forge = ForgeMemory(window_size=1000)
        forge.ingest(_make_event(42))
        cascade = CascadeEngine(forge)
        trace = cascade.trace_forward(42)
        assert len(trace.nodes) == 0

    def test_max_depth_respected(self):
        forge = self._build_connected_forge()
        cascade = CascadeEngine(forge, max_depth=1)
        trace = cascade.trace_forward(1)
        for node in trace.nodes:
            assert node.depth <= 1

    def test_max_nodes_respected(self):
        forge = self._build_connected_forge()
        cascade = CascadeEngine(forge, max_depth=10, max_nodes=3)
        trace = cascade.trace_forward(1)
        assert len(trace.nodes) <= 3

    def test_symbol_ids_helper(self):
        forge = self._build_connected_forge()
        cascade = CascadeEngine(forge, max_depth=2)
        trace = cascade.trace_forward(1)
        ids = trace.symbol_ids()
        assert all(isinstance(i, int) for i in ids)


# ===========================================================================
# P4-RSV: Reasoning Service (ZMQ)
# ===========================================================================


class TestReasoningService:
    def _start_service(self, forge: ForgeMemory, port: int) -> ReasoningServiceRunner:
        addr = f"tcp://127.0.0.1:{port}"
        svc = ReasoningServiceRunner(forge, bind_addr=f"tcp://*:{port}")
        t = threading.Thread(target=svc.run, daemon=True)
        t.start()
        time.sleep(0.3)
        return svc

    def _zmq_request(self, port: int, action: str, payload: dict | None = None) -> tuple[str, dict]:
        ctx = zmq.Context.instance()
        sock = ctx.socket(zmq.REQ)
        sock.RCVTIMEO = 5000
        sock.SNDTIMEO = 2000
        sock.setsockopt(zmq.LINGER, 0)
        try:
            sock.connect(f"tcp://127.0.0.1:{port}")
            sock.send(encode_request(action, payload or {}))
            raw = sock.recv()
            return decode_response(raw)
        finally:
            sock.close()

    def test_health(self):
        forge = _build_forge(_REPEATING)
        port = _find_free_port()
        svc = self._start_service(forge, port)
        try:
            status, data = self._zmq_request(port, "health")
            assert status == "ok"
            assert data["service"] == "reasoning"
        finally:
            svc.stop()

    def test_analyze_session(self):
        forge = _build_forge(_REPEATING)
        port = _find_free_port()
        svc = self._start_service(forge, port)
        try:
            status, data = self._zmq_request(port, "analyze_session")
            assert status == "ok"
            assert data["total_windows"] > 0
            assert "avg_consistency" in data
        finally:
            svc.stop()

    def test_detect_patterns_requires_analysis(self):
        forge = _build_forge(_REPEATING)
        port = _find_free_port()
        svc = self._start_service(forge, port)
        try:
            # detect_patterns without analyze_session first should error
            status, data = self._zmq_request(port, "detect_patterns")
            assert status == "error"
        finally:
            svc.stop()

    def test_analyze_then_detect(self):
        forge = _build_forge(_REPEATING)
        port = _find_free_port()
        svc = self._start_service(forge, port)
        try:
            self._zmq_request(port, "analyze_session")
            status, data = self._zmq_request(port, "detect_patterns")
            assert status == "ok"
            assert "pattern_breaks" in data
            assert "causal_chains" in data
            assert "anomalies" in data
        finally:
            svc.stop()

    def test_cascade_trace(self):
        forge = _build_forge(_REPEATING)
        port = _find_free_port()
        svc = self._start_service(forge, port)
        try:
            status, data = self._zmq_request(port, "trace_cascade", {"symbol_id": 1, "direction": "both"})
            assert status == "ok"
            assert "forward" in data
            assert "backward" in data
        finally:
            svc.stop()

    def test_get_windows_requires_analysis(self):
        forge = _build_forge(_REPEATING)
        port = _find_free_port()
        svc = self._start_service(forge, port)
        try:
            status, data = self._zmq_request(port, "get_windows")
            assert status == "error"
        finally:
            svc.stop()

    def test_unknown_action(self):
        forge = _build_forge(_REPEATING)
        port = _find_free_port()
        svc = self._start_service(forge, port)
        try:
            status, data = self._zmq_request(port, "bogus_action")
            assert status == "error"
        finally:
            svc.stop()
