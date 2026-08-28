import tempfile
import unittest

from securecore.forge.reader import ForgeReader
from securecore.truevision.pol import (
    CameraPresenceSnapshot,
    LocalHIDSnapshot,
    ProofOfLifeWorker,
    build_proof_of_life_event,
)


class FakeHIDProbe:
    def __init__(self, recent=True):
        self.recent = recent

    def sample(self, *, recent_threshold_seconds=15.0):
        return LocalHIDSnapshot(
            available=True,
            idle_seconds=1.5 if self.recent else 100.0,
            local_hid_recent=self.recent,
            foreground_process="Code.exe",
        )


class FakeCameraProbe:
    def __init__(self, available=False, present=False):
        self.available = available
        self.present = present

    def sample(self):
        return CameraPresenceSnapshot(
            available=self.available,
            human_present=self.present,
            confidence=0.75 if self.present else 0.25,
            method="fake",
        )


class ProofOfLifeWorkerTests(unittest.TestCase):
    def test_pol_event_builder_does_not_write_and_preserves_metadata_boundary(self):
        event = build_proof_of_life_event(
            host_id="host-test",
            sequence=0,
            previous_event_hash="GENESIS",
            batch_id="batch-pol",
            batch_index=0,
            observed_at_utc="2026-05-17T09:00:00.000000Z",
            hid=LocalHIDSnapshot(
                available=True,
                idle_seconds=1.0,
                local_hid_recent=True,
                foreground_process="Code.exe",
            ),
            camera=CameraPresenceSnapshot(
                available=False,
                human_present=False,
                confidence=0.0,
                method="camera_unavailable",
            ),
        )

        self.assertEqual(event["sensor_id"], "securecore.proof_of_life")
        self.assertEqual(event["sensor_class"], "hid")
        self.assertTrue(event["payload"]["human_present"])
        self.assertFalse(event["payload"]["raw_content_stored"])
        self.assertNotIn("keystroke", str(event).casefold())
        self.assertNotIn("frame", str(event).casefold())

    def test_pol_uses_hid_when_camera_unavailable_and_writes_forge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            worker = ProofOfLifeWorker(
                forge_root=tmpdir,
                host_id="host-test",
                hid_probe=FakeHIDProbe(recent=True),
                camera_probe=FakeCameraProbe(available=False),
                clock=lambda: "2026-05-17T09:00:00.000000Z",
            )
            result = worker.sample_once(batch_id="batch-pol")

            payload = result["payload"]
            self.assertEqual(payload["source"], "local_hid")
            self.assertTrue(payload["human_present"])
            self.assertFalse(payload["raw_content_stored"])
            self.assertNotIn("frame", str(payload).casefold())
            self.assertNotIn("keystroke", str(payload).casefold())
            reader = ForgeReader(f"{tmpdir}/sensor_hid")
            self.assertTrue(reader.verify()["intact"])
            self.assertEqual(reader.count(), 1)

    def test_pol_prefers_camera_presence_metadata_when_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            worker = ProofOfLifeWorker(
                forge_root=tmpdir,
                host_id="host-test",
                hid_probe=FakeHIDProbe(recent=False),
                camera_probe=FakeCameraProbe(available=True, present=True),
                clock=lambda: "2026-05-17T09:00:00.000000Z",
            )
            result = worker.sample_once(batch_id="batch-pol")

            self.assertEqual(result["payload"]["source"], "camera")
            self.assertTrue(result["payload"]["human_present"])
            self.assertEqual(result["payload"]["camera"]["method"], "fake")

    def test_pol_repeated_samples_keep_forge_chain_intact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            worker = ProofOfLifeWorker(
                forge_root=tmpdir,
                host_id="host-test",
                hid_probe=FakeHIDProbe(recent=True),
                camera_probe=FakeCameraProbe(available=False),
                clock=lambda: "2026-05-17T09:00:00.000000Z",
            )
            worker.sample_once(batch_id="batch-pol")
            worker.sample_once(batch_id="batch-pol")

            verify = ForgeReader(f"{tmpdir}/sensor_hid").verify()
            self.assertTrue(verify["intact"])
            self.assertEqual(verify["total_records"], 2)
            self.assertEqual(verify["last_sequence"], 1)


if __name__ == "__main__":
    unittest.main()
