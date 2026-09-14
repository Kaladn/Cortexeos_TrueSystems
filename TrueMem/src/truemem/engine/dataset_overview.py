from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .anchors import symbol_hex
from .base import COUNT_BACKEND, dataset_paths, safe_id, unique_stamp, utc_now, with_protected_notice, write_json
from .determinism import file_receipt
from .job_publication import write_job_receipt
from .storage import (
    block_anchor_record_for_path,
    index_readiness,
    iter_anchor_records,
    iter_relation_records,
    read_blocks,
    read_symbol_to_anchor,
)


def dataset_overview(
    runtime_root: str | Path,
    dataset_id: str,
    out: str | Path,
    *,
    top_anchors: int = 25,
    top_relations: int = 50,
    trail_limit: int = 5,
) -> dict[str, Any]:
    """Write count-derived dataset overviews with source trails.

    This is not a reasoning engine and does not run retrieval. It reads the
    existing native count/index artifacts and links count field structure back
    to canonical blocks/citations for operator inspection.
    """
    paths = dataset_paths(runtime_root, dataset_id)
    readiness = index_readiness(runtime_root, dataset_id)
    if not readiness["query_allowed"]:
        raise RuntimeError(
            "INDEX_NOT_READY: dataset-overview requires built count, block, citation, and coordinate artifacts"
        )

    output_root = Path(out).expanduser().resolve()
    dataset_root = paths.root.resolve()
    if output_root == dataset_root or dataset_root in output_root.parents or output_root in dataset_root.parents:
        raise ValueError("overview outputs must be separate from the source dataset")
    receipts = output_root / "receipts"
    output_root.mkdir(parents=True, exist_ok=True)
    receipts.mkdir(parents=True, exist_ok=True)

    before = _core_artifact_receipts(paths)

    symbol_to_anchor = read_symbol_to_anchor(paths)
    blocks = read_blocks(paths)
    anchor_rows = _top_anchor_rows(paths, symbol_to_anchor, top_anchors)
    relation_rows = _top_relation_rows(paths, symbol_to_anchor, top_relations)
    relevant_symbols = _relevant_symbols(anchor_rows, relation_rows)
    block_positions = _read_relevant_postings(paths.block_anchor_path, relevant_symbols)

    anchor_overviews = [
        _anchor_overview(row, relation_rows, block_positions, blocks, trail_limit)
        for row in anchor_rows
    ]
    relationship_trails = [
        _relationship_trail(row, block_positions, blocks, trail_limit)
        for row in relation_rows
    ]

    _write_jsonl(output_root / "anchor_overviews.jsonl", anchor_overviews)
    _write_jsonl(output_root / "relationship_trails.jsonl", relationship_trails)

    summary = with_protected_notice({
        "schema": "truemem_dataset_overview_summary@2",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "runtime_root": str(Path(runtime_root).expanduser().resolve()),
        "dataset_root": str(paths.root),
        "count_backend": COUNT_BACKEND,
        "model_used": "none",
        "model_may_search": False,
        "query_ran": False,
        "intake_ran": False,
        "counts_written": False,
        "reasoning_engine_used": False,
        "overview_kind": "count_field_overview_with_source_trails",
        "core_law": "Counts are the brain. Blocks are witnesses. Speech is form. Evidence remains authority.",
        "readiness": readiness,
        "parameters": {
            "top_anchors": int(top_anchors),
            "top_relations": int(top_relations),
            "trail_limit": int(trail_limit),
        },
        "anchor_overview_count": len(anchor_overviews),
        "relationship_trail_count": len(relationship_trails),
        "top_anchors": anchor_overviews,
        "top_relationships": relationship_trails,
        "outputs": {
            "overview_summary_json": str(output_root / "overview_summary.json"),
            "overview_summary_md": str(output_root / "overview_summary.md"),
            "anchor_overviews": str(output_root / "anchor_overviews.jsonl"),
            "relationship_trails": str(output_root / "relationship_trails.jsonl"),
            "run_receipt": str(receipts / "run_receipt.json"),
        },
    })
    write_json(output_root / "overview_summary.json", summary)
    (output_root / "overview_summary.md").write_text(_summary_markdown(summary), encoding="utf-8")

    after = _core_artifact_receipts(paths)
    mutation_receipt = with_protected_notice({
        "schema": "truemem_dataset_overview_no_mutation_receipt@1",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "checked_artifacts_before": before,
        "checked_artifacts_after": after,
        "mutated_artifacts": _mutated_artifacts(before, after),
        "dataset_artifacts_mutated": bool(_mutated_artifacts(before, after)),
        "production_counts_mutated": False,
        "lifetime_memory_mutated": False,
        "query_ran": False,
        "intake_ran": False,
    })

    run_receipt = with_protected_notice({
        "schema": "truemem_dataset_overview_run_receipt@2",
        "created_at": utc_now(),
        "run_id": unique_stamp(),
        "dataset_id": safe_id(dataset_id),
        "runtime_root": str(Path(runtime_root).expanduser().resolve()),
        "output_root": str(output_root),
        "count_backend": COUNT_BACKEND,
        "model_used": "none",
        "query_ran": False,
        "intake_ran": False,
        "counts_written": False,
        "anchor_overview_count": len(anchor_overviews),
        "relationship_trail_count": len(relationship_trails),
        "no_mutation_receipt": mutation_receipt,
    })
    write_job_receipt(receipts / "run_receipt.json", run_receipt)

    summary["outputs"]["run_receipt"] = str(receipts / "run_receipt.json")
    summary["output_root"] = str(output_root)
    return summary


