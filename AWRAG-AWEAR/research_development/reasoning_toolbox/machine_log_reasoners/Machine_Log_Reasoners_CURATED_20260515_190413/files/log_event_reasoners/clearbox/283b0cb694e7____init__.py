"""
av_security operators — Operator #18: Audio-Visual Correlation Detector.

Consumes fused event streams from visual_io and audio_io sessions.
Detects 4 anomaly types: PHANTOM_AUDIO, SILENT_VISUAL,
DELAYED_CORRELATION, DIRECTION_MISMATCH.
"""

from __future__ import annotations
from typing import Any
from wolf_engine.modules.base import WolfModule
from av_security.config import (
    CORRELATION_WINDOW_MS, DELAYED_CORRELATION_THRESHOLD_MS,
    CONFIDENCE_THRESHOLD, DIRECTION_MISMATCH_THRESHOLD_DEG,
    ANOMALY_PHANTOM_AUDIO, ANOMALY_SILENT_VISUAL,
    ANOMALY_DELAYED_CORRELATION, ANOMALY_DIRECTION_MISMATCH,
)


class AVCorrelationOperator(WolfModule):
    """
    Operator #18 — Audio-Visual Correlation Detector.
    Pairs audio chunks with visual frames by timestamp.
    Flags phantom audio, silent visuals, delayed correlation, direction mismatch.
    """
    key = "op_av_correlation"
    name = "AV Correlation Detector"
    category = "operator"
    description = "Detects AV timing/direction mismatches — phantom audio, silent visuals, lag"

    def analyze_pair(
        self,
        audio_event: dict,
        visual_event: dict | None,
    ) -> list[dict[str, Any]]:
        """
        Analyze one audio event against its nearest visual event.
        Returns list of anomaly dicts (0, 1, or more).
        """
        findings = []
        audio_t = audio_event.get("timestamp", {}).get("wall_clock", 0.0)
        audio_dir = audio_event.get("data", {}).get("direction_deg", 0.0)
        audio_rms = audio_event.get("data", {}).get("rms", 0.0)
        sound_type = audio_event.get("data", {}).get("sound_type", "misc")

        if visual_event is None:
            # Sound with no nearby visual event
            if audio_rms > 0.05:
                findings.append({
                    "operator": self.key,
                    "anomaly":  ANOMALY_PHANTOM_AUDIO,
                    "sound_type": sound_type,
                    "audio_t":  audio_t,
                    "audio_rms": audio_rms,
                    "confidence": min(audio_rms * 10, CONFIDENCE_THRESHOLD),
                })
            return findings

        visual_t = visual_event.get("timestamp", {}).get("wall_clock", 0.0)
        av_delay_ms = abs(audio_t - visual_t) * 1000.0

        # Delayed correlation
        if av_delay_ms > DELAYED_CORRELATION_THRESHOLD_MS:
            findings.append({
                "operator":   self.key,
                "anomaly":    ANOMALY_DELAYED_CORRELATION,
                "av_delay_ms": round(av_delay_ms, 2),
                "audio_t":    audio_t,
                "visual_t":   visual_t,
                "confidence": min(av_delay_ms / 200.0, 1.0),
            })

        # Direction mismatch
        visual_sectors = visual_event.get("data", {}).get("sectors", {})
        left_val = visual_sectors.get("LEFT", 0.0)
        right_val = visual_sectors.get("RIGHT", 0.0)
        visual_dir = 0.0
        if abs(left_val - right_val) > 0.3:
            visual_dir = -45.0 if left_val > right_val else 45.0

        dir_diff = abs(audio_dir - visual_dir)
        if dir_diff > DIRECTION_MISMATCH_THRESHOLD_DEG:
            findings.append({
                "operator":         self.key,
                "anomaly":          ANOMALY_DIRECTION_MISMATCH,
                "audio_dir_deg":    audio_dir,
                "visual_dir_deg":   visual_dir,
                "angular_diff_deg": round(dir_diff, 2),
                "confidence":       min(dir_diff / 180.0, 1.0),
            })

        return findings

    def info(self) -> dict:
        return {"key": self.key, "name": self.name,
                "category": self.category, "description": self.description}


class SilentVisualOperator(WolfModule):
    """
    Detects visual anomaly events (HIGH_ENTROPY, VECTOR_ANOMALY)
    that have no corresponding audio — silent visual events.
    """
    key = "op_silent_visual"
    name = "Silent Visual Operator"
    category = "operator"
    description = "Flags visual anomaly frames with no corresponding audio event"

    def analyze_pair(
        self,
        visual_event: dict,
        audio_event: dict | None,
    ) -> dict[str, Any] | None:
        flags = visual_event.get("data", {}).get("anomaly_metrics", {}).get("anomaly_flags", [])
        if not flags:
            return None
        if audio_event is not None:
            return None
        visual_t = visual_event.get("timestamp", {}).get("wall_clock", 0.0)
        return {
            "operator":    self.key,
            "anomaly":     ANOMALY_SILENT_VISUAL,
            "visual_t":    visual_t,
            "flags":       flags,
            "frame_id":    visual_event.get("data", {}).get("frame_id"),
            "confidence":  len(flags) / 3.0,
        }

    def info(self) -> dict:
        return {"key": self.key, "name": self.name,
                "category": self.category, "description": self.description}
