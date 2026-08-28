"""
Wolf Engine — Red Team Anomalous Telemetry Test Suite (Phase 5)

Deterministic seed -> deterministic anomalies -> deterministic score.
Multi-layer anomaly injection targeting Wolf's internal evidence/loggers.

Difficulty weights: NEEDLE=5, HARD=3, MED=2, EASY=1
Output: hits, misses, weighted score, Phase 6 backlog items.
"""

from __future__ import annotations

import math
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Ensure plugins/ is on sys.path
_plugins = str(Path(__file__).resolve().parent.parent / "plugins")
if _plugins not in sys.path:
    sys.path.insert(0, _plugins)

import pytest

from wolf_engine.archon.judge import Judge
from wolf_engine.archon.schemas import (
    EngineResponse,
    FlagSeverity,
    GovernanceFlag,
    Verdict,
    VerdictStatus,
)
from wolf_engine.modules.truevision import (
    ManipulationFlags,
    OperatorResult,
)

# ── Constants ────────────────────────────────────────────────

SEED = 1337

# Difficulty weights
NEEDLE = 5
HARD = 3
MED = 2
EASY = 1

# Minimum passing score (percentage of max possible)
TARGET_RATIO = 0.55


# ── Anomaly Manifest ─────────────────────────────────────────

@dataclass
class AnomalySpec:
    """One planted anomaly with expected detection outcome."""
    name: str
    layer: str           # citadel | confidence | temporal | operator | forge | raw_data
    difficulty: int       # EASY / MED / HARD / NEEDLE
    expect_caught: bool   # True if Judge SHOULD catch it
    expect_codes: list[str] = field(default_factory=list)  # expected flag codes
    description: str = ""


MANIFEST: list[AnomalySpec] = [
    # ── Citadel layer (easy catches) ──────────────────────
    AnomalySpec(
        name="nan_confidence",
        layer="citadel", difficulty=EASY, expect_caught=True,
        expect_codes=["nan_confidence"],
        description="NaN confidence value — Citadel quarantine",
    ),
    AnomalySpec(
        name="inf_confidence",
        layer="citadel", difficulty=EASY, expect_caught=True,
        expect_codes=["nan_confidence"],
        description="Inf confidence value — Citadel quarantine",
    ),
    AnomalySpec(
        name="negative_confidence",
        layer="citadel", difficulty=EASY, expect_caught=True,
        expect_codes=["negative_confidence"],
        description="Negative confidence — Citadel quarantine",
    ),

    # ── Citadel layer (medium) ────────────────────────────
    AnomalySpec(
        name="confidence_overflow",
        layer="citadel", difficulty=MED, expect_caught=True,
        expect_codes=["confidence_overflow"],
        description="Confidence 1.7 exceeds valid range",
    ),
    AnomalySpec(
        name="future_timestamp_59min",
        layer="citadel", difficulty=MED, expect_caught=True,
        expect_codes=["future_timestamp"],
        description="Timestamp 59 minutes in future (just under 1h)",
    ),
    AnomalySpec(
        name="zero_windows_nonzero_conf",
        layer="citadel", difficulty=MED, expect_caught=True,
        expect_codes=["empty_analysis"],
        description="Zero analysis windows but claims 0.6 confidence",
    ),

    # ── Confidence governance (medium-hard) ───────────────
    AnomalySpec(
        name="overconfident_blatant",
        layer="confidence", difficulty=MED, expect_caught=True,
        expect_codes=["overconfident"],
        description="Confidence 0.95, consistency 0.1 — obvious mismatch",
    ),
    AnomalySpec(
        name="overconfident_subtle",
        layer="confidence", difficulty=HARD, expect_caught=True,
        expect_codes=["mild_overconfidence"],
        description="Confidence 0.75, consistency 0.35 — caught by soft threshold",
    ),

    # ── Temporal coherence (hard) ─────────────────────────
    AnomalySpec(
        name="flip_flop_obvious",
        layer="temporal", difficulty=HARD, expect_caught=True,
        expect_codes=["flip_flop"],
        description="Confidence swings 0.2 -> 0.9 between sequential requests",
    ),
    AnomalySpec(
        name="oscillation_aba",
        layer="temporal", difficulty=NEEDLE, expect_caught=True,
        expect_codes=["oscillation"],
        description="A->B->A pattern: 0.8 -> 0.2 -> 0.8",
    ),
    AnomalySpec(
        name="slow_oscillation_below_threshold",
        layer="temporal", difficulty=NEEDLE, expect_caught=True,
        expect_codes=["pattern_oscillation"],
        description="Oscillation 0.4 <-> 0.6 — caught by pattern oscillation detector",
    ),

    # ── Confidence calibration drift (needle) ─────────────
    AnomalySpec(
        name="calibration_drift_slow",
        layer="confidence", difficulty=NEEDLE, expect_caught=True,
        expect_codes=["calibration_drift"],
        description="10 requests with avg conf 0.85 vs avg consistency 0.3",
    ),

    # ── Operator governance (hard) ────────────────────────
    AnomalySpec(
        name="operator_stacked_flags",
        layer="operator", difficulty=HARD, expect_caught=True,
        expect_codes=["op_hitbox_drift", "op_recoil_anomaly"],
        description="Two operators with distinct flags — both should register",
    ),
    AnomalySpec(
        name="operator_unknown_flag",
        layer="operator", difficulty=HARD, expect_caught=True,
        expect_codes=["op_unknown_spectral_drift_unknown"],
        description="Unknown flag — caught by unknown-flag catch-all",
    ),

    # ── Citadel deep scan (needles — previously blind) ────
    AnomalySpec(
        name="nested_nan_raw_data",
        layer="raw_data", difficulty=NEEDLE, expect_caught=True,
        expect_codes=["raw_data_nan"],
        description="NaN in raw_data.metrics.sub_score — caught by deep scan",
    ),
    AnomalySpec(
        name="ghost_cooccurrence_forge",
        layer="forge", difficulty=NEEDLE, expect_caught=False,
        expect_codes=[],
        description="Phantom co-occurrence — requires Forge access (P3 backlog)",
    ),
    AnomalySpec(
        name="verdict_replay_fresh_ts",
        layer="raw_data", difficulty=NEEDLE, expect_caught=True,
        expect_codes=["verdict_replay"],
        description="Verdict-shaped data in raw_data — caught by replay detector",
    ),
]


