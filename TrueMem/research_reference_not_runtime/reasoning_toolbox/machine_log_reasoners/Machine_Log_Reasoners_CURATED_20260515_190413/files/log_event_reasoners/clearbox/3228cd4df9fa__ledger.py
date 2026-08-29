"""Append-only tool-creation lake writes."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from security.data_paths import (
    TOOL_CREATION_LEDGER_DIR,
    TOOL_CREATION_SESSIONS_DIR,
    TOOL_CREATION_TESTS_DIR,
    TOOL_CREATION_TOOLS_DIR,
)

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date_key(timestamp: str) -> str:
    return (timestamp or _iso_now())[:10]


def _stamp_key(timestamp: str) -> str:
    return (timestamp or _iso_now()).replace(":", "").replace("-", "").replace(".", "")


def _safe_name(value: str, fallback: str = "unknown") -> str:
    clean = _SAFE_NAME_RE.sub("_", (value or "").strip()).strip("._")
    return clean or fallback


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")


def _append_ledger(event_type: str, payload: dict[str, Any], observed_at_utc: str) -> dict[str, Any]:
    event = {
        "event_type": event_type,
        "observed_at_utc": observed_at_utc,
        **payload,
    }
    _append_jsonl(TOOL_CREATION_LEDGER_DIR / f"{_date_key(observed_at_utc)}.jsonl", event)
    return event


def record_factory_turn(
    *,
    session_id: str,
    side_chat_id: str | None,
    provider: str,
    model: str | None,
    user_message: str,
    response_text: str,
    error_text: str | None = None,
    reasoning_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observed_at_utc = _iso_now()
    thread_id = _safe_name(side_chat_id or session_id or "tool_factory", "tool_factory")
    payload = {
        "session_id": session_id,
        "side_chat_id": side_chat_id,
        "provider": provider,
        "model": model,
        "user_message": user_message,
        "response_text": response_text,
        "error_text": error_text,
        "reasoning_trace": reasoning_trace or {},
    }
    event = _append_ledger("factory_turn", payload, observed_at_utc)
    _append_jsonl(TOOL_CREATION_SESSIONS_DIR / f"{thread_id}.jsonl", event)
    return event


def record_tool_definition_event(
    *,
    action: str,
    tool_name: str,
    tool_data: dict[str, Any] | None,
    actor: str = "human",
    source: str = "tool_workshop",
) -> dict[str, Any]:
    observed_at_utc = _iso_now()
    safe_tool = _safe_name(tool_name)
    payload = {
        "action": action,
        "tool_name": tool_name,
        "actor": actor,
        "source": source,
        "tool_data": tool_data or {},
    }
    event = _append_ledger("tool_definition", payload, observed_at_utc)
    snapshot = {
        "observed_at_utc": observed_at_utc,
        "action": action,
        "tool_name": tool_name,
        "actor": actor,
        "source": source,
        "tool_data": tool_data or {},
    }
    _write_json(
        TOOL_CREATION_TOOLS_DIR / safe_tool / f"{_stamp_key(observed_at_utc)}_{_safe_name(action)}.json",
        snapshot,
    )
    return event


def record_tool_test_run(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    result: str,
    actor: str = "human",
    source: str = "tool_workshop",
    session_id: str | None = None,
) -> dict[str, Any]:
    observed_at_utc = _iso_now()
    safe_tool = _safe_name(tool_name)
    payload = {
        "tool_name": tool_name,
        "actor": actor,
        "source": source,
        "session_id": session_id,
        "arguments": arguments,
        "result": result,
    }
    event = _append_ledger("tool_test", payload, observed_at_utc)
    _append_jsonl(TOOL_CREATION_TESTS_DIR / f"{safe_tool}.jsonl", event)
    return event
