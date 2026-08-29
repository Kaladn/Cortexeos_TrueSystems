"""
Phase 5 Archon test suite — schemas, judge (3 modules), verdict store,
CAM stub, orchestrator end-to-end.
"""

from __future__ import annotations

import math
import time
import uuid

import pytest

from wolf_engine.archon.cam_stub import CausalAlignmentMatrix
from wolf_engine.archon.judge import (
    CitadelIsolation,
    ConfidenceGovernance,
    Judge,
    TemporalCoherence,
)
from wolf_engine.archon.orchestrator import Orchestrator
from wolf_engine.archon.schemas import (
    EngineResponse,
    FlagSeverity,
    Verdict,
    VerdictStatus,
)
from wolf_engine.archon.verdict import VerdictStore
from wolf_engine.contracts import SymbolEvent
from wolf_engine.forge.forge_memory import ForgeMemory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _response(
    confidence: float = 0.5,
    consistency: float = 0.5,
    windows: int = 10,
    session_id: str = "sess_1",
    **kwargs,
) -> EngineResponse:
    return EngineResponse(
        session_id=session_id,
        confidence=confidence,
        avg_consistency=consistency,
        total_windows=windows,
        **kwargs,
    )


def _make_event(sid: int, ctx: list[int] | None = None) -> SymbolEvent:
    return SymbolEvent(
        event_id=str(uuid.uuid4()),
        session_id="test",
        pulse_id=1,
        symbol_id=sid,
        context_symbols=ctx or [],
    )


def _make_events_with_context(symbol_ids: list[int]) -> list[SymbolEvent]:
    events = []
    for i, sid in enumerate(symbol_ids):
        ctx = symbol_ids[max(0, i - 6): i] + symbol_ids[i + 1: i + 7]
        events.append(_make_event(sid, ctx))
    return events


# ===========================================================================
# Schemas
# ===========================================================================


class TestSchemas:
    def test_engine_response_defaults(self):
        r = EngineResponse()
        assert r.confidence == 0.0
        assert r.request_id  # UUID auto-generated

    def test_verdict_to_dict(self):
        v = Verdict(
            status=VerdictStatus.APPROVED,
            original_confidence=0.7,
            adjusted_confidence=0.65,
        )
        d = v.to_dict()
        assert d["status"] == "approved"
        assert d["adjusted_confidence"] == 0.65

    def test_verdict_status_values(self):
        assert VerdictStatus.APPROVED.value == "approved"
        assert VerdictStatus.QUARANTINED.value == "quarantined"
        assert VerdictStatus.PENALIZED.value == "penalized"
        assert VerdictStatus.ADJUSTED.value == "adjusted"


# ===========================================================================
# Citadel Isolation
# ===========================================================================


class TestCitadel:
    def test_nan_confidence_flagged(self):
        citadel = CitadelIsolation()
        flags = citadel.evaluate(_response(confidence=float("nan")))
        assert any(f.code == "nan_confidence" for f in flags)
        assert any(f.severity == FlagSeverity.CRITICAL for f in flags)

    def test_inf_confidence_flagged(self):
        citadel = CitadelIsolation()
        flags = citadel.evaluate(_response(confidence=float("inf")))
        assert any(f.code == "nan_confidence" for f in flags)

    def test_negative_confidence_flagged(self):
        citadel = CitadelIsolation()
        flags = citadel.evaluate(_response(confidence=-0.5))
        assert any(f.code == "negative_confidence" for f in flags)

    def test_overflow_confidence_flagged(self):
        citadel = CitadelIsolation()
        flags = citadel.evaluate(_response(confidence=999.0))
        assert any(f.code == "confidence_overflow" for f in flags)

    def test_empty_analysis_flagged(self):
        citadel = CitadelIsolation()
        flags = citadel.evaluate(_response(confidence=0.5, windows=0))
        assert any(f.code == "empty_analysis" for f in flags)

    def test_future_timestamp_flagged(self):
        citadel = CitadelIsolation()
        r = _response()
        r.timestamp = time.time() + 3600  # 1 hour in the future
        flags = citadel.evaluate(r)
        assert any(f.code == "future_timestamp" for f in flags)

    def test_clean_response_no_flags(self):
        citadel = CitadelIsolation()
        flags = citadel.evaluate(_response(confidence=0.5, windows=10))
        assert flags == []


# ===========================================================================
# Confidence Governance
# ===========================================================================


