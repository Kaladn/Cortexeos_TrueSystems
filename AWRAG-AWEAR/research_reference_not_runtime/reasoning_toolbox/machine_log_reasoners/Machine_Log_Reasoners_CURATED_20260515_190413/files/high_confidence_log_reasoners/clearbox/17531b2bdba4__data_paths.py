"""Centralized data path resolution for Clearbox AI Studio.

Data root resolution order:
  1) CLEARBOX_DATA_ROOT env var
  2) %LOCALAPPDATA%\\ClearboxAI\\storage_paths.json ("data_root")
  3) Fallback: D:\\CLEARBOX

Encryption policy:
  data/chats/   -> ENCRYPTED  (chat JSONL via secure_append_line / secure_read_lines)
  data/secrets/ -> ENCRYPTED  (API keys, WebAuthn, Ed25519 node pairs, profiles)
  Everything else -> plaintext JSON / JSONL

Code and models stay in the workspace root (shareable, not personal).
"""

import json
import os
from pathlib import Path


def _bootstrap_storage_file() -> Path:
    """Path used before CLEARBOX_ROOT is known."""
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "ClearboxAI" / "storage_paths.json"
    return Path.home() / ".clearbox_ai" / "storage_paths.json"


def _read_bootstrap_data_root() -> Path | None:
    """Read persisted data root selected at install time."""
    cfg = _bootstrap_storage_file()
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    root = data.get("data_root")
    if not root or not isinstance(root, str):
        return None
    return Path(root).expanduser()


