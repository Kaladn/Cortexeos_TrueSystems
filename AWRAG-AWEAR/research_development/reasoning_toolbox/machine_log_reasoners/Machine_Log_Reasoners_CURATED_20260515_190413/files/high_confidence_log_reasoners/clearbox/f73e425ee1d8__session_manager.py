"""Session pointer-state manager — governed by the Reader-Writer Gateway.

Persists volatile session state so server restarts don't lose context:
    - active_model            (which GGUF model is loaded)
    - current_conversation_id (UUID of current chat conversation)
    - last_map_run_id         (timestamp-id of last bridge map run)
    - ui_state                (arbitrary UI pointer state)

All writes go through WriteZone.SESSIONS via gateway.write("system", ...).
All reads go through gateway.read(WriteZone.SESSIONS, ...).

Session state is plaintext JSON at rest and every mutation is audited.

Usage:
    from scripts.session_manager import session

    # Save after model load
    session.set("active_model", "qwen2.5:7b")

    # Save after new conversation
    session.set("current_conversation_id", str(uuid))

    # Restore on startup
    model = session.get("active_model")

    # Bulk save (atomic — single gateway write)
    session.update({"active_model": "qwen2.5:7b", "conversation_id": str(uuid)})
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from security.gateway import gateway, WriteZone

# ── Constants ─────────────────────────────────────────────────

_SESSION_FILE = "session_pointer.json"   # Single file, atomic replace
_VERSION = 2                              # Schema version — bump on breaking change


# ── Session Manager ───────────────────────────────────────────


class SessionManager:
    """Governed pointer-state persistence.

    In-memory cache backed by WriteZone.SESSIONS on disk.
    Thread-safe at the gateway level (gateway serializes writes).
    """

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._loaded = False

    # ── Public API ────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Read a session key. Lazy-loads from disk on first access."""
        self._ensure_loaded()
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a single session key and persist immediately."""
        self._ensure_loaded()
        self._cache[key] = value
        self._persist()

    def update(self, data: dict[str, Any]) -> None:
        """Bulk-update multiple keys in a single atomic write."""
        self._ensure_loaded()
        self._cache.update(data)
        self._persist()

    def delete(self, key: str) -> None:
        """Remove a session key and persist."""
        self._ensure_loaded()
        self._cache.pop(key, None)
        self._persist()

    def clear(self) -> None:
        """Clear all session state and persist the empty state."""
        self._cache.clear()
        self._loaded = True
        self._persist()

    def all(self) -> dict[str, Any]:
        """Return a copy of all session state."""
        self._ensure_loaded()
        return dict(self._cache)

    def refresh(self) -> None:
        """Force re-read from disk (useful after external changes)."""
        self._loaded = False
        self._ensure_loaded()

    # ── Internal ──────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        """Lazy-load session state from governed storage on first access."""
        if self._loaded:
            return
        raw = gateway.read(WriteZone.SESSIONS, _SESSION_FILE)
        if raw is not None:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    # Strip envelope, keep payload
                    self._cache = data.get("state", data)
                else:
                    self._cache = {}
            except json.JSONDecodeError:
                self._cache = {}
        else:
            self._cache = {}
        self._loaded = True

    def _persist(self) -> None:
        """Write the full session state to disk through the gateway."""
        envelope = {
            "version": _VERSION,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "state": self._cache,
        }
        content = json.dumps(envelope, indent=2, ensure_ascii=False)
        result = gateway.write(
            "system",
            WriteZone.SESSIONS,
            _SESSION_FILE,
            content,
            encrypt=True,
        )
        if not result.success:
            import sys
            print(
                f"⚠️  Session persist failed: {result.error}",
                file=sys.stderr,
            )


# ── Module-level singleton ────────────────────────────────────
session = SessionManager()
