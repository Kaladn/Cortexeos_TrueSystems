"""Telegram channel adapter for Reach.

Thin wrapper around python-telegram-bot. Receives messages, normalizes to
ReachMessage, forwards through dispatcher, sends response back.

Requires: pip install python-telegram-bot
Token: REACH_TELEGRAM_TOKEN environment variable
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from reach.bus.dispatcher import Dispatcher
from reach.bus.message import ReachResponse
from reach.channels.base import ChannelAdapter

logger = logging.getLogger(__name__)


class TelegramAdapter(ChannelAdapter):
    """Telegram bot channel adapter."""

    channel_name = "telegram"

    def __init__(self, dispatcher: Dispatcher, config: Dict[str, Any]):
        super().__init__(dispatcher, config)
        self._app = None
        self._token: Optional[str] = None
        self._allowed_chats = set(config.get("allowed_chats", []))

    async def start(self) -> None:
        """Start the Telegram bot."""
        try:
            from telegram import Update
            from telegram.ext import (
                ApplicationBuilder,
                ContextTypes,
                MessageHandler,
                filters,
            )
        except ImportError:
            logger.error(
                "python-telegram-bot not installed — run: pip install python-telegram-bot"
            )
            return

        token_env = self._config.get("token_env", "REACH_TELEGRAM_TOKEN")
        self._token = os.environ.get(token_env)
        if not self._token:
            logger.error("Telegram token not set in env var %s", token_env)
            return

        adapter = self

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message or not update.message.text:
                return

            chat_id = str(update.message.chat_id)
            user_id = str(update.message.from_user.id)

            # Chat allowlist check
            if adapter._allowed_chats and chat_id not in adapter._allowed_chats:
                return

            await adapter.handle_message(
                text=update.message.text,
                channel_message_id=str(update.message.message_id),
                channel_user_id=user_id,
                context=update,
                session_id=f"reach_telegram_{user_id}",
            )

        self._app = ApplicationBuilder().token(self._token).build()
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        self._running = True
        logger.info("Telegram adapter started")

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        self._running = False
        logger.info("Telegram adapter stopped")

    async def send_response(self, response: ReachResponse, context: Any) -> None:
        """Send response back to Telegram chat."""
        if context is None:
            logger.warning("No Telegram context to reply to")
            return

        update = context
        if not update.message:
            return

        text = response.text

        # Telegram has a 4096 char limit
        if len(text) > 4090:
            chunks = [text[i : i + 4090] for i in range(0, len(text), 4090)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(text)
