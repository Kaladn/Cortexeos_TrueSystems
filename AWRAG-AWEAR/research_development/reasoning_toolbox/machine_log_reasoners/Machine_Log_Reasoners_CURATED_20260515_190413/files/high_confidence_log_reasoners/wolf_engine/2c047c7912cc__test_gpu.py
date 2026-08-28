"""
Phase 2 GPU test suite — device detection, window engine, ForgeMemoryGPU, NCV-73 batch.

Tests run on whatever hardware is available. CUDA tests are skipped if no GPU present.
CPU fallback paths are always tested.
"""

from __future__ import annotations

import uuid
from collections import Counter

import pytest
import torch

from wolf_engine.contracts import SymbolEvent
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.gpu.device import DeviceInfo, select_device, to_tensor
from wolf_engine.gpu.forge_memory_gpu import ForgeMemoryGPU
from wolf_engine.gpu.ncv_batch import (
    NCV_DIM,
    batch_generate_ncv_73,
    generate_ncv_73,
)
from wolf_engine.gpu.window_engine import compute_window_counts

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HAS_CUDA = torch.cuda.is_available()

skip_no_cuda = pytest.mark.skipif(not HAS_CUDA, reason="No CUDA device available")


def _make_event(
    symbol_id: int,
    context_symbols: list[int] | None = None,
    session_id: str = "",
    pulse_id: int = 1,
) -> SymbolEvent:
    return SymbolEvent(
        event_id=str(uuid.uuid4()),
        session_id=session_id or str(uuid.uuid4()),
        pulse_id=pulse_id,
        symbol_id=symbol_id,
        context_symbols=context_symbols or [],
        category="core",
        priority=1,
    )


# ===========================================================================
# P2-DEV: Device Detection
# ===========================================================================


class TestDeviceDetection:
    def test_select_cpu_forced(self):
        dev = select_device("cpu")
        assert dev.type == "cpu"
        assert not dev.is_cuda
        assert dev.torch_device == torch.device("cpu")

    def test_select_auto(self):
        dev = select_device("auto")
        if HAS_CUDA:
            assert dev.type == "cuda"
            assert dev.is_cuda
            assert "cuda" in str(dev.torch_device)
        else:
            assert dev.type == "cpu"

    @skip_no_cuda
    def test_select_cuda_explicit(self):
        dev = select_device("cuda")
        assert dev.is_cuda
        assert dev.name  # Should have device name like "NVIDIA GeForce RTX 4080"

    def test_select_cuda_no_gpu_raises(self):
        if HAS_CUDA:
            pytest.skip("CUDA is available, can't test missing-GPU error")
        with pytest.raises(RuntimeError, match="CUDA requested but not available"):
            select_device("cuda")

    def test_select_invalid_mode(self):
        with pytest.raises(ValueError, match="Unknown device mode"):
            select_device("tpu")

    def test_to_tensor_cpu(self):
        dev = select_device("cpu")
        t = to_tensor([1, 2, 3], dev)
        assert t.dtype == torch.long
        assert t.tolist() == [1, 2, 3]
        assert t.device == torch.device("cpu")

    @skip_no_cuda
    def test_to_tensor_cuda(self):
        dev = select_device("cuda")
        t = to_tensor([10, 20, 30], dev)
        assert t.dtype == torch.long
        assert t.tolist() == [10, 20, 30]
        assert t.device.type == "cuda"

    def test_device_info_str(self):
        cpu = DeviceInfo(type="cpu", name="cpu")
        assert str(cpu) == "cpu"
        gpu = DeviceInfo(type="cuda", name="RTX 4080", index=0)
        assert "RTX 4080" in str(gpu)
        assert "cuda:0" in str(gpu)


# ===========================================================================
# P2-WIN: Window Engine
# ===========================================================================


