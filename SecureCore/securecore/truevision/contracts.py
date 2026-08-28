"""TrueVision SC Edition contracts.

Security goal: record quick visual state changes from GPU pre-render state
without storing frames, screenshots, video, text-extraction labels, or model
detections. The output is intentionally small.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from securecore.time import is_canonical_utc_timestamp


EDITION = "truevision_sc_edition"
KIND = "truevision_sc_state_change"
CAPTURE_SURFACES = {"gpu_pre_render"}
FORBIDDEN_KEYS = {
    "frame",
    "frame_bytes",
    "image",
    "image_bytes",
    "pixels",
    "raw_frame",
    "raw_pixels",
    "screenshot",
    "text",
    "video",
    "video_bytes",
    "video_path",
}
FORBIDDEN_TERMS = {"yo" + "lo", "o" + "cr", "recognition", "ultra" + "lytics", "dark" + "net"}


class TrueVisionSCError(ValueError):
    """Raised when a TrueVision SC Edition record violates the compact contract."""


def grid_hash(grid: list[list[int]]) -> str:
    return hashlib.sha256(
        json.dumps(grid, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def build_state_change(
    *,
    change_id: str,
    source_id: str,
    session_id: str,
    observed_at_utc: str,
    native_geometry: dict[str, int],
    grid_shape: list[int],
    current_grid_hash: str,
    previous_grid_hash: str,
    changed_cell_count: int,
    total_cell_count: int,
    letterbox_cell_count: int,
    capture_surface: str = "gpu_pre_render",
    glyph_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total = max(1, int(total_cell_count))
    changed = max(0, int(changed_cell_count))
    record = {
        "schema_version": 1,
        "edition": EDITION,
        "kind": KIND,
        "change_id": str(change_id),
        "source_id": source_id,
        "session_id": session_id,
        "observed_at_utc": observed_at_utc,
        "capture_surface": capture_surface,
        "native_geometry": dict(native_geometry),
        "grid_shape": list(grid_shape),
        "current_grid_hash": current_grid_hash,
        "previous_grid_hash": previous_grid_hash,
        "changed_cell_count": changed,
        "total_cell_count": total,
        "change_ratio": round(changed / total, 6),
        "letterbox_cell_count": max(0, int(letterbox_cell_count)),
        "distortion_applied": False,
        "state_flags": ["visual_state_changed"] if changed else [],
        "analysis_status": "not_run",
        "payload_class": "small_metadata",
    }
    if glyph_summary is not None:
        record["glyph_summary"] = dict(glyph_summary)
    return record


def validate_state_change(record: dict[str, Any]) -> dict[str, Any]:
    _require(record, "schema_version", 1)
    _require(record, "edition", EDITION)
    _require(record, "kind", KIND)
    for field in ("change_id", "source_id", "session_id", "observed_at_utc"):
        _require_nonempty_string(record, field)
    if not is_canonical_utc_timestamp(record["observed_at_utc"]):
        raise TrueVisionSCError("observed_at_utc must use canonical UTC timestamp format")
    if record.get("capture_surface") not in CAPTURE_SURFACES:
        raise TrueVisionSCError("capture_surface must be gpu_pre_render")
    _require_int_dict(record, "native_geometry", ("width", "height"))
    _require_grid_shape(record.get("grid_shape"))
    for field in ("current_grid_hash", "previous_grid_hash"):
        _require_nonempty_string(record, field)
    for field in ("changed_cell_count", "total_cell_count", "letterbox_cell_count"):
        if not isinstance(record.get(field), int) or record[field] < 0:
            raise TrueVisionSCError(f"{field} must be a non-negative integer")
    if record["total_cell_count"] < 1:
        raise TrueVisionSCError("total_cell_count must be positive")
    expected_ratio = round(record["changed_cell_count"] / record["total_cell_count"], 6)
    if record.get("change_ratio") != expected_ratio:
        raise TrueVisionSCError("change_ratio does not match changed/total cells")
    _require(record, "distortion_applied", False)
    _require(record, "analysis_status", "not_run")
    _require(record, "payload_class", "small_metadata")
    if "glyph_summary" in record:
        _validate_glyph_summary(record["glyph_summary"])
    _reject_forbidden(record)
    return dict(record)


def _reject_forbidden(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            clean_key = str(key).casefold()
            if clean_key in FORBIDDEN_KEYS:
                raise TrueVisionSCError(f"forbidden visual payload field: {path}{key}")
            _reject_terms(clean_key)
            _reject_forbidden(child, f"{path}{key}.")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden(child, f"{path}{index}.")
    elif isinstance(value, str):
        _reject_terms(value)


def _reject_terms(value: str) -> None:
    clean = str(value or "").casefold()
    if any(term in clean for term in FORBIDDEN_TERMS):
        raise TrueVisionSCError("recognition/detector language is not allowed in TrueVision SC Edition")


def _require(row: dict[str, Any], field: str, expected: Any) -> None:
    if row.get(field) != expected:
        raise TrueVisionSCError(f"{field} must be {expected!r}")


def _require_nonempty_string(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), str) or not row[field].strip():
        raise TrueVisionSCError(f"{field} must be a non-empty string")


def _require_int_dict(row: dict[str, Any], field: str, keys: tuple[str, ...]) -> None:
    value = row.get(field)
    if not isinstance(value, dict):
        raise TrueVisionSCError(f"{field} must be an object")
    for key in keys:
        if not isinstance(value.get(key), int) or value[key] < 0:
            raise TrueVisionSCError(f"{field}.{key} must be a non-negative integer")


def _require_grid_shape(value: Any) -> None:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) and item > 0 for item in value)
    ):
        raise TrueVisionSCError("grid_shape must be [positive_int, positive_int]")


def _validate_glyph_summary(value: Any) -> None:
    if not isinstance(value, dict):
        raise TrueVisionSCError("glyph_summary must be an object")
    for field in ("known_pattern_count", "unknown_pattern_count"):
        if not isinstance(value.get(field), int) or value[field] < 0:
            raise TrueVisionSCError(f"glyph_summary.{field} must be a non-negative integer")
    for field in ("known_pattern_hashes", "unknown_pattern_hashes", "anomaly_kinds"):
        if field in value and (
            not isinstance(value[field], list)
            or not all(isinstance(item, str) for item in value[field])
        ):
            raise TrueVisionSCError(f"glyph_summary.{field} must be a list of strings")
    if value.get("text_reconstruction_allowed") is not False:
        raise TrueVisionSCError("glyph_summary.text_reconstruction_allowed must be false")
    if value.get("raw_content_stored") is not False:
        raise TrueVisionSCError("glyph_summary.raw_content_stored must be false")
    if value.get("fact_authority") is not False:
        raise TrueVisionSCError("glyph_summary.fact_authority must be false")
