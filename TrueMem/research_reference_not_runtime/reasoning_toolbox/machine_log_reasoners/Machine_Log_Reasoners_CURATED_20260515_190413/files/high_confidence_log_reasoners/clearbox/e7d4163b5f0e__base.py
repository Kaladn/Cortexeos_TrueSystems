"""Abstract base class for Reach channel adapters.

Every channel adapter is a thin protocol handler. It knows how to:
  1. Receive messages from its platform
  2. Normalize them into ReachMessage
  3. Send ReachResponse back formatted for its platform
  4. Nothing else — no decisions, no processing

The dispatcher handles authentication, routing, and audit.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from reach.bus.dispatcher import Dispatcher
from reach.bus.message import ReachMessage, ReachResponse

logger = logging.getLogger(__name__)


class ChannelAdapter(ABC):
    """Base class for all Reach channel adapters."""

    channel_name: str = "unknown"

    def __init__(self, dispatcher: Dispatcher, config: Dict[str, Any]):
        self._dispatcher = dispatcher
        self._config = config
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """Start listening for messages on this channel."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening and clean up."""

    @abstractmethod
    async def send_response(self, response: ReachResponse, context: Any) -> None:
        """Send a response back through this channel.

        Args:
            response: The ReachResponse to send.
            context: Platform-specific context needed to reply
                     (e.g., Discord message object, Telegram chat_id).
        """

    async def handle_message(
        self,
        text: str,
        channel_message_id: str,
        channel_user_id: str,
        context: Any = None,
        session_id: Optional[str] = None,
    ) -> ReachResponse:
        """Common handler: normalize → dispatch → respond.

        Channel adapters call this from their platform-specific event handlers.
        """
        msg = ReachMessage(
            channel=self.channel_name,
            channel_message_id=channel_message_id,
            channel_user_id=channel_user_id,
            text=text,
            session_id=session_id,
        )

        response = await self._dispatcher.dispatch(msg)

        try:
            await self.send_response(response, context)
        except Exception as e:
            logger.error(
                "[%s] Failed to send response for %s: %s",
                self.channel_name,
                msg.message_id,
                e,
            )

        return response

    @property
    def is_running(self) -> bool:
        return self._running

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"<{self.__class__.__name__} channel={self.channel_name} {status}>"
