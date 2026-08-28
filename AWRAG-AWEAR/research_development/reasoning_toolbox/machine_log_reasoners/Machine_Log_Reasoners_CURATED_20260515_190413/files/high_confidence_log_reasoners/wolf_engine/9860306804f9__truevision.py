"""TrueVision domain schemas — operators, frames, telemetry.

Pure Python dataclasses. No external deps.
Used by operators, loggers, and frame-based reasoning modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ManipulationFlags(Enum):
    """Flags indicating detected manipulation vectors."""
    HITBOX_DRIFT = "hitbox_drift"
    AIM_SNAP = "aim_snap"
    SPAWN_PRESSURE = "spawn_pressure"
    SPAWN_FLOOD = "spawn_flood"
    RECOIL_ANOMALY = "recoil_anomaly"
    TIMING_ANOMALY = "timing_anomaly"


@dataclass
class FrameGrid:
    """ARC-style grid representation of a captured frame."""
    frame_id: int = 0
    t_sec: float = 0.0
    grid: List[List[int]] = field(default_factory=list)
    source: str = ""
    capture_region: str = ""
    h: int = 0
    w: int = 0
    thermal_buffer: Any = None  # Optional numpy array
    depth_buffer: Any = None    # Optional numpy array


@dataclass
class FrameSequence:
    """Contiguous sequence of frames for temporal analysis."""
    frames: List[FrameGrid] = field(default_factory=list)
    t_start: float = 0.0
    t_end: float = 0.0
    src: str = ""


@dataclass
class OperatorResult:
    """Output from a TrueVision operator."""
    operator_name: str = ""
    confidence: float = 0.0
    flags: List[ManipulationFlags] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TelemetryWindow:
    """Unified telemetry window from EOMM compositor."""
    window_start_epoch: float = 0.0
    window_end_epoch: float = 0.0
    session_id: str = ""
    frame_count: int = 0
    composite_score: float = 0.0
    operator_results: List[OperatorResult] = field(default_factory=list)
    flags: List[ManipulationFlags] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
