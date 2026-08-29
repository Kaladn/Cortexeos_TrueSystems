from __future__ import annotations

import shutil
import subprocess
from typing import Any

import numpy as np


DEFAULT_SAMPLE_RATE = 48_000
DEFAULT_CHANNELS = 2


def capture_linux_pipewire_loopback(
    *,
    duration_seconds: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Capture the default Linux output monitor through PipeWire/Pulse.

    ``parec`` reads ``@DEFAULT_MONITOR@``, the monitor attached to the current
    default output sink. The function reads an exact requested number of
    float32 frames and returns no raw-audio artifact.
    """
    if duration_seconds <= 0 or duration_seconds > 3600:
        raise ValueError("duration_seconds must be greater than 0 and no more than 3600")
    if sample_rate < 8_000 or sample_rate > 384_000:
        raise ValueError("sample_rate must be between 8000 and 384000")
    if channels not in {1, 2}:
        raise ValueError("channels must be 1 or 2")

    parec = shutil.which("parec")
    if not parec:
        raise RuntimeError("Linux PipeWire/Pulse monitor capture requires parec")

    requested_frames = max(1, int(round(float(duration_seconds) * sample_rate)))
    requested_bytes = requested_frames * channels * np.dtype("<f4").itemsize
    command = [
        parec,
        "--record",
        "--device=@DEFAULT_MONITOR@",
        "--raw",
        "--format=float32le",
        f"--rate={sample_rate}",
        f"--channels={channels}",
        "--client-name=TrueAudio",
        "--stream-name=TrueAudio machine output state",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw = b""
    stderr = b""
    try:
        if process.stdout is None:
            raise RuntimeError("parec did not expose captured audio")
        raw = process.stdout.read(requested_bytes)
    finally:
        process.terminate()
        try:
            _, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            _, stderr = process.communicate()

    if len(raw) != requested_bytes:
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"PipeWire monitor returned {len(raw)} of {requested_bytes} requested bytes"
            + (f": {detail}" if detail else "")
        )

    samples = np.frombuffer(raw, dtype="<f4").astype(np.float32).reshape((-1, channels))
    if channels == 1:
        samples = np.repeat(samples, 2, axis=1)
    samples = np.clip(samples, -1.0, 1.0)
    return samples, {
        "backend": "linux_pipewire_pulse_monitor",
        "capture_tool": parec,
        "device": "@DEFAULT_MONITOR@",
        "sample_rate": sample_rate,
        "channels": 2,
        "requested_frames": requested_frames,
        "captured_frames": int(samples.shape[0]),
        "duration_seconds": round(samples.shape[0] / float(sample_rate), 6),
        "device_role": "default_output_monitor",
        "capture_stage": "pre_speaker_loopback",
        "raw_audio_saved": False,
    }
