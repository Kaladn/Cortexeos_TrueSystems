"""
GPU Window Engine — 6-1-6 Co-occurrence Computation.

Ported from forest_ai/bridges/forest_gpu.py (compute_window_counts).
Uses torch.stack() + torch.unique() on paired tensors to count
co-occurrences at each offset in a single GPU kernel call.

CPU fallback: pure Python dictionary approach (same results, slower).
"""

from __future__ import annotations

from collections import Counter

import torch

from wolf_engine.gpu.device import DeviceInfo, to_tensor


def compute_window_counts(
    symbol_ids: list[int],
    window: int,
    device: DeviceInfo,
) -> dict[int, Counter]:
    """
    Compute co-occurrence counts for each symbol across a sliding window.

    For each offset 1..window, counts how many times (focus, context) pairs
    appear in both forward and backward directions.

    Args:
        symbol_ids: Ordered list of symbol IDs from a session/pulse stream.
        window: Context window size (6 for 6-1-6).
        device: DeviceInfo for compute device selection.

    Returns:
        Dict mapping symbol_id → Counter of {neighbor_id: count}.
    """
    if len(symbol_ids) < 2:
        return {}

    if device.is_cuda:
        return _gpu_window_counts(symbol_ids, window, device)
    return _cpu_window_counts(symbol_ids, window)


def _gpu_window_counts(
    symbol_ids: list[int],
    window: int,
    device: DeviceInfo,
) -> dict[int, Counter]:
    """GPU path: torch.unique on stacked pairs per offset."""
    ids = to_tensor(symbol_ids, device)
    n = ids.size(0)
    result: dict[int, Counter] = {}

    for offset in range(1, window + 1):
        if offset >= n:
            break

        # Forward pairs: (focus[i], context[i+offset])
        focus = ids[:n - offset]
        context = ids[offset:]
        pairs = torch.stack([focus, context], dim=1)
        unique_pairs, counts = torch.unique(pairs, return_counts=True, dim=0)

        # Accumulate into result
        for pair, count in zip(unique_pairs.tolist(), counts.tolist()):
            fid, cid = pair
            if fid not in result:
                result[fid] = Counter()
            result[fid][cid] += count

        # Backward pairs: (context[i+offset], focus[i])
        pairs_back = torch.stack([context, focus], dim=1)
        unique_back, counts_back = torch.unique(pairs_back, return_counts=True, dim=0)

        for pair, count in zip(unique_back.tolist(), counts_back.tolist()):
            fid, cid = pair
            if fid not in result:
                result[fid] = Counter()
            result[fid][cid] += count

    if device.is_cuda:
        torch.cuda.synchronize(device.torch_device)

    return result


def _cpu_window_counts(
    symbol_ids: list[int],
    window: int,
) -> dict[int, Counter]:
    """CPU fallback: pure Python dictionary approach."""
    n = len(symbol_ids)
    result: dict[int, Counter] = {}

    for i in range(n):
        fid = symbol_ids[i]
        if fid not in result:
            result[fid] = Counter()

        # Forward window
        for j in range(i + 1, min(i + window + 1, n)):
            cid = symbol_ids[j]
            result[fid][cid] += 1

        # Backward window
        for j in range(max(0, i - window), i):
            cid = symbol_ids[j]
            result[fid][cid] += 1

    return result
