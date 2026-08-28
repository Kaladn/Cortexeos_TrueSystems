"""Base event contract for SecureCore sensor lanes."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from securecore.time import is_canonical_utc_timestamp, utc_now


SENSOR_CLASSES = {
    "process",
    "network",
    "eventlog",
    "hid",
    "window",
    "device",
    "security",
    "vision",
    "truevision_temporal_pulse",
}
EVENT_TYPES = {"snapshot", "diff", "state_change", "alert"}
CONFIDENCE_VALUES = {"observed", "derived", "witnessed"}
PRIVACY_LEVELS = {"metadata", "content", "sensitive"}


class SensorEventValidationError(ValueError):
    """Raised when a sensor event does not satisfy the base contract."""


def payload_hash(payload: dict) -> str:
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build_sensor_event(
    *,
    sensor_id: str,
    sensor_class: str,
    host_id: str,
    event_type: str,
    sequence: int,
    cursor: dict,
    subject: dict,
    payload: dict,
    previous_event_hash: str,
    confidence: str,
    privacy_level: str,
    writer_id: str,
    batch_id: str,
    batch_index: int,
    event_id: str | None = None,
    observed_at_utc: str | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "sensor_id": sensor_id,
        "sensor_class": sensor_class,
        "host_id": host_id,
        "event_id": event_id or str(uuid4()),
        "event_type": event_type,
        "observed_at_utc": observed_at_utc or utc_now(),
        "sequence": sequence,
        "cursor": cursor,
        "subject": subject,
        "payload": payload,
        "payload_hash": payload_hash(payload),
        "previous_event_hash": previous_event_hash,
        "confidence": confidence,
        "privacy_level": privacy_level,
        "forge_write": {
            "batch_id": batch_id,
            "batch_index": batch_index,
            "writer_id": writer_id,
        },
    }


def validate_sensor_event(event: dict) -> None:
    required = [
        "schema_version",
        "sensor_id",
        "sensor_class",
        "host_id",
        "event_id",
        "event_type",
        "observed_at_utc",
        "sequence",
        "cursor",
        "subject",
        "payload",
        "payload_hash",
        "previous_event_hash",
        "confidence",
        "privacy_level",
        "forge_write",
    ]
    for key in required:
        if key not in event:
            raise SensorEventValidationError(f"missing field: {key}")

    if event["schema_version"] != 1:
        raise SensorEventValidationError("schema_version must be 1")
    if not is_canonical_utc_timestamp(event["observed_at_utc"]):
        raise SensorEventValidationError("observed_at_utc must use canonical UTC format")
    if event["sensor_class"] not in SENSOR_CLASSES:
        raise SensorEventValidationError(f"unknown sensor_class: {event['sensor_class']}")
    if event["event_type"] not in EVENT_TYPES:
        raise SensorEventValidationError(f"unknown event_type: {event['event_type']}")
    if event["confidence"] not in CONFIDENCE_VALUES:
        raise SensorEventValidationError(f"unknown confidence: {event['confidence']}")
    if event["privacy_level"] not in PRIVACY_LEVELS:
        raise SensorEventValidationError(f"unknown privacy_level: {event['privacy_level']}")
    if not isinstance(event["sequence"], int) or event["sequence"] < 0:
        raise SensorEventValidationError("sequence must be a non-negative integer")
    if not isinstance(event["cursor"], dict):
        raise SensorEventValidationError("cursor must be an object")
    if not isinstance(event["subject"], dict):
        raise SensorEventValidationError("subject must be an object")
    if not isinstance(event["payload"], dict):
        raise SensorEventValidationError("payload must be an object")
    if event["payload_hash"] != payload_hash(event["payload"]):
        raise SensorEventValidationError("payload_hash mismatch")

    forge_write = event["forge_write"]
    if not isinstance(forge_write, dict):
        raise SensorEventValidationError("forge_write must be an object")
    for key in ("batch_id", "batch_index", "writer_id"):
        if key not in forge_write:
            raise SensorEventValidationError(f"missing forge_write field: {key}")
    if not isinstance(forge_write["batch_index"], int) or forge_write["batch_index"] < 0:
        raise SensorEventValidationError("forge_write.batch_index must be a non-negative integer")
