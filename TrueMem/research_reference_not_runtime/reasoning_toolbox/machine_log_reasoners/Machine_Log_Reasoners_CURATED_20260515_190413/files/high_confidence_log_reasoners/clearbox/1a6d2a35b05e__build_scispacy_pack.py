"""Build scispaCy biomedical language pack.

Extracts the ~785K vocabulary from Allen AI's en_core_sci_lg model
(trained on PubMed/MEDLINE), diffs against system lexicon and any
previously built packs, outputs net-new biomedical terms.

IMPORTANT: No expansion on medical terms. "carcinoma" stays "carcinoma".
           We do NOT generate "carcinomaed", "carcinomaing", etc.

Usage:
    python tools\build_scispacy_pack.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import spacy

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

MODEL = "en_core_sci_lg"   # 785K vocab, 600K word vectors
MIN_LEN = 3                # medical terms shorter than 3 chars are noise
NO_EXPANSION = True        # DO NOT expand medical terms

REPO = Path(__file__).resolve().parent.parent.parent
DESKTOP = Path.home() / "Desktop"
OUT_DIR = DESKTOP / "scispacy_words"
LEXICON_DIR = REPO / "Lexical Data" / "Canonical"
WORDFREQ_DIR = REPO / "Lexical Data" / "WordFreq"

valid_re = re.compile(r"^[a-z]+$")


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def valid(word: str) -> bool:
    return len(word) >= MIN_LEN and valid_re.match(word) is not None


def load_existing_words(*dirs: Path) -> set[str]:
    """Load all words from one or more lexicon directories."""
    words = set()
    for d in dirs:
        if not d.exists():
            continue
        for path in sorted(d.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    slots = json.load(f)
                for slot in slots:
                    if isinstance(slot, dict):
                        w = slot.get("word")
                        if w:
                            words.add(w.lower())
                    elif isinstance(slot, str):
                        words.add(slot.lower())
            except Exception:
                continue
    return words


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if "--legacy-paths" not in sys.argv[1:]:
        print("Refusing to run hardcoded legacy paths.")
        print("Re-run with: python tools/domain/build_scispacy_pack.py --legacy-paths")
        sys.exit(1)

    start = time.time()

    # Step 1: Load scispaCy model
    print(f"Loading {MODEL}...")
    t0 = time.time()
    nlp = spacy.load(MODEL)
    vocab_size = len(nlp.vocab)
    print(f"  Model loaded ({time.time()-t0:.1f}s)")
    print(f"  Vocab size: {vocab_size:,}")

    # Step 2: Extract all vocabulary strings from word vectors
    # nlp.vocab only has loaded lexemes (~800). The real vocabulary
    # is in the word vectors table — that's where the 785K lives.
    print("Extracting vocabulary from word vectors...")
    raw_words = set()

    # Primary source: word vectors (this is the 785K)
    vector_keys = nlp.vocab.vectors.keys()
    print(f"  Vector keys: {len(vector_keys):,}")
    for key in vector_keys:
        try:
            text = nlp.vocab.strings[key].lower().strip()
            if valid(text):
                raw_words.add(text)
        except KeyError:
            continue

    # Secondary source: vocab lexemes (small, but catches stragglers)
    for word in nlp.vocab:
        text = word.text.lower().strip()
        if valid(text):
            raw_words.add(text)

    print(f"  {len(raw_words):,} valid alpha-only words extracted")

    # Free the model
    del nlp

    # Step 3: Load existing words for dedup
    print("Loading existing lexicons for dedup...")
    t0 = time.time()
    existing = load_existing_words(LEXICON_DIR, WORDFREQ_DIR)
    print(f"  {len(existing):,} existing words loaded ({time.time()-t0:.1f}s)")

    # Step 4: Diff — net-new only
    net_new = raw_words - existing
    print(f"  {len(net_new):,} net-new biomedical terms")

    # Step 5: NO expansion for medical terms
    if NO_EXPANSION:
        print("  Skipping expansion (medical terms stay as-is)")
        final = net_new
    else:
        # Would expand here if needed
        final = net_new

    # Step 6: Bucket by letter
    print("Bucketing...")
    buckets: dict[str, list[str]] = defaultdict(list)
    for w in final:
        first = w[0].upper()
        if first.isalpha():
            buckets[first].append(w)

    # Step 7: Write
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        words_list = sorted(set(buckets.get(letter, [])))
        path = OUT_DIR / f"scispacy_{letter}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(words_list, f, indent=2)
        count = len(words_list)
        total += count
        if count > 0:
            print(f"  {letter}: {count:,}")

    elapsed = time.time() - start
    print(f"\nDONE in {elapsed:.1f}s")
    print(f"  Total net-new biomedical terms: {total:,}")
    print(f"  Output → {OUT_DIR}")


if __name__ == "__main__":
    main()
