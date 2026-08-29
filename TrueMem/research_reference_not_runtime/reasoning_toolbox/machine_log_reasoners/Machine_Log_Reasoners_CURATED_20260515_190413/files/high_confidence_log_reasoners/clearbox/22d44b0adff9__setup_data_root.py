#!/usr/bin/env python3
"""One-time setup script: initialize D:\\CLEARBOX\\ data root.

Run this BEFORE starting the app for the first time on a new install or
after moving from the old %LOCALAPPDATA%\\ClearboxAI\\ root.

Steps performed:
  1. Creates all required directories under D:\\CLEARBOX\\
  2. Copies encrypted secrets from old AppData location (if present)
  3. Copies system lexicon from workspace (if not already present)
  4. Prints a summary

Usage:
    python scripts/setup_data_root.py
    python scripts/setup_data_root.py --no-copy   # create dirs only
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from security.data_paths import (
    CLEARBOX_ROOT,
    AUTH_DIR,
    TLS_DIR,
    CLEARBOX_NODE_PAIRS_DIR,
    CLEARBOX_NODE_MOBILE_KEYS,
    CONFIG_DIR,
    STATE_DIR,
    SESSIONS_DIR,
    CACHE_DIR,
    CHAT_THREADS_DIR,
    CHAT_SUMMARIES_DIR,
    CHAT_CITATIONS_DIR,
    CHAT_NOTES_DIR,
    CHAT_MAPS_DIR,
    CHAT_MEMORY_DIR,
    CHAT_ARCHIVE_DIR,
    LAKESPEAK_INDEX_DIR,
    LAKESPEAK_EVENTS_DIR,
    LAKESPEAK_EVAL_DIR,
    LAKESPEAK_CHUNKS_DIR,
    LAKESPEAK_BM25_DIR,
    LAKESPEAK_DENSE_DIR,
    CLEARBOX_NODE_DIR,
    ROUTING_DIR,
    ROUTING_PROFILES_DIR,
    OBSERVE_DIR,
    AUDIT_DIR,
    DIAGNOSTIC_DIR,
    PACKS_DIR,
    MODULES_DIR,
    IDEAS_DIR,
    CHAT_PACKS_DIR,
    CHAT_PACKS_PACKS_DIR,
    CHAT_PACKS_SESSIONS_DIR,
    TOOLS_DIR,
    HELP_DIR,
    HELP_TUTORIALS_DIR,
    SOURCE_ROOT,
)

ALL_DIRS = [
    CHAT_THREADS_DIR,
    CHAT_SUMMARIES_DIR,
    CHAT_CITATIONS_DIR,
    CHAT_NOTES_DIR,
    CHAT_MAPS_DIR,
    CHAT_MEMORY_DIR,
    CHAT_ARCHIVE_DIR,
    CONFIG_DIR,
    TOOLS_DIR,
    STATE_DIR,
    SESSIONS_DIR,
    CACHE_DIR,
    AUTH_DIR,
    TLS_DIR,
    CLEARBOX_NODE_PAIRS_DIR,
    CLEARBOX_NODE_MOBILE_KEYS,
    LAKESPEAK_INDEX_DIR,
    LAKESPEAK_EVENTS_DIR,
    LAKESPEAK_EVAL_DIR,
    LAKESPEAK_CHUNKS_DIR,
    LAKESPEAK_BM25_DIR,
    LAKESPEAK_DENSE_DIR,
    CLEARBOX_NODE_DIR,
    ROUTING_DIR,
    ROUTING_PROFILES_DIR,
    OBSERVE_DIR,
    AUDIT_DIR,
    DIAGNOSTIC_DIR,
    PACKS_DIR,
    MODULES_DIR,
    IDEAS_DIR,
    CHAT_PACKS_DIR,
    CHAT_PACKS_PACKS_DIR,
    CHAT_PACKS_SESSIONS_DIR,
    HELP_DIR,
    HELP_TUTORIALS_DIR,
]


def create_dirs() -> int:
    created = 0
    for d in ALL_DIRS:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"  + {d}")
            created += 1
        else:
            print(f"  . {d}  (exists)")
    return created


def copy_secrets(old_root: Path) -> None:
    """Copy encrypted secrets from old AppData root to new D:\\CLEARBOX\\data\\secrets\\."""
    old_auth = old_root / "auth"
    if not old_auth.exists():
        print(f"  [skip] old auth not found: {old_auth}")
        return

    copied = 0
    for src in old_auth.rglob("*"):
        if src.is_file():
            rel = src.relative_to(old_auth)
            dst = AUTH_DIR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
                print(f"  copied: {src.name} -> {dst}")
                copied += 1
            else:
                print(f"  exists: {dst.name}  (not overwritten)")
    print(f"  Secrets copied: {copied} file(s)")


def copy_system_lexicon() -> None:
    """Confirm system lexicon is accessible from workspace (no copy needed — it's in source)."""
    lex_dir = SOURCE_ROOT / "Lexicon_Canonical"
    if lex_dir.exists():
        count = sum(1 for _ in lex_dir.rglob("*.json"))
        print(f"  System lexicon: {lex_dir} ({count} JSON files) — already in workspace, no copy needed")
    else:
        print(f"  WARNING: system lexicon not found at {lex_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize D:\\CLEARBOX\\ data root")
    parser.add_argument("--no-copy", action="store_true", help="Skip copying secrets from old AppData location")
    args = parser.parse_args()

    # Locate old data root
    local_app_data = os.environ.get("LOCALAPPDATA")
    old_root = Path(local_app_data) / "ClearboxAI" if local_app_data else None

    print(f"\n{'='*60}")
    print(f" Clearbox AI Studio — Data Root Setup")
    print(f" Target: {CLEARBOX_ROOT}")
    print(f"{'='*60}\n")

    print("Creating directories:")
    created = create_dirs()
    print(f"\n  Total created: {created} director(ies)\n")

    if not args.no_copy:
        if old_root and old_root.exists():
            print(f"Migrating secrets from {old_root}:")
            copy_secrets(old_root)
        else:
            print(f"  [info] old data root not found — nothing to migrate")
        print()

    print("System lexicon:")
    copy_system_lexicon()

    print(f"\n{'='*60}")
    print(f" Setup complete. Start the app — it will use D:\\CLEARBOX\\")
    print(f" Old data at {old_root} can be deleted once you confirm the app works.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