# ── Anomaly Runners ──────────────────────────────────────────

@dataclass
class AnomalyResult:
    spec: AnomalySpec
    caught: bool
    verdict: Verdict | None = None
    flags_found: list[str] = field(default_factory=list)
    note: str = ""


def _run_citadel_nan(rng: random.Random) -> AnomalyResult:
    judge = Judge()
    resp = EngineResponse(session_id="rt-nan", confidence=float("nan"),
                          avg_consistency=0.5, total_windows=10)
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[0], caught="nan_confidence" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_citadel_inf(rng: random.Random) -> AnomalyResult:
    judge = Judge()
    resp = EngineResponse(session_id="rt-inf", confidence=float("inf"),
                          avg_consistency=0.5, total_windows=10)
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[1], caught="nan_confidence" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_citadel_negative(rng: random.Random) -> AnomalyResult:
    judge = Judge()
    resp = EngineResponse(session_id="rt-neg", confidence=-0.3,
                          avg_consistency=0.5, total_windows=10)
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[2], caught="negative_confidence" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_citadel_overflow(rng: random.Random) -> AnomalyResult:
    judge = Judge()
    resp = EngineResponse(session_id="rt-overflow", confidence=1.7,
                          avg_consistency=0.5, total_windows=10)
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[3], caught="confidence_overflow" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_citadel_future_ts(rng: random.Random) -> AnomalyResult:
    judge = Judge()
    future_ts = time.time() + (59 * 60)
    resp = EngineResponse(session_id="rt-future", confidence=0.5,
                          avg_consistency=0.5, total_windows=10,
                          timestamp=future_ts)
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[4], caught="future_timestamp" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_citadel_zero_windows(rng: random.Random) -> AnomalyResult:
    judge = Judge()
    resp = EngineResponse(session_id="rt-zero-win", confidence=0.6,
                          avg_consistency=0.5, total_windows=0)
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[5], caught="empty_analysis" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_overconfident_blatant(rng: random.Random) -> AnomalyResult:
    judge = Judge()
    resp = EngineResponse(session_id="rt-overconf", confidence=0.95,
                          avg_consistency=0.1, total_windows=20)
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[6], caught="overconfident" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_overconfident_subtle(rng: random.Random) -> AnomalyResult:
    """Subtle mismatch: conf=0.75, consistency=0.35 — caught by mild threshold."""
    judge = Judge()
    resp = EngineResponse(session_id="rt-subtle", confidence=0.75,
                          avg_consistency=0.35, total_windows=20)
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[7],
        caught="overconfident" in codes or "mild_overconfidence" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_flip_flop(rng: random.Random) -> AnomalyResult:
    """Two sequential requests with >0.4 confidence delta on same session."""
    judge = Judge()
    sid = "rt-flipflop"
    resp1 = EngineResponse(session_id=sid, confidence=0.2,
                           avg_consistency=0.2, total_windows=10)
    judge.evaluate(resp1)
    resp2 = EngineResponse(session_id=sid, confidence=0.9,
                           avg_consistency=0.9, total_windows=10)
    verdict = judge.evaluate(resp2)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[8], caught="flip_flop" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_oscillation_aba(rng: random.Random) -> AnomalyResult:
    """A->B->A oscillation: 0.8 -> 0.2 -> 0.8."""
    judge = Judge()
    sid = "rt-oscillate"
    resp1 = EngineResponse(session_id=sid, confidence=0.8,
                           avg_consistency=0.8, total_windows=10)
    judge.evaluate(resp1)
    resp2 = EngineResponse(session_id=sid, confidence=0.2,
                           avg_consistency=0.2, total_windows=10)
    judge.evaluate(resp2)
    resp3 = EngineResponse(session_id=sid, confidence=0.8,
                           avg_consistency=0.8, total_windows=10)
    verdict = judge.evaluate(resp3)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[9], caught="oscillation" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_slow_oscillation(rng: random.Random) -> AnomalyResult:
    """Oscillation 0.4<->0.6 — caught by pattern oscillation detector."""
    judge = Judge()
    sid = "rt-slow-osc"
    for i in range(10):
        conf = 0.4 if i % 2 == 0 else 0.6
        resp = EngineResponse(session_id=sid, confidence=conf,
                              avg_consistency=conf, total_windows=10)
        verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[10],
        caught=any(c in codes for c in ["flip_flop", "oscillation", "pattern_oscillation"]),
        verdict=verdict, flags_found=codes,
    )


