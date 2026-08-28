"""Live sensor reading — maps sensor IDs to psutil / gpu-smi calls.

Batches reads by source for efficiency (one psutil call per group,
one smi subprocess per GPU read batch — rocm-smi for AMD, nvidia-smi for NVIDIA).
"""
from __future__ import annotations

import subprocess
import sys
import time
import platform
from datetime import datetime, timezone
from typing import Any

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    _HAS_PSUTIL = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Source readers (batched) ───────────────────────────────────

def _read_cpu() -> dict[str, Any]:
    """Read all cpu.* sensors in one call."""
    vals: dict[str, Any] = {}
    if not _HAS_PSUTIL:
        return vals
    try:
        vals["cpu.percent"] = psutil.cpu_percent(interval=0)
        per_core = psutil.cpu_percent(interval=0, percpu=True)
        for i, pct in enumerate(per_core):
            vals[f"cpu.core.{i}.percent"] = pct
        vals["cpu.count"] = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        if freq:
            vals["cpu.freq_mhz"] = round(freq.current, 1)
    except Exception:
        pass
    return vals


def _read_ram() -> dict[str, Any]:
    vals: dict[str, Any] = {}
    if not _HAS_PSUTIL:
        return vals
    try:
        mem = psutil.virtual_memory()
        vals["ram.percent"] = mem.percent
        vals["ram.used_gb"] = round(mem.used / (1024**3), 2)
        vals["ram.total_gb"] = round(mem.total / (1024**3), 2)
        vals["ram.available_gb"] = round(mem.available / (1024**3), 2)
    except Exception:
        pass
    return vals


def _read_disk() -> dict[str, Any]:
    vals: dict[str, Any] = {}
    if not _HAS_PSUTIL:
        return vals
    try:
        usage = psutil.disk_usage("/")
        vals["disk.percent"] = usage.percent
        vals["disk.used_gb"] = round(usage.used / (1024**3), 2)
        vals["disk.total_gb"] = round(usage.total / (1024**3), 2)
    except Exception:
        pass
    try:
        counters = psutil.disk_io_counters()
        if counters:
            vals["disk.read_bytes"] = counters.read_bytes
            vals["disk.write_bytes"] = counters.write_bytes
    except Exception:
        pass
    return vals


def _read_net() -> dict[str, Any]:
    vals: dict[str, Any] = {}
    if not _HAS_PSUTIL:
        return vals
    try:
        counters = psutil.net_io_counters()
        if counters:
            vals["net.bytes_sent"] = counters.bytes_sent
            vals["net.bytes_recv"] = counters.bytes_recv
            vals["net.packets_sent"] = counters.packets_sent
            vals["net.packets_recv"] = counters.packets_recv
    except Exception:
        pass
    return vals


def _read_gpu() -> dict[str, Any]:
    """Read GPU sensors via rocm-smi (AMD ROCm) or nvidia-smi (CUDA).

    Uses gpu_backend.query_gpu_json() which normalizes both backends to
    the same key set: name, util_pct, temp_c, mem_used_mb, mem_total_mb, power_w.
    """
    vals: dict[str, Any] = {}
    try:
        from bridges.gpu_backend import query_gpu_json
        stats = query_gpu_json()
        if stats:
            if "name" in stats:
                vals["gpu.name"] = stats["name"]
            if "util_pct" in stats:
                vals["gpu.util_percent"] = stats["util_pct"]
            if "temp_c" in stats:
                vals["gpu.temp_c"] = stats["temp_c"]
            if "mem_used_mb" in stats:
                vals["gpu.mem_used_mb"] = stats["mem_used_mb"]
            if "mem_total_mb" in stats:
                vals["gpu.mem_total_mb"] = stats["mem_total_mb"]
            if "power_w" in stats:
                vals["gpu.power_w"] = stats["power_w"]
    except Exception:
        pass
    return vals


def _read_os() -> dict[str, Any]:
    vals: dict[str, Any] = {}
    if _HAS_PSUTIL:
        try:
            vals["os.uptime_sec"] = round(time.time() - psutil.boot_time())
            vals["os.boot_time"] = psutil.boot_time()
        except Exception:
            pass
    vals["os.platform"] = platform.platform()
    vals["os.python_version"] = sys.version.split()[0]
    return vals


