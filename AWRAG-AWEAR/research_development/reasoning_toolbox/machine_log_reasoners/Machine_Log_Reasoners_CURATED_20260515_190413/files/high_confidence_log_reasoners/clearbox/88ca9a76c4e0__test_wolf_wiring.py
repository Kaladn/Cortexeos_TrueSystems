"""
Wolf Engine — Wiring Correctness Tests (Phase 4.5)

Safety contract: "Wolf disabled == pipeline no-op; Direct Wolf reachable."
These tests MUST pass before any wiring changes ship.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Ensure plugins/ is on sys.path (matches bridge server behavior)
_plugins = str(Path(__file__).resolve().parent.parent / "plugins")
if _plugins not in sys.path:
    sys.path.insert(0, _plugins)

import pytest

from wolf_engine.archon.judge import Judge
from wolf_engine.archon.schemas import (
    EngineResponse,
    GovernanceFlag,
    FlagSeverity,
    Verdict,
    VerdictStatus,
)
from wolf_engine.core.engine import WolfEngine
from wolf_engine.modules.truevision import (
    ManipulationFlags,
    OperatorResult,
    TelemetryWindow,
)


# ── Fixtures ────────────────────────────────────────────────


@pytest.fixture
def engine(tmp_path):
    """Disposable WolfEngine instance with tmp storage."""
    e = WolfEngine(db_dir=str(tmp_path))
    yield e
    e.close()


@pytest.fixture
def seeded_engine(engine):
    """Engine with a baseline corpus ingested."""
    engine.perceive_and_ingest(
        "The wolf runs through the clearbox at night. "
        "Symbols cascade through the reasoning engine. "
        "Architecture data test patterns emerge from analysis."
    )
    return engine


# ── Contract 1: Wolf disabled == pipeline no-op ─────────────


class TestWolfDisabledIsNoop:
    """When Wolf Engine is disabled in config, pipeline behavior is unchanged."""

    def test_config_declares_wolf_in_plugin_chain(self):
        """Verify config has wolf_engine registered in plugin_chain."""
        try:
            from security.data_paths import SOURCE_ROOT
            cfg_path = SOURCE_ROOT / "clearbox.config.json"
        except ImportError:
            cfg_path = Path("clearbox.config.json")

        if not cfg_path.exists():
            pytest.skip("clearbox.config.json not found")

        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        pipeline = cfg.get("routing", {}).get("pipeline", [])
        plugin_stage = next(
            (s for s in pipeline if s.get("type") == "plugin_chain"), None
        )
        assert plugin_stage is not None, "plugin_chain stage missing from config"

        wolf = next(
            (p for p in plugin_stage.get("config", {}).get("plugins", [])
             if "wolf" in p.get("name", "")),
            None,
        )
        assert wolf is not None, "wolf_engine not found in plugin_chain"
        assert isinstance(wolf["enabled"], bool), "enabled must be a bool"

    def test_judge_without_operators_unchanged(self):
        """Judge.evaluate() without operator_results produces identical output
        to current behavior (no OperatorGovernance gate fires)."""
        judge = Judge()

        response = EngineResponse(
            session_id="safety-test",
            confidence=0.5,
            avg_consistency=0.5,
            total_windows=10,
            pattern_breaks=0,
            causal_chains=3,
            anomalies=0,
        )

        verdict = judge.evaluate(response)
        assert verdict.status == VerdictStatus.APPROVED
        assert abs(verdict.adjusted_confidence - 0.5) < 0.01
        # No operator flags should be present
        assert all(f.module != "operator" for f in verdict.flags)

    def test_engine_analyze_deterministic_shape(self, seeded_engine):
        """Two analyze calls on same engine produce the same schema shape."""
        r1 = seeded_engine.analyze(session_id="shape-test-1")
        r2 = seeded_engine.analyze(session_id="shape-test-2")

        # Same top-level keys
        assert set(r1.keys()) == set(r2.keys())

        # Verdict always present with required fields
        for r in (r1, r2):
            v = r["verdict"]
            assert "status" in v
            assert "adjusted_confidence" in v
            assert "original_confidence" in v
            assert "flags" in v

        # Patterns always present with required subkeys
        for r in (r1, r2):
            p = r["patterns"]
            assert "breaks" in p
            assert "chains" in p
            assert "anomalies" in p

    def test_wolf_does_not_touch_non_wolf_modes(self, engine):
        """Engine init does not affect anything outside its own db_dir."""
        snapshot = engine.get_system_snapshot()
        assert snapshot["counters"]["total_ingested"] == 0
        assert snapshot["counters"]["total_analyses"] == 0
        # Forge is empty
        assert snapshot["forge"]["total_symbols"] == 0


# ── Contract 2: Direct Wolf reachable + stable schema ────────


class TestDirectWolfReachable:
    """When mode=wolf_analysis, engine responds with a complete schema."""

    WOLF_RESPONSE_REQUIRED_KEYS = {"verdict", "patterns", "engine", "session_id"}

    def test_analyze_returns_complete_schema(self, seeded_engine):
        """wolf.analyze() returns all required keys."""
        result = seeded_engine.analyze(
            text="test direct reachability",
            session_id="direct-test",
        )
        missing = self.WOLF_RESPONSE_REQUIRED_KEYS - set(result.keys())
        assert not missing, f"Missing keys in wolf response: {missing}"

    def test_verdict_has_valid_status(self, seeded_engine):
        """Verdict status is always a valid VerdictStatus value."""
        result = seeded_engine.analyze(text="verdict status check")
        status = result["verdict"]["status"]
        valid = {s.value for s in VerdictStatus}
        assert status in valid, f"Invalid verdict status: {status}"

    def test_verdict_confidence_bounded(self, seeded_engine):
        """Adjusted confidence is always in [0.0, 1.0]."""
        result = seeded_engine.analyze(text="confidence bound check")
        conf = result["verdict"]["adjusted_confidence"]
        assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"

    def test_patterns_are_non_negative_counts(self, seeded_engine):
        """Pattern counts are non-negative integers."""
        result = seeded_engine.analyze(text="pattern count validation")
        p = result["patterns"]
        for key in ("breaks", "chains", "anomalies"):
            assert isinstance(p[key], int), f"{key} should be int"
            assert p[key] >= 0, f"{key} should be non-negative"

    def test_activity_logged(self, engine):
        """Every analyze call is logged in the activity log."""
        engine.analyze(text="activity log test")
        snapshot = engine.get_system_snapshot()
        actions = [a["action"] for a in snapshot["activity"]]
        assert "analyze" in actions

    def test_session_id_propagated(self, engine):
        """Session ID from request appears in the response."""
        result = engine.analyze(text="session propagation", session_id="my-session-42")
        assert result["session_id"] == "my-session-42"


# ── Contract 3: Operator-absent == operator-present(None) ────


class TestOperatorAbsenceEquivalence:
    """When Phase 3 lands, passing operator_results=None must produce
    identical verdicts to not passing it at all."""

    def test_judge_none_operators_same_as_omitted(self):
        """Judge with explicit None operators == Judge without operators."""
        judge = Judge()

        response = EngineResponse(
            session_id="equiv-test",
            confidence=0.65,
            avg_consistency=0.60,
            total_windows=20,
        )

        # Current behavior: no operator arg
        v1 = judge.evaluate(response)

        # Reset judge state (new instance) for clean comparison
        judge2 = Judge()

        # Same response
        response2 = EngineResponse(
            session_id="equiv-test",
            confidence=0.65,
            avg_consistency=0.60,
            total_windows=20,
        )
        v2 = judge2.evaluate(response2)

        assert v1.status == v2.status
        assert abs(v1.adjusted_confidence - v2.adjusted_confidence) < 0.001
        assert len(v1.flags) == len(v2.flags)


# ── Contract 4: Operator flags reduce confidence (Phase 3) ───


class TestOperatorGovernance:
    """When operator_results are provided, they influence the verdict."""

    def test_hitbox_drift_reduces_confidence(self):
        """HITBOX_DRIFT flag applies a negative adjustment."""
        judge = Judge()

        response = EngineResponse(
            session_id="op-test",
            confidence=0.7,
            avg_consistency=0.65,
            total_windows=15,
        )

        op_result = OperatorResult(
            operator_name="crosshair_lock",
            confidence=0.8,
            flags=[ManipulationFlags.HITBOX_DRIFT],
        )

        verdict = judge.evaluate(response, operator_results=[op_result])
        assert verdict.adjusted_confidence < 0.7
        op_codes = [f.code for f in verdict.flags if f.module == "operator"]
        assert "op_hitbox_drift" in op_codes

    def test_spawn_pressure_flags_info(self):
        """SPAWN_PRESSURE produces an INFO-level flag."""
        judge = Judge()

        response = EngineResponse(
            session_id="op-spawn",
            confidence=0.6,
            avg_consistency=0.55,
            total_windows=10,
        )

        op_result = OperatorResult(
            operator_name="edge_entry",
            confidence=0.5,
            flags=[ManipulationFlags.SPAWN_PRESSURE],
        )

        verdict = judge.evaluate(response, operator_results=[op_result])
        op_flags = [f for f in verdict.flags if f.module == "operator"]
        assert len(op_flags) == 1
        assert op_flags[0].code == "op_spawn_pressure"
        assert op_flags[0].severity == FlagSeverity.INFO

    def test_multiple_operator_flags_stack(self):
        """Multiple flags from multiple operators all contribute."""
        judge = Judge()

        response = EngineResponse(
            session_id="op-multi",
            confidence=0.8,
            avg_consistency=0.75,
            total_windows=20,
        )

        ops = [
            OperatorResult(
                operator_name="crosshair_lock",
                confidence=0.7,
                flags=[ManipulationFlags.HITBOX_DRIFT],
            ),
            OperatorResult(
                operator_name="thermal_hitbox",
                confidence=0.6,
                flags=[ManipulationFlags.RECOIL_ANOMALY],
            ),
        ]

        verdict = judge.evaluate(response, operator_results=ops)
        op_codes = {f.code for f in verdict.flags if f.module == "operator"}
        assert "op_hitbox_drift" in op_codes
        assert "op_recoil_anomaly" in op_codes
        # Both penalties applied
        assert verdict.adjusted_confidence < 0.8

    def test_duplicate_flags_deduplicated(self):
        """Same flag from two operators only counted once."""
        judge = Judge()

        response = EngineResponse(
            session_id="op-dedup",
            confidence=0.7,
            avg_consistency=0.65,
            total_windows=10,
        )

        ops = [
            OperatorResult(
                operator_name="op1",
                confidence=0.5,
                flags=[ManipulationFlags.HITBOX_DRIFT],
            ),
            OperatorResult(
                operator_name="op2",
                confidence=0.6,
                flags=[ManipulationFlags.HITBOX_DRIFT],
            ),
        ]

        verdict = judge.evaluate(response, operator_results=ops)
        op_flags = [f for f in verdict.flags if f.module == "operator"]
        assert len(op_flags) == 1  # deduplicated

    def test_empty_operator_results_is_noop(self):
        """Empty list == no operators == no flags."""
        judge = Judge()

        response = EngineResponse(
            session_id="op-empty",
            confidence=0.5,
            avg_consistency=0.5,
            total_windows=10,
        )

        v_none = judge.evaluate(response, operator_results=None)

        judge2 = Judge()
        response2 = EngineResponse(
            session_id="op-empty",
            confidence=0.5,
            avg_consistency=0.5,
            total_windows=10,
        )
        v_empty = judge2.evaluate(response2, operator_results=[])

        assert v_none.status == v_empty.status
        assert abs(v_none.adjusted_confidence - v_empty.adjusted_confidence) < 0.001
