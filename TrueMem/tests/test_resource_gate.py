from __future__ import annotations

from pathlib import Path

import pytest

from truemem.engine import pipeline
from truemem.engine.hardware import enforce_minimum_runtime_requirements


def _resources_without_gpu() -> dict[str, object]:
    return {
        "logical_cpu_count": 8,
        "total_ram_bytes": 16 * 1024 * 1024 * 1024,
        "available_ram_bytes": 12 * 1024 * 1024 * 1024,
        "gpu_devices": [],
        "max_gpu_memory_bytes": 0,
    }


def test_minimum_runtime_gate_allows_cpu_ram_only_by_default() -> None:
    enforce_minimum_runtime_requirements(_resources_without_gpu())


def test_minimum_runtime_gate_can_still_require_gpu() -> None:
    with pytest.raises(RuntimeError, match="max_gpu_memory_bytes=0"):
        enforce_minimum_runtime_requirements(_resources_without_gpu(), require_gpu=True)


def test_intake_resource_plan_records_gpu_gate_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.md"
    source.write_text("alpha beta gamma\n", encoding="utf-8")
    monkeypatch.setattr(pipeline, "_detect_system_resources", _resources_without_gpu)

    plan = pipeline._build_intake_resource_plan(
        files=[source],
        requested_workers="4",
        reserve_ram_fraction=0.15,
        ram_budget_gb=8.0,
    )

    assert plan["effective_workers"] == 4
    assert plan["gpu_requirement_enforced"] is False
    assert plan["gpu_usage"] == "unused_by_intake"
