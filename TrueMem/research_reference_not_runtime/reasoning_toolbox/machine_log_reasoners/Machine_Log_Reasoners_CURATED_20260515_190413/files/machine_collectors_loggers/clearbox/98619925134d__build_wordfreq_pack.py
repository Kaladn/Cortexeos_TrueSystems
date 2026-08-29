"""Build wordfreq modern English language pack.

Extracts real-usage English words from wordfreq (Google Books, Wikipedia,
Twitter, Reddit, subtitles), diffs against the system lexicon, and outputs
net-new words bucketed by letter for binding.

Usage:
    python tools\build_wordfreq_pack.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from wordfreq import top_n_list, zipf_frequency

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

MIN_ZIPF = 1.0          # appears at least once per 100M words
TOP_N = 500_000          # pull top 500K words from wordfreq
MIN_LEN = 2
ALLOW_POSSESSIVE = False  # wordfreq words don't need possessive expansion

DESKTOP = Path(os.path.expanduser("~")) / "Desktop"
OUT_DIR = DESKTOP / "wordfreq_words"
REPO = Path(__file__).resolve().parent.parent.parent
LEXICON_DIR = REPO / "Lexical Data" / "Canonical"

valid_re = re.compile(r"^[a-z]+$")


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def valid(word: str) -> bool:
    return len(word) >= MIN_LEN and valid_re.match(word) is not None


def expand_word(w: str) -> set[str]:
    """Same deterministic expansions as base lexicon build."""
    forms = set()
    forms.add(w)
    forms.add(w + "s")
    forms.add(w + "es")
    forms.add(w + "ed")
    forms.add(w + "ing")
    forms.add(w + "er")
    forms.add(w + "ers")
    forms.add(w + "ly")
    forms.add(w + "ness")
    forms.add(w + "ment")
    return forms


def load_system_lexicon_words() -> set[str]:
    """Load all words from the locked system lexicon."""
    print("Loading system lexicon words for dedup...")
    t0 = time.time()
    words = set()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        path = LEXICON_DIR / f"canonical_{letter}.json"
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            slots = json.load(f)
        for slot in slots:
            w = slot.get("word")
            if w:
                words.add(w.lower())
        del slots
    print(f"  {len(words):,} system words loaded ({time.time()-t0:.1f}s)")
    return words


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if "--legacy-paths" not in sys.argv[1:]:
        print("Refusing to run hardcoded legacy paths.")
        print("Re-run with: python tools/domain/build_wordfreq_pack.py --legacy-paths")
        sys.exit(1)

    start = time.time()

    # Step 1: Pull words from wordfreq
    print(f"Pulling top {TOP_N:,} English words from wordfreq...")
    raw_words = top_n_list("en", TOP_N, wordlist="best")
    print(f"  Got {len(raw_words):,} words")

    # Step 2: Filter — alpha only, min length, above zipf threshold
    print(f"Filtering (alpha-only, min len {MIN_LEN}, zipf >= {MIN_ZIPF})...")
    roots = set()
    for w in raw_words:
        w = w.lower().strip()
        if valid(w) and zipf_frequency(w, "en") >= MIN_ZIPF:
            roots.add(w)
    print(f"  {len(roots):,} valid roots after filter")

    # Step 3: Load system lexicon for dedup
    system_words = load_system_lexicon_words()

    # Step 4: Filter out words already in system lexicon (check roots only first)
    new_roots = roots - system_words
    print(f"  {len(new_roots):,} net-new roots (not in system lexicon)")

    # Step 5: Expand
    print("Expanding forms...")
    all_words = set()
    for w in new_roots:
        for f in expand_word(w):
            if valid(f):
                all_words.add(f)

    # Step 6: Final dedup against system lexicon (expanded forms too)
    net_new = all_words - system_words
    print(f"  {len(net_new):,} total net-new words after expansion and dedup")

    # Step 7: Bucket by letter
    print("Bucketing...")
    buckets: dict[str, list[str]] = defaultdict(list)
    for w in net_new:
        first = w[0].upper()
        if first.isalpha():
            buckets[first].append(w)

    # Step 8: Write
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        words_list = sorted(set(buckets.get(letter, [])))
        path = OUT_DIR / f"wordfreq_{letter}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(words_list, f, indent=2)
        count = len(words_list)
        total += count
        if count > 0:
            print(f"  {letter}: {count:,}")

    elapsed = time.time() - start
    print(f"\nDONE in {elapsed:.1f}s")
    print(f"  Total net-new words: {total:,}")
    print(f"  Output → {OUT_DIR}")


if __name__ == "__main__":
    main()
