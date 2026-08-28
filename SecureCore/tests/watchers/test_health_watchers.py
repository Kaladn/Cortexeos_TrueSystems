import json
import tempfile
import unittest
from pathlib import Path

from securecore.watchers.health import (
    FusionWatcher,
    ForgeWatcher,
    QueuePressureWatcher,
    RetentionWatcher,
    WorkerHealthWatcher,
    run_health_watchers,
)


class HealthWatcherTests(unittest.TestCase):
    def test_watchers_emit_quiet_clean_receipt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            forge = root / "forge" / "sensor_process"
            forge.mkdir(parents=True)
            (forge / "records.bin").write_bytes(b"records")
            (forge / "records.index.jsonl").write_text("{}\n", encoding="utf-8")
            fusion = root / "fusion"
            fusion.mkdir()
            (fusion / "fusion_blocks.scfb").write_bytes(b"fusion")
            retention = root / "receipts" / "health"
            retention.mkdir(parents=True)
            (retention / "ok.health.json").write_text("{}", encoding="utf-8")

            receipt = run_health_watchers(
                watchers=[
                    ForgeWatcher(root / "forge", expected_streams=["sensor_process"]),
                    FusionWatcher(root / "fusion"),
                    WorkerHealthWatcher({"logger": {"last_seen_seconds": 5, "timeout_seconds": 30}}),
                    QueuePressureWatcher({"forge": {"depth": 1, "max_depth": 10}}),
                    RetentionWatcher(root / "receipts"),
                ],
                receipt_path=root / "health_receipts" / "watcher.json",
            )

            self.assertEqual(receipt["status"], "ok")
            self.assertEqual(receipt["anomaly_count"], 0)
            self.assertTrue(Path(receipt["receipt_path"]).exists())
            saved = json.loads(Path(receipt["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["kind"], "securecore_watcher_health_receipt")

    def test_watcher_reports_anomalies_without_recovery_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            receipt = run_health_watchers(
                watchers=[
                    ForgeWatcher(root / "forge", expected_streams=["sensor_process"]),
                    WorkerHealthWatcher({"logger": {"last_seen_seconds": 99, "timeout_seconds": 30}}),
                    QueuePressureWatcher({"forge": {"depth": 50, "max_depth": 10}}),
                    RetentionWatcher(root / "receipts"),
                ],
                receipt_path=root / "health_receipts" / "watcher.json",
            )

            self.assertEqual(receipt["status"], "alert")
            self.assertGreaterEqual(receipt["anomaly_count"], 3)
            self.assertEqual(receipt["recovery_action_taken"], False)


if __name__ == "__main__":
    unittest.main()
