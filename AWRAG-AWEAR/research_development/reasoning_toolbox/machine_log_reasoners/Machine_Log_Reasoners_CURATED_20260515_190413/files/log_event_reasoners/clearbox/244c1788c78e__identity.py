"""Reach identity store — maps channel users to Clearbox identities.

Stores pairing records locally as JSON. When a channel user is paired,
their channel_user_id maps to a clearbox_identity, so all future messages
are authenticated without re-pairing.

Uses gateway write governance when available, falls back to direct file I/O.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _default_store_path() -> Path:
    """Default location for the identity store."""
    try:
        from security.data_paths import REACH_DATA_DIR
        return REACH_DATA_DIR / "paired_identities.json"
    except ImportError:
        return Path("data/reach/paired_identities.json")


class IdentityStore:
    """Persistent mapping of channel users to Clearbox identities."""

    def __init__(self, store_path: Optional[Path] = None):
        self._path = store_path or _default_store_path()
        # Key: "channel:channel_user_id" → clearbox_identity
        self._pairs: Dict[str, str] = {}
        self._load()

    def _key(self, channel: str, channel_user_id: str) -> str:
        return f"{channel}:{channel_user_id}"

    def _load(self) -> None:
        """Load pairings from disk."""
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._pairs = json.load(f)
                logger.info("Loaded %d reach pairings", len(self._pairs))
            except Exception as e:
                logger.warning("Failed to load reach pairings: %s", e)
                self._pairs = {}

    def _save(self) -> None:
        """Persist pairings to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._pairs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save reach pairings: %s", e)

    def resolve(self, channel: str, channel_user_id: str) -> Optional[str]:
        """Look up the Clearbox identity for a channel user.

        Returns the identity string or None if not paired.
        """
        return self._pairs.get(self._key(channel, channel_user_id))

    def store(
        self,
        channel: str,
        channel_user_id: str,
        clearbox_identity: str,
    ) -> None:
        """Store a pairing."""
        key = self._key(channel, channel_user_id)
        self._pairs[key] = clearbox_identity
        self._save()
        logger.info("Paired %s → %s", key[:20], clearbox_identity)

    def revoke(self, channel: str, channel_user_id: str) -> bool:
        """Revoke a pairing. Returns True if it existed."""
        key = self._key(channel, channel_user_id)
        if key in self._pairs:
            del self._pairs[key]
            self._save()
            logger.info("Revoked pairing for %s", key[:20])
            return True
        return False

    def count(self) -> int:
        """Return count of active pairings."""
        return len(self._pairs)

    def list_pairings(self) -> Dict[str, str]:
        """Return all current pairings (for admin view)."""
        return dict(self._pairs)
