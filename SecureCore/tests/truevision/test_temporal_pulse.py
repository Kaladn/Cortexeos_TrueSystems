import json
import math
import tempfile
import unittest
from pathlib import Path

from securecore.forge.reader import ForgeReader
from securecore.sensors.contracts import validate_sensor_event
from securecore.sensors.fusion import build_temporal_fusion_block
from securecore.truevision.temporal_pulse import (
    temporal_pulse_to_sensor_event,
    validate_temporal_pulse_packet,
    write_temporal_pulse_bridge,
)


def _pulse(t):
    centers = (0.45, 0.95, 1.55, 2.2)
    return sum(math.exp(-((t - center) / 0.035) ** 2) for center in centers)


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


class TrueAVTemporalPulseTests(unittest.TestCase):
    def test_truevision_temporal_pulse_packet_becomes_fusion_lane_metadata_only(self):
        packet = {
            "schema": "truevision_temporal_pulse_v1",
            "source_system": "TrueVision",
            "run_id": "tv-run-1",
            "source_manifest_hash": "sha256:" + ("a" * 64),
            "source_receipt_hash": "sha256:" + ("b" * 64),
            "clock_basis": "frame_index_fps",
            "fps": 60,
            "frame_index": 1234,
            "time_sec": 20.5667,
            "pulse_id": "pulse-1234",
            "pulse_kind": "beat",
            "alignment_confidence": 0.92,
        }

        validated = validate_temporal_pulse_packet(packet)
        event = temporal_pulse_to_sensor_event(
            validated,
            host_id="host-test",
            sequence=7,
            previous_event_hash="GENESIS",
            batch_id="batch-tv-pulse",
            batch_index=0,
            observed_at_utc="2026-05-27T10:00:00.000000Z",
        )
        validate_sensor_event(event)
        block = build_temporal_fusion_block(
            block_id="fusion-tv-pulse",
            source_id="securecore.local_shape",
            window_start_utc="2026-05-27T10:00:00.000000Z",
            window_duration_ms=3000,
            events=[event],
        )

        self.assertEqual(event["sensor_id"], "truevision.temporal_pulse")
        self.assertEqual(event["sensor_class"], "truevision_temporal_pulse")
        self.assertEqual(block["source_counts"]["truevision_temporal_pulse"], 1)
        self.assertEqual(block["source_counts"]["vision"], 0)
        self.assertFalse(block["raw_content_stored"])
        self.assertFalse(block["recognition_authority"])

    def test_truevision_temporal_pulse_packet_rejects_raw_media_fields(self):
        packet = {
            "schema": "truevision_temporal_pulse_v1",
            "source_system": "TrueVision",
            "run_id": "tv-run-raw",
            "source_manifest_hash": "sha256:" + ("a" * 64),
            "source_receipt_hash": "sha256:" + ("b" * 64),
            "clock_basis": "frame_index_fps",
            "fps": 60,
            "frame_index": 4,
            "time_sec": 0.0667,
            "pulse_id": "pulse-raw",
            "pulse_kind": "sync_marker",
            "alignment_confidence": 0.5,
            "raw_video": "base64-nope",
        }

        with self.assertRaises(ValueError):
            validate_temporal_pulse_packet(packet)

    def test_bridge_passes_when_audio_visual_pulses_align_inside_tolerance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vision_path = root / "vision.jsonl"
            audio_path = root / "audio.jsonl"
            offset_seconds = 0.032

            vision_rows = [
                {
                    "frame_number": index,
                    "elapsed_seconds": round(index / 30.0, 6),
                    "screen_energy": _pulse(index / 30.0),
                }
                for index in range(90)
            ]
            audio_rows = []
            previous = 0.0
            for index in range(180):
                t = index / 60.0
                value = _pulse(t - offset_seconds)
                audio_rows.append(
                    {
                        "frame_index": index,
                        "time_seconds": round(t, 6),
                        "level": {"rms_norm": value},
                        "bands": {"bass": value * 0.8, "mid": value * 0.5, "high": value * 0.2},
                        "dynamics": {"attack": max(0.0, value - previous), "transient": value > 0.65},
                    }
                )
                previous = value

            _write_jsonl(vision_path, vision_rows)
            _write_jsonl(audio_path, audio_rows)

            result = write_temporal_pulse_bridge(
                vision_records_path=vision_path,
                audio_state_path=audio_path,
                forge_root=root / "forge",
                run_id="aligned",
                max_allowed_offset_ms=45.0,
            )

            receipt = result["receipt"]
            self.assertEqual(receipt["kind"], "trueav_temporal_pulse_receipt")
            self.assertEqual(receipt["sync_status"], "pass")
            self.assertAlmostEqual(receipt["estimated_audio_minus_visual_offset_ms"], 32.0, delta=18.0)
            self.assertGreater(receipt["pulse_correlation"], 0.82)
            self.assertFalse(receipt["raw_audio_saved"])
            self.assertFalse(receipt["raw_frames_saved"])
            self.assertTrue(receipt["sync_claim_requires_pulse_match"])

            reader = ForgeReader(root / "forge" / "trueav_temporal_pulse")
            self.assertTrue(reader.verify()["intact"])
            records = list(reader.iter_records())
            self.assertGreater(len(records), 4)
            self.assertEqual(records[-1].record_type, "trueav_temporal_pulse_receipt")
            self.assertEqual(records[-1].payload["sync_status"], "pass")

    def test_bridge_fails_closed_when_offset_exceeds_tolerance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vision_path = root / "vision.jsonl"
            audio_path = root / "audio.jsonl"
            offset_seconds = 0.12

            _write_jsonl(
                vision_path,
                [
                    {
                        "frame_number": index,
                        "elapsed_seconds": round(index / 30.0, 6),
                        "screen_energy": _pulse(index / 30.0),
                    }
                    for index in range(90)
                ],
            )
            _write_jsonl(
                audio_path,
                [
                    {
                        "frame_index": index,
                        "time_seconds": round(index / 60.0, 6),
                        "level": {"rms_norm": _pulse((index / 60.0) - offset_seconds)},
                        "bands": {"bass": 0.0, "mid": 0.0, "high": 0.0},
                        "dynamics": {"attack": 0.0, "transient": False},
                    }
                    for index in range(180)
                ],
            )

            result = write_temporal_pulse_bridge(
                vision_records_path=vision_path,
                audio_state_path=audio_path,
                forge_root=root / "forge",
                run_id="misaligned",
                max_allowed_offset_ms=40.0,
            )

            receipt = result["receipt"]
            self.assertEqual(receipt["sync_status"], "fail")
            self.assertGreater(abs(receipt["estimated_audio_minus_visual_offset_ms"]), 40.0)
            self.assertEqual(receipt["failure_reason"], "offset_exceeds_tolerance")
            plan = receipt["temporal_phase_shift_correction"]
            self.assertEqual(plan["schema_version"], "state_temporal_phase_shift_correction_v1")
            self.assertEqual(plan["preferred_target"], "audio")
            self.assertEqual(plan["correction_strategy"], "advance_audio")
            self.assertAlmostEqual(
                plan["audio_shift_to_apply_ms"],
                -receipt["estimated_audio_minus_visual_offset_ms"],
                delta=0.001,
            )
            self.assertEqual(plan["video_shift_to_apply_ms"], receipt["estimated_audio_minus_visual_offset_ms"])
            self.assertTrue(plan["auto_apply_allowed"])
            self.assertIn("film_global_av_sync", plan["applicable_lanes"])

    def test_correction_plan_delays_audio_when_audio_leads_visual(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vision_path = root / "vision.jsonl"
            audio_path = root / "audio.jsonl"
            offset_seconds = -0.09

            _write_jsonl(
                vision_path,
                [
                    {
                        "frame_number": index,
                        "elapsed_seconds": round(index / 30.0, 6),
                        "screen_energy": _pulse(index / 30.0),
                    }
                    for index in range(90)
                ],
            )
            _write_jsonl(
                audio_path,
                [
                    {
                        "frame_index": index,
                        "time_seconds": round(index / 60.0, 6),
                        "level": {"rms_norm": _pulse((index / 60.0) - offset_seconds)},
                        "bands": {"bass": 0.0, "mid": 0.0, "high": 0.0},
                        "dynamics": {"attack": 0.0, "transient": False},
                    }
                    for index in range(180)
                ],
            )

            result = write_temporal_pulse_bridge(
                vision_records_path=vision_path,
                audio_state_path=audio_path,
                forge_root=root / "forge",
                run_id="audio-leads",
                max_allowed_offset_ms=20.0,
            )

            receipt = result["receipt"]
            self.assertEqual(receipt["sync_status"], "fail")
            self.assertLess(receipt["estimated_audio_minus_visual_offset_ms"], -20.0)
            plan = receipt["temporal_phase_shift_correction"]
            self.assertEqual(plan["correction_strategy"], "delay_audio")
            self.assertGreater(plan["audio_shift_to_apply_ms"], 20.0)
            self.assertTrue(plan["auto_apply_allowed"])

    def test_bridge_fails_closed_when_audio_trace_has_no_pulse_energy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vision_path = root / "vision.jsonl"
            audio_path = root / "audio.jsonl"

            _write_jsonl(
                vision_path,
                [
                    {
                        "frame_number": index,
                        "elapsed_seconds": round(index / 30.0, 6),
                        "screen_energy": _pulse(index / 30.0),
                    }
                    for index in range(90)
                ],
            )
            _write_jsonl(
                audio_path,
                [
                    {
                        "frame_index": index,
                        "time_seconds": round(index / 60.0, 6),
                        "level": {"rms_norm": 0.0},
                        "bands": {"bass": 0.0, "mid": 0.0, "high": 0.0},
                        "dynamics": {"attack": 0.0, "transient": False},
                    }
                    for index in range(180)
                ],
            )

            result = write_temporal_pulse_bridge(
                vision_records_path=vision_path,
                audio_state_path=audio_path,
                forge_root=root / "forge",
                run_id="silent-audio",
                max_allowed_offset_ms=40.0,
            )

            receipt = result["receipt"]
            self.assertEqual(receipt["sync_status"], "fail")
            self.assertEqual(receipt["failure_reason"], "insufficient_audio_pulse_energy")
            self.assertEqual(receipt["audio_pulse_span"], 0.0)


if __name__ == "__main__":
    unittest.main()