def _top_anchor_rows(paths: Any, symbol_to_anchor: dict[str, str], limit: int) -> list[dict[str, Any]]:
    rows = [
        {
            "symbol": symbol_hex(symbol),
            "anchor": symbol_to_anchor.get(symbol_hex(symbol), "<unknown>"),
            "observations": int(observations),
        }
        for symbol, observations in iter_anchor_records(paths)
    ]
    rows.sort(key=lambda row: (-int(row["observations"]), str(row["anchor"]), str(row["symbol"])))
    return rows[: max(0, int(limit))]


def _top_relation_rows(paths: Any, symbol_to_anchor: dict[str, str], limit: int) -> list[dict[str, Any]]:
    rows = [
        {
            "center_symbol": symbol_hex(center),
            "center_anchor": symbol_to_anchor.get(symbol_hex(center), "<unknown>"),
            "neighbor_symbol": symbol_hex(neighbor),
            "neighbor_anchor": symbol_to_anchor.get(symbol_hex(neighbor), "<unknown>"),
            "offset": int(offset),
            "observations": int(observations),
        }
        for center, neighbor, offset, observations in iter_relation_records(paths)
    ]
    rows.sort(key=lambda row: (-int(row["observations"]), str(row["center_anchor"]), int(row["offset"]), str(row["neighbor_anchor"])))
    return rows[: max(0, int(limit))]


def _relevant_symbols(anchor_rows: list[dict[str, Any]], relation_rows: list[dict[str, Any]]) -> set[str]:
    out = {str(row["symbol"]) for row in anchor_rows}
    for row in relation_rows:
        out.add(str(row["center_symbol"]))
        out.add(str(row["neighbor_symbol"]))
    return out


