from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from awrag.engine.anchors import anchorize
from awrag.engine.base import sha1_text, utc_now, with_protected_notice, write_json


SCHEMA = "awrag_evidence_cloud_speech_run@0"
CASE_SCHEMA = "awrag_evidence_cloud_speech_case@0"
TRACE_SCHEMA = "awrag_evidence_cloud_speech_trace@0"
PRETTY_SCHEMA = "awrag_evidence_cloud_speech_pretty_answer@0"
SENTENCE_RE = re.compile(r"[^.!?\n]+(?:[.!?]|$)")
METADATA_PREFIX_RE = re.compile(r"^[A-Z0-9_ -]{2,40}:\s*")


@dataclass(frozen=True)
class ArtifactState:
    path: str
    exists: bool
    size: int
    sha256: str | None
    modified_ns: int | None


def run_evidence_cloud_speech(
    *,
    packet_path: str | Path,
    question: str | None = None,
    out_dir: str | Path,
    max_passes: int = 1,
    operator_stepped: bool = True,
) -> dict[str, Any]:
    """Compress an existing top-K evidence packet into a citation-bound answer.

    This is a report/tool lane. It reads one existing AWEAR query packet,
    builds a temporary in-memory micro-map from admitted evidence locations
    only, and renders a step result. By default it is operator-stepped: one
    boil-down pass proves itself, then the operator chooses stop, continue,
    widen, or reject. It does not run dataset search, mutate counts, train, or
    write dataset state.
    """

    packet = Path(packet_path).expanduser().resolve()
    if not packet.exists():
        raise FileNotFoundError(f"packet not found: {packet}")
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    for child in ("per_case", "evidence_trace", "pretty_answer", "receipts"):
        (out / child).mkdir(parents=True, exist_ok=True)

    before = _artifact_states([packet])
    payload = _read_json(packet)
    effective_question = str(question or payload.get("question") or "").strip()
    if not effective_question:
        raise ValueError("question is required when the packet has no question")

    record = build_evidence_cloud_speech_record(
        packet=payload,
        packet_path=packet,
        question=effective_question,
        max_passes=max_passes,
        operator_stepped=operator_stepped,
    )
    case_id = str(record["case_id"])
    write_json(out / "per_case" / f"{case_id}_evidence_cloud_speech.json", record)
    _write_case_markdown(out / "per_case" / f"{case_id}_evidence_cloud_speech.md", record)
    write_json(out / "evidence_trace" / f"{case_id}_evidence_cloud_trace.json", record["evidence_trace"])
    write_json(out / "pretty_answer" / f"{case_id}_pretty_answer.json", record["pretty_answer"])
    _write_pretty_markdown(out / "pretty_answer" / f"{case_id}_pretty_answer.md", record)

    after = _artifact_states([packet])
    no_mutation = _compare_artifact_states(before, after)
    write_json(out / "receipts" / "no_mutation_receipt.json", no_mutation)
    write_json(out / "receipts" / "inputs_receipt.json", {
        "schema": "awrag_evidence_cloud_speech_inputs_receipt@0",
        "packet_path": str(packet),
        "question_source": "operator_override" if question else "packet_question",
        "before": [state.__dict__ for state in before],
        "after": [state.__dict__ for state in after],
    })
    run_receipt = {
        "schema": "awrag_evidence_cloud_speech_run_receipt@0",
        "created_at": utc_now(),
        "packet_path": str(packet),
        "output_dir": str(out),
        "retrieval_ran": False,
        "topk_ran": False,
        "intake_ran": False,
        "dataset_mutation": False,
        "model_used": "none",
        "model_may_search": False,
        "temporary_micro_map_only": True,
        "source": "top_k_evidence_packet",
        "operator_stepped": bool(operator_stepped),
        "requires_operator_approval_for_next_pass": bool(operator_stepped),
        "trace_path": str(out / "evidence_trace" / f"{case_id}_evidence_cloud_trace.json"),
        "pretty_answer_path": str(out / "pretty_answer" / f"{case_id}_pretty_answer.md"),
    }
    write_json(out / "receipts" / "run_receipt.json", run_receipt)

    summary = {
        "schema": SCHEMA,
        "records_processed": 1,
        "output_dir": str(out),
        "case_id": case_id,
        "question": effective_question,
        "answer": record["pretty_answer"].get("answer"),
        "support_level": record["pretty_answer"].get("support_level"),
        "citations": record["pretty_answer"].get("citations"),
        "passes": record["evidence_trace"].get("passes"),
        "stable": record["evidence_trace"].get("stable"),
        "operator_stepped": bool(operator_stepped),
        "next_action_required": record["evidence_trace"].get("next_action_required"),
        "retrieval_ran": False,
        "topk_ran": False,
        "intake_ran": False,
        "dataset_mutation": False,
        "input_mutation_detected": no_mutation["mutation_detected"],
        "model_used": "none",
        "model_may_search": False,
        "trace_path": run_receipt["trace_path"],
        "pretty_answer_path": run_receipt["pretty_answer_path"],
        "run_receipt_path": str(out / "receipts" / "run_receipt.json"),
        "no_mutation_receipt_path": str(out / "receipts" / "no_mutation_receipt.json"),
    }
    write_json(out / "EVIDENCE_CLOUD_SPEECH_SUMMARY.json", summary)
    _write_summary_markdown(out / "EVIDENCE_CLOUD_SPEECH_SUMMARY.md", summary)
    return with_protected_notice(summary)


