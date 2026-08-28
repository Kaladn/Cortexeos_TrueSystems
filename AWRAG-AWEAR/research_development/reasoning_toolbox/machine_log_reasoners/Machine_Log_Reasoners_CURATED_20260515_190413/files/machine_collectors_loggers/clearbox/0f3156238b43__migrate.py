#!/usr/bin/env python3
"""One-time migration: move plaintext data → %LOCALAPPDATA%\\ClearboxAI + DPAPI encrypt.

What it does:
  1. Copies config files (clearbox.config.json, logging.json, storage_paths.json)
  2. Copies chat history (threads, summaries, citation flags)
  3. Copies state (last_state.json)
  4. Encrypts everything with DPAPI
  5. Renames originals to .migrated (backup, not deleted)

Safe to run multiple times — skips files that already exist in the target.

Usage:
  python -m security.migrate
  python security/migrate.py
"""

import shutil
import sys
from pathlib import Path

# Add workspace root to path
WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE))

from security.data_paths import (
    CLEARBOX_DATA_ROOT, CHAT_THREADS_DIR, CHAT_SUMMARIES_DIR,
    CITATION_FLAGS_PATH, CONFIG_DIR, STATE_DIR,
    CLEARBOX_CONFIG_PATH, LOGGING_CONFIG_PATH, STORAGE_PATHS_CONFIG,
    LAST_STATE_PATH, CHAT_HISTORY_DIR,
)
from security.secure_storage import (
    secure_write_text, secure_read_text, is_encrypted,
)


def _migrate_file(src: Path, dst: Path, encrypt: bool = True) -> str:
    """Migrate a single file: copy → encrypt → rename original.

    Returns status string.
    """
    if not src.exists():
        return f"  ⏭️  {src.name} — source not found, skipping"

    if dst.exists() and is_encrypted(dst):
        return f"  ✅ {dst.name} — already migrated and encrypted"

    # Read source (plaintext)
    text = src.read_text(encoding="utf-8")

    # Write to new location (encrypted)
    if encrypt:
        secure_write_text(dst, text)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")

    # Rename original to .migrated (backup)
    backup = src.with_suffix(src.suffix + ".migrated")
    if not backup.exists():
        src.rename(backup)

    tag = "encrypted" if encrypt else "copied"
    return f"  🔒 {src.name} → {dst} ({tag})"


def migrate():
    """Run the full migration."""
    print("=" * 60)
    print("🔒 Clearbox AI Security Migration")
    print(f"   Target: {CLEARBOX_DATA_ROOT}")
    print("=" * 60)

    # ── Config files ───────────────────────────────────────────
    print("\n📁 Config files:")
    configs = [
        (WORKSPACE / "clearbox.config.json", CLEARBOX_CONFIG_PATH, True),
        (WORKSPACE / "config" / "logging.json", LOGGING_CONFIG_PATH, True),
        (WORKSPACE / "config" / "storage_paths.json", STORAGE_PATHS_CONFIG, True),
    ]
    for src, dst, enc in configs:
        print(_migrate_file(src, dst, enc))

    # ── Chat threads ───────────────────────────────────────────
    print("\n💬 Chat threads:")
    src_threads = WORKSPACE / "chat_history" / "threads"
    if src_threads.exists():
        count = 0
        for f in sorted(src_threads.glob("*.jsonl")):
            dst = CHAT_THREADS_DIR / f.name
            print(_migrate_file(f, dst, encrypt=True))
            count += 1
        if count == 0:
            print("  ⏭️  No thread files found")
    else:
        print("  ⏭️  No chat_history/threads/ directory")

    # ── Chat summaries ─────────────────────────────────────────
    print("\n📝 Chat summaries:")
    src_summaries = WORKSPACE / "chat_history" / "summaries"
    if src_summaries.exists():
        count = 0
        for f in sorted(src_summaries.glob("*.txt")):
            dst = CHAT_SUMMARIES_DIR / f.name
            print(_migrate_file(f, dst, encrypt=True))
            count += 1
        if count == 0:
            print("  ⏭️  No summary files found")
    else:
        print("  ⏭️  No chat_history/summaries/ directory")

    # ── Citation flags ─────────────────────────────────────────
    print("\n🚩 Citation flags:")
    src_flags = WORKSPACE / "chat_history" / "citation_flags.jsonl"
    print(_migrate_file(src_flags, CITATION_FLAGS_PATH, encrypt=True))

    # ── Chat memory (forensic mode) ───────────────────────────
    print("\n🔗 Chat memory (forensic):")
    src_memory = WORKSPACE / "chat_history" / "chat_memory"
    if src_memory.exists() and any(src_memory.iterdir()):
        dst_memory = CLEARBOX_DATA_ROOT / "chat_history" / "chat_memory"
        # Deep copy entire directory tree
        for src_file in src_memory.rglob("*.json"):
            rel = src_file.relative_to(src_memory)
            dst_file = dst_memory / rel
            print(_migrate_file(src_file, dst_file, encrypt=True))
    else:
        print("  ⏭️  No chat memory data")

    # ── State ──────────────────────────────────────────────────
    print("\n📊 State:")
    src_state = WORKSPACE / "state" / "last_state.json"
    print(_migrate_file(src_state, LAST_STATE_PATH, encrypt=False))

    # ── Summary ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"✅ Migration complete → {CLEARBOX_DATA_ROOT}")
    print()
    print("Original files renamed to .migrated (safe to delete later).")
    print("The system will now read/write from the secure location.")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
