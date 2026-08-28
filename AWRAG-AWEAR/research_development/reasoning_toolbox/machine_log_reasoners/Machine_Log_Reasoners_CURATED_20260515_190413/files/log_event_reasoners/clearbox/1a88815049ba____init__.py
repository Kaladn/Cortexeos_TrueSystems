"""
audio_io operators — FootstepDirectionOperator and AVCorrelationOperator.

Both extend wolf_engine WolfModule (category="operator").
Source logic: Operator #17 (ILD direction) and Operator #18 (AV correlation)
from Lee's Audio Organ spec.
"""

from __future__ import annotations
from typing import Any
from wolf_engine.modules.base import WolfModule
from audio_io.config import DIRECTION_MISMATCH_THRESHOLD_DEG


class FootstepDirectionOperator(WolfModule):
    """
    Operator #17 — Footstep Direction Validator.
    Maps ILD-derived audio direction vs visual player/enemy position.
    Flags if angular difference exceeds threshold.
    Severity: HIGH if >120°, MEDIUM if 60-120°.
    """
    key = "op_footstep_direction"
    name = "Footstep Direction Validator"
    category = "operator"
    description = "ILD stereo direction vs visual position mismatch detector (Op#17)"

    def analyze(self, audio_event: dict, visual_state: dict | None = None) -> dict | None:
        if audio_event.get("sound_type") != "footstep":
            return None
        audio_dir = audio_event.get("direction_deg", 0.0)
        if visual_state is None:
            return None
        # visual_state sectors give us a proxy for where activity is
        sectors = visual_state.get("sectors", {})
        # Estimate visual direction from sector dominance: LEFT=-45, RIGHT=+45
        visual_dir = 0.0
        left_val = sectors.get("LEFT", 0.0)
        right_val = sectors.get("RIGHT", 0.0)
        if abs(left_val - right_val) > 0.5:
            visual_dir = -45.0 if left_val > right_val else 45.0

        diff = abs(audio_dir - visual_dir)
        if diff < DIRECTION_MISMATCH_THRESHOLD_DEG:
            return None

        severity = "HIGH" if diff > 120.0 else "MEDIUM"
        return {
            "operator": self.key,
            "anomaly": "FOOTSTEP_DIRECTION_MISMATCH",
            "audio_direction_deg": audio_dir,
            "visual_direction_deg": visual_dir,
            "angular_diff_deg": round(diff, 2),
            "severity": severity,
            "confidence": min(diff / 180.0, 1.0),
            "sound_type": audio_event.get("sound_type"),
        }

    def info(self) -> dict:
        return {"key": self.key, "name": self.name,
                "category": self.category, "description": self.description}


class SoundClassifierOperator(WolfModule):
    """
    Flags high-confidence sound classification events worth surfacing
    (gunshots, hitmarkers) — passes through footsteps/misc silently.
    """
    key = "op_sound_classifier"
    name = "Sound Classifier Operator"
    category = "operator"
    description = "Surfaces high-confidence combat sound events for the evidence stream"

    ALERT_TYPES = {"gunshot", "hitmarker"}

    def analyze(self, audio_event: dict) -> dict | None:
        stype = audio_event.get("sound_type", "misc")
        if stype not in self.ALERT_TYPES:
            return None
        return {
            "operator":   self.key,
            "anomaly":    "COMBAT_SOUND_DETECTED",
            "sound_type": stype,
            "rms":        audio_event.get("rms"),
            "centroid":   audio_event.get("centroid"),
            "duration_ms": audio_event.get("duration_ms"),
            "confidence": 0.8,
        }

    def info(self) -> dict:
        return {"key": self.key, "name": self.name,
                "category": self.category, "description": self.description}
