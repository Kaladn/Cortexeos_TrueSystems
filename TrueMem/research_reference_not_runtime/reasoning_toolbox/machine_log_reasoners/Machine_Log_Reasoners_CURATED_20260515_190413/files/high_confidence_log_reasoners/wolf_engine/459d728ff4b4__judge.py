"""
Archon Judge — Four governance modules for single-engine quality.

1. Confidence Governance: Calibrates engine confidence against historical
   accuracy. Flags overconfident or underconfident results.

2. Temporal Coherence (TCM): Penalizes verdict flip-flopping across
   sequential requests for the same session.

3. Citadel Isolation: Quarantines anomalous results (NaN confidence,
   empty causal chains, impossible timestamps).

4. Operator Governance: Evaluates TrueVision operator flags (HITBOX_DRIFT,
   SPAWN_PRESSURE, etc.) when operator_results are provided. No-op when None.
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict

from wolf_engine.archon.schemas import (
    EngineResponse,
    FlagSeverity,
    GovernanceFlag,
    Verdict,
    VerdictStatus,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# Helpers
# ===========================================================================


def _scan_nan(obj, prefix: str = "") -> list[str]:
    """Recursively find NaN/Inf values in nested dicts/lists."""
    paths: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            paths.extend(_scan_nan(v, f"{prefix}.{k}"))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            paths.extend(_scan_nan(v, f"{prefix}[{i}]"))
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            paths.append(prefix)
    return paths


def _scan_verdict_shapes(obj, prefix: str = "") -> list[str]:
    """Find dict values that look like verdict objects (replay detection)."""
    paths: list[str] = []
    if isinstance(obj, dict):
        has_vid = "verdict_id" in obj
        has_extra = "status" in obj or "adjusted_confidence" in obj
        if has_vid and has_extra:
            paths.append(prefix or "root")
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                paths.extend(_scan_verdict_shapes(v, f"{prefix}.{k}"))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                paths.extend(_scan_verdict_shapes(v, f"{prefix}[{i}]"))
    return paths


# ===========================================================================
# Module 1: Confidence Governance
# ===========================================================================


class ConfidenceGovernance:
    """
    Calibrates engine confidence against a running accuracy baseline.

    Tracks historical confidence vs actual outcome quality (approximated
    by consistency scores). Flags results that deviate significantly
    from the calibration curve.
    """

    def __init__(self, history_size: int = 100):
        self._history: list[tuple[float, float]] = []  # (confidence, consistency)
        self._history_size = history_size

    def evaluate(self, response: EngineResponse) -> list[GovernanceFlag]:
        flags = []
        conf = response.confidence
        consistency = response.avg_consistency

        # Record for calibration
        self._history.append((conf, consistency))
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size:]

        # Check for overconfidence: high confidence but low consistency
        if conf > 0.8 and consistency < 0.3:
            flags.append(GovernanceFlag(
                module="confidence",
                severity=FlagSeverity.WARNING,
                code="overconfident",
                message=f"Confidence {conf:.2f} but consistency only {consistency:.2f}",
                adjustment=-0.3,
            ))

        # Mild overconfidence: significant gap below hard thresholds
        elif (conf - consistency) > 0.35 and conf > 0.6:
            flags.append(GovernanceFlag(
                module="confidence",
                severity=FlagSeverity.INFO,
                code="mild_overconfidence",
                message=f"Confidence-consistency gap: {conf:.2f} vs {consistency:.2f}",
                adjustment=0.0,
            ))

        # Check for underconfidence: low confidence but high consistency
        if conf < 0.3 and consistency > 0.7:
            flags.append(GovernanceFlag(
                module="confidence",
                severity=FlagSeverity.INFO,
                code="underconfident",
                message=f"Confidence {conf:.2f} but consistency is {consistency:.2f}",
                adjustment=0.2,
            ))

        # Calibration check: if we have enough history, check drift
        if len(self._history) >= 10:
            avg_conf = sum(h[0] for h in self._history) / len(self._history)
            avg_cons = sum(h[1] for h in self._history) / len(self._history)
            drift = abs(avg_conf - avg_cons)
            if drift > 0.4:
                flags.append(GovernanceFlag(
                    module="confidence",
                    severity=FlagSeverity.WARNING,
                    code="calibration_drift",
                    message=f"Avg confidence {avg_conf:.2f} vs avg consistency {avg_cons:.2f} (drift {drift:.2f})",
                    adjustment=0.0,
                ))

        return flags


# ===========================================================================
# Module 2: Temporal Coherence (TCM)
# ===========================================================================


class TemporalCoherence:
    """
    Penalizes verdict flip-flopping across sequential requests.

    Tracks the last N verdicts per session. If confidence swings wildly
    between requests (>0.4 delta), applies a stability penalty.
    """

    def __init__(self, max_swing: float = 0.4, penalty: float = -0.15):
        self.max_swing = max_swing
        self.penalty = penalty
        self._session_history: dict[str, list[float]] = defaultdict(list)

    def evaluate(self, response: EngineResponse) -> list[GovernanceFlag]:
        flags = []
        sid = response.session_id
        conf = response.confidence

        history = self._session_history[sid]
        if history:
            last_conf = history[-1]
            delta = abs(conf - last_conf)
            if delta > self.max_swing:
                flags.append(GovernanceFlag(
                    module="temporal",
                    severity=FlagSeverity.WARNING,
                    code="flip_flop",
                    message=f"Confidence swung {delta:.2f} (from {last_conf:.2f} to {conf:.2f})",
                    adjustment=self.penalty,
                ))

            # Check for oscillation pattern (A→B→A)
            if len(history) >= 2:
                prev_prev = history[-2]
                if abs(conf - prev_prev) < 0.1 and delta > self.max_swing:
                    flags.append(GovernanceFlag(
                        module="temporal",
                        severity=FlagSeverity.CRITICAL,
                        code="oscillation",
                        message=f"Oscillation detected: {prev_prev:.2f} → {last_conf:.2f} → {conf:.2f}",
                        adjustment=self.penalty * 2,
                    ))

        history.append(conf)

        # Pattern oscillation: systematic alternation below individual threshold
        if len(history) >= 7:
            recent = history[-7:]
            deltas = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
            sign_changes = 0
            for i in range(1, len(deltas)):
                if abs(deltas[i]) > 0.01 and abs(deltas[i - 1]) > 0.01:
                    if (deltas[i] > 0) != (deltas[i - 1] > 0):
                        sign_changes += 1
            if sign_changes >= 4:
                flags.append(GovernanceFlag(
                    module="temporal",
                    severity=FlagSeverity.WARNING,
                    code="pattern_oscillation",
                    message=f"Systematic oscillation: {sign_changes} direction reversals in 7 requests",
                    adjustment=-0.10,
                ))

        # Keep bounded
        if len(history) > 20:
            self._session_history[sid] = history[-20:]

        return flags


# ===========================================================================
# Module 3: Citadel Isolation
# ===========================================================================


class CitadelIsolation:
    """
    Quarantines anomalous results that should never propagate downstream.

    Checks for:
      - NaN/Inf confidence values
      - Negative confidence
      - Confidence > 1.0 (impossible range)
      - Zero windows with non-zero confidence
      - Future timestamps
    """

    def evaluate(self, response: EngineResponse) -> list[GovernanceFlag]:
        flags = []

        # NaN/Inf check
        if math.isnan(response.confidence) or math.isinf(response.confidence):
            flags.append(GovernanceFlag(
                module="citadel",
                severity=FlagSeverity.CRITICAL,
                code="nan_confidence",
                message=f"Confidence is {response.confidence} — quarantined",
                adjustment=0.0,
            ))

        # Range check
        if response.confidence < 0.0:
            flags.append(GovernanceFlag(
                module="citadel",
                severity=FlagSeverity.CRITICAL,
                code="negative_confidence",
                message=f"Confidence is {response.confidence} — impossible value",
                adjustment=0.0,
            ))

        if response.confidence > 1.0:
            flags.append(GovernanceFlag(
                module="citadel",
                severity=FlagSeverity.CRITICAL,
                code="confidence_overflow",
                message=f"Confidence {response.confidence} exceeds 1.0 — clamped",
                adjustment=0.0,
            ))

        # Logical contradiction: no windows but claims confidence
        if response.total_windows == 0 and response.confidence > 0.0:
            flags.append(GovernanceFlag(
                module="citadel",
                severity=FlagSeverity.WARNING,
                code="empty_analysis",
                message="Non-zero confidence with zero windows",
                adjustment=0.0,
            ))

        # Future timestamp
        if response.timestamp > time.time() + 60:
            flags.append(GovernanceFlag(
                module="citadel",
                severity=FlagSeverity.CRITICAL,
                code="future_timestamp",
                message=f"Timestamp {response.timestamp} is in the future",
                adjustment=0.0,
            ))

        # Deep NaN/Inf scan of raw_data
        if response.raw_data:
            nan_paths = _scan_nan(response.raw_data, "raw_data")
            if nan_paths:
                flags.append(GovernanceFlag(
                    module="citadel",
                    severity=FlagSeverity.WARNING,
                    code="raw_data_nan",
                    message=f"NaN/Inf found at: {', '.join(nan_paths[:5])}",
                    adjustment=0.0,
                ))

        # Verdict replay detection
        if response.raw_data:
            replay_paths = _scan_verdict_shapes(response.raw_data, "raw_data")
            if replay_paths:
                flags.append(GovernanceFlag(
                    module="citadel",
                    severity=FlagSeverity.WARNING,
                    code="verdict_replay",
                    message=f"Verdict-shaped data at: {', '.join(replay_paths[:3])}",
                    adjustment=0.0,
                ))

        return flags


# ===========================================================================
# Module 4: Operator Governance (TrueVision)
# ===========================================================================


class OperatorGovernance:
    """
    Evaluates TrueVision operator flags and maps them to confidence penalties.

    Only runs when operator_results are provided. When None, produces no flags
    (zero behavioral change from pre-Phase-3 behavior).

    Penalty map is deliberately conservative — operators flag suspicion,
    they don't convict.
    """

    # flag → (code, penalty, severity)
    _PENALTY_MAP = {
        "hitbox_drift":    ("op_hitbox_drift",    -0.10, FlagSeverity.WARNING),
        "aim_snap":        ("op_aim_snap",        -0.12, FlagSeverity.WARNING),
        "spawn_pressure":  ("op_spawn_pressure",  -0.05, FlagSeverity.INFO),
        "spawn_flood":     ("op_spawn_flood",     -0.08, FlagSeverity.WARNING),
        "recoil_anomaly":  ("op_recoil_anomaly",  -0.07, FlagSeverity.WARNING),
        "timing_anomaly":  ("op_timing_anomaly",  -0.06, FlagSeverity.INFO),
    }

    def evaluate(self, operator_results: list | None) -> list[GovernanceFlag]:
        if not operator_results:
            return []

        flags: list[GovernanceFlag] = []
        seen_codes: set[str] = set()

        for result in operator_results:
            op_flags = getattr(result, "flags", [])
            for flag in op_flags:
                flag_val = flag.value if hasattr(flag, "value") else str(flag)
                if flag_val in self._PENALTY_MAP and flag_val not in seen_codes:
                    code, penalty, severity = self._PENALTY_MAP[flag_val]
                    seen_codes.add(flag_val)
                    flags.append(GovernanceFlag(
                        module="operator",
                        severity=severity,
                        code=code,
                        message=f"TrueVision operator flagged: {flag_val}",
                        adjustment=penalty,
                    ))
                elif flag_val not in self._PENALTY_MAP and flag_val not in seen_codes:
                    seen_codes.add(flag_val)
                    flags.append(GovernanceFlag(
                        module="operator",
                        severity=FlagSeverity.INFO,
                        code=f"op_unknown_{flag_val}",
                        message=f"Unmapped operator flag: {flag_val}",
                        adjustment=0.0,
                    ))

        return flags


# ===========================================================================
# Judge Pipeline
# ===========================================================================


class Judge:
    """
    Runs all governance modules and produces a final Verdict.

    Pipeline: Citadel (quarantine check) → Confidence → Temporal → Verdict
    If Citadel quarantines, skip remaining modules.
    """

    def __init__(self):
        self.citadel = CitadelIsolation()
        self.confidence = ConfidenceGovernance()
        self.temporal = TemporalCoherence()
        self.operator = OperatorGovernance()

    def evaluate(self, response: EngineResponse,
                 operator_results: list | None = None) -> Verdict:
        all_flags: list[GovernanceFlag] = []

        # Stage 1: Citadel (quarantine gate)
        citadel_flags = self.citadel.evaluate(response)
        all_flags.extend(citadel_flags)

        quarantined = any(
            f.severity == FlagSeverity.CRITICAL for f in citadel_flags
        )

        if quarantined:
            return Verdict(
                request_id=response.request_id,
                session_id=response.session_id,
                status=VerdictStatus.QUARANTINED,
                original_confidence=response.confidence,
                adjusted_confidence=0.0,
                flags=all_flags,
            )

        # Stage 2: Confidence calibration
        conf_flags = self.confidence.evaluate(response)
        all_flags.extend(conf_flags)

        # Stage 3: Temporal coherence
        temporal_flags = self.temporal.evaluate(response)
        all_flags.extend(temporal_flags)

        # Stage 4: Operator governance (no-op when None)
        op_flags = self.operator.evaluate(operator_results)
        all_flags.extend(op_flags)

        # Compute adjusted confidence
        adjusted = response.confidence
        for flag in all_flags:
            adjusted += flag.adjustment
        adjusted = max(0.0, min(1.0, adjusted))  # Clamp to [0, 1]

        # Determine status
        if any(f.code in ("flip_flop", "oscillation", "pattern_oscillation") for f in all_flags):
            status = VerdictStatus.PENALIZED
        elif abs(adjusted - response.confidence) > 0.01:
            status = VerdictStatus.ADJUSTED
        else:
            status = VerdictStatus.APPROVED

        return Verdict(
            request_id=response.request_id,
            session_id=response.session_id,
            status=status,
            original_confidence=response.confidence,
            adjusted_confidence=adjusted,
            flags=all_flags,
        )
