"""One-shot logging smoke test for the sensor and Forge path."""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from securecore.forge.reader import ForgeReader
from securecore.log_streams.streams import LogRouter
from securecore.sensors.eventlog_collector import collect_eventlog_source
from securecore.sensors.cursors import CursorStore
from securecore.sensors.forge_sink import SensorForgeSink
from securecore.sensors.fusion import build_temporal_fusion_block
from securecore.sensors.fusion_store import FusionBlockStore
from securecore.sensors.source_registry import default_source_registry
from securecore.sensors.windows_readers import (
    diff_open_windows,
    diff_network_connections,
    diff_processes,
    open_window_rows_to_events,
    snapshot_network_connections,
    snapshot_open_windows,
    snapshot_processes,
)
from securecore.time import is_canonical_utc_timestamp, utc_now


def run_logging_smoke(
    runtime_root: str | Path,
    *,
    duration_seconds: float = 1.0,
    sleep_seconds: float = 0.2,
    process_snapshots: tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]] | None = None,
    network_snapshots: tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]] | None = None,
    window_snapshots: tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]] | None = None,
    eventlog_records: list[dict[str, Any]] | None = None,
    hid_events: list[dict[str, Any]] | None = None,
    vision_events: list[dict[str, Any]] | None = None,
    include_live_windows: bool = False,
    include_live_eventlog: bool = False,
    process_snapshot_func=snapshot_processes,
    network_snapshot_func=snapshot_network_connections,
    window_snapshot_func=snapshot_open_windows,
    sleep_func=time.sleep,
) -> dict[str, Any]:
    """Run a contained one-shot smoke test.

    This function does not install services, start agents, schedule jobs, or
    change system settings. It writes only under ``runtime_root``.
    """

    root = Path(runtime_root)
    logs_dir = root / "logs"
    forge_root = root / "forge"
    cursor_store = CursorStore(root / "cursors" / "sensor_cursors.json")
    router = LogRouter(str(logs_dir))
    sink = SensorForgeSink(forge_root)
    batch_id = f"smoke-{uuid4()}"
    host_id = platform.node() or "local"

    start = time.monotonic()
    observation_window_start_utc = utc_now()
    _log(router, "health", "smoke_started", {"batch_id": batch_id, "agents": "disabled"})

    previous_processes = process_snapshots[0] if process_snapshots is not None else process_snapshot_func()
    previous_network = network_snapshots[0] if network_snapshots is not None else network_snapshot_func()
    previous_windows: dict[str, dict[str, Any]] = {}
    current_windows: dict[str, dict[str, Any]] = {}
    if window_snapshots is not None or include_live_windows:
        previous_windows = window_snapshots[0] if window_snapshots is not None else window_snapshot_func()

    needs_live_observation_wait = (
        process_snapshots is None
        or network_snapshots is None
        or (include_live_windows and window_snapshots is None)
    )
    observation_wait_seconds = max(0.0, min(duration_seconds, sleep_seconds)) if needs_live_observation_wait else duration_seconds
    observation_window_duration_ms = max(1, int(observation_wait_seconds * 1000))
    if needs_live_observation_wait:
        sleep_func(observation_wait_seconds)

    current_processes = process_snapshots[1] if process_snapshots is not None else process_snapshot_func()
    current_network = network_snapshots[1] if network_snapshots is not None else network_snapshot_func()
    if window_snapshots is not None or include_live_windows:
        current_windows = window_snapshots[1] if window_snapshots is not None else window_snapshot_func()

    process_events = diff_processes(
        previous_processes,
        current_processes,
        host_id=host_id,
        sequence_start=0,
        previous_event_hash="GENESIS",
        batch_id=batch_id,
    )
    network_events = diff_network_connections(
        previous_network,
        current_network,
        host_id=host_id,
        sequence_start=0,
        previous_event_hash="GENESIS",
        batch_id=batch_id,
    )
    window_events = diff_open_windows(
        previous_windows,
        current_windows,
        host_id=host_id,
        sequence_start=0,
        previous_event_hash="GENESIS",
        batch_id=batch_id,
    )
    if include_live_windows and not window_events and current_windows:
        window_events = open_window_rows_to_events(
            list(current_windows.values()),
            host_id=host_id,
            sequence_start=0,
            previous_event_hash="GENESIS",
            batch_id=batch_id,
        )

    eventlog_events: list[dict[str, Any]] = []
    if eventlog_records is not None or include_live_eventlog:
        registry = default_source_registry()
        source_id = "windows.defender.operational"
        eventlog_events = collect_eventlog_source(
            source_id=source_id,
            source_config=registry[source_id],
            cursor_store=cursor_store,
            host_id=host_id,
            batch_id=batch_id,
            max_events=20,
            records=eventlog_records,
        )

    process_count = sink.write_events("sensor_process", process_events)
    network_count = sink.write_events("sensor_network", network_events)
    window_count = sink.write_events("sensor_window", window_events)
    eventlog_count = sink.write_events("sensor_eventlog", eventlog_events)
    hid_count = sink.write_events("sensor_hid", list(hid_events or []))
    vision_count = sink.write_events("sensor_vision", list(vision_events or []))

    _log(router, "health", "smoke_counts", {
        "process_events": process_count,
        "network_events": network_count,
        "window_events": window_count,
        "eventlog_events": eventlog_count,
        "hid_events": hid_count,
        "vision_events": vision_count,
    })

    fusion_events = [
        *process_events,
        *network_events,
        *window_events,
        *eventlog_events,
        *(hid_events or []),
        *(vision_events or []),
    ]
    fusion_block = build_temporal_fusion_block(
        block_id=f"fusion-{batch_id}",
        source_id="securecore.logging_smoke",
        window_start_utc=observation_window_start_utc,
        window_duration_ms=observation_window_duration_ms,
        events=fusion_events,
    )
    fusion_store = FusionBlockStore(root / "fusion")
    fusion_store.append(fusion_block)
    fusion_verify = fusion_store.verify()

    _log(router, "operator", "smoke_completed", {"batch_id": batch_id, "activation": "none"})

    forge_verify = {
        name: ForgeReader(forge_root / name).verify()
        for name in ("sensor_process", "sensor_network", "sensor_window", "sensor_eventlog", "sensor_hid", "sensor_vision")
        if (forge_root / name / "records.bin").exists()
    }
    bad_timestamps = _count_bad_timestamps([*process_events, *network_events, *window_events, *eventlog_events])
    report = {
        "ok": bad_timestamps == 0 and all(row.get("intact") for row in forge_verify.values()),
        "duration_seconds": round(time.monotonic() - start, 6),
        "observation_window_start_utc": observation_window_start_utc,
        "observation_window_duration_ms": observation_window_duration_ms,
        "runtime_root": str(root),
        "log_counts": router.stats(),
        "sensor_process_events": process_count,
        "sensor_network_events": network_count,
        "sensor_window_events": window_count,
        "sensor_eventlog_events": eventlog_count,
        "sensor_hid_events": hid_count,
        "sensor_vision_events": vision_count,
        "fusion_block_events": fusion_block["event_count"],
        "fusion_source_counts": fusion_block["source_counts"],
        "fusion_verify": fusion_verify,
        "forge_verify": forge_verify,
        "bad_timestamps": bad_timestamps,
        "agents": "disabled",
        "camera": "disabled",
        "microphone": "disabled",
    }
    (root / "reports").mkdir(parents=True, exist_ok=True)
    (root / "reports" / "logging_smoke_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


def _log(router: LogRouter, stream: str, event_type: str, payload: dict[str, Any]) -> None:
    router.log(
        {
            "stream": stream,
            "event_type": event_type,
            "timestamp": utc_now(),
            "payload": payload,
        }
    )


def _count_bad_timestamps(events: list[dict[str, Any]]) -> int:
    return sum(1 for event in events if not is_canonical_utc_timestamp(str(event.get("observed_at_utc", ""))))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a one-shot SecureCore logging smoke test.")
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--duration-seconds", type=float, default=1.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--include-eventlog", action="store_true")
    parser.add_argument("--include-windows", action="store_true")
    args = parser.parse_args()

    report = run_logging_smoke(
        args.runtime_root,
        duration_seconds=args.duration_seconds,
        sleep_seconds=args.sleep_seconds,
        include_live_eventlog=args.include_eventlog,
        include_live_windows=args.include_windows,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
