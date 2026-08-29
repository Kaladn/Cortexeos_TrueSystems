from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .base import utc_now, with_protected_notice, write_json
from .evidence_formula import score_evidence_formula
from .legal_anchor_typing import typed_anchor_summary


def run_topk_diagnostic(
    *,
    packet_paths: list[str | Path] | None = None,
    batch_summary_path: str | Path | None = None,
    out_dir: str | Path,
    max_rank: int = 5,
) -> dict[str, Any]:
    packets = _load_packets(packet_paths=packet_paths or [], batch_summary_path=batch_summary_path)
    walk = build_rank_layer_walk(packets, max_rank=max_rank)
    result = write_topk_ladder_outputs(walk, out_dir)
    result["packet_count"] = len(packets)
    result["packet_paths"] = [str(path) for path in _packet_paths(packet_paths or [], batch_summary_path)]
    result["batch_summary_path"] = str(Path(batch_summary_path).expanduser().resolve()) if batch_summary_path else None
    return result


def build_topk_diagnostic_packet(packet: dict[str, Any], *, max_rank: int = 5) -> dict[str, Any]:
    question = _packet_question(packet)
    answer_packet = packet.get("answer_packet") if isinstance(packet.get("answer_packet"), dict) else packet
    locations = _candidate_locations(answer_packet)
    question_anchors = _classify_question_anchors(question)
    rows: list[dict[str, Any]] = []
    bundle_counter: Counter[str] = Counter()

    for index, candidate in enumerate(locations or [], start=1):
        if index > max_rank:
            break
        location = candidate["location"]
        if not isinstance(location, dict):
            continue
        text = _location_text(location)
        evidence_anchors = _classify_evidence_anchors(text)
        cross_classification = _cross_classify(question_anchors, evidence_anchors)
        bridge_status = _bridge_status(question_anchors, evidence_anchors)
        local_recount = dict(Counter(evidence_anchors["all_anchors"]).most_common(25))
        formula_row = {
            "question_evidence_cross_classification": cross_classification,
            "bridge_conflict_gap_status": bridge_status,
            "local_recount": local_recount,
            "citation": location.get("citation"),
        }
        bundle_counter.update(evidence_anchors["all_anchors"])
        rows.append(
            {
                "rank": int(location.get("rank") or index),
                "source_candidate_lane": candidate["lane"],
                "citation": location.get("citation"),
                "coordinates": location.get("coordinates"),
                "source_support_state": _source_support_state(location),
                "original_passage": text,
                "evidence_anchor_classification": evidence_anchors,
                "question_evidence_cross_classification": cross_classification,
                "topk_speech_answer": _rank_speech(location, evidence_anchors),
                "local_recount": local_recount,
                "bridge_conflict_gap_status": bridge_status,
                "evidence_formula_score": score_evidence_formula(formula_row),
            }
        )

    return {
        "schema": "truemem_topk_diagnostic_packet@1",
        "diagnostic_mode": "no_refusal",
        "truth_status": "diagnostic_not_final_truth",
        "question": question,
        "question_anchor_classification": question_anchors,
        "topk_results": rows,
        "topk_bundle_recount": dict(bundle_counter.most_common(50)),
        "receipt": {
            "no_refusal": True,
            "no_ranking_mutation": True,
            "no_dataset_mutation": True,
            "no_answer_key_leakage": True,
            "diagnostic_only": True,
        },
    }


def build_rank_layer_walk(packets: list[dict[str, Any]], *, max_rank: int = 5) -> dict[str, Any]:
    diagnostics = [build_topk_diagnostic_packet(packet, max_rank=max_rank) for packet in packets]
    layers: dict[int, list[dict[str, Any]]] = {rank: [] for rank in range(1, max_rank + 1)}
    for question_index, diagnostic in enumerate(diagnostics, start=1):
        question = diagnostic["question"]
        starter = _answer_starter_with_subject(diagnostic["question_anchor_classification"])
        for row in diagnostic["topk_results"]:
            rank = int(row["rank"])
            if 1 <= rank <= max_rank:
                layers[rank].append(
                    {
                        "question_index": question_index,
                        "question": question,
                        "answer_starter_with_subject": starter,
                        **row,
                    }
                )
    return {
        "schema": "truemem_topk_ladder_walk@1",
        "created_at": utc_now(),
        "walk_order": "rank_layer_across_questions",
        "max_rank": max_rank,
        "diagnostic_packets": diagnostics,
        "layers": layers,
        "receipt": {
            "no_refusal": True,
            "no_dataset_mutation": True,
            "no_ranking_mutation": True,
            "no_retrieval": True,
            "diagnostic_only": True,
        },
    }


def write_topk_ladder_outputs(walk: dict[str, Any], out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir).expanduser().resolve()
    layer_dir = out / "rank_layers"
    layer_dir.mkdir(parents=True, exist_ok=True)
    packets_path = out / "TOPK_DIAGNOSTIC_PACKETS.jsonl"
    _write_jsonl(packets_path, walk.get("diagnostic_packets") or [])
    layer_paths: dict[str, str] = {}
    for rank, rows in (walk.get("layers") or {}).items():
        path = layer_dir / f"TOPK_LAYER_{rank}.jsonl"
        _write_jsonl(path, rows)
        layer_paths[str(rank)] = str(path)

    summary = with_protected_notice(
        {
            "schema": "truemem_topk_ladder_summary@1",
            "created_at": utc_now(),
            "out_dir": str(out),
            "diagnostic_packet_path": str(packets_path),
            "rank_layer_paths": layer_paths,
            "question_count": len(walk.get("diagnostic_packets") or []),
            "max_rank": walk.get("max_rank"),
            "walk_order": walk.get("walk_order"),
            "receipt": walk.get("receipt"),
        }
    )
    summary_path = out / "TOPK_LADDER_SUMMARY.json"
    write_json(summary_path, summary)
    write_json(out / "RUN_RECEIPT.json", summary)
    _write_summary_markdown(out / "TOPK_LADDER_SUMMARY.md", summary)
    summary["summary_path"] = str(summary_path)
    return summary


