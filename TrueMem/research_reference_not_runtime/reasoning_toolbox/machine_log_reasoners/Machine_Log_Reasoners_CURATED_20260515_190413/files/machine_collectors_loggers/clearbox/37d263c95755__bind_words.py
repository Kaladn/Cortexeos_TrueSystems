"""Bind verified word lists to canonical slots.

Usage:
    python bind_words.py C:\\Users\\mydyi\\Desktop\\verified_words

Input:  Directory containing verified_A.json .. verified_Z.json
        Each file is a flat JSON array of strings.

Behaviour:
    1. For each letter A-Z, open verified_<L>.json and canonical_<L>.json
    2. Normalize words to lowercase, deduplicate, sort
    3. Walk canonical slots, find AVAILABLE, bind word, flip status to ASSIGNED
    4. Save canonical_<L>.json back in place
    5. Print per-letter and total summary
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
LEXICON_DIR = REPO / "Lexical Data" / "Canonical"
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


def load_and_normalize(path: Path) -> list[str]:
    """Load word list, normalize lowercase, deduplicate, sort."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    seen = set()
    words = []
    for w in raw:
        if not isinstance(w, str):
            continue
        norm = w.strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            words.append(norm)
    words.sort()
    return words


def bind_letter(letter: str, words_path: Path) -> dict:
    """Bind a single letter's word list to its canonical slot file."""
    slot_file = LEXICON_DIR / f"canonical_{letter}.json"

    if not words_path.exists():
        return {"letter": letter, "words": 0, "slots": 0, "bound": 0, "skipped": 0, "note": "no word file"}
    if not slot_file.exists():
        return {"letter": letter, "words": 0, "slots": 0, "bound": 0, "skipped": 0, "note": "no slot file"}

    # Load words
    words = load_and_normalize(words_path)
    if not words:
        return {"letter": letter, "words": 0, "slots": 0, "bound": 0, "skipped": 0, "note": "empty word list"}

    # Load slots
    with open(slot_file, "r", encoding="utf-8") as f:
        slots = json.load(f)

    total_slots = len(slots)
    bound = 0
    word_iter = iter(words)
    current_word = next(word_iter, None)

    for slot in slots:
        if current_word is None:
            break
        if slot.get("status") != "AVAILABLE":
            continue
        slot["word"] = current_word
        slot["status"] = "ASSIGNED"
        bound += 1
        current_word = next(word_iter, None)

    # Count remaining unbound words
    remaining = 0
    if current_word is not None:
        remaining = 1
        for _ in word_iter:
            remaining += 1

    # Save — write to temp file first, then swap (protects original on crash)
    tmp_file = slot_file.with_suffix('.tmp')
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write('[\n')
        last = len(slots) - 1
        for i, slot in enumerate(slots):
            f.write(json.dumps(slot, ensure_ascii=False))
            if i < last:
                f.write(',\n')
            else:
                f.write('\n')
        f.write(']\n')
    # Atomic-ish swap: remove original, rename temp
    os.replace(tmp_file, slot_file)

    return {
        "letter": letter,
        "words": len(words),
        "slots": total_slots,
        "bound": bound,
        "skipped": remaining,
        "available_after": total_slots - bound,
    }


def main():
    allow_legacy, args = _consume_legacy_flag(sys.argv[1:])
    if not allow_legacy:
        print("Refusing to run hardcoded legacy paths.")
        print("Re-run with: python tools/domain/bind_words.py --legacy-paths <verified_words_directory>")
        sys.exit(1)

    if len(args) < 1:
        print("Usage: python bind_words.py <verified_words_directory>")
        print("       python bind_words.py --legacy-paths <verified_words_directory>")
        sys.exit(1)

    words_dir = Path(args[0])
    if not words_dir.is_dir():
        print(f"Not a directory: {words_dir}")
        sys.exit(1)

    print(f"Word list dir:  {words_dir}")
    print(f"Lexicon dir:    {LEXICON_DIR}")
    print(f"{'='*70}")

    start = time.time()
    total_words = 0
    total_bound = 0
    total_skipped = 0
    total_slots = 0
    total_available_after = 0

    for letter in LETTERS:
        words_path = words_dir / f"verified_{letter}.json"
        t0 = time.time()
        result = bind_letter(letter, words_path)
        dt = time.time() - t0

        total_words += result.get("words", 0)
        total_bound += result.get("bound", 0)
        total_skipped += result.get("skipped", 0)
        total_slots += result.get("slots", 0)
        total_available_after += result.get("available_after", 0)

        note = result.get("note", "")
        if note:
            print(f"  [{letter}] {note}")
        else:
            print(
                f"  [{letter}]  words: {result['words']:>8,}  "
                f"slots: {result['slots']:>8,}  "
                f"bound: {result['bound']:>8,}  "
                f"skipped: {result['skipped']:>6,}  "
                f"avail after: {result['available_after']:>8,}  "
                f"({dt:.1f}s)"
            )

    elapsed = time.time() - start

    print(f"\n{'='*70}")
    print(f"COMPLETE in {elapsed:.1f}s")
    print(f"  Total words:           {total_words:>12,}")
    print(f"  Total slots:           {total_slots:>12,}")
    print(f"  Total bound:           {total_bound:>12,}")
    print(f"  Total skipped:         {total_skipped:>12,}")
    print(f"  Slots available after: {total_available_after:>12,}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
