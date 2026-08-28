from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine import (
    ANCHOR_RECORD,
    BLOCK_ANCHOR_RECORD,
    COUNT_BACKEND,
    RELATION_RECORD,
    SYMBOL_BYTES,
    SYMBOL_SYSTEM,
    anchorize,
    dataset_paths,
    jsonl_count,
    protected_notice,
    record_count,
    safe_id,
    with_protected_notice,
)


def get_protected_notice() -> dict[str, Any]:
    """Return the public-review notice without reading or writing dataset files."""
    return protected_notice()


def get_status(runtime_root: str | Path, dataset_id: str) -> dict[str, Any]:
    """Read dataset status without creating or touching dataset artifacts."""
    paths = dataset_paths(runtime_root, dataset_id)
    return with_protected_notice({
        "schema": "awrag_ui_status@1",
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
        "persistent_memory": False,
        "read_only": True,
    })


def get_manifest(runtime_root: str | Path, dataset_id: str) -> dict[str, Any]:
    """Return the existing dataset manifest exactly as stored."""
    paths = dataset_paths(runtime_root, dataset_id)
    return _read_json(paths.manifest_path)


def search_lexicon(
    runtime_root: str | Path,
    dataset_id: str,
    *,
    query: str | None = None,
    prefix: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Search the dataset-local lexicon for display."""
    rows = _lexicon_rows(runtime_root, dataset_id)
    normalized_query = (query or "").casefold().strip()
    normalized_prefix = (prefix or "").casefold().strip()
    max_rows = _bounded_limit(limit)

    matches: list[dict[str, Any]] = []
    for row in rows:
        anchor = str(row.get("anchor", ""))
        symbol = str(row.get("symbol", ""))
        anchor_key = anchor.casefold()
        symbol_key = symbol.casefold()
        if normalized_query and normalized_query not in anchor_key and normalized_query not in symbol_key:
            continue
        if normalized_prefix and not anchor_key.startswith(normalized_prefix):
            continue
        matches.append(dict(row))

    return with_protected_notice({
        "schema": "awrag_ui_lexicon_search@1",
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "query": query,
        "prefix": prefix,
        "limit": max_rows,
        "total_matches": len(matches),
        "returned_count": min(len(matches), max_rows),
        "anchors": matches[:max_rows],
        "read_only": True,
    })


def get_anchor_detail(
    runtime_root: str | Path,
    dataset_id: str,
    *,
    anchor: str | None = None,
    symbol: str | None = None,
) -> dict[str, Any]:
    """Return one lexicon row by anchor or symbol for read-only UI display."""
    if not anchor and not symbol:
        raise ValueError("anchor or symbol is required")

    anchor_key = (anchor or "").casefold()
    symbol_key = (symbol or "").casefold()
    for row in _lexicon_rows(runtime_root, dataset_id):
        row_anchor = str(row.get("anchor", ""))
        row_symbol = str(row.get("symbol", ""))
        if anchor_key and row_anchor.casefold() == anchor_key:
            return _anchor_detail_payload(runtime_root, dataset_id, row)
        if symbol_key and row_symbol.casefold() == symbol_key:
            return _anchor_detail_payload(runtime_root, dataset_id, row)

    raise KeyError(anchor or symbol)


def search_anchor_locations(
    runtime_root: str | Path,
    dataset_id: str,
    *,
    query: str | None,
    limit: int = 25,
) -> dict[str, Any]:
    """Search lexicon rows and source blocks for one anchor or an anchor group."""
    query_anchors = anchorize(query or "")
    if not query_anchors:
        raise ValueError("query produced no anchors")

    max_rows = _bounded_limit(limit)
    lexicon_by_anchor = {str(row.get("anchor", "")).casefold(): row for row in _lexicon_rows(runtime_root, dataset_id)}
    lexicon_matches = []
    for anchor in query_anchors:
        row = lexicon_by_anchor.get(anchor.casefold())
        lexicon_matches.append({
            "anchor": anchor,
            "known": row is not None,
            "symbol": row.get("symbol") if row else None,
            "observations": int(row.get("observations", 0)) if row else 0,
        })

    locations = []
    for block in _read_blocks(runtime_root, dataset_id):
        block_anchors = anchorize(str(block.get("text", "")))
        anchor_positions = _anchor_positions(block_anchors, query_anchors)
        if any(not anchor_positions.get(anchor) for anchor in query_anchors):
            continue
        sequence_positions = _sequence_positions(block_anchors, query_anchors)
        locations.append({
            "block_id": block.get("block_id"),
            "block_ordinal": block.get("block_ordinal"),
            "file_path": block.get("file_path"),
            "file_uri": _file_uri(block.get("file_path")),
            "line_start": block.get("line_start"),
            "line_end": block.get("line_end"),
            "citation_id": block.get("citation_id"),
            "marker": block.get("marker"),
            "text_hash": block.get("text_hash"),
            "matched_anchors": query_anchors,
            "positions": anchor_positions,
            "exact_sequence": bool(sequence_positions),
            "sequence_positions": sequence_positions,
            "snippet": _snippet(str(block.get("text", ""))),
        })

    locations.sort(key=lambda row: (not bool(row.get("exact_sequence")), str(row.get("file_path", "")), int(row.get("line_start") or 0)))
    return with_protected_notice({
        "schema": "awrag_ui_anchor_location_search@1",
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "query": query,
        "query_anchors": query_anchors,
        "search_kind": "single" if len(query_anchors) == 1 else "group",
        "limit": max_rows,
        "lexicon_matches": lexicon_matches,
        "total_locations": len(locations),
        "returned_count": min(len(locations), max_rows),
        "locations": locations[:max_rows],
        "source": "state/blocks.jsonl",
        "count_files_used": False,
        "read_only": True,
    })


def get_count_backend_status(runtime_root: str | Path, dataset_id: str) -> dict[str, Any]:
    """Return count backend display state from existing count artifacts."""
    status = get_status(runtime_root, dataset_id)
    return with_protected_notice({
        "schema": "awrag_ui_count_backend_status@1",
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "count_backend": status["count_backend"],
        "anchor_counts_path": status["anchor_counts_path"],
        "relation_counts_path": status["relation_counts_path"],
        "block_anchor_postings_path": status["block_anchor_postings_path"],
        "anchor_count": status["anchor_count"],
        "relation_count": status["relation_count"],
        "block_anchor_posting_count": status["block_anchor_posting_count"],
        "read_only": True,
    })


def get_symbol_system_status(runtime_root: str | Path, dataset_id: str) -> dict[str, Any]:
    """Return dataset symbol namespace state from existing metadata."""
    manifest = get_manifest(runtime_root, dataset_id)
    lexicon = _read_lexicon(runtime_root, dataset_id)
    return with_protected_notice({
        "schema": "awrag_ui_symbol_system_status@1",
        "dataset_id": safe_id(dataset_id),
        "scope": manifest.get("scope", "dataset_local"),
        "symbol_system": manifest.get("symbol_system", lexicon.get("symbol_system", SYMBOL_SYSTEM)),
        "symbol_bytes": manifest.get("symbol_bytes", lexicon.get("symbol_bytes", SYMBOL_BYTES)),
        "symbol_scope": manifest.get("symbol_scope", lexicon.get("symbol_scope", "dataset_local_demo_only")),
        "symbol_transferable": manifest.get("symbol_transferable", lexicon.get("symbol_transferable", False)),
        "lifetime_allowed": manifest.get("lifetime_allowed", lexicon.get("lifetime_allowed", False)),
        "anchorworks_lifetime_symbol_compatible": manifest.get(
            "anchorworks_lifetime_symbol_compatible",
            lexicon.get("anchorworks_lifetime_symbol_compatible", False),
        ),
        "read_only": True,
    })


def _anchor_detail_payload(runtime_root: str | Path, dataset_id: str, row: dict[str, Any]) -> dict[str, Any]:
    return with_protected_notice({
        "schema": "awrag_ui_anchor_detail@1",
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "anchor": row.get("anchor"),
        "symbol": row.get("symbol"),
        "symbol_system": row.get("symbol_system", SYMBOL_SYSTEM),
        "symbol_bytes": row.get("symbol_bytes", SYMBOL_BYTES),
        "observations": int(row.get("observations", 0)),
        "symbol_scope": row.get("symbol_scope", "dataset_local_demo_only"),
        "transferable": bool(row.get("transferable", False)),
        "lifetime_allowed": bool(row.get("lifetime_allowed", False)),
        "anchorworks_lifetime_symbol_compatible": bool(row.get("anchorworks_lifetime_symbol_compatible", False)),
        "promotion_allowed": bool(row.get("promotion_allowed", False)),
        "read_only": True,
    })


def _read_blocks(runtime_root: str | Path, dataset_id: str) -> list[dict[str, Any]]:
    paths = dataset_paths(runtime_root, dataset_id)
    if not paths.blocks_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in paths.blocks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _anchor_positions(block_anchors: list[str], query_anchors: list[str]) -> dict[str, list[int]]:
    wanted = {anchor: [] for anchor in query_anchors}
    wanted_keys = {anchor.casefold(): anchor for anchor in query_anchors}
    for position, anchor in enumerate(block_anchors):
        original = wanted_keys.get(anchor.casefold())
        if original is not None:
            wanted[original].append(position)
    return wanted


def _sequence_positions(block_anchors: list[str], query_anchors: list[str]) -> list[int]:
    if not query_anchors or len(query_anchors) > len(block_anchors):
        return []
    wanted = [anchor.casefold() for anchor in query_anchors]
    out: list[int] = []
    width = len(wanted)
    for start in range(0, len(block_anchors) - width + 1):
        if [anchor.casefold() for anchor in block_anchors[start:start + width]] == wanted:
            out.append(start)
    return out


def _file_uri(value: Any) -> str | None:
    if not value:
        return None
    try:
        return Path(str(value)).expanduser().resolve().as_uri()
    except Exception:
        return None


def _snippet(text: str, limit: int = 360) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[:limit - 1].rstrip() + "..."


def _read_lexicon(runtime_root: str | Path, dataset_id: str) -> dict[str, Any]:
    paths = dataset_paths(runtime_root, dataset_id)
    return _read_json(paths.lexicon_path)


def _lexicon_rows(runtime_root: str | Path, dataset_id: str) -> list[dict[str, Any]]:
    lexicon = _read_lexicon(runtime_root, dataset_id)
    rows = [dict(row) for row in lexicon.get("anchors", []) if isinstance(row, dict)]
    return sorted(rows, key=lambda row: str(row.get("anchor", "")))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bounded_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 1000:
        return 1000
    return int(limit)