def build_evidence_cloud_speech_record(
    *,
    packet: dict[str, Any],
    packet_path: Path,
    question: str,
    max_passes: int,
    operator_stepped: bool,
) -> dict[str, Any]:
    question_anchors = [str(anchor) for anchor in packet.get("question_anchors") or anchorize(question)]
    blocks = _evidence_blocks(packet)
    cloud = {
        "question": question,
        "question_anchors": question_anchors,
        "source_packet_path": str(packet_path),
        "blocks": blocks,
    }

    passes: list[dict[str, Any]] = []
    previous_zone_id: str | None = None
    final_result: dict[str, Any] | None = None
    stable = False
    current_blocks = blocks
    requested_max_passes = max(1, int(max_passes))
    max_passes = 1 if operator_stepped else requested_max_passes

    for pass_index in range(max_passes):
        micro_map = _build_micro_map(current_blocks)
        result = _micro_search(
            question=question,
            question_anchors=question_anchors,
            blocks=current_blocks,
            micro_map=micro_map,
            pass_index=pass_index,
        )
        passes.append({
            "pass": pass_index,
            "step_proved": True,
            "block_count": len(current_blocks),
            "sentence_zone_count": result["sentence_zone_count"],
            "winner": result["winner"],
            "support_score": result["support_score"],
            "support_level": result["support_level"],
            "micro_map_summary": micro_map["summary"],
        })
        final_result = result
        winner = result["winner"]
        zone_id = str(winner.get("zone_id") or "")
        if zone_id and zone_id == previous_zone_id:
            stable = True
            break
        previous_zone_id = zone_id
        current_blocks = _narrow_blocks(current_blocks, winner)
        if len(current_blocks) == 1 and pass_index > 0:
            stable = True
            break

    if final_result is None:
        final_result = _empty_result(question=question)

    answer_text = _render_answer_from_final_zone(final_result)
    citations = _final_citations(final_result)
    case_id = _case_id(packet_path=packet_path, question=question)
    comparison = _step_comparison(passes)
    next_action = _next_action_required(
        operator_stepped=operator_stepped,
        requested_max_passes=requested_max_passes,
        passes=passes,
        stable=stable,
        final_result=final_result,
    )
    trace = {
        "schema": TRACE_SCHEMA,
        "case_id": case_id,
        "created_at": utc_now(),
        "source_packet_path": str(packet_path),
        "question": question,
        "question_anchors": question_anchors,
        "source": "top_k_evidence_packet",
        "mode": "evidence_cloud_boil_down",
        "operator_stepped": bool(operator_stepped),
        "evidence_block_count": len(blocks),
        "temporary_micro_map_only": True,
        "retrieval_ran": False,
        "topk_ran": False,
        "intake_ran": False,
        "model_used": "none",
        "model_may_search": False,
        "passes": passes,
        "step_comparison": comparison,
        "stable": stable,
        "next_action_required": next_action,
        "allowed_next_actions": ["stop", "continue", "widen", "reject"],
        "final_result": final_result,
        "citation_policy": {
            "speech_from_final_zone_only": True,
            "citations_from_source_packet_locations": True,
            "full_document_wandering": False,
        },
    }
    pretty = {
        "schema": PRETTY_SCHEMA,
        "case_id": case_id,
        "source_packet_path": str(packet_path),
        "question": question,
        "answer": answer_text,
        "support_level": final_result.get("support_level"),
        "final_blocks": _final_blocks(final_result),
        "citations": citations,
        "receipt": {
            "mode": "evidence_cloud_boil_down",
            "passes": len(passes),
            "stable": stable,
            "mutated_dataset": False,
            "source": "top_k_evidence_packet",
            "temporary_micro_map_only": True,
            "operator_stepped": bool(operator_stepped),
            "next_action_required": next_action,
            "model_used": "none",
            "model_may_search": False,
        },
    }
    return {
        "schema": CASE_SCHEMA,
        "case_id": case_id,
        "source_packet_path": str(packet_path),
        "evidence_cloud": {
            "question": question,
            "block_count": len(blocks),
            "source_packet_id": str(packet.get("output_path") or packet_path),
        },
        "evidence_trace": trace,
        "pretty_answer": pretty,
    }


