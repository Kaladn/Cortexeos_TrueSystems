import json
import tempfile
import unittest
from pathlib import Path

from truecore.performance.logger import (
    PerformanceLogger,
    build_performance_receipt,
    validate_performance_receipt,
)
from truecore.time import is_canonical_utc_timestamp


class PerformanceLoggerTests(unittest.TestCase):
    def test_performance_receipt_tracks_cost_without_truth_or_behavior_authority(self):
        receipt = build_performance_receipt(
            algorithm_id="fusion.block.build",
            run_id="run-1",
            input_size=1000,
            duration_ms=250.5,
            cpu_ms=190.0,
            memory_peak_mb=84.25,
            disk_read_mb=1.5,
            disk_write_mb=0.75,
            forge_write_latency_ms=12.5,
            fusion_block_build_ms=44.0,
            queue_wait_ms=5.0,
            model_inference_latency_ms=0.0,
            gpu_vram_peak_mb=None,
            energy_estimate_wh=None,
            records_processed=1000,
            blocks_processed=4,
            error_count=0,
        )

        validated = validate_performance_receipt(receipt)

        self.assertEqual(validated["kind"], "truecore_performance_receipt")
        self.assertTrue(is_canonical_utc_timestamp(validated["created_at_utc"]))
        self.assertEqual(validated["truth_authority"], False)
        self.assertEqual(validated["behavior_change_authority"], False)
        self.assertEqual(validated["policy_approval_authority"], False)
        self.assertEqual(validated["events_per_second"], 3992.016)
        self.assertEqual(validated["blocks_per_second"], 15.968)
        self.assertEqual(validated["bottleneck_hint"], "cpu")

    def test_performance_logger_writes_receipts_to_cost_lane(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PerformanceLogger(Path(tmpdir) / "performance")
            receipt = logger.write_receipt(
                algorithm_id="eventlog.collect",
                run_id="run-2",
                input_size=50,
                duration_ms=1000.0,
                cpu_ms=100.0,
                memory_peak_mb=20.0,
                disk_write_mb=0.1,
                records_processed=50,
            )

            receipt_path = Path(receipt["receipt_path"])
            self.assertTrue(receipt_path.exists())
            self.assertIn("performance", receipt_path.parts)
            saved = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["algorithm_id"], "eventlog.collect")
            self.assertEqual(saved["events_per_second"], 50.0)

    def test_performance_receipt_rejects_authority_or_negative_costs(self):
        receipt = build_performance_receipt(
            algorithm_id="runner.agent",
            run_id="run-3",
            input_size=1,
            duration_ms=1.0,
        )

        receipt["truth_authority"] = True
        with self.assertRaises(ValueError):
            validate_performance_receipt(receipt)

        receipt["truth_authority"] = False
        receipt["duration_ms"] = -1.0
        with self.assertRaises(ValueError):
            validate_performance_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