def _run_calibration_drift(rng: random.Random) -> AnomalyResult:
    """10 requests where avg confidence >> avg consistency -> drift flag."""
    judge = Judge()
    for i in range(12):
        resp = EngineResponse(
            session_id=f"rt-drift-{i}",
            confidence=0.85 + rng.uniform(-0.05, 0.05),
            avg_consistency=0.30 + rng.uniform(-0.05, 0.05),
            total_windows=15,
        )
        verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[11], caught="calibration_drift" in codes,
        verdict=verdict, flags_found=codes,
    )


def _run_operator_stacked(rng: random.Random) -> AnomalyResult:
    """Two operators with distinct flags — both should register."""
    judge = Judge()
    resp = EngineResponse(session_id="rt-op-stack", confidence=0.8,
                          avg_consistency=0.75, total_windows=20)
    ops = [
        OperatorResult(operator_name="crosshair_lock", confidence=0.7,
                       flags=[ManipulationFlags.HITBOX_DRIFT]),
        OperatorResult(operator_name="thermal_hitbox", confidence=0.6,
                       flags=[ManipulationFlags.RECOIL_ANOMALY]),
    ]
    verdict = judge.evaluate(resp, operator_results=ops)
    codes = [f.code for f in verdict.flags if f.module == "operator"]
    has_both = "op_hitbox_drift" in codes and "op_recoil_anomaly" in codes
    return AnomalyResult(
        spec=MANIFEST[12], caught=has_both,
        verdict=verdict, flags_found=codes,
    )


