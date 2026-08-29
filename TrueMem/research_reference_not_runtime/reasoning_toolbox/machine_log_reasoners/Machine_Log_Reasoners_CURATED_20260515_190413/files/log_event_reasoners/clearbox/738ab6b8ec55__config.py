"""visual_io config — all settings in one place, no hardcoded values anywhere else."""

from pathlib import Path

# ── Capture ───────────────────────────────────────────────────
DEFAULT_FPS: float = 2.0          # frames per second to capture (low = cheap, high = rich)
MAX_FPS: float = 30.0
GRID_SIZE: int = 32               # NxN grid for downsampling (32 = ARC-style symbolic)
PALETTE_LEVELS: int = 10          # quantize to 0-9 discrete levels
CAPTURE_REGION: dict | None = None  # None = full primary monitor; or {"top":0,"left":0,"width":W,"height":H}

# ── Operator thresholds ───────────────────────────────────────
ENTROPY_SPIKE_THRESHOLD: float = 0.75   # global_entropy above this → flag
SYMMETRY_BREAK_THRESHOLD: float = 0.30  # |h_symmetry - v_symmetry| above this → flag
VECTOR_ANOMALY_MIN_DIRS: int = 3        # min directions with high gradient to flag

# ── Session storage ───────────────────────────────────────────
_PLUGIN_DIR = Path(__file__).resolve().parent
SESSIONS_DIR: Path = _PLUGIN_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# ── Worker ────────────────────────────────────────────────────
WORKER_INTERVAL_SEC: float = 1.0 / DEFAULT_FPS
NODE_ID: str = "visual_io_node"
