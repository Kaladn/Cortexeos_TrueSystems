"""Discord channel adapter for Reach.

Thin wrapper around discord.py. Receives messages, normalizes to ReachMessage,
forwards through dispatcher, sends response back as Discord message.

Requires: pip install discord.py
Token: REACH_DISCORD_TOKEN environment variable
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from reach.bus.dispatcher import Dispatcher
from reach.bus.message import ReachResponse
from reach.channels.base import ChannelAdapter

logger = logging.getLogger(__name__)


class DiscordAdapter(ChannelAdapter):
    """Discord bot channel adapter."""

    channel_name = "discord"

    def __init__(self, dispatcher: Dispatcher, config: Dict[str, Any]):
        super().__init__(dispatcher, config)
        self._client = None
        self._token: Optional[str] = None
        self._allowed_guilds = set(config.get("allowed_guilds", []))

    async def start(self) -> None:
        """Start the Discord bot."""
        try:
            import discord
        except ImportError:
            logger.error("discord.py not installed — run: pip install discord.py")
            return

        token_env = self._config.get("token_env", "REACH_DISCORD_TOKEN")
        self._token = os.environ.get(token_env)
        if not self._token:
            logger.error("Discord token not set in env var %s", token_env)
            return

        intents = discord.Intents.default()
        intents.message_content = True
        self._client = discord.Client(intents=intents)

        adapter = self

        @self._client.event
        async def on_ready():
            logger.info("Reach Discord adapter connected as %s", self._client.user)
            adapter._running = True

        @self._client.event
        async def on_message(message):
            # Ignore own messages
            if message.author == self._client.user:
                return

            # Ignore bots
            if message.author.bot:
                return

            # Guild allowlist check
            if adapter._allowed_guilds and message.guild:
                if str(message.guild.id) not in adapter._allowed_guilds:
                    return

            # Only respond to DMs or mentions
            is_dm = message.guild is None
            is_mentioned = self._client.user in message.mentions
            if not is_dm and not is_mentioned:
                return

            # Strip the mention from the text
            text = message.content
            if is_mentioned and self._client.user:
                text = text.replace(f"<@{self._client.user.id}>", "").strip()

            if not text:
                return

            await adapter.handle_message(
                text=text,
                channel_message_id=str(message.id),
                channel_user_id=str(message.author.id),
                context=message,
                session_id=f"reach_discord_{message.author.id}",
            )

        # Run in background task so we don't block
        asyncio.create_task(self._client.start(self._token))
        logger.info("Discord adapter starting...")

    async def stop(self) -> None:
        """Disconnect the Discord bot."""
        if self._client:
            await self._client.close()
        self._running = False
        logger.info("Discord adapter stopped")

    async def send_response(self, response: ReachResponse, context: Any) -> None:
        """Send response back to Discord channel/DM."""
        if context is None:
            logger.warning("No Discord context to reply to")
            return

        text = response.text

        # Discord has a 2000 char limit
        if len(text) > 1990:
            chunks = [text[i : i + 1990] for i in range(0, len(text), 1990)]
            for chunk in chunks:
                await context.reply(chunk)
        else:
            await context.reply(text)
