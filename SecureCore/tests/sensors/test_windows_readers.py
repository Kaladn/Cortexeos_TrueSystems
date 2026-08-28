import unittest

from securecore.sensors.contracts import validate_sensor_event
from securecore.sensors.windows_readers import (
    diff_network_connections,
    diff_processes,
    eventlog_records_to_events,
)


class WindowsReaderDiffTests(unittest.TestCase):
    def test_process_diff_emits_started_and_stopped_events(self):
        previous = {
            10: {"pid": 10, "name": "old.exe", "exe": "C:\\old.exe", "cmdline": ["old.exe"]},
            20: {"pid": 20, "name": "same.exe", "exe": "C:\\same.exe", "cmdline": ["same.exe"]},
        }
        current = {
            20: {"pid": 20, "name": "same.exe", "exe": "C:\\same.exe", "cmdline": ["same.exe"]},
            30: {"pid": 30, "name": "new.exe", "exe": "C:\\new.exe", "cmdline": ["new.exe"]},
        }

        events = diff_processes(
            previous,
            current,
            host_id="host-local",
            sequence_start=5,
            previous_event_hash="prev",
            batch_id="batch-process",
        )

        self.assertEqual([event["event_type"] for event in events], ["diff", "diff"])
        self.assertEqual([event["payload"]["state"] for event in events], ["started", "stopped"])
        self.assertEqual([event["sequence"] for event in events], [5, 6])
        for event in events:
            self.assertEqual(event["sensor_id"], "windows.process.diff")
            validate_sensor_event(event)

    def test_network_diff_emits_opened_and_closed_events(self):
        previous = {
            "tcp|127.0.0.1:1|10.0.0.1:443|ESTABLISHED|100": {
                "protocol": "tcp",
                "local": "127.0.0.1:1",
                "remote": "10.0.0.1:443",
                "status": "ESTABLISHED",
                "pid": 100,
            }
        }
        current = {
            "tcp|127.0.0.1:2|10.0.0.2:443|ESTABLISHED|200": {
                "protocol": "tcp",
                "local": "127.0.0.1:2",
                "remote": "10.0.0.2:443",
                "status": "ESTABLISHED",
                "pid": 200,
            }
        }

        events = diff_network_connections(
            previous,
            current,
            host_id="host-local",
            sequence_start=9,
            previous_event_hash="prev",
            batch_id="batch-network",
        )

        self.assertEqual([event["payload"]["state"] for event in events], ["opened", "closed"])
        self.assertEqual([event["sequence"] for event in events], [9, 10])
        for event in events:
            self.assertEqual(event["sensor_id"], "windows.network.diff")
            validate_sensor_event(event)

    def test_eventlog_records_become_metadata_sensor_events(self):
        records = [
            {
                "log_name": "Microsoft-Windows-Windows Defender/Operational",
                "record_id": 100,
                "provider_name": "Microsoft-Windows-Windows Defender",
                "event_id": 1116,
                "level_display_name": "Warning",
                "time_created_utc": "2026-05-16T18:00:00.000000Z",
                "message_hash": "abc123",
                "message_preview": "Threat detected",
            },
            {
                "log_name": "Microsoft-Windows-PowerShell/Operational",
                "record_id": 200,
                "provider_name": "Microsoft-Windows-PowerShell",
                "event_id": 4104,
                "level_display_name": "Information",
                "time_created_utc": "2026-05-16T18:00:01.000000Z",
                "message_hash": "def456",
                "message_preview": "Script block logging",
            },
        ]

        events = eventlog_records_to_events(
            records,
            host_id="host-local",
            sequence_start=30,
            previous_event_hash="prev",
            batch_id="batch-eventlog",
        )

        self.assertEqual([event["sequence"] for event in events], [30, 31])
        self.assertEqual(events[0]["sensor_id"], "windows.eventlog.Microsoft-Windows-Windows_Defender.Operational")
        self.assertEqual(events[1]["sensor_id"], "windows.eventlog.Microsoft-Windows-PowerShell.Operational")
        self.assertEqual(events[0]["payload"]["record_id"], 100)
        self.assertNotIn("message", events[0]["payload"])
        for event in events:
            self.assertEqual(event["sensor_class"], "eventlog")
            self.assertEqual(event["privacy_level"], "metadata")
            validate_sensor_event(event)


if __name__ == "__main__":
    unittest.main()
