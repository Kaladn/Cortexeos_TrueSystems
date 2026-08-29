import unittest

from truecore.incidents.window_builder import build_incident_window


class IncidentWindowBuilderTests(unittest.TestCase):
    def test_window_selects_events_around_trigger_and_extracts_entities(self):
        rows = [
            {
                "event_id": "before",
                "observed_at_utc": "2026-05-16T19:00:00.000000Z",
                "payload": {"remote_ip": "10.0.0.1"},
            },
            {
                "event_id": "trigger",
                "observed_at_utc": "2026-05-16T19:00:10.000000Z",
                "payload": {"process": {"name": "pwsh.exe"}, "user": "lee"},
            },
            {
                "event_id": "after",
                "observed_at_utc": "2026-05-16T19:00:15.000000Z",
                "payload": {"file": "C:/temp/a.ps1"},
            },
            {
                "event_id": "outside",
                "observed_at_utc": "2026-05-16T19:02:00.000000Z",
                "payload": {"device": "late"},
            },
        ]

        window = build_incident_window(
            "trigger",
            rows,
            before_seconds=20,
            after_seconds=20,
        )

        self.assertEqual([row["event_id"] for row in window["timeline"]], ["before", "trigger", "after"])
        self.assertIn("pwsh.exe", window["entities"]["processes"])
        self.assertIn("10.0.0.1", window["entities"]["remote_ips"])
        self.assertIn("lee", window["entities"]["users"])
        self.assertIn("C:/temp/a.ps1", window["entities"]["files"])


if __name__ == "__main__":
    unittest.main()
