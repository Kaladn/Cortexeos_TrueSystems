"""Temporal pulse bridge for TrueVision and TrueSound state traces.

This module is deliberately SecureCore-shaped: it consumes derived state logs,
estimates audio/video temporal offset from pulse structure, and writes the
result through Forge. It does not store raw frames or raw audio.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

from securecore.forge.pulse_writer import ForgePulseWriter, PulseConfig
from securecore.forge.writer import ForgeWriter
from securecore.sensors.contracts import build_sensor_event, validate_sensor_event
from securecore.time import utc_now


SUBSTRATE = "trueav_temporal_pulse"
PULSE_SCHEMA = "truevision_temporal_pulse_v1"
PULSE_SENSOR_CLASS = "truevision_temporal_pulse"
PULSE_SENSOR_ID = "truevision.temporal_pulse"
PULSE_KINDS = {"beat", "section", "frame_window", "event_window", "sync_marker"}
PULSE_FIELDS = {
    "schema",
    "source_system",
    "run_id",
    "source_manifest_hash",
    "source_receipt_hash",
    "clock_basis",
    "fps",
    "frame_index",
    "time_sec",
    "pulse_id",
    "pulse_kind",
    "alignment_confidence",
}
RAW_MEDIA_FIELDS = {
    "raw_audio",
    "raw_video",
    "raw_frame",
    "raw_frames",
    "frames",
    "frame_bytes",
    "cell_arrays",
    "waveform",
    "waveforms",
    "audio_samples",
    "audio_bytes",
    "screenshot",
    "screenshots",
    "caption",
    "captions",
    "generated_media",
    "image_bytes",
    "video_bytes",
}


def validate_temporal_pulse_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate a TrueVision temporal pulse as timing metadata only."""

    if not isinstance(packet, dict):
        raise ValueError("temporal pulse packet must be an object")
    _reject_raw_media_fields(packet)
    extra = set(packet) - PULSE_FIELDS
    if extra:
        raise ValueError(f"temporal pulse packet has unsupported fields: {sorted(extra)}")
    missing = PULSE_FIELDS - set(packet)
    if missing:
        raise ValueError(f"temporal pulse packet missing fields: {sorted(missing)}")
    if packet["schema"] != PULSE_SCHEMA:
        raise ValueError(f"schema must be {PULSE_SCHEMA}")
    if packet["source_system"] != "TrueVision":
        raise ValueError("source_system must be TrueVision")
    for field in ("run_id", "pulse_id"):
        if not isinstance(packet[field], str) or not packet[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    for field in ("source_manifest_hash", "source_receipt_hash"):
        if not _is_sha256_ref(packet[field]):
            raise ValueError(f"{field} must be sha256:<64 hex>")
    if packet["clock_basis"] != "frame_index_fps":
        raise ValueError("clock_basis must be frame_index_fps")
    if not isinstance(packet["fps"], (int, float)) or isinstance(packet["fps"], bool) or float(packet["fps"]) <= 0:
        raise ValueError("fps must be positive")
    if not isinstance(packet["frame_index"], int) or isinstance(packet["frame_index"], bool) or packet["frame_index"] < 0:
        raise ValueError("frame_index must be a non-negative integer")
    if not isinstance(packet["time_sec"], (int, float)) or isinstance(packet["time_sec"], bool) or float(packet["time_sec"]) < 0:
        raise ValueError("time_sec must be non-negative")
    if packet["pulse_kind"] not in PULSE_KINDS:
        raise ValueError("pulse_kind must be beat, section, frame_window, event_window, or sync_marker")
    if (
        not isinstance(packet["alignment_confidence"], (int, float))
        or isinstance(packet["alignment_confidence"], bool)
        or not 0.0 <= float(packet["alignment_confidence"]) <= 1.0
    ):
        raise ValueError("alignment_confidence must be between 0.0 and 1.0")
    return {
        "schema": PULSE_SCHEMA,
        "source_system": "TrueVision",
        "run_id": str(packet["run_id"]),
        "source_manifest_hash": str(packet["source_manifest_hash"]),
        "source_receipt_hash": str(packet["source_receipt_hash"]),
        "clock_basis": "frame_index_fps",
        "fps": float(packet["fps"]),
        "frame_index": int(packet["frame_index"]),
        "time_sec": round(float(packet["time_sec"]), 6),
        "pulse_id": str(packet["pulse_id"]),
        "pulse_kind": str(packet["pulse_kind"]),
        "alignment_confidence": round(float(packet["alignment_confidence"]), 6),
    }


def temporal_pulse_to_sensor_event(
    packet: dict[str, Any],
    *,
    host_id: str,
    sequence: int,
    previous_event_hash: str,
    batch_id: str,
    batch_index: int,
    writer_id: str = "forge.sensor.truevision_temporal_pulse",
    observed_at_utc: str | None = None,
) -> dict[str, Any]:
    """Convert a validated pulse packet into a fusion-countable sensor event."""

    validated = validate_temporal_pulse_packet(packet)
    event = build_sensor_event(
        sensor_id=PULSE_SENSOR_ID,
        sensor_class=PULSE_SENSOR_CLASS,
        host_id=host_id,
        event_type="state_change",
        sequence=sequence,
        cursor={
            "clock_basis": validated["clock_basis"],
            "frame_index": validated["frame_index"],
            "fps": validated["fps"],
            "time_sec": validated["time_sec"],
        },
        subject={
            "source_system": "TrueVision",
            "run_id": validated["run_id"],
            "pulse_id": validated["pulse_id"],
            "pulse_kind": validated["pulse_kind"],
        },
        payload=validated,
        previous_event_hash=previous_event_hash,
        confidence="derived",
        privacy_level="metadata",
        writer_id=writer_id,
        batch_id=batch_id,
        batch_index=batch_index,
        event_id=f"truevision-temporal-pulse:{validated['run_id']}:{validated['pulse_id']}",
        observed_at_utc=observed_at_utc,
    )
    validate_sensor_event(event)
    return event


def write_temporal_pulse_bridge(
    *,
    vision_records_path: str | Path,
    audio_state_path: str | Path,
    forge_root: str | Path,
    run_id: str,
    max_allowed_offset_ms: float = 20.0,
    max_lag_seconds: float = 0.5,
) -> dict[str, Any]:
    """Write a SecureCore Forge bridge and receipt for AV pulse alignment."""

    vision_path = Path(vision_records_path)
    audio_path = Path(audio_state_path)
    visual_times, visual_values = _extract_visual_series(_read_jsonl(vision_path))
    audio_times, audio_values = _extract_audio_series(_read_jsonl(audio_path))
    if len(visual_times) < 3:
        raise ValueError("vision trace must contain at least three timed pulse records")
    if len(audio_times) < 3:
        raise ValueError("audio trace must contain at least three timed pulse records")

    visual_pulse_span = _span(visual_values)
    audio_pulse_span = _span(audio_values)
    visual_values = _normalize(visual_values)
    audio_values = _normalize(audio_values)
    sample_dt = _common_dt(visual_times, audio_times)
    estimate = _estimate_offset(
        visual_times,
        visual_values,
        audio_times,
        audio_values,
        max_lag_seconds=max_lag_seconds,
        step_seconds=sample_dt,
    )
    max_allowed_seconds = max(0.0, float(max_allowed_offset_ms) / 1000.0)
    sync_status = "pass"
    failure_reason = ""
    if visual_pulse_span <= 1.0e-8:
        sync_status = "fail"
        failure_reason = "insufficient_visual_pulse_energy"
    elif audio_pulse_span <= 1.0e-8:
        sync_status = "fail"
        failure_reason = "insufficient_audio_pulse_energy"
    elif abs(estimate["offset_seconds"]) > max_allowed_seconds:
        sync_status = "fail"
        failure_reason = "offset_exceeds_tolerance"

    forge_dir = Path(forge_root) / SUBSTRATE
    writer = ForgeWriter(forge_dir)
    pulse_writer = ForgePulseWriter(
        writer,
        PulseConfig(max_records_per_pulse=64, max_bytes_per_pulse=128 * 1024, max_age_ms_per_pulse=250),
    )

    bridge_records = _bridge_records(
        run_id=run_id,
        estimate=estimate,
        sample_count=96,
    )
    written = []
    for row in bridge_records:
        written.extend(pulse_writer.submit(row))

    receipt = _build_receipt(
        run_id=run_id,
        vision_path=vision_path,
        audio_path=audio_path,
        visual_count=len(visual_times),
        audio_count=len(audio_times),
        sample_dt=sample_dt,
        visual_pulse_span=visual_pulse_span,
        audio_pulse_span=audio_pulse_span,
        estimate=estimate,
        max_allowed_offset_ms=float(max_allowed_offset_ms),
        sync_status=sync_status,
        failure_reason=failure_reason,
    )
    written.extend(pulse_writer.submit(_forge_record(run_id, "receipt", "trueav_temporal_pulse_receipt", receipt)))
    written.extend(pulse_writer.close())

    return {
        "receipt": receipt,
        "forge_dir": str(forge_dir),
        "written_records": len(written),
        "bridge_record_count": len(bridge_records),
        "forge_stats": writer.stats(),
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _is_sha256_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(char in "0123456789abcdefABCDEF" for char in digest)


def _reject_raw_media_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in RAW_MEDIA_FIELDS:
                raise ValueError("temporal pulse packet may not contain raw media fields")
            _reject_raw_media_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_raw_media_fields(child)


def _extract_visual_series(rows: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    times = []
    values = []
    for row in rows:
        time_value = _number(row, "elapsed_seconds", "time_seconds", "timestamp_seconds")
        if time_value is None:
            continue
        pulse = _number(row, "screen_energy", "change_ratio")
        if pulse is None:
            payload = row.get("payload", {})
            if isinstance(payload, dict):
                sensor_event = payload.get("sensor_event", {})
                if isinstance(sensor_event, dict):
                    event_payload = sensor_event.get("payload", {})
                    if isinstance(event_payload, dict):
                        pulse = _number(event_payload, "screen_energy", "change_ratio")
        if pulse is None:
            continue
        times.append(float(time_value))
        values.append(float(pulse))
    return _sorted_series(times, values)


def _extract_audio_series(rows: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    times = []
    values = []
    previous_rms = 0.0
    for row in rows:
        time_value = _number(row, "time_seconds", "elapsed_seconds", "timestamp_seconds")
        if time_value is None:
            continue
        level = row.get("level", {})
        bands = row.get("bands", {})
        dynamics = row.get("dynamics", {})
        if not isinstance(level, dict):
            level = {}
        if not isinstance(bands, dict):
            bands = {}
        if not isinstance(dynamics, dict):
            dynamics = {}

        rms = _as_float(level.get("rms_norm"), default=0.0)
        attack = _as_float(dynamics.get("attack"), default=max(0.0, rms - previous_rms))
        bass = _as_float(bands.get("bass"), default=0.0)
        mid = _as_float(bands.get("mid"), default=0.0)
        high = _as_float(bands.get("high"), default=0.0)
        transient = 0.15 if dynamics.get("transient") is True else 0.0
        pulse = (rms * 0.52) + (attack * 0.28) + (bass * 0.08) + (mid * 0.04) + (high * 0.03) + transient
        times.append(float(time_value))
        values.append(float(pulse))
        previous_rms = rms
    return _sorted_series(times, values)


def _number(row: dict[str, Any], *fields: str) -> float | None:
    for field in fields:
        value = row.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _as_float(value: Any, *, default: float) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return default


def _sorted_series(times: list[float], values: list[float]) -> tuple[list[float], list[float]]:
    pairs = sorted(zip(times, values), key=lambda item: item[0])
    return [pair[0] for pair in pairs], [pair[1] for pair in pairs]


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if math.isclose(high, low):
        return [0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def _span(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(max(values) - min(values))


def _common_dt(visual_times: list[float], audio_times: list[float]) -> float:
    intervals = _positive_intervals(visual_times) + _positive_intervals(audio_times)
    if not intervals:
        return 1.0 / 60.0
    return max(1.0 / 240.0, min(1.0 / 15.0, median(intervals)))


def _positive_intervals(times: list[float]) -> list[float]:
    return [b - a for a, b in zip(times, times[1:]) if b > a]


def _estimate_offset(
    visual_times: list[float],
    visual_values: list[float],
    audio_times: list[float],
    audio_values: list[float],
    *,
    max_lag_seconds: float,
    step_seconds: float,
) -> dict[str, Any]:
    max_lag = max(0.0, float(max_lag_seconds))
    step = max(1.0 / 240.0, float(step_seconds))
    candidate_count = int((max_lag * 2.0) / step) + 1
    best = {"offset_seconds": 0.0, "correlation": -2.0, "samples": []}
    for index in range(candidate_count + 1):
        offset = -max_lag + (index * step)
        start = max(visual_times[0], audio_times[0] - offset)
        end = min(visual_times[-1], audio_times[-1] - offset)
        if end <= start:
            continue
        grid = _grid(start, end, step)
        visual = [_interp(visual_times, visual_values, t) for t in grid]
        audio = [_interp(audio_times, audio_values, t + offset) for t in grid]
        correlation = _pearson(visual, audio)
        if correlation > best["correlation"]:
            best = {
                "offset_seconds": offset,
                "correlation": correlation,
                "samples": [
                    {
                        "visual_time_seconds": round(t, 6),
                        "audio_time_seconds": round(t + offset, 6),
                        "visual_pulse": round(v, 6),
                        "audio_pulse": round(a, 6),
                        "pulse_delta": round(abs(v - a), 6),
                    }
                    for t, v, a in zip(grid, visual, audio)
                ],
            }
    return best


def _grid(start: float, end: float, step: float) -> list[float]:
    values = []
    current = start
    while current <= end:
        values.append(current)
        current += step
    return values


def _interp(times: list[float], values: list[float], t: float) -> float:
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    low = 0
    high = len(times) - 1
    while high - low > 1:
        mid = (low + high) // 2
        if times[mid] <= t:
            low = mid
        else:
            high = mid
    left_t = times[low]
    right_t = times[high]
    if math.isclose(right_t, left_t):
        return values[low]
    ratio = (t - left_t) / (right_t - left_t)
    return values[low] + ((values[high] - values[low]) * ratio)


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) < 3 or len(left) != len(right):
        return -1.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_den = math.sqrt(sum((a - left_mean) ** 2 for a in left))
    right_den = math.sqrt(sum((b - right_mean) ** 2 for b in right))
    denom = left_den * right_den
    if math.isclose(denom, 0.0):
        return -1.0
    return numerator / denom


def _bridge_records(*, run_id: str, estimate: dict[str, Any], sample_count: int) -> list[dict[str, Any]]:
    samples = estimate["samples"]
    if not samples:
        return []
    stride = max(1, len(samples) // max(1, sample_count))
    rows = []
    for index, sample in enumerate(samples[::stride][:sample_count]):
        payload = {
            "kind": "trueav_temporal_pulse_bridge_sample",
            "run_id": run_id,
            "sample_index": index,
            "estimated_audio_minus_visual_offset_ms": round(estimate["offset_seconds"] * 1000.0, 3),
            "pulse_correlation": round(float(estimate["correlation"]), 6),
            **sample,
        }
        rows.append(_forge_record(run_id, f"bridge-{index:04d}", "trueav_temporal_pulse_bridge", payload))
    return rows


def _build_receipt(
    *,
    run_id: str,
    vision_path: Path,
    audio_path: Path,
    visual_count: int,
    audio_count: int,
    sample_dt: float,
    visual_pulse_span: float,
    audio_pulse_span: float,
    estimate: dict[str, Any],
    max_allowed_offset_ms: float,
    sync_status: str,
    failure_reason: str,
) -> dict[str, Any]:
    samples = estimate["samples"]
    max_delta = max((sample["pulse_delta"] for sample in samples), default=0.0)
    receipt = {
        "schema_version": 1,
        "kind": "trueav_temporal_pulse_receipt",
        "run_id": run_id,
        "created_at_utc": utc_now(),
        "vision_trace_hash": _file_hash(vision_path),
        "audio_trace_hash": _file_hash(audio_path),
        "vision_record_count": visual_count,
        "audio_record_count": audio_count,
        "visual_pulse_span": round(float(visual_pulse_span), 8),
        "audio_pulse_span": round(float(audio_pulse_span), 8),
        "sample_dt_seconds": round(sample_dt, 6),
        "estimated_audio_minus_visual_offset_ms": round(float(estimate["offset_seconds"]) * 1000.0, 3),
        "max_allowed_offset_ms": round(float(max_allowed_offset_ms), 3),
        "pulse_correlation": round(float(estimate["correlation"]), 6),
        "max_pulse_delta": round(max_delta, 6),
        "sync_status": sync_status,
        "failure_reason": failure_reason,
        "temporal_phase_shift_correction": _correction_plan(
            offset_ms=round(float(estimate["offset_seconds"]) * 1000.0, 3),
            max_allowed_offset_ms=round(float(max_allowed_offset_ms), 3),
            pulse_correlation=round(float(estimate["correlation"]), 6),
            visual_pulse_span=visual_pulse_span,
            audio_pulse_span=audio_pulse_span,
            sync_status=sync_status,
            failure_reason=failure_reason,
        ),
        "raw_audio_saved": False,
        "raw_frames_saved": False,
        "sync_claim_requires_pulse_match": True,
        "start_button_is_not_causality_proof": True,
        "policy_authority": False,
        "mutation_authorized": False,
        "retention_class": "state_sync_receipt_keep",
    }
    receipt["receipt_id"] = _receipt_id(receipt)
    return receipt


def _correction_plan(
    *,
    offset_ms: float,
    max_allowed_offset_ms: float,
    pulse_correlation: float,
    visual_pulse_span: float,
    audio_pulse_span: float,
    sync_status: str,
    failure_reason: str,
) -> dict[str, Any]:
    audio_shift_ms = round(-float(offset_ms), 3)
    video_shift_ms = round(float(offset_ms), 3)
    abs_offset = abs(float(offset_ms))
    if abs_offset <= max_allowed_offset_ms:
        strategy = "none_required"
    elif offset_ms > 0:
        strategy = "advance_audio"
    else:
        strategy = "delay_audio"

    confidence = max(0.0, min(1.0, (float(pulse_correlation) + 1.0) / 2.0))
    auto_apply_allowed = (
        failure_reason == "offset_exceeds_tolerance"
        and pulse_correlation >= 0.75
        and visual_pulse_span > 1.0e-8
        and audio_pulse_span > 1.0e-8
    )
    return {
        "schema_version": "state_temporal_phase_shift_correction_v1",
        "law": "measure_state_phase_first_then_shift_media_presentation",
        "preferred_target": "audio",
        "estimated_audio_minus_visual_offset_ms": round(float(offset_ms), 3),
        "audio_shift_to_apply_ms": audio_shift_ms,
        "video_shift_to_apply_ms": video_shift_ms,
        "correction_strategy": strategy,
        "correction_confidence": round(confidence, 6),
        "auto_apply_allowed": bool(auto_apply_allowed),
        "manual_review_required": not bool(auto_apply_allowed) and sync_status == "fail",
        "audio_filter_hint": _audio_filter_hint(audio_shift_ms),
        "applicable_lanes": [
            "rendered_video_mux",
            "film_global_av_sync",
            "presentation_video_sync",
        ],
        "not_authority_for": [
            "phoneme_lip_sync",
            "per_shot_drift",
            "semantic_mouth_tracking",
        ],
        "next_step_for_mouth_to_speech": "derive windowed mouth-motion state and voice-presence state, then apply segmented phase correction",
    }


def _audio_filter_hint(audio_shift_ms: float) -> str:
    if math.isclose(audio_shift_ms, 0.0, abs_tol=0.5):
        return "none"
    if audio_shift_ms > 0:
        delay_ms = int(round(audio_shift_ms))
        return f"adelay={delay_ms}|{delay_ms},asetpts=PTS-STARTPTS"
    trim_seconds = abs(float(audio_shift_ms)) / 1000.0
    return f"atrim=start={trim_seconds:.6f},asetpts=PTS-STARTPTS"


def _forge_record(run_id: str, suffix: str, record_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": f"{SUBSTRATE}:{run_id}:{suffix}",
        "substrate": SUBSTRATE,
        "timestamp": utc_now(),
        "cell_id": f"{run_id}:temporal_pulse",
        "record_type": record_type,
        "payload": payload,
    }


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _receipt_id(receipt: dict[str, Any]) -> str:
    row = dict(receipt)
    row["receipt_id"] = ""
    digest = hashlib.sha256(
        json.dumps(row, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"receipt-{digest[:24]}"
