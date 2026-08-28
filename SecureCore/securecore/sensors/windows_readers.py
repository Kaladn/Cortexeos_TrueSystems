"""Windows sensor snapshot and diff helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
import ctypes
from typing import Any

import psutil

from securecore.sensors.contracts import build_sensor_event, payload_hash
from securecore.time import utc_now


def snapshot_processes() -> dict[int, dict[str, Any]]:
    processes: dict[int, dict[str, Any]] = {}
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline", "username", "create_time"]):
        try:
            info = proc.info
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        pid = int(info.get("pid") or 0)
        if pid <= 0:
            continue
        processes[pid] = {
            "pid": pid,
            "name": info.get("name") or "",
            "exe": info.get("exe") or "",
            "cmdline": info.get("cmdline") or [],
            "username": info.get("username") or "",
            "create_time": info.get("create_time") or 0.0,
        }
    return processes


def snapshot_network_connections() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for conn in psutil.net_connections(kind="inet"):
        local = _addr(conn.laddr)
        remote = _addr(conn.raddr)
        protocol = "tcp" if conn.type.name == "SOCK_STREAM" else "udp"
        row = {
            "protocol": protocol,
            "local": local,
            "remote": remote,
            "status": conn.status,
            "pid": conn.pid or 0,
        }
        rows[_network_key(row)] = row
    return rows


def snapshot_open_windows() -> dict[str, dict[str, Any]]:
    """Snapshot visible top-level windows with approximate occlusion metadata."""

    rows: list[dict[str, Any]] = []
    user32 = ctypes.windll.user32

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _window_text(hwnd)
        if not title:
            return True
        rect = _window_rect(hwnd)
        if rect["right"] <= rect["left"] or rect["bottom"] <= rect["top"]:
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_name = ""
        try:
            process_name = psutil.Process(int(pid.value)).name()
        except Exception:
            process_name = ""
        rows.append(
            {
                "hwnd": str(int(hwnd)),
                "pid": int(pid.value),
                "process_name": process_name,
                "title_hash": hashlib.sha256(title.encode("utf-8")).hexdigest(),
                "title_preview": title[:80],
                "rect": rect,
                "z_order": len(rows),
                "visible": True,
                "occluded": False,
            }
        )
        return True

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback)
    user32.EnumWindows(enum_proc, 0)
    _mark_occlusion(rows)
    return {row["hwnd"]: row for row in rows}


def open_window_rows_to_events(
    rows: list[dict[str, Any]],
    *,
    host_id: str,
    sequence_start: int,
    previous_event_hash: str,
    batch_id: str,
) -> list[dict]:
    scrubbed = [_scrub_window_row(row) for row in rows]
    event = build_sensor_event(
        sensor_id="windows.open_window.snapshot",
        sensor_class="window",
        host_id=host_id,
        event_type="snapshot",
        sequence=sequence_start,
        cursor={"window_count": len(scrubbed)},
        subject={"window_count": len(scrubbed)},
        payload={"windows": scrubbed},
        previous_event_hash=previous_event_hash,
        confidence="observed",
        privacy_level="metadata",
        writer_id="forge.sensor.window",
        batch_id=batch_id,
        batch_index=0,
    )
    return [event]


def diff_processes(
    previous: dict[int, dict[str, Any]],
    current: dict[int, dict[str, Any]],
    *,
    host_id: str,
    sequence_start: int,
    previous_event_hash: str,
    batch_id: str,
) -> list[dict]:
    events: list[dict] = []
    sequence = sequence_start
    last_hash = previous_event_hash

    for pid in sorted(set(current) - set(previous)):
        event = _build_diff_event(
            sensor_id="windows.process.diff",
            sensor_class="process",
            host_id=host_id,
            sequence=sequence,
            cursor={"pid": pid},
            subject={"pid": pid},
            payload={"state": "started", "process": current[pid]},
            previous_event_hash=last_hash,
            writer_id="forge.sensor.process",
            batch_id=batch_id,
            batch_index=len(events),
        )
        events.append(event)
        last_hash = _event_hash(event)
        sequence += 1

    for pid in sorted(set(previous) - set(current)):
        event = _build_diff_event(
            sensor_id="windows.process.diff",
            sensor_class="process",
            host_id=host_id,
            sequence=sequence,
            cursor={"pid": pid},
            subject={"pid": pid},
            payload={"state": "stopped", "process": previous[pid]},
            previous_event_hash=last_hash,
            writer_id="forge.sensor.process",
            batch_id=batch_id,
            batch_index=len(events),
        )
        events.append(event)
        last_hash = _event_hash(event)
        sequence += 1

    return events


def diff_network_connections(
    previous: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
    *,
    host_id: str,
    sequence_start: int,
    previous_event_hash: str,
    batch_id: str,
) -> list[dict]:
    events: list[dict] = []
    sequence = sequence_start
    last_hash = previous_event_hash

    for key in sorted(set(current) - set(previous)):
        event = _build_diff_event(
            sensor_id="windows.network.diff",
            sensor_class="network",
            host_id=host_id,
            sequence=sequence,
            cursor={"connection": key},
            subject={"connection": key, "pid": current[key].get("pid", 0)},
            payload={"state": "opened", "connection": current[key]},
            previous_event_hash=last_hash,
            writer_id="forge.sensor.network",
            batch_id=batch_id,
            batch_index=len(events),
        )
        events.append(event)
        last_hash = _event_hash(event)
        sequence += 1

    for key in sorted(set(previous) - set(current)):
        event = _build_diff_event(
            sensor_id="windows.network.diff",
            sensor_class="network",
            host_id=host_id,
            sequence=sequence,
            cursor={"connection": key},
            subject={"connection": key, "pid": previous[key].get("pid", 0)},
            payload={"state": "closed", "connection": previous[key]},
            previous_event_hash=last_hash,
            writer_id="forge.sensor.network",
            batch_id=batch_id,
            batch_index=len(events),
        )
        events.append(event)
        last_hash = _event_hash(event)
        sequence += 1

    return events


def diff_open_windows(
    previous: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
    *,
    host_id: str,
    sequence_start: int,
    previous_event_hash: str,
    batch_id: str,
) -> list[dict]:
    events: list[dict] = []
    sequence = sequence_start
    last_hash = previous_event_hash

    for hwnd in sorted(set(previous) & set(current)):
        changed_fields = _window_changed_fields(previous[hwnd], current[hwnd])
        if not changed_fields:
            continue
        event = _build_diff_event(
            sensor_id="windows.open_window.diff",
            sensor_class="window",
            host_id=host_id,
            sequence=sequence,
            cursor={"hwnd": hwnd},
            subject={"hwnd": hwnd, "pid": current[hwnd].get("pid", 0)},
            payload={
                "state": "changed",
                "changed_fields": changed_fields,
                "window": _scrub_window_row(current[hwnd]),
            },
            previous_event_hash=last_hash,
            writer_id="forge.sensor.window",
            batch_id=batch_id,
            batch_index=len(events),
        )
        events.append(event)
        last_hash = _event_hash(event)
        sequence += 1

    for hwnd in sorted(set(previous) - set(current)):
        event = _build_diff_event(
            sensor_id="windows.open_window.diff",
            sensor_class="window",
            host_id=host_id,
            sequence=sequence,
            cursor={"hwnd": hwnd},
            subject={"hwnd": hwnd, "pid": previous[hwnd].get("pid", 0)},
            payload={"state": "closed", "window": _scrub_window_row(previous[hwnd])},
            previous_event_hash=last_hash,
            writer_id="forge.sensor.window",
            batch_id=batch_id,
            batch_index=len(events),
        )
        events.append(event)
        last_hash = _event_hash(event)
        sequence += 1

    for hwnd in sorted(set(current) - set(previous)):
        event = _build_diff_event(
            sensor_id="windows.open_window.diff",
            sensor_class="window",
            host_id=host_id,
            sequence=sequence,
            cursor={"hwnd": hwnd},
            subject={"hwnd": hwnd, "pid": current[hwnd].get("pid", 0)},
            payload={"state": "opened", "window": _scrub_window_row(current[hwnd])},
            previous_event_hash=last_hash,
            writer_id="forge.sensor.window",
            batch_id=batch_id,
            batch_index=len(events),
        )
        events.append(event)
        last_hash = _event_hash(event)
        sequence += 1

    return events


def read_eventlog_records(
    log_name: str,
    *,
    after_record_id: int = 0,
    max_events: int = 100,
) -> list[dict[str, Any]]:
    """Read Windows Event Log records after a cursor.

    This is a metadata reader. It hashes the full message and keeps only a
    short preview so SecureCore can witness Windows without copying whole logs.
    """

    safe_log = json.dumps(log_name)
    script = f"""
