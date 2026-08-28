from __future__ import annotations

import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from .base import SYMBOL_BYTES, SYMBOL_SYSTEM, dataset_paths, safe_id, utc_now, unique_stamp, with_protected_notice, write_json

MAX_SYMBOL_VALUE = (1 << (SYMBOL_BYTES * 8)) - 1
ANCHOR_RECORD_HEADER = struct.Struct(">6sQ")


def symbol_hex_from_int(value: int) -> str:
    if value < 0 or value > MAX_SYMBOL_VALUE:
        raise ValueError(f"symbol value out of range for {SYMBOL_BYTES} bytes: {value}")
    return "0x" + int(value).to_bytes(SYMBOL_BYTES, "big").hex().upper()


def allocate_dataset_symbols(
    runtime_root: str | Path,
    dataset_id: str,
    anchors: Counter[str],
) -> dict[str, Any]:
    """Allocate one monotonic workspace symbol range for a dataset intake."""

    runtime = Path(runtime_root).expanduser().resolve()
    dataset = safe_id(dataset_id)
    symbolizer_root = runtime / "symbolizer"
    receipts_root = symbolizer_root / "receipts"
    state_path = symbolizer_root / "symbol_state.json"
    receipts_root.mkdir(parents=True, exist_ok=True)

    active = scan_active_symbol_ranges(runtime, exclude_dataset_id=dataset)
    state = _load_or_initialize_state(state_path, active)
    _verify_state_matches_active_ranges(state, active)

    sorted_anchors = sorted(anchors)
    symbol_count = len(sorted_anchors)
    last_before = int(state.get("last_assigned_symbol", -1))
    start = last_before + 1 if symbol_count else None
    end = last_before + symbol_count if symbol_count else None
    if end is not None and end > MAX_SYMBOL_VALUE:
        raise RuntimeError("SYMBOLIZER_RANGE_EXHAUSTED")

    symbol_map = {
        anchor: symbol_hex_from_int(last_before + index)
        for index, anchor in enumerate(sorted_anchors, start=1)
    }
    receipt_path = receipts_root / f"symbolizer_{unique_stamp()}_{dataset}.json"
    receipt = with_protected_notice({
        "schema": "awrag_symbolizer_allocation_receipt@1",
        "created_at": utc_now(),
        "dataset_id": dataset,
        "runtime_root": str(runtime),
        "symbolizer_state_path": str(state_path),
        "symbol_namespace": SYMBOL_SYSTEM,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "allocator_kind": "workspace_monotonic_integer_6b",
        "last_assigned_symbol_before": last_before,
        "last_assigned_symbol_after": int(end if end is not None else last_before),
        "symbol_start": int(start) if start is not None else None,
        "symbol_end": int(end) if end is not None else None,
        "symbol_count": int(symbol_count),
        "collision_count": 0,
        "range_overlap_detected": False,
        "active_ranges_checked": active["ranges"],
        "state_verified_before_allocation": True,
    })
    write_json(receipt_path, receipt)

    if symbol_count:
        state.setdefault("assigned_ranges", []).append({
            "dataset_id": dataset,
            "dataset_folder": str(dataset_paths(runtime, dataset).root),
            "range_start": int(start),
            "range_end": int(end),
            "symbol_count": int(symbol_count),
            "created_at": utc_now(),
            "receipt": str(receipt_path),
        })
        state["last_assigned_symbol"] = int(end)
    state["updated_at"] = utc_now()
    write_json(state_path, state)
    return {
        "schema": "awrag_dataset_symbol_allocation@1",
        "dataset_id": dataset,
        "symbol_map": symbol_map,
        "symbol_start": int(start) if start is not None else None,
        "symbol_end": int(end) if end is not None else None,
        "symbol_count": int(symbol_count),
        "last_assigned_symbol_before": last_before,
        "last_assigned_symbol_after": int(end if end is not None else last_before),
        "symbolizer_state_path": str(state_path),
        "symbolizer_state_receipt": str(receipt_path),
        "allocator_kind": "workspace_monotonic_integer_6b",
    }


def update_dataset_manifest_symbol_allocation(paths: Any, allocation: dict[str, Any]) -> None:
    manifest = _read_json(paths.manifest_path)
    manifest.update({
        "symbol_allocator_kind": allocation["allocator_kind"],
        "symbolizer_state_path": allocation["symbolizer_state_path"],
        "symbolizer_state_receipt": allocation["symbolizer_state_receipt"],
        "symbol_start": allocation["symbol_start"],
        "symbol_end": allocation["symbol_end"],
        "symbol_count": allocation["symbol_count"],
        "symbol_assignment": "workspace_monotonic_integer_6b",
        "symbol_collision_count": 0,
        "symbol_range_overlap_detected": False,
    })
    write_json(paths.manifest_path, manifest)


