"""Reach audit logger — append-only, daily-rotated JSONL.

Logs every message in and every response out. Content logging is opt-in.
Uses gateway.append() when available, falls back to direct file I/O.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from reach.bus.message import ReachMessage, ReachResponse

logger = logging.getLogger(__name__)


class ReachAuditLogger:
    """Append-only JSONL audit writer for Reach traffic."""

    def __init__(self, log_content: bool = False):
        self._log_content = log_content
        self._gateway = None
        self._zone = None
        self._audit_dir = None
        self._init_io()

    def _init_io(self) -> None:
        try:
            from security.gateway import gateway, WriteZone
            self._gateway = gateway
            self._zone = WriteZone.REACH_AUDIT
        except (ImportError, AttributeError):
            pass

        try:
            from security.data_paths import REACH_AUDIT_DIR
            self._audit_dir = REACH_AUDIT_DIR
        except ImportError:
            pass

    def _today_filename(self) -> str:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"reach_audit_{day}.jsonl"

    def _write_line(self, line: str) -> None:
        filename = self._today_filename()

        if self._gateway is not None and self._zone is not None:
            try:
                result = self._gateway.append(
                    caller="system",
                    zone=self._zone,
                    name=filename,
                    line=line,
                    encrypt=False,
                )
                if not getattr(result, "success", True):
                    logger.error("Reach audit gateway write failed: %s",
                                 getattr(result, "error", "unknown"))
            except Exception as e:
                logger.error("Reach audit gateway error: %s", e)
                self._fallback_write(filename, line)
        else:
            self._fallback_write(filename, line)

    def _fallback_write(self, filename: str, line: str) -> None:
        if self._audit_dir is None:
            logger.error("No audit directory configured — audit entry dropped")
            return
        try:
            self._audit_dir.mkdir(parents=True, exist_ok=True)
            filepath = self._audit_dir / filename
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.error("Reach audit fallback write error: %s", e)

    def log_inbound(self, msg: ReachMessage) -> None:
        """Log an inbound message from a channel."""
        entry = {
            "direction": "inbound",
            "message_id": msg.message_id,
            "timestamp_utc": msg.timestamp_utc,
            "channel": msg.channel,
            "channel_user_id": msg.channel_user_id,
            "clearbox_identity": msg.clearbox_identity,
            "paired": msg.paired,
            "session_id": msg.session_id,
        }
        if self._log_content:
            entry["text"] = msg.text
        self._write_line(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))

    def log_outbound(self, resp: ReachResponse) -> None:
        """Log an outbound response to a channel."""
        entry = {
            "direction": "outbound",
            "message_id": resp.message_id,
            "in_reply_to": resp.in_reply_to,
            "timestamp_utc": resp.timestamp_utc,
            "channel": resp.channel,
            "bridge_endpoint": resp.bridge_endpoint,
            "bridge_status": resp.bridge_status,
            "grounded": resp.grounded,
        }
        if self._log_content:
            entry["text"] = resp.text
        self._write_line(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))

    def log_pairing_attempt(
        self,
        channel: str,
        channel_user_id: str,
        code: str,
        success: bool,
        identity: Optional[str] = None,
    ) -> None:
        """Log a pairing attempt."""
        entry = {
            "direction": "pairing",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "channel": channel,
            "channel_user_id": channel_user_id,
            "pairing_code": code,
            "success": success,
            "clearbox_identity": identity,
        }
        self._write_line(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
