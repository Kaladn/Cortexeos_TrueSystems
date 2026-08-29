"""Deterministic speech-state detection and candidate lyric alignment."""

from .lyrics import align_lyrics_to_speech_segments
from .speech import detect_speech_segments_from_replayable_state

__all__ = [
    "align_lyrics_to_speech_segments",
    "detect_speech_segments_from_replayable_state",
]