def _classify_question_anchors(question: str) -> dict[str, Any]:
    typed = typed_anchor_summary(question)
    anchors = typed["all_anchors"]
    return {
        "all_anchors": anchors,
        "typed_anchors": typed["typed_anchors"],
        "proof_needs": typed["proof_needs"],
        "scenario_anchors": [],
        "evidence_bearing_anchors": anchors,
        "ambiguity_anchors": [],
    }


def _classify_evidence_anchors(text: str) -> dict[str, Any]:
    typed = typed_anchor_summary(text)
    anchors = typed["all_anchors"]
    return {
        "all_anchors": anchors,
        "typed_anchors": typed["typed_anchors"],
        "proof_needs": typed["proof_needs"],
        "evidence_anchors": anchors,
        "weak_anchors": [],
    }


def _cross_classify(question_anchors: dict[str, Any], evidence_anchors: dict[str, Any]) -> dict[str, Any]:
    q = set(question_anchors.get("all_anchors") or [])
    e = set(evidence_anchors.get("all_anchors") or [])
    return {
        "matched_anchors": sorted(q & e),
        "missing_question_anchors": sorted(q - e),
        "extra_evidence_anchors": sorted(e - q),
    }


def _bridge_status(question_anchors: dict[str, Any], evidence_anchors: dict[str, Any]) -> dict[str, Any]:
    cross = _cross_classify(question_anchors, evidence_anchors)
    matched = len(cross["matched_anchors"])
    missing = len(cross["missing_question_anchors"])
    status = "bridge_possible" if matched and missing else "direct_overlap" if matched else "gap"
    return {"status": status, "matched_count": matched, "missing_count": missing, "conflict_count": 0}


def _rank_speech(location: dict[str, Any], evidence_anchors: dict[str, Any]) -> dict[str, Any]:
    citation = location.get("citation") or "uncited"
    dominant = ", ".join((evidence_anchors.get("all_anchors") or [])[:8])
    return {
        "mode": "topk_rank_attempt",
        "answer": f"Rank evidence at {citation} points to: {dominant}",
        "warning": "diagnostic speech from one TopK slice; not final truth",
    }


def _answer_starter_with_subject(classification: dict[str, Any]) -> str:
    anchors = classification.get("evidence_bearing_anchors") or classification.get("all_anchors") or []
    subject = str(anchors[0]) if anchors else "the question"
    return f"For {subject}, the cited evidence starts from"


def _packet_question(packet: dict[str, Any]) -> str:
    return str(packet.get("question") or packet.get("input_question") or packet.get("original_question") or "")


def _candidate_locations(answer_packet: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(answer_packet, dict):
        return []
    rows: list[dict[str, Any]] = []
    for lane in ("locations", "rejected_locations"):
        for location in answer_packet.get(lane) or []:
            if isinstance(location, dict):
                rows.append({"lane": lane, "location": location})
    return rows


def _location_text(location: dict[str, Any]) -> str:
    return str(location.get("text") or location.get("passage") or location.get("snippet") or "")


def _source_support_state(location: dict[str, Any]) -> str | None:
    qualification = location.get("qualification") if isinstance(location.get("qualification"), dict) else {}
    state = qualification.get("support_state")
    return str(state) if state is not None else None


def _load_packets(*, packet_paths: list[str | Path], batch_summary_path: str | Path | None) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for path in _packet_paths(packet_paths, batch_summary_path):
        packets.append(_read_json(path))
    return packets


def _packet_paths(packet_paths: list[str | Path], batch_summary_path: str | Path | None) -> list[Path]:
    paths = [Path(path).expanduser().resolve() for path in packet_paths]
    if batch_summary_path:
        batch_path = Path(batch_summary_path).expanduser().resolve()
        batch = _read_json(batch_path)
        for row in batch.get("question_results") or []:
            if isinstance(row, dict):
                for key in ("output_path", "packet_path", "query_output_path"):
                    if row.get(key):
                        paths.append(Path(str(row[key])).expanduser().resolve())
        for path in batch.get("output_paths") or []:
            paths.append(Path(str(path)).expanduser().resolve())
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(with_protected_notice(row), ensure_ascii=True, sort_keys=True) + "\n")


def _write_summary_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# TopK Ladder Diagnostic Summary",
        "",
        f"Created: {summary.get('created_at')}",
        f"Question count: {summary.get('question_count')}",
        f"Max rank: {summary.get('max_rank')}",
        f"Walk order: {summary.get('walk_order')}",
        "",
        "## Receipts",
        "",
        "- No refusal: true",
        "- No retrieval: true",
        "- No ranking mutation: true",
        "- No dataset mutation: true",
        "- Diagnostic only: true",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
