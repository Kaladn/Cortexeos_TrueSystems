"""Pydantic models for Reach API endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PairRequest(BaseModel):
    """Confirm a pairing code."""
    code: str = Field(..., min_length=6, max_length=6, description="6-character pairing code")
    identity: str = Field(..., min_length=1, description="Clearbox user identity")


class PairResponse(BaseModel):
    """Pairing confirmation result."""
    success: bool
    message: str


class RevokeResponse(BaseModel):
    """Pairing revocation result."""
    success: bool
    message: str


class ChannelStatus(BaseModel):
    """Status of a single channel."""
    enabled: bool = False
    running: bool = False


class ReachStatus(BaseModel):
    """Overall Reach status."""
    enabled: bool = True
    bridge_url: str = ""
    paired_count: int = 0
    pending_codes: int = 0
    channels: Dict[str, ChannelStatus] = {}


class WebhookInbound(BaseModel):
    """Inbound webhook payload."""
    text: str = Field(..., min_length=1, description="Message text")
    source: str = Field(..., min_length=1, description="Platform identifier (slack, x, custom)")
    user_id: str = Field(..., min_length=1, description="Platform user identifier")
    message_id: str = Field(default="", description="Platform message ID")


class WebhookResponse(BaseModel):
    """Webhook response payload."""
    status: int = 200
    message_id: str = ""
    text: str = ""
    grounded: bool = False
    citations: List[Dict[str, Any]] = []
    error: Optional[str] = None


class AuditEntry(BaseModel):
    """A single audit log entry."""
    direction: str
    message_id: str = ""
    timestamp_utc: str = ""
    channel: str = ""
    channel_user_id: str = ""
    paired: bool = False


class PairingListEntry(BaseModel):
    """A single pairing record."""
    channel_key: str
    clearbox_identity: str


class HelpResponse(BaseModel):
    """Machine-readable help response."""
    plugin: str = "reach"
    version: str = ""
    description: str = ""
    endpoints: List[Dict[str, str]] = []
    channels_supported: List[str] = []
