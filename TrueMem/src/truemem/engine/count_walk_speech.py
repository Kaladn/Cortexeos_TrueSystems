from __future__ import annotations

from pathlib import Path
from typing import Any

from .anchors import anchorize, symbol_hex
from .base import COUNT_BACKEND, dataset_paths, safe_id, sha1_text, unique_stamp, utc_now, with_protected_notice, write_json
from .determinism import file_receipt
from .querying import query
from .storage import BLOCK_ANCHOR_RECORD, iter_relation_records, read_blocks, read_symbol_to_anchor


def count_walk_speech(
    runtime_root: str | Path,
    dataset_id: str,
    question: str,
    out: str | Path,
    *,
    starter: str | None = None,
    top_k: int = 5,
    max_steps: int = 50,
    branch_k: int = 5,
) -> dict[str, Any]:
    """Walk count-selected local block spine into a rough speech draft.

    Query/count ranking selects the evidence block. Block postings provide the
    local spine. Relation counts choose among local continuation candidates.
    This is a report/tool lane, not a reasoning engine or final answerer.
    """
    paths = dataset_paths(runtime_root, dataset_id)
    output_root = Path(out).expanduser().resolve()
    trace_dir = output_root / "evidence_trace"
    pretty_dir = output_root / "pretty_answer"
    receipts_dir = output_root / "receipts"
    for path in (trace_dir, pretty_dir, receipts_dir):
        path.mkdir(parents=True, exist_ok=True)

    before = _core_artifact_receipts(paths)
    packet = query(runtime_root, dataset_id, question, top_k=top_k)
    locations = list((packet.get("answer_packet") or {}).get("locations") or [])
    selected_location = locations[0] if locations else None

    if selected_location is None:
        trace = _empty_trace(
            runtime_root=runtime_root,
            dataset_id=dataset_id,
            question=question,
            starter=starter,
            packet=packet,
            reason="no_qualified_locations",
        )
    else:
        trace = _walk_selected_location(
            runtime_root=runtime_root,
            dataset_id=dataset_id,
            question=question,
            starter=starter,
            packet=packet,
            selected_location=selected_location,
            max_steps=max_steps,
            branch_k=branch_k,
        )

    trace_path = trace_dir / f"count_walk_trace_{sha1_text(question)[:8]}.json"
    pretty_path = pretty_dir / f"count_walk_speech_{sha1_text(question)[:8]}.md"
    write_json(trace_path, trace)
    pretty = _pretty_answer(trace, trace_path)
    pretty_path.write_text(pretty, encoding="utf-8")

    after = _core_artifact_receipts(paths)
    mutated = _mutated_artifacts(before, after)
    no_mutation = with_protected_notice({
        "schema": "truemem_count_walk_speech_no_mutation_receipt@1",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "dataset_artifacts_mutated": bool(mutated),
        "mutated_artifacts": mutated,
        "checked_artifacts_before": before,
        "checked_artifacts_after": after,
        "query_output_written": packet.get("output_path"),
        "production_counts_mutated": False,
        "lifetime_memory_mutated": False,
        "model_used": "none",
    })
    write_json(receipts_dir / "no_mutation_receipt.json", no_mutation)

    run_receipt = with_protected_notice({
        "schema": "truemem_count_walk_speech_run_receipt@1",
        "created_at": utc_now(),
        "run_id": unique_stamp(),
        "dataset_id": safe_id(dataset_id),
        "runtime_root": str(Path(runtime_root).expanduser().resolve()),
        "question": question,
        "starter": starter,
        "top_k": int(top_k),
        "branch_k": int(branch_k),
        "max_steps": int(max_steps),
        "query_ran": True,
        "retrieval_changed": False,
        "rank_changed": False,
        "intake_ran": False,
        "model_used": "none",
        "model_may_search": False,
        "trace_path": str(trace_path),
        "pretty_answer_path": str(pretty_path),
        "no_mutation_receipt": str(receipts_dir / "no_mutation_receipt.json"),
    })
    write_json(receipts_dir / "run_receipt.json", run_receipt)

    return with_protected_notice({
        "schema": "truemem_count_walk_speech_result@1",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "question": question,
        "starter": starter,
        "output_root": str(output_root),
        "evidence_trace_path": str(trace_path),
        "pretty_answer_path": str(pretty_path),
        "run_receipt_path": str(receipts_dir / "run_receipt.json"),
        "no_mutation_receipt_path": str(receipts_dir / "no_mutation_receipt.json"),
        "walk_status": trace["walk_status"],
        "walked_anchor_count": len(trace.get("walked_anchors") or []),
        "model_used": "none",
        "model_may_search": False,
    })