def _run_operator_unknown_flag(rng: random.Random) -> AnomalyResult:
    """Unknown flag — caught by unknown-flag catch-all."""
    judge = Judge()
    resp = EngineResponse(session_id="rt-op-unk", confidence=0.7,
                          avg_consistency=0.65, total_windows=15)

    class FakeFlag:
        value = "spectral_drift_unknown"

    op = OperatorResult(operator_name="phantom_op", confidence=0.5)
    op.flags = [FakeFlag()]

    verdict = judge.evaluate(resp, operator_results=[op])
    op_codes = [f.code for f in verdict.flags if f.module == "operator"]
    return AnomalyResult(
        spec=MANIFEST[13], caught=len(op_codes) > 0,
        verdict=verdict, flags_found=op_codes,
    )


def _run_nested_nan_raw_data(rng: random.Random) -> AnomalyResult:
    """NaN buried in raw_data — caught by Citadel deep scan."""
    judge = Judge()
    resp = EngineResponse(
        session_id="rt-nested-nan", confidence=0.6,
        avg_consistency=0.55, total_windows=15,
        raw_data={"metrics": {"sub_score": float("nan"), "valid": True}},
    )
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    nan_related = [c for c in codes if "nan" in c]
    return AnomalyResult(
        spec=MANIFEST[14], caught=len(nan_related) > 0,
        verdict=verdict, flags_found=codes,
        note="NaN in raw_data.metrics.sub_score — caught by deep scan",
    )


def _run_ghost_cooccurrence(rng: random.Random) -> AnomalyResult:
    """Phantom co-occurrence data — Judge doesn't audit Forge state."""
    judge = Judge()
    resp = EngineResponse(
        session_id="rt-ghost", confidence=0.65,
        avg_consistency=0.60, total_windows=20,
        raw_data={"forge_ghost": {"phantom_symbol": 99999, "resonance": 0.99}},
    )
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[15],
        caught=len(codes) > 0 and any("ghost" in c or "forge" in c for c in codes),
        verdict=verdict, flags_found=codes,
        note="Ghost co-occurrence in forge — still a blind spot (P3)",
    )


def _run_verdict_replay(rng: random.Random) -> AnomalyResult:
    """Replayed verdict dict — caught by replay detector."""
    judge = Judge()
    fake_verdict = {
        "verdict_id": "replayed-fake-id",
        "status": "approved",
        "adjusted_confidence": 0.99,
        "timestamp": time.time(),
    }
    resp = EngineResponse(
        session_id="rt-replay", confidence=0.5,
        avg_consistency=0.5, total_windows=10,
        raw_data={"previous_verdict": fake_verdict},
    )
    verdict = judge.evaluate(resp)
    codes = [f.code for f in verdict.flags]
    return AnomalyResult(
        spec=MANIFEST[16], caught=any("replay" in c for c in codes),
        verdict=verdict, flags_found=codes,
        note="Verdict replay in raw_data — caught by replay detector",
    )


# Runner dispatch table (ordered same as MANIFEST)
_RUNNERS = [
    _run_citadel_nan,
    _run_citadel_inf,
    _run_citadel_negative,
    _run_citadel_overflow,
    _run_citadel_future_ts,
    _run_citadel_zero_windows,
    _run_overconfident_blatant,
    _run_overconfident_subtle,
    _run_flip_flop,
    _run_oscillation_aba,
    _run_slow_oscillation,
    _run_calibration_drift,
    _run_operator_stacked,
    _run_operator_unknown_flag,
    _run_nested_nan_raw_data,
    _run_ghost_cooccurrence,
    _run_verdict_replay,
]


# ── Scoring Engine ───────────────────────────────────────────

@dataclass
class RedTeamReport:
    """Full red team run output."""
    seed: int
    total_anomalies: int
    hits: list[str]
    misses: list[str]
    expected_misses: list[str]   # Planned blind spots
    unexpected_misses: list[str] # Should have caught but didn't
    unexpected_hits: list[str]   # Caught something we didn't expect
    weighted_score: int
    max_possible: int
    score_ratio: float
    backlog: list[dict]          # Phase 6 items


