"""GPU and CPU execution utilities for Forest AI bridges.

This module attempts to use PyTorch for CUDA acceleration when available.
It falls back to efficient CPU computations when GPU support is not present.
"""
from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

try:
    import torch  # type: ignore
except Exception:  # pragma: no cover - torch might not be installed
    torch = None

LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Describes the execution device."""

    type: str  # "cuda" or "cpu"
    name: str
    index: int = 0

    @property
    def torch_device(self):
        if self.type == "cuda":
            return f"cuda:{self.index}"
        return "cpu"

    @property
    def is_cuda(self) -> bool:
        return self.type == "cuda"


def _query_gpu_name() -> str | None:
    """Attempt to read the GPU name via nvidia-smi for logging purposes."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[0] if lines else None


def select_device(mode: str = "auto") -> DeviceInfo:
    """Select the execution device based on configuration.

    Parameters
    ----------
    mode:
        "auto" (default) attempts to use CUDA if torch+CUDA is available,
        otherwise falls back to CPU. "gpu" requires CUDA and will raise if
        unavailable. "cpu" forces CPU execution.
    """

    mode = (mode or "auto").lower()
    if mode not in {"auto", "gpu", "cpu"}:
        raise ValueError(f"Unsupported device mode '{mode}'.")

    if mode == "cpu":
        LOGGER.info("Device forced to CPU mode.")
        return DeviceInfo(type="cpu", name="CPU")

    if torch is None:
        if mode == "gpu":
            raise RuntimeError(
                "GPU mode requested but PyTorch is not installed. Install torch with CUDA support."
            )
        LOGGER.warning("PyTorch not available; defaulting to CPU mode.")
        return DeviceInfo(type="cpu", name="CPU")

    if not torch.cuda.is_available():
        if mode == "gpu":
            raise RuntimeError("GPU mode requested but CUDA devices are not available.")
        LOGGER.warning("CUDA not detected by PyTorch; defaulting to CPU mode.")
        return DeviceInfo(type="cpu", name="CPU")

    index = torch.cuda.current_device()
    name = torch.cuda.get_device_name(index)
    smi_name = _query_gpu_name()
    if smi_name and smi_name != name:
        LOGGER.info("CUDA device: %s (nvidia-smi reports %s)", name, smi_name)
    else:
        LOGGER.info("CUDA device: %s", name)
    return DeviceInfo(type="cuda", name=name, index=index)


def to_tensor(values: Iterable[int], device: DeviceInfo):
    """Convert an iterable of integers into a 1-D torch tensor on the device."""
    if torch is None:
        raise RuntimeError("PyTorch is not installed; cannot create tensors.")
    tensor = torch.tensor(list(values), dtype=torch.long)
    if device.is_cuda:
        return tensor.to(device.torch_device, non_blocking=True)
    return tensor


def compute_window_counts(
    token_ids: List[int],
    window: int,
    device: DeviceInfo,
) -> Dict[int, List[Tuple[int, int, int]]]:
    """Compute co-occurrence counts within a +/- window around each focus token.

    Returns a mapping from positional offset (negative for "before", positive for
    "after") to a list of tuples ``(focus_id, context_id, count)``. When CUDA is
    available the heavy lifting is delegated to PyTorch for GPU acceleration.
    """

    if window <= 0:
        raise ValueError("Window size must be positive.")
    if not token_ids:
        return {}

    if torch is None or (not device.is_cuda):
        # CPU fall-back using efficient dictionary updates.
        counts: Dict[int, Dict[Tuple[int, int], int]] = {}
        length = len(token_ids)
        for idx, focus in enumerate(token_ids):
            # Explore backward positions (-window .. -1)
            for offset in range(1, window + 1):
                before_pos = idx - offset
                if before_pos < 0:
                    break
                pair = (focus, token_ids[before_pos])
                counts.setdefault(-offset, {})[pair] = counts.setdefault(-offset, {}).get(pair, 0) + 1
            # Explore forward positions (1 .. window)
            for offset in range(1, window + 1):
                after_pos = idx + offset
                if after_pos >= length:
                    break
                pair = (focus, token_ids[after_pos])
                counts.setdefault(offset, {})[pair] = counts.setdefault(offset, {}).get(pair, 0) + 1
        return {
            offset: [(focus, ctx, cnt) for (focus, ctx), cnt in pairs.items()]
            for offset, pairs in counts.items()
        }

    # GPU path: use vectorized operations in PyTorch.
    device_str = device.torch_device
    focus_tensor = to_tensor(token_ids, device)
    length = focus_tensor.size(0)
    result: Dict[int, List[Tuple[int, int, int]]] = {}

    for offset in range(1, window + 1):
        if offset >= length:
            break
        # Forward (positive offset)
        left = focus_tensor[:-offset]
        right = focus_tensor[offset:]
        pairs = torch.stack([left, right], dim=1)
        unique_pairs, counts = torch.unique(pairs, return_counts=True, dim=0)
        result[offset] = [
            (int(focus), int(ctx), int(count))
            for (focus, ctx), count in zip(unique_pairs.tolist(), counts.tolist())
        ]
        # Backward (negative offset): reuse by swapping order
        left_b = focus_tensor[offset:]
        right_b = focus_tensor[:-offset]
        pairs_b = torch.stack([left_b, right_b], dim=1)
        unique_pairs_b, counts_b = torch.unique(pairs_b, return_counts=True, dim=0)
        result[-offset] = [
            (int(focus), int(ctx), int(count))
            for (focus, ctx), count in zip(unique_pairs_b.tolist(), counts_b.tolist())
        ]

    # Move tensors off device promptly
    if torch.cuda.is_available():
        torch.cuda.synchronize(device_str)

    return result


__all__ = ["DeviceInfo", "select_device", "compute_window_counts", "to_tensor"]
