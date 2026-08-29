"""Extract AVAILABLE slots from system lexicon into Spare_Slots_Pool.

After running:
  - Lexicon_Canonical/ contains ONLY ASSIGNED entries (locked system lexicon)
  - Spare_Slots_Pool/  contains ONLY AVAILABLE slots (user allocation pool)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
LEXICON_DIR = REPO / "Lexical Data" / "Canonical"
POOL_DIR = REPO / "Lexical Data" / "Spare_Slots"
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
    if "--legacy-paths" not in sys.argv[1:]:
        print("Refusing to run hardcoded legacy paths.")
        print("Re-run with: python tools/lexicon/extract_pool.py --legacy-paths")
        sys.exit(1)

    POOL_DIR.mkdir(parents=True, exist_ok=True)

    print(f"System lexicon: {LEXICON_DIR}")
    print(f"Pool output:    {POOL_DIR}")
    print(f"{'='*70}")
    print(f"{'Letter':>6} {'Total':>10} {'Assigned':>10} {'Available':>10}")
    print(f"{'-'*46}")

    grand_assigned = 0
    grand_available = 0
    start = time.time()

    for letter in LETTERS:
        src = LEXICON_DIR / f"canonical_{letter}.json"
        pool_out = POOL_DIR / f"pool_{letter}.json"

        if not src.exists():
            print(f"     {letter}  MISSING")
            continue

        t0 = time.time()
        with open(src, "r", encoding="utf-8") as f:
            slots = json.load(f)

        assigned = []
        available = []
        for slot in slots:
            if slot.get("status") == "ASSIGNED":
                assigned.append(slot)
            else:
                available.append(slot)

        # Free original list
        del slots

        # Write assigned back to system lexicon
        stream_write(src, assigned)

        # Write available to pool
        stream_write(pool_out, available)

        dt = time.time() - t0
        print(f"     {letter}  {len(assigned)+len(available):>10,}  {len(assigned):>10,}  {len(available):>10,}  ({dt:.1f}s)")

        grand_assigned += len(assigned)
        grand_available += len(available)

        # Free memory before next letter
        del assigned, available

    elapsed = time.time() - start
    print(f"{'-'*46}")
    print(f" TOTAL  {grand_assigned+grand_available:>10,}  {grand_assigned:>10,}  {grand_available:>10,}")
    print(f"\nCOMPLETE in {elapsed:.1f}s")
    print(f"  System lexicon (locked): {grand_assigned:>12,} entries")
    print(f"  Spare slots pool:        {grand_available:>12,} slots")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
