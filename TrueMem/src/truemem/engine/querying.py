from __future__ import annotations

import os
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

from ..nlp_resolver import resolve_answer
from .anchors import GLUE_ANCHORS, anchorize, anchors_to_text, answer_direction_anchors, expand_query_anchors, symbol_hex
from .base import COUNT_BACKEND, safe_id, sha1_text, unique_stamp, utc_now, with_protected_notice, write_json
from .chat import apply_block_metadata_filter, build_metadata_filter
from .forensic import build_forensic_support_receipt
from .hardware import MIN_RUNTIME_WORKERS, detect_system_resources, enforce_minimum_runtime_requirements
from .qualification import qualify_evidence, significant_question_terms
from .prediction_walk import (
    Relation,
    citation_coordinates_for_path,
    deeper_wider_relationship_search,
    predict_anchor_path,
)
from .pipeline import numbered_sentences
from .qa_ledger import append_query_record
from .storage import (
    DatasetPaths,
    dataset_paths,
    ensure_dataset,
    index_readiness,
    iter_anchor_records,
    iter_relation_records,
    read_anchor_to_symbol,
    read_block_anchor_rows,
    read_blocks,
    read_symbol_to_anchor,
)


def query(
    runtime_root: str | Path,
    dataset_id: str,
    question: str,
    *,
    top_k: int = 5,
    created_after: str | None = None,
    created_before: str | None = None,
    speaker: str | None = None,
) -> dict[str, Any]:
    paths = dataset_paths(runtime_root, dataset_id)
    ensure_dataset(runtime_root, dataset_id)
    readiness = index_readiness(runtime_root, dataset_id)
    if not readiness["query_allowed"]:
        reason = ", ".join(readiness.get("reasons") or ["index_not_ready"])
        raise RuntimeError(f"INDEX_NOT_READY: query_allowed=false; {reason}")
    raw_q_anchors = anchorize(question)
    q_anchors = expand_query_anchors(raw_q_anchors)
    direction_anchors = answer_direction_anchors(q_anchors)
    if not direction_anchors:
        raise ValueError("question produced no answer-direction anchors")
    q_counter = Counter(direction_anchors)
    cloud_gate = dataset_cloud_gate(paths, question, q_counter)
    if not cloud_gate["approved"]:
        output = _cloud_mismatch_result(
            paths=paths,
            dataset_id=dataset_id,
            question=question,
            q_counter=q_counter,
            readiness=readiness,
            cloud_gate=cloud_gate,
        )
        qa_record = append_query_record(paths, output)
        output["qa_record"] = qa_record
        write_json(Path(str(output["output_path"])), output)
        return with_protected_notice(output)

    blocks = read_blocks(paths)
    block_anchor_rows = read_block_anchor_rows(paths)
    metadata_filter = build_metadata_filter(created_after=created_after, created_before=created_before, speaker=speaker)
    if metadata_filter["active"]:
        blocks, block_anchor_rows = apply_block_metadata_filter(blocks, block_anchor_rows, metadata_filter)
    relation_neighbors = top_relation_neighbors(paths, q_counter, limit=16)
    raw_candidate_blocks = score_blocks(paths, blocks, block_anchor_rows, q_counter, relation_neighbors, top_k=max(top_k * 5, 25))
    qualified = qualify_evidence(question, Counter(anchorize(question)), raw_candidate_blocks, top_k=top_k)
    cloud_gate = {**cloud_gate, "retrieval_ran": True, "topk_ran": True}
    anchor_prediction_answer = _anchor_prediction_answer(paths, direction_anchors, qualified["locations"], blocks)

    answer_packet = {
        "instruction": "Use cited local evidence coordinates only. This packet is a facsimile output, not source evidence.",
        "citations_owned_by": "TrueMem",
        "qualification": qualified["summary"],
        "qualification_receipts": qualified["receipts"],
        "locations": qualified["locations"],
        "rejected_locations": qualified["rejected"],
        "anchor_prediction_answer": anchor_prediction_answer,
    }
    final_answer = resolve_answer(question, answer_packet)
    forensic_receipt = build_forensic_support_receipt(question, answer_packet, final_answer)

    output = {
        "schema": "truemem_query_result@1",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "question": question,
        "question_anchors": q_anchors,
        "answer_direction_anchors": direction_anchors,
        "answer_direction_formula": {
            "preserved_map_anchors": len(q_anchors),
            "steering_anchor_kinds": ["content", "relation"],
            "relationship_operators_shape_direction": True,
            "glue_and_boundaries_may_continue_path": True,
            "glue_and_boundaries_may_steer_path": False,
            "evidence_fit": "dataset_presence + inverse_block_frequency + native_signed_relationship_counts",
        },
        "relation_neighbors": relation_neighbors,
        "count_backend": COUNT_BACKEND,
        "model_used": "none",
        "model_may_search": False,
        "persistent_memory": False,
        "index_readiness": readiness,
        "metadata_filter": metadata_filter,
        "dataset_cloud_gate": cloud_gate,
        "answer_packet": answer_packet,
        "final_answer": final_answer,
        "anchor_prediction_answer": anchor_prediction_answer,
        "forensic_support_receipt": forensic_receipt,
    }
    output_path = paths.outputs / f"query_{unique_stamp()}_{sha1_text(question)[:8]}.json"
    output["output_path"] = str(output_path)
    write_json(output_path, output)
    qa_record = append_query_record(paths, output)
    output["qa_record"] = qa_record
    write_json(output_path, output)
    return with_protected_notice(output)


