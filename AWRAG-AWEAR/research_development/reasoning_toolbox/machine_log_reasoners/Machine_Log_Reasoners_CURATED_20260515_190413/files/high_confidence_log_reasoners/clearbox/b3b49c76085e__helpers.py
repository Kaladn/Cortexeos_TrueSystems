"""Module-level helper functions — extracted from clearbox_bridge_server.py."""
from __future__ import annotations

import glob
import json
import logging
import os as _os
import re
import socket as _socket
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse as _urlparse

from fastapi import HTTPException

if __package__ is None or __package__ == "":
    BASE_DIR = Path(__file__).resolve().parent.parent
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

from security.data_paths import STATE_DIR

# Chat logging + history retrieval — bridge handles directly
from Conversations.threads.reader import load_recent_days as _load_recent_days
from Conversations.threads.history_retriever import build_history_context as _build_history_context

LOGGER = logging.getLogger("clearbox_bridge_server")

# ── Path traversal protection ────────────────────────────────────────────
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")

_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s]+|/(?:home|usr|tmp|var|etc|root|opt|mnt|Users)/[^\s]+")

def _safe_error(exc: Exception) -> str:
    """Sanitize exception messages for HTTP responses — strip filesystem paths."""
    msg = str(exc)
    return _PATH_RE.sub("<path>", msg)

def _validate_path_id(value: str, label: str = "ID") -> None:
    """Reject path-component values containing traversal sequences."""
    if not value or not _SAFE_ID_RE.match(value):
        raise HTTPException(400, f"Invalid {label}: must be alphanumeric/underscore/dot/hyphen")

def _validate_path_within(path: Path, base: Path, label: str = "path") -> Path:
    """Resolve *path* and verify it lives inside *base*. Returns resolved path."""
    resolved = path.resolve()
    base_resolved = base.resolve()
    if resolved != base_resolved and not str(resolved).startswith(str(base_resolved) + _os.sep):
        raise HTTPException(400, f"Invalid {label}: escapes allowed directory")
    return resolved

# ── SSRF protection ──────────────────────────────────────────────────────

_SSRF_BLOCKED_NETS = (
    "127.", "10.", "192.168.", "169.254.", "0.",
    "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
)

def _validate_url_ssrf(url: str) -> None:
    """Reject URLs targeting private/loopback/metadata addresses."""
    parsed = _urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, f"Blocked URL scheme: {parsed.scheme}")
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "::1", ""):
        raise HTTPException(400, f"Blocked URL host: {host}")
    try:
        ip = _socket.gethostbyname(host)
    except _socket.gaierror:
        raise HTTPException(400, f"DNS resolution failed for: {host}")
    if any(ip.startswith(net) for net in _SSRF_BLOCKED_NETS):
        raise HTTPException(400, f"Blocked URL: resolves to private address")

# Single source of truth for the fallback model name
DEFAULT_MODEL = "current model"


# ── Routing stubs (routing/ module removed) ─────────────────────
# RouteEngine was a telemetry/tracing object; these no-ops keep callers stable.