def scan_active_symbol_ranges(runtime_root: str | Path, *, exclude_dataset_id: str | None = None) -> dict[str, Any]:
    runtime = Path(runtime_root).expanduser().resolve()
    datasets_root = runtime / "datasets"
    ranges: list[dict[str, Any]] = []
    if datasets_root.exists():
        for dataset_root in sorted(path for path in datasets_root.iterdir() if path.is_dir()):
            dataset_id = dataset_root.name
            if exclude_dataset_id is not None and dataset_id == safe_id(exclude_dataset_id):
                continue
            manifest = _read_json(dataset_root / "dataset_manifest.json")
            start = manifest.get("symbol_start")
            end = manifest.get("symbol_end")
            if start is None or end is None:
                legacy = _legacy_symbol_high_water(dataset_root)
                if legacy["highest_symbol"] >= 0:
                    ranges.append({
                        "dataset_id": dataset_id,
                        "dataset_folder": str(dataset_root),
                        "range_start": 0,
                        "range_end": int(legacy["highest_symbol"]),
                        "symbol_count": int(legacy["symbol_count"]),
                        "manifest_path": str(dataset_root / "dataset_manifest.json"),
                        "range_source": "legacy_symbols_without_manifest_range",
                    })
                continue
            ranges.append({
                "dataset_id": dataset_id,
                "dataset_folder": str(dataset_root),
                "range_start": int(start),
                "range_end": int(end),
                "symbol_count": int(manifest.get("symbol_count") or (int(end) - int(start) + 1)),
                "manifest_path": str(dataset_root / "dataset_manifest.json"),
                "range_source": "manifest",
            })
    highest = max((int(row["range_end"]) for row in ranges), default=-1)
    return {
        "schema": "awrag_active_symbol_range_scan@1",
        "runtime_root": str(runtime),
        "ranges": ranges,
        "highest_symbol": int(highest),
    }


def _load_or_initialize_state(state_path: Path, active: dict[str, Any]) -> dict[str, Any]:
    if state_path.exists():
        return _read_json(state_path)
    if int(active["highest_symbol"]) >= 0:
        raise RuntimeError("SYMBOLIZER_STATE_MISMATCH: active dataset symbol ranges exist but workspace state is missing")
    return with_protected_notice({
        "schema": "awrag_workspace_symbolizer_state@1",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "symbol_namespace": SYMBOL_SYSTEM,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "allocator_kind": "workspace_monotonic_integer_6b",
        "last_assigned_symbol": -1,
        "assigned_ranges": [],
        "decommission_reset_allowed_only_by_explicit_operation": True,
    })


def _verify_state_matches_active_ranges(state: dict[str, Any], active: dict[str, Any]) -> None:
    if state.get("allocator_kind") != "workspace_monotonic_integer_6b":
        raise RuntimeError("SYMBOLIZER_STATE_MISMATCH: allocator kind is not workspace_monotonic_integer_6b")
    state_last = int(state.get("last_assigned_symbol", -1))
    active_highest = int(active.get("highest_symbol", -1))
    if state_last < active_highest:
        raise RuntimeError(
            "SYMBOLIZER_STATE_MISMATCH: persisted symbolizer state is lower than highest active dataset symbol"
        )
    ranges = list(active.get("ranges") or [])
    _assert_no_range_overlaps(ranges)


def _assert_no_range_overlaps(ranges: list[dict[str, Any]]) -> None:
    ordered = sorted(ranges, key=lambda row: int(row["range_start"]))
    previous: dict[str, Any] | None = None
    for row in ordered:
        if previous is not None and int(row["range_start"]) <= int(previous["range_end"]):
            raise RuntimeError("SYMBOLIZER_STATE_MISMATCH: active dataset symbol ranges overlap")
        previous = row


def _legacy_symbol_high_water(dataset_root: Path) -> dict[str, int]:
    values: list[int] = []
    lexicon = _read_json(dataset_root / "state" / "dataset_lexicon.json")
    for row in lexicon.get("anchors", []) if isinstance(lexicon.get("anchors"), list) else []:
        symbol = str(row.get("symbol") or "")
        value = _symbol_int_from_hex(symbol)
        if value is not None:
            values.append(value)
    count_path = dataset_root / "counts" / "anchor_counts.awbin"
    if count_path.exists():
        with count_path.open("rb") as handle:
            while chunk := handle.read(ANCHOR_RECORD_HEADER.size):
                if len(chunk) != ANCHOR_RECORD_HEADER.size:
                    continue
                symbol, _observations = ANCHOR_RECORD_HEADER.unpack(chunk)
                values.append(int.from_bytes(symbol, "big"))
    return {
        "highest_symbol": max(values, default=-1),
        "symbol_count": len(set(values)),
    }


def _symbol_int_from_hex(symbol: str) -> int | None:
    if not symbol.startswith("0x"):
        return None
    try:
        raw = bytes.fromhex(symbol[2:])
    except ValueError:
        return None
    if len(raw) != SYMBOL_BYTES:
        return None
    return int.from_bytes(raw, "big")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