class TestConfidenceGovernance:
    def test_overconfident_flagged(self):
        cg = ConfidenceGovernance()
        flags = cg.evaluate(_response(confidence=0.95, consistency=0.1))
        assert any(f.code == "overconfident" for f in flags)
        assert any(f.adjustment < 0 for f in flags)

    def test_underconfident_flagged(self):
        cg = ConfidenceGovernance()
        flags = cg.evaluate(_response(confidence=0.1, consistency=0.9))
        assert any(f.code == "underconfident" for f in flags)
        assert any(f.adjustment > 0 for f in flags)

    def test_calibrated_no_flags(self):
        cg = ConfidenceGovernance()
        flags = cg.evaluate(_response(confidence=0.5, consistency=0.5))
        assert flags == []

    def test_calibration_drift_after_history(self):
        cg = ConfidenceGovernance(history_size=10)
        # Build history with large drift
        for _ in range(10):
            cg.evaluate(_response(confidence=0.9, consistency=0.2))
        flags = cg.evaluate(_response(confidence=0.9, consistency=0.2))
        assert any(f.code == "calibration_drift" for f in flags)


# ===========================================================================
# Temporal Coherence
# ===========================================================================


class TestTemporalCoherence:
    def test_flip_flop_flagged(self):
        tc = TemporalCoherence(max_swing=0.3)
        tc.evaluate(_response(confidence=0.2, session_id="s1"))
        flags = tc.evaluate(_response(confidence=0.8, session_id="s1"))
        assert any(f.code == "flip_flop" for f in flags)

    def test_oscillation_flagged(self):
        tc = TemporalCoherence(max_swing=0.3)
        tc.evaluate(_response(confidence=0.2, session_id="s1"))
        tc.evaluate(_response(confidence=0.8, session_id="s1"))
        flags = tc.evaluate(_response(confidence=0.2, session_id="s1"))
        assert any(f.code == "oscillation" for f in flags)

    def test_stable_no_flags(self):
        tc = TemporalCoherence()
        tc.evaluate(_response(confidence=0.5, session_id="s1"))
        flags = tc.evaluate(_response(confidence=0.55, session_id="s1"))
        assert flags == []

    def test_different_sessions_independent(self):
        tc = TemporalCoherence(max_swing=0.3)
        tc.evaluate(_response(confidence=0.2, session_id="s1"))
        flags = tc.evaluate(_response(confidence=0.8, session_id="s2"))
        assert flags == []  # Different session, no flip-flop


# ===========================================================================
# Judge Pipeline
# ===========================================================================


class TestJudge:
    def test_clean_response_approved(self):
        judge = Judge()
        verdict = judge.evaluate(_response(confidence=0.5, consistency=0.5))
        assert verdict.status == VerdictStatus.APPROVED

    def test_nan_quarantined(self):
        judge = Judge()
        verdict = judge.evaluate(_response(confidence=float("nan")))
        assert verdict.status == VerdictStatus.QUARANTINED
        assert verdict.adjusted_confidence == 0.0

    def test_overconfident_adjusted(self):
        judge = Judge()
        verdict = judge.evaluate(_response(confidence=0.95, consistency=0.1))
        assert verdict.status == VerdictStatus.ADJUSTED
        assert verdict.adjusted_confidence < verdict.original_confidence

    def test_flip_flop_penalized(self):
        judge = Judge()
        judge.evaluate(_response(confidence=0.2, session_id="s1"))
        verdict = judge.evaluate(_response(confidence=0.9, session_id="s1"))
        assert verdict.status == VerdictStatus.PENALIZED

    def test_confidence_clamped_to_0_1(self):
        judge = Judge()
        # Very overconfident — big negative adjustment should clamp to 0
        verdict = judge.evaluate(_response(confidence=0.01, consistency=0.01))
        assert 0.0 <= verdict.adjusted_confidence <= 1.0


# ===========================================================================
# Verdict Store (SQLite)
# ===========================================================================


class TestVerdictStore:
    def test_record_and_retrieve(self, tmp_path):
        store = VerdictStore(str(tmp_path / "verdicts.db"))
        v = Verdict(
            session_id="s1",
            status=VerdictStatus.APPROVED,
            original_confidence=0.7,
            adjusted_confidence=0.7,
        )
        store.record(v)
        results = store.get_by_session("s1")
        assert len(results) == 1
        assert results[0]["status"] == "approved"
        assert results[0]["original_confidence"] == 0.7
        store.close()

    def test_count_by_status(self, tmp_path):
        store = VerdictStore(str(tmp_path / "verdicts.db"))
        for status in [VerdictStatus.APPROVED, VerdictStatus.APPROVED, VerdictStatus.QUARANTINED]:
            store.record(Verdict(session_id="s1", status=status))
        counts = store.count_by_status()
        assert counts["approved"] == 2
        assert counts["quarantined"] == 1
        store.close()

    def test_get_recent(self, tmp_path):
        store = VerdictStore(str(tmp_path / "verdicts.db"))
        for i in range(5):
            store.record(Verdict(session_id=f"s{i}", status=VerdictStatus.APPROVED))
        recent = store.get_recent(3)
        assert len(recent) == 3
        store.close()

    def test_get_by_status(self, tmp_path):
        store = VerdictStore(str(tmp_path / "verdicts.db"))
        store.record(Verdict(session_id="s1", status=VerdictStatus.QUARANTINED))
        store.record(Verdict(session_id="s2", status=VerdictStatus.APPROVED))
        quarantined = store.get_by_status("quarantined")
        assert len(quarantined) == 1
        assert quarantined[0]["session_id"] == "s1"
        store.close()


