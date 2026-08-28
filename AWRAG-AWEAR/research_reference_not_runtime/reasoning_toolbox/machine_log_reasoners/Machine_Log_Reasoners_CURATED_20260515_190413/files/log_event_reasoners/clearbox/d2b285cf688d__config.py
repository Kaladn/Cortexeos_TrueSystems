"""av_security config."""
from pathlib import Path

# ── Correlation thresholds ────────────────────────────────────
CORRELATION_WINDOW_MS: float = 100.0    # search window for AV pair matching
DELAYED_CORRELATION_THRESHOLD_MS: float = 70.0  # flag if AV delay > this
CONFIDENCE_THRESHOLD: float = 0.75
DIRECTION_MISMATCH_THRESHOLD_DEG: float = 60.0

# ── Anomaly types (Operator #18) ──────────────────────────────
ANOMALY_PHANTOM_AUDIO = "PHANTOM_AUDIO"     # sound with no visual event
ANOMALY_SILENT_VISUAL = "SILENT_VISUAL"     # visual event with no audio
ANOMALY_DELAYED_CORRELATION = "DELAYED_CORRELATION"  # >70ms AV lag
ANOMALY_DIRECTION_MISMATCH = "DIRECTION_MISMATCH"    # audio dir ≠ visual dir

# ── Storage ───────────────────────────────────────────────────
_PLUGIN_DIR = Path(__file__).resolve().parent
SESSIONS_DIR: Path = _PLUGIN_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
NODE_ID: str = "av_security_node"
