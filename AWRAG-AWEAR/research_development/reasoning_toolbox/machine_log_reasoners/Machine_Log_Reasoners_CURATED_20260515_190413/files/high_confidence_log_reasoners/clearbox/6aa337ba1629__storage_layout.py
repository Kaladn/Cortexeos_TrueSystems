"""Canonical Storage Layout — the contract for where everything lives.

This module is the SINGLE SOURCE OF TRUTH for all storage paths in Clearbox AI.
Nothing should construct its own paths. Everything asks this module.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │  CLEARBOX_DATA_ROOT (%LOCALAPPDATA%\\ClearboxAI)                │
    │                                                             │
    │  GOVERNED (writes go through gateway)                       │
    │  ├── system/artifacts/        AI writes here only           │
    │  ├── system/staging/          Human review                  │
    │  ├── system/implementation/   Human-activated (live)        │
    │  ├── data/raw/                Immutable input snapshots     │
    │  ├── data/mapped/             Mapping outputs (versioned)   │
    │  ├── sessions/                Session state                 │
    │  ├── lexicon/user/            User-created lexicon entries  │
    │  ├── conversations/threads/   JSONL daily chat logs          │
    │  ├── conversations/summaries/ Daily summaries                │
    │  └── state/                   Runtime state                 │
    │                                                             │
    │  PROTECTED (gateway hard-blocks ALL writes)                 │
    │  ├── lexicon/system/          Base lexicon (read-only)      │
    │  ├── config/                  Configuration                 │
    │  ├── auth/                    WebAuthn credentials          │
    │  └── audit/                   Gateway audit trail           │
    │                                                             │
    │  SOURCE_ROOT (workspace — code, models, samples)            │
    │  ├── models/                  GGUF model files              │
    │  ├── bridges/                 Bridge engine + server        │
    │  ├── Lexicon_Canonical/       LEGACY lexicon location       │
    │  └── ...                      (source code, not user data)  │
    └─────────────────────────────────────────────────────────────┘

Lexicon layout (per temp-3 design — address-space codex):
    lexicon/system/
    ├── manifest.json       ← name, version, entry_count, checksum
    ├── A.json              ← all entries starting with 'A'
    ├── B.json
    ├── ...
    ├── Z.json
    ├── _numeric.json       ← entries starting with digits
    └── _other.json         ← entries starting with symbols/unicode

    lexicon/user/
    ├── manifest.json
    ├── A.json
    └── ...

Map output layout:
    data/raw/{run_id}/
    ├── manifest.json       ← source, timestamp, lexicon_version, token_count
    └── input.txt           ← original input (immutable snapshot)

    data/mapped/{run_id}/
    ├── manifest.json       ← links to raw, maps to lexicon version, hashes
    └── 616_map.json        ← the mapping output
"""

from __future__ import annotations

import hashlib
import json
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from security.data_paths import (
    CLEARBOX_ROOT, CLEARBOX_DATA_ROOT, SOURCE_ROOT,
    CHAT_THREADS_DIR, CHAT_SUMMARIES_DIR,
    CHAT_MAPS_DIR,
    CONFIG_DIR, AUTH_DIR, AUDIT_DIR,
    STATE_DIR, SESSIONS_DIR,
)


# ═══════════════════════════════════════════════════════════════
# PATH CONSTANTS — all resolve through data_paths.CLEARBOX_ROOT
# ═══════════════════════════════════════════════════════════════

# ── Governed zones ────────────────────────────────────────────
ARTIFACTS_DIR      = CLEARBOX_ROOT / "data" / "artifacts"
STAGING_DIR        = CLEARBOX_ROOT / "data" / "staging"
IMPLEMENTATION_DIR = CLEARBOX_ROOT / "data" / "implementation"

DATA_RAW_DIR    = CLEARBOX_ROOT / "data" / "raw"
DATA_MAPPED_DIR = CHAT_MAPS_DIR             # 6-1-6 map files → D:\CLEARBOX\data\maps

