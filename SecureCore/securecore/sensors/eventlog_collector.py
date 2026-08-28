"""Bounded Windows Event Log collection helpers."""

from __future__ import annotations

from typing import Any

from securecore.sensors.cursors import CursorStore
from securecore.sensors.source_registry import SourceMode
from securecore.sensors.windows_readers import (
    eventlog_records_to_events,
    read_eventlog_records,
)


def collect_eventlog_source(
    *,
    source_id: str,
    source_config: dict,
    cursor_store: CursorStore,
    host_id: str,
    batch_id: str,
    max_events: int = 100,
    records: list[dict[str, Any]] | None = None,
) -> list[dict]:
    """Collect one configured Event Log source into sensor events.

    This function is a one-shot collector. It does not schedule itself, does
    not subscribe to Windows events, and does not activate any agent.
    """

    cursor = cursor_store.get(source_id)
    after_record_id = int(cursor.get("last_record_id", 0) or 0)
    sequence_start = int(cursor.get("last_sequence", -1) or -1) + 1
    previous_event_hash = str(cursor.get("last_event_hash", "GENESIS") or "GENESIS")

    raw_records = records
    if raw_records is None:
        raw_records = read_eventlog_records(
            str(source_config.get("source_name", "")),
            after_record_id=after_record_id,
            max_events=max_events,
        )

    raw_records = [row for row in raw_records if int(row.get("record_id", 0) or 0) > after_record_id]
    raw_records.sort(key=lambda row: int(row.get("record_id", 0) or 0))

    event_ids = {int(value) for value in source_config.get("event_ids_of_interest", [])}
    filtered_records = [
        row for row in raw_records if not event_ids or int(row.get("event_id", 0) or 0) in event_ids
    ]

    events = eventlog_records_to_events(
        filtered_records,
        host_id=host_id,
        sequence_start=sequence_start,
        previous_event_hash=previous_event_hash,
        batch_id=batch_id,
    )

    if raw_records:
        last_record_id = max(int(row.get("record_id", 0) or 0) for row in raw_records)
        cursor_update = {
            "source_name": source_config.get("source_name", ""),
            "last_record_id": last_record_id,
            "last_sequence": sequence_start + len(events) - 1 if events else sequence_start - 1,
            "last_event_hash": events[-1]["payload_hash"] if events else previous_event_hash,
        }
        cursor_store.update(source_id, cursor_update)

    return events


def collect_enabled_eventlog_sources(
    *,
    registry: dict[str, dict],
    cursor_store: CursorStore,
    host_id: str,
    batch_id: str,
    max_events_per_source: int = 100,
    records_by_source: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, list[dict]]:
    """Collect all enabled Event Log registry sources once.

    Only sources targeting ``sensor_eventlog`` are collected. Process, network,
    window, HID, and vision lanes keep their own readers.
    """

    results: dict[str, list[dict]] = {}
    for source_id, source_config in sorted(registry.items()):
        if source_config.get("mode") == SourceMode.DISABLED.value:
            continue
        if source_config.get("forge_destination") != "sensor_eventlog":
            continue
        injected_records = None
        if records_by_source is not None:
            injected_records = records_by_source.get(source_id, [])
        events = collect_eventlog_source(
            source_id=source_id,
            source_config=source_config,
            cursor_store=cursor_store,
            host_id=host_id,
            batch_id=batch_id,
            max_events=max_events_per_source,
            records=injected_records,
        )
        results[source_id] = events
    return results
