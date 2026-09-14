from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .anchors import symbol_for
from .job_publication import write_job_receipt
from .base import COUNT_BACKEND, SYMBOL_BYTES, SYMBOL_SYSTEM, safe_id, utc_now, with_protected_notice, write_json

REQUIRED_RESONANCE_FILES = (
    "context_map.json",
    "context_clouds.json",
    "analysis_results.json",
    "summary_report.md",
)

OPTIONAL_RESONANCE_FILES = (
    "standalone_context_parser.py",
    "process_story_standalone.py",
    "process_story.py",
    "plots/cloud_size_distribution.png",
    "plots/resonance_heatmap.png",
)


def adapt_resonance_sample(
    source_dir: str | Path,
    out_dir: str | Path,
    *,
    dataset_id: str = "resonance_sample",
    copy_source: bool = False,
    symbolize: bool = False,
    top_n: int = 25,
) -> dict[str, Any]:
    """Adapt a standalone 6-1-6 resonance sample into TrueMem review artifacts.

    This is intentionally not an TrueMem intake path. It reads existing resonance
    artifacts, writes compact receipts/reports, and leaves symbol/binary
    promotion as a later explicit decision.
    """
    source = Path(source_dir).expanduser().resolve()
    out = Path(out_dir).expanduser().resolve()
    if out == source or source in out.parents or out in source.parents:
        raise ValueError("resonance outputs must be separate from the source")
    if not source.exists() or not source.is_dir():
        raise FileNotFoundError(f"resonance source folder not found: {source}")

    missing = [name for name in REQUIRED_RESONANCE_FILES if not (source / name).exists()]
    if missing:
        raise FileNotFoundError(f"resonance source missing required files: {', '.join(missing)}")

    out.mkdir(parents=True, exist_ok=True)
    receipts = out / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)

    before_hashes = _source_file_receipts(source)
    context_map = _read_json(source / "context_map.json")
    context_clouds = _read_json(source / "context_clouds.json")
    analysis_results = _read_json(source / "analysis_results.json")

    anchor_records = _build_anchor_records(context_map, context_clouds, top_n=top_n)
    anchor_records_path = out / "resonance_anchor_records.jsonl"
    with anchor_records_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in anchor_records:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    summary = _build_summary(
        dataset_id=safe_id(dataset_id),
        source=source,
        context_map=context_map,
        context_clouds=context_clouds,
        analysis_results=analysis_results,
        anchor_records=anchor_records,
        top_n=top_n,
        symbolize=symbolize,
    )
    symbol_outputs: dict[str, Any] = {}
    if symbolize:
        symbol_outputs = _write_symbol_artifacts(
            out,
            dataset_id=safe_id(dataset_id),
            anchor_records=anchor_records,
            receipts_dir=receipts,
        )
        summary["symbol_plan"].update(symbol_outputs["symbol_plan"])
        summary["binary_plan"].update(symbol_outputs["binary_plan"])
    summary_json_path = out / "resonance_adapter_summary.json"
    summary_md_path = out / "resonance_adapter_summary.md"
    write_json(summary_json_path, summary)
    summary_md_path.write_text(_summary_markdown(summary), encoding="utf-8")

    copied_files: list[str] = []
    if copy_source:
        copied_files = _copy_review_artifacts(source, out / "source_copy")

    after_hashes = _source_file_receipts(source)
    no_mutation = {
        "schema": "truemem_resonance_no_mutation_receipt@1",
        "created_at": utc_now(),
        "source_dir": str(source),
        "source_file_count_before": len(before_hashes),
        "source_file_count_after": len(after_hashes),
        "source_hashes_unchanged": before_hashes == after_hashes,
        "source_mutated": before_hashes != after_hashes,
    }
    source_receipt = {
        "schema": "truemem_resonance_source_receipt@1",
        "created_at": utc_now(),
        "source_dir": str(source),
        "files": before_hashes,
        "cache_residue_present": any(row["classification"] == "cache_residue" for row in before_hashes),
    }
    run_receipt = {
        "schema": "truemem_resonance_adapter_run_receipt@2",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "source_dir": str(source),
        "out_dir": str(out),
        "copy_source": bool(copy_source),
        "copied_files": copied_files,
        "adapter_only": True,
        "aw_intake_ran": False,
        "counts_written": False,
        "lexicon_written": bool(symbolize),
        "symbols_assigned": bool(symbolize),
        "binaries_written": False,
        "whole_dataset_records_written": len(anchor_records),
        "outputs": {
            "anchor_records": str(anchor_records_path),
            "summary_json": str(summary_json_path),
            "summary_md": str(summary_md_path),
            "run_receipt": str(receipts / "run_receipt.json"),
            **symbol_outputs.get("outputs", {}),
        },
    }

    run_receipt["source_receipt"] = source_receipt
    run_receipt["no_mutation_receipt"] = no_mutation
    run_receipt["source_files_after"] = after_hashes
    write_job_receipt(receipts / "run_receipt.json", run_receipt)

    return with_protected_notice({
        "schema": "truemem_resonance_adapter_result@2",
        "dataset_id": safe_id(dataset_id),
        "source_dir": str(source),
        "out_dir": str(out),
        "whole_dataset_records_written": len(anchor_records),
        "context_anchor_count": summary["context_anchor_count"],
        "cloud_anchor_count": summary["cloud_anchor_count"],
        "cloud_membership_count": summary["cloud_membership_count"],
        "symbols_assigned": bool(symbolize),
        "symbol_plan": summary["symbol_plan"],
        "binary_plan": summary["binary_plan"],
        "outputs": run_receipt["outputs"],
        "source_mutated": no_mutation["source_mutated"],
    })


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_anchor_records(
    context_map: dict[str, Any],
    context_clouds: dict[str, Any],
    *,
    top_n: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    all_anchors = sorted(set(context_map) | set(context_clouds))
    for anchor in all_anchors:
        positions = context_map.get(anchor) or {}
        cloud = context_clouds.get(anchor) or {}
        strengths = cloud.get("strengths") or {}
        top_strengths = sorted(
            [{"anchor": str(name), "resonance": float(value)} for name, value in strengths.items()],
            key=lambda row: (-row["resonance"], row["anchor"]),
        )[:top_n]
        records.append({
            "schema": "truemem_resonance_anchor_record@1",
            "anchor": str(anchor),
            "symbol_status": "not_assigned",
            "context_slot_count": len(positions),
            "context_member_count": sum(len(words or []) for words in positions.values()),
            "context_positions": {str(pos): list(words or []) for pos, words in sorted(positions.items(), key=lambda item: int(item[0]))},
            "cloud_size": len(cloud.get("members") or []),
            "cloud_members": list(cloud.get("members") or []),
            "top_resonance_strengths": top_strengths,
        })
    return records


def _build_summary(
    *,
    dataset_id: str,
    source: Path,
    context_map: dict[str, Any],
    context_clouds: dict[str, Any],
    analysis_results: dict[str, Any],
    anchor_records: list[dict[str, Any]],
    top_n: int,
    symbolize: bool,
) -> dict[str, Any]:
    context_anchors = set(context_map)
    cloud_anchors = set(context_clouds)
    top_clouds = sorted(
        [{"anchor": row["anchor"], "cloud_size": int(row["cloud_size"])} for row in anchor_records],
        key=lambda row: (-row["cloud_size"], row["anchor"]),
    )[:top_n]
    top_pairs = _top_resonance_pairs(context_clouds, top_n=top_n)
    context_slot_count = sum(int(row["context_slot_count"]) for row in anchor_records)
    context_member_count = sum(int(row["context_member_count"]) for row in anchor_records)
    cloud_membership_count = sum(int(row["cloud_size"]) for row in anchor_records)
    focus_words = sorted(set((analysis_results.get("context_windows") or {}).keys()))
    return {
        "schema": "truemem_resonance_adapter_summary@1",
        "created_at": utc_now(),
        "dataset_id": dataset_id,
        "source_dir": str(source),
        "adapter_role": "read_only_resonance_sample_bridge",
        "context_anchor_count": len(context_anchors),
        "cloud_anchor_count": len(cloud_anchors),
        "shared_anchor_count": len(context_anchors & cloud_anchors),
        "context_without_cloud_count": len(context_anchors - cloud_anchors),
        "cloud_without_context_count": len(cloud_anchors - context_anchors),
        "context_position_slot_count": context_slot_count,
        "context_member_edge_count": context_member_count,
        "cloud_membership_count": cloud_membership_count,
        "focus_word_count": len(focus_words),
        "focus_words": focus_words,
        "top_clouds": top_clouds,
        "top_resonance_pairs": top_pairs,
        "symbol_plan": {
            "symbols_assigned_now": bool(symbolize),
            "symbol_system": SYMBOL_SYSTEM,
            "symbol_bytes": SYMBOL_BYTES,
            "symbol_assignment_method": "current_truemem_symbol_for(anchor)",
            "decision": "symbolized_adapter_artifacts_written" if symbolize else "defer_until_operator_promotes_adapter_output",
        },
        "binary_plan": {
            "binaries_written_now": False,
            "count_backend": COUNT_BACKEND,
            "decision": "blocked_until_raw_position_observation_counts_exist" if symbolize else "defer_until_symbolized_adapter_output_is_accepted",
            "reason": "The saved resonance JSON preserves top-k positional layout and resonance strengths, not raw observation counts per center/offset/neighbor.",
        },
    }


def _top_resonance_pairs(context_clouds: dict[str, Any], *, top_n: int) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for source, cloud in context_clouds.items():
        for target, value in (cloud.get("strengths") or {}).items():
            pairs.append({"source": str(source), "target": str(target), "resonance": float(value)})
    pairs.sort(key=lambda row: (-row["resonance"], row["source"], row["target"]))
    return pairs[:top_n]


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Resonance Sample Adapter Summary",
        "",
        f"- Dataset ID: `{summary['dataset_id']}`",
        f"- Source: `{summary['source_dir']}`",
        f"- Adapter role: `{summary['adapter_role']}`",
        f"- Context anchors: {summary['context_anchor_count']}",
        f"- Cloud anchors: {summary['cloud_anchor_count']}",
        f"- Shared anchors: {summary['shared_anchor_count']}",
        f"- Context position slots: {summary['context_position_slot_count']}",
        f"- Context member edges: {summary['context_member_edge_count']}",
        f"- Cloud memberships: {summary['cloud_membership_count']}",
        f"- Focus words: {summary['focus_word_count']}",
        "",
        "## Top Clouds",
        "",
    ]
    for row in summary["top_clouds"][:10]:
        lines.append(f"- `{row['anchor']}`: {row['cloud_size']}")
    lines.extend(["", "## Top Resonance Pairs", ""])
    for row in summary["top_resonance_pairs"][:10]:
        lines.append(f"- `{row['source']}` -> `{row['target']}`: {row['resonance']:.4f}")
    lines.extend([
        "",
        "## Symbols",
        "",
        f"Symbols assigned now: `{summary['symbol_plan']['symbols_assigned_now']}`",
        f"Symbol system: `{summary['symbol_plan']['symbol_system']}`",
        f"Symbol method: `{summary['symbol_plan']['symbol_assignment_method']}`",
        "",
        "## Binary Storage",
        "",
        f"Binaries written now: `{summary['binary_plan']['binaries_written_now']}`",
        f"Decision: `{summary['binary_plan']['decision']}`",
        "",
        summary["binary_plan"]["reason"],
    ])
    return "\n".join(lines) + "\n"