# ── Lexicon dirs ──────────────────────────────────────────────
LEXICON_SYSTEM_DIR = SOURCE_ROOT / "Lexicon_Canonical"   # read-only in workspace
LEXICON_USER_DIR   = CLEARBOX_ROOT / "config" / "lexicon" / "user"

# ── Legacy (workspace origin) — no longer needs migration ─────
LEGACY_LEXICON_DIR = SOURCE_ROOT / "Lexicon_Canonical"
LEGACY_MAPS_DIR    = CHAT_MAPS_DIR          # maps are now in D:\CLEARBOX\data\maps


# ═══════════════════════════════════════════════════════════════
# LEXICON LAYOUT — address-space codex, one file per letter
# ═══════════════════════════════════════════════════════════════

# The 28 lexicon partition files (A-Z + _numeric + _other)
LEXICON_PARTITIONS: list[str] = [
    f"{c}.json" for c in string.ascii_uppercase
] + ["_numeric.json", "_other.json"]


def lexicon_partition_key(word: str) -> str:
    """Determine which partition file a word belongs to.

    Rules:
        "apple"  → "A.json"
        "Zebra"  → "Z.json"
        "3d"     → "_numeric.json"
        "—dash"  → "_other.json"
        ""       → "_other.json"
    """
    if not word:
        return "_other.json"
    first = word[0].upper()
    if first in string.ascii_uppercase:
        return f"{first}.json"
    elif first.isdigit():
        return "_numeric.json"
    else:
        return "_other.json"


def lexicon_system_path(partition: str) -> Path:
    """Absolute path to a system lexicon partition file."""
    return LEXICON_SYSTEM_DIR / partition


def lexicon_user_path(partition: str) -> Path:
    """Absolute path to a user lexicon partition file."""
    return LEXICON_USER_DIR / partition


def lexicon_manifest_path(layer: str = "system") -> Path:
    """Path to the lexicon manifest for a layer."""
    if layer == "system":
        return LEXICON_SYSTEM_DIR / "manifest.json"
    return LEXICON_USER_DIR / "manifest.json"


# ═══════════════════════════════════════════════════════════════
# MAP OUTPUT LAYOUT — raw input + mapped output, versioned
# ═══════════════════════════════════════════════════════════════

