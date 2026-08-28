"""Audit all domain lexicon packs.

Checks:
  1. Per-pack: total entries, unique words, unique hex, zero dupes
  2. Cross-pack: no word appears in multiple packs
  3. Cross-system: no domain word duplicates a system lexicon word
  4. Pool depletion report
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from collections import Counter

REPO = Path(__file__).resolve().parent.parent.parent
BASE_DIR = REPO / "Lexical Data"
LEXICON_DIRS = {
    "System (base)": BASE_DIR / "Canonical",
    "Medical (bio)": BASE_DIR / "Medical",
}
POOL_DIR = BASE_DIR / "Spare_Slots"


def _require_legacy_opt_in() -> None:
    if "--legacy-paths" in sys.argv[1:]:
        return
    raise SystemExit(
        "Refusing to run hardcoded legacy paths. Re-run with: "
        "python tools/audit/audit_domain_packs.py --legacy-paths"
    )


def scan_dir(name: str, d: Path) -> tuple[set[str], set[str], int]:
    """Scan a lexicon directory. Returns (words, hex_addrs, total_entries)."""
    words = set()
    hexes = set()
    total = 0
    word_dupes = 0
    hex_dupes = 0

    if not d.exists():
        print(f"\n  [{name}]  NOT FOUND — skipping")
        return words, hexes, total

    print(f"\n  [{name}]  {d}")

    for path in sorted(d.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            slots = json.load(f)

        file_words = Counter()
        file_hexes = Counter()

        for slot in slots:
            if not isinstance(slot, dict):
                continue
            total += 1
            w = slot.get("word")
            h = slot.get("hex")
            if w:
                norm = w.lower()
                file_words[norm] += 1
                words.add(norm)
            if h:
                file_hexes[h] += 1
                hexes.add(h)

        fw_dupes = sum(1 for c in file_words.values() if c > 1)
        fh_dupes = sum(1 for c in file_hexes.values() if c > 1)
        word_dupes += fw_dupes
        hex_dupes += fh_dupes

    status = "CLEAN" if (word_dupes == 0 and hex_dupes == 0) else f"{word_dupes} word dupes, {hex_dupes} hex dupes"
    print(f"    Entries:      {total:>12,}")
    print(f"    Unique words: {len(words):>12,}")
    print(f"    Unique hex:   {len(hexes):>12,}")
    print(f"    Status:       {status}")

    return words, hexes, total


def count_pool() -> int:
    """Count remaining available slots in pool."""
    total = 0
    if not POOL_DIR.exists():
        return 0
    for path in sorted(POOL_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            slots = json.load(f)
        total += len(slots)
    return total


def main():
    _require_legacy_opt_in()
    start = time.time()
    print("=" * 70)
    print("DOMAIN LEXICON PACK AUDIT")
    print("=" * 70)

    all_packs: dict[str, set[str]] = {}
    all_hexes: dict[str, set[str]] = {}
    grand_total = 0

    for name, d in LEXICON_DIRS.items():
        words, hexes, total = scan_dir(name, d)
        all_packs[name] = words
        all_hexes[name] = hexes
        grand_total += total

    # Cross-pack word overlap
    print(f"\n{'='*70}")
    print("CROSS-PACK ANALYSIS")
    print(f"{'='*70}")

    pack_names = list(all_packs.keys())
    overlap_found = False
    for i in range(len(pack_names)):
        for j in range(i + 1, len(pack_names)):
            n1, n2 = pack_names[i], pack_names[j]
            overlap = all_packs[n1] & all_packs[n2]
            if overlap:
                overlap_found = True
                print(f"\n  ✗ OVERLAP: {n1} ∩ {n2} = {len(overlap):,} words")
                if len(overlap) <= 10:
                    for w in sorted(overlap):
                        print(f"      '{w}'")
                else:
                    for w in sorted(overlap)[:5]:
                        print(f"      '{w}'")
                    print(f"      ... and {len(overlap)-5:,} more")
            else:
                print(f"\n  ✓ {n1} ∩ {n2} = 0 (clean)")

    # Cross-pack hex overlap
    hex_overlap_found = False
    for i in range(len(pack_names)):
        for j in range(i + 1, len(pack_names)):
            n1, n2 = pack_names[i], pack_names[j]
            h_overlap = all_hexes[n1] & all_hexes[n2]
            if h_overlap:
                hex_overlap_found = True
                print(f"\n  ✗ HEX OVERLAP: {n1} ∩ {n2} = {len(h_overlap):,} addresses")

    if not hex_overlap_found:
        print(f"\n  ✓ No hex address overlaps across packs")

    # Pool status
    print(f"\n{'='*70}")
    print("POOL STATUS")
    print(f"{'='*70}")
    pool_remaining = count_pool()
    print(f"  Pool slots remaining: {pool_remaining:>12,}")
    print(f"  Total bound (all):    {grand_total:>12,}")
    print(f"  Original pool:        {9_851_559:>12,}")
    print(f"  Utilization:          {(grand_total/9_851_559)*100:>11.1f}%")

    # Summary
    elapsed = time.time() - start
    clean = not overlap_found and not hex_overlap_found

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for name in pack_names:
        print(f"  {name:<25} {len(all_packs[name]):>12,} words")
    print(f"  {'Pool remaining':<25} {pool_remaining:>12,} slots")
    print(f"\n  Completed in {elapsed:.1f}s")

    if clean:
        print(f"\n  ✓ ALL PACKS CLEAN — NO OVERLAPS")
    else:
        print(f"\n  ✗ OVERLAPS DETECTED — SEE ABOVE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