# ===========================================================================
# CAM Stub
# ===========================================================================


class TestCAMStub:
    def test_dormant_by_default(self):
        cam = CausalAlignmentMatrix()
        assert not cam.is_active

    def test_single_engine_perfect_agreement(self):
        cam = CausalAlignmentMatrix()
        score = cam.compare(_response())
        assert score.agreement == 1.0
        assert not score.active

    def test_register_activates(self):
        cam = CausalAlignmentMatrix()
        cam.register_engine("secondary")
        assert cam.is_active

    def test_multi_engine_comparison(self):
        cam = CausalAlignmentMatrix()
        cam.register_engine("secondary")
        a = _response(confidence=0.8, consistency=0.7)
        b = _response(confidence=0.3, consistency=0.2)
        score = cam.compare(a, b)
        assert score.active
        assert score.agreement < 1.0
        assert len(score.divergence_points) > 0

    def test_multi_engine_agreement(self):
        cam = CausalAlignmentMatrix()
        cam.register_engine("secondary")
        a = _response(confidence=0.7, consistency=0.6)
        b = _response(confidence=0.7, consistency=0.6)
        score = cam.compare(a, b)
        assert score.agreement == 1.0


# ===========================================================================
# Orchestrator End-to-End
# ===========================================================================


class TestOrchestrator:
    def _build_forge(self, ids: list[int]) -> ForgeMemory:
        forge = ForgeMemory(window_size=10000)
        events = _make_events_with_context(ids)
        for e in events:
            forge.ingest(e)
        return forge

    def test_basic_analysis(self, tmp_path):
        ids = [i % 5 + 1 for i in range(50)]
        forge = self._build_forge(ids)
        orch = Orchestrator(forge, str(tmp_path / "verdicts.db"))
        events = _make_events_with_context(ids)
        verdict = orch.analyze(events, session_id="test_session")
        assert verdict.status in (VerdictStatus.APPROVED, VerdictStatus.ADJUSTED)
        assert 0.0 <= verdict.adjusted_confidence <= 1.0
        orch.close()

    def test_garbage_confidence_quarantined(self, tmp_path):
        ids = [i % 5 + 1 for i in range(50)]
        forge = self._build_forge(ids)
        orch = Orchestrator(forge, str(tmp_path / "verdicts.db"))
        events = _make_events_with_context(ids)
        verdict = orch.analyze(events, session_id="s1", confidence=float("nan"))
        assert verdict.status == VerdictStatus.QUARANTINED
        orch.close()

    def test_overflow_confidence_quarantined(self, tmp_path):
        ids = [i % 5 + 1 for i in range(50)]
        forge = self._build_forge(ids)
        orch = Orchestrator(forge, str(tmp_path / "verdicts.db"))
        events = _make_events_with_context(ids)
        verdict = orch.analyze(events, session_id="s1", confidence=999.0)
        assert verdict.status == VerdictStatus.QUARANTINED
        orch.close()

    def test_audit_trail_persisted(self, tmp_path):
        ids = [i % 5 + 1 for i in range(30)]
        forge = self._build_forge(ids)
        orch = Orchestrator(forge, str(tmp_path / "verdicts.db"))
        events = _make_events_with_context(ids)
        orch.analyze(events, session_id="audit_test")
        orch.analyze(events, session_id="audit_test")
        trail = orch.get_audit_trail("audit_test")
        assert len(trail) == 2
        orch.close()

    def test_status_counts(self, tmp_path):
        ids = [i % 3 + 1 for i in range(20)]
        forge = self._build_forge(ids)
        orch = Orchestrator(forge, str(tmp_path / "verdicts.db"))
        events = _make_events_with_context(ids)
        orch.analyze(events, session_id="s1")
        orch.analyze(events, session_id="s1", confidence=float("nan"))
        counts = orch.get_status_counts()
        assert sum(counts.values()) == 2
        orch.close()

    def test_analyze_from_forge(self, tmp_path):
        ids = [i % 5 + 1 for i in range(40)]
        forge = self._build_forge(ids)
        orch = Orchestrator(forge, str(tmp_path / "verdicts.db"))
        # Analyze without passing events — reads from Forge
        verdict = orch.analyze(session_id="forge_test")
        assert verdict.status in (
            VerdictStatus.APPROVED, VerdictStatus.ADJUSTED,
            VerdictStatus.QUARANTINED, VerdictStatus.PENALIZED,
        )
        orch.close()
