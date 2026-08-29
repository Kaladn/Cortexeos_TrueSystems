"""Small Linux-native process, memory, and graphics inventory helpers."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Any


def memory_snapshot() -> dict[str, int | None]:
    values: dict[str, str] = {}
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition(":")
            if separator:
                values[key] = value.strip()
    except OSError:
        pass

    def byte_value(key: str) -> int | None:
        parts = values.get(key, "").split()
        return int(parts[0]) * 1024 if parts and parts[0].isdigit() else None

    meminfo: dict[str, str] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition(":")
            if separator:
                meminfo[key] = value.strip()
    except OSError:
        pass

    def system_bytes(key: str) -> int | None:
        parts = meminfo.get(key, "").split()
        return int(parts[0]) * 1024 if parts and parts[0].isdigit() else None

    return {
        "working_set_bytes": byte_value("VmRSS"),
        "peak_working_set_bytes": byte_value("VmHWM"),
        "pagefile_usage_bytes": byte_value("VmSwap"),
        "private_usage_bytes": byte_value("RssAnon"),
        "system_available_physical_bytes": system_bytes("MemAvailable"),
        "system_total_physical_bytes": system_bytes("MemTotal"),
    }


def gpu_entries() -> list[dict[str, Any]]:
    try:
        completed = subprocess.run(["lspci", "-mm"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return []
    return [
        {"description": line}
        for line in completed.stdout.splitlines()
        if "VGA compatible controller" in line or "3D controller" in line
    ]


def hardware_snapshot() -> dict[str, Any]:
    memory = memory_snapshot()
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_logical": os.cpu_count(),
        "ram_total_bytes": memory["system_total_physical_bytes"],
        "ram_available_bytes_at_start": memory["system_available_physical_bytes"],
        "gpu_adapters_detected": gpu_entries(),
    }
