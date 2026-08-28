"""Ephemeral OpenAI API key sessions for SecureCore chat.

Keys live in process memory only. Public session payloads intentionally expose
only non-secret metadata so routes, receipts, and chat rows cannot persist the
operator's API key by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
import secrets
from threading import RLock
from typing import Any


DEFAULT_OPENAI_MODEL = os.environ.get("SECURECORE_OPENAI_DEFAULT_MODEL", "gpt-4.1-mini")


@dataclass
class OpenAIKeySession:
    user_id: str
    api_key: str
    model: str
    session_id: str
    key_fingerprint: str
    created_at_utc: str


class OpenAIKeyVault:
    """Small in-memory key vault keyed by authenticated SecureCore identity."""

    def __init__(self, *, default_model: str = DEFAULT_OPENAI_MODEL) -> None:
        self._default_model = default_model
        self._sessions: dict[str, OpenAIKeySession] = {}
        self._lock = RLock()

    def login(self, *, user_id: str, api_key: str, model: str | None = None) -> dict[str, Any]:
        cleaned_key = str(api_key or "").strip()
        if not cleaned_key:
            raise ValueError("OpenAI API key required")
        cleaned_user_id = str(user_id or "").strip()
        if not cleaned_user_id:
            raise ValueError("user_id required")
        cleaned_model = str(model or "").strip() or self._default_model
        fingerprint = hashlib.sha256(cleaned_key.encode("utf-8")).hexdigest()[:12]
        session = OpenAIKeySession(
            user_id=cleaned_user_id,
            api_key=cleaned_key,
            model=cleaned_model,
            session_id=f"openai_sess_{secrets.token_hex(12)}",
            key_fingerprint=fingerprint,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._sessions[cleaned_user_id] = session
        return self._public_status(session)

    def status(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            session = self._sessions.get(str(user_id))
        if session is None:
            return {"active": False}
        return self._public_status(session)

    def has_session(self, user_id: str | None) -> bool:
        if not user_id:
            return False
        with self._lock:
            return str(user_id) in self._sessions

    def get_api_key(self, user_id: str) -> str | None:
        with self._lock:
            session = self._sessions.get(str(user_id))
        return session.api_key if session is not None else None

    def get_session(self, user_id: str) -> OpenAIKeySession | None:
        with self._lock:
            return self._sessions.get(str(user_id))

    def logout(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            self._sessions.pop(str(user_id), None)
        return {"active": False}

    @staticmethod
    def _public_status(session: OpenAIKeySession) -> dict[str, Any]:
        return {
            "active": True,
            "model": session.model,
            "session_id": session.session_id,
            "key_fingerprint": session.key_fingerprint,
            "created_at_utc": session.created_at_utc,
            "persistence": "process_memory_only",
        }
