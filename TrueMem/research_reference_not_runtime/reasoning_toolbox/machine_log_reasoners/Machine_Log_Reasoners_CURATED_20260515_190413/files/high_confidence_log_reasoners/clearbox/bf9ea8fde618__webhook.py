"""Generic webhook channel adapter for Reach.

Handles inbound webhooks from Slack, X (Twitter), or any custom service.
Each webhook POST is normalized to a ReachMessage, dispatched, and the
response is returned as JSON.

This adapter doesn't run a separate bot — it exposes FastAPI routes
that external services POST to. Configure your platform's webhook URL
to point at: https://<your-clearbox>:5050/api/reach/webhook/inbound

Security: HMAC signature verification using REACH_WEBHOOK_SECRET.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any, Dict, List, Optional

from reach.bus.dispatcher import Dispatcher
from reach.bus.message import ReachMessage, ReachResponse
from reach.channels.base import ChannelAdapter

logger = logging.getLogger(__name__)


class WebhookAdapter(ChannelAdapter):
    """Generic webhook channel adapter.

    Unlike Discord/Telegram adapters, this doesn't maintain a persistent
    connection. It processes individual webhook POSTs via handle_webhook().
    """

    channel_name = "webhook"

    def __init__(self, dispatcher: Dispatcher, config: Dict[str, Any]):
        super().__init__(dispatcher, config)
        self._secret: Optional[str] = None
        self._allowed_origins: List[str] = config.get("allowed_origins", [])

    async def start(self) -> None:
        """Initialize webhook adapter (load secret)."""
        secret_env = self._config.get("secret_env", "REACH_WEBHOOK_SECRET")
        self._secret = os.environ.get(secret_env)
        if not self._secret:
            logger.warning(
                "Webhook secret not set in %s — signature verification disabled",
                secret_env,
            )
        self._running = True
        logger.info("Webhook adapter ready")

    async def stop(self) -> None:
        self._running = False
        logger.info("Webhook adapter stopped")

    async def send_response(self, response: ReachResponse, context: Any) -> None:
        """Webhook responses are returned inline — no async send needed."""
        pass

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature on inbound webhook."""
        if not self._secret:
            return True  # No secret configured — skip verification

        expected = hmac.new(
            self._secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected}", signature)

    async def handle_webhook(
        self,
        text: str,
        source: str,
        user_id: str,
        message_id: str = "",
        signature: str = "",
        raw_body: bytes = b"",
    ) -> Dict[str, Any]:
        """Process an inbound webhook POST.

        Args:
            text: The message text.
            source: Platform identifier (e.g., "slack", "x", "custom").
            user_id: Platform user identifier.
            message_id: Platform message ID (optional).
            signature: HMAC signature header (optional).
            raw_body: Raw request body for signature verification.

        Returns:
            Dict with the response data.
        """
        # Verify signature if provided
        if signature and raw_body:
            if not self.verify_signature(raw_body, signature):
                logger.warning("Webhook signature verification failed from %s", source)
                return {
                    "error": "Invalid signature",
                    "status": 403,
                }

        # Origin check
        if self._allowed_origins and source not in self._allowed_origins:
            logger.warning("Webhook from disallowed origin: %s", source)
            return {
                "error": "Origin not allowed",
                "status": 403,
            }

        msg = ReachMessage(
            channel="webhook",
            channel_message_id=message_id or "webhook_msg",
            channel_user_id=f"{source}:{user_id}",
            text=text,
            session_id=f"reach_webhook_{source}_{user_id}",
        )

        response = await self._dispatcher.dispatch(msg)

        return {
            "status": 200,
            "message_id": response.message_id,
            "text": response.text,
            "grounded": response.grounded,
            "citations": response.citations,
        }
