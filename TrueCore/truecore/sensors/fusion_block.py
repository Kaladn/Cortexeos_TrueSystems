"""Compatibility wrapper for TrueCore binary temporal fusion.

New code should import ``truecore.sensors.fusion`` directly.
"""

from __future__ import annotations

from typing import Any

from truecore.sensors.fusion import (
    SOURCE_ORDER,
    FusionError,
    build_temporal_fusion_block,
    decode_temporal_fusion_block,
    encode_temporal_fusion_block,
    validate_temporal_fusion_block,
)


SENSOR_CLASS_ORDER = SOURCE_ORDER
SensorFusionBlockError = FusionError


def build_fusion_block(
    *,
    block_id: str,
    source_id: str,
    bucket_start_utc: str,
    bucket_duration_ms: int,
    events: list[dict[str, Any]],
    previous_block_hash: str = "GENESIS",
) -> dict[str, Any]:
    block = build_temporal_fusion_block(
        block_id=block_id,
        source_id=source_id,
        window_start_utc=bucket_start_utc,
        window_duration_ms=bucket_duration_ms,
        events=events,
        previous_block_hash=previous_block_hash,
    )
    block["bucket_start_utc"] = block["window_start_utc"]
    block["bucket_duration_ms"] = block["window_duration_ms"]
    block["sensor_class_mask"] = block["source_mask"]
    block["class_counts"] = block["source_counts"]
    return block


def validate_fusion_block(block: dict[str, Any]) -> dict[str, Any]:
    if "window_start_utc" not in block and "bucket_start_utc" in block:
        block = dict(block)
        block["window_start_utc"] = block["bucket_start_utc"]
        block["window_duration_ms"] = block["bucket_duration_ms"]
        block["source_mask"] = block["sensor_class_mask"]
        block["source_counts"] = block["class_counts"]
        block.setdefault("window_start_ns", 0)
        block.setdefault("anomaly_flags", 0)
        block.setdefault("state_hashes", {name: "0" * 64 for name in SOURCE_ORDER})
        block.setdefault("relation_hints", [])
        block.setdefault("recognition_authority", False)
    return validate_temporal_fusion_block(block)


def encode_fusion_block(block: dict[str, Any]) -> bytes:
    return encode_temporal_fusion_block(validate_fusion_block(block))


def decode_fusion_block(raw: bytes) -> dict[str, Any]:
    block = decode_temporal_fusion_block(raw)
    block["bucket_start_utc"] = block["window_start_utc"]
    block["bucket_duration_ms"] = block["window_duration_ms"]
    block["sensor_class_mask"] = block["source_mask"]
    block["class_counts"] = block["source_counts"]
    return block