def _read_process() -> dict[str, Any]:
    """Read top-5 CPU and top-5 memory processes."""
    vals: dict[str, Any] = {}
    if not _HAS_PSUTIL:
        return vals
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        vals["proc.count"] = len(procs)

        # Top 5 by CPU
        by_cpu = sorted(procs, key=lambda x: x.get("cpu_percent") or 0, reverse=True)[:5]
        for i, p in enumerate(by_cpu):
            vals[f"proc.top_cpu.{i}.name"] = p.get("name", "unknown")
            vals[f"proc.top_cpu.{i}.percent"] = round(p.get("cpu_percent") or 0, 1)

        # Top 5 by memory
        by_mem = sorted(procs, key=lambda x: x.get("memory_percent") or 0, reverse=True)[:5]
        for i, p in enumerate(by_mem):
            vals[f"proc.top_mem.{i}.name"] = p.get("name", "unknown")
            vals[f"proc.top_mem.{i}.percent"] = round(p.get("memory_percent") or 0, 1)
    except Exception:
        pass
    return vals


# ── Grouped source readers ─────────────────────────────────────
_SOURCE_READERS = {
    "cpu": _read_cpu,
    "ram": _read_ram,
    "disk": _read_disk,
    "net": _read_net,
    "gpu": _read_gpu,
    "os": _read_os,
    "process": _read_process,
}


# ── Public API ─────────────────────────────────────────────────

def read_sensors(
    ids: list[str], catalog: list[dict],
) -> dict[str, dict[str, Any]]:
    """Read live values for the given sensor IDs.

    Returns {id: {value, unit, timestamp, source}} for each readable sensor.
    """
    # Determine which source groups to call
    id_set = set(ids)
    catalog_map = {s["id"]: s for s in catalog}
    needed_groups: set[str] = set()
    for sid in ids:
        sensor = catalog_map.get(sid)
        if sensor:
            needed_groups.add(sensor["category"])

    # Read all needed groups (batched)
    all_vals: dict[str, Any] = {}
    for group in needed_groups:
        reader = _SOURCE_READERS.get(group)
        if reader:
            all_vals.update(reader())

    # Build result for requested IDs only
    ts = _now_iso()
    result: dict[str, dict] = {}
    for sid in ids:
        if sid in all_vals:
            sensor = catalog_map.get(sid, {})
            result[sid] = {
                "value": all_vals[sid],
                "unit": sensor.get("unit", ""),
                "timestamp": ts,
                "source": sensor.get("source", "unknown"),
            }
    return result


def read_with_window(
    ids: list[str], catalog: list[dict],
    window_sec: int = 60, samples: int = 3,
) -> dict[str, dict[str, Any]]:
    """Read sensors multiple times over a window and return aggregates.

    Returns {id: {min, max, avg, latest, unit, samples, source}}.
    """
    if samples < 1:
        samples = 1
    interval = max(window_sec / samples, 0.5) if samples > 1 else 0

    all_readings: dict[str, list] = {sid: [] for sid in ids}

    for i in range(samples):
        snapshot = read_sensors(ids, catalog)
        for sid, reading in snapshot.items():
            val = reading.get("value")
            if isinstance(val, (int, float)):
                all_readings[sid].append(val)
        if i < samples - 1 and interval > 0:
            time.sleep(interval)

    # Build aggregates
    ts = _now_iso()
    catalog_map = {s["id"]: s for s in catalog}
    result: dict[str, dict] = {}
    for sid in ids:
        readings = all_readings.get(sid, [])
        sensor = catalog_map.get(sid, {})
        if readings:
            result[sid] = {
                "min": min(readings),
                "max": max(readings),
                "avg": round(sum(readings) / len(readings), 2),
                "latest": readings[-1],
                "unit": sensor.get("unit", ""),
                "samples": len(readings),
                "source": sensor.get("source", "unknown"),
            }
        else:
            # Non-numeric sensor (e.g. gpu.name, os.platform)
            snapshot = read_sensors([sid], catalog)
            if sid in snapshot:
                result[sid] = {
                    "value": snapshot[sid]["value"],
                    "unit": sensor.get("unit", ""),
                    "samples": 1,
                    "source": sensor.get("source", "unknown"),
                }
    return result
