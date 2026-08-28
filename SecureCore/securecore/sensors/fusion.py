"""Binary temporal fusion for SecureCore logger lanes.

Loggers witness. Forge orders. Fusion compresses. Agents decide later.

Fusion is a derived, replayable temporal reducer over Forge-ordered sensor
events. It is not a TrueVision component and it is not an inference engine.
"""

from __future__ import annotations

import hashlib
import json
import struct
from datetime import datetime, timezone
from typing import Any

from securecore.time import is_canonical_utc_timestamp


MAGIC = b"SCFB"
VERSION = 1
KIND = "securecore_temporal_fusion_block"
SOURCE_ORDER = (
    "process",
    "network",
    "eventlog",
    "hid",
    "window",
    "device",
    "security",
    "vision",
    "truevision_temporal_pulse",
    "audio",
)
SOURCE_BITS = {name: 1 << index for index, name in enumerate(SOURCE_ORDER)}
ANOMALY_BITS = {
    "has_alert": 1 << 0,
    "has_security": 1 << 1,
    "has_vision_change": 1 << 2,
    "has_hid_presence": 1 << 3,
    "has_network_change": 1 << 4,
    "has_process_change": 1 << 5,
    "has_explicit_risk": 1 << 6,
}
HEADER = struct.Struct("<4sHHqIIQQq32s32s")
COUNTS = struct.Struct("<" + ("H" * len(SOURCE_ORDER)))
STATE_HASH_SIZE = 32


class FusionError(ValueError):
    """Raised when a temporal fusion block violates SecureCore law."""


