"""Gutenberg Stream — automated ingest of Project Gutenberg texts into LakeSpeak.

Downloads plain-text books by ID, strips boilerplate header/footer,
ingests through the LakeSpeak pipeline with bridge anchors.

Usage:
    # Single book
    python scripts/gutenberg_stream.py 12345

    # Multiple books
    python scripts/gutenberg_stream.py 12345 67890 11111

    # From a topic batch file (one ID per line, # comments ok)
    python scripts/gutenberg_stream.py --batch scripts/gutenberg_clearboxry.txt

    # Dry run (download + strip, show stats, don't ingest)
    python scripts/gutenberg_stream.py --dry-run 12345

    # Skip reindex (useful when ingesting many books in sequence)
    python scripts/gutenberg_stream.py --no-reindex 12345 67890
    python scripts/gutenberg_stream.py --reindex   # standalone reindex after batch
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# ── Paths ────────────────────────────────────────────────────

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "plugins"))

MANIFEST_PATH = WORKSPACE_ROOT / "state" / "gutenberg_manifest.jsonl"

# ── Gutenberg URL Patterns ───────────────────────────────────

# Primary: UTF-8 plain text
_URL_PATTERNS = [
    "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt",
    "https://www.gutenberg.org/files/{id}/{id}-0.txt",
    "https://www.gutenberg.org/files/{id}/{id}.txt",
]

# ── Boilerplate Stripping ────────────────────────────────────

_START_RE = re.compile(
    r"\*\*\*\s*START OF (?:THE |THIS )?PROJECT GUTENBERG.*?\*\*\*",
    re.IGNORECASE,
)
_END_RE = re.compile(
    r"\*\*\*\s*END OF (?:THE |THIS )?PROJECT GUTENBERG.*?\*\*\*",
    re.IGNORECASE,
)


def strip_gutenberg_boilerplate(text: str) -> str:
    """Remove Project Gutenberg header and footer boilerplate.

    Finds the *** START OF ... *** and *** END OF ... *** markers
    and returns only the content between them.
    """
    # Find start marker — content begins AFTER this line
    start_match = _START_RE.search(text)
    if start_match:
        text = text[start_match.end():]

    # Find end marker — content ends BEFORE this line
    end_match = _END_RE.search(text)
    if end_match:
        text = text[:end_match.start()]

    # Strip leading/trailing whitespace
    return text.strip()


# ── Download ─────────────────────────────────────────────────

def fetch_gutenberg_text(book_id: int) -> Optional[str]:
    """Download plain text for a Gutenberg book ID.

    Tries multiple URL patterns in order.
    Returns stripped text or None on failure.
    """
    for pattern in _URL_PATTERNS:
        url = pattern.format(id=book_id)
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ClearboxAI-LakeSpeak/0.1 (research)"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                # Try UTF-8 first, fall back to Latin-1
                try:
                    text = raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1")

                if len(text) < 500:
                    continue  # Probably an error page

                return strip_gutenberg_boilerplate(text)

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            continue

    return None


# ── Manifest (dedup tracking) ────────────────────────────────

def _load_manifest() -> dict:
    """Load the manifest of previously ingested Gutenberg books."""
    manifest = {}
    if MANIFEST_PATH.exists():
        for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    manifest[entry["gutenberg_id"]] = entry
                except (json.JSONDecodeError, KeyError):
                    pass
    return manifest


def _append_manifest(entry: dict) -> None:
    """Append an entry to the manifest."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Ingest ───────────────────────────────────────────────────

def ingest_book(
    book_id: int,
    text: str,
    bridge,
    dry_run: bool = False,
) -> Optional[dict]:
    """Ingest a Gutenberg book into LakeSpeak.

    Returns the ingest receipt dict, or None on dry run.
    """
    if dry_run:
        words = len(text.split())
        chars = len(text)
        print(f"   [DRY RUN] {chars:,} chars, {words:,} words — would ingest")
        return None

    from lakespeak.ingest.pipeline import ingest_text

    receipt = ingest_text(
        text=text,
        source_type="url",
        source_path=f"gutenberg:{book_id}",
        bridge=bridge,
    )

    return receipt


# ── Bridge Loader ────────────────────────────────────────────

def _load_bridge():
    """Lazy-load the ClearboxLexiconBridge for anchor extraction."""
    try:
        from bridges.clearbox_bridge import ClearboxLexiconBridge
        bridge = ClearboxLexiconBridge()
        if hasattr(bridge, "word_index") and len(bridge.word_index) > 0:
            print(f"   Bridge loaded: {len(bridge.word_index):,} lexicon entries")
            return bridge
        else:
            print("   Bridge loaded but lexicon is empty — ingesting without anchors")
            return bridge
    except Exception as e:
        print(f"   Bridge not available ({e}) — ingesting without anchors")
        return None


