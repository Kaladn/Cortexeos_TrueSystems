import unittest

from securecore.sensors.contracts import (
    SensorEventValidationError,
    build_sensor_event,
    payload_hash,
    validate_sensor_event,
)


class SensorContractTests(unittest.TestCase):
    def test_build_sensor_event_uses_boring_required_shape(self):
        event = build_sensor_event(
            sensor_id="windows.process.diff",
            sensor_class="process",
            host_id="host-local",
            event_type="diff",
            sequence=7,
            cursor={"snapshot": 7},
            subject={"pid": 1234},
            payload={"image": "pwsh.exe", "state": "started"},
            previous_event_hash="prev",
            confidence="observed",
            privacy_level="metadata",
            writer_id="forge.sensor.process",
            batch_id="batch-1",
            batch_index=0,
        )

        self.assertEqual(event["schema_version"], 1)
        self.assertEqual(event["sensor_class"], "process")
        self.assertEqual(event["payload_hash"], payload_hash(event["payload"]))
        self.assertEqual(event["forge_write"]["writer_id"], "forge.sensor.process")
        validate_sensor_event(event)

    def test_validate_sensor_event_rejects_bad_hash(self):
        event = build_sensor_event(
            sensor_id="windows.network.diff",
            sensor_class="network",
            host_id="host-local",
            event_type="diff",
            sequence=1,
            cursor={},
            subject={},
            payload={"remote_ip": "127.0.0.1"},
            previous_event_hash="GENESIS",
            confidence="observed",
            privacy_level="metadata",
            writer_id="forge.sensor.network",
            batch_id="batch-1",
            batch_index=0,
        )
        event["payload_hash"] = "wrong"

        with self.assertRaises(SensorEventValidationError):
            validate_sensor_event(event)

    def test_validate_sensor_event_rejects_unknown_sensor_class(self):
        event = build_sensor_event(
            sensor_id="windows.magic.diff",
            sensor_class="magic",
            host_id="host-local",
            event_type="diff",
            sequence=1,
            cursor={},
            subject={},
            payload={},
            previous_event_hash="GENESIS",
            confidence="observed",
            privacy_level="metadata",
            writer_id="forge.sensor.magic",
            batch_id="batch-1",
            batch_index=0,
        )

        with self.assertRaises(SensorEventValidationError):
            validate_sensor_event(event)

    def test_vision_sensor_is_metadata_state_change_not_video_capture(self):
        event = build_sensor_event(
            sensor_id="truevision.state_change",
            sensor_class="vision",
            host_id="host-local",
            event_type="state_change",
            sequence=2,
            cursor={"frame": 42},
            subject={"source": "screen"},
            payload={
                "state_hash": "abc123",
                "changed_regions": [{"x": 10, "y": 20, "w": 30, "h": 40}],
                "change_magnitude": 0.42,
            },
            previous_event_hash="prev",
            confidence="witnessed",
            privacy_level="metadata",
            writer_id="forge.sensor.vision",
            batch_id="batch-vision",
            batch_index=0,
        )

        self.assertNotIn("frame_bytes", event["payload"])
        self.assertNotIn("video_path", event["payload"])
        validate_sensor_event(event)


if __name__ == "__main__":
    unittest.main()
