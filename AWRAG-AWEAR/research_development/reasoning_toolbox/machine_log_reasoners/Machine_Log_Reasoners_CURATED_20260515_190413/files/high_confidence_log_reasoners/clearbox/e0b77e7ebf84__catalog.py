"""Sensor catalog: discover all available machine sensors with metadata.

Catalog is built once on startup and cached in memory.
Each sensor is a dict with: id, name, category, unit, source, description, risk_tag.
"""
from __future__ import annotations

import platform
import subprocess
import sys
import time
from typing import Any

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    _HAS_PSUTIL = False

# ── Module-level cache ─────────────────────────────────────────
_catalog_cache: list[dict] | None = None


def _sensor(
    sid: str, name: str, category: str, unit: str,
    source: str, description: str, risk_tag: str = "low",
) -> dict:
    return {
        "id": sid, "name": name, "category": category,
        "unit": unit, "source": source, "description": description,
        "risk_tag": risk_tag,
    }


# ── Discovery functions ────────────────────────────────────────

def _discover_cpu() -> list[dict]:
    sensors = [_sensor("cpu.percent", "CPU Usage", "cpu", "%", "psutil",
                       "Overall CPU utilization percentage")]
    if not _HAS_PSUTIL:
        return sensors
    try:
        core_count = psutil.cpu_count(logical=True) or 0
        sensors.append(_sensor("cpu.count", "CPU Core Count", "cpu", "cores",
                               "psutil", "Number of logical CPU cores"))
        for i in range(core_count):
            sensors.append(_sensor(
                f"cpu.core.{i}.percent", f"Core {i} Usage", "cpu", "%",
                "psutil", f"CPU core {i} utilization percentage",
            ))
        freq = psutil.cpu_freq()
        if freq:
            sensors.append(_sensor("cpu.freq_mhz", "CPU Frequency", "cpu", "MHz",
                                   "psutil", "Current CPU frequency"))
    except Exception:
        pass
    return sensors


def _discover_ram() -> list[dict]:
    return [
        _sensor("ram.percent", "RAM Usage", "ram", "%", "psutil",
                "RAM utilization percentage"),
        _sensor("ram.used_gb", "RAM Used", "ram", "GB", "psutil",
                "RAM currently in use"),
        _sensor("ram.total_gb", "RAM Total", "ram", "GB", "psutil",
                "Total installed RAM"),
        _sensor("ram.available_gb", "RAM Available", "ram", "GB", "psutil",
                "RAM available for allocation"),
    ]


def _discover_disk() -> list[dict]:
    sensors = [
        _sensor("disk.percent", "Disk Usage", "disk", "%", "psutil",
                "Primary disk utilization percentage"),
        _sensor("disk.used_gb", "Disk Used", "disk", "GB", "psutil",
                "Disk space in use"),
        _sensor("disk.total_gb", "Disk Total", "disk", "GB", "psutil",
                "Total disk capacity"),
    ]
    if _HAS_PSUTIL:
        try:
            counters = psutil.disk_io_counters()
            if counters:
                sensors.extend([
                    _sensor("disk.read_bytes", "Disk Read Bytes", "disk", "bytes",
                            "psutil", "Cumulative bytes read from disk"),
                    _sensor("disk.write_bytes", "Disk Write Bytes", "disk", "bytes",
                            "psutil", "Cumulative bytes written to disk"),
                ])
        except Exception:
            pass
    return sensors


def _discover_net() -> list[dict]:
    sensors = []
    if _HAS_PSUTIL:
        try:
            counters = psutil.net_io_counters()
            if counters:
                sensors.extend([
                    _sensor("net.bytes_sent", "Network Bytes Sent", "net", "bytes",
                            "psutil", "Cumulative bytes sent", "med"),
                    _sensor("net.bytes_recv", "Network Bytes Received", "net", "bytes",
                            "psutil", "Cumulative bytes received", "med"),
                    _sensor("net.packets_sent", "Network Packets Sent", "net", "packets",
                            "psutil", "Cumulative packets sent", "med"),
                    _sensor("net.packets_recv", "Network Packets Received", "net", "packets",
                            "psutil", "Cumulative packets received", "med"),
                ])
        except Exception:
            pass
    return sensors


