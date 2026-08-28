"""
ForgeMemoryGPU — GPU-accelerated Forge working memory.

Extends ForgeMemory with GPU-backed operations (ROCm or CUDA via torch.cuda API):
  - Resonance as a GPU tensor (fast batch updates + topk)
  - GPU-accelerated co-occurrence batch computation
  - torch.topk() for chain building

CPU ForgeMemory dict structures remain the authoritative store.
GPU tensors are acceleration overlays — sync'd on demand.
"""

from __future__ import annotations

import logging
from collections import Counter

import torch

from wolf_engine.contracts import ForgeStats, QueryResult, SymbolEvent
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.gpu.device import DeviceInfo, select_device

logger = logging.getLogger(__name__)

# Max symbol index for fixed-size tensors. Symbols beyond this use CPU path.
_MAX_SYMBOL_INDEX = 100_000


class ForgeMemoryGPU(ForgeMemory):
    """ForgeMemory with GPU-accelerated resonance and co-occurrence."""

    def __init__(self, window_size: int = 10000, device: DeviceInfo | None = None):
        super().__init__(window_size=window_size)
        self.device = device or select_device("auto")
        self._gpu_ready = self.device.is_cuda

        if self._gpu_ready:
            # Resonance as float32 tensor on GPU
            self._resonance_tensor = torch.zeros(
                _MAX_SYMBOL_INDEX, dtype=torch.float32, device=self.device.torch_device
            )
            logger.info(
                "ForgeMemoryGPU: GPU active on %s, resonance tensor %s",
                self.device.name, self._resonance_tensor.shape,
            )
        else:
            self._resonance_tensor = None
            logger.info("ForgeMemoryGPU: no GPU detected")

    def ingest(self, symbol_event: SymbolEvent) -> None:
        """Ingest with GPU resonance update."""
        super().ingest(symbol_event)

        if self._gpu_ready and symbol_event.symbol_id < _MAX_SYMBOL_INDEX:
            self._resonance_tensor[symbol_event.symbol_id] += 1.0

    def batch_ingest(self, events: list[SymbolEvent]) -> None:
        """Batch ingest with a single GPU resonance update."""
        # CPU path: ingest each event normally
        for event in events:
            super().ingest(event)

        # GPU path: batch resonance update
        if self._gpu_ready and events:
            ids = [e.symbol_id for e in events if e.symbol_id < _MAX_SYMBOL_INDEX]
            if ids:
                id_tensor = torch.tensor(ids, dtype=torch.long, device=self.device.torch_device)
                self._resonance_tensor.scatter_add_(
                    0, id_tensor, torch.ones_like(id_tensor, dtype=torch.float32)
                )

    def top_resonance(self, k: int = 10) -> list[tuple[int, float]]:
        """Get top-k symbols by resonance using GPU torch.topk()."""
        if self._gpu_ready:
            values, indices = torch.topk(self._resonance_tensor, min(k, _MAX_SYMBOL_INDEX))
            result = []
            for val, idx in zip(values.tolist(), indices.tolist()):
                if val > 0:
                    result.append((idx, val))
            return result

        # CPU fallback
        sorted_res = sorted(self.resonance.items(), key=lambda x: x[1], reverse=True)
        return sorted_res[:k]

    def gpu_co_occurrence_matrix(
        self, symbol_ids: list[int], max_dim: int = 10000
    ) -> torch.Tensor | None:
        """
        Build a sparse co-occurrence matrix on GPU from current state.

        Returns a (max_dim × max_dim) sparse float32 tensor, or None if CPU mode.
        """
        if not self._gpu_ready:
            return None

        rows, cols, vals = [], [], []
        for sid, neighbors in self.co_occurrence.items():
            if sid >= max_dim:
                continue
            for nid, count in neighbors.items():
                if nid >= max_dim:
                    continue
                rows.append(sid)
                cols.append(nid)
                vals.append(float(count))

        if not rows:
            return torch.sparse_coo_tensor(
                indices=torch.empty(2, 0, dtype=torch.long),
                values=torch.empty(0, dtype=torch.float32),
                size=(max_dim, max_dim),
                device=self.device.torch_device,
            )

        indices = torch.tensor([rows, cols], dtype=torch.long, device=self.device.torch_device)
        values = torch.tensor(vals, dtype=torch.float32, device=self.device.torch_device)
        return torch.sparse_coo_tensor(indices, values, size=(max_dim, max_dim))

    def reload_from_events(self, events: list[SymbolEvent]) -> None:
        """Clear and rebuild, including GPU tensors."""
        super().reload_from_events(events)
        if self._gpu_ready:
            self._resonance_tensor.zero_()
            ids = [e.symbol_id for e in events if e.symbol_id < _MAX_SYMBOL_INDEX]
            if ids:
                id_tensor = torch.tensor(ids, dtype=torch.long, device=self.device.torch_device)
                self._resonance_tensor.scatter_add_(
                    0, id_tensor, torch.ones_like(id_tensor, dtype=torch.float32)
                )

    def stats(self) -> ForgeStats:
        """Stats with GPU resonance count."""
        base = super().stats()
        if self._gpu_ready:
            # GPU resonance count for verification
            gpu_nonzero = int((self._resonance_tensor > 0).sum().item())
            logger.debug("GPU resonance nonzero: %d, CPU resonance keys: %d", gpu_nonzero, len(self.resonance))
        return base
