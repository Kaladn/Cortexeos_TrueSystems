"""Canonical directory layout — the law of the filesystem.

This module defines the COMPLETE directory structure that must exist
under the Clearbox AI data root. It provides:

    1. DIRECTORY_LAW  — the authoritative tree definition
    2. validate()     — boot-time check: create missing, report anomalies
    3. Zone path accessors for the gateway

Design rule: if a directory is not in DIRECTORY_LAW, it should not exist
under the governed root. Unexpected directories are logged (not deleted —
deletion is a human action).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from security.data_paths import (
    CLEARBOX_ROOT,
    CLEARBOX_DATA_ROOT,
    CHAT_THREADS_DIR,
    CHAT_SUMMARIES_DIR,
    CHAT_CITATIONS_DIR,
    CHAT_NOTES_DIR,
    CHAT_MAPS_DIR,
    CHAT_MEMORY_DIR,
    CHAT_ARCHIVE_DIR,
    CONFIG_DIR,
    STATE_DIR,
    SESSIONS_DIR,
    CACHE_DIR,
    AUTH_DIR,
    AUDIT_DIR,
    OBSERVE_DIR,
    DIAGNOSTIC_DIR,
    LAKESPEAK_DIR,
    LAKESPEAK_INDEX_DIR,
    LAKESPEAK_BM25_DIR,
    LAKESPEAK_DENSE_DIR,
    LAKESPEAK_CHUNKS_DIR,
    LAKESPEAK_EVENTS_DIR,
    LAKESPEAK_EVAL_DIR,
    CLEARBOX_NODE_DIR,
    CLEARBOX_NODE_PAIRS_DIR,
    CLEARBOX_NODE_MOBILE_KEYS,
    ROUTING_DIR,
    ROUTING_PROFILES_DIR,
    PACKS_DIR,
    MODULES_DIR,
    CHAT_PACKS_DIR,
    CHAT_PACKS_PACKS_DIR,
    CHAT_PACKS_SESSIONS_DIR,
    IDEAS_DIR,
    TOOLS_DIR,
)


# ── The Law ───────────────────────────────────────────────────
# Every entry is an absolute Path under CLEARBOX_ROOT.
# Validated at boot by validate() — missing dirs are created.

DIRECTORY_LAW: list[Path] = [
    # ── Encrypted zones ───────────────────────────────────────
    CHAT_THREADS_DIR,              # chat JSONL (ENCRYPTED)
    AUTH_DIR,                      # secrets: API keys, WebAuthn, node pairs (ENCRYPTED)
    CLEARBOX_NODE_PAIRS_DIR,         # Ed25519 node key pairs (ENCRYPTED)
    CLEARBOX_NODE_MOBILE_KEYS,       # mobile auth keys (ENCRYPTED)

    # ── Chat / Conversation data (plaintext) ──────────────────
    CHAT_SUMMARIES_DIR,
    CHAT_CITATIONS_DIR,
    CHAT_NOTES_DIR,
    CHAT_MAPS_DIR,
    CHAT_MEMORY_DIR,
    CHAT_ARCHIVE_DIR,

    # ── Config (plaintext) ────────────────────────────────────
    CONFIG_DIR,
    TOOLS_DIR,

    # ── Runtime (plaintext) ───────────────────────────────────
    STATE_DIR,
    SESSIONS_DIR,
    CACHE_DIR,
    ROUTING_DIR,
    ROUTING_PROFILES_DIR,
    CLEARBOX_NODE_DIR,

    # ── LakeSpeak indexes (plaintext) ─────────────────────────
    LAKESPEAK_DIR,
    LAKESPEAK_INDEX_DIR,
    LAKESPEAK_BM25_DIR,
    LAKESPEAK_DENSE_DIR,
    LAKESPEAK_CHUNKS_DIR,
    LAKESPEAK_EVENTS_DIR,
    LAKESPEAK_EVAL_DIR,

    # ── Logs (plaintext) ──────────────────────────────────────
    AUDIT_DIR,
    OBSERVE_DIR,
    DIAGNOSTIC_DIR,

    # ── Misc data (plaintext) ─────────────────────────────────
    PACKS_DIR,
    MODULES_DIR,
    IDEAS_DIR,
    CHAT_PACKS_DIR,
    CHAT_PACKS_PACKS_DIR,
    CHAT_PACKS_SESSIONS_DIR,
]

# Directories that must NEVER be written to by automated processes
PROTECTED_DIRECTORIES: list[Path] = [
    CONFIG_DIR,
    AUTH_DIR,
]

# Directories that only the gateway may write to
GOVERNED_DIRECTORIES: list[Path] = [
    CHAT_THREADS_DIR,
    CHAT_SUMMARIES_DIR,
    CHAT_CITATIONS_DIR,
    CHAT_MAPS_DIR,
    STATE_DIR,
    SESSIONS_DIR,
    LAKESPEAK_INDEX_DIR,
    LAKESPEAK_EVENTS_DIR,
    LAKESPEAK_EVAL_DIR,
    ROUTING_DIR,
    ROUTING_PROFILES_DIR,
    IDEAS_DIR,
]


# ── Validation ────────────────────────────────────────────────


def validate(root: Optional[Path] = None, fix: bool = True) -> dict:
    """Validate the directory structure against DIRECTORY_LAW.

    Args:
        root: Ignored — DIRECTORY_LAW now uses absolute paths from data_paths.
        fix:  If True, create missing directories. If False, report only.

    Returns:
        {
            "valid": bool,
            "root": str,
            "created": [str, ...],      # directories that were created
            "missing": [str, ...],      # directories missing (if fix=False)
            "unexpected": [str, ...],   # directories not in the law
            "timestamp": str,
        }
    """
    root = CLEARBOX_ROOT
    created = []
    missing = []

    # ── Check required directories ────────────────────────────
    for dir_path in DIRECTORY_LAW:
        if not dir_path.exists():
            if fix:
                dir_path.mkdir(parents=True, exist_ok=True)
                created.append(str(dir_path))
            else:
                missing.append(str(dir_path))

    # ── Detect unexpected immediate children of root ───────────
    unexpected = []
    if root.exists():
        legal_tops = {p.relative_to(root).parts[0] for p in DIRECTORY_LAW}
        for child in root.iterdir():
            if child.is_dir() and child.name not in legal_tops:
                unexpected.append(child.name + "/")

    valid = len(missing) == 0 and len(unexpected) == 0

    return {
        "valid": valid,
        "root": str(root),
        "created": created,
        "missing": missing,
        "unexpected": unexpected,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def validate_and_report(root: Optional[Path] = None, fix: bool = True) -> bool:
    """Run validation and print a human-readable report.

    Returns True if the structure is valid (after fixes).
    """
    result = validate(root, fix=fix)
    root_str = result["root"]

    print(f"🏗️  Directory validation: {root_str}")
    print(f"   Timestamp: {result['timestamp']}")

    if result["created"]:
        print(f"   ✅ Created {len(result['created'])} missing directories:")
        for d in result["created"]:
            print(f"      + {d}")

    if result["missing"]:
        print(f"   ❌ Missing {len(result['missing'])} required directories:")
        for d in result["missing"]:
            print(f"      - {d}")

    if result["unexpected"]:
        print(f"   ⚠️  Found {len(result['unexpected'])} unexpected directories:")
        for d in result["unexpected"]:
            print(f"      ? {d}")

    if result["valid"] or (result["created"] and not result["missing"]):
        print("   ✅ Structure valid")
    else:
        print("   ❌ Structure INVALID — manual inspection required")

    return result["valid"] or (len(result["missing"]) == 0)


# ── Boot-Time Hook ────────────────────────────────────────────

def boot_validate() -> bool:
    """Called at application startup. Creates missing directories, warns about anomalies.

    Returns True if structure is valid after bootstrap.
    """
    return validate_and_report(fix=True)
