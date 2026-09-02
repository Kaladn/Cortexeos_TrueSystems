from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import COUNT_BACKEND, SYMBOL_BYTES, SYMBOL_SYSTEM, dataset_paths, safe_id, with_protected_notice
from .hardware import detect_system_resources
from .qa_ledger import jsonl_count
from .storage import ANCHOR_RECORD, BLOCK_ANCHOR_RECORD, RELATION_RECORD, block_anchor_record, index_readiness, record_count


def system_metrics(
    runtime_root: str | Path | None = None,
    dataset_id: str | None = None,
    *,
    workspace_path: str | Path | None = None,
    repo_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return read-only operator metrics without touching dataset artifacts."""

    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else None
    workspace = Path(workspace_path).expanduser().resolve() if workspace_path is not None else None
    repo = Path(repo_path).expanduser().resolve() if repo_path is not None else _find_repo_root()
    resources = detect_system_resources()
    ram_total = resources.get("total_ram_bytes")
    ram_available = resources.get("available_ram_bytes")
    ram_used = int(ram_total) - int(ram_available) if isinstance(ram_total, int) and isinstance(ram_available, int) else None
    reserve_15 = int(int(ram_total) * 0.15) if isinstance(ram_total, int) else None

    datasets_root = runtime / "datasets" if runtime is not None else None
    dataset_ids = _dataset_ids(datasets_root)
    per_dataset = [_dataset_summary(runtime, item) for item in dataset_ids] if runtime is not None else []
    active_dataset = _dataset_summary(runtime, dataset_id) if runtime is not None and dataset_id else None
    symbolizer = _symbolizer_audit(runtime, per_dataset) if runtime is not None else _symbolizer_audit(None, [])

    return with_protected_notice({
        "schema": "truemem_system_metrics@1",
        "no_mutation": True,
        "runtime_path": str(runtime) if runtime is not None else None,
        "workspace_path": str(workspace) if workspace is not None else None,
        "repo_path": str(repo) if repo is not None else None,
        "active_dataset_id": safe_id(dataset_id) if dataset_id else None,
        "dataset_count": len(dataset_ids),
        "datasets": per_dataset,
        "active_dataset": active_dataset,
        "totals": _totals(per_dataset),
        "resources": {
            "logical_cpu_count": resources.get("logical_cpu_count"),
            "ram_total_bytes": ram_total,
            "ram_used_bytes": ram_used,
            "ram_available_bytes": ram_available,
            "ram_reserved_15_percent_bytes": reserve_15,
            "ram_available_after_15_percent_reserve_bytes": (
                max(0, int(ram_available) - int(reserve_15))
                if isinstance(ram_available, int) and isinstance(reserve_15, int)
                else None
            ),
            "gpu_detection_method": resources.get("gpu_detection_method"),
            "gpu_devices": resources.get("gpu_devices", []),
            "max_gpu_memory_bytes": resources.get("max_gpu_memory_bytes"),
        },
        "symbol_allocation_audit": symbolizer,
        "count_backend": COUNT_BACKEND,
    })


def _dataset_ids(datasets_root: Path | None) -> list[str]:
    if datasets_root is None or not datasets_root.exists():
        return []
    return sorted(item.name for item in datasets_root.iterdir() if item.is_dir())


def _dataset_summary(runtime_root: Path, dataset_id: str | None) -> dict[str, Any] | None:
    if not dataset_id:
        return None
    paths = dataset_paths(runtime_root, dataset_id)
    manifest = _read_json(paths.manifest_path)
    latest_intake = _latest_json(paths.receipts, "intake_*.json")
    latest_query = _latest_json(paths.outputs, "query_*.json")
    intake_payload = _read_json(latest_intake) if latest_intake else {}
    readiness = index_readiness(runtime_root, dataset_id)
    counts = readiness.get("counts", {}) if isinstance(readiness, dict) else {}
    return {
        "dataset_id": safe_id(dataset_id),
        "dataset_root": str(paths.root),
        "exists": paths.root.exists(),
        "manifest_path": str(paths.manifest_path),
        "manifest_exists": paths.manifest_path.exists(),
        "index_status": readiness.get("status") if isinstance(readiness, dict) else None,
        "query_allowed": readiness.get("query_allowed") if isinstance(readiness, dict) else False,
        "admitted_dataset_artifact_size_bytes": _tree_size(paths.root),
        "anchor_count": int(counts.get("anchor_count", record_count(paths.anchor_counts_path, ANCHOR_RECORD.size)) or 0),
        "relation_count": int(counts.get("relation_count", record_count(paths.relation_counts_path, RELATION_RECORD.size)) or 0),
        "block_anchor_posting_count": int(counts.get("block_anchor_posting_count", record_count(paths.block_anchor_path, block_anchor_record(paths).size)) or 0),
        "block_count": int(counts.get("block_count", jsonl_count(paths.blocks_path)) or 0),
        "citation_count": int(counts.get("citation_count", jsonl_count(paths.citations / "citations.jsonl")) or 0),
        "coordinate_count": int(counts.get("coordinate_count", jsonl_count(paths.coordinates / "coordinate_index.jsonl")) or 0),
        "qa_record_count": jsonl_count(paths.qa_ledger_path),
        "qa_ledger_path": str(paths.qa_ledger_path),
        "symbol_start": manifest.get("symbol_start"),
        "symbol_end": manifest.get("symbol_end"),
        "symbol_count": _manifest_symbol_count(manifest),
        "symbol_range_recorded": "symbol_start" in manifest and "symbol_end" in manifest,
        "symbol_system": manifest.get("symbol_system", SYMBOL_SYSTEM),
        "symbol_bytes": manifest.get("symbol_bytes", SYMBOL_BYTES),
        "last_ingest_receipt_path": str(latest_intake) if latest_intake else None,
        "last_query_receipt_path": str(latest_query) if latest_query else None,
        "workers_requested_last_ingest": intake_payload.get("workers_requested"),
        "workers_actual_last_ingest": intake_payload.get("workers_actual"),
        "last_ingest_resource_plan": intake_payload.get("resource_plan") if isinstance(intake_payload, dict) else None,
    }


def _manifest_symbol_count(manifest: dict[str, Any]) -> int | None:
    symbol_count = manifest.get("symbol_count")
    if symbol_count is not None:
        return int(symbol_count)
    start = manifest.get("symbol_start")
    end = manifest.get("symbol_end")
    if start is None or end is None:
        return None
    return int(end) - int(start) + 1


def _totals(datasets: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        "admitted_dataset_artifact_size_bytes",
        "anchor_count",
        "relation_count",
        "block_anchor_posting_count",
        "block_count",
        "citation_count",
        "coordinate_count",
        "qa_record_count",
    ]
    return {
        field: sum(int(row.get(field) or 0) for row in datasets)
        for field in fields
    } | {
        "total_symbols_allocated": sum(int(row.get("symbol_count") or 0) for row in datasets if row.get("symbol_range_recorded")),
        "total_dataset_lexicon_symbols_observed": sum(int(row.get("anchor_count") or 0) for row in datasets),
        "last_global_symbol_id": max(
            (int(row["symbol_end"]) for row in datasets if row.get("symbol_end") is not None),
            default=None,
        ),
    }


def _symbolizer_audit(runtime: Path | None, datasets: list[dict[str, Any]]) -> dict[str, Any]:
    state_path = runtime / "symbolizer" / "symbol_state.json" if runtime is not None else None
    state = _read_json(state_path) if state_path is not None else {}
    active = bool(state) and state.get("allocator_kind") == "workspace_monotonic_integer_6b"
    ranges_recorded = all(bool(row.get("symbol_range_recorded")) for row in datasets) if datasets else False
    first_start = min((int(row["symbol_start"]) for row in datasets if row.get("symbol_start") is not None), default=None)
    sorted_ranges = sorted(
        [
            (int(row["symbol_start"]), int(row["symbol_end"]), str(row["dataset_id"]))
            for row in datasets
            if row.get("symbol_start") is not None and row.get("symbol_end") is not None
        ],
        key=lambda item: item[0],
    )
    contiguous = True
    previous_end: int | None = None
    for start, end, _dataset in sorted_ranges:
        if previous_end is not None and start != previous_end + 1:
            contiguous = False
        previous_end = end
    last_symbol = state.get("last_assigned_symbol") if active else None
    return {
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "current_allocator_kind": state.get("allocator_kind") if active else "deterministic_anchor_hash_6b",
        "workspace_monotonic_allocator_active": bool(active),
        "global_monotonic_allocator_active": bool(active),
        "symbolizer_state_path": str(state_path) if state_path is not None else None,
        "last_global_symbol_id": last_symbol,
        "last_workspace_symbol_id": last_symbol,
        "symbol_ranges_recorded_in_manifests": bool(ranges_recorded),
        "first_dataset_starts_at_zero_verified": first_start == 0 if sorted_ranges else False,
        "next_dataset_starts_at_last_plus_one_verified": bool(sorted_ranges and contiguous),
        "audit_result": "ACTIVE" if active else "NOT_ACTIVE_IN_CURRENT_CODE",
        "operator_note": (
            "Workspace monotonic symbol allocation is active for datasets in this runtime."
            if active
            else "No workspace monotonic symbolizer state exists for this runtime."
        ),
    }


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_json(root: Path, pattern: str) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(root.glob(pattern), key=lambda item: item.stat().st_mtime_ns, reverse=True)
    return matches[0] if matches else None


def _tree_size(root: Path) -> int:
    if not root.exists():
        return 0
    total = 0
    for item in root.rglob("*"):
        if item.is_file():
            try:
                total += int(item.stat().st_size)
            except OSError:
                continue
    return total


def _find_repo_root() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return None
