"""TrueVision SC Edition Forge adapter."""

from __future__ import annotations

from securecore.sensors.contracts import build_sensor_event, validate_sensor_event
from securecore.truevision.contracts import validate_state_change


def state_change_to_sensor_event(
    record: dict,
    *,
    host_id: str,
    sequence: int,
    previous_event_hash: str,
    batch_id: str,
    batch_index: int,
) -> dict:
    validated = validate_state_change(record)
    event = build_sensor_event(
        sensor_id="truevision.state_change",
        sensor_class="vision",
        host_id=host_id,
        event_type="state_change",
        sequence=sequence,
        cursor={"change_id": validated["change_id"], "grid_hash": validated["current_grid_hash"]},
        subject={
            "source_id": validated["source_id"],
            "session_id": validated["session_id"],
            "change_id": validated["change_id"],
        },
        payload=validated,
        previous_event_hash=previous_event_hash,
        confidence="witnessed",
        privacy_level="metadata",
        writer_id="forge.sensor.vision",
        batch_id=batch_id,
        batch_index=batch_index,
        event_id=f"truevision-sc:{validated['session_id']}:{validated['change_id']}",
        observed_at_utc=validated["observed_at_utc"],
    )
    validate_sensor_event(event)
    return event
