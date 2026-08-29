"""Email alert patterns and device-pool notification policy."""

from __future__ import annotations

from dataclasses import dataclass, field

from truecore.email_sentinel.bridge import MailHeader


SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass(frozen=True)
class AlertPattern:
    pattern_id: str
    kind: str
    sender_domains: list[str]
    subject_contains: list[str]
    require_auth_pass: bool = True
    severity: str = "medium"

    def matches(self, header: MailHeader) -> bool:
        domain = header.from_address.rsplit("@", 1)[-1].lower() if "@" in header.from_address else ""
        if self.sender_domains and domain not in {item.lower() for item in self.sender_domains}:
            return False
        subject = header.subject.lower()
        if any(needle.lower() not in subject for needle in self.subject_contains):
            return False
        if self.require_auth_pass and not _auth_passed(header.auth_results):
            return False
        return True


@dataclass(frozen=True)
class UserDevice:
    device_id: str
    channel: str
    destination: str
    enabled: bool
    severity_threshold: str = "medium"

    def accepts(self, severity: str) -> bool:
        if not self.enabled:
            return False
        return SEVERITY_RANK.get(severity, 0) >= SEVERITY_RANK.get(self.severity_threshold, 0)


@dataclass(frozen=True)
class DevicePool:
    devices: list[UserDevice] = field(default_factory=list)

    def recipients_for(self, severity: str) -> list[UserDevice]:
        return [device for device in self.devices if device.accepts(severity)]


def _auth_passed(auth_results: str) -> bool:
    text = auth_results.lower()
    return "spf=pass" in text and ("dkim=pass" in text or "dmarc=pass" in text)

