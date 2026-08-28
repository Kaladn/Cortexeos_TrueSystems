import json
import tempfile
import unittest
from pathlib import Path

from securecore.retention.rolling import (
    RetentionPolicy,
    RetentionWindow,
    RollingRetentionManager,
)
from securecore.sensors.fusion import build_temporal_fusion_block
from securecore.sensors.fusion_store import FusionBlockStore


class RollingRetentionTests(unittest.TestCase):
    def test_clean_two_hour_window_writes_receipts_and_deletes_detail_logs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw = root / "raw"
            raw.mkdir()
            detail_log = raw / "process-detail.jsonl"
            detail_log.write_text("temporary detail\n", encoding="utf-8")
            fusion_store = FusionBlockStore(root / "fusion")
            fusion_store.append(
                build_temporal_fusion_block(
                    block_id="clean-1",
                    source_id="securecore.local_shape",
                    window_start_utc="2026-05-17T05:19:00.000000Z",
                    window_duration_ms=7_200_000,
                    events=[],
                )
            )
            manager = RollingRetentionManager(
                policy=RetentionPolicy(),
                fusion_store=fusion_store,
                managed_roots=[raw],
                receipt_root=root / "receipts",
            )

            report = manager.close_window(
                RetentionWindow(
                    start_utc="2026-05-17T05:19:00.000000Z",
                    end_utc="2026-05-17T07:19:00.000000Z",
                )
            )

            self.assertEqual(report["decision"], "deleted_clean_window")
            self.assertFalse(detail_log.exists())
            self.assertTrue(Path(report["health_receipt_path"]).exists())
            self.assertTrue(Path(report["deletion_receipt_path"]).exists())
            health = json.loads(Path(report["health_receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(health["anomaly_count"], 0)
            self.assertEqual(health["fusion_block_count"], 1)
            deletion = json.loads(Path(report["deletion_receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(deletion["deleted_file_count"], 1)
            self.assertEqual(deletion["backed_up"], False)

    def test_anomaly_window_preserves_logs_and_writes_forensic_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw = root / "raw"
            raw.mkdir()
            detail_log = raw / "vision-detail.bin"
            detail_log.write_bytes(b"temporary detail")
            event = {
                "sensor_id": "truevision.state_change",
                "sensor_class": "vision",
                "event_id": "vision-1",
                "event_type": "state_change",
                "sequence": 1,
                "observed_at_utc": "2026-05-17T06:00:00.000000Z",
                "payload_hash": "abc",
                "payload": {"changed_cell_count": 3, "change_ratio": 0.4, "anomaly_level": "high"},
            }
            fusion_store = FusionBlockStore(root / "fusion")
            fusion_store.append(
                build_temporal_fusion_block(
                    block_id="anomaly-1",
                    source_id="securecore.local_shape",
                    window_start_utc="2026-05-17T05:19:00.000000Z",
                    window_duration_ms=7_200_000,
                    events=[event],
                )
            )
            manager = RollingRetentionManager(
                policy=RetentionPolicy(),
                fusion_store=fusion_store,
                managed_roots=[raw],
                receipt_root=root / "receipts",
            )

            report = manager.close_window(
                RetentionWindow(
                    start_utc="2026-05-17T05:19:00.000000Z",
                    end_utc="2026-05-17T07:19:00.000000Z",
                )
            )

            self.assertEqual(report["decision"], "preserved_anomaly_window")
            self.assertTrue(detail_log.exists())
            self.assertTrue(Path(report["forensic_manifest_path"]).exists())
            manifest = json.loads(Path(report["forensic_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["preservation_reason"], "anomaly_detected")
            self.assertEqual(manifest["leadup_minutes"], 30)
            self.assertEqual(manifest["lookahead_minutes"], 15)

    def test_clean_vision_window_deletes_detail_after_receipt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw = root / "raw"
            raw.mkdir()
            detail_log = raw / "vision-clean-detail.bin"
            detail_log.write_bytes(b"clean visual detail expires")
            event = {
                "sensor_id": "truevision.state_change",
                "sensor_class": "vision",
                "event_id": "vision-clean-1",
                "event_type": "state_change",
                "sequence": 1,
                "observed_at_utc": "2026-05-17T06:00:00.000000Z",
                "payload_hash": "clean-hash",
                "payload": {"changed_cell_count": 0, "change_ratio": 0.0},
            }
            fusion_store = FusionBlockStore(root / "fusion")
            fusion_store.append(
                build_temporal_fusion_block(
                    block_id="vision-clean-1",
                    source_id="securecore.local_shape",
                    window_start_utc="2026-05-17T05:19:00.000000Z",
                    window_duration_ms=7_200_000,
                    events=[event],
                )
            )
            manager = RollingRetentionManager(
                policy=RetentionPolicy(),
                fusion_store=fusion_store,
                managed_roots=[raw],
                receipt_root=root / "receipts",
            )

            report = manager.close_window(
                RetentionWindow(
                    start_utc="2026-05-17T05:19:00.000000Z",
                    end_utc="2026-05-17T07:19:00.000000Z",
                )
            )

            self.assertEqual(report["decision"], "deleted_clean_window")
            self.assertFalse(detail_log.exists())
            self.assertEqual(report["source_counts"]["vision"], 1)
            self.assertEqual(report["anomaly_count"], 0)

    def test_verification_failure_blocks_deletion_without_silent_success(self):
        class BrokenFusionStore:
            def verify(self):
                return {"intact": False, "error": "broken chain"}

            def iter_blocks(self):
                return []

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw = root / "raw"
            raw.mkdir()
            detail_log = raw / "detail.jsonl"
            detail_log.write_text("must remain\n", encoding="utf-8")
            manager = RollingRetentionManager(
                policy=RetentionPolicy(),
                fusion_store=BrokenFusionStore(),
                managed_roots=[raw],
                receipt_root=root / "receipts",
            )

            report = manager.close_window(
                RetentionWindow(
                    start_utc="2026-05-17T05:19:00.000000Z",
                    end_utc="2026-05-17T07:19:00.000000Z",
                )
            )

            self.assertEqual(report["decision"], "blocked_verification_failed")
            self.assertTrue(detail_log.exists())
            self.assertIn("broken chain", report["error"])


if __name__ == "__main__":
    unittest.main()
