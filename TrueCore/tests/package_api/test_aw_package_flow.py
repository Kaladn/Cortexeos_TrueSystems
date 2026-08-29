import tempfile
import unittest
from pathlib import Path

from truecore.package_api.contracts import TrueCoreRequest
from truecore.package_api.service import TrueCorePackageService
from truecore.retention.rolling import RetentionPolicy, RetentionWindow, RollingRetentionManager
from truecore.sensors.contracts import build_sensor_event
from truecore.sensors.fusion import build_temporal_fusion_block
from truecore.sensors.fusion_store import FusionBlockStore


class AnchorWorksPackageFlowTests(unittest.TestCase):
    def test_aw_can_read_health_fusion_and_report_after_clean_ops_window(self):
        hid_event = build_sensor_event(
            sensor_id="truecore.proof_of_life",
            sensor_class="hid",
            host_id="host-test",
            event_type="snapshot",
            sequence=0,
            cursor={"sample": 0},
            subject={"source": "local_hid"},
            payload={"kind": "truecore_proof_of_life", "human_present": True},
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
            fusion_block = build_temporal_fusion_block(
                block_id="fusion-batch-e2e",
                source_id="truecore.package_flow_test",
                window_start_utc="2026-05-17T12:00:00.000000Z",
                window_duration_ms=10,
                events=[hid_event, vision_event],
            )
            fusion_store = FusionBlockStore(root / "fusion")
            fusion_store.append(fusion_block)
            self.assertTrue(fusion_store.verify()["intact"])
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

            service = TrueCorePackageService(
                fusion_store=fusion_store,
                receipt_root=root / "receipts",
            )
            health = service.handle(
                TrueCoreRequest(
                    request_id="aw-health",
                    caller="anchorworks",
                    route="logs.health",
                    purpose="read logger health",
                )
            )
            latest = service.handle(
                TrueCoreRequest(
                    request_id="aw-fusion",
                    caller="anchorworks",
                    route="fusion.latest",
                    purpose="read latest fusion",
                )
            )
            report = service.handle(
                TrueCoreRequest(
                    request_id="aw-report",
                    caller="anchorworks",
                    route="report.text_facts",
                    purpose="shape facts",
                    payload={
                        "title": "TrueCore Ops",
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
