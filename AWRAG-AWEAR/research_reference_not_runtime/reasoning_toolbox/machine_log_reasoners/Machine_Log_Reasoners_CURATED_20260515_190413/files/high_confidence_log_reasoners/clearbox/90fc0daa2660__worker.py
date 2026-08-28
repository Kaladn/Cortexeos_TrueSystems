"""
AudioWorker — Live mic capture with MFCC fingerprinting and ILD direction.

Extends wolf_engine WorkerBase.
Each collect() cycle captures one chunk, computes fingerprint,
classifies sound type, measures ILD direction, emits EvidenceEvent.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

from wolf_engine.evidence.worker_base import WorkerBase
from wolf_engine.evidence.session_manager import EvidenceSessionManager
from audio_io.config import (
    SAMPLE_RATE, CHANNELS, CHUNK_SAMPLES, DEVICE_INDEX,
    N_MFCC, SOUND_THRESHOLDS, SESSIONS_DIR, NODE_ID, WORKER_INTERVAL_SEC,
)

logger = logging.getLogger(__name__)


# ── MFCC Fingerprinting ───────────────────────────────────────────────────────

def compute_fingerprint(audio_mono: np.ndarray) -> dict[str, Any]:
    """MFCC fingerprint. Returns mfcc (13), centroid, rms, zcr."""
    try:
        import librosa
        mfccs = librosa.feature.mfcc(y=audio_mono.astype(float), sr=SAMPLE_RATE, n_mfcc=N_MFCC)
        mfcc_mean = np.mean(mfccs, axis=1)
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=audio_mono.astype(float), sr=SAMPLE_RATE)))
        rms = float(np.mean(librosa.feature.rms(y=audio_mono.astype(float))))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(audio_mono.astype(float))))
        return {"mfcc": mfcc_mean.tolist(), "centroid": round(centroid, 2),
                "rms": round(rms, 6), "zcr": round(zcr, 6)}
    except ImportError:
        # Fallback without librosa: basic stats only
        rms = float(np.sqrt(np.mean(audio_mono.astype(float) ** 2)))
        return {"mfcc": [], "centroid": 0.0, "rms": round(rms, 6), "zcr": 0.0}


def classify_sound(fp: dict, duration_ms: float) -> str:
    """Heuristic classification. No ML. Returns sound type string."""
    for sound_type, thresholds in SOUND_THRESHOLDS.items():
        d_min, d_max = thresholds["duration_ms"]
        c_min, c_max = thresholds["centroid"]
        r_min, r_max = thresholds["rms"]
        if (d_min <= duration_ms <= d_max
                and c_min <= fp["centroid"] <= c_max
                and r_min <= fp["rms"] <= r_max):
            return sound_type
    return "misc"


# ── ILD Direction ─────────────────────────────────────────────────────────────

def compute_ild_direction(stereo: np.ndarray) -> float:
    """
    Interaural Level Difference → direction in degrees.
    -90 = hard left, 0 = center, +90 = hard right.
    stereo shape: (samples, 2) or (2, samples)
    """
    if stereo.ndim == 2 and stereo.shape[1] == 2:
        left, right = stereo[:, 0].astype(float), stereo[:, 1].astype(float)
    elif stereo.ndim == 2 and stereo.shape[0] == 2:
        left, right = stereo[0].astype(float), stereo[1].astype(float)
    else:
        return 0.0
    l_rms = float(np.sqrt(np.mean(left ** 2))) + 1e-9
    r_rms = float(np.sqrt(np.mean(right ** 2))) + 1e-9
    ild_ratio = (r_rms - l_rms) / (r_rms + l_rms)
    return round(ild_ratio * 90.0, 2)


# ── AudioWorker ───────────────────────────────────────────────────────────────

class AudioWorker(WorkerBase):
    """
    Captures mic audio in chunks, fingerprints, classifies, measures direction.
    Extends wolf_engine WorkerBase — runs in daemon thread, JSONL output.
    """

    worker_name = "audio_io"

    def __init__(self, session_mgr: EvidenceSessionManager,
                 device_index: int | None = DEVICE_INDEX):
        super().__init__(session_mgr=session_mgr, interval_sec=WORKER_INTERVAL_SEC)
        self.device_index = device_index
        self._stream = None
        self._chunk_buffer: np.ndarray | None = None
        self._latest_event: dict | None = None

    def start(self) -> None:
        try:
            import sounddevice as sd
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=CHUNK_SAMPLES,
                device=self.device_index,
                callback=self._audio_callback,
            )
            self._stream.start()
        except ImportError:
            logger.error("sounddevice not installed — pip install sounddevice")
        except Exception as exc:
            logger.error("AudioWorker stream open failed: %s", exc)
        super().start()

    def stop(self) -> int:
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        return super().stop()

    def _audio_callback(self, indata, frames, time_info, status):
        """sounddevice callback — stores latest chunk."""
        self._chunk_buffer = indata.copy()

    def collect(self) -> list[dict[str, Any]]:
        chunk = self._chunk_buffer
        if chunk is None:
            return []
        self._chunk_buffer = None

        # Mono mix for fingerprint, stereo for ILD
        mono = chunk.mean(axis=1) if chunk.ndim == 2 else chunk
        duration_ms = (len(mono) / SAMPLE_RATE) * 1000.0

        # Skip near-silence
        rms_raw = float(np.sqrt(np.mean(mono ** 2)))
        if rms_raw < 0.001:
            return []

        fp = compute_fingerprint(mono)
        sound_type = classify_sound(fp, duration_ms)
        direction_deg = compute_ild_direction(chunk)

        event = {
            "event_type":    "audio_chunk",
            "sound_type":    sound_type,
            "duration_ms":   round(duration_ms, 2),
            "direction_deg": direction_deg,
            "rms":           round(rms_raw, 6),
            "centroid":      fp["centroid"],
            "zcr":           fp["zcr"],
            "mfcc":          fp["mfcc"],
        }
        self._latest_event = event
        return [event]

    @property
    def latest_event(self) -> dict | None:
        return self._latest_event
