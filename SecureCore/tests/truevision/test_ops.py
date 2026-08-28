import tempfile
import unittest

from securecore.forge.reader import ForgeReader
from securecore.truevision.config import TrueVisionRuntimeConfig
from securecore.truevision.ops import run_truevision_ops_once


class TrueVisionOpsTests(unittest.TestCase):
    def test_default_config_is_enabled_and_content_safe(self):
        config = TrueVisionRuntimeConfig()

        self.assertTrue(config.enabled)
        self.assertFalse(config.allow_camera)
        self.assertFalse(config.allow_raw_frames)
        self.assertEqual(config.max_payload_bytes, 4096)

    def test_disabled_ops_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_truevision_ops_once(
                forge_root=tmpdir,
                host_id="host-test",
                config=TrueVisionRuntimeConfig(enabled=False),
                capture_backend=lambda: [[(0, 0, 0)]],
            )

            self.assertEqual(result["status"], "skipped_disabled")
            self.assertEqual(result["written"], 0)
            self.assertEqual(ForgeReader(f"{tmpdir}/sensor_vision").count(), 0)

    def test_enabled_ops_writes_one_vision_event_without_raw_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_truevision_ops_once(
                forge_root=tmpdir,
                host_id="host-test",
                config=TrueVisionRuntimeConfig(
                    enabled=True,
                    session_id="session-ops",
                    grid_size=2,
                ),
                capture_backend=lambda: [
                    [(0, 0, 0), (255, 255, 255)],
                    [(255, 0, 0), (0, 0, 0)],
                ],
            )

            self.assertEqual(result["status"], "written")
            self.assertEqual(result["written"], 1)
            self.assertLessEqual(result["payload_bytes"], 4096)
            reader = ForgeReader(f"{tmpdir}/sensor_vision")
            self.assertTrue(reader.verify()["intact"])
            record_text = str(reader.last_record().payload).casefold()
            self.assertNotIn("raw_frame", record_text)
            self.assertNotIn("frame_bytes", record_text)
            self.assertNotIn("pixels", record_text)


if __name__ == "__main__":
    unittest.main()
