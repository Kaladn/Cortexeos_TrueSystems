"""GPU backend detection — CUDA (NVIDIA) and ROCm (AMD).

ROCm PyTorch builds still expose the full torch.cuda.* API surface.
Backend identity comes from torch.version.hip (ROCm) vs torch.version.cuda (NVIDIA).

Forest AI requires a GPU. CPU-only mode is not supported — callers that
need a fallback must handle RuntimeError themselves.
"""
from __future__ import annotations

import json
import subprocess
from typing import Literal

try:
    import torch  # type: ignore
except ImportError:
    torch = None  # type: ignore[assignment]

BackendType = Literal["cuda", "rocm"]


def detect_backend() -> BackendType:
    """Identify the active GPU compute backend.

    Returns "rocm" if torch was built with ROCm/HIP, "cuda" for NVIDIA.
    Raises RuntimeError if torch is missing or no GPU is available.
    """
    if torch is None:
        raise RuntimeError(
            "PyTorch is not installed. "
            "Clearbox AI Studio requires torch with ROCm (AMD) or CUDA (NVIDIA) support."
        )
    if not torch.cuda.is_available():
        raise RuntimeError(
            "No GPU detected. Clearbox AI Studio requires a ROCm (AMD) or CUDA (NVIDIA) GPU. "
            "CPU-only mode is not supported."
        )
    if getattr(torch.version, "hip", None):
        return "rocm"
    if getattr(torch.version, "cuda", None):
        return "cuda"
    # GPU present but no version string — default to cuda (covers some edge builds)
    return "cuda"


def gpu_available() -> bool:
    """Return True if a GPU is available (CUDA or ROCm)."""
    return torch is not None and torch.cuda.is_available()


def gpu_device_name(index: int = 0) -> str:
    """Return GPU device name. Works identically for CUDA and ROCm."""
    return torch.cuda.get_device_name(index)


def gpu_version_string() -> str:
    """Return compute backend version: 'ROCm X.Y' or 'CUDA X.Y'."""
    hip = getattr(getattr(torch, "version", None), "hip", None)
    if hip:
        return f"ROCm {hip}"
    cuda = getattr(getattr(torch, "version", None), "cuda", None)
    if cuda:
        return f"CUDA {cuda}"
    return "GPU (version unknown)"


def _is_rocm() -> bool:
    return bool(getattr(getattr(torch, "version", None), "hip", None))


def run_smi(args: list[str]) -> str | None:
    """Run rocm-smi (AMD) or nvidia-smi (NVIDIA) with the given args.

    Returns stdout on success, None on failure / tool not found.
    """
    tool = "rocm-smi" if _is_rocm() else "nvidia-smi"
    try:
        r = subprocess.run(
            [tool, *args],
            check=False, capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def query_gpu_csv(fields: str) -> str | None:
    """Query GPU stats in CSV form.

    CUDA:  runs nvidia-smi --query-gpu=<fields> --format=csv,noheader,nounits
    ROCm:  runs rocm-smi --showallinfo --json (fields arg unused; parse JSON yourself)
    """
    if _is_rocm():
        return run_smi(["--showallinfo", "--json"])
    return run_smi([f"--query-gpu={fields}", "--format=csv,noheader,nounits"])


def query_gpu_json() -> dict | None:
    """Return normalized GPU stats — same keys regardless of backend.

    Keys (all optional): name, util_pct, temp_c, mem_used_mb, mem_total_mb, power_w

    ROCm: rocm-smi --showallinfo --json  (7900 XT field names handled)
    CUDA: nvidia-smi CSV
    """
    if _is_rocm():
        raw = run_smi(["--showallinfo", "--json"])
        if not raw:
            return None
        try:
            data = json.loads(raw)
            card = next((v for k, v in data.items() if k.startswith("card")), None)
            if not card:
                return None
            result: dict = {}
            for name_key in ("Card Series", "Card model", "GPU ID"):
                if name_key in card:
                    result["name"] = str(card[name_key])
                    break
            for util_key in ("GPU use (%)", "GPU Activity (%)"):
                if util_key in card:
                    try:
                        result["util_pct"] = float(str(card[util_key]).strip())
                    except ValueError:
                        pass
                    break
            for temp_key in ("Temperature (Sensor edge) (C)", "GFX Temperature (C)",
                             "Junction Temperature (C)"):
                if temp_key in card:
                    try:
                        result["temp_c"] = float(str(card[temp_key]).strip())
                    except ValueError:
                        pass
                    break
            for used_key in ("VRAM Total Used Memory (B)",):
                if used_key in card:
                    try:
                        result["mem_used_mb"] = round(float(card[used_key]) / (1024 ** 2), 1)
                    except (ValueError, TypeError):
                        pass
                    break
            for total_key in ("VRAM Total Memory (B)",):
                if total_key in card:
                    try:
                        result["mem_total_mb"] = round(float(card[total_key]) / (1024 ** 2), 1)
                    except (ValueError, TypeError):
                        pass
                    break
            for pwr_key in ("Average Graphics Package Power (W)",
                            "Current Socket Graphics Package Power (W)"):
                if pwr_key in card:
                    try:
                        result["power_w"] = float(str(card[pwr_key]).strip())
                    except ValueError:
                        pass
                    break
            return result or None
        except (json.JSONDecodeError, StopIteration):
            return None
    else:
        raw = run_smi([
            "--query-gpu=name,utilization.gpu,temperature.gpu,"
            "memory.used,memory.total,power.draw",
            "--format=csv,noheader,nounits",
        ])
        if not raw:
            return None
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < 6:
            return None
        result = {}
        result["name"] = parts[0]
        for key, idx in (("util_pct", 1), ("temp_c", 2), ("mem_used_mb", 3),
                         ("mem_total_mb", 4), ("power_w", 5)):
            try:
                result[key] = float(parts[idx])
            except (ValueError, IndexError):
                pass
        return result


__all__ = [
    "BackendType",
    "detect_backend",
    "gpu_available",
    "gpu_device_name",
    "gpu_version_string",
    "run_smi",
    "query_gpu_csv",
    "query_gpu_json",
]
