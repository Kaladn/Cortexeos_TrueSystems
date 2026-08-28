"""audio_io config."""
from pathlib import Path

# ── Capture ───────────────────────────────────────────────────
SAMPLE_RATE: int = 44100
CHANNELS: int = 2          # stereo required for ILD direction analysis
CHUNK_SAMPLES: int = 4096  # samples per capture chunk (~93ms at 44.1kHz)
DEVICE_INDEX: int | None = None  # None = system default input device

# ── Fingerprint ───────────────────────────────────────────────
N_MFCC: int = 13
SIMILARITY_THRESHOLD: float = 0.95   # cosine sim above this = duplicate

# ── Classification thresholds (heuristic, no ML) ─────────────
SOUND_THRESHOLDS: dict = {
    "footstep":  {"duration_ms": (50, 150),   "centroid": (500, 2000),    "rms": (0.1, 0.6)},
    "gunshot":   {"duration_ms": (10, 60),    "centroid": (2000, 8000),   "rms": (0.4, 1.0)},
    "hitmarker": {"duration_ms": (20, 80),    "centroid": (4000, 12000),  "rms": (0.3, 0.8)},
    "speech":    {"duration_ms": (100, 2000), "centroid": (300, 3000),    "rms": (0.05, 0.5)},
}

# ── ILD direction ─────────────────────────────────────────────
DIRECTION_MISMATCH_THRESHOLD_DEG: float = 60.0

# ── Session storage ───────────────────────────────────────────
_PLUGIN_DIR = Path(__file__).resolve().parent
SESSIONS_DIR: Path = _PLUGIN_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# ── Worker ────────────────────────────────────────────────────
WORKER_INTERVAL_SEC: float = 0.093  # ~1 chunk at 44.1kHz
NODE_ID: str = "audio_io_node"