def _write_symbol_artifacts(
    out: Path,
    *,
    dataset_id: str,
    anchor_records: list[dict[str, Any]],
    receipts_dir: Path,
) -> dict[str, Any]:
    symbol_dir = out / "symbolized"
    symbol_dir.mkdir(parents=True, exist_ok=True)

    anchors = _collect_all_display_anchors(anchor_records)
    lexicon_path = symbol_dir / "dataset_symbol_lexicon.json"
    symbol_records_path = symbol_dir / "resonance_symbol_records.jsonl"
    context_edges_path = symbol_dir / "resonance_context_edges.jsonl"
    cloud_edges_path = symbol_dir / "resonance_cloud_edges.jsonl"
    symbol_receipt_path = receipts_dir / "symbol_receipt.json"
    binary_readiness_path = receipts_dir / "binary_count_readiness_receipt.json"

    symbol_map = {anchor: symbol_for(anchor) for anchor in anchors}
    write_json(lexicon_path, {
        "schema": "truemem_resonance_symbol_lexicon@1",
        "created_at": utc_now(),
        "dataset_id": dataset_id,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "symbol_scope": "adapter_dataset_local",
        "active_aw_query_lexicon": False,
        "anchor_count": len(anchors),
        "anchors": [
            {
                "anchor": anchor,
                "symbol": symbol_map[anchor],
                "scope": "adapter_dataset_local",
                "active_aw_query_symbol": False,
            }
            for anchor in anchors
        ],
    })

    context_edge_count = 0
    cloud_edge_count = 0
    with symbol_records_path.open("w", encoding="utf-8", newline="\n") as symbol_handle, \
            context_edges_path.open("w", encoding="utf-8", newline="\n") as context_handle, \
            cloud_edges_path.open("w", encoding="utf-8", newline="\n") as cloud_handle:
        for record in anchor_records:
            center = str(record["anchor"])
            symbolized_positions: dict[str, list[dict[str, Any]]] = {}
            for offset, neighbors in (record.get("context_positions") or {}).items():
                rows: list[dict[str, Any]] = []
                for rank, neighbor in enumerate(neighbors or [], start=1):
                    neighbor_anchor = str(neighbor)
                    edge = {
                        "schema": "truemem_resonance_context_edge@1",
                        "center_anchor": center,
                        "center_symbol": symbol_map[center],
                        "neighbor_anchor": neighbor_anchor,
                        "neighbor_symbol": symbol_map[neighbor_anchor],
                        "offset": int(offset),
                        "position_rank": int(rank),
                        "raw_observation_count_available": False,
                        "raw_observation_count": None,
                    }
                    context_handle.write(json.dumps(edge, ensure_ascii=True) + "\n")
                    context_edge_count += 1
                    rows.append({
                        "anchor": neighbor_anchor,
                        "symbol": symbol_map[neighbor_anchor],
                        "position_rank": int(rank),
                    })
                symbolized_positions[str(offset)] = rows

            symbolized_cloud_members = []
            for member in record.get("cloud_members") or []:
                member_anchor = str(member)
                symbolized_cloud_members.append({"anchor": member_anchor, "symbol": symbol_map[member_anchor]})

            for row in record.get("top_resonance_strengths") or []:
                target = str(row["anchor"])
                edge = {
                    "schema": "truemem_resonance_cloud_edge@1",
                    "source_anchor": center,
                    "source_symbol": symbol_map[center],
                    "target_anchor": target,
                    "target_symbol": symbol_map[target],
                    "resonance": float(row["resonance"]),
                    "resonance_is_count": False,
                }
                cloud_handle.write(json.dumps(edge, ensure_ascii=True) + "\n")
                cloud_edge_count += 1

            symbol_handle.write(json.dumps({
                "schema": "truemem_resonance_symbol_record@1",
                "anchor": center,
                "symbol": symbol_map[center],
                "context_positions": symbolized_positions,
                "cloud_members": symbolized_cloud_members,
                "raw_observation_counts_available": False,
            }, ensure_ascii=True) + "\n")

    symbol_receipt = {
        "schema": "truemem_resonance_symbol_receipt@1",
        "created_at": utc_now(),
        "dataset_id": dataset_id,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "anchor_count": len(anchors),
        "symbol_collision_count": len(anchors) - len(set(symbol_map.values())),
        "symbolized_records": len(anchor_records),
        "context_edges": context_edge_count,
        "cloud_edges": cloud_edge_count,
        "active_aw_query_lexicon": False,
        "outputs": {
            "lexicon": str(lexicon_path),
            "symbol_records": str(symbol_records_path),
            "context_edges": str(context_edges_path),
            "cloud_edges": str(cloud_edges_path),
        },
    }
    binary_readiness = {
        "schema": "truemem_resonance_binary_count_readiness@1",
        "created_at": utc_now(),
        "dataset_id": dataset_id,
        "native_count_backend": COUNT_BACKEND,
        "native_awbin_counts_written": False,
        "blocked": True,
        "reason": "The saved resonance sample contains top-k positional layout and resonance strengths, not raw observation counts per center/offset/neighbor.",
        "required_inputs_for_true_counts": [
            "original source text, or",
            "raw count table keyed by center_anchor, neighbor_anchor, offset, observation_count",
        ],
        "current_aw_count_paths_preserved": True,
        "do_not_fake_counts_from_rank_or_resonance": True,
    }
    write_json(symbol_receipt_path, symbol_receipt)
    write_json(binary_readiness_path, binary_readiness)
    return {
        "outputs": {
            "symbol_lexicon": str(lexicon_path),
            "symbol_records": str(symbol_records_path),
            "symbol_context_edges": str(context_edges_path),
            "symbol_cloud_edges": str(cloud_edges_path),
            "symbol_receipt": str(symbol_receipt_path),
            "binary_count_readiness_receipt": str(binary_readiness_path),
        },
        "symbol_plan": {
            "symbols_assigned_now": True,
            "symbol_anchor_count": len(anchors),
            "symbol_collision_count": symbol_receipt["symbol_collision_count"],
            "symbol_lexicon_path": str(lexicon_path),
            "symbol_records_path": str(symbol_records_path),
        },
        "binary_plan": {
            "binaries_written_now": False,
            "binary_count_readiness_receipt": str(binary_readiness_path),
            "decision": "blocked_until_raw_position_observation_counts_exist",
        },
    }


