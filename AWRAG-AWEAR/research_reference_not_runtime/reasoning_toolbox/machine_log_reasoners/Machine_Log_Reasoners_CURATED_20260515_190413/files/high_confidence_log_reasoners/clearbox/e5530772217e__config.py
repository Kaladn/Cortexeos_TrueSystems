"""netlog config."""
from pathlib import Path

# ── Capture interval ──────────────────────────────────────────
POLL_INTERVAL_SEC: float = 1.0     # how often to snapshot connections
MAX_EVENTS_IN_MEMORY: int = 10000  # ring buffer for /latest endpoint

# ── Filters ───────────────────────────────────────────────────
IGNORE_LOCAL_LOOPBACK: bool = True  # skip 127.x.x.x connections
IGNORE_STATUSES: list = ["NONE", "TIME_WAIT"]  # noisy, skip

# ── Packet-level capture (optional, requires scapy + elevated) ─
PACKET_CAPTURE_ENABLED: bool = False  # flip True if scapy available + admin
PACKET_IFACE: str | None = None       # None = scapy chooses default

# ── Operator thresholds ───────────────────────────────────────
NEW_PROCESS_ALERT: bool = True        # flag first-seen process opening connections
HIGH_CONNECTION_COUNT: int = 20       # per-process connection count alert
FOREIGN_PORT_ALERTLIST: list = [4444, 1337, 31337, 6666]  # classic RAT/shell ports

# ── Storage ───────────────────────────────────────────────────
_PLUGIN_DIR = Path(__file__).resolve().parent
SESSIONS_DIR: Path = _PLUGIN_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
NODE_ID: str = "netlog_node"
