"""Reach dispatcher — normalize, authenticate, forward to bridge, return response.

This is the single choke point. Every message from every channel passes through
here. The dispatcher:
  1. Checks pairing (rejects unpaired if required)
  2. Resolves clearbox identity
  3. Forwards to the bridge API
  4. Wraps the bridge response in a ReachResponse
  5. Audits both directions
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from reach.bus.audit import ReachAuditLogger
from reach.bus.message import ReachMessage, ReachResponse
from reach.config import load_reach_config
from reach.security.identity import IdentityStore
from reach.security.pairing import PairingManager

logger = logging.getLogger(__name__)


class Dispatcher:
    """Central message dispatcher for all Reach channels."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or load_reach_config()
        self._pairing = PairingManager()
        self._identity = IdentityStore()
        self._audit = ReachAuditLogger(
            log_content=self._config.get("audit_content", False)
        )
        self._bridge_url = self._config.get("bridge_url", "https://127.0.0.1:5050")
        self._max_len = self._config.get("max_message_length", 4000)

    async def dispatch(self, msg: ReachMessage) -> ReachResponse:
        """Process an inbound message and return a response.

        Flow: authenticate → resolve identity → forward → audit → respond.
        """
        # Truncate oversized messages
        if len(msg.text) > self._max_len:
            msg.text = msg.text[: self._max_len]

        # Resolve identity from pairing store
        identity = self._identity.resolve(msg.channel, msg.channel_user_id)
        if identity:
            msg.clearbox_identity = identity
            msg.paired = True
        else:
            msg.paired = False

        # Audit inbound
        self._audit.log_inbound(msg)

        # Check pairing requirement
        channel_config = self._config.get("channels", {}).get(msg.channel, {})
        pairing_required = channel_config.get(
            "pairing_required", self._config.get("pairing_required", True)
        )

        if pairing_required and not msg.paired:
            return self._handle_unpaired(msg)

        # Forward to bridge
        response = await self._forward_to_bridge(msg)

        # Audit outbound
        self._audit.log_outbound(response)

        return response

    def _handle_unpaired(self, msg: ReachMessage) -> ReachResponse:
        """Generate a pairing code for an unpaired user."""
        code = self._pairing.create_code(msg.channel, msg.channel_user_id)

        self._audit.log_pairing_attempt(
            channel=msg.channel,
            channel_user_id=msg.channel_user_id,
            code=code,
            success=False,
        )

        resp = ReachResponse(
            in_reply_to=msg.message_id,
            channel=msg.channel,
            text=(
                f"Pairing required. Your code is: {code}\n\n"
                f"Enter this code in your Clearbox UI at https://127.0.0.1:5050 "
                f"or POST to /api/reach/pair to connect this account."
            ),
            bridge_endpoint="",
            bridge_status=0,
        )
        self._audit.log_outbound(resp)
        return resp

    async def _forward_to_bridge(self, msg: ReachMessage) -> ReachResponse:
        """Forward the message to the Clearbox bridge API."""
        import httpx

        endpoint = "/api/chat/send"
        url = urljoin(self._bridge_url, endpoint)

        payload = {
            "message": msg.text,
            "mode": "grounded",
            "session_id": msg.session_id or f"reach_{msg.channel}_{msg.channel_user_id}",
            "caller": "human",
            "source": f"reach:{msg.channel}",
        }

        try:
            async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                status = resp.status_code

                if status == 200:
                    data = resp.json()
                    return ReachResponse(
                        in_reply_to=msg.message_id,
                        channel=msg.channel,
                        text=data.get("answer_text", data.get("response", "")),
                        grounded=data.get("grounded", False),
                        citations=data.get("citations", []),
                        bridge_endpoint=endpoint,
                        bridge_status=status,
                    )
                else:
                    logger.error("Bridge returned %d: %s", status, resp.text[:200])
                    return ReachResponse(
                        in_reply_to=msg.message_id,
                        channel=msg.channel,
                        text=f"Bridge error (HTTP {status}). Your workbench may be offline.",
                        bridge_endpoint=endpoint,
                        bridge_status=status,
                    )

        except httpx.ConnectError:
            logger.error("Cannot connect to bridge at %s", self._bridge_url)
            return ReachResponse(
                in_reply_to=msg.message_id,
                channel=msg.channel,
                text="Cannot reach your Clearbox workbench. Is it running?",
                bridge_endpoint=endpoint,
                bridge_status=0,
            )
        except Exception as e:
            logger.error("Bridge forward error: %s", e)
            return ReachResponse(
                in_reply_to=msg.message_id,
                channel=msg.channel,
                text="Internal error forwarding to workbench.",
                bridge_endpoint=endpoint,
                bridge_status=0,
            )

    def confirm_pairing(self, code: str, identity: str) -> bool:
        """Confirm a pairing code from the local UI."""
        record = self._pairing.confirm(code)
        if record is None:
            return False

        self._identity.store(
            channel=record["channel"],
            channel_user_id=record["channel_user_id"],
            clearbox_identity=identity,
        )

        self._audit.log_pairing_attempt(
            channel=record["channel"],
            channel_user_id=record["channel_user_id"],
            code=code,
            success=True,
            identity=identity,
        )
        return True

    def revoke_pairing(self, channel: str, channel_user_id: str) -> bool:
        """Revoke a pairing."""
        return self._identity.revoke(channel, channel_user_id)

    def get_status(self) -> Dict[str, Any]:
        """Return current reach status."""
        return {
            "enabled": self._config.get("enabled", True),
            "bridge_url": self._bridge_url,
            "paired_count": self._identity.count(),
            "pending_codes": self._pairing.pending_count(),
            "channels": {
                name: {"enabled": ch.get("enabled", False)}
                for name, ch in self._config.get("channels", {}).items()
            },
        }