class TestWindowEngine:
    def test_empty_input(self):
        dev = select_device("cpu")
        result = compute_window_counts([], 6, dev)
        assert result == {}

    def test_single_symbol(self):
        dev = select_device("cpu")
        result = compute_window_counts([42], 6, dev)
        assert result == {}

    def test_cpu_basic_window(self):
        dev = select_device("cpu")
        ids = [1, 2, 3, 1, 2]
        result = compute_window_counts(ids, 2, dev)
        # Symbol 1 should co-occur with 2 and 3
        assert 1 in result
        assert 2 in result[1]

    def test_cpu_symmetry(self):
        """Forward (1→2) and backward (2→1) should both be counted."""
        dev = select_device("cpu")
        ids = [10, 20]
        result = compute_window_counts(ids, 1, dev)
        assert result[10][20] >= 1
        assert result[20][10] >= 1

    @skip_no_cuda
    def test_gpu_matches_cpu(self):
        """GPU and CPU paths must produce identical results."""
        ids = list(range(1, 101))  # 100 symbols
        cpu_dev = select_device("cpu")
        gpu_dev = select_device("cuda")

        cpu_result = compute_window_counts(ids, 6, cpu_dev)
        gpu_result = compute_window_counts(ids, 6, gpu_dev)

        # Same keys
        assert set(cpu_result.keys()) == set(gpu_result.keys())

        # Same counts
        for sid in cpu_result:
            assert dict(cpu_result[sid]) == dict(gpu_result[sid]), (
                f"Mismatch for symbol {sid}"
            )

    @skip_no_cuda
    def test_gpu_large_stream(self):
        """Stress: 10K symbols through GPU path."""
        import random
        random.seed(42)
        ids = [random.randint(1, 500) for _ in range(10_000)]
        dev = select_device("cuda")
        result = compute_window_counts(ids, 6, dev)
        assert len(result) > 0
        # Every symbol in the stream should appear in results
        assert len(result) == len(set(ids))


# ===========================================================================
# P2-FGP: ForgeMemoryGPU
# ===========================================================================


class TestForgeMemoryGPU:
    def test_cpu_fallback_mode(self):
        """ForgeMemoryGPU works on CPU when no CUDA available."""
        dev = DeviceInfo(type="cpu", name="cpu")
        fgpu = ForgeMemoryGPU(window_size=1000, device=dev)
        assert not fgpu._gpu_ready

        event = _make_event(100, [99, 101])
        fgpu.ingest(event)
        assert fgpu.resonance[100] > 0

    def test_cpu_top_resonance(self):
        dev = DeviceInfo(type="cpu", name="cpu")
        fgpu = ForgeMemoryGPU(window_size=1000, device=dev)
        for i in range(1, 6):
            for _ in range(i * 10):
                fgpu.ingest(_make_event(i))
        top = fgpu.top_resonance(3)
        assert len(top) == 3
        # Highest resonance should be symbol 5 (50 ingests)
        assert top[0][0] == 5

    def test_batch_ingest_cpu(self):
        dev = DeviceInfo(type="cpu", name="cpu")
        fgpu = ForgeMemoryGPU(window_size=5000, device=dev)
        events = [_make_event(i % 100 + 1) for i in range(500)]
        fgpu.batch_ingest(events)
        assert len(fgpu.resonance) > 0

    @skip_no_cuda
    def test_cuda_ingest(self):
        dev = select_device("cuda")
        fgpu = ForgeMemoryGPU(window_size=5000, device=dev)
        assert fgpu._gpu_ready

        for i in range(100):
            fgpu.ingest(_make_event(i + 1, [i, i + 2]))

        # CPU resonance
        assert len(fgpu.resonance) == 100
        # GPU resonance tensor should have nonzero entries
        gpu_nonzero = int((fgpu._resonance_tensor > 0).sum().item())
        assert gpu_nonzero == 100

    @skip_no_cuda
    def test_cuda_batch_ingest(self):
        dev = select_device("cuda")
        fgpu = ForgeMemoryGPU(window_size=10000, device=dev)
        events = [_make_event(i % 200 + 1) for i in range(2000)]
        fgpu.batch_ingest(events)

        cpu_count = len(fgpu.resonance)
        gpu_nonzero = int((fgpu._resonance_tensor > 0).sum().item())
        assert cpu_count == 200
        assert gpu_nonzero == 200

    @skip_no_cuda
    def test_cuda_top_resonance(self):
        dev = select_device("cuda")
        fgpu = ForgeMemoryGPU(window_size=5000, device=dev)
        # Symbol 42 gets the most ingests
        for _ in range(50):
            fgpu.ingest(_make_event(42))
        for _ in range(10):
            fgpu.ingest(_make_event(7))
        for _ in range(5):
            fgpu.ingest(_make_event(99))

        top = fgpu.top_resonance(3)
        assert top[0][0] == 42
        assert top[0][1] == 50.0

    @skip_no_cuda
    def test_cuda_co_occurrence_matrix(self):
        dev = select_device("cuda")
        fgpu = ForgeMemoryGPU(window_size=5000, device=dev)
        for _ in range(10):
            fgpu.ingest(_make_event(5, [3, 7]))
        mat = fgpu.gpu_co_occurrence_matrix([5, 3, 7], max_dim=100)
        assert mat is not None
        assert mat.is_sparse

    def test_cpu_co_occurrence_matrix_returns_none(self):
        dev = DeviceInfo(type="cpu", name="cpu")
        fgpu = ForgeMemoryGPU(window_size=1000, device=dev)
        mat = fgpu.gpu_co_occurrence_matrix([1, 2], max_dim=100)
        assert mat is None

    @skip_no_cuda
    def test_cuda_reload(self):
        dev = select_device("cuda")
        fgpu = ForgeMemoryGPU(window_size=5000, device=dev)
        events = [_make_event(i + 1) for i in range(50)]
        fgpu.reload_from_events(events)
        gpu_nonzero = int((fgpu._resonance_tensor > 0).sum().item())
        assert gpu_nonzero == 50

    def test_stats(self):
        dev = DeviceInfo(type="cpu", name="cpu")
        fgpu = ForgeMemoryGPU(window_size=1000, device=dev)
        fgpu.ingest(_make_event(1))
        stats = fgpu.stats()
        assert stats.total_symbols >= 1