class RouteEngine:
    """No-op routing telemetry stub."""

    def __init__(self, profile: dict | None = None) -> None:
        self._profile = profile or {}

    def prepare(self, mode: str, message: str) -> dict:
        return {"mode": mode, "stages": []}

    def record(self, rctx: dict, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        pass

    def telemetry_block(self, rctx: dict) -> dict:
        return rctx


def load_routing_profile(raw: Any = None) -> dict:
    """Return a minimal routing profile dict (routing module removed)."""
    if isinstance(raw, dict):
        return raw
    return {"name": "default", "pipeline": []}


def validate_routing_profile(profile: dict) -> tuple[bool, str | None]:
    """Always valid — routing module removed."""
    return (True, None)


def list_named_profiles() -> list[str]:
    """No named profiles — routing module removed."""
    return []


def load_named_profile(name: str) -> dict | None:
    """No named profiles — routing module removed."""
    return None


def save_named_profile(name: str, profile: dict) -> tuple[bool, str | None]:
    """No-op — routing module removed."""
    return (True, None)


def _build_chat_messages(current_msg: str, max_turns: int = 20, branch: str = "main") -> list[dict]:
    """Build messages array from recent conversation history + current message.

    Memory layers injected as system messages (newest first):
      1. AI_BRIEF (pinned today) — session brief
      2. Latest daily summary — "story so far" from yesterday
      3. History retrieval (keyword BM25) — older relevant context
      4. Last 20 turns of raw conversation
      5. Current user message
    """
    history = _load_recent_days(days=3)
    target_branch = (branch or "main").strip() or "main"
    branch_msgs = [m for m in history if m.branch == target_branch]
    # Convert logged messages to role/content pairs
    msgs = []
    for m in branch_msgs:
        # Skip system-note entries that should not be replayed into model context.
        if getattr(m, "kind", None) in {"AI_BRIEF", "SIDE_CHAT_LINK"}:
            continue
        role = "user" if m.sender == "user" else "assistant"
        msgs.append({"role": role, "content": m.content})
    # Keep tail to avoid blowing context window
    if len(msgs) > max_turns:
        msgs = msgs[-max_turns:]

    # ── Memory layers injected before conversation (always present) ──

    # L2: AI_BRIEF (pinned today)
    _brief_digest = _get_todays_pinned_digest() or "AI_BRIEF: No pinned digest for today."
    msgs.insert(0, {"role": "system", "content": _brief_digest})

    # L2: Latest daily summary — gives model "what happened recently"
    _summary = _load_latest_summary() or "SESSION CONTEXT: No daily summary available yet."
    msgs.insert(0, {"role": "system", "content": _summary})

    # L2: History retrieval — keyword search for older relevant context
    _history_ctx = _retrieve_history_context(current_msg, branch=target_branch) or "HISTORY CONTEXT: No relevant prior conversation found."
    msgs.insert(0, {"role": "system", "content": _history_ctx})

    # L3: Lessons learned — decisions, corrections, facts from recent sessions
    _lessons = _load_lessons() or "LESSONS LEARNED: No lessons recorded yet. Lessons are extracted from daily debriefs."
    msgs.insert(0, {"role": "system", "content": _lessons})

    # L4: Reasoning trace — recent tool calls and chain activity
    _reasoning = _load_reasoning_trace() or "REASONING TRACE: No recent tool calls or chain activity recorded yet."
    msgs.insert(0, {"role": "system", "content": _reasoning})

    # Append current user message
    msgs.append({"role": "user", "content": current_msg})
    return msgs


def _load_latest_summary() -> str | None:
    """Load the most recent daily summary as context for the model."""
    try:
        from Conversations.threads.summarizer import get_latest_summary
        result = get_latest_summary()
        if result:
            date_str, text = result
            return f"SESSION CONTEXT (summary from {date_str}):\n{text}"
    except Exception:
        pass
    return None


def _retrieve_history_context(query: str, branch: str = "main") -> str | None:
    """Retrieve relevant older conversation context via keyword search.

    Only fires for substantive queries (>= 2 tokens).
    Returns None if no relevant hits found.
    """
    try:
        result = _build_history_context(
            query,
            max_chars=6000,
            per_hit_chars=600,
            max_hits=8,
            branch=branch,
            days_limit=30,
        )
        if result and isinstance(result, str) and len(result) > 50:
            return result
    except Exception:
        pass
    return None


def _load_lessons() -> str | None:
    """L3: Load recent lessons learned for LLM context injection."""
    try:
        from Conversations.threads.lessons import load_recent_lessons
        return load_recent_lessons(days=7)
    except Exception:
        return None


def _load_reasoning_trace() -> str | None:
    """L4: Load recent reasoning traces (tool calls, chain activity)."""
    try:
        from Conversations.threads.reasoning_log import load_recent_reasoning
        return load_recent_reasoning(days=3)
    except Exception:
        return None


def build_slot_memory_context() -> str:
    """Build compact memory context for chain slot injection.

    Lighter than hub context: latest daily summary + lessons only.
    No history retrieval, no reasoning trace, no AI_BRIEF.
    Always returns a string (placeholder if nothing available).
    """
    parts = []
    summary = _load_latest_summary()
    if summary:
        parts.append(summary)
    lessons = _load_lessons()
    if lessons:
        parts.append(lessons)
    if not parts:
        return "SESSION MEMORY: No summaries or lessons available yet."
    return "\n\n".join(parts)


def _get_todays_pinned_digest() -> str | None:
    """Return the pinned AI_BRIEF digest content for today, or None."""
    try:
        from Conversations.threads.daily_logger import get_today_file
        from security.secure_storage import secure_read_lines
        today_file = get_today_file()
        if not today_file.exists():
            return None
        for line in secure_read_lines(today_file):
            try:
                obj = json.loads(line)
                if obj.get("kind") == "AI_BRIEF":
                    return obj.get("content")
            except (json.JSONDecodeError, AttributeError):
                continue
    except Exception:
        pass
    return None


def _merge_consecutive_roles(messages: list[dict]) -> list[dict]:
    """Merge consecutive same-role messages for APIs that require alternation.

    Used by Claude mode only. Merges content with double-newline separator.
    Does NOT drop messages — information is preserved.
    """
    if not messages:
        return messages
    out = [messages[0].copy()]
    for m in messages[1:]:
        if m.get("role") == out[-1].get("role"):
            out[-1]["content"] = f'{out[-1].get("content", "")}\n\n{m.get("content", "")}'.strip()
        else:
            out.append(m.copy())
    return out

def _parse_tool_request(text: str) -> list[dict] | None:
    """Parse structured tool_request JSON from a slot response.

    Expected format (anywhere in text):
        {"type": "tool_request", "requests": [{"name": "...", "arguments": {}, "reason": "..."}]}

    Returns list of request dicts, or None if not found.
    """
    import json as _json
    import re as _re

    # Look for JSON object with type: tool_request
    for match in _re.finditer(r'\{[^{}]*"type"\s*:\s*"tool_request"[^{}]*"requests"\s*:\s*\[.*?\]\s*\}', text, _re.DOTALL):
        try:
            parsed = _json.loads(match.group())
            if parsed.get("type") == "tool_request" and isinstance(parsed.get("requests"), list):
                reqs = []
                for r in parsed["requests"]:
                    if isinstance(r, dict) and "name" in r:
                        reqs.append({
                            "name": r["name"],
                            "arguments": r.get("arguments", {}),
                            "reason": r.get("reason", ""),
                        })
                return reqs if reqs else None
        except (_json.JSONDecodeError, TypeError):
            continue
    return None


def _normalise_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        return (BASE_DIR / path).resolve()
    return path.resolve()


# ── DocuMap Job Ledger ────────────────────────────────────────
_DOCUMAP_LEDGER = STATE_DIR / "documap_jobs.jsonl"


def _read_documap_ledger() -> dict:
    """Read documap job ledger, return last event per fingerprint."""
    events: Dict[str, dict] = {}
    if not _DOCUMAP_LEDGER.exists():
        return events
    try:
        with open(_DOCUMAP_LEDGER, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                evt = json.loads(line)
                fp = evt.get("fingerprint")
                if fp:
                    events[fp] = evt
    except Exception as e:
        LOGGER.warning("Could not read documap ledger: %s", e)
    return events


def _append_documap_event(event: dict) -> None:
    """Append an event to the documap job ledger."""
    _DOCUMAP_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(_DOCUMAP_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _mapped_fingerprints() -> set:
    """Return set of fingerprints with last event == 'completed'."""
    ledger = _read_documap_ledger()
    return {fp for fp, evt in ledger.items() if evt.get("event") == "completed"}


def _parse_patterns(pattern: Optional[str]) -> List[str]:
    if not pattern:
        return ["*"]
    parts = [part.strip() for part in re.split(r"[;,]", pattern) if part.strip()]
    return parts or ["*"]


def _iter_directory(path: Path, recursive: bool, patterns: List[str]) -> Iterable[Path]:
    for pattern in patterns:
        iterator = path.rglob(pattern) if recursive else path.glob(pattern)
        for candidate in iterator:
            if candidate.is_file():
                yield candidate.resolve()


def resolve_job_inputs(paths: List[str], recursive: bool, pattern: Optional[str]) -> Tuple[List[Path], List[str]]:
    patterns = _parse_patterns(pattern)
    resolved: List[Path] = []
    missing: List[str] = []
    seen: Set[Path] = set()

    for raw in paths:
        raw_clean = raw.strip()
        if not raw_clean:
            continue

        if any(ch in raw_clean for ch in "*?["):
            pattern_path = Path(raw_clean).expanduser()
            if not pattern_path.is_absolute():
                pattern_path = BASE_DIR / pattern_path
            matches = [Path(match).resolve() for match in glob.glob(str(pattern_path), recursive=True)]
            files = [candidate for candidate in matches if candidate.is_file()]
            if files:
                for candidate in files:
                    if candidate not in seen:
                        seen.add(candidate)
                        resolved.append(candidate)
            else:
                missing.append(raw_clean)
            continue

        normalised = _normalise_path(raw_clean)

        if normalised.is_dir():
            files = list(_iter_directory(normalised, recursive, patterns))
            if files:
                for candidate in files:
                    if candidate not in seen:
                        seen.add(candidate)
                        resolved.append(candidate)
            else:
                missing.append(raw_clean)
            continue

        if normalised.is_file():
            if normalised not in seen:
                seen.add(normalised)
                resolved.append(normalised)
            continue

        missing.append(raw_clean)

    return resolved, missing
