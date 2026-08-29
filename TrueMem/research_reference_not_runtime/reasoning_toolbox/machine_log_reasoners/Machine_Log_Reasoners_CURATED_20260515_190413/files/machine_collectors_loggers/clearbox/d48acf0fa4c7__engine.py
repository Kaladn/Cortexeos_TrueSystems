"""
System Pulse Plugin — Engine
Reads CPU, RAM, disk, GPU (AMD ROCm via rocm-smi or psutil fallback).
All methods synchronous — call from asyncio.to_thread().
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SystemPulseEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []
        self._max_history = 120  # 2 min at 1s intervals
        self._rocm_available: Optional[bool] = None
        logger.info("SystemPulseEngine initialised")

    # ── Snapshot ──────────────────────────────────────────────────────────────
    def snapshot(self) -> Dict[str, Any]:
        """Full system snapshot — CPU, RAM, disk, GPU."""
        import psutil
        now = time.time()

        cpu_pct = psutil.cpu_percent(interval=0.2)
        cpu_freq = psutil.cpu_freq()
        cpu_count = psutil.cpu_count(logical=True)
        cpu_physical = psutil.cpu_count(logical=False)

        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "mountpoint": part.mountpoint,
                    "device": part.device,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / 1e9, 1),
                    "used_gb":  round(usage.used  / 1e9, 1),
                    "free_gb":  round(usage.free  / 1e9, 1),
                    "pct":      usage.percent,
                })
            except Exception:
                pass

        gpu = self._gpu_stats()

        snap = {
            "ts": now,
            "cpu": {
                "pct": cpu_pct,
                "cores_logical": cpu_count,
                "cores_physical": cpu_physical,
                "freq_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
                "freq_max_mhz": round(cpu_freq.max, 0) if cpu_freq else None,
            },
            "ram": {
                "total_gb":     round(mem.total    / 1e9, 2),
                "used_gb":      round(mem.used     / 1e9, 2),
                "available_gb": round(mem.available/ 1e9, 2),
                "pct":          mem.percent,
            },
            "swap": {
                "total_gb": round(swap.total / 1e9, 2),
                "used_gb":  round(swap.used  / 1e9, 2),
                "pct":      swap.percent,
            },
            "disks": disks,
            "gpu": gpu,
        }

        with self._lock:
            self._history.append({"ts": now, "cpu_pct": cpu_pct, "ram_pct": mem.percent})
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        return snap

    def history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)

    def status(self) -> Dict[str, Any]:
        return {"ok": True, "plugin_id": "system_pulse", "version": "0.1.0", "rocm_available": self._rocm_available or False}

    # ── GPU (AMD ROCm) ────────────────────────────────────────────────────────
    def _gpu_stats(self) -> Dict[str, Any]:
        # Try rocm-smi first (AMD)
        if self._rocm_available is None:
            self._rocm_available = shutil.which("rocm-smi") is not None

        if self._rocm_available:
            return self._rocm_stats()
        return self._psutil_gpu()

    def _rocm_stats(self) -> Dict[str, Any]:
        """Parse rocm-smi --showuse --showmeminfo vram --json output."""
        try:
            result = subprocess.run(
                ["rocm-smi", "--showuse", "--showmeminfo", "vram", "--json"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr)
            import json
            data = json.loads(result.stdout)
            # rocm-smi JSON format varies by version; try to extract key fields
            gpus = []
            for card_key, card_data in data.items():
                if not card_key.startswith("card"):
                    continue
                gpu_use  = card_data.get("GPU use (%)", card_data.get("GPU Use (%)", 0))
                mem_use  = card_data.get("VRAM Total Memory (B)", 0)
                mem_used = card_data.get("VRAM Total Used Memory (B)", 0)
                gpus.append({
                    "id": card_key,
                    "driver": "ROCm",
                    "pct": float(gpu_use) if gpu_use else 0.0,
                    "vram_total_gb": round(int(mem_use)  / 1e9, 2) if mem_use  else None,
                    "vram_used_gb":  round(int(mem_used) / 1e9, 2) if mem_used else None,
                    "vram_pct": round(int(mem_used)/int(mem_use)*100, 1) if mem_use and mem_used and int(mem_use) > 0 else None,
                })
            return {"driver": "ROCm", "gpus": gpus, "error": None}
        except Exception as exc:
            return {"driver": "ROCm", "gpus": [], "error": str(exc)}

    def _psutil_gpu(self) -> Dict[str, Any]:
        """Fallback: no GPU data without ROCm or nvidia-smi."""
        return {"driver": None, "gpus": [], "error": "rocm-smi not found; GPU stats unavailable"}
