"""L4 — Reasoning trace persistence and retrieval.

Captures tool calls, chain contributions, and multi-step reasoning
artifacts from LLM and chain executor responses. Stored as append-only
JSONL in CHAT_MEMORY_DIR/reasoning/{YYYY-MM-DD}.jsonl.

Each record: {
    "ts": ISO timestamp,
    "mode": "llm" | "multi_llm",
    "model": "model_name",
    "type": "tool_call" | "chain_contribution" | "grounded_retrieval",
    "summary": "one-line description",
    "detail": { ... provider-specific payload ... }
}

Retrieval: load_recent_reasoning(days=3) returns formatted context block.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

import os as _os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security.data_paths import CHAT_MEMORY_DIR

REASONING_DIR = CHAT_MEMORY_DIR / "reasoning"

# ── Governed I/O ──────────────────────────────────────────────
try:
    from security.gateway import WriteZone, gateway as _gw
    _GOVERNED = True
except ImportError:
    _GOVERNED = False

ALLOW_LEGACY_WRITES = _os.environ.get("ALLOW_LEGACY_WRITES", "false").lower() in ("true", "1", "yes")


def _ensure_dir() -> None:
    REASONING_DIR.mkdir(parents=True, exist_ok=True)


def log_tool_call(
    model: str,
    tool_name: str,
    tool_args: dict,
    result_preview: str,
    ms: int,
) -> None:
    """Persist a tool call from LLM mode."""
    _append_record({
        "type": "tool_call",
        "mode": "llm",
        "model": model,
        "summary": f"Called {tool_name}({', '.join(f'{k}={v!r}' for k, v in (tool_args or {}).items())})",
        "detail": {
            "tool": tool_name,
            "args": tool_args,
            "result_preview": result_preview[:300],
            "ms": ms,
        },
    })


def log_chain_contribution(
    slot_id: int,
    provider: str,
    model: str,
    content_preview: str,
    ms: int,
) -> None:
    """Persist a chain slot contribution from multi_llm mode."""
    _append_record({
        "type": "chain_contribution",
        "mode": "multi_llm",
        "model": model,
        "summary": f"Slot {slot_id} ({provider}/{model}): {content_preview[:120]}",
        "detail": {
            "slot_id": slot_id,
            "provider": provider,
            "content_preview": content_preview[:500],
            "ms": ms,
        },
    })


def log_grounded_retrieval(
    model: str,
    query: str,
    citation_count: int,
    verdict: str,
) -> None:
    """Persist a grounded retrieval event."""
    _append_record({
        "type": "grounded_retrieval",
        "mode": "grounded",
        "model": model,
        "summary": f"Grounded query: {query[:80]}... → {citation_count} citations ({verdict})",
        "detail": {
            "query_preview": query[:200],
            "citation_count": citation_count,
            "verdict": verdict,
        },
    })


def _append_record(record: dict[str, Any]) -> None:
    """Append a reasoning record to today's JSONL file."""
    try:
        record["ts"] = datetime.now(timezone.utc).isoformat()
        today = date.today().isoformat()
        filename = f"{today}.jsonl"
        line = json.dumps(record, ensure_ascii=False)

        if _GOVERNED:
            rel = str(Path("reasoning") / filename)
            result = _gw.append("system", WriteZone.CHAT_MEMORY, rel, line, encrypt=False)
            if not result.success:
                logger.warning("Reasoning log gateway append failed: %s", result.error)
        else:
            if not ALLOW_LEGACY_WRITES:
                logger.debug("Reasoning log: legacy writes disabled, skipping")
                return
            _ensure_dir()
            path = REASONING_DIR / filename
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:
        logger.warning("Reasoning log write failed: %s", e)


def _load_day_records(target_date: str) -> list[dict]:
    """Load reasoning records for a specific date."""
    path = REASONING_DIR / f"{target_date}.jsonl"
    if not path.exists():
        return []
    records = []
    try:
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                records.append(json.loads(line))
    except Exception:
        pass
    return records


def load_recent_reasoning(days: int = 3) -> str | None:
    """Load reasoning traces from last N days, formatted for LLM context.

    Returns a formatted string block or None if no traces found.
    Keeps it compact — only summaries, not full details.
    """
    today = date.today()
    summaries: list[str] = []

    for i in range(days):
        day = (today - timedelta(days=i)).isoformat()
        for r in _load_day_records(day):
            summaries.append(f"  [{r.get('ts', day)[:16]}] {r.get('summary', '')}")

    if not summaries:
        return None

    # Cap at 20 most recent to avoid bloat
    summaries = summaries[:20]

    return "REASONING TRACE (recent tool calls and chain activity):\n" + "\n".join(summaries)
