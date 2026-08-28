"""Daily logger - Append to today's JSONL file.

Design principles:
- One file per day (YYYY-MM-DD.jsonl)
- Append-only within the day
- Sequential message IDs (1, 2, 3...)
- Full SHA-256 integrity hashing + legacy 16-char short hash
- UUID global identity per message (absorbed from memory/ system)
- Service day cutoff warnings
"""

import json
import hashlib
import logging
import threading
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Literal, Dict, Any
from .models import Message, ModelIdentity, Seat, ActorType

logger = logging.getLogger(__name__)

# Storage location — secure user-scoped directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security.data_paths import CHAT_THREADS_DIR
from security.secure_storage import (
    secure_read_lines, secure_append_line, secure_read_text,
    secure_count_lines,
)

# ── Governed I/O: route writes through the gateway ────────────
try:
    from security.gateway import WriteZone, gateway as _gw
    _GOVERNED = True
except ImportError:
    _GOVERNED = False

import os as _os
ALLOW_LEGACY_WRITES = _os.environ.get("ALLOW_LEGACY_WRITES", "false").lower() in ("true", "1", "yes")

THREADS_ROOT = CHAT_THREADS_DIR
THREADS_ROOT.mkdir(parents=True, exist_ok=True)

# Serialize read-ID → build-message → append-to-file to prevent duplicate IDs
_log_lock = threading.Lock()

# Service day cutoff configuration
SERVICE_DAY_END_HOUR = 23  # 11 PM local time
CUTOFF_WARNING_MINUTES = 30  # Warn 30 minutes before


