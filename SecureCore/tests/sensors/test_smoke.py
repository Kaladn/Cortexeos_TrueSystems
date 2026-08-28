import tempfile
import time
import unittest
from pathlib import Path

from securecore.sensors.contracts import build_sensor_event
from securecore.sensors.smoke import run_logging_smoke


class LoggingSmokeTests(unittest.TestCase):
    def test_smoke_writes_contained_logs_and_forge_records_without_agents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_logging_smoke(
                Path(tmpdir),
                duration_seconds=0.01,
                sleep_seconds=0.0,
                process_snapshots=(
                    {},
                    {10: {"pid": 10, "name": "test.exe", "exe": "", "cmdline": ["test.exe"]}},
                ),
                network_snapshots=(
                    {},
                    {
                        "tcp|127.0.0.1:1|10.0.0.1:443|ESTABLISHED|10": {
                            "protocol": "tcp",
                            "local": "127.0.0.1:1",
                            "remote": "10.0.0.1:443",
                            "status": "ESTABLISHED",
                            "pid": 10,
                        }
                    },
                ),
                window_snapshots=(
                    {},
                    {
                        "100": {
                            "hwnd": "100",
                            "pid": 10,
                            "process_name": "test.exe",
                            "title_hash": "abc123",
                            "title_preview": "Test Window",
                            "rect": {"left": 0, "top": 0, "right": 100, "bottom": 100},
                            "z_order": 0,
                            "visible": True,
                            "occluded": False,
                        }
                    },
                ),
                eventlog_records=[],
            )

            self.assertTrue(report["ok"])
            self.assertEqual(report["agents"], "disabled")
            self.assertEqual(report["camera"], "disabled")
            self.assertEqual(report["microphone"], "disabled")
            self.assertEqual(report["sensor_process_events"], 1)
            self.assertEqual(report["sensor_network_events"], 1)
            self.assertEqual(report["sensor_window_events"], 1)
            self.assertEqual(report["fusion_block_events"], 3)
            self.assertEqual(report["fusion_source_counts"]["process"], 1)
            self.assertEqual(report["fusion_source_counts"]["network"], 1)
            self.assertEqual(report["fusion_source_counts"]["window"], 1)
            self.assertTrue(report["fusion_verify"]["intact"])
            self.assertTrue((Path(tmpdir) / "fusion" / "fusion_blocks.scfb").exists())
            self.assertTrue((Path(tmpdir) / "logs" / "health.jsonl").exists())
            self.assertTrue(report["forge_verify"]["sensor_process"]["intact"])
            self.assertTrue(report["forge_verify"]["sensor_network"]["intact"])
            self.assertTrue(report["forge_verify"]["sensor_window"]["intact"])

    def test_smoke_can_fuse_process_network_eventlog_hid_and_vision(self):
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
            batch_id="batch-smoke",
            batch_index=0,
            observed_at_utc="2026-05-17T11:00:00.000000Z",
        )
        vision_event = build_sensor_event(
            sensor_id="truevision.state_change",
            sensor_class="vision",
            host_id="host-test",
            event_type="state_change",
            sequence=0,
            cursor={"change": 0},
            subject={"source": "gpu.pre_render"},
            payload={"changed_cell_count": 1, "change_ratio": 0.05},
            previous_event_hash="GENESIS",
            confidence="witnessed",
            privacy_level="metadata",
            writer_id="forge.sensor.vision",
            batch_id="batch-smoke",
            batch_index=0,
            observed_at_utc="2026-05-17T11:00:00.000000Z",
        )
        eventlog_record = {
            "log_name": "Microsoft-Windows-Windows Defender/Operational",
            "record_id": 100,
            "provider_name": "Defender",
            "event_id": 1116,
            "level_display_name": "Warning",
            "time_created_utc": "2026-05-17T11:00:00.000000Z",
            "message_hash": "defender-hash",
            "message_preview": "Threat found",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_logging_smoke(
                Path(tmpdir),
                duration_seconds=0.01,
                sleep_seconds=0.0,
                process_snapshots=(
                    {},
                    {10: {"pid": 10, "name": "test.exe", "exe": "", "cmdline": ["test.exe"]}},
                ),
                network_snapshots=(
                    {},
                    {
                        "tcp|127.0.0.1:1|10.0.0.1:443|ESTABLISHED|10": {
                            "protocol": "tcp",
                            "local": "127.0.0.1:1",
                            "remote": "10.0.0.1:443",
                            "status": "ESTABLISHED",
                            "pid": 10,
                        }
                    },
                ),
                eventlog_records=[eventlog_record],
                hid_events=[hid_event],
                vision_events=[vision_event],
            )

            self.assertTrue(report["ok"])
            self.assertEqual(report["sensor_process_events"], 1)
            self.assertEqual(report["sensor_network_events"], 1)
            self.assertEqual(report["sensor_eventlog_events"], 1)
            self.assertEqual(report["sensor_hid_events"], 1)
            self.assertEqual(report["sensor_vision_events"], 1)
            self.assertEqual(report["fusion_block_events"], 5)
            self.assertEqual(report["fusion_source_counts"]["process"], 1)
            self.assertEqual(report["fusion_source_counts"]["network"], 1)
            self.assertEqual(report["fusion_source_counts"]["eventlog"], 1)
            self.assertEqual(report["fusion_source_counts"]["hid"], 1)
            self.assertEqual(report["fusion_source_counts"]["vision"], 1)
            self.assertTrue(report["fusion_verify"]["intact"])
            self.assertTrue(report["forge_verify"]["sensor_hid"]["intact"])
            self.assertTrue(report["forge_verify"]["sensor_vision"]["intact"])

    def test_smoke_uses_one_shared_observation_window_for_live_snapshot_lanes(self):
        sleep_calls = []
        process_rows = [
            {},
            {10: {"pid": 10, "name": "test.exe", "exe": "", "cmdline": ["test.exe"]}},
        ]
        network_rows = [
            {},
            {
                "tcp|127.0.0.1:1|10.0.0.1:443|ESTABLISHED|10": {
                    "protocol": "tcp",
                    "local": "127.0.0.1:1",
                    "remote": "10.0.0.1:443",
                    "status": "ESTABLISHED",
                    "pid": 10,
                }
            },
        ]
        window_rows = [
            {},
            {
                "100": {
                    "hwnd": "100",
                    "pid": 10,
                    "process_name": "test.exe",
                    "title_hash": "abc123",
                    "title_preview": "Test Window",
                    "rect": {"left": 0, "top": 0, "right": 100, "bottom": 100},
                    "z_order": 0,
                    "visible": True,
                    "occluded": False,
                }
            },
        ]

        def next_process_snapshot():
            return process_rows.pop(0)

        def next_network_snapshot():
            return network_rows.pop(0)

        def next_window_snapshot():
            return window_rows.pop(0)

        def record_sleep(seconds):
            sleep_calls.append(seconds)

        with tempfile.TemporaryDirectory() as tmpdir:
            started = time.monotonic()
            report = run_logging_smoke(
                Path(tmpdir),
                duration_seconds=0.12,
                sleep_seconds=0.12,
                include_live_windows=True,
                process_snapshot_func=next_process_snapshot,
                network_snapshot_func=next_network_snapshot,
                window_snapshot_func=next_window_snapshot,
                sleep_func=record_sleep,
            )
            elapsed = time.monotonic() - started

            self.assertTrue(report["ok"])
            self.assertEqual(sleep_calls, [0.12])
            self.assertLess(elapsed, 0.35)
            self.assertLess(report["duration_seconds"], 0.35)
            self.assertEqual(report["observation_window_duration_ms"], 120)
            self.assertEqual(report["sensor_process_events"], 1)
            self.assertEqual(report["sensor_network_events"], 1)
            self.assertEqual(report["sensor_window_events"], 1)


if __name__ == "__main__":
    unittest.main()
