"""FastAPI router for Reach management endpoints.

These routes let you manage Reach from the Clearbox UI or API:
  - Check status of all channels
  - Confirm/revoke pairings
  - View audit entries
  - Process inbound webhooks
  - Get machine-readable help
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from reach import VERSION
from reach.api.models import (
    AuditEntry,
    ChannelStatus,
    HelpResponse,
    PairRequest,
    PairResponse,
    PairingListEntry,
    ReachStatus,
    RevokeResponse,
    WebhookInbound,
    WebhookResponse,
)
from reach.bus.dispatcher import Dispatcher
from reach.config import load_reach_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reach", tags=["reach"])

# Lazy singleton — initialized on first request
_dispatcher = None
_webhook_adapter = None
_config = None


def _get_config():
    global _config
    if _config is None:
        _config = load_reach_config()
    return _config


def _get_dispatcher():
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = Dispatcher(_get_config())
    return _dispatcher


def _get_webhook():
    global _webhook_adapter
    if _webhook_adapter is None:
        from reach.channels.webhook import WebhookAdapter
        config = _get_config().get("channels", {}).get("webhook", {})
        _webhook_adapter = WebhookAdapter(_get_dispatcher(), config)
    return _webhook_adapter


# ── Status ──────────────────────────────────────────────

@router.get("/status", response_model=ReachStatus)
async def get_status():
    """Return Reach status: enabled channels, pairing counts."""
    dispatcher = _get_dispatcher()
    raw = dispatcher.get_status()

    channels = {}
    for name, info in raw.get("channels", {}).items():
        channels[name] = ChannelStatus(enabled=info.get("enabled", False))

    return ReachStatus(
        enabled=raw.get("enabled", True),
        bridge_url=raw.get("bridge_url", ""),
        paired_count=raw.get("paired_count", 0),
        pending_codes=raw.get("pending_codes", 0),
        channels=channels,
    )


# ── Channels ────────────────────────────────────────────

@router.get("/channels")
async def list_channels():
    """List all configured channels and their status."""
    config = _get_config()
    channels = config.get("channels", {})
    return {
        name: {"enabled": ch.get("enabled", False)}
        for name, ch in channels.items()
    }


# ── Pairing ─────────────────────────────────────────────

@router.post("/pair", response_model=PairResponse)
async def confirm_pairing(req: PairRequest):
    """Confirm a pairing code from the local UI."""
    dispatcher = _get_dispatcher()
    success = dispatcher.confirm_pairing(req.code, req.identity)
    if success:
        return PairResponse(success=True, message=f"Paired to identity: {req.identity}")
    else:
        return PairResponse(success=False, message="Invalid or expired pairing code")


@router.delete("/pair/{channel}/{channel_user_id}", response_model=RevokeResponse)
async def revoke_pairing(channel: str, channel_user_id: str):
    """Revoke a pairing for a specific channel user."""
    dispatcher = _get_dispatcher()
    success = dispatcher.revoke_pairing(channel, channel_user_id)
    if success:
        return RevokeResponse(success=True, message="Pairing revoked")
    else:
        return RevokeResponse(success=False, message="Pairing not found")


@router.get("/pairings", response_model=List[PairingListEntry])
async def list_pairings():
    """List all active pairings (admin only)."""
    dispatcher = _get_dispatcher()
    pairs = dispatcher._identity.list_pairings()
    return [
        PairingListEntry(channel_key=k, clearbox_identity=v)
        for k, v in pairs.items()
    ]


# ── Webhook inbound ─────────────────────────────────────

@router.post("/webhook/inbound", response_model=WebhookResponse)
async def webhook_inbound(
    payload: WebhookInbound,
    request: Request,
    x_signature: str = Header(default="", alias="X-Reach-Signature"),
):
    """Process an inbound webhook from Slack, X, or custom service."""
    config = _get_config()
    if not config.get("channels", {}).get("webhook", {}).get("enabled", False):
        return WebhookResponse(status=503, error="Webhook channel not enabled")

    webhook = _get_webhook()
    raw_body = await request.body()

    result = await webhook.handle_webhook(
        text=payload.text,
        source=payload.source,
        user_id=payload.user_id,
        message_id=payload.message_id,
        signature=x_signature,
        raw_body=raw_body,
    )

    return WebhookResponse(**result)


# ── Audit ───────────────────────────────────────────────

@router.get("/audit")
async def get_audit(limit: int = 50):
    """Return recent audit entries."""
    try:
        from security.data_paths import REACH_AUDIT_DIR
        audit_dir = REACH_AUDIT_DIR
    except ImportError:
        audit_dir = Path("data/reach/audit")

    if not audit_dir.exists():
        return []

    # Get the most recent audit file
    files = sorted(audit_dir.glob("reach_audit_*.jsonl"), reverse=True)
    if not files:
        return []

    entries = []
    with open(files[0], "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Return most recent entries
    return entries[-limit:]


# ── Help ────────────────────────────────────────────────

@router.get("/help", response_model=HelpResponse)
async def get_help():
    """Machine-readable API schema for Reach."""
    return HelpResponse(
        plugin="reach",
        version=VERSION,
        description="Channel gateway — control your Clearbox workbench from anywhere",
        endpoints=[
            {"method": "GET", "path": "/api/reach/status", "description": "Channel status and pairing counts"},
            {"method": "GET", "path": "/api/reach/channels", "description": "List configured channels"},
            {"method": "POST", "path": "/api/reach/pair", "description": "Confirm a pairing code"},
            {"method": "DELETE", "path": "/api/reach/pair/{channel}/{channel_user_id}", "description": "Revoke a pairing"},
            {"method": "GET", "path": "/api/reach/pairings", "description": "List all active pairings"},
            {"method": "POST", "path": "/api/reach/webhook/inbound", "description": "Process inbound webhook"},
            {"method": "GET", "path": "/api/reach/audit", "description": "Recent audit entries"},
            {"method": "GET", "path": "/api/reach/help", "description": "This help"},
        ],
        channels_supported=["discord", "telegram", "webhook", "websocket"],
    )
