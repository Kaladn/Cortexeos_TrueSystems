"""Pydantic models for chat threads.

Minimal schema optimized for:
- Daily journaling
- Branching conversations
- Model context loading
- Simple integrity verification
- Deterministic actor + seat identity (envelope v2)
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ModelIdentity(BaseModel):
    """AI model provenance (who generated this response)."""

    provider: str = Field(
        ...,
        description="Model provider (e.g., 'openai', 'anthropic', 'ollama')"
    )

    model: str = Field(
        ...,
        description="Model name (e.g., 'gpt-4o', 'qwen2.5:32b')"
    )

    engine: str = Field(
        default="chat",
        description="Engine type (e.g., 'chat', 'completion', 'instruct')"
    )

    revision: Optional[str] = Field(
        default=None,
        description="Model revision/quantization (if applicable)"
    )


class Seat(BaseModel):
    """Seat: which execution context produced this message.

    For actor='assistant': the model that generated it.
    For actor='tool': the tool/plugin that produced output.
    For actor='system': the subsystem (e.g. 'clearbox_bridge', 'ui').
    For actor='user': always null (user has no seat).
    """
    provider: str = Field(
        ...,
        description="Provider (e.g., 'ollama', 'openai', 'anthropic', 'reasoning_engine')"
    )
    model: str = Field(
        ...,
        description="Model or tool name (e.g., 'qwen2.5:32b', 'gpt-4o', 'wolf', 'documap')"
    )
    seat_id: Optional[str] = Field(
        default=None,
        description="Unique seat instance (e.g., 'local', 'api-key-hash-prefix')"
    )
    node_id: Optional[str] = Field(
        default=None,
        description="Execution node (e.g., 'server', 'remote', 'local')"
    )
    error_code: Optional[str] = Field(
        default=None,
        description="If this seat failed (e.g., 'seat_no_response', 'seat_timeout')"
    )


# Actor type — the authoritative identity of who is speaking
ActorType = Literal["user", "assistant", "tool", "system"]


class Message(BaseModel):
    """Single message in conversation thread.

    Ancestry tracking enables branching and path reconstruction.
    Identity contract (envelope v2): actor + seat are authoritative.
    """

    id: int = Field(
        ...,
        description="Sequential message number (per day, starts at 1)"
    )

    parent: Optional[int] = Field(
        default=None,
        description="Parent message ID (None for first message of day)"
    )

    branch: str = Field(
        default="main",
        description="Branch name: 'main', 'A', 'B', 'C', 'A1', 'B1', 'C1'"
    )

    fork_point: Optional[int] = Field(
        default=None,
        description="Message ID where this branch originated (only on first message of branch)"
    )

    sender: Literal["user", "ai"] = Field(
        ...,
        description="Legacy sender field (kept for hash backward compat)"
    )

    # ── Envelope v2: actor + seat (authoritative identity) ─────
    actor: Optional[ActorType] = Field(
        default=None,
        description="Who is speaking: user | assistant | tool | system. "
                    "Authoritative — never infer from display_name."
    )

    seat: Optional[Seat] = Field(
        default=None,
        description="Execution context (model/provider/node). "
                    "Null for actor='user'. Required for actor='assistant'."
    )

    content: str = Field(
        ...,
        description="Message text"
    )

    model: Optional[ModelIdentity] = Field(
        default=None,
        description="Legacy AI model identity (kept for backward compat, prefer seat)"
    )

    timestamp: str = Field(
        ...,
        description="ISO-8601 UTC timestamp"
    )

    hash: str = Field(
        default="",
        description="SHA-256 hash of message (16-char short hash for simplicity)"
    )

    # ── Unified fields (absorbed from Conversations/memory/) ───
    message_uuid: Optional[str] = Field(
        default=None,
        description="UUIDv4 global message identifier"
    )

    conversation_uuid: Optional[str] = Field(
        default=None,
        description="UUIDv4 conversation/session identifier"
    )

    integrity_hash: Optional[str] = Field(
        default=None,
        description="Full 64-char SHA-256 integrity hash (canonical sorted-keys JSON)"
    )

    kind: Optional[str] = Field(
        default=None,
        description="Message kind tag (e.g. 'AI_BRIEF' for pinned doctrine digest)"
    )

    envelope_version: int = Field(
        default=2,
        description="Envelope schema version (2 = actor+seat identity)"
    )


def backfill_actor_seat(msg: Message) -> Message:
    """Backfill actor + seat from legacy sender + model fields.

    Used when loading pre-v2 JSONL records that lack actor/seat.
    Deterministic: sender='user' → actor='user', sender='ai' → actor='assistant'.
    """
    if msg.actor is None:
        msg.actor = "user" if msg.sender == "user" else "assistant"
    if msg.seat is None and msg.model is not None:
        msg.seat = Seat(
            provider=msg.model.provider,
            model=msg.model.model,
            seat_id="local" if msg.model.provider == "ollama" else None,
            node_id="server",
        )
    return msg


# Branch topology rules
BRANCH_RULES = {
    "main": {"max_children": 3, "allowed_branches": ["A", "B", "C"]},
    "A": {"max_children": 1, "allowed_branches": ["A1"]},
    "B": {"max_children": 1, "allowed_branches": ["B1"]},
    "C": {"max_children": 1, "allowed_branches": ["C1"]},
    "A1": {"max_children": 0, "allowed_branches": []},  # TERMINAL
    "B1": {"max_children": 0, "allowed_branches": []},  # TERMINAL
    "C1": {"max_children": 0, "allowed_branches": []},  # TERMINAL
}