def _walk_selected_location(
    *,
    runtime_root: str | Path,
    dataset_id: str,
    question: str,
    starter: str | None,
    packet: dict[str, Any],
    selected_location: dict[str, Any],
    max_steps: int,
    branch_k: int,
) -> dict[str, Any]:
    paths = dataset_paths(runtime_root, dataset_id)
    blocks = read_blocks(paths)
    block = _find_block_for_location(blocks, selected_location)
    if block is None:
        return _empty_trace(
            runtime_root=runtime_root,
            dataset_id=dataset_id,
            question=question,
            starter=starter,
            packet=packet,
            reason="selected_location_not_found_in_blocks",
        )

    symbol_to_anchor = read_symbol_to_anchor(paths)
    block_spine = _block_spine(paths.block_anchor_path, int(block["block_ordinal"]), symbol_to_anchor)
    relation_counts = _relation_count_lookup(paths)
    start = _start_position(block_spine, question=question, starter=starter)
    if start["status"] != "ready":
        return with_protected_notice({
            "schema": "truemem_count_walk_speech_trace@1",
            "created_at": utc_now(),
            "dataset_id": safe_id(dataset_id),
            "question": question,
            "starter": starter,
            "count_backend": COUNT_BACKEND,
            "walk_status": start["status"],
            "stop_reason": start["reason"],
            "model_used": "none",
            "model_may_search": False,
            "query_output_path": packet.get("output_path"),
            "selected_location": _location_receipt(selected_location, block),
            "local_spine": block_spine,
            "walked_anchors": [],
            "steps": [],
            "speech_policy": _speech_policy(),
        })

    current_index = int(start["position"])
    walked = [block_spine[current_index]["anchor"]]
    steps: list[dict[str, Any]] = []
    stop_reason = "max_steps_reached"

    for _ in range(max(0, int(max_steps) - 1)):
        candidates = _local_branch_candidates(
            block_spine,
            current_index,
            relation_counts,
            branch_k=branch_k,
        )
        if not candidates:
            stop_reason = "no_count_linked_local_candidates"
            break
        chosen = candidates[0]
        steps.append({
            "from_position": current_index,
            "from_anchor": block_spine[current_index]["anchor"],
            "branch_candidates": candidates,
            "chosen": chosen,
            "chosen_by": "highest_native_relation_count_inside_count_selected_local_spine",
        })
        current_index = int(chosen["position"])
        walked.append(str(chosen["anchor"]))
        if current_index >= len(block_spine) - 1:
            stop_reason = "end_of_local_spine"
            break

    return with_protected_notice({
        "schema": "truemem_count_walk_speech_trace@1",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "question": question,
        "starter": starter,
        "count_backend": COUNT_BACKEND,
        "walk_status": "walk_complete",
        "stop_reason": stop_reason,
        "model_used": "none",
        "model_may_search": False,
        "query_output_path": packet.get("output_path"),
        "selected_location": _location_receipt(selected_location, block),
        "start": start,
        "local_spine": block_spine,
        "walked_anchors": walked,
        "rough_count_walk_text": " ".join(walked),
        "steps": steps,
        "speech_policy": _speech_policy(),
    })