def score_and_diagnose(results: list[AnomalyResult]) -> RedTeamReport:
    """Score all anomaly results, generate Phase 6 backlog from misses."""
    hits = []
    misses = []
    expected_misses = []
    unexpected_misses = []
    unexpected_hits = []
    weighted_score = 0
    max_possible = 0
    backlog = []

    for r in results:
        spec = r.spec
        if spec.expect_caught:
            max_possible += spec.difficulty
            if r.caught:
                hits.append(spec.name)
                weighted_score += spec.difficulty
            else:
                misses.append(spec.name)
                unexpected_misses.append(spec.name)
                backlog.append({
                    "anomaly": spec.name,
                    "layer": spec.layer,
                    "difficulty": spec.difficulty,
                    "description": spec.description,
                    "action": f"Add governance check for {spec.layer} layer: {spec.name}",
                })
        else:
            # Expected blind spot — if Judge catches it, that's a bonus
            if r.caught:
                unexpected_hits.append(spec.name)
                weighted_score += spec.difficulty  # Bonus points
            else:
                expected_misses.append(spec.name)

    ratio = weighted_score / max_possible if max_possible > 0 else 0.0

    return RedTeamReport(
        seed=SEED,
        total_anomalies=len(results),
        hits=hits,
        misses=misses,
        expected_misses=expected_misses,
        unexpected_misses=unexpected_misses,
        unexpected_hits=unexpected_hits,
        weighted_score=weighted_score,
        max_possible=max_possible,
        score_ratio=ratio,
        backlog=backlog,
    )


# ── Test Functions ───────────────────────────────────────────


