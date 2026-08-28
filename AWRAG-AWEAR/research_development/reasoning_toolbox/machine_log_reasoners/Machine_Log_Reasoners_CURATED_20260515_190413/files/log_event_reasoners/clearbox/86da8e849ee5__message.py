"""Canonical message envelopes for Reach.

Every message from every channel gets normalized into a ReachMessage.
Every response from the bridge gets wrapped in a ReachResponse.
These are the FROZEN schemas — reach_message@1 and reach_response@1.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

REACH_MESSAGE_VERSION = "reach_message@1"
REACH_RESPONSE_VERSION = "reach_response@1"


def _make_id() -> str:
    return f"rm_{uuid.uuid4().hex[:16]}"


@dataclass
class ReachMessage:
    """Canonical inbound message from any channel."""

    channel: str
    channel_message_id: str
    channel_user_id: str
    text: str
    message_id: str = field(default_factory=_make_id)
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    clearbox_identity: Optional[str] = None
    paired: bool = False
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    session_id: Optional[str] = None
    schema_version: str = REACH_MESSAGE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "message_id": self.message_id,
            "timestamp_utc": self.timestamp_utc,
            "channel": self.channel,
            "channel_message_id": self.channel_message_id,
            "channel_user_id": self.channel_user_id,
            "clearbox_identity": self.clearbox_identity,
            "paired": self.paired,
            "text": self.text,
            "attachments": self.attachments,
            "session_id": self.session_id,
        }


@dataclass
class ReachResponse:
    """Canonical outbound response to send back through a channel."""

    in_reply_to: str
    channel: str
    text: str
    message_id: str = field(default_factory=_make_id)
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    grounded: bool = False
    citations: List[Dict[str, Any]] = field(default_factory=list)
    bridge_endpoint: str = ""
    bridge_status: int = 0
    schema_version: str = REACH_RESPONSE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "message_id": self.message_id,
            "in_reply_to": self.in_reply_to,
            "timestamp_utc": self.timestamp_utc,
            "channel": self.channel,
            "text": self.text,
            "grounded": self.grounded,
            "citations": self.citations,
            "bridge_endpoint": self.bridge_endpoint,
            "bridge_status": self.bridge_status,
        }