def dataset_cloud_gate(paths: DatasetPaths, question: str, q_counter: Counter[str]) -> dict[str, Any]:
    question_terms = significant_question_terms(answer_direction_anchors(list(q_counter)))
    anchor_counts = _anchor_observation_counts(paths)
    present = [anchor for anchor in question_terms if int(anchor_counts.get(anchor, 0)) > 0]
    absent = [anchor for anchor in question_terms if int(anchor_counts.get(anchor, 0)) <= 0]
    block_cloud = _block_cloud_fit(paths, present)
    coverage = len(present) / max(1, len(question_terms))
    low_fit = [
        {"anchor": anchor, "reason": "not_in_dataset_cloud", "observations": int(anchor_counts.get(anchor, 0))}
        for anchor in absent
    ]
    if not question_terms:
        approved = False
        reject_reason = "no_significant_question_anchors"
    elif coverage < 0.40 and int(block_cloud["best_block_match_count"]) < 2:
        approved = False
        reject_reason = "dataset_cloud_coverage_below_minimum"
    elif absent and int(block_cloud["best_block_match_count"]) < 2:
        approved = False
        reject_reason = "present_anchors_do_not_form_local_cloud"
    else:
        approved = True
        reject_reason = None
    return {
        "schema": "truemem_dataset_cloud_gate@1",
        "question": question,
        "approved": approved,
        "threshold": 0.60,
        "coverage": round(float(coverage), 4),
        "significant_question_anchors": question_terms,
        "present_anchors": present,
        "absent_anchors": absent,
        "low_fit_anchors": low_fit,
        "block_cloud_fit": block_cloud,
        "reject_reason": reject_reason,
        "retrieval_ran": False,
        "topk_ran": False,
    }


def _cloud_mismatch_result(
    *,
    paths: DatasetPaths,
    dataset_id: str,
    question: str,
    q_counter: Counter[str],
    readiness: dict[str, Any],
    cloud_gate: dict[str, Any],
) -> dict[str, Any]:
    answer_packet = {
        "instruction": "Dataset cloud gate refused before TopK. No retrieval or answer generation ran.",
        "citations_owned_by": "TrueMem",
        "qualification": {
            "schema": "truemem_evidence_qualification_summary@1",
            "support_state": "dataset_cloud_mismatch",
            "raw_candidate_count": 0,
            "qualified_count": 0,
            "rejected_count": 0,
            "required_terms": cloud_gate["significant_question_anchors"],
            "path_or_config_intent": False,
        },
        "qualification_receipts": [],
        "locations": [],
        "rejected_locations": [],
    }
    final_answer = {
        "schema": "truemem_nlp_answer@1",
        "resolver": "truemem_dataset_cloud_gate@1",
        "status": "dataset_cloud_mismatch",
        "text": "The question does not fit the admitted dataset cloud closely enough to run retrieval.",
        "citations": [],
        "model_used": "none",
        "model_may_search": False,
        "citation_source": "truemem_dataset_cloud_gate",
    }
    forensic_receipt = build_forensic_support_receipt(question, answer_packet, final_answer)
    forensic_receipt["gate_refusal"] = "dataset_cloud_mismatch"
    forensic_receipt["conclusion"] = "Retrieval was not run because the question failed the dataset cloud gate."
    output = {
        "schema": "truemem_query_result@1",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "question": question,
        "question_anchors": anchorize(question),
        "answer_direction_anchors": list(q_counter),
        "relation_neighbors": [],
        "count_backend": COUNT_BACKEND,
        "model_used": "none",
        "model_may_search": False,
        "persistent_memory": False,
        "index_readiness": readiness,
        "metadata_filter": build_metadata_filter(created_after=None, created_before=None, speaker=None),
        "dataset_cloud_gate": cloud_gate,
        "answer_packet": answer_packet,
        "final_answer": final_answer,
        "forensic_support_receipt": forensic_receipt,
    }
    output_path = paths.outputs / f"query_{unique_stamp()}_{sha1_text(question)[:8]}_cloud_mismatch.json"
    output["output_path"] = str(output_path)
    write_json(output_path, output)
    return output


