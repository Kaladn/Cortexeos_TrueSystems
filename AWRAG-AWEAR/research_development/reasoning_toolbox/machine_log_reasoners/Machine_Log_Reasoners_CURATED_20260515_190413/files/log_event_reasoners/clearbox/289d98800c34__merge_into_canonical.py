"""Merge a domain pack INTO Lexicon_Canonical (append entries).

Usage:
    python tools\merge_into_canonical.py Lexicon_WordFreq

This appends all entries from the domain pack into the matching
canonical_<L>.json files in Lexicon_Canonical, then optionally removes
the source directory.

Only use this for GENERAL LANGUAGE packs that belong in the base.
Do NOT use for domain-specific packs (medical, legal, etc.).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BASE_DIR = REPO / "Lexical Data"
LEXICON_DIR = BASE_DIR / "Canonical"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def stream_write(path: Path, slots: list):
    """Write slots as compact JSON via temp file."""
    tmp = path.with_suffix('.tmp')
    with open(tmp, "w", encoding="utf-8") as f:
        f.write('[\n')
        last = len(slots) - 1
        for i, slot in enumerate(slots):
            f.write(json.dumps(slot, ensure_ascii=False))
            if i < last:
                f.write(',\n')
            else:
                f.write('\n')
        f.write(']\n')
    os.replace(tmp, path)


def main():
    import sys
    args = [arg for arg in sys.argv[1:] if arg != "--legacy-paths"]
    allow_legacy = "--legacy-paths" in sys.argv[1:]
    if not allow_legacy:
        print("Refusing to run hardcoded legacy paths.")
        print("Re-run with: python tools/lexicon/merge_into_canonical.py --legacy-paths <source_dir_name>")
        sys.exit(1)

    if len(args) < 1:
        print("Usage: python merge_into_canonical.py <source_dir_name>")
        print("       python merge_into_canonical.py --legacy-paths <source_dir_name>")
        print("  e.g.: python merge_into_canonical.py Lexicon_WordFreq")
        sys.exit(1)

    source_name = args[0]
    source_dir = BASE_DIR / source_name
    if not source_dir.is_dir():
        print(f"Not found: {source_dir}")
        sys.exit(1)

    print(f"Source:      {source_dir}")
    print(f"Destination: {LEXICON_DIR}")
    print(f"{'='*70}")

    start = time.time()
    total_merged = 0

    for letter in LETTERS:
        # Find source file — try common prefixes
        src_file = None
        for pattern in source_dir.glob(f"*_{letter}.json"):
            src_file = pattern
            break

        if src_file is None or not src_file.exists():
            continue

        dst_file = LEXICON_DIR / f"canonical_{letter}.json"

        t0 = time.time()

        # Load source entries
        with open(src_file, "r", encoding="utf-8") as f:
            new_entries = json.load(f)

        if not new_entries:
            continue

        # Load destination
        with open(dst_file, "r", encoding="utf-8") as f:
            existing = json.load(f)

        before = len(existing)

        # Deduplicate by word — don't add if word already exists
        existing_words = set()
        for slot in existing:
            w = slot.get("word")
            if w:
                existing_words.add(w.lower())

        added = 0
        for entry in new_entries:
            w = entry.get("word", "").lower()
            if w and w not in existing_words:
                existing.append(entry)
                existing_words.add(w)
                added += 1

        # Save merged file
        stream_write(dst_file, existing)

        dt = time.time() - t0
        total_merged += added
        print(f"  [{letter}]  was: {before:>10,}  added: {added:>8,}  now: {len(existing):>10,}  ({dt:.1f}s)")

        del existing, new_entries

    elapsed = time.time() - start
    print(f"\n{'='*70}")
    print(f"MERGE COMPLETE in {elapsed:.1f}s")
    print(f"  Total entries merged: {total_merged:,}")
    print(f"  Source: {source_dir}")
    print(f"  → Lexicon_Canonical now contains base + merged entries")
    print(f"\n  Source directory left intact for manual cleanup.")
    print(f"  To remove: rename to _DELETE_ME_{source_name}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
