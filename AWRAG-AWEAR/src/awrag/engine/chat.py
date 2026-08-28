from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


def parse_chat_metadata_block(text: str) -> dict[str, Any]:
    metadata: dict[str, str] = {}
    wanted = {
        "CHAT_CONVERSATION_ID": "conversation_id",
        "CHAT_MESSAGE_ID": "message_id",
        "CHAT_TITLE": "title",
        "CHAT_CREATED_AT": "created_at_original",
        "CHAT_SPEAKER": "speaker",
        "CHAT_TRUTH_SCOPE": "truth_scope",
        "CHAT_LIFETIME_ALLOWED": "lifetime_allowed",
    }
    turn_match = re.search(r"^##\s+CHAT_TURN_([0-9]+)\s*$", text, flags=re.MULTILINE)
    if turn_match:
        metadata["turn_index"] = turn_match.group(1)
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        target = wanted.get(key)
        if target:
            metadata[target] = value.strip()
    if not metadata.get("conversation_id") and not metadata.get("message_id") and "turn_index" not in metadata:
        return {}
    created = metadata.get("created_at_original", "")
    parsed = parse_chat_datetime(created)
    if parsed:
        metadata["created_at"] = parsed.isoformat()
        metadata["date"] = parsed.date().isoformat()
        metadata["time"] = parsed.time().isoformat(timespec="seconds")
    speaker = metadata.get("speaker")
    if speaker:
        metadata["speaker"] = speaker.casefold()
    if "lifetime_allowed" in metadata:
        metadata["lifetime_allowed"] = metadata["lifetime_allowed"].casefold() == "true"
    if "turn_index" in metadata:
        metadata["turn_index"] = int(metadata["turn_index"])
    return metadata

def parse_chat_datetime(value: str) -> datetime | None:
    value = str(value or "").strip()
    if not value:
        return None
    formats = [
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def parse_filter_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parse_chat_datetime(value)
    if parsed:
        return parsed
    raise ValueError(f"invalid chat metadata date filter: {value!r}")

def build_metadata_filter(
    *,
    created_after: str | None,
    created_before: str | None,
    speaker: str | None,
) -> dict[str, Any]:
    after = parse_filter_date(created_after)
    before = parse_filter_date(created_before)
    normalized_speaker = speaker.casefold().strip() if speaker else None
    return {
        "schema": "awrag_query_metadata_filter@1",
        "active": bool(after or before or normalized_speaker),
        "created_after": after.isoformat() if after else None,
        "created_before": before.isoformat() if before else None,
        "speaker": normalized_speaker,
    }

def apply_block_metadata_filter(
    blocks: dict[int, dict[str, Any]],
    block_anchor_rows: list[tuple[bytes, int, int]],
    metadata_filter: dict[str, Any],
) -> tuple[dict[int, dict[str, Any]], list[tuple[bytes, int, int]]]:
    allowed: set[int] = set()
    after = parse_filter_date(metadata_filter.get("created_after"))
    before = parse_filter_date(metadata_filter.get("created_before"))
    speaker = metadata_filter.get("speaker")
    for ordinal, block in blocks.items():
        metadata = block.get("chat_metadata") or {}
        if not metadata:
            continue
        if speaker and str(metadata.get("speaker", "")).casefold() != speaker:
            continue
        created = parse_chat_datetime(str(metadata.get("created_at") or metadata.get("created_at_original") or ""))
        if after and (not created or created < after):
            continue
        if before and (not created or created > before):
            continue
        allowed.add(ordinal)
    filtered_blocks = {ordinal: block for ordinal, block in blocks.items() if ordinal in allowed}
    filtered_rows = [row for row in block_anchor_rows if row[1] in allowed]
    return filtered_blocks, filtered_rows