def _discover_gpu() -> list[dict]:
    """Discover GPU sensors via rocm-smi (AMD ROCm) or nvidia-smi (CUDA)."""
    sensors = []
    try:
        from bridges.gpu_backend import query_gpu_json
        stats = query_gpu_json()
        if stats:
            source = "rocm-smi" if _is_rocm_backend() else "nvidia-smi"
            sensors.extend([
                _sensor("gpu.name", "GPU Name", "gpu", "", source,
                        "GPU model name"),
                _sensor("gpu.util_percent", "GPU Utilization", "gpu", "%", source,
                        "GPU core utilization percentage"),
                _sensor("gpu.temp_c", "GPU Temperature", "gpu", "C", source,
                        "GPU die temperature"),
                _sensor("gpu.mem_used_mb", "GPU Memory Used", "gpu", "MiB", source,
                        "GPU VRAM in use"),
                _sensor("gpu.mem_total_mb", "GPU Memory Total", "gpu", "MiB", source,
                        "Total GPU VRAM"),
                _sensor("gpu.power_w", "GPU Power Draw", "gpu", "W", source,
                        "GPU power consumption"),
            ])
    except Exception:
        pass
    return sensors


def _is_rocm_backend() -> bool:
    try:
        import torch
        return bool(getattr(getattr(torch, "version", None), "hip", None))
    except Exception:
        return False


def _discover_os() -> list[dict]:
    return [
        _sensor("os.uptime_sec", "System Uptime", "os", "sec", "psutil",
                "Seconds since last boot"),
        _sensor("os.boot_time", "Boot Time", "os", "epoch", "psutil",
                "System boot time as Unix timestamp"),
        _sensor("os.platform", "Platform", "os", "", "stdlib",
                "Operating system platform string"),
        _sensor("os.python_version", "Python Version", "os", "", "stdlib",
                "Python interpreter version"),
    ]


def _discover_process() -> list[dict]:
    sensors = [
        _sensor("proc.count", "Process Count", "process", "count", "psutil",
                "Number of running processes", "med"),
    ]
    for i in range(5):
        sensors.extend([
            _sensor(f"proc.top_cpu.{i}.name", f"Top CPU #{i+1} Name", "process",
                    "", "psutil", f"Process #{i+1} by CPU usage — name", "med"),
            _sensor(f"proc.top_cpu.{i}.percent", f"Top CPU #{i+1} %", "process",
                    "%", "psutil", f"Process #{i+1} by CPU usage — percent", "med"),
        ])
    for i in range(5):
        sensors.extend([
            _sensor(f"proc.top_mem.{i}.name", f"Top Memory #{i+1} Name", "process",
                    "", "psutil", f"Process #{i+1} by memory usage — name", "med"),
            _sensor(f"proc.top_mem.{i}.percent", f"Top Memory #{i+1} %", "process",
                    "%", "psutil", f"Process #{i+1} by memory usage — percent", "med"),
        ])
    return sensors


# ── Public API ─────────────────────────────────────────────────

def build_catalog() -> list[dict]:
    """Discover all available sensors on this machine."""
    sensors: list[dict] = []
    sensors.extend(_discover_cpu())
    sensors.extend(_discover_ram())
    sensors.extend(_discover_disk())
    sensors.extend(_discover_net())
    sensors.extend(_discover_gpu())
    sensors.extend(_discover_os())
    sensors.extend(_discover_process())
    return sensors


def get_catalog(force_refresh: bool = False) -> list[dict]:
    """Return the cached catalog, building it on first call."""
    global _catalog_cache
    if _catalog_cache is None or force_refresh:
        _catalog_cache = build_catalog()
    return _catalog_cache


def get_categories(catalog: list[dict] | None = None) -> dict[str, int]:
    """Return {category: count} summary."""
    cat = catalog or get_catalog()
    counts: dict[str, int] = {}
    for s in cat:
        c = s["category"]
        counts[c] = counts.get(c, 0) + 1
    return counts


def get_sensor_by_id(sensor_id: str, catalog: list[dict] | None = None) -> dict | None:
    """Lookup a single sensor by ID."""
    cat = catalog or get_catalog()
    for s in cat:
        if s["id"] == sensor_id:
            return s
    return None
