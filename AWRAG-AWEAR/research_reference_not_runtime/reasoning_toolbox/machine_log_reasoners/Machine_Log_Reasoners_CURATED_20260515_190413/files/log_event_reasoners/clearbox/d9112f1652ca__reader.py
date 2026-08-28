"""Reader - Load conversation history for model context.

Provides read-only access to:
- Today's messages
- Recent days (for context window)
- Specific branches
- Full conversation reconstruction
- Integrity verification (warning-only, non-blocking)
"""

import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from .models import Message

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security.data_paths import CHAT_THREADS_DIR
from security.secure_storage import secure_read_lines
THREADS_ROOT = CHAT_THREADS_DIR

logger = logging.getLogger(__name__)


def _verify_integrity(msg: Message) -> None:
    """Check integrity hash if present. Warning only — never crashes."""
    if not msg.integrity_hash:
        return
    try:
        from .daily_logger import calculate_full_integrity_hash
        expected = calculate_full_integrity_hash(msg)
        if msg.integrity_hash != expected:
            logger.warning(
                "Integrity mismatch on msg %d (uuid=%s): "
                "expected=%s..., got=%s...",
                msg.id, msg.message_uuid or "?",
                expected[:16], msg.integrity_hash[:16],
            )
    except Exception:
        pass  # Non-blocking — integrity check is best-effort


def load_today() -> List[Message]:
    """Load all messages from today's file.

    Returns:
        List of Message objects (empty if no file)
    """
    from .daily_logger import get_today_file
    today_file = get_today_file()

    if not today_file.exists():
        return []

    messages = []
    lines = secure_read_lines(today_file)
    for line in lines:
        try:
            msg = Message(**json.loads(line))
            _verify_integrity(msg)
            messages.append(msg)
        except (json.JSONDecodeError, ValueError):
            # Skip malformed lines
            continue

    return messages


def load_day(date_str: str) -> List[Message]:
    """Load all messages from a specific day.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        List of Message objects (empty if no file)
    """
    file_path = THREADS_ROOT / f"{date_str}.jsonl"
    if not file_path.exists():
        return []

    messages = []
    for line in secure_read_lines(file_path):
        try:
            msg = Message(**json.loads(line))
            _verify_integrity(msg)
            messages.append(msg)
        except (json.JSONDecodeError, ValueError):
            continue
    return messages


def load_recent_days(days: int = 7) -> List[Message]:
    """Load messages from last N days for model context.
    
    Args:
        days: Number of days to load (default 7)
        
    Returns:
        List of Message objects from recent days
    """
    messages = []

    for i in range(days - 1, -1, -1):  # oldest first → today last
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        file_path = THREADS_ROOT / f"{date}.jsonl"
        
        if file_path.exists():
            lines = secure_read_lines(file_path)
            for line in lines:
                try:
                    msg = Message(**json.loads(line))
                    _verify_integrity(msg)
                    messages.append(msg)
                except (json.JSONDecodeError, ValueError):
                    continue

    return messages


def get_branch_messages(branch: str = "main", date: Optional[str] = None) -> List[Message]:
    """Get all messages in a specific branch.
    
    Args:
        branch: Branch name (default "main")
        date: Date string YYYY-MM-DD (default today)
        
    Returns:
        List of Message objects in that branch
    """
    if date is None:
        messages = load_today()
    else:
        file_path = THREADS_ROOT / f"{date}.jsonl"
        if not file_path.exists():
            return []
        
        messages = []
        for line in secure_read_lines(file_path):
            try:
                messages.append(Message(**json.loads(line)))
            except (json.JSONDecodeError, ValueError):
                continue
    
    return [m for m in messages if m.branch == branch]


def reconstruct_path(messages: List[Message], start_id: int, branch: str) -> List[Message]:
    """Reconstruct conversation path from fork point to current message.
    
    Args:
        messages: List of all messages
        start_id: Starting message ID
        branch: Target branch
        
    Returns:
        Ordered list of messages in path
    """
    # Build message lookup
    msg_map = {m.id: m for m in messages}
    
    # Get all messages in target branch
    branch_msgs = [m for m in messages if m.branch == branch]
    
    if not branch_msgs:
        return []
    
    # Find fork point
    fork_msg = next((m for m in branch_msgs if m.fork_point is not None), None)
    
    if fork_msg is None:
        # No fork point means main branch
        return sorted(branch_msgs, key=lambda m: m.id)
    
    # Reconstruct parent path up to fork point
    path = []
    current_id = fork_msg.fork_point
    
    while current_id is not None:
        if current_id in msg_map:
            path.append(msg_map[current_id])
            current_id = msg_map[current_id].parent
        else:
            break
    
    path.reverse()
    
    # Add branch messages
    path.extend(sorted(branch_msgs, key=lambda m: m.id))
    
    return path


def format_for_model_context(messages: List[Message], max_chars: int = 10000) -> str:
    """Format messages as text for LLM context window.
    
    Args:
        messages: List of messages
        max_chars: Maximum character limit
        
    Returns:
        Formatted string for model context
    """
    lines = []
    
    for msg in messages:
        timestamp = msg.timestamp[:19]  # Remove timezone
        lines.append(f"[{timestamp}] {msg.sender}: {msg.content}")
    
    full_text = "\n".join(lines)
    
    # Truncate if too long (keep most recent)
    if len(full_text) > max_chars:
        lines_reversed = list(reversed(lines))
        truncated = []
        char_count = 0
        
        for line in lines_reversed:
            if char_count + len(line) > max_chars:
                break
            truncated.append(line)
            char_count += len(line)
        
        truncated.reverse()
        full_text = "\n".join(truncated)
        full_text = "[...earlier messages truncated...]\n" + full_text
    
    return full_text


def get_conversation_summary() -> dict:
    """Get summary of all available conversation files.
    
    Returns:
        {
            "total_files": int,
            "total_messages": int,
            "date_range": [str, str],
            "files": List[dict]
        }
    """
    files = sorted(THREADS_ROOT.glob("*.jsonl"))
    
    if not files:
        return {
            "total_files": 0,
            "total_messages": 0,
            "date_range": [None, None],
            "files": []
        }
    
    file_info = []
    total_messages = 0
    
    for file_path in files:
        message_count = len(secure_read_lines(file_path))
        total_messages += message_count
        
        file_info.append({
            "date": file_path.stem,
            "message_count": message_count,
            "size_kb": round(file_path.stat().st_size / 1024, 2)
        })
    
    return {
        "total_files": len(files),
        "total_messages": total_messages,
        "date_range": [files[0].stem, files[-1].stem],
        "files": file_info
    }
