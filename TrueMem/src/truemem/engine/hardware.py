from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

MIN_RUNTIME_WORKERS = 4
MIN_SYSTEM_RAM_BYTES = 8 * 1024 * 1024 * 1024
MIN_GPU_RAM_BYTES = 8 * 1024 * 1024 * 1024


def detect_system_resources() -> dict[str, Any]:
    cpu_count = os.cpu_count() or 1
    total_ram: int | None = None
    available_ram: int | None = None
    method = "unavailable"
    if hasattr(os, "sysconf"):
        try:
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            total_pages = int(os.sysconf("SC_PHYS_PAGES"))
            available_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
            total_ram = page_size * total_pages
            available_ram = page_size * available_pages
            method = "posix_sysconf"
        except (OSError, ValueError):
            method = "unavailable"

    # Linux MemAvailable includes reclaimable cache. SC_AVPHYS_PAGES reports
    # free pages and must not be presented as the Linux admission budget.
    if sys.platform.startswith("linux"):
        try:
            fields = {}
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                name, value = line.split(":", 1)
                if name in {"MemTotal", "MemAvailable"}:
                    amount, unit = value.split()
                    if unit != "kB":
                        raise ValueError("unexpected meminfo unit")
                    fields[name] = int(amount) * 1024
            if not 0 <= fields["MemAvailable"] <= fields["MemTotal"]:
                raise ValueError("invalid meminfo memory range")
            total_ram = fields["MemTotal"]
            available_ram = fields["MemAvailable"]
            method = "linux_proc_meminfo_memavailable"
        except (OSError, ValueError, KeyError):
            # Keep the conservative sysconf observation, labeled as such.
            pass

    gpu = _detect_gpu_resources()
    return {
        "logical_cpu_count": int(cpu_count),
        "total_ram_bytes": total_ram,
        "available_ram_bytes": available_ram,
        "ram_detection_method": method,
        **gpu,
    }


def enforce_minimum_runtime_requirements(resources: dict[str, Any], *, require_gpu: bool = False) -> None:
    failures: list[str] = []
    cpu_count = int(resources.get("logical_cpu_count") or 0)
    total_ram = resources.get("total_ram_bytes")
    max_gpu = int(resources.get("max_gpu_memory_bytes") or 0)
    if cpu_count < MIN_RUNTIME_WORKERS:
        failures.append(f"logical_cpu_count={cpu_count} below minimum {MIN_RUNTIME_WORKERS}")
    if not isinstance(total_ram, int) or total_ram < MIN_SYSTEM_RAM_BYTES:
        actual = int(total_ram or 0)
        failures.append(f"system_ram_bytes={actual} below minimum {MIN_SYSTEM_RAM_BYTES}")
    if require_gpu and max_gpu < MIN_GPU_RAM_BYTES:
        failures.append(f"max_gpu_memory_bytes={max_gpu} below minimum {MIN_GPU_RAM_BYTES}")
    if failures:
        raise RuntimeError("MINIMUM_RUNTIME_REQUIREMENTS_NOT_MET: " + "; ".join(failures))


def _detect_gpu_resources() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - hardware/environment dependent
        return {
            "gpu_detection_method": "nvidia-smi_unavailable",
            "gpu_detection_error": str(exc),
            "gpu_devices": [],
            "max_gpu_memory_bytes": 0,
        }
    if completed.returncode != 0:
        return {
            "gpu_detection_method": "nvidia-smi_failed",
            "gpu_detection_error": completed.stderr.strip(),
            "gpu_devices": [],
            "max_gpu_memory_bytes": 0,
        }
    devices = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        if "," not in line:
            continue
        name, memory_mib = line.rsplit(",", 1)
        try:
            memory_bytes = int(memory_mib.strip()) * 1024 * 1024
        except ValueError:
            memory_bytes = 0
        devices.append({
            "name": name.strip(),
            "memory_total_mib": int(memory_mib.strip()) if memory_mib.strip().isdigit() else None,
            "memory_total_bytes": memory_bytes,
        })
    return {
        "gpu_detection_method": "nvidia-smi",
        "gpu_devices": devices,
        "max_gpu_memory_bytes": max((int(row["memory_total_bytes"]) for row in devices), default=0),
    }