def _anchor_observation_counts(paths: DatasetPaths) -> dict[str, int]:
    symbol_to_anchor = read_symbol_to_anchor(paths)
    counts: dict[str, int] = {}
    for symbol, observations in iter_anchor_records(paths):
        anchor = symbol_to_anchor.get(symbol_hex(symbol), symbol_hex(symbol))
        counts[anchor] = int(observations)
    return counts


def _block_cloud_fit(paths: DatasetPaths, anchors: list[str]) -> dict[str, Any]:
    if not anchors:
        return {
            "schema": "truemem_block_cloud_fit@1",
            "best_block_match_count": 0,
            "best_block_ordinal": None,
            "best_block_anchors": [],
        }
    wanted = set(anchors)
    symbol_to_anchor = {
        bytes.fromhex(symbol[2:]): anchor
        for symbol, anchor in read_symbol_to_anchor(paths).items()
        if anchor in wanted and symbol.startswith("0x")
    }
    block_hits: dict[int, set[str]] = {}
    for symbol, block_ordinal, _position in read_block_anchor_rows(paths):
        anchor = symbol_to_anchor.get(symbol)
        if anchor is None:
            continue
        block_hits.setdefault(int(block_ordinal), set()).add(anchor)

    if not block_hits:
        return {
            "schema": "truemem_block_cloud_fit@1",
            "best_block_match_count": 0,
            "best_block_ordinal": None,
            "best_block_anchors": [],
        }
    best_block_ordinal, best_anchors = max(
        block_hits.items(),
        key=lambda item: (len(item[1]), -int(item[0])),
    )
    return {
        "schema": "truemem_block_cloud_fit@1",
        "best_block_match_count": len(best_anchors),
        "best_block_ordinal": int(best_block_ordinal),
        "best_block_anchors": sorted(best_anchors),
    }

