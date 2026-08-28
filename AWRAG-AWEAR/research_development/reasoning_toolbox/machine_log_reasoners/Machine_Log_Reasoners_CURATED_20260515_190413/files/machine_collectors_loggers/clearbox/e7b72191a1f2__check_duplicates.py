"""Duplicate and integrity check across the system lexicon.

Checks:
  1. Duplicate words within each letter file
  2. Duplicate words across letter files
  3. Words in wrong letter file (e.g. "banana" in canonical_A.json)
  4. Duplicate hex addresses within each file
  5. Duplicate hex addresses across all files
  6. Entries missing required fields
  7. Summary stats
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from collections import Counter

REPO = Path(__file__).resolve().parent.parent.parent
LEXICON_DIR = REPO / "Lexical Data" / "Canonical"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _require_legacy_opt_in() -> None:
    if "--legacy-paths" in sys.argv[1:]:
        return
    raise SystemExit(
        "Refusing to run hardcoded legacy paths. Re-run with: "
        "python tools/audit/check_duplicates.py --legacy-paths"
    )


def main():
    _require_legacy_opt_in()
    start = time.time()

    all_words: Counter = Counter()       # word -> count across ALL files
    all_hex: Counter = Counter()         # hex -> count across ALL files
    word_locations: dict[str, list[str]] = {}  # word -> [letters where found]

    total_entries = 0
    total_assigned = 0
    total_no_word = 0
    total_no_hex = 0
    wrong_letter = 0
    within_file_word_dupes = 0
    within_file_hex_dupes = 0

    print(f"Scanning {LEXICON_DIR}")
    print(f"{'='*70}")

    for letter in LETTERS:
        path = LEXICON_DIR / f"canonical_{letter}.json"
        if not path.exists():
            print(f"  [{letter}] MISSING")
            continue

        with open(path, "r", encoding="utf-8") as f:
            slots = json.load(f)

        file_words: Counter = Counter()
        file_hex: Counter = Counter()
        file_no_word = 0
        file_no_hex = 0
        file_wrong_letter = 0

        for slot in slots:
            if not isinstance(slot, dict):
                continue

            word = slot.get("word")
            hex_addr = slot.get("hex")
            status = slot.get("status", "UNKNOWN")

            # Track hex
            if hex_addr:
                file_hex[hex_addr] += 1
                all_hex[hex_addr] += 1
            else:
                file_no_hex += 1
                total_no_hex += 1

            # Track word (only for ASSIGNED)
            if status == "ASSIGNED":
                total_assigned += 1
                if word and isinstance(word, str) and word.strip():
                    norm = word.strip().lower()
                    file_words[norm] += 1
                    all_words[norm] += 1
                    word_locations.setdefault(norm, []).append(letter)

                    # Check correct letter file
                    expected = norm[0].upper() if norm[0].isalpha() else "_"
                    if expected != letter:
                        file_wrong_letter += 1
                        wrong_letter += 1
                else:
                    file_no_word += 1
                    total_no_word += 1

            total_entries += 1

        # Within-file duplicates
        word_dupes = {w: c for w, c in file_words.items() if c > 1}
        hex_dupes = {h: c for h, c in file_hex.items() if c > 1}
        within_file_word_dupes += len(word_dupes)
        within_file_hex_dupes += len(hex_dupes)

        issues = []
        if word_dupes:
            issues.append(f"{len(word_dupes)} word dupes")
        if hex_dupes:
            issues.append(f"{len(hex_dupes)} hex dupes")
        if file_wrong_letter:
            issues.append(f"{file_wrong_letter} wrong letter")
        if file_no_word:
            issues.append(f"{file_no_word} assigned without word")
        if file_no_hex:
            issues.append(f"{file_no_hex} missing hex")

        status_str = "  CLEAN" if not issues else "  " + ", ".join(issues)
        print(f"  [{letter}] {len(slots):>8,} entries  {sum(1 for w,c in file_words.items()):>8,} unique words{status_str}")

        if word_dupes and len(word_dupes) <= 10:
            for w, c in sorted(word_dupes.items()):
                print(f"        DUPE WORD: '{w}' x{c}")
        elif word_dupes:
            top = sorted(word_dupes.items(), key=lambda x: -x[1])[:5]
            print(f"        Top dupes: {', '.join(f'{w} x{c}' for w,c in top)} ...")

    # Cross-file analysis
    print(f"\n{'='*70}")
    print("CROSS-FILE ANALYSIS")
    print(f"{'='*70}")

    cross_word_dupes = {w: c for w, c in all_words.items() if c > 1}
    cross_hex_dupes = {h: c for h, c in all_hex.items() if c > 1}

    print(f"\n  Unique words:          {len(all_words):>12,}")
    print(f"  Unique hex addresses:  {len(all_hex):>12,}")

    print(f"\n  Cross-file word dupes: {len(cross_word_dupes):>12,}")
    if cross_word_dupes:
        top = sorted(cross_word_dupes.items(), key=lambda x: -x[1])[:20]
        for w, c in top:
            locs = word_locations.get(w, [])
            print(f"    '{w}' x{c} in files: {', '.join(locs)}")

    print(f"\n  Cross-file hex dupes:  {len(cross_hex_dupes):>12,}")
    if cross_hex_dupes and len(cross_hex_dupes) <= 10:
        for h, c in sorted(cross_hex_dupes.items(), key=lambda x: -x[1]):
            print(f"    {h} x{c}")
    elif cross_hex_dupes:
        print(f"    (showing top 10)")
        for h, c in sorted(cross_hex_dupes.items(), key=lambda x: -x[1])[:10]:
            print(f"    {h} x{c}")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Total entries scanned:     {total_entries:>12,}")
    print(f"  Total ASSIGNED:            {total_assigned:>12,}")
    print(f"  Unique words:              {len(all_words):>12,}")
    print(f"  Unique hex addresses:      {len(all_hex):>12,}")
    print(f"  Within-file word dupes:    {within_file_word_dupes:>12,}")
    print(f"  Within-file hex dupes:     {within_file_hex_dupes:>12,}")
    print(f"  Cross-file word dupes:     {len(cross_word_dupes):>12,}")
    print(f"  Cross-file hex dupes:      {len(cross_hex_dupes):>12,}")
    print(f"  Wrong letter file:         {wrong_letter:>12,}")
    print(f"  Assigned without word:     {total_no_word:>12,}")
    print(f"  Missing hex address:       {total_no_hex:>12,}")

    elapsed = time.time() - start
    clean = (within_file_word_dupes == 0 and within_file_hex_dupes == 0
             and len(cross_word_dupes) == 0 and len(cross_hex_dupes) == 0
             and wrong_letter == 0 and total_no_word == 0 and total_no_hex == 0)

    print(f"\n  Completed in {elapsed:.1f}s")
    if clean:
        print(f"\n  ✓ LEXICON IS CLEAN — NO ISSUES FOUND")
    else:
        print(f"\n  ✗ ISSUES DETECTED — SEE ABOVE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
