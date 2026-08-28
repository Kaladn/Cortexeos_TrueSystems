"""Tool execution telemetry — append-only JSONL following temporal doctrine.

Records every tool call with model, tool, verdict, latency, and temporal fields.
Used by the Control Panel dashboard for per-model success/fail/denied tracking.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from security.data_paths import AUDIT_DIR

TOOL_TELEMETRY_PATH = AUDIT_DIR / "tool_telemetry.jsonl"

# Temporal doctrine: boot_id + seq counter
_BOOT_ID = ""
_SEQ = 0


def _get_boot_id() -> str:
    global _BOOT_ID
    if not _BOOT_ID:
        import uuid
        _BOOT_ID = uuid.uuid4().hex[:12]
    return _BOOT_ID


def _next_seq() -> int:
    global _SEQ
    _SEQ += 1
    return _SEQ


def record_tool_call(
    model: str,
    tool: str,
    verdict: str,
    latency_ms: int,
    schema_ok: bool = True,
    trace_id: str | None = None,
) -> None:
    """Append one telemetry record. Never raises.

    verdict: "success" | "fail" | "denied"
    """
    entry = {
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") +
                  f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z",
        "mono_ns": time.monotonic_ns(),
        "boot_id": _get_boot_id(),
        "seq": _next_seq(),
        "model_id": model,
        "tool_id": tool,
        "verdict": verdict,
        "latency_ms": latency_ms,
        "schema_ok": schema_ok,
    }
    if trace_id:
        entry["trace_id"] = trace_id
    try:
        TOOL_TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOOL_TELEMETRY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def aggregate_stats(last_n: int = 500) -> dict:
    """Read last N lines from telemetry, return per-model-per-tool counts.

    Returns: {model_id: {tool_id: {calls, success, fail, denied, last_used}}}
    """
    stats: dict[str, dict[str, dict]] = {}
    try:
        if not TOOL_TELEMETRY_PATH.exists():
            return stats
        lines = TOOL_TELEMETRY_PATH.read_text(encoding="utf-8").splitlines()
        if len(lines) > last_n:
            lines = lines[-last_n:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                mid = rec.get("model_id", "unknown")
                tid = rec.get("tool_id", "unknown")
                verdict = rec.get("verdict", "fail")
                if mid not in stats:
                    stats[mid] = {}
                if tid not in stats[mid]:
                    stats[mid][tid] = {
                        "calls": 0, "success": 0, "fail": 0,
                        "denied": 0, "last_used": "",
                    }
                bucket = stats[mid][tid]
                bucket["calls"] += 1
                if verdict in ("success", "fail", "denied"):
                    bucket[verdict] += 1
                bucket["last_used"] = rec.get("ts_utc", "")
            except (json.JSONDecodeError, KeyError):
                continue
    except Exception:
        pass
    return stats


def tail_raw(lines: int = 100) -> list[dict]:
    """Return last N raw telemetry records as dicts."""
    result = []
    try:
        if not TOOL_TELEMETRY_PATH.exists():
            return result
        all_lines = TOOL_TELEMETRY_PATH.read_text(encoding="utf-8").splitlines()
        if len(all_lines) > lines:
            all_lines = all_lines[-lines:]
        for line in all_lines:
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    return result