def batch_questions(
    runtime_root: str | Path,
    dataset_id: str,
    questions_path: str | Path,
    *,
    top_k: int = 5,
    show_progress: bool = False,
    workers: int | str = "auto",
) -> dict[str, Any]:
    """Run a plain question list through the existing single-question query path."""
    paths = dataset_paths(runtime_root, dataset_id)
    ensure_dataset(runtime_root, dataset_id)
    source = Path(questions_path).expanduser().resolve()
    question_items = _load_batch_question_items(source)
    effective_workers = _resolve_batch_workers(workers)
    run_id = unique_stamp()
    run_dir = paths.outputs / f"batch_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    started = perf_counter()
    completed = 0
    failures: list[dict[str, Any]] = []
    output_paths: list[str] = []
    question_results: list[dict[str, Any]] = []

    future_map = {}
    with ProcessPoolExecutor(max_workers=effective_workers) as pool:
        for item in question_items:
            future = pool.submit(
                _run_batch_query_item,
                str(Path(runtime_root).expanduser().resolve()),
                str(dataset_id),
                item,
                int(top_k),
            )
            future_map[future] = int(item["index"])

        items = _progress_iter(as_completed(future_map), total=len(future_map), enabled=show_progress)
        for future in items:
            row = future.result()
            question_results.append(row)
            if row["status"] == "completed":
                completed += 1
                output_paths.append(str(row["output_path"]))
            else:
                failures.append(row)

    total_elapsed = perf_counter() - started
    average = total_elapsed / len(question_items) if question_items else 0.0
    question_results = sorted(question_results, key=lambda row: int(row["index"]))
    output_paths = [str(row["output_path"]) for row in question_results if row["status"] == "completed"]
    failures = [row for row in question_results if row["status"] == "failed"]
    summary = with_protected_notice({
        "schema": "truemem_batch_run_summary@1",
        "run_id": run_id,
        "created_at": utc_now(),
        "dataset": safe_id(dataset_id),
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "questions_path": str(source),
        "question_count": len(question_items),
        "completed": completed,
        "failed": len(failures),
        "output_paths": output_paths,
        "question_results": question_results,
        "failures": failures,
        "workers_requested": str(workers),
        "workers_effective": int(effective_workers),
        "parallel_execution": True,
        "avg_query_time": average,
        "avg_query_time_seconds": average,
        "total_time_seconds": total_elapsed,
        "model_used": "none",
        "model_may_search": False,
        "persistent_memory": False,
    })
    summary_path = run_dir / "batch_run_summary.json"
    write_json(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    return summary


def _run_batch_query_item(
    runtime_root: str,
    dataset_id: str,
    item: dict[str, Any],
    top_k: int,
) -> dict[str, Any]:
    item_started = perf_counter()
    index = int(item["index"])
    question = str(item["question"])
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    try:
        result = query(runtime_root, dataset_id, question, top_k=top_k)
        elapsed = perf_counter() - item_started
        return {
            "index": int(index),
            "question": question,
            "metadata": metadata,
            "status": "completed",
            "output_path": str(result["output_path"]),
            "query_time_seconds": elapsed,
            "model_used": result.get("model_used", "none"),
        }
    except Exception as exc:  # pragma: no cover - defensive batch receipt path
        elapsed = perf_counter() - item_started
        return {
            "index": int(index),
            "question": question,
            "metadata": metadata,
            "status": "failed",
            "error": str(exc),
            "query_time_seconds": elapsed,
            "model_used": "none",
        }


def _load_batch_question_items(path: Path) -> list[dict[str, Any]]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix.lower() == ".jsonl":
        items: list[dict[str, Any]] = []
        for fallback_index, line in enumerate(lines, start=1):
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            question = " ".join(str(payload.get("question") or "").split())
            if not question:
                continue
            index = int(payload.get("question_index") or fallback_index)
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            items.append({"index": index, "question": question, "metadata": metadata})
        return items
    return [
        {"index": index, "question": line.strip(), "metadata": {}}
        for index, line in enumerate(lines, start=1)
        if line.strip()
    ]


def _resolve_batch_workers(workers: int | str) -> int:
    resources = detect_system_resources()
    enforce_minimum_runtime_requirements(resources)
    cpu_count = int(resources.get("logical_cpu_count") or os.cpu_count() or 1)
    if isinstance(workers, str):
        if workers.lower() == "auto":
            requested = max(MIN_RUNTIME_WORKERS, min(cpu_count, max(1, cpu_count - 1)))
        else:
            requested = int(workers)
    else:
        requested = int(workers)
    if requested < MIN_RUNTIME_WORKERS:
        raise ValueError(f"batch requires at least {MIN_RUNTIME_WORKERS} workers; single-core/low-core execution is not allowed")
    if requested > cpu_count:
        raise RuntimeError(f"requested workers={requested} exceeds logical cpu count={cpu_count}")
    return int(requested)


def _progress_iter(iterable: Iterable[Any], *, total: int, enabled: bool) -> Iterable[Any]:
    if not enabled:
        return iterable
    try:
        from tqdm import tqdm
    except Exception:  # pragma: no cover - fallback only when tqdm is unavailable
        return iterable
    return tqdm(iterable, total=total, desc="TrueMem batch", unit="question")

def top_relation_neighbors(paths: DatasetPaths, q_counter: Counter[str], *, limit: int) -> list[dict[str, Any]]:
    scores: Counter[bytes] = Counter()
    anchor_to_symbol = read_anchor_to_symbol(paths)
    blocked_symbols = {
        symbol
        for anchor in [*q_counter, *GLUE_ANCHORS]
        if (symbol := _dataset_symbol_bytes(anchor_to_symbol, anchor)) is not None
    }
    query_symbols = {
        symbol: weight
        for anchor, weight in q_counter.items()
        if (symbol := _dataset_symbol_bytes(anchor_to_symbol, anchor)) is not None
    }
    symbol_to_anchor = read_symbol_to_anchor(paths)
    for anchor_symbol, neighbor_symbol, _offset, observations in iter_relation_records(paths):
        weight = query_symbols.get(anchor_symbol)
        if not weight or neighbor_symbol in blocked_symbols:
            continue
        scores[neighbor_symbol] += observations * weight
    return [
        {"anchor": symbol_to_anchor.get(symbol_hex(symbol), symbol_hex(symbol)), "symbol": symbol_hex(symbol), "score": score}
        for symbol, score in scores.most_common(limit)
    ]

def score_blocks(
    paths: DatasetPaths,
    blocks: dict[int, dict[str, Any]],
    block_anchor_rows: list[tuple[bytes, int, int]],
    q_counter: Counter[str],
    relation_neighbors: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    weights: Counter[bytes] = Counter()
    anchor_to_symbol = read_anchor_to_symbol(paths)
    direct_symbols = {
        symbol
        for anchor in q_counter
        if (symbol := _dataset_symbol_bytes(anchor_to_symbol, anchor)) is not None
    }
    symbol_to_anchor = read_symbol_to_anchor(paths)
    for anchor, count in q_counter.items():
        symbol = _dataset_symbol_bytes(anchor_to_symbol, anchor)
        if symbol is not None:
            weights[symbol] += 80 * count
    for index, row in enumerate(relation_neighbors):
        weights[bytes.fromhex(str(row["symbol"])[2:])] += max(1, 4 - index // 4)

    posting_counts: Counter[bytes] = Counter(symbol for symbol, _block, _pos in block_anchor_rows)
    block_lengths: Counter[int] = Counter(block for _symbol, block, _pos in block_anchor_rows)
    block_scores: Counter[int] = Counter()
    hits: dict[int, set[bytes]] = {}
    direct_hits: Counter[int] = Counter()
    seen_postings: set[tuple[bytes, int]] = set()

    for symbol, block_ordinal, _position in block_anchor_rows:
        weight = weights.get(symbol)
        if not weight:
            continue
        posting_key = (symbol, block_ordinal)
        if posting_key in seen_postings:
            continue
        seen_postings.add(posting_key)
        document_frequency = posting_counts[symbol]
        adjusted_weight = weight / max(1.0, document_frequency ** 0.5)
        block_scores[block_ordinal] += adjusted_weight
        hits.setdefault(block_ordinal, set()).add(symbol)
        if symbol in direct_symbols:
            direct_hits[block_ordinal] += 1

    ranked_rows: list[tuple[int, float, float, int]] = []
    for block_ordinal, score in block_scores.items():
        anchor_count = block_lengths.get(block_ordinal, 1)
        density = float(score) / max(1.0, anchor_count ** 0.5)
        ranked_rows.append((block_ordinal, float(score), density, anchor_count))
    ranked = sorted(ranked_rows, key=lambda item: (-direct_hits[item[0]], -item[2], -item[1], item[0]))

    out: list[dict[str, Any]] = []
    for block_ordinal, score, density, anchor_count in ranked[:top_k]:
        block = blocks.get(block_ordinal)
        if not block:
            continue
        matched_symbols = hits.get(block_ordinal, set())
        out.append({
            "citation": str(block["marker"]),
            "file_path": str(block["file_path"]),
            "line_start": int(block["line_start"]),
            "line_end": int(block["line_end"]),
            "score": round(float(score), 4),
            "density_score": round(float(density), 4),
            "block_anchor_count": anchor_count,
            "direct_hit_count": int(direct_hits[block_ordinal]),
            "direct_matched_anchors": sorted(symbol_to_anchor.get(symbol_hex(symbol), symbol_hex(symbol)) for symbol in matched_symbols & direct_symbols),
            "matched_anchors": sorted(symbol_to_anchor.get(symbol_hex(symbol), symbol_hex(symbol)) for symbol in matched_symbols),
            "text": str(block["text"]),
            "block_ordinal": int(block_ordinal),
            "sentences": block.get("sentences") or numbered_sentences(str(block["text"])),
        })
    return out


def deeper_wider_after_answer(
    runtime_root: str | Path,
    dataset_id: str,
    first_answer: dict[str, Any],
    *,
    depth: int = 3,
    width: int = 12,
) -> dict[str, Any]:
    """Run the optional second relationship search over the same count authority."""
    paths = dataset_paths(runtime_root, dataset_id)
    relations = _decoded_relations(paths)
    result = deeper_wider_relationship_search(
        relations,
        first_answer=first_answer,
        anchor_frequencies=_anchor_observation_counts(paths),
        depth=depth,
        width=width,
    )
    result["dataset_id"] = safe_id(dataset_id)
    result["count_backend"] = COUNT_BACKEND
    return with_protected_notice(result)


def _anchor_prediction_answer(
    paths: DatasetPaths,
    question_anchors: list[str],
    locations: list[dict[str, Any]],
    blocks: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    if not locations:
        return {
            "schema": "truemem_anchor_prediction_answer@1",
            "status": "no_qualified_evidence",
            "prediction": None,
            "citations": [],
            "deeper_wider_available": False,
        }
    selected = locations[0]
    block_ordinal = int(selected.get("block_ordinal", -1))
    block = blocks.get(block_ordinal)
    if block is None:
        return {
            "schema": "truemem_anchor_prediction_answer@1",
            "status": "selected_block_unavailable",
            "prediction": None,
            "citations": [],
            "deeper_wider_available": False,
        }
    block_anchors = anchorize(str(block.get("text") or ""))
    start_index = next(
        (index for index, anchor in enumerate(block_anchors) if anchor in set(question_anchors)),
        0,
    )
    resolved_history = block_anchors[max(0, start_index - 5) : start_index + 1]
    if not resolved_history:
        return {
            "schema": "truemem_anchor_prediction_answer@1",
            "status": "selected_block_has_no_anchors",
            "prediction": None,
            "citations": [],
            "deeper_wider_available": False,
        }
    prediction = predict_anchor_path(
        _decoded_relations(paths),
        resolved_history=resolved_history,
        query_anchors=question_anchors,
        anchor_frequencies=_anchor_observation_counts(paths),
        max_new_anchors=24,
    )
    citation_blocks = []
    for row in blocks.values():
        citation_blocks.append({
            **row,
            "sentences": row.get("sentences") or numbered_sentences(str(row.get("text") or "")),
        })
    citations = citation_coordinates_for_path(prediction["complete_path"], blocks=citation_blocks)
    return {
        "schema": "truemem_anchor_prediction_answer@1",
        "status": "predicted_from_native_map",
        "answer_anchors": prediction["generated_anchors"],
        "answer_text": anchors_to_text(prediction["generated_anchors"]),
        "prediction": prediction,
        "citations": citations,
        "evidence_convergence": {
            "status": "converged" if citations else "no_source_coordinate_convergence",
            "locations": citations,
            "authority": "source_block_sentence_coordinates",
        },
        "citation_format": "block_ordinal + sentence_ordinals",
        "deeper_wider_available": True,
        "deeper_wider_default": False,
        "deeper_wider_requires_first_answer": True,
        "model_handoff": {
            "verify_citations_before_final_language": True,
            "evidence_authority": "TrueMem",
            "model_authority": False,
        },
    }


def _decoded_relations(paths: DatasetPaths) -> list[Relation]:
    symbol_to_anchor = read_symbol_to_anchor(paths)
    return [
        Relation(
            symbol_to_anchor.get(symbol_hex(center), symbol_hex(center)),
            symbol_to_anchor.get(symbol_hex(neighbor), symbol_hex(neighbor)),
            int(offset),
            int(observations),
        )
        for center, neighbor, offset, observations in iter_relation_records(paths)
    ]


def _dataset_symbol_bytes(anchor_to_symbol: dict[str, str], anchor: str) -> bytes | None:
    symbol = anchor_to_symbol.get(anchor)
    if not symbol or not symbol.startswith("0x"):
        return None
    return bytes.fromhex(symbol[2:])
