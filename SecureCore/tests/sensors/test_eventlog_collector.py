import tempfile
import unittest
from pathlib import Path

from securecore.sensors.cursors import CursorStore
from securecore.sensors.eventlog_collector import collect_enabled_eventlog_sources, collect_eventlog_source


class EventLogCollectorTests(unittest.TestCase):
    def test_collector_filters_to_interesting_event_ids_and_updates_cursor(self):
        records = [
            {
                "log_name": "Security",
                "record_id": 10,
                "provider_name": "Security",
                "event_id": 4624,
                "level_display_name": "Information",
                "time_created_utc": "2026-05-16T18:00:00.000000Z",
                "message_hash": "a",
                "message_preview": "logon",
            },
            {
                "log_name": "Security",
                "record_id": 11,
                "provider_name": "Security",
                "event_id": 9999,
                "level_display_name": "Information",
                "time_created_utc": "2026-05-16T18:00:01.000000Z",
                "message_hash": "b",
                "message_preview": "noise",
            },
            {
                "log_name": "Security",
                "record_id": 12,
                "provider_name": "Security",
                "event_id": 4625,
                "level_display_name": "Warning",
                "time_created_utc": "2026-05-16T18:00:02.000000Z",
                "message_hash": "c",
                "message_preview": "failed",
            },
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CursorStore(Path(tmpdir) / "cursors.json")
            events = collect_eventlog_source(
                source_id="windows.security",
                source_config={
                    "source_name": "Security",
                    "event_ids_of_interest": [4624, 4625],
                    "mode": "mirror",
                    "forge_destination": "sensor_eventlog",
                    "privacy_level": "metadata",
                },
                cursor_store=store,
                host_id="local",
                records=records,
                batch_id="batch",
            )

            self.assertEqual([event["payload"]["event_id"] for event in events], [4624, 4625])
            self.assertEqual(store.get("windows.security")["last_record_id"], 12)
            self.assertEqual(store.get("windows.security")["last_sequence"], 1)

    def test_collect_enabled_eventlog_sources_skips_disabled_and_non_eventlog_sources(self):
        registry = {
            "windows.security": {
                "source_name": "Security",
                "sensor_class": "security",
                "mode": "mirror",
                "event_ids_of_interest": [4625],
                "forge_destination": "sensor_eventlog",
                "privacy_level": "metadata",
            },
            "windows.system": {
                "source_name": "System",
                "sensor_class": "system",
                "mode": "index",
                "event_ids_of_interest": [],
                "forge_destination": "sensor_eventlog",
                "privacy_level": "metadata",
            },
            "windows.network.diff": {
                "source_name": "network_connection_diff",
                "sensor_class": "network",
                "mode": "index",
                "event_ids_of_interest": [],
                "forge_destination": "sensor_network",
                "privacy_level": "metadata",
            },
            "windows.disabled": {
                "source_name": "Application",
                "sensor_class": "system",
                "mode": "disabled",
                "event_ids_of_interest": [],
                "forge_destination": "sensor_eventlog",
                "privacy_level": "metadata",
            },
        }
        records_by_source = {
            "windows.security": [
                {
                    "log_name": "Security",
                    "record_id": 100,
                    "provider_name": "Security",
                    "event_id": 4625,
                    "level_display_name": "Warning",
                    "time_created_utc": "2026-05-16T18:00:00.000000Z",
                    "message_hash": "a",
                    "message_preview": "failed",
                }
            ],
            "windows.system": [
                {
                    "log_name": "System",
                    "record_id": 50,
                    "provider_name": "Service Control Manager",
                    "event_id": 7036,
                    "level_display_name": "Information",
                    "time_created_utc": "2026-05-16T18:00:00.000000Z",
                    "message_hash": "b",
                    "message_preview": "service changed state",
                }
            ],
            "windows.disabled": [
                {
                    "log_name": "Application",
                    "record_id": 1,
                    "provider_name": "App",
                    "event_id": 1,
                    "level_display_name": "Information",
                    "time_created_utc": "2026-05-16T18:00:00.000000Z",
                    "message_hash": "c",
                    "message_preview": "disabled",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CursorStore(Path(tmpdir) / "cursors.json")
            result = collect_enabled_eventlog_sources(
                registry=registry,
                cursor_store=store,
                host_id="local",
                batch_id="batch",
                records_by_source=records_by_source,
            )

            self.assertEqual(set(result), {"windows.security", "windows.system"})
            self.assertEqual(result["windows.security"][0]["payload"]["event_id"], 4625)
            self.assertEqual(result["windows.system"][0]["payload"]["event_id"], 7036)
            self.assertEqual(store.get("windows.security")["last_record_id"], 100)
            self.assertEqual(store.get("windows.system")["last_record_id"], 50)


if __name__ == "__main__":
    unittest.main()
