"""Build bounded incident windows from temporal rows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def build_incident_window(
    trigger_event_id: str,
    temporal_rows: list[dict[str, Any]],
    *,
    before_seconds: int,
    after_seconds: int,
) -> dict[str, Any]:
    indexed = {
        str(row.get("event_id", "")): row
        for row in temporal_rows
        if _parse_utc(str(row.get("observed_at_utc", ""))) is not None
    }
    if trigger_event_id not in indexed:
        raise ValueError(f"trigger event not found: {trigger_event_id}")

    trigger = indexed[trigger_event_id]
    trigger_time = _parse_utc(str(trigger["observed_at_utc"]))
    assert trigger_time is not None

    start = trigger_time - timedelta(seconds=before_seconds)
    end = trigger_time + timedelta(seconds=after_seconds)
    timeline = []
    for row in temporal_rows:
        observed_at = _parse_utc(str(row.get("observed_at_utc", "")))
        if observed_at is not None and start <= observed_at <= end:
            timeline.append(row)

    timeline.sort(key=lambda row: (str(row.get("observed_at_utc", "")), str(row.get("event_id", ""))))
    return {
        "trigger_event_id": trigger_event_id,
        "window_start_utc": _format_utc(start),
        "window_end_utc": _format_utc(end),
        "timeline": timeline,
        "entities": _extract_entities(timeline),
    }


def _extract_entities(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    entities = {
        "processes": set(),
        "remote_ips": set(),
        "users": set(),
        "files": set(),
        "devices": set(),
    }
    for row in rows:
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            continue
        process = payload.get("process", {})
        if isinstance(process, dict) and process.get("name"):
            entities["processes"].add(str(process["name"]))
        connection = payload.get("connection", {})
        if isinstance(connection, dict) and connection.get("remote"):
            remote = str(connection["remote"]).split(":", 1)[0]
            if remote:
                entities["remote_ips"].add(remote)
        for key, target in (
            ("remote_ip", "remote_ips"),
            ("user", "users"),
            ("file", "files"),
            ("device", "devices"),
        ):
            value = payload.get(key)
            if value:
                entities[target].add(str(value))
    return {key: sorted(value) for key, value in entities.items()}


def _parse_utc(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
