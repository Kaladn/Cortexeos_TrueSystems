"""
NCV-73 Batch Generator — GPU-accelerated feature vector construction.

Generalized from causal_analyzer.py._generate_ncv_73().
Original was finance-specific (close/volume/high/low). This version is
domain-agnostic: each context position contributes 6 features derived
from the symbol's resonance and co-occurrence in Forge.

Vector layout (73 dimensions):
  [0:36]  — 6 preceding context symbols × 6 features each
  [36]    — anchor symbol feature (resonance)
  [37:73] — 6 following context symbols × 6 features each

Features per position (6):
  0: symbol_id (normalized by max_id)
  1: resonance score
  2: co-occurrence count with anchor
  3: position distance from anchor (1-6, normalized)
  4: context density (how many co-occurrences this symbol has total)
  5: uniqueness (1/resonance, capped at 1.0)
"""

from __future__ import annotations

import torch

from wolf_engine.contracts import SymbolEvent
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.gpu.device import DeviceInfo

NCV_DIM = 73
FEATURES_PER_POSITION = 6
CONTEXT_POSITIONS = 6


def generate_ncv_73(
    event: SymbolEvent,
    forge: ForgeMemory,
    max_symbol_id: float = 1e10,
) -> list[float]:
    """
    Generate a 73-dimensional feature vector for a single SymbolEvent.

    CPU-only, single-event path. Use batch_generate_ncv_73 for GPU.
    """
    vector = []

    # Preceding context (pad with zeros if < 6)
    ctx_before = event.context_symbols[-CONTEXT_POSITIONS:]  # last 6
    padded_before = [0] * (CONTEXT_POSITIONS - len(ctx_before)) + list(ctx_before)
    for i, sid in enumerate(padded_before):
        vector.extend(_symbol_features(
            sid, event.symbol_id, forge, max_symbol_id, distance=CONTEXT_POSITIONS - i
        ))

    # Anchor feature
    anchor_res = forge.resonance.get(event.symbol_id, 0.0)
    vector.append(anchor_res)

    # Following context (pad with zeros if < 6)
    ctx_after = event.context_symbols[:CONTEXT_POSITIONS]  # first 6
    padded_after = list(ctx_after) + [0] * (CONTEXT_POSITIONS - len(ctx_after))
    for i, sid in enumerate(padded_after):
        vector.extend(_symbol_features(
            sid, event.symbol_id, forge, max_symbol_id, distance=i + 1
        ))

    return vector[:NCV_DIM]


def _symbol_features(
    symbol_id: int,
    anchor_id: int,
    forge: ForgeMemory,
    max_symbol_id: float,
    distance: int,
) -> list[float]:
    """Compute 6 features for a single context symbol."""
    if symbol_id == 0:
        return [0.0] * FEATURES_PER_POSITION

    resonance = forge.resonance.get(symbol_id, 0.0)
    co_count = forge.co_occurrence.get(anchor_id, {}).get(symbol_id, 0)
    density = sum(forge.co_occurrence.get(symbol_id, {}).values()) if symbol_id in forge.co_occurrence else 0
    uniqueness = min(1.0 / resonance, 1.0) if resonance > 0 else 1.0

    return [
        symbol_id / max_symbol_id,          # normalized id
        resonance,                           # resonance score
        float(co_count),                     # co-occurrence with anchor
        distance / CONTEXT_POSITIONS,        # normalized distance
        float(density),                      # total co-occurrence density
        uniqueness,                          # rarity signal
    ]


def batch_generate_ncv_73(
    events: list[SymbolEvent],
    forge: ForgeMemory,
    device: DeviceInfo,
    max_symbol_id: float = 1e10,
) -> torch.Tensor:
    """
    Batch-generate NCV-73 vectors on GPU.

    Args:
        events: List of SymbolEvents to vectorize.
        forge: ForgeMemory for resonance/co-occurrence lookups.
        device: DeviceInfo for tensor placement.
        max_symbol_id: Normalization factor for symbol IDs.

    Returns:
        Float32 tensor of shape (len(events), 73) on device.
    """
    batch = []
    for event in events:
        vec = generate_ncv_73(event, forge, max_symbol_id)
        batch.append(vec)

    tensor = torch.tensor(batch, dtype=torch.float32)
    if device.is_cuda:
        tensor = tensor.to(device.torch_device, non_blocking=True)
    return tensor