def _collect_all_display_anchors(anchor_records: list[dict[str, Any]]) -> list[str]:
    anchors: set[str] = set()
    for record in anchor_records:
        anchors.add(str(record["anchor"]))
        for neighbors in (record.get("context_positions") or {}).values():
            anchors.update(str(neighbor) for neighbor in (neighbors or []))
        anchors.update(str(member) for member in (record.get("cloud_members") or []))
        anchors.update(str(row["anchor"]) for row in (record.get("top_resonance_strengths") or []))
    return sorted(anchor for anchor in anchors if anchor)


def _source_file_receipts(source: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted([item for item in source.rglob("*") if item.is_file()]):
        rel = path.relative_to(source).as_posix()
        rows.append({
            "relative_path": rel,
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
            "classification": _classify_source_file(rel),
        })
    return rows


def _classify_source_file(relative_path: str) -> str:
    lowered = relative_path.casefold()
    if "__pycache__/" in lowered or lowered.endswith(".pyc"):
        return "cache_residue"
    if lowered.endswith(".json"):
        return "resonance_artifact"
    if lowered.endswith(".md"):
        return "human_report"
    if lowered.endswith(".py"):
        return "sample_code"
    if lowered.endswith(".png"):
        return "plot"
    return "other"


def _copy_review_artifacts(source: Path, destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for relative in [*REQUIRED_RESONANCE_FILES, *OPTIONAL_RESONANCE_FILES]:
        src = source / relative
        if not src.exists() or not src.is_file():
            continue
        dst = destination / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(dst))
    return copied


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()