def _read_relevant_postings(block_anchor_path: Path, symbols: set[str]) -> dict[int, dict[str, list[int]]]:
    positions: dict[int, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    if not block_anchor_path.exists() or not symbols:
        return positions
    record = block_anchor_record_for_path(block_anchor_path)
    with block_anchor_path.open("rb") as handle:
        while chunk := handle.read(record.size):
            if len(chunk) != record.size:
                raise RuntimeError("TRUNCATED_BLOCK_ANCHOR_POSTING_RECORD")
            symbol, block_ordinal, position = record.unpack(chunk)
            symbol_id = symbol_hex(symbol)
            if symbol_id in symbols:
                positions[int(block_ordinal)][symbol_id].append(int(position))
    return positions


def _anchor_overview(
    row: dict[str, Any],
    relation_rows: list[dict[str, Any]],
    block_positions: dict[int, dict[str, list[int]]],
    blocks: dict[int, dict[str, Any]],
    trail_limit: int,
) -> dict[str, Any]:
    symbol = str(row["symbol"])
    top_neighbors = [
        {
            "neighbor_anchor": relation["neighbor_anchor"],
            "neighbor_symbol": relation["neighbor_symbol"],
            "offset": relation["offset"],
            "observations": relation["observations"],
        }
        for relation in relation_rows
        if relation["center_symbol"] == symbol
    ][:10]
    trails = []
    for block_ordinal in sorted(block_positions):
        if len(trails) >= trail_limit:
            break
        positions = block_positions[block_ordinal].get(symbol, [])
        if not positions:
            continue
        block = blocks.get(block_ordinal)
        if not block:
            continue
        trails.append(_block_trail(block, positions[0]))
    return with_protected_notice({
        "schema": "truemem_anchor_overview@1",
        **row,
        "top_neighbors": top_neighbors,
        "source_trails": trails,
    })


def _relationship_trail(
    row: dict[str, Any],
    block_positions: dict[int, dict[str, list[int]]],
    blocks: dict[int, dict[str, Any]],
    trail_limit: int,
) -> dict[str, Any]:
    center_symbol = str(row["center_symbol"])
    neighbor_symbol = str(row["neighbor_symbol"])
    offset = int(row["offset"])
    trails = []
    for block_ordinal in sorted(block_positions):
        if len(trails) >= trail_limit:
            break
        positions = block_positions[block_ordinal]
        center_positions = positions.get(center_symbol, [])
        neighbor_positions = set(positions.get(neighbor_symbol, []))
        for center_position in center_positions:
            if center_position + offset not in neighbor_positions:
                continue
            block = blocks.get(block_ordinal)
            if not block:
                continue
            trail = _block_trail(block, center_position)
            trail["neighbor_position"] = center_position + offset
            trails.append(trail)
            break
    return with_protected_notice({
        "schema": "truemem_relationship_trail@1",
        **row,
        "source_trails": trails,
    })


def _block_trail(block: dict[str, Any], position: int) -> dict[str, Any]:
    return {
        "block_ordinal": int(block["block_ordinal"]),
        "block_id": block["block_id"],
        "citation": block["marker"],
        "citation_id": block["citation_id"],
        "file_path": block["file_path"],
        "line_start": int(block["line_start"]),
        "line_end": int(block["line_end"]),
        "position": int(position),
        "snippet": _snippet(str(block.get("text", ""))),
    }


def _snippet(text: str, *, limit: int = 420) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _core_artifact_receipts(paths: Any) -> dict[str, dict[str, Any]]:
    files = {
        "dataset_manifest": paths.manifest_path,
        "dataset_lexicon": paths.lexicon_path,
        "blocks": paths.blocks_path,
        "chat_metadata_index": paths.chat_metadata_path,
        "anchor_counts": paths.anchor_counts_path,
        "relation_counts": paths.relation_counts_path,
        "block_anchor_postings": paths.block_anchor_path,
        "citations": paths.citations / "citations.jsonl",
        "coordinate_index": paths.coordinates / "coordinate_index.jsonl",
    }
    return {name: file_receipt(path) for name, path in files.items()}


def _mutated_artifacts(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> list[str]:
    mutated = []
    for name in sorted(before):
        left = before.get(name, {})
        right = after.get(name, {})
        if left.get("sha256") != right.get("sha256") or left.get("size_bytes") != right.get("size_bytes"):
            mutated.append(name)
    return mutated


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# TrueMem Dataset Overview",
        "",
        "This is a count-derived overview, not model summary.",
        "",
        f"- dataset: {summary['dataset_id']}",
        f"- count backend: {summary['count_backend']}",
        f"- model used: {summary['model_used']}",
        f"- query ran: {str(summary['query_ran']).lower()}",
        f"- intake ran: {str(summary['intake_ran']).lower()}",
        "",
        "## Top Anchors",
    ]
    for row in summary["top_anchors"]:
        lines.append(f"- {row['anchor']} ({row['symbol']}): {row['observations']} observations")
        for trail in row.get("source_trails", [])[:1]:
            lines.append(
                f"  source: {trail['citation']} {trail['file_path']} lines {trail['line_start']}-{trail['line_end']}"
            )
    lines.extend(["", "## Top Relationships"])
    for row in summary["top_relationships"]:
        lines.append(
            f"- {row['center_anchor']} -> {row['neighbor_anchor']} offset {row['offset']}: {row['observations']} observations"
        )
        for trail in row.get("source_trails", [])[:1]:
            lines.append(
                f"  source: {trail['citation']} {trail['file_path']} lines {trail['line_start']}-{trail['line_end']}"
            )
    lines.extend([
        "",
        "## Rule",
        "",
        "Counts are the brain. Blocks are witnesses. Speech is form. Evidence remains authority.",
        "",
    ])
    return "\n".join(lines)