def _is_usable_root(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


def _resolve_data_root() -> Path:
    env_root = os.environ.get("CLEARBOX_DATA_ROOT")
    if env_root:
        candidate = Path(env_root.strip().strip('"')).expanduser()
        if _is_usable_root(candidate):
            return candidate
    saved = _read_bootstrap_data_root()
    if saved is not None and _is_usable_root(saved):
        return saved
    for candidate in (Path("D:/CLEARBOX"), Path.home() / "ClearboxAI"):
        if _is_usable_root(candidate):
            return candidate
    return Path("D:/CLEARBOX")


# ── Single root constant ─────────────────────────────────────────
CLEARBOX_ROOT    = _resolve_data_root()
CLEARBOX_DATA_ROOT = CLEARBOX_ROOT          # backward-compat alias

# ── Chat threads (ENCRYPTED) ────────────────────────────────────
CHAT_THREADS_DIR           = CLEARBOX_ROOT / "data" / "chats"
CHAT_SUMMARIES_DIR         = CLEARBOX_ROOT / "data" / "summaries"
CHAT_SUMMARIES_WEEK_DIR    = CHAT_SUMMARIES_DIR / "week"
CHAT_SUMMARIES_MONTH_DIR   = CHAT_SUMMARIES_DIR / "month"
CHAT_SUMMARIES_YEAR_DIR    = CHAT_SUMMARIES_DIR / "year"
CHAT_CITATIONS_DIR         = CLEARBOX_ROOT / "data" / "citations"
CHAT_NOTES_DIR             = CLEARBOX_ROOT / "data" / "notes"
CHAT_MAPS_DIR              = CLEARBOX_ROOT / "data" / "maps"
CHAT_MEMORY_DIR            = CLEARBOX_ROOT / "data" / "memory"
CHAT_ARCHIVE_DIR           = CLEARBOX_ROOT / "data" / "archive"
CITATION_FLAGS_PATH        = CLEARBOX_ROOT / "data" / "citation_flags.jsonl"
CITATION_DB_PATH           = CLEARBOX_ROOT / "data" / "citations.db"

# Legacy aliases (no outside file imports CONVERSATIONS_DIR or CHAT_HISTORY_DIR
# directly, but keep to avoid any hidden usages)
CONVERSATIONS_DIR = CHAT_THREADS_DIR
CHAT_HISTORY_DIR  = CHAT_THREADS_DIR

# ── Config ──────────────────────────────────────────────────────
CONFIG_DIR           = CLEARBOX_ROOT / "config"
CLEARBOX_CONFIG_PATH   = CONFIG_DIR / "clearbox.config.json"
LOGGING_CONFIG_PATH  = CONFIG_DIR / "logging.json"
STORAGE_PATHS_CONFIG = CONFIG_DIR / "storage_paths.json"
TOOLS_DIR            = CONFIG_DIR / "tools"

# ── State + Sessions ─────────────────────────────────────────────
STATE_DIR        = CLEARBOX_ROOT / "runtime" / "temp"
LAST_STATE_PATH  = STATE_DIR / "last_state.json"
SESSIONS_DIR     = CLEARBOX_ROOT / "runtime" / "cache"
CACHE_DIR        = CLEARBOX_ROOT / "runtime" / "cache"

# ── Secrets (ENCRYPTED — API keys, WebAuthn, profiles, node pairs) ─
AUTH_DIR               = CLEARBOX_ROOT / "data" / "secrets"
TLS_DIR                = AUTH_DIR / "tls"
CLEARBOX_NODE_PAIRS_DIR  = AUTH_DIR / "node_pairs"
CLEARBOX_NODE_MOBILE_KEYS = AUTH_DIR / "mobile_keys"

# ── LakeSpeak ───────────────────────────────────────────────────
LAKESPEAK_DIR        = CLEARBOX_ROOT / "data" / "indexes" / "lakespeak"
LAKESPEAK_INDEX_DIR  = LAKESPEAK_DIR / "index"
LAKESPEAK_EVENTS_DIR = LAKESPEAK_DIR / "events"
LAKESPEAK_EVAL_DIR   = LAKESPEAK_DIR / "eval"
LAKESPEAK_CHUNKS_DIR = LAKESPEAK_INDEX_DIR / "chunks"
LAKESPEAK_GENERAL_DIR = LAKESPEAK_CHUNKS_DIR / "general"
LAKESPEAK_CHATS_DIR   = LAKESPEAK_CHUNKS_DIR / "chats"
LAKESPEAK_GUTENBERG_DIR = LAKESPEAK_CHUNKS_DIR / "gutenberg"
LAKESPEAK_BM25_DIR   = LAKESPEAK_INDEX_DIR / "bm25"
LAKESPEAK_DENSE_DIR  = LAKESPEAK_INDEX_DIR / "dense"

# ── Clearbox Node runtime (non-secret) ────────────────────────────
CLEARBOX_NODE_DIR      = CLEARBOX_ROOT / "runtime" / "jobs"
CLEARBOX_NODE_JOBS_DIR = CLEARBOX_ROOT / "runtime" / "jobs"

# ── Routing ─────────────────────────────────────────────────────
ROUTING_DIR          = CLEARBOX_ROOT / "runtime" / "routing"
ROUTING_PROFILES_DIR = ROUTING_DIR / "profiles"

# ── Observe + Audit (plaintext logs) ────────────────────────────
OBSERVE_DIR    = CLEARBOX_ROOT / "data" / "logs" / "observe"
AUDIT_DIR      = CLEARBOX_ROOT / "data" / "logs" / "audit"
DIAGNOSTIC_DIR = CLEARBOX_ROOT / "data" / "logs" / "diagnostic"

# ── Misc data ───────────────────────────────────────────────────
PACKS_DIR               = CLEARBOX_ROOT / "data" / "packs"
MODULES_DIR             = CLEARBOX_ROOT / "data" / "modules"
CHAT_PACKS_DIR          = CLEARBOX_ROOT / "data" / "chat_packs"
CHAT_PACKS_PACKS_DIR    = CHAT_PACKS_DIR / "packs"
CHAT_PACKS_SESSIONS_DIR = CHAT_PACKS_DIR / "sessions"
IDEAS_DIR               = CLEARBOX_ROOT / "data" / "ideas"

# ── Help ────────────────────────────────────────────────────────
HELP_DIR           = CLEARBOX_ROOT / "config" / "help"
HELP_TUTORIALS_DIR = HELP_DIR / "tutorials"

# ── Source root (workspace — code, models, lexicon) ─────────────
SOURCE_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR  = SOURCE_ROOT / "models"

# ── Ensure all data directories exist on first import ──────────
for _d in [
    CHAT_THREADS_DIR, CHAT_SUMMARIES_DIR,
    CHAT_SUMMARIES_WEEK_DIR, CHAT_SUMMARIES_MONTH_DIR, CHAT_SUMMARIES_YEAR_DIR,
    CHAT_CITATIONS_DIR, CHAT_NOTES_DIR, CHAT_MAPS_DIR,
    CHAT_MEMORY_DIR, CHAT_ARCHIVE_DIR,
    CONFIG_DIR, TOOLS_DIR,
    STATE_DIR, SESSIONS_DIR, CACHE_DIR,
    AUTH_DIR, TLS_DIR, CLEARBOX_NODE_PAIRS_DIR, CLEARBOX_NODE_MOBILE_KEYS,
    PACKS_DIR, MODULES_DIR, IDEAS_DIR,
    LAKESPEAK_INDEX_DIR, LAKESPEAK_EVENTS_DIR, LAKESPEAK_EVAL_DIR,
    LAKESPEAK_CHUNKS_DIR, LAKESPEAK_GENERAL_DIR, LAKESPEAK_CHATS_DIR,
    LAKESPEAK_GUTENBERG_DIR, LAKESPEAK_BM25_DIR, LAKESPEAK_DENSE_DIR,
    CLEARBOX_NODE_DIR, CLEARBOX_NODE_JOBS_DIR,
    ROUTING_DIR, ROUTING_PROFILES_DIR,
    OBSERVE_DIR, AUDIT_DIR, DIAGNOSTIC_DIR,
    HELP_DIR, HELP_TUTORIALS_DIR,
    CHAT_PACKS_DIR, CHAT_PACKS_PACKS_DIR, CHAT_PACKS_SESSIONS_DIR,
]:
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Some environments expose the configured data root read-only.
        # Runtime writers create the exact corpus/receipt dirs on demand.
        pass

print(f"Data root: {CLEARBOX_ROOT}")
