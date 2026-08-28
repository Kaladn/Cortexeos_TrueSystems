"""Runtime config for TrueVision SC Edition."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrueVisionRuntimeConfig:
    """Operator-controlled TrueVision logger settings."""

    enabled: bool = True
    source_id: str = "gpu.pre_render"
    session_id: str = "securecore-local"
    grid_size: int = 32
    sample_interval_ms: int = 1000
    max_payload_bytes: int = 4096
    allow_camera: bool = False
    allow_raw_frames: bool = False

    def __post_init__(self) -> None:
        if self.grid_size < 1:
            raise ValueError("grid_size must be positive")
        if self.sample_interval_ms < 100:
            raise ValueError("sample_interval_ms must be at least 100")
        if self.max_payload_bytes < 512:
            raise ValueError("max_payload_bytes must be at least 512")
        if self.allow_raw_frames:
            raise ValueError("TrueVision SC Edition may not allow raw frames")