def _empty_trace(
    *,
    runtime_root: str | Path,
    dataset_id: str,
    question: str,
    starter: str | None,
    packet: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return with_protected_notice({
        "schema": "truemem_count_walk_speech_trace@1",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "runtime_root": str(Path(runtime_root).expanduser().resolve()),
        "question": question,
        "starter": starter,
        "count_backend": COUNT_BACKEND,
        "walk_status": "not_walked",
        "stop_reason": reason,
        "model_used": "none",
        "model_may_search": False,
        "query_output_path": packet.get("output_path"),
        "selected_location": None,
        "local_spine": [],
        "walked_anchors": [],
        "steps": [],
        "speech_policy": _speech_policy(),
    })


def _find_block_for_location(blocks: dict[int, dict[str, Any]], location: dict[str, Any]) -> dict[str, Any] | None:
    citation = str(location.get("citation") or "").strip("[]")
    file_path = str(location.get("file_path") or "")
    line_start = int(location.get("line_start") or -1)
    line_end = int(location.get("line_end") or -1)
    for block in blocks.values():
        if str(block.get("citation_id")) == citation:
            return block
    for block in blocks.values():
        if (
            str(block.get("file_path")) == file_path
            and int(block.get("line_start") or -2) == line_start
            and int(block.get("line_end") or -2) == line_end
        ):
            return block
    return None


def _block_spine(block_anchor_path: Path, block_ordinal: int, symbol_to_anchor: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with block_anchor_path.open("rb") as handle:
        while chunk := handle.read(BLOCK_ANCHOR_RECORD.size):
            if len(chunk) != BLOCK_ANCHOR_RECORD.size:
                continue
            symbol, row_block_ordinal, position = BLOCK_ANCHOR_RECORD.unpack(chunk)
            if int(row_block_ordinal) != block_ordinal:
                continue
            symbol_id = symbol_hex(symbol)
            rows.append({
                "position": int(position),
                "symbol": symbol_id,
                "anchor": symbol_to_anchor.get(symbol_id, symbol_id),
            })
    rows.sort(key=lambda row: int(row["position"]))
    return rows


def _relation_count_lookup(paths: Any) -> dict[tuple[str, str, int], int]:
    lookup: dict[tuple[str, str, int], int] = {}
    for center, neighbor, offset, observations in iter_relation_records(paths):
        lookup[(symbol_hex(center), symbol_hex(neighbor), int(offset))] = int(observations)
    return lookup


def _start_position(spine: list[dict[str, Any]], *, question: str, starter: str | None) -> dict[str, Any]:
    if not spine:
        return {"status": "no_local_spine", "reason": "selected block has no block-anchor postings", "position": None}
    spine_anchors = [str(row["anchor"]) for row in spine]
    if starter:
        starter_anchors = anchorize(starter)
        start_index = _subsequence_index(spine_anchors, starter_anchors)
        if start_index is None:
            return {
                "status": "starter_not_found",
                "reason": "starter anchors were not found inside count-selected local spine",
                "starter_anchors": starter_anchors,
                "position": None,
            }
        return {
            "status": "ready",
            "mode": "starter_exact_match",
            "starter_anchors": starter_anchors,
            "position": start_index + len(starter_anchors) - 1,
        }
    question_anchors = anchorize(question)
    for index, anchor in enumerate(spine_anchors):
        if anchor in question_anchors:
            return {
                "status": "ready",
                "mode": "first_question_anchor_in_local_spine",
                "question_anchors": question_anchors,
                "position": index,
            }
    return {
        "status": "ready",
        "mode": "local_spine_start",
        "question_anchors": question_anchors,
        "position": 0,
    }


def _subsequence_index(values: list[str], needle: list[str]) -> int | None:
    if not needle:
        return None
    width = len(needle)
    for index in range(0, len(values) - width + 1):
        if values[index:index + width] == needle:
            return index
    return None


def _local_branch_candidates(
    spine: list[dict[str, Any]],
    current_index: int,
    relation_counts: dict[tuple[str, str, int], int],
    *,
    branch_k: int,
) -> list[dict[str, Any]]:
    current = spine[current_index]
    candidates: list[dict[str, Any]] = []
    for next_index in range(current_index + 1, min(len(spine), current_index + 7)):
        candidate = spine[next_index]
        offset = int(candidate["position"]) - int(current["position"])
        count_value = int(relation_counts.get((str(current["symbol"]), str(candidate["symbol"]), offset), 0))
        if count_value <= 0:
            continue
        candidates.append({
            "position": int(next_index),
            "block_position": int(candidate["position"]),
            "anchor": candidate["anchor"],
            "symbol": candidate["symbol"],
            "offset": offset,
            "native_relation_count": count_value,
        })
    candidates.sort(key=lambda row: (-int(row["native_relation_count"]), int(row["offset"]), int(row["position"])))
    return candidates[: max(1, int(branch_k))]


def _location_receipt(location: dict[str, Any], block: dict[str, Any]) -> dict[str, Any]:
    return {
        "citation": location.get("citation"),
        "citation_id": block.get("citation_id"),
        "file_path": location.get("file_path"),
        "line_start": location.get("line_start"),
        "line_end": location.get("line_end"),
        "direct_hit_count": location.get("direct_hit_count"),
        "density_score": location.get("density_score"),
        "score": location.get("score"),
        "block_ordinal": block.get("block_ordinal"),
        "block_id": block.get("block_id"),
    }


def _speech_policy() -> dict[str, Any]:
    return {
        "method": "count_selected_local_spine_walk",
        "retrieval_selects_evidence": True,
        "global_relations_can_rank_or_pressure": True,
        "global_relations_do_not_speak_directly": True,
        "documents_verify_custody": True,
        "document_text_lookup_used_for_speech_body": False,
        "rough_output_is_anchor_sequence_not_final_clearspeak": True,
    }


def _pretty_answer(trace: dict[str, Any], trace_path: Path) -> str:
    lines = [
        "# TrueMem Count-Walk Speech",
        "",
        f"Question: {trace.get('question')}",
        f"Status: {trace.get('walk_status')}",
        f"Stop reason: {trace.get('stop_reason')}",
        f"Model used: {trace.get('model_used')}",
        "",
    ]
    selected = trace.get("selected_location")
    if selected:
        lines.extend([
            "## Evidence",
            f"- citation: {selected.get('citation')}",
            f"- source: {selected.get('file_path')} lines {selected.get('line_start')}-{selected.get('line_end')}",
            f"- rank key: direct={selected.get('direct_hit_count')} density={selected.get('density_score')} score={selected.get('score')}",
            "",
        ])
    lines.extend([
        "## Rough Count-Walk Output",
        "",
        str(trace.get("rough_count_walk_text") or "No count-walk speech was produced."),
        "",
        "## Trace",
        "",
        f"Evidence trace: {trace_path}",
        "",
        "This is a rough anchor-speech walk, not final ClearSpeak.",
        "Counts choose the local continuation path; blocks/citations prove custody.",
        "",
    ])
    return "\n".join(lines)


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
