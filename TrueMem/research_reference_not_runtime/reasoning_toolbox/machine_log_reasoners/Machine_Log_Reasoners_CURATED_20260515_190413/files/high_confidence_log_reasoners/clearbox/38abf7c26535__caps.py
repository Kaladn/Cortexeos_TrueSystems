"""Local machine capability detection — no Clearbox repo deps.

Uses psutil (if available) for cross-platform stats, falls back to stdlib.
GPU detection: tries torch first, then nvidia-smi subprocess.
"""

from __future__ import annotations

import os
import platform
import socket
import subprocess
from typing import Any, Dict


def get_local_caps() -> Dict[str, Any]:
    """Return local machine capabilities for node advertisements."""
    caps: Dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "cpu_cores": os.cpu_count() or 0,
        "ram_gb": _get_ram_gb(),
        "gpu_name": _get_gpu_name(),
        "vram_gb": _get_vram_gb(),
    }
    return caps


def _get_gpu_name() -> str | None:
    # Try torch first (works when running inside Clearbox with model loaded)
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
    except Exception:
        pass
    # Fallback: nvidia-smi (works on any machine with NVIDIA drivers)
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        name = r.stdout.strip().split("\n")[0].strip()
        if name:
            return name
    except Exception:
        pass
    return None


def _get_vram_gb() -> float | None:
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.get_device_properties(0).total_mem / (1024 ** 3), 1)
    except Exception:
        pass
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        mb = float(r.stdout.strip().split("\n")[0].strip())
        return round(mb / 1024, 1)
    except Exception:
        pass
    return None


def _get_ram_gb() -> float:
    """Get total system RAM in GB. psutil → ctypes (Windows) → /proc (Linux)."""
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        pass
    # Windows ctypes fallback
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return round(stat.ullTotalPhys / (1024 ** 3), 1)
    except Exception:
        pass
    # Linux fallback
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return round(kb / (1024 ** 2), 1)
    except Exception:
        pass
    return 0.0


def get_telemetry() -> Dict[str, Any]:
    """Live system utilization — for IoT read-only monitoring."""
    telem: Dict[str, Any] = {"timestamp": __import__("time").time()}
    try:
        import psutil
        telem["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        telem["ram_used_gb"] = round(mem.used / (1024 ** 3), 1)
        telem["ram_total_gb"] = round(mem.total / (1024 ** 3), 1)
        telem["ram_percent"] = mem.percent
        telem["disk_percent"] = psutil.disk_usage("/").percent
    except ImportError:
        telem["error"] = "psutil not installed"
    # GPU utilization via nvidia-smi
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        parts = r.stdout.strip().split(",")
        if len(parts) >= 3:
            telem["gpu_percent"] = float(parts[0].strip())
            telem["vram_used_mb"] = float(parts[1].strip())
            telem["vram_total_mb"] = float(parts[2].strip())
    except Exception:
        pass
    return telem
