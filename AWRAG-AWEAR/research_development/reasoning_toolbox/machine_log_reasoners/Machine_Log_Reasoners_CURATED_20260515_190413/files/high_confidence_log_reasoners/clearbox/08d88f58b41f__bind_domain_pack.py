"""Bind a domain word list to spare pool slots, creating a new domain lexicon.

Usage:
    python tools\bind_domain_pack.py <word_dir> <output_dir> <prefix>

Examples:
    python tools\bind_domain_pack.py Desktop\wordfreq_words Lexicon_WordFreq wf
    python tools\bind_domain_pack.py Desktop\scispacy_words Lexicon_Medical med

Input:  Directory containing <prefix>_A.json .. <prefix>_Z.json (or wordfreq_A, med_A, etc.)
        Each file is a flat JSON array of strings.

Behaviour:
    1. For each letter A-Z, load word list and pool file
    2. Bind words to AVAILABLE pool slots
    3. Move bound slots from pool to new domain lexicon directory
    4. Save updated pool (minus consumed slots)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BASE_DIR = REPO / "Lexical Data"
POOL_DIR = BASE_DIR / "Spare_Slots"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _consume_legacy_flag(argv: list[str]) -> tuple[bool, list[str]]:
    allow = False
    filtered: list[str] = []
    for arg in argv:
        if arg == "--legacy-paths":
            allow = True
            continue
        filtered.append(arg)
    return allow, filtered


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


def find_word_file(words_dir: Path, letter: str) -> Path | None:
    """Find word file for a letter — tries common naming patterns."""
    patterns = [
        f"wordfreq_{letter}.json",
        f"scispacy_{letter}.json",
        f"med_{letter}.json",
        f"wf_{letter}.json",
        f"verified_{letter}.json",
        f"legal_{letter}.json",
        f"finance_{letter}.json",
    ]
    for pattern in patterns:
        path = words_dir / pattern
        if path.exists():
            return path
    # Try any file matching *_<letter>.json
    for p in words_dir.glob(f"*_{letter}.json"):
        return p
    return None


def main():
    allow_legacy, args = _consume_legacy_flag(sys.argv[1:])
    if not allow_legacy:
        print("Refusing to run hardcoded legacy paths.")
        print("Re-run with: python tools/domain/bind_domain_pack.py --legacy-paths <word_dir> <output_dir_name> <file_prefix>")
        sys.exit(1)

    if len(args) < 3:
        print("Usage: python bind_domain_pack.py <word_dir> <output_dir_name> <file_prefix>")
        print("       python bind_domain_pack.py --legacy-paths <word_dir> <output_dir_name> <file_prefix>")
        print("  word_dir:        path to directory with word lists")
        print("  output_dir_name: name of output directory (e.g. Lexicon_WordFreq)")
        print("  file_prefix:     prefix for output files (e.g. wf → wf_A.json)")
        sys.exit(1)

    words_dir = Path(args[0])
    if not words_dir.is_absolute():
        # Try relative to Desktop or CLEARBOX_AI_PRODUCTION
        desktop = Path(os.path.expanduser("~")) / "Desktop"
        if (desktop / words_dir).is_dir():
            words_dir = desktop / words_dir
        elif (BASE_DIR / words_dir).is_dir():
            words_dir = BASE_DIR / words_dir

    output_name = args[1]
    output_dir = BASE_DIR / output_name
    prefix = args[2]

    if not words_dir.is_dir():
        print(f"Not a directory: {words_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Word list dir:  {words_dir}")
    print(f"Pool dir:       {POOL_DIR}")
    print(f"Output dir:     {output_dir}")
    print(f"File prefix:    {prefix}")
    print(f"{'='*70}")

    start = time.time()
    total_words = 0
    total_bound = 0
    total_skipped = 0
    pool_consumed = 0

    for letter in LETTERS:
        word_file = find_word_file(words_dir, letter)
        pool_file = POOL_DIR / f"pool_{letter}.json"
        out_file = output_dir / f"{prefix}_{letter}.json"

        if word_file is None:
            continue

        t0 = time.time()

        # Load words
        with open(word_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        words = sorted(set(w.strip().lower() for w in raw if isinstance(w, str) and w.strip()))

        if not words:
            print(f"  [{letter}]  empty word list")
            continue

        # Load pool
        if not pool_file.exists():
            print(f"  [{letter}]  NO POOL FILE — skipping {len(words)} words")
            total_skipped += len(words)
            continue

        with open(pool_file, "r", encoding="utf-8") as f:
            pool = json.load(f)

        # Bind words to available pool slots
        bound_slots = []
        remaining_pool = []
        word_iter = iter(words)
        current_word = next(word_iter, None)

        for slot in pool:
            if current_word is None:
                remaining_pool.append(slot)
                continue
            if slot.get("status") != "AVAILABLE":
                remaining_pool.append(slot)
                continue
            slot["word"] = current_word
            slot["status"] = "ASSIGNED"
            bound_slots.append(slot)
            current_word = next(word_iter, None)

        # If we ran out of available slots before words
        if current_word is None:
            # Collect remaining pool slots
            pass  # remaining_pool already has them
        else:
            # Count remaining unbound words
            remaining_pool_tail = []
            skipped = 1  # current_word wasn't placed
            for _ in word_iter:
                skipped += 1
            total_skipped += skipped

        bound = len(bound_slots)
        total_words += len(words)
        total_bound += bound
        pool_consumed += bound

        # Save domain lexicon file
        stream_write(out_file, bound_slots)

        # Save updated pool (minus consumed slots)
        stream_write(pool_file, remaining_pool)

        dt = time.time() - t0
        avail_after = len(remaining_pool)
        print(
            f"  [{letter}]  words: {len(words):>8,}  "
            f"bound: {bound:>8,}  "
            f"pool remaining: {avail_after:>8,}  "
            f"({dt:.1f}s)"
        )

        del pool, bound_slots, remaining_pool

    elapsed = time.time() - start

    print(f"\n{'='*70}")
    print(f"COMPLETE in {elapsed:.1f}s")
    print(f"  Total words:       {total_words:>12,}")
    print(f"  Total bound:       {total_bound:>12,}")
    print(f"  Total skipped:     {total_skipped:>12,}")
    print(f"  Pool slots used:   {pool_consumed:>12,}")
    print(f"  Output → {output_dir}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
