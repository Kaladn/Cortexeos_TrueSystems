"""Canonical reasoning engine ownership and access."""
from __future__ import annotations

import asyncio
import logging
import re
import threading
from typing import Any


LOGGER = logging.getLogger("clearbox_bridge_server")


class ReasoningService:
    """Single owner of the in-process reasoning engine."""

    def __init__(self) -> None:
        self._engine = None
        self._lock = threading.Lock()

    @property
    def engine(self) -> Any | None:
        return self._engine

    @property
    def is_ready(self) -> bool:
        return self._engine is not None

    def is_available(self) -> bool:
        if self._engine is not None:
            return True
        try:
            from core.reasoning_engine.engine import get_engine  # noqa: F401

            return True
        except Exception:
            return False

    @staticmethod
    def extract_subject(question: str) -> str:
        parts = re.findall(r"[a-z0-9_\-']+", question.lower())
        if not parts:
            return question.strip()

        def _strip_articles(tokens: list[str]) -> list[str]:
            while tokens and tokens[0] in {"the", "a", "an", "this", "that", "these", "those"}:
                tokens.pop(0)
            return tokens

        if len(parts) >= 3 and parts[0] == "what" and parts[1] in {"does", "do", "is", "are"}:
            subject_tokens = parts[2:]
            if parts[1] in {"does", "do"} and subject_tokens and subject_tokens[-1] == "do":
                subject_tokens = subject_tokens[:-1]
            subject_tokens = _strip_articles(subject_tokens)
            if subject_tokens:
                return " ".join(subject_tokens)

        words = _strip_articles(parts[:])
        return words[-1] if words else question.strip()

    def _ensure_engine_sync(self):
        if self._engine is not None:
            return self._engine
        with self._lock:
            if self._engine is None:
                from core.reasoning_engine.engine import get_engine

                engine = get_engine()
                engine.scan_and_update_indexes()
                self._engine = engine
                LOGGER.info("Reasoning engine loaded in-process")
        return self._engine

    async def ensure_engine(self):
        return await asyncio.to_thread(self._ensure_engine_sync)

    async def query_what_does_x_do(self, question: str, topk: int = 8):
        subject = self.extract_subject(question)
        engine = await self.ensure_engine()
        return await asyncio.to_thread(engine.query_what_does_x_do, subject, topk)