# ── Reindex ──────────────────────────────────────────────────

def do_reindex():
    """Rebuild BM25 + dense indexes from all stored chunks."""
    print("\n   Reindexing...")
    try:
        from lakespeak.retrieval.query import LakeSpeakEngine
        engine = LakeSpeakEngine()
        stats = engine.reindex()
        print(f"   Reindex done: {stats.get('chunks_indexed', 0)} chunks, "
              f"{stats.get('receipts_processed', 0)} receipts")
        return stats
    except Exception as e:
        print(f"   Reindex failed: {e}")
        return None


# ── Batch File Loader ────────────────────────────────────────

def load_batch_file(path: str) -> List[int]:
    """Load book IDs from a batch file (one per line, # comments ok)."""
    ids = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Support "12345  # Some Book Title" format
            parts = line.split("#", 1)
            id_part = parts[0].strip()
            if id_part.isdigit():
                ids.append(int(id_part))
    return ids


# ── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ingest Project Gutenberg texts into LakeSpeak",
    )
    parser.add_argument(
        "book_ids", nargs="*", type=int,
        help="Gutenberg book IDs to ingest",
    )
    parser.add_argument(
        "--batch", type=str, default=None,
        help="Path to batch file with book IDs (one per line)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Download and strip only — don't ingest",
    )
    parser.add_argument(
        "--no-reindex", action="store_true",
        help="Skip reindex after ingest (useful for large batches)",
    )
    parser.add_argument(
        "--reindex", action="store_true",
        help="Only reindex (no download/ingest)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-ingest even if already in manifest",
    )
    parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Seconds between downloads (be polite to Gutenberg)",
    )

    args = parser.parse_args()

    # Standalone reindex
    if args.reindex:
        do_reindex()
        return

    # Collect book IDs
    book_ids: List[int] = list(args.book_ids or [])
    if args.batch:
        book_ids.extend(load_batch_file(args.batch))

    if not book_ids:
        parser.print_help()
        print("\nNo book IDs specified. Use positional args or --batch file.")
        return

    # Dedup input
    book_ids = list(dict.fromkeys(book_ids))

    manifest = _load_manifest()
    bridge = None if args.dry_run else _load_bridge()

    print(f"\n{'='*60}")
    print(f" Gutenberg Stream — {len(book_ids)} book(s) queued")
    print(f"{'='*60}\n")

    results = {"ingested": 0, "skipped": 0, "failed": 0, "dry_run": 0}

    for i, book_id in enumerate(book_ids):
        print(f"[{i+1}/{len(book_ids)}] Book #{book_id}")

        # Check manifest
        if book_id in manifest and not args.force:
            prev = manifest[book_id]
            print(f"   Already ingested (receipt: {prev.get('receipt_id', '?')}) — skipping")
            results["skipped"] += 1
            continue

        # Download
        print(f"   Downloading from Gutenberg...")
        text = fetch_gutenberg_text(book_id)

        if text is None:
            print(f"   FAILED — could not download book #{book_id}")
            results["failed"] += 1
            continue

        words = len(text.split())
        chars = len(text)
        print(f"   Downloaded: {chars:,} chars, {words:,} words")

        # Ingest
        receipt = ingest_book(book_id, text, bridge, dry_run=args.dry_run)

        if args.dry_run:
            results["dry_run"] += 1
        elif receipt:
            print(f"   Ingested: receipt={receipt['receipt_id']}, "
                  f"chunks={receipt['chunk_count']}, "
                  f"anchors={receipt['anchor_count']}")

            # Record in manifest
            _append_manifest({
                "gutenberg_id": book_id,
                "receipt_id": receipt["receipt_id"],
                "chunk_count": receipt["chunk_count"],
                "anchor_count": receipt["anchor_count"],
                "chars": chars,
                "words": words,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
            results["ingested"] += 1
        else:
            print(f"   FAILED — ingest returned no receipt")
            results["failed"] += 1

        # Rate limit
        if i < len(book_ids) - 1:
            time.sleep(args.delay)

    # Summary
    print(f"\n{'='*60}")
    print(f" Results: {results['ingested']} ingested, "
          f"{results['skipped']} skipped, "
          f"{results['failed']} failed"
          + (f", {results['dry_run']} dry-run" if results['dry_run'] else ""))
    print(f"{'='*60}")

    # Reindex
    if results["ingested"] > 0 and not args.no_reindex:
        do_reindex()
    elif results["ingested"] > 0 and args.no_reindex:
        print("\n   Skipped reindex (--no-reindex). Run: python scripts/gutenberg_stream.py --reindex")


if __name__ == "__main__":
    main()
