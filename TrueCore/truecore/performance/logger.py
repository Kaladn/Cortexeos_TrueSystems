"""TrueCore performance cost receipts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from truecore.time import is_canonical_utc_timestamp, utc_now


class PerformanceLogger:
    """Write cost posture receipts for workers, tools, algorithms, and models."""

    def __init__(self, receipt_root: str | Path):
        self.receipt_root = Path(receipt_root)

    def write_receipt(self, **kwargs) -> dict[str, Any]:
        receipt = build_performance_receipt(**kwargs)
        safe_time = receipt["created_at_utc"].replace(":", "").replace(".", "")
        path = self.receipt_root / f"{safe_time}-{receipt['receipt_id']}.performance.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        receipt["receipt_path"] = str(path)
        return receipt


def build_performance_receipt(
    *,
    algorithm_id: str,
    run_id: str,
    input_size: int,
    duration_ms: float,
    cpu_ms: float = 0.0,
    memory_peak_mb: float = 0.0,
    disk_read_mb: float = 0.0,
    disk_write_mb: float = 0.0,
    forge_write_latency_ms: float = 0.0,
    fusion_block_build_ms: float = 0.0,
    queue_wait_ms: float = 0.0,
    model_inference_latency_ms: float = 0.0,
    gpu_vram_peak_mb: float | None = None,
    energy_estimate_wh: float | None = None,
    records_processed: int = 0,
    blocks_processed: int = 0,
    error_count: int = 0,
) -> dict[str, Any]:
    receipt = {
        "schema_version": 1,
        "kind": "truecore_performance_receipt",
        "receipt_id": "",
        "created_at_utc": utc_now(),
        "algorithm_id": algorithm_id,
        "run_id": run_id,
        "input_size": int(input_size),
        "duration_ms": _round(duration_ms),
        "cpu_ms": _round(cpu_ms),
        "memory_peak_mb": _round(memory_peak_mb),
        "disk_read_mb": _round(disk_read_mb),
        "disk_write_mb": _round(disk_write_mb),
        "forge_write_latency_ms": _round(forge_write_latency_ms),
        "fusion_block_build_ms": _round(fusion_block_build_ms),
        "queue_wait_ms": _round(queue_wait_ms),
        "model_inference_latency_ms": _round(model_inference_latency_ms),
        "gpu_vram_peak_mb": _optional_round(gpu_vram_peak_mb),
        "energy_estimate_wh": _optional_round(energy_estimate_wh),
        "records_processed": int(records_processed),
        "blocks_processed": int(blocks_processed),
        "error_count": int(error_count),
        "events_per_second": _rate(records_processed, duration_ms),
        "blocks_per_second": _rate(blocks_processed, duration_ms),
        "bottleneck_hint": _bottleneck_hint(
            duration_ms=duration_ms,
            cpu_ms=cpu_ms,
            memory_peak_mb=memory_peak_mb,
            disk_read_mb=disk_read_mb,
            disk_write_mb=disk_write_mb,
            forge_write_latency_ms=forge_write_latency_ms,
            fusion_block_build_ms=fusion_block_build_ms,
            queue_wait_ms=queue_wait_ms,
            model_inference_latency_ms=model_inference_latency_ms,
            gpu_vram_peak_mb=gpu_vram_peak_mb,
        ),
        "truth_authority": False,
        "behavior_change_authority": False,
        "policy_approval_authority": False,
    }
    receipt["receipt_id"] = _receipt_id(receipt)
    return validate_performance_receipt(receipt)


def validate_performance_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "kind",
        "receipt_id",
        "created_at_utc",
        "algorithm_id",
        "run_id",
        "input_size",
        "duration_ms",
        "cpu_ms",
        "memory_peak_mb",
        "disk_read_mb",
        "disk_write_mb",
        "forge_write_latency_ms",
        "fusion_block_build_ms",
        "queue_wait_ms",
        "model_inference_latency_ms",
        "gpu_vram_peak_mb",
        "energy_estimate_wh",
        "records_processed",
        "blocks_processed",
        "error_count",
        "events_per_second",
        "blocks_per_second",
        "bottleneck_hint",
        "truth_authority",
        "behavior_change_authority",
        "policy_approval_authority",
    }
    missing = sorted(required.difference(receipt))
    if missing:
        raise ValueError(f"performance receipt missing fields: {missing}")
    _require(receipt, "schema_version", 1)
    _require(receipt, "kind", "truecore_performance_receipt")
    _require(receipt, "truth_authority", False)
    _require(receipt, "behavior_change_authority", False)
    _require(receipt, "policy_approval_authority", False)
    if not is_canonical_utc_timestamp(str(receipt["created_at_utc"])):
        raise ValueError("created_at_utc must be canonical UTC")
    if not str(receipt["algorithm_id"]):
        raise ValueError("algorithm_id is required")
    if not str(receipt["run_id"]):
        raise ValueError("run_id is required")
    for field in (
        "input_size",
        "duration_ms",
        "cpu_ms",
        "memory_peak_mb",
        "disk_read_mb",
        "disk_write_mb",
        "forge_write_latency_ms",
        "fusion_block_build_ms",
        "queue_wait_ms",
        "model_inference_latency_ms",
        "records_processed",
        "blocks_processed",
        "error_count",
        "events_per_second",
        "blocks_per_second",
    ):
        if float(receipt[field]) < 0:
            raise ValueError(f"{field} may not be negative")
    for field in ("gpu_vram_peak_mb", "energy_estimate_wh"):
        value = receipt[field]
        if value is not None and float(value) < 0:
            raise ValueError(f"{field} may not be negative")
    return receipt


def _bottleneck_hint(
    *,
    duration_ms: float,
    cpu_ms: float,
    memory_peak_mb: float,
    disk_read_mb: float,
    disk_write_mb: float,
    forge_write_latency_ms: float,
    fusion_block_build_ms: float,
    queue_wait_ms: float,
    model_inference_latency_ms: float,
    gpu_vram_peak_mb: float | None,
) -> str:
    if duration_ms <= 0:
        return "none"
    candidates = {
        "cpu": cpu_ms / duration_ms,
        "forge_write": forge_write_latency_ms / duration_ms,
        "fusion": fusion_block_build_ms / duration_ms,
        "queue": queue_wait_ms / duration_ms,
        "model": model_inference_latency_ms / duration_ms,
        "disk": (disk_read_mb + disk_write_mb) / max(duration_ms / 1000.0, 1.0) / 1000.0,
        "memory": memory_peak_mb / 32768.0,
        "gpu_vram": (gpu_vram_peak_mb or 0.0) / 32768.0,
    }
    best, score = max(candidates.items(), key=lambda item: item[1])
    return best if score > 0 else "none"


def _rate(count: int, duration_ms: float) -> float:
    if duration_ms <= 0:
        return 0.0
    return _round(float(count) / (duration_ms / 1000.0))


def _round(value: Any) -> float:
    return round(float(value or 0.0), 3)


def _optional_round(value: Any) -> float | None:
    if value is None:
        return None
    return _round(value)


def _receipt_id(receipt: dict[str, Any]) -> str:
    row = dict(receipt)
    row["receipt_id"] = ""
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _require(row: dict[str, Any], field: str, expected: Any) -> None:
    if row.get(field) != expected:
        raise ValueError(f"{field} must be {expected!r}")
