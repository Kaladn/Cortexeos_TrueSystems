"""Local machine capability detection using stdlib only."""

from __future__ import annotations

import os
import platform
import socket
from typing import Any, Dict


def get_local_caps() -> Dict[str, Any]:
    """Return local machine capabilities for node advertisements."""
    caps: Dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "cpu_cores": os.cpu_count() or 0,
        "ram_gb": _get_ram_gb(),
        "gpu_name": None,
        "vram_gb": None,
    }

    # Detect GPU — torch.cuda.* works for both NVIDIA CUDA and AMD ROCm builds
    try:
        from bridges.gpu_backend import gpu_available, gpu_device_name, gpu_version_string
        import torch
        if gpu_available():
            caps["gpu_name"] = gpu_device_name(0)
            caps["gpu_backend"] = gpu_version_string()
            caps["vram_gb"] = round(torch.cuda.get_device_properties(0).total_mem / (1024 ** 3), 1)
    except Exception:
        pass

    return caps


def _get_ram_gb() -> float:
    """Get total system RAM in GB."""
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
        return 0.0
