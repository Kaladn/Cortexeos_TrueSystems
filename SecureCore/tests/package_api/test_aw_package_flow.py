import tempfile
import unittest
from pathlib import Path

from securecore.package_api.contracts import SecureCoreRequest
from securecore.package_api.service import SecureCorePackageService
from securecore.retention.rolling import RetentionPolicy, RetentionWindow, RollingRetentionManager
from securecore.sensors.contracts import build_sensor_event
from securecore.sensors.fusion_store import FusionBlockStore
from securecore.sensors.smoke import run_logging_smoke


class AnchorWorksPackageFlowTests(unittest.TestCase):
    def test_aw_can_read_health_fusion_and_report_after_clean_ops_window(self):
        hid_event = build_sensor_event(
            sensor_id="securecore.proof_of_life",
            sensor_class="hid",
            host_id="host-test",
            event_type="snapshot",
            sequence=0,
            cursor={"sample": 0},
            subject={"source": "local_hid"},
            payload={"kind": "securecore_proof_of_life", "human_present": True},
            previous_event_hash="GENESIS",
            confidence="observed",
            privacy_level="metadata",
            writer_id="forge.sensor.hid",
            batch_id="batch-e2e",
            batch_index=0,
            observed_at_utc="2026-05-17T12:00:00.000000Z",
        )
        vision_event = build_sensor_event(
            sensor_id="truevision.state_change",
            sensor_class="vision",
            host_id="host-test",
            event_type="state_change",
            sequence=0,
            cursor={"change": 0},
            subject={"source": "gpu.pre_render"},
            payload={"changed_cell_count": 0, "change_ratio": 0.0},
            previous_event_hash="GENESIS",
            confidence="witnessed",
            privacy_level="metadata",
            writer_id="forge.sensor.vision",
            batch_id="batch-e2e",
            batch_index=0,
            observed_at_utc="2026-05-17T12:00:00.000000Z",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw = root / "raw"
            raw.mkdir()
            (raw / "detail.jsonl").write_text("temporary\n", encoding="utf-8")
            smoke = run_logging_smoke(
                root,
                duration_seconds=0.01,
                sleep_seconds=0.0,
                process_snapshots=({}, {}),
                network_snapshots=({}, {}),
                eventlog_records=[],
                hid_events=[hid_event],
                vision_events=[vision_event],
            )
            self.assertTrue(smoke["fusion_verify"]["intact"])

            fusion_store = FusionBlockStore(root / "fusion")
            manager = RollingRetentionManager(
                policy=RetentionPolicy(),
                fusion_store=fusion_store,
                managed_roots=[raw],
                receipt_root=root / "receipts",
            )
            retention = manager.close_window(
                RetentionWindow(
                    start_utc="2026-05-17T00:00:00.000000Z",
                    end_utc="2026-05-18T00:00:00.000000Z",
                )
            )
            self.assertEqual(retention["decision"], "deleted_clean_window")

            service = SecureCorePackageService(
                fusion_store=fusion_store,
                receipt_root=root / "receipts",
            )
            health = service.handle(
                SecureCoreRequest(
                    request_id="aw-health",
                    caller="anchorworks",
                    route="logs.health",
                    purpose="read logger health",
                )
            )
            latest = service.handle(
                SecureCoreRequest(
                    request_id="aw-fusion",
                    caller="anchorworks",
                    route="fusion.latest",
                    purpose="read latest fusion",
                )
            )
            report = service.handle(
                SecureCoreRequest(
                    request_id="aw-report",
                    caller="anchorworks",
                    route="report.text_facts",
                    purpose="shape facts",
                    payload={
                        "title": "SecureCore Ops",
                        "facts": [health.facts[0], latest.facts[0]],
                        "evidence_refs": [*health.evidence_refs, *latest.evidence_refs],
                        "warnings": [],
                    },
                )
            )

            self.assertEqual(health.status, "ok")
            self.assertEqual(latest.status, "ok")
            self.assertEqual(report.status, "ok")
            self.assertFalse(health.action_required)
            self.assertFalse(latest.action_required)
            self.assertFalse(report.action_required)


if __name__ == "__main__":
    unittest.main()
