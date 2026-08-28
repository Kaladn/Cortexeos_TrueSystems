"""
GPU Device Detection — CUDA (NVIDIA) and ROCm (AMD).

ROCm PyTorch builds expose the same torch.cuda.* API.
Backend is identified via gpu_backend.detect_backend().

CPU fallback is not supported — select_device() raises RuntimeError
if no GPU is available.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import torch

from bridges.gpu_backend import detect_backend, gpu_version_string

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Encapsulates a compute device (CUDA or ROCm — no CPU mode)."""

    type: str       # "cuda" — covers NVIDIA CUDA and AMD ROCm (compat layer)
    name: str       # e.g. "AMD Radeon RX 7900 XT" or "NVIDIA GeForce RTX 4080"
    index: int = 0  # device index

    @property
    def torch_device(self) -> torch.device:
        # ROCm maps to "cuda:N" via PyTorch HIP compatibility layer
        if self.type == "cuda":
            return torch.device(f"cuda:{self.index}")
        return torch.device("cpu")

    @property
    def is_cuda(self) -> bool:
        """True when GPU active. Works for both NVIDIA CUDA and AMD ROCm."""
        return self.type == "cuda"

    @property
    def is_gpu(self) -> bool:
        """Backend-neutral alias for is_cuda."""
        return self.type == "cuda"

    def __str__(self) -> str:
        if self.is_cuda:
            return f"{self.name} ({gpu_version_string()}, index:{self.index})"
        return "cpu"


def select_device(mode: str = "auto") -> DeviceInfo:
    """
    Select compute device. Requires a GPU — raises if unavailable.

    Args:
        mode: "auto" or "gpu" (GPU required), "cpu" (test-only, not for production)

    Raises:
        RuntimeError: if no GPU is available.
    """
    if mode == "cpu":
        logger.warning("CPU mode explicitly requested — GPU acceleration disabled.")
        return DeviceInfo(type="cpu", name="cpu")

    # detect_backend() raises RuntimeError if no GPU / torch not installed
    detect_backend()

    idx = torch.cuda.current_device()
    name = torch.cuda.get_device_name(idx)
    props = torch.cuda.get_device_properties(idx)
    vram_gb = props.total_memory / (1024 ** 3)
    logger.info("Device: %s (%.1f GB VRAM, %s)", name, vram_gb, gpu_version_string())
    return DeviceInfo(type="cuda", name=name, index=idx)


def to_tensor(values: list[int], device: DeviceInfo) -> torch.Tensor:
    """Convert a list of ints to a torch.long tensor on the given device."""
    t = torch.tensor(values, dtype=torch.long)
    if device.is_cuda:
        return t.to(device.torch_device, non_blocking=True)
    return t
