"""Append-only sandbox storage for email sentinel observations."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

from securecore.email_sentinel.bridge import MailHeader
from securecore.email_sentinel.patterns import AlertPattern, UserDevice


class EmailSandbox:
    def __init__(self, root: Path):
        self.root = root
        self.cursor_dir = root / "cursors"
        self.header_dir = root / "sanitized_headers"
        self.alert_dir = root / "alert_events"
        self.log_dir = root / "ingest_logs"
        for directory in [self.cursor_dir, self.header_dir, self.alert_dir, self.log_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def load_cursor(self, source_key: str) -> str | None:
        path = self.cursor_dir / f"{_safe_name(source_key)}.cursor"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip() or None

    def save_cursor(self, source_key: str, cursor: str) -> None:
        path = self.cursor_dir / f"{_safe_name(source_key)}.cursor"
        path.write_text(str(cursor), encoding="utf-8")

    def write_header(self, header: MailHeader) -> Path:
        record = {
            "schema_version": "email_sentinel.header.v1",
            "source_shape": "header_only",
            **asdict(header),
            "source_hash": _record_hash(asdict(header)),
            "forbidden_payloads": {
                "message_content_downloaded": False,
                "html_rendered": False,
                "attachments_fetched": False,
                "remote_content_loaded": False,
            },
        }
        path = self.header_dir / f"{_safe_name(header.uid)}-{record['source_hash'][:12]}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_alert(self, header: MailHeader, pattern: AlertPattern, recipients: list[UserDevice]) -> Path:
        record = {
            "schema_version": "email_sentinel.alert.v1",
            "message_uid": header.uid,
            "message_id": header.message_id,
            "mailbox": header.mailbox,
            "received_at": header.received_at,
            "pattern_id": pattern.pattern_id,
            "kind": pattern.kind,
            "severity": pattern.severity,
            "from_address": header.from_address,
            "subject": header.subject,
            "recipients": [asdict(device) for device in recipients],
            "delivery_status": "intent_logged_only",
        }
        digest = _record_hash(record)
        path = self.alert_dir / f"{_safe_name(header.uid)}-{digest[:12]}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return path


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in str(value))[:120] or "item"


def _record_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
