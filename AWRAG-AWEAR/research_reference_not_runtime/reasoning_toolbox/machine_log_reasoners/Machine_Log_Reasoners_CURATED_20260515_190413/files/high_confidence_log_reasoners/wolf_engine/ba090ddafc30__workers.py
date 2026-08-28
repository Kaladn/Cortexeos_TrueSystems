"""
Evidence Workers — Concrete telemetry collectors.

Phase 3 ships 4 workers (plan called for starting with 4, not 13):
  1. SystemPerfWorker  — CPU/RAM/GPU temps via psutil (all nodes)
  2. NetworkLoggerWorker — Inter-node ping and connectivity (Node 3)
  3. ProcessLoggerWorker — Running processes, resource hogs (all nodes)
  4. InputLoggerWorker  — Aggregate input activity patterns (game machine)

All workers subclass WorkerBase and implement collect().
Workers gracefully degrade if optional dependencies (psutil, GPUtil) are missing.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import time
from typing import Any

from wolf_engine.evidence.worker_base import WorkerBase

logger = logging.getLogger(__name__)

# Try importing psutil — graceful fallback if not installed
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    _HAS_PSUTIL = False
    logger.warning("psutil not available — SystemPerfWorker and ProcessLoggerWorker will emit limited data")


class SystemPerfWorker(WorkerBase):
    """Collects CPU, RAM, disk, and (optionally) GPU metrics."""

    worker_name = "system_perf"

    def collect(self) -> list[dict[str, Any]]:
        data: dict[str, Any] = {"event_type": "system_perf"}

        if _HAS_PSUTIL:
            data["cpu_percent"] = psutil.cpu_percent(interval=None)
            data["cpu_count"] = psutil.cpu_count()

            mem = psutil.virtual_memory()
            data["ram_total_gb"] = round(mem.total / (1024 ** 3), 2)
            data["ram_used_gb"] = round(mem.used / (1024 ** 3), 2)
            data["ram_percent"] = mem.percent

            disk = psutil.disk_usage("/")
            data["disk_total_gb"] = round(disk.total / (1024 ** 3), 2)
            data["disk_used_percent"] = disk.percent

            # CPU temps (platform-dependent, may not be available)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Take first available sensor group
                    first_group = next(iter(temps.values()))
                    data["cpu_temp_c"] = first_group[0].current if first_group else None
            except (AttributeError, StopIteration):
                data["cpu_temp_c"] = None
        else:
            data["cpu_percent"] = None
            data["ram_percent"] = None
            data["note"] = "psutil not installed"

        # GPU via torch — torch.cuda.* works for both NVIDIA CUDA and AMD ROCm builds
        try:
            import torch
            if torch.cuda.is_available():
                idx = torch.cuda.current_device()
                data["gpu_name"] = torch.cuda.get_device_name(idx)
                mem_alloc = torch.cuda.memory_allocated(idx)
                mem_total = torch.cuda.get_device_properties(idx).total_memory
                data["gpu_mem_used_gb"] = round(mem_alloc / (1024 ** 3), 2)
                data["gpu_mem_total_gb"] = round(mem_total / (1024 ** 3), 2)
        except Exception:
            pass

        return [data]


class NetworkLoggerWorker(WorkerBase):
    """Pings configured cluster nodes and records latency."""

    worker_name = "network_logger"

    def __init__(self, targets: list[str] | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.targets = targets or ["192.168.1.10", "192.168.1.11", "192.168.1.12"]

    def collect(self) -> list[dict[str, Any]]:
        results = []
        for target in self.targets:
            data: dict[str, Any] = {
                "event_type": "network_ping",
                "target": target,
            }
            latency = self._ping(target)
            data["latency_ms"] = latency
            data["reachable"] = latency is not None
            results.append(data)
        return results

    @staticmethod
    def _ping(host: str, timeout: int = 2) -> float | None:
        """Ping a host and return latency in ms, or None if unreachable."""
        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
            else:
                cmd = ["ping", "-c", "1", "-W", str(timeout), host]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 2
            )
            if result.returncode == 0:
                # Parse latency from output
                output = result.stdout
                if "time=" in output:
                    # Extract "time=X.Xms" or "time=X.X ms"
                    for part in output.split():
                        if part.startswith("time=") or part.startswith("time<"):
                            ms_str = part.split("=")[-1].split("<")[-1]
                            ms_str = ms_str.replace("ms", "").strip()
                            return float(ms_str)
            return None
        except (subprocess.TimeoutExpired, OSError, ValueError):
            return None


class ProcessLoggerWorker(WorkerBase):
    """Logs top processes by CPU and memory usage."""

    worker_name = "process_logger"

    def __init__(self, top_n: int = 10, **kwargs: Any):
        super().__init__(**kwargs)
        self.top_n = top_n

    def collect(self) -> list[dict[str, Any]]:
        if not _HAS_PSUTIL:
            return [{"event_type": "process_snapshot", "note": "psutil not installed", "processes": []}]

        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_percent": round(info["memory_percent"] or 0.0, 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by CPU usage, take top N
        procs.sort(key=lambda p: p["cpu_percent"], reverse=True)
        top_procs = procs[: self.top_n]

        return [{
            "event_type": "process_snapshot",
            "total_processes": len(procs),
            "processes": top_procs,
        }]


class InputLoggerWorker(WorkerBase):
    """
    Logs aggregate input activity patterns.

    On Windows, uses GetLastInputInfo to detect idle duration.
    On other platforms, emits a basic uptime metric.
    Adapted from unzipped_cleanup/activity_logger.py.
    """

    worker_name = "input_logger"

    def collect(self) -> list[dict[str, Any]]:
        data: dict[str, Any] = {"event_type": "input_activity"}

        if platform.system().lower() == "windows":
            idle_sec = self._windows_idle_seconds()
            data["idle_seconds"] = idle_sec
            data["active"] = idle_sec < 60  # Active if input within last minute
            data["active_window"] = self._windows_active_window()
        else:
            # Non-Windows: basic uptime via /proc/uptime
            data["idle_seconds"] = None
            data["active"] = None
            data["note"] = "Non-Windows platform, limited input data"

        return [data]

    @staticmethod
    def _windows_idle_seconds() -> float:
        """Get seconds since last user input on Windows."""
        try:
            import ctypes
            import ctypes.wintypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.wintypes.UINT),
                    ("dwTime", ctypes.wintypes.DWORD),
                ]

            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return millis / 1000.0
        except Exception:
            return -1.0

    @staticmethod
    def _windows_active_window() -> str | None:
        """Get the title of the active window on Windows."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value if buf.value else None
        except Exception:
            return None
