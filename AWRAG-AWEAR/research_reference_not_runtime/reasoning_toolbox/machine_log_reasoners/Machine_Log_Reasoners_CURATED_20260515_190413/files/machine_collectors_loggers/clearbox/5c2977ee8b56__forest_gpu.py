"""GPU execution utilities for Forest AI bridges.

Supports CUDA (NVIDIA) and ROCm (AMD). ROCm builds expose the same
torch.cuda.* API — backend identity lives in gpu_backend.detect_backend().

CPU-only mode is not supported. select_device() raises RuntimeError
if no GPU is available.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

try:
    import torch  # type: ignore
except Exception:  # pragma: no cover
    torch = None

from bridges.gpu_backend import detect_backend, gpu_version_string, run_smi

LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Describes the execution device (CUDA or ROCm — no CPU mode)."""

    type: str  # "cuda" (covers both NVIDIA CUDA and AMD ROCm via compat layer)
    name: str
    index: int = 0

    @property
    def torch_device(self):
        # ROCm builds map to "cuda:N" via the CUDA compatibility layer
        if self.type == "cuda":
            return f"cuda:{self.index}"
        return "cpu"

    @property
    def is_cuda(self) -> bool:
        """True when a GPU is active (CUDA or ROCm — both use torch.cuda API)."""
        return self.type == "cuda"

    @property
    def is_gpu(self) -> bool:
        """Alias for is_cuda — preferred for backend-neutral code."""
        return self.type == "cuda"


def _query_gpu_name() -> str | None:
    """Read the GPU name via the backend smi tool (rocm-smi or nvidia-smi)."""
    raw = run_smi(["--query-gpu=name", "--format=csv,noheader"])  # nvidia-smi form
    if raw is None:
        # ROCm fallback: rocm-smi --showproductname
        raw = run_smi(["--showproductname"])
    if not raw:
        return None
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    return lines[0] if lines else None


def select_device(mode: str = "auto") -> DeviceInfo:
    """Select the execution device.

    Parameters
    ----------
    mode:
        "auto" or "gpu" — requires a GPU (CUDA or ROCm). Raises RuntimeError
        if none is available. CPU fallback is intentionally not supported.
        "cpu" is accepted only for isolated unit tests; production code should
        never pass "cpu".
    """
    mode = (mode or "auto").lower()
    if mode not in {"auto", "gpu", "cpu"}:
        raise ValueError(f"Unsupported device mode '{mode}'.")

    if mode == "cpu":
        LOGGER.warning("CPU mode explicitly requested — GPU acceleration disabled.")
        return DeviceInfo(type="cpu", name="CPU")

    # detect_backend() raises RuntimeError if no GPU / torch missing
    backend = detect_backend()
    index = torch.cuda.current_device()
    name = torch.cuda.get_device_name(index)
    smi_name = _query_gpu_name()
    if smi_name and smi_name != name:
        LOGGER.info("%s device: %s (smi reports: %s)", gpu_version_string(), name, smi_name)
    else:
        LOGGER.info("%s device: %s", gpu_version_string(), name)
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

    # Sync GPU (works for both CUDA and ROCm via torch.cuda compat layer)
    if torch.cuda.is_available():
        torch.cuda.synchronize(device_str)

    return result


__all__ = ["DeviceInfo", "select_device", "compute_window_counts", "to_tensor"]