def _evidence_blocks(packet: dict[str, Any]) -> list[dict[str, Any]]:
    answer_packet = packet.get("answer_packet") if isinstance(packet.get("answer_packet"), dict) else {}
    locations = list(answer_packet.get("locations") or [])
    blocks: list[dict[str, Any]] = []
    for index, location in enumerate(locations):
        if not isinstance(location, dict):
            continue
        raw_text = str(location.get("text") or "")
        text = _document_text(raw_text)
        if not text:
            continue
        block_id = str(location.get("block_id") or location.get("block_ordinal") or index)
        blocks.append({
            "doc_id": _doc_id(location, raw_text),
            "block_id": block_id,
            "block_index": index,
            "text": text,
            "citation": location.get("citation"),
            "score": _float(location.get("score")),
            "density_score": _float(location.get("density_score")),
            "direct_hit_count": int(location.get("direct_hit_count") or 0),
            "anchors": anchorize(text),
            "coordinates": {
                "file_path": location.get("file_path"),
                "line_start": location.get("line_start"),
                "line_end": location.get("line_end"),
                "block_ordinal": location.get("block_ordinal"),
            },
            "source_location": {
                key: location.get(key)
                for key in (
                    "citation",
                    "file_path",
                    "line_start",
                    "line_end",
                    "score",
                    "density_score",
                    "direct_hit_count",
                    "block_anchor_count",
                    "block_ordinal",
                )
            },
        })
    return blocks


def _build_micro_map(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    local_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str, int]] = Counter()
    block_refs: dict[str, list[str]] = {}
    local_symbols: dict[str, str] = {}
    for block in blocks:
        anchors = [str(anchor) for anchor in block.get("anchors") or []]
        block_id = str(block.get("block_id"))
        for index, anchor in enumerate(anchors):
            local_counts[anchor] += 1
            local_symbols.setdefault(anchor, f"local:{len(local_symbols):06d}")
            block_refs.setdefault(anchor, []).append(block_id)
            for next_index in range(index + 1, min(len(anchors), index + 7)):
                offset = next_index - index
                pair_counts[(anchor, anchors[next_index], offset)] += 1
    top_counts = [
        {"anchor": anchor, "count": count}
        for anchor, count in local_counts.most_common(20)
    ]
    top_paths = [
        {"left": left, "right": right, "offset": offset, "count": count}
        for (left, right, offset), count in pair_counts.most_common(20)
    ]
    return {
        "local_symbols": local_symbols,
        "local_counts": dict(local_counts),
        "local_anchor_paths": {
            f"{left}|{right}|{offset}": count
            for (left, right, offset), count in pair_counts.items()
        },
        "block_refs": block_refs,
        "summary": {
            "block_count": len(blocks),
            "unique_anchor_count": len(local_counts),
            "anchor_observation_count": sum(local_counts.values()),
            "local_path_count": len(pair_counts),
            "top_counts": top_counts,
            "top_paths": top_paths,
        },
    }


