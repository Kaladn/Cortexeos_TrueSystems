"""Daily chat ingestion — 616 map + LakeSpeak data lake.

Reads a day's JSONL chat log, extracts all message content,
runs it through the 616 mapping pipeline, stores the map in
citations.db, and ingests the text into LakeSpeak for grounded search.

Designed to run from:
  1. Auto-rollup trigger (daily_logger._fire_auto_summary)
  2. Manual endpoint (POST /api/memory/rollup or /api/memory/bootstrap)

Requires a bridge instance (ClearboxLexiconBridge) for map_text().
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Secure data paths
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from security.data_paths import CHAT_THREADS_DIR
from security.secure_storage import secure_read_lines


def _load_day_text(target_date: str) -> str:
    """Load all messages from a day's JSONL and return as plain text.

    Each message is prefixed with [USER] or [AI] for context.
    Returns empty string if no file or no messages.
    """
    thread_path = CHAT_THREADS_DIR / f"{target_date}.jsonl"
    if not thread_path.exists():
        logger.info("No chat file for %s", target_date)
        return ""

    parts = []
    lines = secure_read_lines(thread_path)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            sender = (obj.get("sender") or "unknown").upper()
            content = (obj.get("content") or "").strip()
            if content:
                parts.append(f"[{sender}] {content}")
        except json.JSONDecodeError:
            continue

    return "\n\n".join(parts)


def ingest_chat_day(
    target_date: str,
    bridge: Any,
    *,
    skip_if_exists: bool = True,
) -> Dict[str, Any]:
    """Run 616 mapping + LakeSpeak ingest for a day's chat log.

    Args:
        target_date: YYYY-MM-DD date string
        bridge: ClearboxLexiconBridge instance (for map_text + write_report)
        skip_if_exists: If True, skip if citation already exists for this date

    Returns:
        Dict with results: {ok, date, chars, cite_id, map_id, grove_receipt, ...}
    """
    from Conversations.threads.map_manager import map_manager

    text = _load_day_text(target_date)
    if not text:
        return {"ok": False, "date": target_date, "reason": "no_chat_data"}

    filename = f"chat_{target_date}.jsonl"
    result: Dict[str, Any] = {
        "ok": False,
        "date": target_date,
        "chars": len(text),
    }

    # ── Step 1: Create citation (idempotent by content hash) ──
    try:
        citation = map_manager.create_citation(
            content=text,
            filename=filename,
            source_type="system",
            source_metadata={"type": "daily_chat", "date": target_date},
            subject=f"Chat log {target_date}",
            note=f"Auto-ingested daily chat transcript for {target_date}",
        )
        result["cite_id"] = citation.cite_id
    except Exception as e:
        logger.warning("Chat ingest citation failed for %s: %s", target_date, e)
        result["error"] = f"citation: {e}"
        return result

    # ── Step 2: 616 map via bridge ──
    try:
        # Check if map already exists
        existing_map = map_manager.get_existing_map(citation.cite_id)
        if existing_map and skip_if_exists:
            result["map_id"] = existing_map.map_id
            result["map_skipped"] = True
            logger.info("Chat map already exists for %s: %s", target_date, existing_map.map_id)
        else:
            map_data = bridge.map_text(text, source=f"chat_{target_date}", device="cpu")
            map_record = map_manager.create_map(
                cite_id=citation.cite_id,
                map_data=map_data,
                force=not skip_if_exists,
            )
            result["map_id"] = map_record.map_id
            result["total_tokens"] = map_record.total_tokens
            result["unique_anchors"] = map_record.unique_anchors
            logger.info("Chat 616 map created for %s: %s (%d anchors)",
                        target_date, map_record.map_id, map_record.unique_anchors)
    except Exception as e:
        logger.warning("Chat ingest 616 map failed for %s: %s", target_date, e)
        result["map_error"] = str(e)

    # ── Step 3: LakeSpeak ingest ──
    try:
        from plugins.lakespeak.ingest.pipeline import ingest_text

        grove_receipt = ingest_text(
            text=text,
            source_type="daily_chat",
            source_path=f"chat/{target_date}",
            bridge=bridge,
            skip_mapped_guard=True,  # Chat text hasn't been through DocuMap commit
        )
        result["grove_receipt"] = grove_receipt.get("receipt_id")
        result["grove_chunks"] = grove_receipt.get("chunk_count", 0)
        logger.info("Chat LakeSpeak ingest for %s: %s (%d chunks)",
                    target_date, grove_receipt.get("receipt_id", "?"),
                    grove_receipt.get("chunk_count", 0))
    except Exception as e:
        logger.warning("Chat LakeSpeak ingest failed for %s: %s", target_date, e)
        result["grove_error"] = str(e)

    result["ok"] = True
    return result


def ingest_chat_range(
    start_date: str,
    end_date: str,
    bridge: Any,
    *,
    skip_if_exists: bool = True,
) -> list[Dict[str, Any]]:
    """Ingest chat logs for a date range.

    Args:
        start_date: YYYY-MM-DD inclusive start
        end_date: YYYY-MM-DD inclusive end
        bridge: ClearboxLexiconBridge instance

    Returns:
        List of per-day result dicts.
    """
    from datetime import date, timedelta

    results = []
    current = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    while current <= end:
        ds = current.isoformat()
        try:
            r = ingest_chat_day(ds, bridge, skip_if_exists=skip_if_exists)
            results.append(r)
        except Exception as e:
            logger.warning("Chat ingest failed for %s: %s", ds, e)
            results.append({"ok": False, "date": ds, "error": str(e)})
        current += timedelta(days=1)

    return results
