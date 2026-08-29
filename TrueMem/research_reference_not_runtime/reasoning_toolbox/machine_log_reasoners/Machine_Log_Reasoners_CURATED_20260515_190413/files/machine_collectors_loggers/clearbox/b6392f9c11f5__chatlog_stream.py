#!/usr/bin/env python3
"""ChatLog Stream — ingest Clearbox chat JSONL threads into LakeSpeak chats index.

One receipt per day (batch). Uses the LakeSpeak chunker for splitting.
Stores chunks + BM25 index under LAKESPEAK_CHATS_DIR (separate from docs).
Watermark tracks last-ingested line count per day.

Usage:
    python scripts/chatlog_stream.py              # ingest all new messages
    python scripts/chatlog_stream.py --days 7     # only last N days
    python scripts/chatlog_stream.py --dry-run    # preview, no writes
    python scripts/chatlog_stream.py --rebuild    # reset watermark, re-ingest all
    python scripts/chatlog_stream.py --include-ai # also ingest assistant messages
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "plugins"))

from security.data_paths import CHAT_THREADS_DIR, STATE_DIR, LAKESPEAK_CHATS_DIR
from security.secure_storage import secure_read_lines

MANIFEST_PATH = STATE_DIR / "chatlog_stream_manifest.jsonl"
MAX_MSG_CHARS  = 2000
SKIP_KINDS     = {"debrief", "AI_BRIEF", "SIDE_CHAT_LINK"}


# ── Watermark ─────────────────────────────────────────────────

def _load_watermark() -> dict[str, int]:
    """Returns {day_str: lines_ingested}."""
    if not MANIFEST_PATH.exists():
        return {}
    wm: dict[str, int] = {}
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            if rec.get("event") == "ingested":
                wm[rec["day"]] = max(wm.get(rec["day"], 0), rec["last_line"])
        except Exception:
            continue
    return wm


def _save_watermark(day: str, last_line: int, count: int, receipt_id: str) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "event": "ingested", "day": day,
        "last_line": last_line, "count": count,
        "receipt_id": receipt_id,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


# ── Day batch builder ─────────────────────────────────────────

def _build_batch_text(day: str, lines: list[str], include_ai: bool) -> tuple[str, int]:
    """Build a single text block from qualifying messages with coord markers.

    Each message gets a separator line for traceability:
        --- CHAT:YYYY-MM-DD:L{msg_id} [{sender}] ---
    """
    parts: list[str] = []
    count = 0

    for i, raw in enumerate(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue

        sender  = msg.get("sender", "")
        content = msg.get("content", "")
        kind    = msg.get("kind")
        msg_id  = msg.get("id", i + 1)

        if not content or not content.strip():
            continue
        if kind in SKIP_KINDS:
            continue
        if sender == "ai" and not include_ai:
            continue
        if len(content) > MAX_MSG_CHARS:
            continue

        parts.append(f"--- CHAT:{day}:L{msg_id} [{sender}] ---\n{content.strip()}")
        count += 1

    return "\n\n".join(parts), count


# ── Per-day ingest ────────────────────────────────────────────

def ingest_day(day: str, from_line: int, include_ai: bool, dry_run: bool) -> int:
    """Ingest new messages from one day as a single batch into LAKESPEAK_CHATS_DIR."""
    from core.lakespeak.ingest.chunker import chunk_text
    from core.lakespeak.ingest.receipt import make_receipt_id, source_hash
    from core.lakespeak.index.bm25 import BM25Index

    path = CHAT_THREADS_DIR / f"{day}.jsonl"
    if not path.exists():
        return 0

    all_lines = secure_read_lines(path)
    new_lines = all_lines[from_line:]
    if not new_lines:
        return 0

    batch_text, count = _build_batch_text(day, new_lines, include_ai)
    if not batch_text:
        return 0

    if dry_run:
        print(f"  [DRY] {day}: {count} messages, {len(batch_text)} chars → 1 receipt")
        return count

    # Generate receipt
    receipt_id = make_receipt_id()
    src_hash = source_hash(batch_text)

    # Chunk
    chunks = chunk_text(
        text=batch_text,
        receipt_id=receipt_id,
        source_hash=src_hash,
        chunk_size=512,
        chunk_overlap=0,
    )

    if not chunks:
        print(f"  {day}: no chunks produced")
        return 0

    # Store chunks under LAKESPEAK_CHATS_DIR/{receipt_id}/chunks.jsonl
    receipt_dir = LAKESPEAK_CHATS_DIR / receipt_id
    receipt_dir.mkdir(parents=True, exist_ok=True)
    chunks_file = receipt_dir / "chunks.jsonl"

    with open(chunks_file, "w", encoding="utf-8") as f:
        for chunk in chunks:
            rec = {
                "chunk_id": chunk.chunk_id,
                "receipt_id": chunk.receipt_id,
                "ordinal": chunk.ordinal,
                "source_hash": chunk.source_hash,
                "span_start": chunk.span_start,
                "span_end": chunk.span_end,
                "text_hash": chunk.text_hash,
                "token_count": chunk.token_count,
                "text": chunk.text,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Store receipt metadata
    receipt_meta = {
        "receipt_id": receipt_id,
        "source_type": "chat_export",
        "source_path": f"chat:{day}",
        "source_hash": src_hash,
        "chunk_count": len(chunks),
        "day": day,
        "message_count": count,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open(receipt_dir / "receipt.json", "w", encoding="utf-8") as f:
        json.dump(receipt_meta, f, ensure_ascii=False, indent=2)

    # Update BM25 index (chat-scoped)
    bm25_dir = LAKESPEAK_CHATS_DIR / "bm25"
    bm25 = BM25Index(index_dir=bm25_dir)

    chunk_texts = [c.text for c in chunks]
    chunk_ids = [c.chunk_id for c in chunks]
    receipt_ids = [c.receipt_id for c in chunks]

    if bm25._ensure_loaded():
        bm25.add_chunks(chunk_texts, chunk_ids, receipt_ids)
    else:
        bm25.build(chunk_texts, chunk_ids, receipt_ids)
    bm25.save()

    # Save watermark
    _save_watermark(day, from_line + len(new_lines), count, receipt_id)

    print(f"  {day}: {count} messages → {len(chunks)} chunks (receipt {receipt_id[:20]}...)")
    return count


# ── Entry point ───────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest chat logs into LakeSpeak chats index")
    parser.add_argument("--days",       type=int, default=0,
                        help="Only process last N days (0 = all)")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--rebuild",    action="store_true",
                        help="Reset watermark and re-ingest everything")
    parser.add_argument("--include-ai", action="store_true",
                        help="Also ingest assistant messages (default: user only)")
    args = parser.parse_args()

    watermark = {} if args.rebuild else _load_watermark()

    day_files = sorted(CHAT_THREADS_DIR.glob("*.jsonl"))
    if args.days > 0:
        day_files = day_files[-args.days:]

    total = 0
    for path in day_files:
        day = path.stem
        from_line = watermark.get(day, 0)
        count = ingest_day(day, from_line, args.include_ai, args.dry_run)
        if count:
            total += count

    print(f"\nTotal ingested: {total}")


if __name__ == "__main__":
    main()