def generate_run_id() -> str:
    """Generate a deterministic run ID from current UTC time."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def raw_run_dir(run_id: str) -> Path:
    """Directory for a raw input snapshot."""
    return DATA_RAW_DIR / run_id


def mapped_run_dir(run_id: str) -> Path:
    """Directory for a mapping output."""
    return DATA_MAPPED_DIR / run_id


def build_raw_manifest(
    run_id: str,
    source: str,
    token_count: int,
    input_hash: str,
    lexicon_version: str = "unknown",
) -> dict:
    """Build the manifest for a raw input snapshot."""
    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "token_count": token_count,
        "input_hash": input_hash,
        "lexicon_version": lexicon_version,
        "layer": "raw",
    }


def build_mapped_manifest(
    run_id: str,
    raw_run_id: str,
    source: str,
    lexicon_version: str,
    entry_count: int,
    mapped_count: int,
    unmapped_count: int,
    output_hash: str,
) -> dict:
    """Build the manifest for a mapping output."""
    return {
        "run_id": run_id,
        "raw_run_id": raw_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "lexicon_version": lexicon_version,
        "entry_count": entry_count,
        "mapped_count": mapped_count,
        "unmapped_count": unmapped_count,
        "output_hash": output_hash,
        "layer": "mapped",
    }


# ═══════════════════════════════════════════════════════════════
# LEXICON MANIFEST — tracks what's loaded, version, integrity
# ═══════════════════════════════════════════════════════════════

def build_lexicon_manifest(
    name: str,
    layer: str,
    version: str,
    entry_count: int,
    partitions: dict[str, int],
    description: str = "",
    source: str = "",
) -> dict:
    """Build a lexicon manifest.

    Args:
        name:        Human-readable name (e.g. "wordnet_147k")
        layer:       "system" or "user"
        version:     Semantic version string
        entry_count: Total entries across all partitions
        partitions:  Dict of partition_file → entry_count
        description: Optional description
        source:      Origin of the data
    """
    return {
        "name": name,
        "layer": layer,
        "version": version,
        "entry_count": entry_count,
        "partitions": partitions,
        "description": description,
        "source": source,
        "created": datetime.now(timezone.utc).isoformat(),
        "format": "address-space-codex",
        "schema_version": "1.0",
    }


# ═══════════════════════════════════════════════════════════════
# CONTENT HASHING — for manifests and audit
# ═══════════════════════════════════════════════════════════════

def content_hash(content: str) -> str:
    """SHA-256 hash of string content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    """SHA-256 hash of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ═══════════════════════════════════════════════════════════════
# STORAGE CONTRACT — the summary for humans and other modules
# ═══════════════════════════════════════════════════════════════

STORAGE_CONTRACT = {
    "version":    "1.0",
    "date":       "2026-02-09",
    "data_root":  str(CLEARBOX_DATA_ROOT),
    "source_root": str(SOURCE_ROOT),

    "governed_zones": {
        "artifacts":      str(ARTIFACTS_DIR),
        "staging":        str(STAGING_DIR),
        "implementation": str(IMPLEMENTATION_DIR),
        "data_raw":       str(DATA_RAW_DIR),
        "data_mapped":    str(DATA_MAPPED_DIR),
        "sessions":       str(SESSIONS_DIR),
        "lexicon_user":   str(LEXICON_USER_DIR),
        "chat_threads":   str(CHAT_THREADS_DIR),
        "chat_summaries": str(CHAT_SUMMARIES_DIR),
        "state":          str(STATE_DIR),
        "lakespeak_index":  str(CLEARBOX_DATA_ROOT / "lakespeak" / "index"),
        "lakespeak_events": str(CLEARBOX_DATA_ROOT / "lakespeak" / "events"),
        "lakespeak_eval":   str(CLEARBOX_DATA_ROOT / "lakespeak" / "eval"),
    },

    "protected_zones": {
        "lexicon_system": str(LEXICON_SYSTEM_DIR),
        "config":         str(CONFIG_DIR),
        "auth":           str(AUTH_DIR),
        "audit":          str(AUDIT_DIR),
    },

    "lexicon": {
        "format":         "address-space-codex",
        "partitions":     28,
        "partition_scheme": "A-Z + _numeric + _other",
        "system_dir":     str(LEXICON_SYSTEM_DIR),
        "user_dir":       str(LEXICON_USER_DIR),
        "manifest_file":  "manifest.json",
    },

    "maps": {
        "raw_dir":        str(DATA_RAW_DIR),
        "mapped_dir":     str(DATA_MAPPED_DIR),
        "run_id_format":  "YYYYMMDD-HHMMSS",
        "raw_contents":   ["manifest.json", "input.txt"],
        "mapped_contents": ["manifest.json", "616_map.json"],
    },

    "rules": [
        "AI writes to artifacts/ only",
        "Human promotes: artifacts → staging → implementation",
        "No automated promotion — ever",
        "System lexicon is read-only — protected zone",
        "User lexicon writes go through gateway (WriteZone.LEXICON_USER)",
        "Map outputs: raw (immutable) + mapped (versioned), never silent overwrite",
        "Every mutation logged to audit trail",
        "Word variants are separate entries — no inference, no magic",
        "Tokens without symbols stay raw — allowed, promoted later",
    ],
}


def print_contract() -> None:
    """Print the storage contract for human inspection."""
    print(json.dumps(STORAGE_CONTRACT, indent=2))


if __name__ == "__main__":
    print_contract()
