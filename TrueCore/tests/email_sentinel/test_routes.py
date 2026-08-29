import tempfile
import unittest
from pathlib import Path

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from truecore.email_sentinel.bridge import HeaderDiff, MailHeader, StaticHeaderBridge
from truecore.email_sentinel.patterns import AlertPattern, DevicePool, UserDevice
from truecore.email_sentinel.routes import email_sentinel_bp, init_email_sentinel_routes
from truecore.email_sentinel.sandbox import EmailSandbox
from truecore.email_sentinel.service import EmailSentinelService


class EmailSentinelRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = Flask(__name__)
        self.app.config["JWT_SECRET_KEY"] = "test-secret-test-secret-test-secret"
        JWTManager(self.app)
        bridge = StaticHeaderBridge(
            [
                HeaderDiff(
                    cursor="1",
                    headers=[
                        MailHeader(
                            uid="1",
                            message_id="<sec-1>",
                            mailbox="INBOX",
                            received_at="2026-05-16T10:00:00Z",
                            from_address="security@vendor.example",
                            from_display="Vendor Security",
                            reply_to="",
                            to_summary=["lee@example.test"],
                            cc_summary=[],
                            subject="Account security alert",
                            auth_results="spf=pass dkim=pass dmarc=pass",
                            provider_labels=[],
                        )
                    ],
                )
            ]
        )
        service = EmailSentinelService(
            bridge=bridge,
            sandbox=EmailSandbox(Path(self.tmp.name)),
            patterns=[
                AlertPattern(
                    pattern_id="security_alert",
                    kind="security",
                    sender_domains=["vendor.example"],
                    subject_contains=["security alert"],
                    require_auth_pass=True,
                    severity="high",
                )
            ],
            device_pool=DevicePool(
                [
                    UserDevice(
                        device_id="phone-main",
                        channel="sms",
                        destination="+15555550123",
                        enabled=True,
                        severity_threshold="low",
                    )
                ]
            ),
        )
        init_email_sentinel_routes(service)
        self.app.register_blueprint(email_sentinel_bp)
        self.client = self.app.test_client()
        with self.app.app_context():
            self.token = create_access_token(identity="1", additional_claims={"role": "admin"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_requires_auth(self):
        response = self.client.get("/api/email-sentinel/status")
        self.assertEqual(response.status_code, 401)

    def test_status_and_poll(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        status = self.client.get("/api/email-sentinel/status", headers=headers)
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.get_json()["ok"])
        self.assertEqual(status.get_json()["mode"], "header_diff_only")

        poll = self.client.post("/api/email-sentinel/poll-once", headers=headers)
        self.assertEqual(poll.status_code, 200)
        payload = poll.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["headers_seen"], 1)
        self.assertEqual(payload["result"]["alerts_created"], 1)


if __name__ == "__main__":
    unittest.main()

