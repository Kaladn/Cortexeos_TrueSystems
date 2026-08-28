from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .anchors import anchorize
from .base import sha1_text, with_protected_notice, write_json


def default_chat_count_root(*, runtime_root: str | Path | None = None, repo_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve() / "speech_fields" / "operator_chat"
    base = Path(repo_root).expanduser().resolve() if repo_root is not None else Path.cwd().resolve()
    return base / "runtime" / "speech_fields" / "operator_chat"


def append_chat_count(
    chat_count_root: str | Path,
    text: str,
    *,
    source: str = "operator_chat",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Append one normal chat input into the daily operator chat count field."""

    value = str(text or "")
    if not value.strip():
        return with_protected_notice({
            "schema": "awrag_operator_chat_count_append@1",
            "appended": False,
            "reason": "empty_chat_input",
            "no_dataset_qa_ledger_write": True,
        })
    current = now.astimezone() if now is not None and now.tzinfo is not None else (now or datetime.now().astimezone())
    day = current.date().isoformat()
    root = Path(chat_count_root).expanduser().resolve()
    day_root = root / "daily" / day
    day_root.mkdir(parents=True, exist_ok=True)

    events_path = day_root / "chat_events.jsonl"
    counts_path = day_root / "anchor_counts.json"
    manifest_path = day_root / "manifest.json"

    anchors = anchorize(value)
    event_count = _jsonl_count(events_path) + 1
    record_id = f"CHAT-{sha1_text(f'{current.isoformat()}|{value}')[:16]}"
    event = with_protected_notice({
        "schema": "awrag_operator_chat_event@1",
        "record_id": record_id,
        "timestamp": current.isoformat(),
        "chat_day": day,
        "source": source,
        "text": value,
        "text_hash": sha1_text(value),
        "anchors": anchors,
        "anchor_count": len(anchors),
        "dataset_qa_ledger_write": False,
        "dataset_id": None,
    })
    with events_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")

    counts = Counter(_read_counts(counts_path))
    counts.update(anchors)
    write_json(counts_path, {
        "schema": "awrag_operator_chat_anchor_counts@1",
        "chat_day": day,
        "source": source,
        "event_count": event_count,
        "unique_anchor_count": len(counts),
        "total_anchor_observations": sum(counts.values()),
        "anchors": dict(sorted(counts.items())),
        "dataset_qa_ledger_write": False,
    })
    write_json(manifest_path, {
        "schema": "awrag_operator_chat_daily_manifest@1",
        "chat_day": day,
        "chat_count_root": str(root),
        "daily_root": str(day_root),
        "events_path": str(events_path),
        "anchor_counts_path": str(counts_path),
        "event_count": event_count,
        "unique_anchor_count": len(counts),
        "total_anchor_observations": sum(counts.values()),
        "midnight_rollover": "local_date_directory",
        "dataset_qa_ledger_write": False,
    })
    return with_protected_notice({
        "schema": "awrag_operator_chat_count_append@1",
        "appended": True,
        "record_id": record_id,
        "chat_day": day,
        "chat_count_root": str(root),
        "daily_root": str(day_root),
        "events_path": str(events_path),
        "anchor_counts_path": str(counts_path),
        "manifest_path": str(manifest_path),
        "anchor_count": len(anchors),
        "unique_anchor_count": len(counts),
        "event_count": event_count,
        "no_dataset_qa_ledger_write": True,
    })


def _read_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    anchors = payload.get("anchors") if isinstance(payload, dict) else {}
    if not isinstance(anchors, dict):
        return {}
    return {str(key): int(value) for key, value in anchors.items()}


def _jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
