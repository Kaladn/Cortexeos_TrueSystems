import tempfile
import unittest

from securecore.forge.reader import ForgeReader
from securecore.sensors.forge_sink import SensorForgeSink
from securecore.truevision.contracts import (
    TrueVisionSCError,
    build_state_change,
    validate_state_change,
)
from securecore.truevision.glyph_extender import build_glyph_extender_summary
from securecore.truevision.forge_adapter import state_change_to_sensor_event
from securecore.truevision.live_capture import TrueVisionSCLiveCapture
from securecore.truevision.workers import (
    TrueVisionSCAnomalyWorker,
    TrueVisionSCForgeWorker,
    TrueVisionSCWorkerSet,
)


class TrueVisionSCEditionTests(unittest.TestCase):
    def test_live_capture_outputs_small_gpu_state_change_record(self):
        capture = TrueVisionSCLiveCapture(
            source_id="gpu.pre_render",
            session_id="session-1",
            grid_size=4,
            capture_backend=lambda: [
                [(255, 255, 255), (255, 255, 255), (255, 255, 255), (255, 255, 255)],
                [(255, 255, 255), (255, 0, 0), (0, 0, 0), (255, 255, 255)],
            ],
            clock=lambda: "2026-05-17T08:00:00.000000Z",
        )

        record = capture.capture_state_change(change_id="state-1")

        self.assertEqual(record["edition"], "truevision_sc_edition")
        self.assertEqual(record["kind"], "truevision_sc_state_change")
        self.assertEqual(record["capture_surface"], "gpu_pre_render")
        self.assertEqual(record["native_geometry"], {"height": 2, "width": 4})
        self.assertEqual(record["grid_shape"], [4, 4])
        self.assertEqual(record["letterbox_cell_count"], 8)
        self.assertEqual(record["distortion_applied"], False)
        self.assertEqual(record["payload_class"], "small_metadata")
        self.assertNotIn("frame", record)
        self.assertNotIn("pixels", record)

    def test_live_capture_can_attach_safe_glyph_summary(self):
        summary = build_glyph_extender_summary(
            [
                {
                    "glyph_id": "glyph-a",
                    "trim_pattern": ["1"],
                    "promotion_status": "approved",
                }
            ],
            [{"component_id": "c1", "bounds": [0, 0, 1, 1], "pattern": ["1"]}],
        )
        capture = TrueVisionSCLiveCapture(
            source_id="gpu.pre_render",
            session_id="session-glyph",
            grid_size=1,
            capture_backend=lambda: [[(0, 0, 0)]],
            glyph_summary_provider=lambda: summary,
            clock=lambda: "2026-05-17T08:00:00.000000Z",
        )

        record = capture.capture_state_change(change_id="glyph-live")

        self.assertEqual(record["glyph_summary"]["known_pattern_count"], 1)
        self.assertFalse(record["glyph_summary"]["text_reconstruction_allowed"])

    def test_state_change_ratio_uses_grid_diff_only(self):
        frames = [
            [[(0, 0, 0), (255, 255, 255)], [(255, 255, 255), (0, 0, 0)]],
            [[(255, 0, 0), (255, 255, 255)], [(255, 255, 255), (0, 0, 0)]],
        ]
        capture = TrueVisionSCLiveCapture(
            source_id="gpu.pre_render",
            session_id="session-1",
            grid_size=2,
            capture_backend=lambda: frames.pop(0),
            clock=lambda: "2026-05-17T08:00:00.000000Z",
        )

        first = capture.capture_state_change(change_id="first")
        second = capture.capture_state_change(change_id="second")

        self.assertEqual(first["change_ratio"], 0.0)
        self.assertEqual(second["changed_cell_count"], 1)
        self.assertEqual(second["total_cell_count"], 4)
        self.assertEqual(second["change_ratio"], 0.25)
        self.assertEqual(second["state_flags"], ["visual_state_changed"])

    def test_rejects_recognition_and_raw_media_fields(self):
        record = build_state_change(
            change_id="bad",
            source_id="gpu.pre_render",
            session_id="session-1",
            observed_at_utc="2026-05-17T08:00:00.000000Z",
            native_geometry={"width": 10, "height": 10},
            grid_shape=[2, 2],
            current_grid_hash="abc",
            previous_grid_hash="def",
            changed_cell_count=1,
            total_cell_count=4,
            letterbox_cell_count=0,
        )
        record["video_path"] = "nope.mp4"

        with self.assertRaises(TrueVisionSCError):
            validate_state_change(record)

        record.pop("video_path")
        record["capture_surface"] = "screen_screenshot"
        with self.assertRaises(TrueVisionSCError):
            validate_state_change(record)

    def test_state_change_allows_metadata_only_glyph_summary(self):
        record = build_state_change(
            change_id="glyph-safe",
            source_id="gpu.pre_render",
            session_id="session-1",
            observed_at_utc="2026-05-17T08:00:00.000000Z",
            native_geometry={"width": 10, "height": 10},
            grid_shape=[2, 2],
            current_grid_hash="abc",
            previous_grid_hash="def",
            changed_cell_count=1,
            total_cell_count=4,
            letterbox_cell_count=0,
            glyph_summary={
                "known_pattern_count": 1,
                "unknown_pattern_count": 0,
                "known_pattern_hashes": ["hash-a"],
                "text_reconstruction_allowed": False,
                "raw_content_stored": False,
                "fact_authority": False,
            },
        )

        validated = validate_state_change(record)

        self.assertEqual(validated["glyph_summary"]["known_pattern_count"], 1)
        self.assertFalse(validated["glyph_summary"]["fact_authority"])

    def test_state_change_writes_to_forge_as_sensor_event(self):
        record = build_state_change(
            change_id="forge-1",
            source_id="gpu.pre_render",
            session_id="session-1",
            observed_at_utc="2026-05-17T08:00:00.000000Z",
            native_geometry={"width": 10, "height": 10},
            grid_shape=[2, 2],
            current_grid_hash="abc",
            previous_grid_hash="def",
            changed_cell_count=1,
            total_cell_count=4,
            letterbox_cell_count=0,
        )
        event = state_change_to_sensor_event(
            record,
            host_id="host-local",
            sequence=0,
            previous_event_hash="GENESIS",
            batch_id="batch-tvsc",
            batch_index=0,
        )

        self.assertEqual(event["sensor_id"], "truevision.state_change")
        self.assertEqual(event["payload"]["edition"], "truevision_sc_edition")

        with tempfile.TemporaryDirectory() as tmpdir:
            sink = SensorForgeSink(tmpdir)
            self.assertEqual(sink.write_events("sensor_vision", [event]), 1)
            reader = ForgeReader(f"{tmpdir}/sensor_vision")
            self.assertTrue(reader.verify()["intact"])
            self.assertEqual(reader.last_record().payload["sensor_event"]["payload"]["payload_class"], "small_metadata")

    def test_worker_set_captures_classifies_and_writes(self):
        frames = [
            [[(0, 0, 0), (255, 255, 255)], [(255, 255, 255), (0, 0, 0)]],
            [[(255, 0, 0), (255, 255, 255)], [(255, 255, 255), (0, 0, 0)]],
        ]
        capture = TrueVisionSCLiveCapture(
            source_id="gpu.pre_render",
            session_id="session-worker",
            grid_size=2,
            capture_backend=lambda: frames.pop(0),
            clock=lambda: "2026-05-17T08:00:00.000000Z",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            workers = TrueVisionSCWorkerSet(
                capture=capture,
                forge_worker=TrueVisionSCForgeWorker(tmpdir, host_id="host-local"),
                anomaly_worker=TrueVisionSCAnomalyWorker(),
            )

            first = workers.step(change_id="one", batch_id="batch-worker")
            second = workers.step(change_id="two", batch_id="batch-worker")

            self.assertEqual(first["anomaly"]["level"], "none")
            self.assertEqual(second["anomaly"]["level"], "medium")
            self.assertTrue(second["anomaly"]["wake_recommended"])
            self.assertNotIn("grid", second)
            self.assertNotIn("frame", str(second).casefold())
            self.assertNotIn("pixels", str(second).casefold())
            self.assertEqual(workers.stats.to_dict()["captured"], 2)
            self.assertEqual(workers.stats.to_dict()["written"], 2)
            reader = ForgeReader(f"{tmpdir}/sensor_vision")
            self.assertTrue(reader.verify()["intact"])
            self.assertEqual(reader.count(), 2)


if __name__ == "__main__":
    unittest.main()
