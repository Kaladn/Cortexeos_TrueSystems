"""Chat Threads — Unified conversation logging.

The single chat system for Clearbox AI (v2.0). Combines:
- Daily JSONL journaling with branching topology
- UUID global identity + full SHA-256 integrity hashing (from memory/)
- Citation lifecycle, history retrieval, daily summaries
- Model identity provenance on every AI message

Storage: One JSONL per day (YYYY-MM-DD.jsonl), append-only.
Identity: Sequential int IDs for line addressing + UUIDs for global identity.
Security: Full SHA-256 integrity hash + legacy 16-char short hash.
"""

from .models import Message, ModelIdentity
from .daily_logger import log_message, is_near_cutoff
from .reader import load_today, load_recent_days, get_branch_messages

__all__ = [
    "Message",
    "ModelIdentity",
    "log_message",
    "is_near_cutoff",
    "load_today",
    "load_recent_days",
    "get_branch_messages",
]

__version__ = "2.5.0"
