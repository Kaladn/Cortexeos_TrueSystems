"""Email Sentinel mini-backend."""

from __future__ import annotations

from dataclasses import asdict
from time import time

from securecore.email_sentinel.bridge import HeaderDiffBridge
from securecore.email_sentinel.patterns import AlertPattern, DevicePool
from securecore.email_sentinel.sandbox import EmailSandbox


class EmailSentinelService:
    mode = "header_diff_only"

    def __init__(
        self,
        bridge: HeaderDiffBridge,
        sandbox: EmailSandbox,
        patterns: list[AlertPattern],
        device_pool: DevicePool,
        poll_interval_seconds: int = 10,
    ):
        self.bridge = bridge
        self.sandbox = sandbox
        self.patterns = patterns
        self.device_pool = device_pool
        self.poll_interval_seconds = poll_interval_seconds
        self.last_poll_at: float | None = None
        self.last_error: str | None = None

    @property
    def source_key(self) -> str:
        return f"{self.bridge.source_id}:{self.bridge.mailbox}"

    def status(self) -> dict:
        return {
            "mode": self.mode,
            "source_key": self.source_key,
            "poll_interval_seconds": self.poll_interval_seconds,
            "last_cursor": self.sandbox.load_cursor(self.source_key),
            "last_poll_at": self.last_poll_at,
            "last_error": self.last_error,
            "pattern_count": len(self.patterns),
            "device_count": len(self.device_pool.devices),
            "body_downloads_allowed": False,
            "attachment_fetch_allowed": False,
            "html_render_allowed": False,
        }

    def poll_once(self) -> dict:
        cursor_before = self.sandbox.load_cursor(self.source_key)
        try:
            diff = self.bridge.fetch_since(cursor_before)
            alerts_created = 0
            headers_seen = 0
            matched_patterns: list[str] = []
            for header in diff.headers:
                headers_seen += 1
                self.sandbox.write_header(header)
                for pattern in self.patterns:
                    if not pattern.matches(header):
                        continue
                    recipients = self.device_pool.recipients_for(pattern.severity)
                    if recipients:
                        self.sandbox.write_alert(header, pattern, recipients)
                        alerts_created += 1
                        matched_patterns.append(pattern.pattern_id)
            self.sandbox.save_cursor(self.source_key, diff.cursor)
            self.last_poll_at = time()
            self.last_error = None
            return {
                "source_key": self.source_key,
                "cursor_before": cursor_before,
                "cursor_after": diff.cursor,
                "headers_seen": headers_seen,
                "alerts_created": alerts_created,
                "matched_patterns": matched_patterns,
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "source_key": self.source_key,
                "cursor_before": cursor_before,
                "cursor_after": cursor_before,
                "headers_seen": 0,
                "alerts_created": 0,
                "matched_patterns": [],
                "error": str(exc),
            }

    def pattern_summary(self) -> list[dict]:
        return [asdict(pattern) for pattern in self.patterns]

