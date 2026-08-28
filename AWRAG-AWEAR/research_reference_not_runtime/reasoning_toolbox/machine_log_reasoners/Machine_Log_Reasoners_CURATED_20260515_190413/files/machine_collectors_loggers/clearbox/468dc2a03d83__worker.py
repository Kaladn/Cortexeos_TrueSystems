"""
VisualWorker — Screen capture worker for the visual_io plugin.

Extends wolf_engine WorkerBase directly.
No YOLO. No OpenCV. numpy + mss + ctypes only.

Each collect() cycle:
  1. Capture screen frame via mss
  2. Downsample to GRID_SIZE x GRID_SIZE via 2D average pooling
  3. Quantize to 0-9 palette (ARC-style)
  4. Compute ScreenVectorState (entropy, symmetry, sectors, rays)
  5. Run registered operators against the state
  6. Return EvidenceEvent dicts for WorkerBase to write as JSONL
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

from wolf_engine.evidence.worker_base import WorkerBase
from wolf_engine.evidence.session_manager import EvidenceSessionManager
from visual_io.config import (
    GRID_SIZE, PALETTE_LEVELS, CAPTURE_REGION, DEFAULT_FPS, NODE_ID,
    ENTROPY_SPIKE_THRESHOLD, SYMMETRY_BREAK_THRESHOLD, VECTOR_ANOMALY_MIN_DIRS,
)

logger = logging.getLogger(__name__)


# ── ScreenVectorState ─────────────────────────────────────────────────────────

def _pool2d(arr: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    """2D average pool arr (H, W) → (out_h, out_w). No external deps."""
    h, w = arr.shape
    ph, pw = h // out_h, w // out_w
    return arr[: ph * out_h, : pw * out_w].reshape(out_h, ph, out_w, pw).mean(axis=(1, 3))


def _quantize(arr: np.ndarray, levels: int = PALETTE_LEVELS) -> np.ndarray:
    """Map 0-255 grayscale → 0-(levels-1) discrete palette."""
    return np.clip((arr / 255.0 * levels).astype(int), 0, levels - 1)


def _sector_stats(grid: np.ndarray) -> dict[str, Any]:
    """Compute UP/DOWN/LEFT/RIGHT sector means from grid."""
    h, w = grid.shape
    mh, mw = h // 2, w // 2
    return {
        "UP":    float(grid[:mh, :].mean()),
        "DOWN":  float(grid[mh:, :].mean()),
        "LEFT":  float(grid[:, :mw].mean()),
        "RIGHT": float(grid[:, mw:].mean()),
    }


def _entropy(arr: np.ndarray, levels: int = PALETTE_LEVELS) -> float:
    """Shannon entropy normalised to [0, 1]."""
    counts = np.bincount(arr.flatten(), minlength=levels).astype(float)
    counts += 1e-9
    probs = counts / counts.sum()
    raw = -float(np.sum(probs * np.log2(probs)))
    max_entropy = np.log2(levels)
    return raw / max_entropy if max_entropy > 0 else 0.0


def _symmetry(grid: np.ndarray) -> tuple[float, float]:
    """Horizontal and vertical symmetry [0=none, 1=perfect]."""
    h_sym = 1.0 - float(np.abs(grid - np.fliplr(grid)).mean()) / (PALETTE_LEVELS - 1)
    v_sym = 1.0 - float(np.abs(grid - np.flipud(grid)).mean()) / (PALETTE_LEVELS - 1)
    return h_sym, v_sym


def _ray_vectors(grid: np.ndarray) -> dict[str, dict[str, float]]:
    """
    8-direction ray vectors from center outward.
    Each direction: gradient_change (mean abs diff along ray), entropy.
    Directions: N, NE, E, SE, S, SW, W, NW
    """
    h, w = grid.shape
    cy, cx = h // 2, w // 2
    directions = {
        "N":  [(cy - i, cx) for i in range(1, cy)],
        "NE": [(cy - i, cx + i) for i in range(1, min(cy, w - cx))],
        "E":  [(cy, cx + i) for i in range(1, w - cx)],
        "SE": [(cy + i, cx + i) for i in range(1, min(h - cy, w - cx))],
        "S":  [(cy + i, cx) for i in range(1, h - cy)],
        "SW": [(cy + i, cx - i) for i in range(1, min(h - cy, cx))],
        "W":  [(cy, cx - i) for i in range(1, cx)],
        "NW": [(cy - i, cx - i) for i in range(1, min(cy, cx))],
    }
    result = {}
    for name, coords in directions.items():
        if len(coords) < 2:
            result[name] = {"gradient_change": 0.0, "entropy": 0.0}
            continue
        vals = np.array([grid[r, c] for r, c in coords if 0 <= r < h and 0 <= c < w], dtype=float)
        grad = float(np.abs(np.diff(vals)).mean()) if len(vals) > 1 else 0.0
        ent = _entropy(vals.astype(int).clip(0, PALETTE_LEVELS - 1), PALETTE_LEVELS)
        result[name] = {"gradient_change": round(grad, 4), "entropy": round(ent, 4)}
    return result


def _core_block(grid: np.ndarray) -> dict[str, float]:
    """2x2 central crosshair block stats."""
    h, w = grid.shape
    cy, cx = h // 2, w // 2
    block = grid[cy - 1:cy + 1, cx - 1:cx + 1]
    return {
        "mean": float(block.mean()),
        "max":  float(block.max()),
        "min":  float(block.min()),
        "std":  float(block.std()),
    }


def build_screen_vector_state(grid: np.ndarray, frame_id: int, t_sec: float) -> dict[str, Any]:
    """Build the full ScreenVectorState dict from a quantized grid."""
    h_sym, v_sym = _symmetry(grid)
    g_ent = _entropy(grid)

    anomaly_flags: list[str] = []
    if g_ent > ENTROPY_SPIKE_THRESHOLD:
        anomaly_flags.append("HIGH_ENTROPY")
    if abs(h_sym - v_sym) > SYMMETRY_BREAK_THRESHOLD:
        anomaly_flags.append("SYMMETRY_BREAK")

    rays = _ray_vectors(grid)
    high_grad_dirs = sum(1 for r in rays.values() if r["gradient_change"] > 0.5)
    if high_grad_dirs >= VECTOR_ANOMALY_MIN_DIRS:
        anomaly_flags.append("VECTOR_ANOMALY")

    return {
        "frame_id":  frame_id,
        "t_sec":     round(t_sec, 4),
        "grid_size": grid.shape[0],
        "core_block": _core_block(grid),
        "sectors":   _sector_stats(grid),
        "rays":      rays,
        "anomaly_metrics": {
            "global_entropy":  round(g_ent, 4),
            "h_symmetry":      round(h_sym, 4),
            "v_symmetry":      round(v_sym, 4),
            "anomaly_flags":   anomaly_flags,
        },
    }


# ── VisualWorker ──────────────────────────────────────────────────────────────

class VisualWorker(WorkerBase):
    """
    Captures screen frames and emits ScreenVectorState events.
    Extends wolf_engine WorkerBase — runs in daemon thread, JSONL output.
    """

    worker_name = "visual_io"

    def __init__(
        self,
        session_mgr: EvidenceSessionManager,
        fps: float = DEFAULT_FPS,
        grid_size: int = GRID_SIZE,
        capture_region: dict | None = CAPTURE_REGION,
    ):
        interval = 1.0 / max(fps, 0.1)
        super().__init__(session_mgr=session_mgr, interval_sec=interval)
        self.fps = fps
        self.grid_size = grid_size
        self.capture_region = capture_region
        self._frame_id = 0
        self._start_time = 0.0
        self._latest_state: dict | None = None

    def collect(self) -> list[dict[str, Any]]:
        try:
            import mss
            import mss.tools
        except ImportError:
            logger.error("mss not installed — pip install mss")
            return []

        try:
            with mss.mss() as sct:
                region = self.capture_region or sct.monitors[1]  # primary monitor
                shot = sct.grab(region)
                # Convert to grayscale numpy array
                raw = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
                gray = (0.299 * raw[:, :, 2] + 0.587 * raw[:, :, 1] + 0.114 * raw[:, :, 0])
        except Exception as exc:
            logger.error("visual_io capture failed: %s", exc)
            return []

        # Downsample → quantize
        pooled = _pool2d(gray, self.grid_size, self.grid_size)
        grid = _quantize(pooled)

        t_sec = time.time() - self._start_time if self._start_time else 0.0
        state = build_screen_vector_state(grid, self._frame_id, t_sec)
        self._latest_state = state
        self._frame_id += 1

        return [{"event_type": "screen_vector_state", **state}]

    def start(self) -> None:
        self._start_time = time.time()
        self._frame_id = 0
        super().start()

    @property
    def latest_state(self) -> dict | None:
        return self._latest_state
