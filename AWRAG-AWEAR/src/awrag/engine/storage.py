from __future__ import annotations

import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .anchors import SYMBOL_BYTES, SYMBOL_SYSTEM, symbol_bytes, symbol_for, symbol_hex
from .base import (
    COUNT_BACKEND,
    DatasetPaths,
    dataset_paths,
    public_paths,
    safe_id,
    utc_now,
    unique_stamp,
    with_protected_notice,
    write_json,
)

ANCHOR_RECORD = struct.Struct(">6sQ")
RELATION_RECORD = struct.Struct(">6s6shI")
BLOCK_ANCHOR_RECORD = struct.Struct(">6sIH")


def ensure_dataset(runtime_root: str | Path, dataset_id: str, *, owner: str = "operator_defined") -> dict[str, Any]:
    paths = dataset_paths(runtime_root, dataset_id)
    for path in (
        paths.root,
        paths.incoming,
        paths.state,
        paths.counts,
        paths.coordinates,
        paths.citations,
        paths.outputs,
        paths.receipts,
        paths.qa,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if not paths.manifest_path.exists():
        write_json(paths.manifest_path, {
            "schema": "awrag_dataset_manifest@1",
            "created_at": utc_now(),
            "dataset_id": safe_id(dataset_id),
            "owner": owner,
            "scope": "dataset_local",
            "rag_allowed": True,
            "promotion_allowed": False,
            "global_training_allowed": False,
            "delete_with_dataset": True,
            "counts_are_memory": False,
            "counts_belong_to": "dataset",
            "count_backend": COUNT_BACKEND,
            "symbol_system": SYMBOL_SYSTEM,
            "symbol_bytes": SYMBOL_BYTES,
            "symbol_scope": "dataset_local_demo_only",
            "symbol_transferable": False,
            "anchorworks_lifetime_symbol_compatible": False,
        })
    if not paths.lexicon_path.exists():
        write_lexicon(paths, Counter())
    touch_binary_files(paths)
    return status(runtime_root, dataset_id)

def status(runtime_root: str | Path, dataset_id: str) -> dict[str, Any]:
    paths = dataset_paths(runtime_root, dataset_id)
    touch_binary_files(paths)
    readiness = index_readiness(runtime_root, dataset_id)
    return with_protected_notice({
        "schema": "awrag_dataset_status@1",
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "dataset_root": str(paths.root),
        "count_backend": COUNT_BACKEND,
        "anchor_counts_path": str(paths.anchor_counts_path),
        "relation_counts_path": str(paths.relation_counts_path),
        "block_anchor_postings_path": str(paths.block_anchor_path),
        "dataset_lexicon_path": str(paths.lexicon_path),
        "anchor_count": record_count(paths.anchor_counts_path, ANCHOR_RECORD.size),
        "relation_count": record_count(paths.relation_counts_path, RELATION_RECORD.size),
        "block_anchor_posting_count": record_count(paths.block_anchor_path, BLOCK_ANCHOR_RECORD.size),
        "block_count": jsonl_count(paths.blocks_path),
        "citation_count": jsonl_count(paths.citations / "citations.jsonl"),
        "chat_metadata_row_count": jsonl_count(paths.chat_metadata_path),
        "chat_metadata_index_path": str(paths.chat_metadata_path),
        "qa_ledger_path": str(paths.qa_ledger_path),
        "qa_record_count": jsonl_count(paths.qa_ledger_path),
        "index_readiness": readiness,
        "index_status": readiness["status"],
        "query_allowed": readiness["query_allowed"],
        "persistent_memory": False,
    })

def index_readiness(runtime_root: str | Path, dataset_id: str) -> dict[str, Any]:
    """Report whether the built index/count surface is ready for query math.

    Canonical blocks are the evidence display surface. Native counts/postings
    are the query surface. Querying is not allowed until the built artifacts
    exist and are non-empty.
    """
    paths = dataset_paths(runtime_root, dataset_id)
    artifacts = {
        "manifest": _artifact_state(paths.manifest_path),
        "blocks": _artifact_state(paths.blocks_path),
        "dataset_lexicon": _artifact_state(paths.lexicon_path),
        "anchor_counts": _artifact_state(paths.anchor_counts_path),
        "relation_counts": _artifact_state(paths.relation_counts_path),
        "block_anchor_postings": _artifact_state(paths.block_anchor_path),
        "citations": _artifact_state(paths.citations / "citations.jsonl"),
        "coordinates": _artifact_state(paths.coordinates / "coordinate_index.jsonl"),
    }
    intake_receipt = _latest_intake_receipt(paths)
    artifacts["latest_intake_receipt"] = _artifact_state(intake_receipt) if intake_receipt else {
        "path": str(paths.receipts),
        "exists": False,
        "size_bytes": 0,
        "modified_time_ns": None,
    }

    reasons: list[str] = []
    for name, row in artifacts.items():
        if not row["exists"]:
            reasons.append(f"{name}_missing")
        elif int(row["size_bytes"]) <= 0:
            reasons.append(f"{name}_empty")

    counts = {
        "anchor_count": record_count(paths.anchor_counts_path, ANCHOR_RECORD.size),
        "relation_count": record_count(paths.relation_counts_path, RELATION_RECORD.size),
        "block_anchor_posting_count": record_count(paths.block_anchor_path, BLOCK_ANCHOR_RECORD.size),
        "block_count": jsonl_count(paths.blocks_path),
        "citation_count": jsonl_count(paths.citations / "citations.jsonl"),
        "coordinate_count": jsonl_count(paths.coordinates / "coordinate_index.jsonl"),
    }
    for name, count in counts.items():
        if count <= 0:
            reasons.append(f"{name}_zero")

    source_freshness = _source_freshness(intake_receipt, artifacts)
    if source_freshness["status"] == "stale_source_newer_than_index":
        reasons.append("source_newer_than_index")

    query_allowed = not reasons
    return {
        "schema": "awrag_index_readiness@1",
        "dataset_id": safe_id(dataset_id),
        "runtime_path": str(Path(runtime_root).expanduser().resolve()),
        "status": "INDEX_READY" if query_allowed else "INDEX_NOT_READY",
        "query_allowed": query_allowed,
        "reasons": reasons,
        "core_law": "Canonical blocks are the evidence display surface; index/count artifacts are the query surface.",
        "fallback_file_search_allowed": False,
        "artifacts": artifacts,
        "counts": counts,
        "source_freshness": source_freshness,
    }

def touch_binary_files(paths: DatasetPaths) -> None:
    paths.counts.mkdir(parents=True, exist_ok=True)
    for path in (paths.anchor_counts_path, paths.relation_counts_path, paths.block_anchor_path):
        path.touch(exist_ok=True)
    paths.blocks_path.parent.mkdir(parents=True, exist_ok=True)
    paths.blocks_path.touch(exist_ok=True)

def write_binary_counts(
    paths: DatasetPaths,
    anchors: Counter[str],
    relations: Counter[tuple[str, str, int]],
    block_anchors: list[tuple[str, int, int]],
    *,
    symbol_map: dict[str, str] | None = None,
) -> None:
    paths.counts.mkdir(parents=True, exist_ok=True)
    with paths.anchor_counts_path.open("wb") as handle:
        for anchor, observations in sorted(anchors.items()):
            handle.write(ANCHOR_RECORD.pack(_symbol_bytes_for(anchor, symbol_map), int(observations)))
    with paths.relation_counts_path.open("wb") as handle:
        for (anchor, neighbor, offset), observations in sorted(relations.items()):
            handle.write(RELATION_RECORD.pack(_symbol_bytes_for(anchor, symbol_map), _symbol_bytes_for(neighbor, symbol_map), int(offset), int(observations)))
    with paths.block_anchor_path.open("wb") as handle:
        for anchor, block_ordinal, position in sorted(block_anchors, key=lambda item: (_symbol_hex_for(item[0], symbol_map), item[1], item[2])):
            handle.write(BLOCK_ANCHOR_RECORD.pack(_symbol_bytes_for(anchor, symbol_map), int(block_ordinal), int(position)))

def iter_anchor_records(paths: DatasetPaths) -> Iterable[tuple[bytes, int]]:
    with paths.anchor_counts_path.open("rb") as handle:
        while chunk := handle.read(ANCHOR_RECORD.size):
            if len(chunk) == ANCHOR_RECORD.size:
                symbol, observations = ANCHOR_RECORD.unpack(chunk)
                yield symbol, int(observations)

def iter_relation_records(paths: DatasetPaths) -> Iterable[tuple[bytes, bytes, int, int]]:
    with paths.relation_counts_path.open("rb") as handle:
        while chunk := handle.read(RELATION_RECORD.size):
            if len(chunk) == RELATION_RECORD.size:
                anchor, neighbor, offset, observations = RELATION_RECORD.unpack(chunk)
                yield anchor, neighbor, int(offset), int(observations)

def read_block_anchor_rows(paths: DatasetPaths) -> list[tuple[bytes, int, int]]:
    rows: list[tuple[bytes, int, int]] = []
    with paths.block_anchor_path.open("rb") as handle:
        while chunk := handle.read(BLOCK_ANCHOR_RECORD.size):
            if len(chunk) == BLOCK_ANCHOR_RECORD.size:
                symbol, block_ordinal, position = BLOCK_ANCHOR_RECORD.unpack(chunk)
                rows.append((symbol, int(block_ordinal), int(position)))
    return rows

def write_blocks_jsonl(paths: DatasetPaths, blocks: list[dict[str, Any]]) -> None:
    paths.blocks_path.parent.mkdir(parents=True, exist_ok=True)
    with paths.blocks_path.open("w", encoding="utf-8", newline="\n") as handle:
        for block in blocks:
            handle.write(json.dumps(block, ensure_ascii=True) + "\n")

def read_blocks(paths: DatasetPaths) -> dict[int, dict[str, Any]]:
    blocks: dict[int, dict[str, Any]] = {}
    if not paths.blocks_path.exists():
        return blocks
    for line in paths.blocks_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        block = json.loads(line)
        blocks[int(block["block_ordinal"])] = block
    return blocks

def write_lexicon(
    paths: DatasetPaths,
    anchors: Counter[str],
    *,
    symbol_map: dict[str, str] | None = None,
    symbol_allocation: dict[str, Any] | None = None,
) -> None:
    rows = [
        {
            "anchor": anchor,
            "symbol": _symbol_hex_for(anchor, symbol_map),
            "symbol_system": SYMBOL_SYSTEM,
            "symbol_bytes": SYMBOL_BYTES,
            "observations": int(observations),
            "scope": "dataset_local",
            "symbol_scope": "dataset_local_demo_only",
            "transferable": False,
            "lifetime_allowed": False,
            "anchorworks_lifetime_symbol_compatible": False,
            "promotion_allowed": False,
        }
        for anchor, observations in sorted(anchors.items())
    ]
    write_json(paths.lexicon_path, {
        "schema": "awrag_dataset_lexicon@1",
        "dataset_id": paths.root.name,
        "scope": "dataset_local",
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "symbol_scope": "dataset_local_demo_only",
        "symbol_transferable": False,
        "symbol_assignment": (
            symbol_allocation.get("allocator_kind")
            if isinstance(symbol_allocation, dict)
            else "deterministic_anchor_hash_6b"
        ),
        "symbol_start": symbol_allocation.get("symbol_start") if isinstance(symbol_allocation, dict) else None,
        "symbol_end": symbol_allocation.get("symbol_end") if isinstance(symbol_allocation, dict) else None,
        "symbolizer_state_receipt": symbol_allocation.get("symbolizer_state_receipt") if isinstance(symbol_allocation, dict) else None,
        "lifetime_allowed": False,
        "anchorworks_lifetime_symbol_compatible": False,
        "anchor_count": len(rows),
        "anchors": rows,
    })

def read_symbol_to_anchor(paths: DatasetPaths) -> dict[str, str]:
    if not paths.lexicon_path.exists():
        return {}
    payload = json.loads(paths.lexicon_path.read_text(encoding="utf-8"))
    return {str(row["symbol"]): str(row["anchor"]) for row in payload.get("anchors", [])}

def read_anchor_to_symbol(paths: DatasetPaths) -> dict[str, str]:
    if not paths.lexicon_path.exists():
        return {}
    payload = json.loads(paths.lexicon_path.read_text(encoding="utf-8"))
    return {str(row["anchor"]): str(row["symbol"]) for row in payload.get("anchors", [])}

def _symbol_hex_for(anchor: str, symbol_map: dict[str, str] | None = None) -> str:
    if symbol_map is not None:
        symbol = symbol_map.get(anchor)
        if symbol is None:
            raise KeyError(f"missing allocated symbol for anchor: {anchor}")
        return symbol
    return symbol_for(anchor)

def _symbol_bytes_for(anchor: str, symbol_map: dict[str, str] | None = None) -> bytes:
    if symbol_map is not None:
        return bytes.fromhex(_symbol_hex_for(anchor, symbol_map)[2:])
    return symbol_bytes(anchor)

def write_citation_jsonl(paths: DatasetPaths, blocks: list[dict[str, Any]]) -> None:
    path = paths.citations / "citations.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(blocks, key=lambda item: str(item["citation_id"])):
            handle.write(json.dumps(with_protected_notice({
                "schema": "awrag_citation@1",
                "citation_id": row["citation_id"],
                "marker": row["marker"],
                "file_path": row["file_path"],
                "line_start": row["line_start"],
                "line_end": row["line_end"],
                "text_hash": row["text_hash"],
                "scope": "dataset_local",
            }), ensure_ascii=True) + "\n")

def write_coordinate_index(paths: DatasetPaths, blocks: list[dict[str, Any]]) -> None:
    path = paths.coordinates / "coordinate_index.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(blocks, key=lambda item: (str(item["file_path"]), int(item["line_start"]))):
            handle.write(json.dumps(with_protected_notice({
                "schema": "awrag_coordinate@1",
                "block_id": row["block_id"],
                "file_path": row["file_path"],
                "line_start": row["line_start"],
                "line_end": row["line_end"],
                "citation_id": row["citation_id"],
                "scope": "dataset_local",
            }), ensure_ascii=True) + "\n")

def write_chat_metadata_index(paths: DatasetPaths, rows: list[dict[str, Any]]) -> None:
    path = paths.chat_metadata_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(rows, key=lambda item: (str(item.get("created_at", "")), int(item["block_ordinal"]))):
            handle.write(json.dumps(with_protected_notice(row), ensure_ascii=True) + "\n")

def record_count(path: Path, record_size: int) -> int:
    if not path.exists():
        return 0
    return path.stat().st_size // record_size

def jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

def _artifact_state(path: Path) -> dict[str, Any]:
    exists = path.exists()
    stat = path.stat() if exists else None
    return {
        "path": str(path),
        "exists": exists,
        "size_bytes": int(stat.st_size) if stat else 0,
        "modified_time_ns": int(stat.st_mtime_ns) if stat else None,
    }

def _latest_intake_receipt(paths: DatasetPaths) -> Path | None:
    if not paths.receipts.exists():
        return None
    receipts = sorted(paths.receipts.glob("intake_*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
    return receipts[0] if receipts else None

def _source_freshness(intake_receipt: Path | None, artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if intake_receipt is None or not intake_receipt.exists():
        return {
            "status": "unknown_no_intake_receipt",
            "checked": False,
            "source_file_count": 0,
        }
    try:
        payload = json.loads(intake_receipt.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "unknown_unreadable_intake_receipt",
            "checked": False,
            "source_file_count": 0,
        }
    sources = payload.get("sources") or []
    source_paths = [Path(str(row.get("path"))) for row in sources if row.get("path")]
    existing_sources = [path for path in source_paths if path.exists()]
    if not existing_sources:
        return {
            "status": "unknown_source_files_unavailable",
            "checked": False,
            "source_file_count": len(source_paths),
        }
    newest_source = max(path.stat().st_mtime_ns for path in existing_sources)
    index_times = [
        int(row["modified_time_ns"])
        for name, row in artifacts.items()
        if name != "latest_intake_receipt" and row.get("modified_time_ns") is not None
    ]
    oldest_index = min(index_times) if index_times else None
    stale = oldest_index is not None and newest_source > oldest_index
    return {
        "status": "stale_source_newer_than_index" if stale else "fresh_or_equal",
        "checked": True,
        "source_file_count": len(source_paths),
        "existing_source_file_count": len(existing_sources),
        "newest_source_modified_time_ns": int(newest_source),
        "oldest_index_modified_time_ns": int(oldest_index) if oldest_index is not None else None,
    }

