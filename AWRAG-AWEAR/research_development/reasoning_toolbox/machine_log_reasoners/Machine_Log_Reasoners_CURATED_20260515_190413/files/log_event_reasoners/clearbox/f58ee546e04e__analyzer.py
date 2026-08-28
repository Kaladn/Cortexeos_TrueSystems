"""
AVAnalyzer — correlates fused visual_io and audio_io JSONL event streams.

Reads two fused_events.jsonl files (one per plugin session),
pairs events by timestamp within CORRELATION_WINDOW_MS,
runs operators, returns findings list.
"""

from __future__ import annotations
import logging
from typing import Any

from wolf_engine.evidence.fusion import read_fused_events
from av_security.config import CORRELATION_WINDOW_MS
from av_security.core.operators import AVCorrelationOperator, SilentVisualOperator

logger = logging.getLogger(__name__)

_av_op = AVCorrelationOperator()
_sv_op = SilentVisualOperator()


def correlate_sessions(
    visual_session_dir: str,
    audio_session_dir: str,
) -> list[dict[str, Any]]:
    """
    Load both event streams, pair by wall_clock proximity,
    run all operators. Returns list of anomaly findings.
    """
    visual_events = read_fused_events(visual_session_dir)
    audio_events  = read_fused_events(audio_session_dir)

    # Filter to relevant event types
    frames = [e for e in visual_events if e.event_type == "screen_vector_state"]
    chunks = [e for e in audio_events  if e.event_type == "audio_chunk"]

    findings: list[dict] = []
    window_sec = CORRELATION_WINDOW_MS / 1000.0

    # For each audio chunk, find nearest visual frame
    for audio_ev in chunks:
        audio_t = audio_ev.timestamp.wall_clock
        nearest = _nearest_event(frames, audio_t, window_sec)
        results = _av_op.analyze_pair(audio_ev.to_dict(), nearest.to_dict() if nearest else None)
        findings.extend(results)

    # For each visual anomaly frame, check for nearby audio
    for visual_ev in frames:
        visual_t = visual_ev.timestamp.wall_clock
        flags = visual_ev.data.get("anomaly_metrics", {}).get("anomaly_flags", [])
        if not flags:
            continue
        nearest_audio = _nearest_event(chunks, visual_t, window_sec)
        result = _sv_op.analyze_pair(
            visual_ev.to_dict(),
            nearest_audio.to_dict() if nearest_audio else None,
        )
        if result:
            findings.append(result)

    logger.info("av_security: %d findings from %d frames / %d chunks",
                len(findings), len(frames), len(chunks))
    return findings


def _nearest_event(events, t_sec: float, window_sec: float):
    """Return the event closest to t_sec within window_sec, or None."""
    best = None
    best_diff = window_sec
    for ev in events:
        diff = abs(ev.timestamp.wall_clock - t_sec)
        if diff < best_diff:
            best_diff = diff
            best = ev
    return best
