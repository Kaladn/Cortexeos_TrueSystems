"""Export sensor events into temporal checker rows."""

from __future__ import annotations


def sensor_event_to_temporal_row(
    event: dict,
    *,
    source_id: str,
    correlation_id: str = "",
    causal_parents: list[str] | None = None,
) -> dict:
    forge_write = event.get("forge_write", {})
    return {
        "event_id": event["event_id"],
        "source_id": source_id,
        "sensor_id": event["sensor_id"],
        "event_type": event["event_type"],
        "observed_at_utc": event["observed_at_utc"],
        "sequence": event["sequence"],
        "writer_id": forge_write.get("writer_id", ""),
        "batch_id": forge_write.get("batch_id", ""),
        "batch_index": forge_write.get("batch_index", 0),
        "cursor": event.get("cursor", {}),
        "payload_hash": event.get("payload_hash", ""),
        "previous_event_hash": event.get("previous_event_hash", ""),
        "causal_parents": list(causal_parents or []),
        "correlation_id": correlation_id,
        "payload": event.get("payload", {}),
    }
