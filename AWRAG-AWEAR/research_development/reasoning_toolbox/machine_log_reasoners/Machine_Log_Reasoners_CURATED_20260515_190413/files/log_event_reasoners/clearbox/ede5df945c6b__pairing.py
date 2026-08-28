"""Reach pairing manager — 6-character codes for channel authentication.

When an unknown user sends a message through any channel, Reach generates
a 6-character pairing code. The user must enter this code in the local
Clearbox UI to prove they control both the external account and the
local workbench.

Codes expire after 10 minutes. No auto-pair. Ever.
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_CODE_CHARS = string.ascii_uppercase + string.digits
_CODE_LENGTH = 6
_CODE_TTL = timedelta(minutes=10)


class PairingManager:
    """Generate and verify pairing codes for channel users."""

    def __init__(self):
        # code → {channel, channel_user_id, created_at}
        self._pending: Dict[str, Dict] = {}

    def create_code(self, channel: str, channel_user_id: str) -> str:
        """Generate a new pairing code for a channel user.

        If the user already has a pending code, return the existing one
        (don't generate duplicates).
        """
        # Check for existing pending code for this user
        for code, record in self._pending.items():
            if (
                record["channel"] == channel
                and record["channel_user_id"] == channel_user_id
                and not self._is_expired(record)
            ):
                return code

        # Generate new code
        code = "".join(secrets.choice(_CODE_CHARS) for _ in range(_CODE_LENGTH))

        # Ensure uniqueness (extremely unlikely collision but be safe)
        while code in self._pending:
            code = "".join(secrets.choice(_CODE_CHARS) for _ in range(_CODE_LENGTH))

        self._pending[code] = {
            "channel": channel,
            "channel_user_id": channel_user_id,
            "created_at": datetime.now(timezone.utc),
        }

        # Garbage collect expired codes
        self._gc()

        logger.info(
            "Pairing code generated for %s:%s",
            channel,
            channel_user_id[:8],
        )
        return code

    def confirm(self, code: str) -> Optional[Dict]:
        """Confirm a pairing code. Returns the record or None.

        Consumes the code — it cannot be used again.
        """
        self._gc()

        code = code.upper().strip()
        record = self._pending.pop(code, None)

        if record is None:
            logger.warning("Pairing code not found: %s", code)
            return None

        if self._is_expired(record):
            logger.warning("Pairing code expired: %s", code)
            return None

        logger.info(
            "Pairing confirmed for %s:%s",
            record["channel"],
            record["channel_user_id"][:8],
        )
        return record

    def pending_count(self) -> int:
        """Return count of pending (non-expired) pairing codes."""
        self._gc()
        return len(self._pending)

    def _is_expired(self, record: Dict) -> bool:
        return datetime.now(timezone.utc) - record["created_at"] > _CODE_TTL

    def _gc(self) -> None:
        """Remove expired codes."""
        expired = [
            code for code, rec in self._pending.items() if self._is_expired(rec)
        ]
        for code in expired:
            del self._pending[code]
