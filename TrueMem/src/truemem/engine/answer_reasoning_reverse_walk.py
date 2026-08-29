from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .anchors import GLUE_ANCHORS, anchor_kind, anchorize, symbol_hex
from .base import safe_id, utc_now, with_protected_notice, write_json
from .storage import (
    dataset_paths,
    ensure_dataset,
    index_readiness,
    iter_relation_records,
    read_anchor_to_symbol,
    read_block_anchor_rows,
    read_blocks,
    read_symbol_to_anchor,
)

MODES = {"blind_reverse_walk", "paired_set_verify"}
WEAK_ANCHORS = GLUE_ANCHORS | {
    "answer",
    "question",
    "supplied",
    "claim",
    "benchmark",
    "according",
    "book",
    "bench",
}


def run_answer_reasoning_reverse_walk(
    *,
    runtime_root: str | Path,
    dataset_id: str,
    claims_path: str | Path,
    out_dir: str | Path,
    mode: str = "blind_reverse_walk",
    top_k: int = 8,
) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"unsupported reverse-walk mode: {mode}")
    if int(top_k) < 1:
        raise ValueError("top_k must be at least 1")
    ensure_dataset(runtime_root, dataset_id)
    paths = dataset_paths(runtime_root, dataset_id)
    readiness = index_readiness(runtime_root, dataset_id)
    if not readiness["query_allowed"]:
        reason = ", ".join(readiness.get("reasons") or ["index_not_ready"])
        raise RuntimeError(f"INDEX_NOT_READY: query_allowed=false; {reason}")

    claims_source = Path(claims_path).expanduser().resolve()
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    traces_dir = out / "traces"
    receipts_dir = out / "receipts"
    traces_dir.mkdir(parents=True, exist_ok=True)
    receipts_dir.mkdir(parents=True, exist_ok=True)

    blocks = read_blocks(paths)
    block_anchor_rows = read_block_anchor_rows(paths)
    anchor_to_symbol = read_anchor_to_symbol(paths)
    symbol_to_anchor = read_symbol_to_anchor(paths)
    relation_pressure = _relation_pressure(paths, symbol_to_anchor)
    claims = _read_claims(claims_source)

    trace_path = traces_dir / "ANSWER_REASONING_REVERSE_WALK_TRACE.jsonl"
    support_counts: Counter[str] = Counter()
    expected_seen = 0
    with trace_path.open("w", encoding="utf-8", newline="\n") as handle:
        for index, claim in enumerate(claims, start=1):
            trace = _trace_claim(
                claim=claim,
                claim_index=index,
                mode=mode,
                top_k=int(top_k),
                blocks=blocks,
                block_anchor_rows=block_anchor_rows,
                anchor_to_symbol=anchor_to_symbol,
                symbol_to_anchor=symbol_to_anchor,
                relation_pressure=relation_pressure,
            )
            support_counts[str(trace["support_decision"])] += 1
            if trace["expected_passage_seen"]:
                expected_seen += 1
            handle.write(json.dumps(with_protected_notice(trace), ensure_ascii=True) + "\n")

    summary = with_protected_notice({
        "schema": "truemem_answer_reasoning_reverse_walk_run@0",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "mode": mode,
        "claims_path": str(claims_source),
        "out_dir": str(out),
        "records_processed": len(claims),
        "top_k": int(top_k),
        "trace_jsonl_path": str(trace_path),
        "support_decision_counts": dict(sorted(support_counts.items())),
        "expected_passage_seen_count": expected_seen,
        "blind_answer_to_corpus_evidence_hit_rate": _rate(
            support_counts["supported"] + support_counts["partially_supported"] + support_counts["needs_bridge"],
            len(claims),
        ),
        "expected_passage_found_in_reverse_topK_rate": _rate(expected_seen, len(claims)),
        "contradiction_count": support_counts["contradicted"],
        "unsupported_count": support_counts["unsupported"],
        "needs_bridge_count": support_counts["needs_bridge"],
        "retrieval_ran": False,
        "topk_ran": False,
        "intake_ran": False,
        "ranking_mutation": False,
        "dataset_mutation": False,
        "speech_mutation": False,
        "model_used": "none",
        "model_may_search": False,
        "no_answer_generation": True,
        "no_benchmark_answer_leakage_into_intake": True,
    })
    summary_path = out / "ANSWER_REASONING_REVERSE_WALK_SUMMARY.json"
    write_json(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    write_json(receipts_dir / "run_receipt.json", summary)
    return summary


def _trace_claim(
    *,
    claim: dict[str, Any],
    claim_index: int,
    mode: str,
    top_k: int,
    blocks: dict[int, dict[str, Any]],
    block_anchor_rows: list[tuple[bytes, int, int]],
    anchor_to_symbol: dict[str, str],
    symbol_to_anchor: dict[str, str],
    relation_pressure: Counter[str],
) -> dict[str, Any]:
    claim_id = str(claim.get("claim_id") or claim_index)
    question = " ".join(str(claim.get("question") or "").split())
    supplied_answer = " ".join(str(claim.get("supplied_answer") or "").split())
    if not supplied_answer:
        raise ValueError(f"claim {claim_id} has no supplied_answer")

    answer_anchor_set = _split_answer_anchors(supplied_answer)
    question_anchor_set = _split_question_anchors(question)
    answer_anchors = answer_anchor_set["all"]
    question_anchors = question_anchor_set["all"]
    candidates = _reverse_candidates(
        answer_anchors=answer_anchors,
        question_anchors=question_anchors,
        blocks=blocks,
        block_anchor_rows=block_anchor_rows,
        anchor_to_symbol=anchor_to_symbol,
        symbol_to_anchor=symbol_to_anchor,
        relation_pressure=relation_pressure,
        top_k=top_k,
    )
    audit_reference = claim.get("audit_reference") if isinstance(claim.get("audit_reference"), dict) else {}
    reference_value = str(audit_reference.get("value") or "")
    reference_seen, reference_rank = _reference_seen(candidates, reference_value)
    paired_verification = None
    if mode == "paired_set_verify":
        reference_candidate = _direct_reference_candidate(
            blocks=blocks,
            value=reference_value,
            answer_anchors=answer_anchors,
            question_anchors=question_anchors,
            relation_pressure=relation_pressure,
        )
        if reference_candidate is None:
            reference_candidate = _find_reference_candidate(candidates, reference_value)
        paired_support = _support_decision(reference_candidate, bool(reference_seen)) if reference_candidate else "unsupported"
        paired_verification = {
            "reference": audit_reference,
            "reference_found": bool(reference_candidate),
            "support_decision": paired_support,
            "reference_candidate": reference_candidate,
        }

    support_decision = paired_verification["support_decision"] if paired_verification else _support_decision(candidates[0] if candidates else None, bool(reference_seen))
    return {
        "schema": "truemem_answer_reasoning_reverse_walk_trace@0",
        "created_at": utc_now(),
        "mode": mode,
        "claim_index": claim_index,
        "claim_id": claim_id,
        "question": question,
        "supplied_answer": supplied_answer,
        "metadata": claim.get("metadata") if isinstance(claim.get("metadata"), dict) else {},
        "answer_anchor_set": answer_anchor_set,
        "question_anchor_set": question_anchor_set,
        "reverse_topK_candidates": candidates,
        "candidate_citations": [candidate["citation"] for candidate in candidates],
        "candidate_passages": [
            {
                "citation": candidate["citation"],
                "file_path": candidate["file_path"],
                "line_start": candidate["line_start"],
                "line_end": candidate["line_end"],
                "text": candidate["text"],
            }
            for candidate in candidates
        ],
        "answer_to_candidate_coverage": candidates[0]["answer_to_candidate_coverage"] if candidates else 0.0,
        "candidate_to_question_coverage": candidates[0]["candidate_to_question_coverage"] if candidates else 0.0,
        "local_neighborhood_blocks": candidates[0]["local_neighborhood_blocks"] if candidates else [],
        "pressure_links": candidates[0]["pressure_links"] if candidates else [],
        "bridge_needed": bool(candidates and candidates[0]["bridge_needed"]),
        "support_decision": support_decision,
        "expected_passage_seen": bool(reference_seen),
        "expected_passage_rank_if_seen": reference_rank,
        "paired_set_verification": paired_verification,
        "reverse_topK_tree": [
            {
                "answer_root": supplied_answer,
                "candidate": {
                    "citation": candidate["citation"],
                    "file_path": candidate["file_path"],
                    "line_start": candidate["line_start"],
                    "line_end": candidate["line_end"],
                    "score": candidate["score"],
                },
                "nearby_blocks": candidate["local_neighborhood_blocks"],
                "question_anchor_pressure": {
                    "candidate_to_question_coverage": candidate["candidate_to_question_coverage"],
                    "matched_question_anchors": candidate["matched_question_anchors"],
                    "missing_question_anchors": candidate["missing_question_anchors"],
                },
            }
            for candidate in candidates
        ],
        "no_mutation_receipt": {
            "no_llm": True,
            "model_used": "none",
            "no_answer_generation": True,
            "no_ranking_mutation": True,
            "no_dataset_mutation": True,
            "no_speech_mutation": True,
            "expected_reference_used_for_retrieval_seed": False,
        },
    }


def _reverse_candidates(
    *,
    answer_anchors: list[str],
    question_anchors: list[str],
    blocks: dict[int, dict[str, Any]],
    block_anchor_rows: list[tuple[bytes, int, int]],
    anchor_to_symbol: dict[str, str],
    symbol_to_anchor: dict[str, str],
    relation_pressure: Counter[str],
    top_k: int,
) -> list[dict[str, Any]]:
    answer_symbols = _symbols_for(answer_anchors, anchor_to_symbol)
    question_symbols = _symbols_for(question_anchors, anchor_to_symbol)
    answer_symbol_set = set(answer_symbols)
    question_symbol_set = set(question_symbols)
    block_hits: dict[int, set[str]] = {}
    block_question_hits: dict[int, set[str]] = {}
    for symbol, block_ordinal, _position in block_anchor_rows:
        anchor = symbol_to_anchor.get(symbol_hex(symbol), symbol_hex(symbol))
        if symbol in answer_symbol_set:
            block_hits.setdefault(int(block_ordinal), set()).add(anchor)
        if symbol in question_symbol_set:
            block_question_hits.setdefault(int(block_ordinal), set()).add(anchor)

    rows: list[dict[str, Any]] = []
    for block_ordinal, answer_hits in block_hits.items():
        block = blocks.get(block_ordinal)
        if not block:
            continue
        question_hits = block_question_hits.get(block_ordinal, set())
        answer_cov = len(answer_hits) / max(1, len(answer_anchors))
        question_cov = len(question_hits) / max(1, len(question_anchors))
        pressure = sum(relation_pressure.get(anchor, 0) for anchor in answer_hits)
        score = (answer_cov * 100.0) + (question_cov * 40.0) + min(20.0, pressure ** 0.5)
        local_blocks = _local_neighborhood(blocks, block_ordinal)
        bridge_needed = answer_cov >= 0.45 and question_cov < 0.25 and bool(question_anchors)
        rows.append({
            "citation": str(block.get("marker") or block.get("citation_id") or ""),
            "file_path": str(block.get("file_path") or ""),
            "line_start": int(block.get("line_start") or 0),
            "line_end": int(block.get("line_end") or 0),
            "block_ordinal": int(block_ordinal),
            "score": round(score, 4),
            "answer_to_candidate_coverage": round(answer_cov, 4),
            "candidate_to_question_coverage": round(question_cov, 4),
            "matched_answer_anchors": sorted(answer_hits),
            "missing_answer_anchors": sorted(set(answer_anchors) - answer_hits),
            "matched_question_anchors": sorted(question_hits),
            "missing_question_anchors": sorted(set(question_anchors) - question_hits),
            "density": round(len(answer_hits) / max(1, len(anchorize(str(block.get("text") or "")))), 4),
            "relation_pressure": int(pressure),
            "pressure_links": _pressure_links(answer_hits, relation_pressure),
            "local_neighborhood_blocks": local_blocks,
            "bridge_needed": bridge_needed,
            "text": str(block.get("text") or ""),
        })
    return sorted(rows, key=lambda row: (-float(row["score"]), -float(row["answer_to_candidate_coverage"]), int(row["block_ordinal"])))[:top_k]


def _split_answer_anchors(text: str) -> dict[str, list[str]]:
    anchors = _meaningful_anchors(text)
    return {
        "all": anchors,
        "conclusion": [anchor for anchor in anchors if anchor in {"no", "yes", "not", "cannot", "required", "allowed", "may", "must"}],
        "condition": [anchor for anchor in anchors if anchor in {"if", "when", "unless", "satisfied", "because", "where"}],
        "authority": [anchor for anchor in anchors if anchor in {"court", "judge", "section", "act", "jury", "juror", "trial"}],
        "weak": [anchor for anchor in anchorize(text) if anchor in WEAK_ANCHORS],
    }


def _split_question_anchors(text: str) -> dict[str, list[str]]:
    anchors = _meaningful_anchors(text)
    scenario = [anchor for anchor in anchors if anchor not in {"court", "judge", "jury", "juror", "trial", "excuse", "required", "must", "may"}]
    evidence = [anchor for anchor in anchors if anchor not in scenario]
    return {
        "all": anchors,
        "scenario": scenario,
        "evidence_bearing": evidence,
        "ambiguity": [anchor for anchor in anchors if anchor in {"required", "may", "must", "not", "can", "cannot"}],
    }


def _meaningful_anchors(text: str) -> list[str]:
    out: list[str] = []
    for anchor in anchorize(text):
        if anchor_kind(anchor) != "content" or len(anchor) < 3 or anchor in WEAK_ANCHORS:
            continue
        if anchor not in out:
            out.append(anchor)
    return out


def _symbols_for(anchors: list[str], anchor_to_symbol: dict[str, str]) -> list[bytes]:
    symbols: list[bytes] = []
    for anchor in anchors:
        symbol = anchor_to_symbol.get(anchor)
        if symbol and symbol.startswith("0x"):
            symbols.append(bytes.fromhex(symbol[2:]))
    return symbols


def _relation_pressure(paths: Any, symbol_to_anchor: dict[str, str]) -> Counter[str]:
    pressure: Counter[str] = Counter()
    for left, right, _offset, observations in iter_relation_records(paths):
        pressure[symbol_to_anchor.get(symbol_hex(left), symbol_hex(left))] += int(observations)
        pressure[symbol_to_anchor.get(symbol_hex(right), symbol_hex(right))] += int(observations)
    return pressure


def _local_neighborhood(blocks: dict[int, dict[str, Any]], block_ordinal: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ordinal in (block_ordinal - 1, block_ordinal, block_ordinal + 1):
        block = blocks.get(ordinal)
        if not block:
            continue
        out.append({
            "block_ordinal": ordinal,
            "citation": str(block.get("marker") or block.get("citation_id") or ""),
            "file_path": str(block.get("file_path") or ""),
            "line_start": int(block.get("line_start") or 0),
            "line_end": int(block.get("line_end") or 0),
            "text": str(block.get("text") or ""),
        })
    return out


def _pressure_links(anchors: set[str], relation_pressure: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"anchor": anchor, "relation_pressure": int(relation_pressure.get(anchor, 0))}
        for anchor in sorted(anchors)
        if int(relation_pressure.get(anchor, 0)) > 0
    ]


def _support_decision(candidate: dict[str, Any] | None, reference_seen: bool) -> str:
    if not candidate:
        return "unsupported"
    answer_cov = float(candidate["answer_to_candidate_coverage"])
    question_cov = float(candidate["candidate_to_question_coverage"])
    if answer_cov >= 0.55 and (question_cov >= 0.20 or reference_seen):
        return "supported"
    if answer_cov >= 0.45 and question_cov < 0.20:
        return "needs_bridge"
    if answer_cov >= 0.35:
        return "partially_supported"
    return "unsupported"


def _reference_seen(candidates: list[dict[str, Any]], value: str) -> tuple[bool, int | None]:
    if not value:
        return False, None
    for index, candidate in enumerate(candidates, start=1):
        if _candidate_matches_reference(candidate, value):
            return True, index
    return False, None


def _find_reference_candidate(candidates: list[dict[str, Any]], value: str) -> dict[str, Any] | None:
    if not value:
        return None
    for candidate in candidates:
        if _candidate_matches_reference(candidate, value):
            return candidate
    return None


def _direct_reference_candidate(
    *,
    blocks: dict[int, dict[str, Any]],
    value: str,
    answer_anchors: list[str],
    question_anchors: list[str],
    relation_pressure: Counter[str],
) -> dict[str, Any] | None:
    if not value:
        return None
    matched_blocks: list[tuple[int, dict[str, Any]]] = []
    matched_file_path: str | None = None
    for block_ordinal, block in blocks.items():
        row = {
            "file_path": str(block.get("file_path") or ""),
            "text": str(block.get("text") or ""),
        }
        if not _candidate_matches_reference(row, value):
            continue
        matched_file_path = str(block.get("file_path") or "")
        matched_blocks = [
            (ordinal, candidate_block)
            for ordinal, candidate_block in sorted(blocks.items())
            if str(candidate_block.get("file_path") or "") == matched_file_path
        ]
        break
    if not matched_blocks:
        return None
    first_ordinal, first_block = matched_blocks[0]
    _last_ordinal, last_block = matched_blocks[-1]
    combined_text = "\n".join(str(block.get("text") or "") for _ordinal, block in matched_blocks)
    block_anchors = set(_meaningful_anchors(combined_text))
    answer_hits = block_anchors & set(answer_anchors)
    question_hits = block_anchors & set(question_anchors)
    answer_cov = len(answer_hits) / max(1, len(answer_anchors))
    question_cov = len(question_hits) / max(1, len(question_anchors))
    pressure = sum(relation_pressure.get(anchor, 0) for anchor in answer_hits)
    return {
        "citation": str(first_block.get("marker") or first_block.get("citation_id") or ""),
        "file_path": str(first_block.get("file_path") or ""),
        "line_start": int(first_block.get("line_start") or 0),
        "line_end": int(last_block.get("line_end") or first_block.get("line_end") or 0),
        "block_ordinal": int(first_ordinal),
        "score": round((answer_cov * 100.0) + (question_cov * 40.0) + min(20.0, pressure ** 0.5), 4),
        "answer_to_candidate_coverage": round(answer_cov, 4),
        "candidate_to_question_coverage": round(question_cov, 4),
        "matched_answer_anchors": sorted(answer_hits),
        "missing_answer_anchors": sorted(set(answer_anchors) - answer_hits),
        "matched_question_anchors": sorted(question_hits),
        "missing_question_anchors": sorted(set(question_anchors) - question_hits),
        "density": round(len(answer_hits) / max(1, len(block_anchors)), 4),
        "relation_pressure": int(pressure),
        "pressure_links": _pressure_links(answer_hits, relation_pressure),
        "local_neighborhood_blocks": [
            {
                "block_ordinal": ordinal,
                "citation": str(block.get("marker") or block.get("citation_id") or ""),
                "file_path": str(block.get("file_path") or ""),
                "line_start": int(block.get("line_start") or 0),
                "line_end": int(block.get("line_end") or 0),
                "text": str(block.get("text") or ""),
            }
            for ordinal, block in matched_blocks
        ],
        "bridge_needed": answer_cov >= 0.45 and question_cov < 0.25 and bool(question_anchors),
        "text": combined_text,
        "direct_reference_verification": True,
        "reference_document_block_count": len(matched_blocks),
    }


def _candidate_matches_reference(candidate: dict[str, Any], value: str) -> bool:
    file_path = str(candidate.get("file_path") or "")
    text = str(candidate.get("text") or "")
    stem = Path(file_path).stem
    return value == stem or value in file_path or f"PASSAGE_ID: {value}" in text or f"corpus/{value}" in text


def _read_claims(path: Path) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            claims.append(payload)
    return claims


def _rate(count: int, total: int) -> float:
    return round(float(count) / max(1, int(total)), 4)