def _micro_search(
    *,
    question: str,
    question_anchors: list[str],
    blocks: list[dict[str, Any]],
    micro_map: dict[str, Any],
    pass_index: int,
) -> dict[str, Any]:
    zones = _sentence_zones(blocks)
    if not zones:
        return _empty_result(question=question)
    wanted = _unique(question_anchors)
    ranked: list[dict[str, Any]] = []
    for zone in zones:
        anchors = [str(anchor) for anchor in zone.get("anchors") or []]
        direct = [anchor for anchor in wanted if anchor in set(anchors)]
        relation_pressure = _relation_pressure(wanted, anchors, micro_map)
        native_packet_score = _float(zone.get("packet_score"))
        density = _float(zone.get("packet_density_score"))
        direct_hit_count = int(zone.get("packet_direct_hit_count") or 0)
        coverage = len(direct) / max(1, len(wanted))
        support_score = (
            (len(direct) * 100.0)
            + (coverage * 80.0)
            + min(relation_pressure, 1000.0) * 0.05
            + direct_hit_count * 10.0
            + density
            + native_packet_score * 0.01
        )
        ranked.append({
            **zone,
            "matched_question_anchors": direct,
            "missing_question_anchors": [anchor for anchor in wanted if anchor not in set(direct)],
            "question_anchor_coverage": round(coverage, 4),
            "relation_pressure": relation_pressure,
            "support_score": round(support_score, 4),
            "score_components": {
                "direct_question_anchor_count": len(direct),
                "question_anchor_coverage": round(coverage, 4),
                "micro_relation_pressure": relation_pressure,
                "packet_direct_hit_count": direct_hit_count,
                "packet_density_score": density,
                "packet_score": native_packet_score,
                "score_kind": "temporary_micro_map_score_not_native_topk",
            },
        })
    ranked.sort(
        key=lambda row: (
            -float(row["support_score"]),
            -int(row["score_components"]["direct_question_anchor_count"]),
            -float(row["question_anchor_coverage"]),
            int(row["block_index"]),
            int(row["sentence_index"]),
        )
    )
    winner = ranked[0]
    support_level = _support_level(winner)
    return {
        "pass": pass_index,
        "question": question,
        "sentence_zone_count": len(zones),
        "winner": winner,
        "top_zones": ranked[:5],
        "support_score": winner["support_score"],
        "support_level": support_level,
        "search_policy": {
            "searched_only_packet_evidence_cloud": True,
            "full_document_wandering": False,
            "temporary_micro_map_only": True,
            "next_pass_requires_operator_approval": True,
        },
    }


def _step_comparison(passes: list[dict[str, Any]]) -> dict[str, Any]:
    if not passes:
        return {
            "changed_from_previous": False,
            "drift_flag": False,
            "support_delta": 0.0,
            "note": "no passes were run",
        }
    if len(passes) == 1:
        return {
            "changed_from_previous": False,
            "drift_flag": False,
            "support_delta": 0.0,
            "note": "first proved step; no previous step to compare",
        }
    previous = passes[-2]
    current = passes[-1]
    previous_winner = str((previous.get("winner") or {}).get("zone_id") or "")
    current_winner = str((current.get("winner") or {}).get("zone_id") or "")
    previous_score = float(previous.get("support_score") or 0.0)
    current_score = float(current.get("support_score") or 0.0)
    delta = round(current_score - previous_score, 4)
    return {
        "changed_from_previous": previous_winner != current_winner,
        "drift_flag": previous_winner != current_winner and delta < 0,
        "support_delta": delta,
        "previous_winner": previous_winner,
        "current_winner": current_winner,
    }


def _next_action_required(
    *,
    operator_stepped: bool,
    requested_max_passes: int,
    passes: list[dict[str, Any]],
    stable: bool,
    final_result: dict[str, Any],
) -> str:
    if not operator_stepped:
        if stable:
            return "stop_or_review_stable_result"
        if len(passes) >= requested_max_passes:
            return "stop_or_review_max_passes_reached"
        return "auto_passes_complete"
    support = str(final_result.get("support_level") or "insufficient")
    if support == "insufficient":
        return "operator_decide_stop_widen_or_reject"
    if stable:
        return "operator_decide_stop_or_accept_stable_result"
    return "operator_decide_stop_continue_widen_or_reject"


