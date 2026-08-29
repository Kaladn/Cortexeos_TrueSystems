import tempfile
import unittest
from pathlib import Path

from truecore.sensors.cursors import CursorStore


class CursorStoreTests(unittest.TestCase):
    def test_cursor_store_round_trips_source_cursor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CursorStore(Path(tmpdir) / "cursors.json")
            store.update("windows.security", {"last_record_id": 123, "last_payload_hash": "abc"})

            reloaded = CursorStore(Path(tmpdir) / "cursors.json")
            self.assertEqual(reloaded.get("windows.security")["last_record_id"], 123)
            self.assertRegex(
                reloaded.get("windows.security")["updated_at_utc"],
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$",
            )

    def test_cursor_store_returns_empty_cursor_for_unknown_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CursorStore(Path(tmpdir) / "cursors.json")
            self.assertEqual(store.get("missing"), {})


if __name__ == "__main__":
    unittest.main()