$events = Get-WinEvent -LogName {safe_log} -ErrorAction SilentlyContinue |
  Where-Object {{ $_.RecordId -gt {int(after_record_id)} }} |
  Select-Object -First {int(max_events)}
$rows = foreach ($e in $events) {{
  $msg = [string]$e.Message
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $hash = [System.BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
  [pscustomobject]@{{
    log_name = $e.LogName
    record_id = [int64]$e.RecordId
    provider_name = $e.ProviderName
    event_id = [int]$e.Id
    level_display_name = [string]$e.LevelDisplayName
    time_created_utc = if ($e.TimeCreated) {{ $e.TimeCreated.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ') }} else {{ '' }}
    message_hash = $hash
    message_preview = if ($msg.Length -gt 160) {{ $msg.Substring(0, 160) }} else {{ $msg }}
  }}
}}
$rows | ConvertTo-Json -Depth 4
"""
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    payload = json.loads(completed.stdout)
    if isinstance(payload, dict):
        return [payload]
    return list(payload)


def eventlog_records_to_events(
    records: list[dict[str, Any]],
    *,
    host_id: str,
    sequence_start: int,
    previous_event_hash: str,
    batch_id: str,
) -> list[dict]:
    events: list[dict] = []
    sequence = sequence_start
    last_hash = previous_event_hash

    for record in records:
        log_name = str(record.get("log_name", ""))
        observed_at = str(record.get("time_created_utc") or utc_now())
        payload = {
            "log_name": log_name,
            "record_id": int(record.get("record_id", 0)),
            "provider_name": str(record.get("provider_name", "")),
            "event_id": int(record.get("event_id", 0)),
            "level_display_name": str(record.get("level_display_name", "")),
            "message_hash": str(record.get("message_hash", "")),
            "message_preview": str(record.get("message_preview", ""))[:160],
        }
        event = build_sensor_event(
            sensor_id=f"windows.eventlog.{_sensor_log_name(log_name)}",
            sensor_class="eventlog",
            host_id=host_id,
            event_type="snapshot",
            sequence=sequence,
            cursor={"log_name": log_name, "record_id": payload["record_id"]},
            subject={
                "log_name": log_name,
                "provider_name": payload["provider_name"],
                "event_id": payload["event_id"],
            },
            payload=payload,
            previous_event_hash=last_hash,
            confidence="observed",
            privacy_level="metadata",
            writer_id="forge.sensor.eventlog",
            batch_id=batch_id,
            batch_index=len(events),
            observed_at_utc=observed_at,
        )
        events.append(event)
        last_hash = _event_hash(event)
        sequence += 1

    return events


def _build_diff_event(**kwargs) -> dict:
    return build_sensor_event(
        event_type="diff",
        confidence="observed",
        privacy_level="metadata",
        **kwargs,
    )


def _addr(addr) -> str:
    if not addr:
        return ""
    return f"{addr.ip}:{addr.port}"


def _network_key(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("protocol", "")),
            str(row.get("local", "")),
            str(row.get("remote", "")),
            str(row.get("status", "")),
            str(row.get("pid", 0)),
        ]
    )


def _sensor_log_name(log_name: str) -> str:
    cleaned = []
    for char in log_name:
        if char.isalnum() or char in "-.":
            cleaned.append(char)
        elif char.isspace():
            cleaned.append("_")
        else:
            cleaned.append(".")
    return "".join(cleaned).strip(".")


def _window_text(hwnd) -> str:
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _window_rect(hwnd) -> dict[str, int]:
    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    rect = RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return {
        "left": int(rect.left),
        "top": int(rect.top),
        "right": int(rect.right),
        "bottom": int(rect.bottom),
    }


def _mark_occlusion(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows):
        rect = row["rect"]
        for above in rows[:index]:
            if _rect_contains(above["rect"], rect):
                row["occluded"] = True
                break


def _rect_contains(outer: dict[str, int], inner: dict[str, int]) -> bool:
    return (
        outer["left"] <= inner["left"]
        and outer["top"] <= inner["top"]
        and outer["right"] >= inner["right"]
        and outer["bottom"] >= inner["bottom"]
    )


def _scrub_window_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "hwnd": str(row.get("hwnd", "")),
        "pid": int(row.get("pid", 0) or 0),
        "process_name": str(row.get("process_name", "")),
        "title_hash": str(row.get("title_hash", "")),
        "title_preview": str(row.get("title_preview", ""))[:80],
        "rect": dict(row.get("rect", {})),
        "z_order": int(row.get("z_order", 0) or 0),
        "visible": bool(row.get("visible", False)),
        "occluded": bool(row.get("occluded", False)),
    }


def _window_changed_fields(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    fields = ("pid", "process_name", "title_hash", "rect", "z_order", "visible", "occluded")
    return [field for field in fields if previous.get(field) != current.get(field)]


def _event_hash(event: dict) -> str:
    return hashlib.sha256(
        (
            str(event.get("sensor_id", ""))
            + str(event.get("event_id", ""))
            + str(event.get("sequence", ""))
            + payload_hash(event.get("payload", {}))
        ).encode("utf-8")
    ).hexdigest()
