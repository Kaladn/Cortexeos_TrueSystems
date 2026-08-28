import unittest

from securecore.sensors.windows_readers import diff_open_windows, open_window_rows_to_events


class WindowReaderTests(unittest.TestCase):
    def test_open_window_rows_convert_to_sensor_events(self):
        rows = [
            {
                "hwnd": "100",
                "pid": 10,
                "process_name": "Code.exe",
                "title_hash": "abc",
                "title_preview": "SecureCore",
                "rect": {"left": 0, "top": 0, "right": 100, "bottom": 100},
                "z_order": 0,
                "visible": True,
                "occluded": False,
            }
        ]

        events = open_window_rows_to_events(
            rows,
            host_id="host-test",
            sequence_start=0,
            previous_event_hash="GENESIS",
            batch_id="batch-window",
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["sensor_id"], "windows.open_window.snapshot")
        self.assertEqual(events[0]["sensor_class"], "window")
        self.assertEqual(events[0]["payload"]["windows"][0]["process_name"], "Code.exe")
        self.assertNotIn("title", events[0]["payload"]["windows"][0])
        self.assertIn("title_hash", events[0]["payload"]["windows"][0])

    def test_diff_open_windows_reports_open_close_and_change(self):
        previous = {
            "100": {
                "hwnd": "100",
                "pid": 10,
                "process_name": "Code.exe",
                "title_hash": "abc",
                "rect": {"left": 0, "top": 0, "right": 100, "bottom": 100},
                "z_order": 0,
                "visible": True,
                "occluded": False,
            },
            "200": {
                "hwnd": "200",
                "pid": 20,
                "process_name": "old.exe",
                "title_hash": "old",
                "rect": {"left": 0, "top": 0, "right": 10, "bottom": 10},
                "z_order": 1,
                "visible": True,
                "occluded": False,
            },
        }
        current = {
            "100": {
                "hwnd": "100",
                "pid": 10,
                "process_name": "Code.exe",
                "title_hash": "def",
                "rect": {"left": 0, "top": 0, "right": 100, "bottom": 100},
                "z_order": 0,
                "visible": True,
                "occluded": True,
            },
            "300": {
                "hwnd": "300",
                "pid": 30,
                "process_name": "new.exe",
                "title_hash": "new",
                "rect": {"left": 0, "top": 0, "right": 10, "bottom": 10},
                "z_order": 1,
                "visible": True,
                "occluded": False,
            },
        }

        events = diff_open_windows(
            previous,
            current,
            host_id="host-test",
            sequence_start=0,
            previous_event_hash="GENESIS",
            batch_id="batch-window",
        )
        states = [event["payload"]["state"] for event in events]

        self.assertEqual(states, ["changed", "closed", "opened"])
        self.assertEqual(events[0]["subject"]["hwnd"], "100")


if __name__ == "__main__":
    unittest.main()
