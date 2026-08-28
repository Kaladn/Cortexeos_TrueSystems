import unittest

from securecore.sensors.contracts import build_sensor_event
from securecore.sensors.fusion import (
    ANOMALY_BITS,
    SOURCE_ORDER,
    build_temporal_fusion_block,
    decode_temporal_fusion_block,
    encode_temporal_fusion_block,
)
from securecore.sensors.fusion_store import FusionBlockStore


def _event(sensor_class: str, sequence: int) -> dict:
    return build_sensor_event(
        sensor_id=f"windows.{sensor_class}.test" if sensor_class != "vision" else "truevision.state_change",
        sensor_class=sensor_class,
        host_id="host-test",
        event_type="state_change" if sensor_class == "vision" else "snapshot",
        sequence=sequence,
        cursor={"sequence": sequence},
        subject={"sensor_class": sensor_class},
        payload={"state": "observed", "sensor_class": sensor_class},
        previous_event_hash="GENESIS",
        confidence="observed",
        privacy_level="metadata",
        writer_id=f"forge.sensor.{sensor_class}",
        batch_id="batch-fusion",
        batch_index=sequence,
        event_id=f"event-{sensor_class}-{sequence}",
        observed_at_utc="2026-05-17T10:00:00.000000Z",
    )


class SensorFusionBlockTests(unittest.TestCase):
    def test_fusion_block_includes_every_logger_lane_count(self):
        events = [_event(sensor_class, index) for index, sensor_class in enumerate(SOURCE_ORDER) if sensor_class != "audio"]

        block = build_temporal_fusion_block(
            block_id="fusion-1",
            source_id="securecore.local_shape",
            window_start_utc="2026-05-17T10:00:00.000000Z",
            window_duration_ms=3000,
            events=events,
        )

        self.assertEqual(block["event_count"], len(SOURCE_ORDER) - 1)
        self.assertEqual(set(block["source_counts"]), set(SOURCE_ORDER))
        for sensor_class in SOURCE_ORDER:
            expected = 0 if sensor_class == "audio" else 1
            self.assertEqual(block["source_counts"][sensor_class], expected)
        self.assertGreater(block["window_start_ns"], 0)
        self.assertEqual(block["payload_class"], "binary_metadata")
        self.assertFalse(block["raw_content_stored"])
        self.assertFalse(block["inference_allowed"])
        self.assertFalse(block["recognition_authority"])

    def test_fusion_block_binary_round_trip_preserves_metadata_not_payloads(self):
        events = [_event("process", 0), _event("network", 1), _event("vision", 2)]
        block = build_temporal_fusion_block(
            block_id="fusion-2",
            source_id="securecore.local_shape",
            window_start_utc="2026-05-17T10:00:00.000000Z",
            window_duration_ms=3000,
            events=events,
        )

        raw = encode_temporal_fusion_block(block)
        decoded = decode_temporal_fusion_block(raw)

        self.assertLess(len(raw), 2048)
        self.assertEqual(decoded["block_id"], "fusion-2")
        self.assertEqual(decoded["source_id"], "securecore.local_shape")
        self.assertEqual(decoded["event_count"], 3)
        self.assertEqual(decoded["source_counts"]["process"], 1)
        self.assertEqual(decoded["source_counts"]["network"], 1)
        self.assertEqual(decoded["source_counts"]["vision"], 1)
        self.assertEqual(decoded["window_start_utc"], "2026-05-17T10:00:00.000000Z")
        self.assertEqual(decoded["anomaly_flags"], 0)
        self.assertFalse(any("payload" in ref for ref in decoded["event_refs"]))
        self.assertTrue(all("payload_hash" in ref for ref in decoded["event_refs"]))

    def test_fusion_block_marks_explicit_alerts_as_anomalous(self):
        alert = _event("security", 0)
        alert["event_type"] = "alert"
        alert["payload"]["risk_score"] = 4

        block = build_temporal_fusion_block(
            block_id="fusion-alert",
            source_id="securecore.local_shape",
            window_start_utc="2026-05-17T10:00:00.000000Z",
            window_duration_ms=3000,
            events=[alert],
        )

        self.assertTrue(block["anomaly_flags"] & ANOMALY_BITS["has_alert"])
        self.assertTrue(block["anomaly_flags"] & ANOMALY_BITS["has_security"])
        self.assertTrue(block["anomaly_flags"] & ANOMALY_BITS["has_explicit_risk"])

    def test_fusion_store_appends_binary_blocks_and_verifies_chain(self):
        import tempfile

        events = [_event("process", 0), _event("eventlog", 1), _event("vision", 2)]
        first = build_temporal_fusion_block(
            block_id="fusion-store-1",
            source_id="securecore.local_shape",
            window_start_utc="2026-05-17T10:00:00.000000Z",
            window_duration_ms=3000,
            events=events,
        )
        second = build_temporal_fusion_block(
            block_id="fusion-store-2",
            source_id="securecore.local_shape",
            window_start_utc="2026-05-17T10:00:03.000000Z",
            window_duration_ms=3000,
            events=[],
            previous_block_hash=first["block_hash"],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FusionBlockStore(tmpdir)
            first_meta = store.append(first)
            second_meta = store.append(second)

            self.assertGreater(first_meta["size"], 0)
            self.assertGreater(second_meta["offset"], first_meta["offset"])
            self.assertEqual([block["block_id"] for block in store.iter_blocks()], ["fusion-store-1", "fusion-store-2"])
            self.assertEqual(store.verify()["checked"], 2)
            self.assertTrue(store.verify()["intact"])


if __name__ == "__main__":
    unittest.main()