def get_today_file() -> Path:
    """Get today's JSONL file path.
    
    Returns:
        Path like conversations/threads/2026-02-07.jsonl
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return THREADS_ROOT / f"{today}.jsonl"


def is_near_cutoff(minutes_before: int = CUTOFF_WARNING_MINUTES) -> bool:
    """Check if we're within X minutes of service day end.
    
    Args:
        minutes_before: Warning threshold in minutes
        
    Returns:
        True if within warning window
    """
    now = datetime.now()
    cutoff = now.replace(hour=SERVICE_DAY_END_HOUR, minute=0, second=0, microsecond=0)
    
    # Handle after-midnight case
    if now.hour < SERVICE_DAY_END_HOUR:
        # We're in the next day already, not near cutoff
        return False
    
    minutes_until = (cutoff - now).total_seconds() / 60
    return 0 < minutes_until <= minutes_before


def get_next_message_id() -> int:
    """Get next sequential ID for today.
    
    Returns:
        Next message ID (1 if file doesn't exist)
    """
    today_file = get_today_file()
    
    if not today_file.exists():
        return 1
    
    # Read last line to get last ID
    try:
        lines = secure_read_lines(today_file)
        if not lines:
            return 1
        last_msg = json.loads(lines[-1])
        return last_msg["id"] + 1
    except (json.JSONDecodeError, KeyError):
        # If file is corrupted, count lines + 1
        return len(lines) + 1


def calculate_message_hash(msg: Message) -> str:
    """Calculate simple SHA-256 hash of message.
    
    Hash includes: id, parent, branch, sender, content, timestamp
    Excludes: hash field itself (circular dependency)
    
    Args:
        msg: Message to hash
        
    Returns:
        16-character hex hash (shortened for simplicity)
    """
    hash_input = f"{msg.id}|{msg.parent}|{msg.branch}|{msg.sender}|{msg.content}|{msg.timestamp}"
    full_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    return full_hash[:16]  # Short hash (64 bits)


def calculate_full_integrity_hash(msg: Message) -> str:
    """Full SHA-256 integrity hash (canonical sorted-keys JSON).

    Covers: id, parent, branch, sender, content, timestamp,
            message_uuid, conversation_uuid, model.
    Deterministic: sorted keys, no whitespace, UTF-8.
    """
    data = {
        "id": msg.id,
        "parent": msg.parent,
        "branch": msg.branch,
        "sender": msg.sender,
        "content": msg.content,
        "timestamp": msg.timestamp,
        "message_uuid": msg.message_uuid,
        "conversation_uuid": msg.conversation_uuid,
        "model": msg.model.model_dump() if msg.model else None,
    }
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def log_message(
    sender: Literal["user", "ai"],
    content: str,
    model_identity: Optional[Dict[str, Any]] = None,
    parent: Optional[int] = None,
    branch: str = "main",
    fork_point: Optional[int] = None,
    conversation_id: Optional[str] = None,
    actor: Optional[ActorType] = None,
    seat: Optional[Dict[str, Any]] = None,
    kind: Optional[str] = None,
) -> Dict[str, Any]:
    """Append message to today's JSONL file.

    Args:
        sender: "user" or "ai" (legacy, kept for hash backward compat)
        content: Message text
        model_identity: AI model info (legacy, prefer seat)
        parent: Parent message ID (auto-calculated if None)
        branch: Branch name (default "main")
        fork_point: Fork origin message ID (only for first message of branch)
        conversation_id: Optional conversation UUID (session scoping)
        actor: Authoritative speaker identity (user/assistant/tool/system)
        seat: Execution context (provider/model/seat_id/node_id)

    Returns:
        {
            "message_id": int,
            "message_uuid": str,
            "conversation_uuid": str | None,
            "conversation_id": str | None,   # alias
            "date": str,
            "near_cutoff": bool,
            "cutoff_warning": str | None
        }
    """
    # ── Critical section: read ID → build → append (must be atomic) ──
    with _log_lock:
        # Get next ID
        msg_id = get_next_message_id()

        # Auto-calculate parent if not provided
        if parent is None:
            parent = msg_id - 1 if msg_id > 1 else None

        # Generate UUID identity
        msg_uuid = str(_uuid.uuid4())
        conv_uuid = conversation_id or None

        # Derive actor from sender if not explicitly provided
        if actor is None:
            actor = "user" if sender == "user" else "assistant"

        # Build seat from model_identity if not explicitly provided
        seat_obj = None
        if seat is not None:
            seat_obj = Seat(**seat)
        elif model_identity is not None:
            seat_obj = Seat(
                provider=model_identity.get("provider", "unknown"),
                model=model_identity.get("model", "unknown"),
                seat_id="local" if model_identity.get("provider") == "ollama" else None,
                node_id="server",
            )

        # Build message
        msg = Message(
            id=msg_id,
            parent=parent,
            branch=branch,
            fork_point=fork_point,
            sender=sender,
            actor=actor,
            seat=seat_obj,
            content=content,
            model=ModelIdentity(**model_identity) if model_identity else None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hash="",
            message_uuid=msg_uuid,
            conversation_uuid=conv_uuid,
            kind=kind,
            integrity_hash=None,
            envelope_version=2,
        )

        # Calculate hashes
        msg.hash = calculate_message_hash(msg)
        msg.integrity_hash = calculate_full_integrity_hash(msg)

        # Append to file
        today_file = get_today_file()
        msg_json = msg.model_dump_json()

        if _GOVERNED:
            # Route through gateway — audited, zone-enforced
            filename = today_file.name  # e.g. "2026-02-09.jsonl"
            result = _gw.append("system", WriteZone.CHAT_THREADS, filename, msg_json)
            if not result.success:
                raise OSError(f"Gateway append failed: {result.error}")
        else:
            if not ALLOW_LEGACY_WRITES:
                raise RuntimeError("Legacy writes disabled. Set ALLOW_LEGACY_WRITES=true to bypass.")
            secure_append_line(today_file, msg_json)

    # ── Outside lock: non-critical, non-blocking ──────────────
    # Auto-summarize: first message of a new day triggers rollups
    if msg_id == 1:
        _fire_auto_summary()

    # Check cutoff warning
    near_cutoff = is_near_cutoff()

    return {
        "message_id": msg_id,
        "message_uuid": msg_uuid,
        "conversation_uuid": conv_uuid,
        "conversation_id": conv_uuid,       # alias for memory/ callers
        "date": datetime.now().strftime("%Y-%m-%d"),
        "near_cutoff": near_cutoff,
        "cutoff_warning": "New chat file starts soon - consider starting new conversation" if near_cutoff else None,
    }


# ── Auto-Summary Trigger ──────────────────────────────────────

def _fire_auto_summary() -> None:
    """Fire summary rollups + chat BM25 ingest in a background daemon thread.

    Non-blocking: log_message() returns immediately.
    Non-fatal: any failure is logged and swallowed.
    """
    def _run():
        try:
            from .summarizer import check_and_run_rollups
            results = check_and_run_rollups()
            logger.info("Auto-summary completed: %s", results)
        except Exception as e:
            logger.warning("Auto-summary background thread failed: %s", e)

        # Auto-trigger chat BM25 ingest for yesterday
        try:
            import subprocess
            import sys
            script = Path(__file__).resolve().parents[2] / "scripts" / "chatlog_stream.py"
            if script.exists():
                subprocess.Popen(
                    [sys.executable, str(script), "--days", "1"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("Auto chat BM25 ingest triggered")
        except Exception as e:
            logger.warning("Auto chat ingest failed: %s", e)

        # Auto-trigger 616 map + LakeSpeak ingest for yesterday's chat
        try:
            import httpx as _hx
            yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
            _hx.post(
                "http://127.0.0.1:5050/api/memory/ingest",
                json={"start_date": yesterday, "end_date": yesterday},
                timeout=120.0,
            )
            logger.info("Auto chat 616+lake ingest triggered for %s", yesterday)
        except Exception as e:
            logger.warning("Auto chat 616+lake ingest failed: %s", e)

    t = threading.Thread(target=_run, name="auto-summary", daemon=True)
    t.start()


def get_today_stats() -> Dict[str, Any]:
    """Get statistics for today's conversation file.
    
    Returns:
        {
            "date": str,
            "message_count": int,
            "file_size_kb": float,
            "branches": List[str]
        }
    """
    today_file = get_today_file()
    
    if not today_file.exists():
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "message_count": 0,
            "file_size_kb": 0.0,
            "branches": []
        }
    
    # Read messages
    branches = set()
    message_count = 0
    
    lines = secure_read_lines(today_file)
    for line in lines:
        message_count += 1
        try:
            msg = json.loads(line)
            branches.add(msg.get("branch", "main"))
        except json.JSONDecodeError:
            pass
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "message_count": message_count,
        "file_size_kb": round(today_file.stat().st_size / 1024, 2),
        "branches": sorted(list(branches))
    }
