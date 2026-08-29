"""Mailbox bridges for the Email Sentinel.

Bridges own source access. The service only receives header diffs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from email import message_from_bytes
from email.header import decode_header, make_header
import imaplib
from typing import Iterable, Protocol


@dataclass(frozen=True)
class MailHeader:
    uid: str
    message_id: str
    mailbox: str
    received_at: str
    from_address: str
    from_display: str
    reply_to: str
    to_summary: list[str]
    cc_summary: list[str]
    subject: str
    auth_results: str = ""
    provider_labels: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HeaderDiff:
    cursor: str
    headers: list[MailHeader]


class HeaderDiffBridge(Protocol):
    source_id: str
    mailbox: str

    def fetch_since(self, cursor: str | None) -> HeaderDiff:
        """Return headers newer than cursor without downloading message bodies."""


class StaticHeaderBridge:
    """Deterministic test bridge.

    Each call returns the next configured diff. When diffs are exhausted,
    it returns an empty diff with the last cursor.
    """

    source_id = "static"
    mailbox = "INBOX"

    def __init__(self, diffs: Iterable[HeaderDiff]):
        self._diffs = list(diffs)
        self._index = 0
        self._last_cursor = ""

    def fetch_since(self, cursor: str | None) -> HeaderDiff:
        if self._index >= len(self._diffs):
            return HeaderDiff(cursor=cursor or self._last_cursor, headers=[])
        diff = self._diffs[self._index]
        self._index += 1
        self._last_cursor = diff.cursor
        return diff


class ImapHeaderBridge:
    """Read-only IMAP UID/header bridge.

    This bridge intentionally fetches RFC822 headers only. It does not fetch
    bodies, attachments, HTML, embedded images, or remote content.
    """

    def __init__(self, host: str, username: str, password: str, mailbox: str = "INBOX", ssl: bool = True):
        self.host = host
        self.username = username
        self.password = password
        self.mailbox = mailbox
        self.ssl = ssl
        self.source_id = f"imap:{username}@{host}:{mailbox}"

    def fetch_since(self, cursor: str | None) -> HeaderDiff:
        start_uid = int(cursor or "0") + 1
        client_cls = imaplib.IMAP4_SSL if self.ssl else imaplib.IMAP4
        with client_cls(self.host) as client:
            client.login(self.username, self.password)
            client.select(self.mailbox, readonly=True)
            status, data = client.uid("SEARCH", None, f"UID {start_uid}:*")
            if status != "OK" or not data:
                return HeaderDiff(cursor=cursor or "0", headers=[])
            uids = [uid.decode("ascii") for uid in data[0].split() if uid]
            headers: list[MailHeader] = []
            max_uid = cursor or "0"
            for uid in uids:
                status, fetched = client.uid("FETCH", uid, "(BODY.PEEK[HEADER])")
                if status != "OK" or not fetched:
                    continue
                raw = next((part[1] for part in fetched if isinstance(part, tuple) and len(part) > 1), b"")
                if not raw:
                    continue
                headers.append(self._parse_header(uid, raw))
                if int(uid) > int(max_uid):
                    max_uid = uid
            return HeaderDiff(cursor=max_uid, headers=headers)

    def _parse_header(self, uid: str, raw: bytes) -> MailHeader:
        msg = message_from_bytes(raw)
        from_display, from_address = _split_address(msg.get("From", ""))
        return MailHeader(
            uid=uid,
            message_id=str(msg.get("Message-ID", "")).strip(),
            mailbox=self.mailbox,
            received_at=str(msg.get("Date", "")).strip(),
            from_address=from_address,
            from_display=from_display,
            reply_to=str(msg.get("Reply-To", "")).strip(),
            to_summary=_split_addresses(msg.get("To", "")),
            cc_summary=_split_addresses(msg.get("Cc", "")),
            subject=_decode_header_value(msg.get("Subject", "")),
            auth_results=str(msg.get("Authentication-Results", "")).strip(),
            provider_labels=[],
        )


def _decode_header_value(value: str) -> str:
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return str(value).strip()


def _split_address(value: str) -> tuple[str, str]:
    from email.utils import parseaddr

    display, addr = parseaddr(value)
    return _decode_header_value(display), addr.lower().strip()


def _split_addresses(value: str) -> list[str]:
    from email.utils import getaddresses

    return [addr.lower().strip() for _, addr in getaddresses([value]) if addr]