def _sentence_zones(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    for block in blocks:
        text = str(block.get("text") or "")
        sentences = [match.group(0).strip() for match in SENTENCE_RE.finditer(text)]
        sentences = [sentence for sentence in sentences if sentence]
        if not sentences and text:
            sentences = [text]
        for sentence_index, sentence in enumerate(sentences):
            block_index = int(block.get("block_index") or 0)
            block_id = str(block.get("block_id"))
            zone_id = f"{block_id}:{sentence_index}"
            zones.append({
                "zone_id": zone_id,
                "block_id": block_id,
                "block_index": block_index,
                "sentence_index": sentence_index,
                "text": " ".join(sentence.split()),
                "anchors": anchorize(sentence),
                "citation": block.get("citation"),
                "doc_id": block.get("doc_id"),
                "coordinates": block.get("coordinates"),
                "packet_score": block.get("score"),
                "packet_density_score": block.get("density_score"),
                "packet_direct_hit_count": block.get("direct_hit_count"),
            })
    return zones


def _relation_pressure(question_anchors: list[str], zone_anchors: list[str], micro_map: dict[str, Any]) -> int:
    paths = micro_map.get("local_anchor_paths") if isinstance(micro_map.get("local_anchor_paths"), dict) else {}
    pressure = 0
    zone_set = set(zone_anchors)
    for left in question_anchors:
        for right in zone_set:
            for offset in range(1, 7):
                pressure += int(paths.get(f"{left}|{right}|{offset}", 0))
                pressure += int(paths.get(f"{right}|{left}|{offset}", 0))
    return pressure


def _narrow_blocks(blocks: list[dict[str, Any]], winner: dict[str, Any]) -> list[dict[str, Any]]:
    block_id = str(winner.get("block_id") or "")
    narrowed = [block for block in blocks if str(block.get("block_id")) == block_id]
    return narrowed or blocks


def _render_answer_from_final_zone(final_result: dict[str, Any]) -> str:
    winner = final_result.get("winner") if isinstance(final_result.get("winner"), dict) else {}
    support_level = str(final_result.get("support_level") or "insufficient")
    citation = str(winner.get("citation") or "").strip()
    text = " ".join(str(winner.get("text") or "").split()).strip()
    if not text:
        return "The available evidence is insufficient to form an answer from the evidence cloud."
    if support_level == "insufficient":
        return (
            "The available evidence is partial and does not directly support a stronger answer. "
            f"Closest final evidence zone: {text} {citation}".strip()
        )
    if support_level == "partial":
        return f"The evidence cloud partially supports this answer: {text} {citation}".strip()
    return f"The final evidence zone supports this answer: {text} {citation}".strip()


def _support_level(result: dict[str, Any]) -> str:
    winner = result.get("winner") if isinstance(result.get("winner"), dict) else result
    coverage = float(winner.get("question_anchor_coverage") or 0.0)
    direct_count = int((winner.get("score_components") or {}).get("direct_question_anchor_count") or 0)
    if direct_count >= 3 and coverage >= 0.5:
        return "strong"
    if direct_count >= 2 and coverage >= 0.25:
        return "partial"
    return "insufficient"


def _final_citations(final_result: dict[str, Any]) -> list[dict[str, Any]]:
    winner = final_result.get("winner") if isinstance(final_result.get("winner"), dict) else {}
    citation = winner.get("citation")
    if not citation:
        return []
    return [{
        "doc_id": winner.get("doc_id"),
        "block_id": winner.get("block_id"),
        "citation": citation,
        "coordinates": winner.get("coordinates"),
        "jump": _jump(winner),
    }]


def _final_blocks(final_result: dict[str, Any]) -> list[dict[str, Any]]:
    winner = final_result.get("winner") if isinstance(final_result.get("winner"), dict) else {}
    if not winner:
        return []
    return [{
        "doc_id": winner.get("doc_id"),
        "block_id": winner.get("block_id"),
        "citation": winner.get("citation"),
        "coordinates": winner.get("coordinates"),
        "support_score": winner.get("support_score"),
        "support_level": final_result.get("support_level"),
    }]


def _empty_result(*, question: str) -> dict[str, Any]:
    return {
        "question": question,
        "sentence_zone_count": 0,
        "winner": {},
        "top_zones": [],
        "support_score": 0.0,
        "support_level": "insufficient",
        "search_policy": {
            "searched_only_packet_evidence_cloud": True,
            "full_document_wandering": False,
            "temporary_micro_map_only": True,
        },
    }


def _doc_id(location: dict[str, Any], text: str) -> str | None:
    for key in ("doc_id", "source_doc_id", "document_id"):
        if location.get(key):
            return str(location.get(key))
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("SCIFACT_DOC_ID:", "NFCORPUS_DOC_ID:", "DOC_ID:")):
            return stripped.split(":", 1)[1].strip() or None
    return None


