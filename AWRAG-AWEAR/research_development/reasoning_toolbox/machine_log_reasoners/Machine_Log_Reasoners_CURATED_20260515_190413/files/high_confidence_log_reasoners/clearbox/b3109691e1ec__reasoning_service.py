"""Canonical reasoning engine ownership and access."""
from __future__ import annotations

import asyncio
import logging
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
            from reasoning_engine.engine import ReasoningEngine  # noqa: F401

            return True
        except Exception:
            return False

    @staticmethod
    def extract_subject(question: str) -> str:
        q = question.lower()
        for pattern, keyword in [
            ("what does", "does"),
            ("what do", "do"),
            ("what is", "is"),
            ("what are", "are"),
        ]:
            if pattern in q:
                parts = q.split()
                if keyword in parts:
                    idx = parts.index(keyword)
                    if idx + 1 < len(parts):
                        return parts[idx + 1]
        words = question.lower().replace("?", "").split()
        return words[-1] if words else question

    def _ensure_engine_sync(self):
        if self._engine is not None:
            return self._engine
        with self._lock:
            if self._engine is None:
                from reasoning_engine.engine import ReasoningEngine

                engine = ReasoningEngine()
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
