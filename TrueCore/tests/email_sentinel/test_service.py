import tempfile
import unittest
from pathlib import Path

from truecore.email_sentinel.bridge import HeaderDiff, MailHeader, StaticHeaderBridge
from truecore.email_sentinel.patterns import AlertPattern, DevicePool, UserDevice
from truecore.email_sentinel.service import EmailSentinelService
from truecore.email_sentinel.sandbox import EmailSandbox


class EmailSentinelServiceTests(unittest.TestCase):
    def test_poll_reads_headers_only_and_advances_cursor(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = StaticHeaderBridge(
                [
                    HeaderDiff(
                        cursor="2",
                        headers=[
                            MailHeader(
                                uid="1",
                                message_id="<bank-1>",
                                mailbox="INBOX",
                                received_at="2026-05-16T10:00:00Z",
                                from_address="alerts@bank.example",
                                from_display="Bank Alerts",
                                reply_to="alerts@bank.example",
                                to_summary=["lee@example.test"],
                                cc_summary=[],
                                subject="Security alert: new login",
                                auth_results="spf=pass dkim=pass dmarc=pass",
                                provider_labels=["inbox"],
                            )
                        ],
                    ),
                    HeaderDiff(cursor="2", headers=[]),
                ]
            )
            sandbox = EmailSandbox(Path(tmp))
            service = EmailSentinelService(
                bridge=bridge,
                sandbox=sandbox,
                patterns=[
                    AlertPattern(
                        pattern_id="bank_login",
                        kind="banking",
                        sender_domains=["bank.example"],
                        subject_contains=["security alert", "login"],
                        require_auth_pass=True,
                        severity="high",
                    )
                ],
                device_pool=DevicePool(
                    devices=[
                        UserDevice(
                            device_id="phone-main",
                            channel="sms",
                            destination="+15555550123",
                            enabled=True,
                            severity_threshold="medium",
                        )
                    ]
                ),
            )

            first = service.poll_once()
            second = service.poll_once()

            self.assertEqual(first["headers_seen"], 1)
            self.assertEqual(first["alerts_created"], 1)
            self.assertEqual(first["cursor_after"], "2")
            self.assertEqual(second["headers_seen"], 0)
            self.assertEqual(second["alerts_created"], 0)
            self.assertEqual(sandbox.load_cursor("static:INBOX"), "2")

            records = list((Path(tmp) / "sanitized_headers").glob("*.json"))
            self.assertEqual(len(records), 1)
            content = records[0].read_text(encoding="utf-8")
            self.assertIn("Security alert: new login", content)
            self.assertNotIn("body", content.lower())
            self.assertNotIn("attachment_bytes", content)

            alerts = list((Path(tmp) / "alert_events").glob("*.json"))
            self.assertEqual(len(alerts), 1)
            alert_content = alerts[0].read_text(encoding="utf-8")
            self.assertIn("phone-main", alert_content)
            self.assertIn("bank_login", alert_content)

    def test_spoofed_auth_fails_required_auth_pattern(self):
        header = MailHeader(
            uid="9",
            message_id="<spoof>",
            mailbox="INBOX",
            received_at="2026-05-16T10:00:00Z",
            from_address="alerts@bank.example",
            from_display="Bank Alerts",
            reply_to="",
            to_summary=[],
            cc_summary=[],
            subject="Security alert: new login",
            auth_results="spf=fail dkim=none dmarc=fail",
            provider_labels=[],
        )
        pattern = AlertPattern(
            pattern_id="bank_login",
            kind="banking",
            sender_domains=["bank.example"],
            subject_contains=["security alert", "login"],
            require_auth_pass=True,
            severity="high",
        )

        self.assertFalse(pattern.matches(header))


if __name__ == "__main__":
    unittest.main()