def build_temporal_fusion_block(
    *,
    block_id: str,
    source_id: str,
    window_start_utc: str,
    window_duration_ms: int,
    events: list[dict[str, Any]],
    previous_block_hash: str = "GENESIS",
    relation_hints: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not is_canonical_utc_timestamp(window_start_utc):
        raise FusionError("window_start_utc must use canonical UTC format")
    if window_duration_ms <= 0:
        raise FusionError("window_duration_ms must be positive")

    source_counts = {name: 0 for name in SOURCE_ORDER}
    source_mask = 0
    anomaly_flags = 0
    event_refs: list[dict[str, Any]] = []
    sequences: list[int] = []

    for event in events:
        sensor_class = _source_class(event)
        source_counts[sensor_class] += 1
        source_mask |= SOURCE_BITS[sensor_class]
        anomaly_flags |= _event_anomaly_flags(event, sensor_class)
        sequence = int(event.get("sequence", 0))
        sequences.append(sequence)
        event_refs.append(_event_ref(event, sensor_class, sequence))

    first_sequence = min(sequences) if sequences else -1
    last_sequence = max(sequences) if sequences else -1
    state_hashes = _state_hashes(event_refs, source_counts, relation_hints or [])
    digest_input = {
        "block_id": block_id,
        "source_id": source_id,
        "window_start_utc": window_start_utc,
        "window_duration_ms": int(window_duration_ms),
        "source_mask": source_mask,
        "source_counts": source_counts,
        "anomaly_flags": anomaly_flags,
        "state_hashes": state_hashes,
        "relation_hints": relation_hints or [],
        "event_refs": event_refs,
        "previous_block_hash": previous_block_hash,
    }
    block_hash = hashlib.sha256(
        json.dumps(digest_input, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    block = {
        "schema_version": VERSION,
        "kind": KIND,
        "block_id": block_id,
        "source_id": source_id,
        "window_start_utc": window_start_utc,
        "window_start_ns": _timestamp_to_epoch_ns(window_start_utc),
        "window_duration_ms": int(window_duration_ms),
        "source_mask": source_mask,
        "source_counts": source_counts,
        "event_count": len(event_refs),
        "anomaly_flags": anomaly_flags,
        "state_hashes": state_hashes,
        "relation_hints": list(relation_hints or []),
        "first_sequence": first_sequence,
        "last_sequence": last_sequence,
        "previous_block_hash": previous_block_hash,
        "block_hash": block_hash,
        "event_refs": event_refs,
        "payload_class": "binary_metadata",
        "raw_content_stored": False,
        "inference_allowed": False,
        "recognition_authority": False,
    }
    validate_temporal_fusion_block(block)
    return block


def validate_temporal_fusion_block(block: dict[str, Any]) -> dict[str, Any]:
    if block.get("schema_version") != VERSION:
        raise FusionError("schema_version must be 1")
    if block.get("kind") != KIND:
        raise FusionError(f"kind must be {KIND}")
    for field in ("block_id", "source_id", "window_start_utc", "block_hash", "previous_block_hash"):
        if not isinstance(block.get(field), str) or not block[field].strip():
            raise FusionError(f"{field} must be a non-empty string")
    if not is_canonical_utc_timestamp(block["window_start_utc"]):
        raise FusionError("window_start_utc must use canonical UTC format")
    for field in ("window_start_ns", "window_duration_ms", "source_mask", "event_count", "anomaly_flags"):
        if not isinstance(block.get(field), int) or block[field] < 0:
            raise FusionError(f"{field} must be a non-negative integer")
    if block["window_duration_ms"] <= 0:
        raise FusionError("window_duration_ms must be positive")
    _validate_source_counts(block.get("source_counts"))
    _validate_state_hashes(block.get("state_hashes"))
    if not isinstance(block.get("relation_hints"), list):
        raise FusionError("relation_hints must be a list")
    if not isinstance(block.get("event_refs"), list) or len(block["event_refs"]) != block["event_count"]:
        raise FusionError("event_refs must match event_count")
    if any("payload" in ref for ref in block["event_refs"] if isinstance(ref, dict)):
        raise FusionError("fusion event refs may not contain raw payloads")
    for field, expected in (
        ("payload_class", "binary_metadata"),
        ("raw_content_stored", False),
        ("inference_allowed", False),
        ("recognition_authority", False),
    ):
        if block.get(field) != expected:
            raise FusionError(f"{field} must be {expected!r}")
    _reject_raw_content_terms(block)
    return dict(block)


def encode_temporal_fusion_block(block: dict[str, Any]) -> bytes:
    block = validate_temporal_fusion_block(block)
    counts = [int(block["source_counts"][name]) for name in SOURCE_ORDER]
    state_blob = b"".join(_hash_to_32_bytes(block["state_hashes"][name]) for name in SOURCE_ORDER)
    refs_blob = json.dumps(
        {
            "block_id": block["block_id"],
            "source_id": block["source_id"],
            "window_start_utc": block["window_start_utc"],
            "event_refs": block["event_refs"],
            "relation_hints": block["relation_hints"],
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    header = HEADER.pack(
        MAGIC,
        VERSION,
        HEADER.size + COUNTS.size + len(state_blob),
        int(block["window_start_ns"]),
        int(block["window_duration_ms"]),
        int(block["event_count"]),
        int(block["source_mask"]),
        int(block["anomaly_flags"]),
        int(block["first_sequence"]),
        _hash_to_32_bytes(block["previous_block_hash"]),
        _hash_to_32_bytes(block["block_hash"]),
    )
    return header + COUNTS.pack(*counts) + state_blob + refs_blob


def decode_temporal_fusion_block(raw: bytes) -> dict[str, Any]:
    min_size = HEADER.size + COUNTS.size + (STATE_HASH_SIZE * len(SOURCE_ORDER))
    if len(raw) < min_size:
        raise FusionError("fusion block frame too small")
    (
        magic,
        version,
        header_size,
        window_start_ns,
        window_duration_ms,
        event_count,
        source_mask,
        anomaly_flags,
        first_sequence,
        previous_hash_bytes,
        block_hash_bytes,
    ) = HEADER.unpack(raw[: HEADER.size])
    if magic != MAGIC:
        raise FusionError("invalid fusion block magic")
    if version != VERSION:
        raise FusionError(f"unsupported fusion block version: {version}")
    expected_header_size = HEADER.size + COUNTS.size + (STATE_HASH_SIZE * len(SOURCE_ORDER))
    if header_size != expected_header_size:
        raise FusionError("unsupported fusion block header size")

    counts_start = HEADER.size
    state_start = counts_start + COUNTS.size
    meta_start = header_size
    counts_raw = COUNTS.unpack(raw[counts_start:state_start])
    state_blob = raw[state_start:meta_start]
    state_hashes = {
        name: state_blob[index * STATE_HASH_SIZE : (index + 1) * STATE_HASH_SIZE].hex()
        for index, name in enumerate(SOURCE_ORDER)
    }
    meta = json.loads(raw[meta_start:].decode("utf-8")) if len(raw) > meta_start else {}
    refs = list(meta.get("event_refs", []))
    sequences = [int(ref.get("sequence", 0)) for ref in refs]
    block = {
        "schema_version": VERSION,
        "kind": KIND,
        "block_id": str(meta.get("block_id", "")),
        "source_id": str(meta.get("source_id", "")),
        "window_start_utc": str(meta.get("window_start_utc") or _epoch_ns_to_timestamp(int(window_start_ns))),
        "window_start_ns": int(window_start_ns),
        "window_duration_ms": int(window_duration_ms),
        "source_mask": int(source_mask),
        "source_counts": dict(zip(SOURCE_ORDER, [int(value) for value in counts_raw])),
        "event_count": int(event_count),
        "anomaly_flags": int(anomaly_flags),
        "state_hashes": state_hashes,
        "relation_hints": list(meta.get("relation_hints", [])),
        "first_sequence": int(first_sequence),
        "last_sequence": max(sequences) if sequences else -1,
        "previous_block_hash": previous_hash_bytes.hex() if previous_hash_bytes.strip(b"\x00") else "GENESIS",
        "block_hash": block_hash_bytes.hex(),
        "event_refs": refs,
        "payload_class": "binary_metadata",
        "raw_content_stored": False,
        "inference_allowed": False,
        "recognition_authority": False,
    }
    return validate_temporal_fusion_block(block)


def _source_class(event: dict[str, Any]) -> str:
    sensor_class = str(event.get("sensor_class", ""))
    if sensor_class in SOURCE_BITS:
        return sensor_class
    sensor_id = str(event.get("sensor_id", "")).casefold()
    if "audio" in sensor_id:
        return "audio"
    raise FusionError(f"unknown source class: {sensor_class}")


def _event_ref(event: dict[str, Any], source_class: str, sequence: int) -> dict[str, Any]:
    return {
        "event_id": str(event.get("event_id", "")),
        "sensor_id": str(event.get("sensor_id", "")),
        "source_class": source_class,
        "event_type": str(event.get("event_type", "")),
        "sequence": sequence,
        "observed_at_utc": str(event.get("observed_at_utc", "")),
        "payload_hash": str(event.get("payload_hash", "")),
    }


def _event_anomaly_flags(event: dict[str, Any], source_class: str) -> int:
    event_type = str(event.get("event_type", ""))
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    flags = 0
    if event_type == "alert":
        flags |= ANOMALY_BITS["has_alert"]
    if source_class == "security" and event_type == "alert":
        flags |= ANOMALY_BITS["has_security"]
    anomaly_level = str(payload.get("anomaly_level", payload.get("level", ""))).casefold()
    if source_class == "vision" and anomaly_level in {"medium", "high", "critical"}:
        flags |= ANOMALY_BITS["has_vision_change"]
    risk_score = payload.get("risk_score", payload.get("risk_seed", 0))
    if isinstance(risk_score, (int, float)) and float(risk_score) > 0:
        flags |= ANOMALY_BITS["has_explicit_risk"]
    return flags


def _state_hashes(
    event_refs: list[dict[str, Any]],
    source_counts: dict[str, int],
    relation_hints: list[dict[str, Any]],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for source_class in SOURCE_ORDER:
        source_refs = [ref for ref in event_refs if ref["source_class"] == source_class]
        blob = {
            "source_class": source_class,
            "count": source_counts[source_class],
            "refs": source_refs,
            "relation_hints": [
                hint for hint in relation_hints if hint.get("source_class") in {source_class, None}
            ],
        }
        result[source_class] = hashlib.sha256(
            json.dumps(blob, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()
    return result


def _validate_source_counts(value: Any) -> None:
    if not isinstance(value, dict):
        raise FusionError("source_counts must be an object")
    for name in SOURCE_ORDER:
        if not isinstance(value.get(name), int) or value[name] < 0:
            raise FusionError(f"source_counts.{name} must be a non-negative integer")


def _validate_state_hashes(value: Any) -> None:
    if not isinstance(value, dict):
        raise FusionError("state_hashes must be an object")
    for name in SOURCE_ORDER:
        item = value.get(name)
        if not isinstance(item, str) or len(item) != 64:
            raise FusionError(f"state_hashes.{name} must be a 32-byte hex hash")


def _reject_raw_content_terms(value: Any) -> None:
    forbidden = {"raw_frame", "frame_bytes", "screenshot", "command_body", "message_body", "raw_audio"}
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in forbidden:
                raise FusionError("fusion block may not contain raw content")
            _reject_raw_content_terms(child)
    elif isinstance(value, list):
        for child in value:
            _reject_raw_content_terms(child)


def _timestamp_to_epoch_ns(value: str) -> int:
    dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000_000)


def _epoch_ns_to_timestamp(value: int) -> str:
    dt = datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _hash_to_32_bytes(value: str) -> bytes:
    if value == "GENESIS":
        return b"\x00" * 32
    if len(value) == 64:
        try:
            return bytes.fromhex(value)
        except ValueError:
            pass
    return hashlib.sha256(value.encode("utf-8")).digest()