class TestRedTeamSeededAnomalies:
    """Full red team run: plant anomalies, score, diagnose."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.rng = random.Random(SEED)
        self.results: list[AnomalyResult] = []
        for runner in _RUNNERS:
            self.results.append(runner(self.rng))
        self.report = score_and_diagnose(self.results)

    def test_all_runners_executed(self):
        """Every anomaly in the manifest was tested."""
        assert len(self.results) == len(MANIFEST)

    def test_weighted_score_meets_target(self):
        """Governance catches enough anomalies to meet target ratio."""
        assert self.report.score_ratio >= TARGET_RATIO, (
            f"Score {self.report.weighted_score}/{self.report.max_possible} "
            f"({self.report.score_ratio:.1%}) below target {TARGET_RATIO:.0%}.\n"
            f"Unexpected misses: {self.report.unexpected_misses}"
        )

    def test_no_unexpected_misses(self):
        """Every anomaly expected to be caught WAS caught."""
        assert len(self.report.unexpected_misses) == 0, (
            f"Governance missed expected catches: {self.report.unexpected_misses}"
        )

    def test_expected_blind_spots_documented(self):
        """Known blind spots are confirmed as misses."""
        blind_spots = {"ghost_cooccurrence_forge"}
        for name in blind_spots:
            assert name in self.report.expected_misses or name in self.report.unexpected_hits, (
                f"Blind spot {name} not accounted for in report"
            )

    def test_backlog_empty_when_governance_holds(self):
        """If governance catches everything it should, backlog is empty."""
        assert len(self.report.backlog) == 0, (
            f"Phase 6 backlog has {len(self.report.backlog)} items: "
            f"{[b['anomaly'] for b in self.report.backlog]}"
        )


class TestRedTeamCitadelLayer:
    """Individual citadel anomaly checks."""

    def test_nan_quarantined(self):
        result = _run_citadel_nan(random.Random(SEED))
        assert result.caught
        assert result.verdict.status == VerdictStatus.QUARANTINED

    def test_inf_quarantined(self):
        result = _run_citadel_inf(random.Random(SEED))
        assert result.caught
        assert result.verdict.status == VerdictStatus.QUARANTINED

    def test_negative_quarantined(self):
        result = _run_citadel_negative(random.Random(SEED))
        assert result.caught
        assert result.verdict.status == VerdictStatus.QUARANTINED

    def test_overflow_quarantined(self):
        result = _run_citadel_overflow(random.Random(SEED))
        assert result.caught
        assert result.verdict.status == VerdictStatus.QUARANTINED

    def test_future_timestamp_caught(self):
        result = _run_citadel_future_ts(random.Random(SEED))
        assert result.caught

    def test_zero_windows_flagged(self):
        result = _run_citadel_zero_windows(random.Random(SEED))
        assert result.caught

    def test_nested_nan_raw_data_detected(self):
        """NaN in raw_data.metrics — Citadel deep scan catches it."""
        result = _run_nested_nan_raw_data(random.Random(SEED))
        assert result.caught
        assert "raw_data_nan" in result.flags_found

    def test_verdict_replay_detected(self):
        """Verdict-shaped dict in raw_data — replay detector catches it."""
        result = _run_verdict_replay(random.Random(SEED))
        assert result.caught
        assert "verdict_replay" in result.flags_found


class TestRedTeamConfidenceLayer:
    """Confidence governance anomaly checks."""

    def test_blatant_overconfidence_flagged(self):
        result = _run_overconfident_blatant(random.Random(SEED))
        assert result.caught
        assert "overconfident" in result.flags_found

    def test_subtle_overconfidence_flagged(self):
        """Gap 0.40 caught by mild_overconfidence soft threshold."""
        result = _run_overconfident_subtle(random.Random(SEED))
        assert result.caught
        assert "mild_overconfidence" in result.flags_found


class TestRedTeamTemporalLayer:
    """Temporal coherence anomaly checks."""

    def test_flip_flop_detected(self):
        result = _run_flip_flop(random.Random(SEED))
        assert result.caught
        assert result.verdict.status == VerdictStatus.PENALIZED

    def test_oscillation_aba_detected(self):
        result = _run_oscillation_aba(random.Random(SEED))
        assert result.caught
        assert "oscillation" in result.flags_found

    def test_slow_oscillation_detected(self):
        """Delta 0.2 caught by pattern oscillation detector."""
        result = _run_slow_oscillation(random.Random(SEED))
        assert result.caught
        assert "pattern_oscillation" in result.flags_found
        assert result.verdict.status == VerdictStatus.PENALIZED


class TestRedTeamOperatorLayer:
    """Operator governance anomaly checks."""

    def test_stacked_flags_both_register(self):
        result = _run_operator_stacked(random.Random(SEED))
        assert result.caught
        assert "op_hitbox_drift" in result.flags_found
        assert "op_recoil_anomaly" in result.flags_found

    def test_unknown_flag_caught(self):
        """Unknown flag produces INFO-level audit trail entry."""
        result = _run_operator_unknown_flag(random.Random(SEED))
        assert result.caught
        assert "op_unknown_spectral_drift_unknown" in result.flags_found


class TestRedTeamBlindSpots:
    """Remaining governance blind spots — P3 backlog."""

    def test_ghost_cooccurrence_undetected(self):
        """Phantom forge data is invisible to Judge (requires Forge access)."""
        result = _run_ghost_cooccurrence(random.Random(SEED))
        assert not result.caught


class TestRedTeamReportIntegrity:
    """Meta-tests: the scoring engine itself is correct."""

    def test_report_seed_matches(self):
        rng = random.Random(SEED)
        results = [runner(rng) for runner in _RUNNERS]
        report = score_and_diagnose(results)
        assert report.seed == SEED

    def test_hits_plus_misses_equals_expected_catches(self):
        rng = random.Random(SEED)
        results = [runner(rng) for runner in _RUNNERS]
        report = score_and_diagnose(results)
        expected_catches = [s for s in MANIFEST if s.expect_caught]
        assert len(report.hits) + len(report.unexpected_misses) == len(expected_catches)

    def test_max_possible_is_sum_of_expected_difficulties(self):
        rng = random.Random(SEED)
        results = [runner(rng) for runner in _RUNNERS]
        report = score_and_diagnose(results)
        expected_max = sum(s.difficulty for s in MANIFEST if s.expect_caught)
        assert report.max_possible == expected_max

    def test_deterministic_across_runs(self):
        """Two runs with same seed produce identical scores."""
        rng1 = random.Random(SEED)
        results1 = [runner(rng1) for runner in _RUNNERS]
        report1 = score_and_diagnose(results1)

        rng2 = random.Random(SEED)
        results2 = [runner(rng2) for runner in _RUNNERS]
        report2 = score_and_diagnose(results2)

        assert report1.weighted_score == report2.weighted_score
        assert report1.hits == report2.hits
        assert report1.misses == report2.misses
