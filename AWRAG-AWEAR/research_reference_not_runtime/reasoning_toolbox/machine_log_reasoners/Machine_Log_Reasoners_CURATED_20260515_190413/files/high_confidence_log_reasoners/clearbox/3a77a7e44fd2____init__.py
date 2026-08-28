"""Reach — Channel gateway for Clearbox AI Studio.

Control your sovereign local workbench from wherever you are:
Discord, Telegram, Slack, X, webhooks, or custom WebSocket clients.

Reach is NOT the product. Clearbox is the product. Reach is the remote control.

Every message in, every response out — audited, paired, governed.
"""

from __future__ import annotations

VERSION = "0.1.0"

from reach.api.router import router  # noqa: E402, F401

__all__ = ["router", "VERSION"]