# ===========================================================================
# P2-NCV: NCV-73 Batch Generation
# ===========================================================================


class TestNCV73:
    def _make_forge_with_data(self) -> ForgeMemory:
        forge = ForgeMemory(window_size=5000)
        for i in range(1, 20):
            forge.ingest(_make_event(i, [i - 1, i + 1] if i > 1 else [i + 1]))
        return forge

    def test_single_vector_length(self):
        forge = self._make_forge_with_data()
        event = _make_event(10, [4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16])
        vec = generate_ncv_73(event, forge)
        assert len(vec) == NCV_DIM

    def test_single_vector_values_finite(self):
        forge = self._make_forge_with_data()
        event = _make_event(10, [4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16])
        vec = generate_ncv_73(event, forge)
        for v in vec:
            assert isinstance(v, float)
            assert not (v != v)  # NaN check

    def test_padded_context(self):
        """Short context should be zero-padded."""
        forge = self._make_forge_with_data()
        event = _make_event(10, [9])  # Only 1 context symbol
        vec = generate_ncv_73(event, forge)
        assert len(vec) == NCV_DIM
        # First 5 positions should be zero-padded (5 × 6 = 30 zeros)
        assert vec[0:30] == [0.0] * 30

    def test_empty_context(self):
        forge = self._make_forge_with_data()
        event = _make_event(10, [])
        vec = generate_ncv_73(event, forge)
        assert len(vec) == NCV_DIM
        # All context positions padded with zeros, only anchor is non-zero
        assert vec[36] >= 0  # anchor resonance

    def test_batch_cpu(self):
        forge = self._make_forge_with_data()
        dev = select_device("cpu")
        events = [
            _make_event(i, [i - 1, i + 1]) for i in range(5, 15)
        ]
        tensor = batch_generate_ncv_73(events, forge, dev)
        assert tensor.shape == (10, NCV_DIM)
        assert tensor.dtype == torch.float32
        assert tensor.device == torch.device("cpu")

    @skip_no_cuda
    def test_batch_cuda(self):
        forge = self._make_forge_with_data()
        dev = select_device("cuda")
        events = [
            _make_event(i, [i - 1, i + 1]) for i in range(5, 15)
        ]
        tensor = batch_generate_ncv_73(events, forge, dev)
        assert tensor.shape == (10, NCV_DIM)
        assert tensor.dtype == torch.float32
        assert tensor.device.type == "cuda"

    def test_batch_single_event(self):
        forge = self._make_forge_with_data()
        dev = select_device("cpu")
        events = [_make_event(10, [9, 11])]
        tensor = batch_generate_ncv_73(events, forge, dev)
        assert tensor.shape == (1, NCV_DIM)

    @skip_no_cuda
    def test_batch_matches_single(self):
        """Batch GPU output must match single-event CPU output."""
        forge = self._make_forge_with_data()
        dev = select_device("cuda")
        events = [
            _make_event(i, [i - 1, i + 1]) for i in range(5, 10)
        ]

        # Single-event CPU path
        expected = [generate_ncv_73(e, forge) for e in events]
        expected_tensor = torch.tensor(expected, dtype=torch.float32)

        # Batch GPU path
        batch_tensor = batch_generate_ncv_73(events, forge, dev).cpu()

        assert torch.allclose(expected_tensor, batch_tensor, atol=1e-6)
