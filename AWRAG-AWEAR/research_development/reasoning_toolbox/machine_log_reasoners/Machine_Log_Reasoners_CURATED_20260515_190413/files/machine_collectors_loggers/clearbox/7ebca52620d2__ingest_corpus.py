#!/usr/bin/env python3
"""Sequential corpus ingest. One chat at a time. Read → symbolize → map → write.

No workers. No parallelism. No race conditions.
Lexicon loads once. Each conversation flows through end-to-end before the next.
"""
import sys
import io
import json
import time
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WINDOW = 6
BASE = (
    "C:/Users/mydyi/Downloads/"
    "05b6e602532b3d075340cbcc28a8c83e4d269fb9a6179f9cc2c87c077f3584ee"
    "-2026-04-07-12-48-39-ad0041cbbad646f5a0a32474b8d459eb"
)

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF\U0000FE00-\U0000FE0F\U0000200D"
    "]+", re.UNICODE,
)
_SPLIT_RE = re.compile(r"[^\w']+", re.UNICODE)


def extract_anchors(text):
    text = _EMOJI_RE.sub(" emjnull ", text)
    text = unicodedata.normalize("NFKC", text).lower()
    return [w for w in _SPLIT_RE.sub(" ", text).split() if w]


def load_docs():
    convos = []
    for f in ["conversations-000.json", "conversations-001.json"]:
        convos.extend(json.loads(open(f"{BASE}/{f}", encoding="utf-8").read()))
    docs = []
    for conv in convos:
        title = conv.get("title", "untitled")[:50]
        parts = []
        for node in conv.get("mapping", {}).values():
            msg = node.get("message")
            if not msg:
                continue
            for part in msg.get("content", {}).get("parts", []):
                if isinstance(part, str) and part.strip():
                    parts.append(part.strip())
        if parts:
            docs.append((title, "\n\n".join(parts)))
    return docs


def process_one(text, word_index):
    """Read → symbolize → map → return symbol-keyed counts."""
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    total_words = 0
    total_symbols = 0

    for block in blocks:
        # 1. Extract anchor words from block
        words = extract_anchors(block)
        total_words += len(words)

        # 2. Convert to symbols (drop unknowns)
        symbols = [word_index.get(w) for w in words]
        symbols = [s for s in symbols if s]
        n = len(symbols)
        total_symbols += n
        if n < 2:
            continue

        # 3. Map: 6-1-6 window count on symbol sequence
        for i in range(n):
            focus = symbols[i]
            for j in range(max(0, i - WINDOW), i):
                counts[focus][j - i][symbols[j]] += 1
            for j in range(i + 1, min(n, i + WINDOW + 1)):
                counts[focus][j - i][symbols[j]] += 1

    # Convert to plain dicts
    plain = {
        f: {o: dict(n) for o, n in offs.items()}
        for f, offs in counts.items()
    }
    return plain, total_words, total_symbols


def main():
    docs = load_docs()
    print(f"Documents: {len(docs)}")

    print("Loading lexicon...")
    t = time.time()
    from bridges.clearbox_bridge import load_bridge_from_config
    from security.data_paths import CLEARBOX_CONFIG_PATH
    bridge = load_bridge_from_config(Path(CLEARBOX_CONFIG_PATH))
    word_index = dict(bridge.word_index)
    del bridge
    print(f"Lexicon: {len(word_index):,} words ({time.time()-t:.1f}s)")

    from bridges.evidence_store import get_evidence_store
    store = get_evidence_store()
    print(f"Evidence before: {store.count():,} cells")
    print()

    t0 = time.time()
    total_words = 0
    total_symbols = 0
    errs = 0

    for i, (title, text) in enumerate(docs):
        try:
            t_doc = time.time()

            # Stage 1: read → symbolize → map (in process_one)
            counts, words, symbols = process_one(text, word_index)
            total_words += words
            total_symbols += symbols
            map_time = time.time() - t_doc

            # Stage 2: write to evidence store
            t_write = time.time()
            if counts:
                store.append_counts(counts)
            write_time = time.time() - t_write

            doc_time = time.time() - t_doc
            elapsed = time.time() - t0
            eta = (len(docs) - i - 1) * (elapsed / (i + 1))

            print(
                f"  [{i+1}/{len(docs)}] {doc_time:.1f}s "
                f"(map {map_time:.1f}s + write {write_time:.1f}s) "
                f"| {len(counts):,} cells | ev={store.count():,} | ETA {eta:.0f}s | {title}"
            )
        except Exception as e:
            errs += 1
            print(f"  ERR [{i+1}] {title}: {str(e)[:120]}")

    elapsed = time.time() - t0
    print()
    print(f"Done {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"OK: {len(docs)-errs} | Errors: {errs}")
    print(f"Total words: {total_words:,}")
    print(f"Total symbols: {total_symbols:,}")
    print(f"Coverage: {total_symbols/max(total_words,1)*100:.1f}%")
    print(f"Evidence cells: {store.count():,}")
    print(f"Evidence size: {store.health()['bin_size_kb']:.1f} KB")


if __name__ == "__main__":
    main()
