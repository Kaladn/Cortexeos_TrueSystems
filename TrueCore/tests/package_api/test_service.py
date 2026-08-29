import tempfile
import unittest
from pathlib import Path

from truecore.package_api.contracts import TrueCoreRequest
from truecore.package_api.service import TrueCorePackageService
from truecore.sensors.fusion import build_temporal_fusion_block
from truecore.sensors.fusion_store import FusionBlockStore


class PackageServiceTests(unittest.TestCase):
    def test_status_summary_returns_facts_without_server_or_agents(self):
        service = TrueCorePackageService()

        response = service.handle(
            TrueCoreRequest(
                request_id="req-status",
                caller="anchorworks",
                route="status.summary",
                purpose="read package status",
            )
        )

        self.assertEqual(response.status, "ok")
        self.assertIn("TrueCore package API is available.", response.facts)
        self.assertFalse(response.action_required)
        self.assertFalse(response.approval_required)

    def test_fusion_latest_returns_latest_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FusionBlockStore(Path(tmpdir) / "fusion")
            block = build_temporal_fusion_block(
                block_id="latest-1",
                source_id="truecore.local_shape",
                window_start_utc="2026-05-17T12:00:00.000000Z",
                window_duration_ms=3000,
                events=[],
            )
            store.append(block)
            service = TrueCorePackageService(fusion_store=store)

            response = service.handle(
                TrueCoreRequest(
                    request_id="req-fusion",
                    caller="anchorworks",
                    route="fusion.latest",
                    purpose="read latest fusion",
                )
            )

            self.assertEqual(response.status, "ok")
            self.assertIn("Latest fusion block latest-1 has 0 events.", response.facts)
            self.assertEqual(response.evidence_refs, ["fusion:block:latest-1"])

    def test_unknown_route_returns_rejected_response(self):
        service = TrueCorePackageService()

        response = service.handle(
            TrueCoreRequest(
                request_id="req-bad",
                caller="anchorworks",
                route="agent.launch",
                purpose="forbidden",
            )
        )

        self.assertEqual(response.status, "rejected")
        self.assertFalse(response.facts)
        self.assertTrue(response.warnings)

    def test_report_text_facts_route_returns_tight_report_fact(self):
        service = TrueCorePackageService()

        response = service.handle(
            TrueCoreRequest(
                request_id="req-report",
                caller="anchorworks",
                route="report.text_facts",
                purpose="shape facts report",
                payload={
                    "title": "Logger Health",
                    "facts": ["Fusion block is intact."],
                    "evidence_refs": ["fusion:block:abc"],
                    "warnings": [],
                },
            )
        )

        self.assertEqual(response.status, "ok")
        self.assertIn("Text facts report Logger Health is ready.", response.facts)
        self.assertEqual(response.evidence_refs, ["fusion:block:abc"])

    def test_report_legal_ip_trace_route_validates_evidence_only_report(self):
        service = TrueCorePackageService()

        response = service.handle(
            TrueCoreRequest(
                request_id="req-legal-ip",
                caller="anchorworks",
                route="report.legal_ip_trace",
                purpose="shape legal ip trace report",
                payload={
                    "report_id": "legal-ip-api-1",
                    "title": "Bounded IP Trace Report",
                    "severity": "high",
                    "remote_ip": "203.0.113.10",
                    "observed_endpoint": "203.0.113.10:443/tcp",
                    "facts": ["Connection metadata was observed."],
                    "evidence_refs": ["forge:sensor_network:evt-1"],
                    "source_refs": ["forge:sensor_network"],
                    "evidence_hashes": {"forge:sensor_network:evt-1": "a" * 64},
                    "chain_of_custody": [
                        {
                            "step": "observed",
                            "actor": "truecore.network.diff",
                            "timestamp_utc": "2026-05-17T13:00:00.000000Z",
                            "evidence_ref": "forge:sensor_network:evt-1",
                            "hash": "a" * 64,
                        }
                    ],
                    "containment_plan": {
                        "plan_hash": "b" * 64,
                        "ttl_seconds": 300,
                        "trap_required": True,
                        "log_required": True,
                        "release_required": True,
                        "rollback_required": True,
                    },
                    "release_receipt_ref": "reaper:release:receipt-1",
                    "unknowns": [],
                },
            )
        )

        self.assertEqual(response.status, "ok")
        self.assertIn("Legal IP trace report legal-ip-api-1 is ready.", response.facts)
        self.assertEqual(response.evidence_refs, ["forge:sensor_network:evt-1"])

    def test_policy_check_action_route_reports_approval_required(self):
        service = TrueCorePackageService()

        response = service.handle(
            TrueCoreRequest(
                request_id="req-policy",
                caller="anchorworks",
                route="policy.check_action",
                purpose="check action",
                payload={"route": "firewall.block"},
            )
        )

        self.assertEqual(response.status, "approval_required")
        self.assertTrue(response.approval_required)
        self.assertFalse(response.action_required)
        self.assertIn("firewall.block is not callable", response.warnings[0])

    def test_runtime_status_route_uses_runtime_manager(self):
        class RuntimeManager:
            def status(self):
                return {"status": "ok", "latest_run_id": "run-1"}

        service = TrueCorePackageService(runtime_manager=RuntimeManager())

        response = service.handle(
            TrueCoreRequest(
                request_id="req-runtime-status",
                caller="anchorworks",
                route="runtime.status",
                purpose="read runtime status",
            )
        )

        self.assertEqual(response.status, "ok")
        self.assertEqual(response.evidence_refs, ["truecore:runtime:status"])
        self.assertIn("Latest runtime run run-1 status is ok.", response.facts)

    def test_runtime_verify_route_reports_missing_manager(self):
        service = TrueCorePackageService()

        response = service.handle(
            TrueCoreRequest(
                request_id="req-runtime-verify",
                caller="anchorworks",
                route="runtime.verify_latest",
                purpose="verify latest runtime proof pack",
            )
        )

        self.assertEqual(response.status, "ok")
        self.assertFalse(response.facts)
        self.assertIn("Runtime manager is not configured.", response.warnings)

    def test_runtime_watch_latest_route_uses_runtime_manager(self):
        class RuntimeManager:
            def watch_latest(self):
                return {"status": "alert", "anomaly_count": 2, "receipt_path": "watcher.json"}

        service = TrueCorePackageService(runtime_manager=RuntimeManager())

        response = service.handle(
            TrueCoreRequest(
                request_id="req-runtime-watch",
                caller="anchorworks",
                route="runtime.watch_latest",
                purpose="watch latest runtime health",
            )
        )

        self.assertEqual(response.status, "ok")
        self.assertIn("Latest watcher receipt status is alert with 2 anomalies.", response.facts)
        self.assertEqual(response.evidence_refs, ["truecore:runtime:watcher"])


if __name__ == "__main__":
    unittest.main()
