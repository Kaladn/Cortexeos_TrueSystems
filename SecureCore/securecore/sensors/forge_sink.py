"""Forge sink for validated sensor events."""

from __future__ import annotations

from pathlib import Path

from securecore.forge.reader import ForgeReader
from securecore.forge.pulse_writer import ForgePulseWriter
from securecore.forge.writer import ForgeWriter
from securecore.sensors.contracts import validate_sensor_event
from securecore.time import utc_now


class SensorForgeSink:
    """Write sensor events to a Forge destination on explicit call only."""

    def __init__(self, forge_root: str | Path):
        self.forge_root = Path(forge_root)

    def write_events(self, destination: str, events: list[dict]) -> int:
        if not events:
            return 0

        destination_root = self.forge_root / destination
        last_record = ForgeReader(destination_root).last_record()
        writer = ForgePulseWriter(
            ForgeWriter(destination_root),
            start_sequence=(last_record.sequence + 1) if last_record else 0,
            previous_hash=last_record.chain_hash if last_record else "GENESIS",
        )
        try:
            for event in events:
                validate_sensor_event(event)
                writer.submit(_forge_record_from_sensor_event(destination, event))
            writer.close()
        finally:
            writer.close()
        return len(events)


def _forge_record_from_sensor_event(destination: str, event: dict) -> dict:
    forge_write = event["forge_write"]
    return {
        "record_id": event["event_id"],
        "substrate": destination,
        "sequence": int(event["sequence"]),
        "timestamp": event["observed_at_utc"] or utc_now(),
        "cell_id": event["sensor_id"],
        "record_type": event["event_type"],
        "payload": {
            "sensor_event": event,
            "batch_id": forge_write["batch_id"],
            "batch_index": forge_write["batch_index"],
            "writer_id": forge_write["writer_id"],
        },
        "previous_hash": event["previous_event_hash"],
        "chain_hash": event["payload_hash"],
    }