def _document_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("SCIFACT_DOC_ID:", "NFCORPUS_DOC_ID:", "DOC_ID:", "CHAT_CONVERSATION_ID:", "CHAT_MESSAGE_ID:")):
            continue
        if line.startswith("TEXT:"):
            lines.append(line.split(":", 1)[1].strip())
            continue
        if METADATA_PREFIX_RE.match(line) and len(line) < 120:
            continue
        lines.append(line)
    return " ".join(lines).strip()


def _jump(winner: dict[str, Any]) -> str | None:
    doc_id = winner.get("doc_id")
    block_id = winner.get("block_id")
    if doc_id is None or block_id is None:
        return None
    return f"doc://{doc_id}#block-{block_id}"


def _case_id(*, packet_path: Path, question: str) -> str:
    digest = hashlib.sha1(f"{packet_path}|{question}".encode("utf-8")).hexdigest()[:10]
    return f"evidence_cloud_{digest}"


def _float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_states(paths: list[Path]) -> list[ArtifactState]:
    states: list[ArtifactState] = []
    for path in paths:
        stat = path.stat() if path.exists() else None
        states.append(ArtifactState(
            path=str(path),
            exists=path.exists(),
            size=int(stat.st_size) if stat else 0,
            sha256=_sha256_file(path) if stat else None,
            modified_ns=int(stat.st_mtime_ns) if stat else None,
        ))
    return states


def _compare_artifact_states(before: list[ArtifactState], after: list[ArtifactState]) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    before_by_path = {row.path: row for row in before}
    for row in after:
        old = before_by_path.get(row.path)
        if old is None:
            changes.append({"path": row.path, "reason": "new_input_path_after_run"})
            continue
        for key in ("exists", "size", "sha256", "modified_ns"):
            if getattr(old, key) != getattr(row, key):
                changes.append({"path": row.path, "field": key, "before": getattr(old, key), "after": getattr(row, key)})
    return {
        "schema": "awrag_evidence_cloud_speech_no_mutation_receipt@0",
        "mutation_detected": bool(changes),
        "checked_input_files": len(before),
        "changes": changes,
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"packet must contain a JSON object: {path}")
    return payload


def _write_case_markdown(path: Path, record: dict[str, Any]) -> None:
    pretty = record["pretty_answer"]
    trace = record["evidence_trace"]
    lines = [
        f"# Evidence Cloud Speech {record['case_id']}",
        "",
        f"Question: {pretty.get('question')}",
        f"Support level: {pretty.get('support_level')}",
        f"Stable: {trace.get('stable')}",
        "",
        "## Answer",
        str(pretty.get("answer") or ""),
        "",
        "## Citations",
    ]
    citations = pretty.get("citations") or []
    lines.extend(f"- {row.get('citation')} {row.get('jump') or ''}".strip() for row in citations) if citations else lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_pretty_markdown(path: Path, record: dict[str, Any]) -> None:
    pretty = record["pretty_answer"]
    lines = [
        f"# Pretty Answer {record['case_id']}",
        "",
        f"Support: {pretty.get('support_level')}",
        "",
        str(pretty.get("answer") or ""),
        "",
        "## Citations",
    ]
    citations = pretty.get("citations") or []
    lines.extend(f"- {row.get('citation')} {row.get('jump') or ''}".strip() for row in citations) if citations else lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Evidence Cloud Speech Summary",
        "",
        f"Records processed: {summary.get('records_processed')}",
        f"Support level: {summary.get('support_level')}",
        f"Stable: {summary.get('stable')}",
        f"Retrieval ran: {summary.get('retrieval_ran')}",
        f"TopK ran: {summary.get('topk_ran')}",
        f"Intake ran: {summary.get('intake_ran')}",
        f"Dataset mutation: {summary.get('dataset_mutation')}",
        f"Model used: {summary.get('model_used')}",
        f"Input mutation detected: {summary.get('input_mutation_detected')}",
        "",
        "## Answer",
        str(summary.get("answer") or ""),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
