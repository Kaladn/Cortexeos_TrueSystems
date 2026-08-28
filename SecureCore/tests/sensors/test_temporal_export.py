import unittest

from securecore.sensors.contracts import build_sensor_event
from securecore.sensors.temporal_export import sensor_event_to_temporal_row


class TemporalExportTests(unittest.TestCase):
    def test_sensor_event_exports_temporal_checker_row(self):
        event = build_sensor_event(
            sensor_id="windows.process.diff",
            sensor_class="process",
            host_id="local",
            event_type="diff",
            sequence=7,
            cursor={"pid": 42},
            subject={"pid": 42},
            payload={"state": "started", "process": {"name": "pwsh.exe"}},
            previous_event_hash="GENESIS",
            confidence="observed",
            privacy_level="metadata",
            writer_id="forge.sensor.process",
            batch_id="batch",
            batch_index=3,
            observed_at_utc="2026-05-16T19:00:00.000000Z",
        )

        row = sensor_event_to_temporal_row(
            event,
            source_id="windows.process.diff",
            correlation_id="corr-1",
            causal_parents=["parent-1"],
        )

        self.assertEqual(row["source_id"], "windows.process.diff")
        self.assertEqual(row["sensor_id"], "windows.process.diff")
        self.assertEqual(row["writer_id"], "forge.sensor.process")
        self.assertEqual(row["batch_id"], "batch")
        self.assertEqual(row["batch_index"], 3)
        self.assertEqual(row["causal_parents"], ["parent-1"])
        self.assertEqual(row["correlation_id"], "corr-1")
        self.assertEqual(row["payload"], event["payload"])


if __name__ == "__main__":
    unittest.main()
