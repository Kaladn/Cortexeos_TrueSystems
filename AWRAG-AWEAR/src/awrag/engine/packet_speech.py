from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from awrag.engine.anchors import anchorize
from awrag.engine.evidence_formula import build_topk_pressure_trellis
from awrag.nlp_resolver import best_sentence


SCHEMA = "awrag_packet_speech_run@0"
EVIDENCE_SCHEMA = "awrag_packet_speech_evidence_trace@0"
PRETTY_SCHEMA = "awrag_packet_speech_pretty_answer@0"
RANK_KEY_ORDER = ["direct_hit_count desc", "density_score desc", "score desc", "block_ordinal asc"]
METADATA_PREFIX_RE = re.compile(r"^[A-Z0-9_ -]{2,40}:\s*")


@dataclass(frozen=True)
class ArtifactState:
    path: str
    exists: bool
    size: int
    sha256: str | None
    modified_ns: int | None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aw_packet_speech",
        description="Report-only AW packet speech. Reads existing query JSON and writes separate evidence/pretty outputs.",
    )
    parser.add_argument("--packet", action="append", type=Path, required=True, help="Existing AWEAR query result JSON. Repeatable.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = run_packet_speech(packet_paths=args.packet, out_dir=args.out)
    print(json.dumps(result, ensure_ascii=True))


def run_packet_speech(*, packet_paths: list[Path], out_dir: Path) -> dict[str, Any]:
    if not packet_paths:
        raise ValueError("at least one packet path is required")
    packet_paths = [Path(path).expanduser().resolve() for path in packet_paths]
    missing = [str(path) for path in packet_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"packet files missing: {missing}")

    before = _artifact_states(packet_paths)
    out_dir.mkdir(parents=True, exist_ok=True)
    for child in ("per_case", "evidence_trace", "pretty_answer", "receipts"):
        (out_dir / child).mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for index, packet_path in enumerate(packet_paths, start=1):
        packet = _read_json(packet_path)
        record = build_packet_speech_record(packet=packet, packet_path=packet_path, index=index)
        records.append(record)
        case_id = record["case_id"]
        _write_json(out_dir / "per_case" / f"{case_id}_packet_speech.json", record)
        _write_markdown(out_dir / "per_case" / f"{case_id}_packet_speech.md", record)
        _write_json(out_dir / "evidence_trace" / f"{case_id}_evidence_trace.json", record["evidence_trace"])
        _write_json(out_dir / "pretty_answer" / f"{case_id}_pretty_answer.json", record["pretty_answer"])
        _write_pretty_markdown(out_dir / "pretty_answer" / f"{case_id}_pretty_answer.md", record)

    after = _artifact_states(packet_paths)
    no_mutation = _compare_artifact_states(before, after)
    form_counts: dict[str, int] = {}
    for record in records:
        form = str(record["pretty_answer"].get("selected_answer_form"))
        form_counts[form] = form_counts.get(form, 0) + 1

    summary = {
        "schema": SCHEMA,
        "records_processed": len(records),
        "output_dir": str(out_dir),
        "selected_answer_form_counts": form_counts,
        "separate_evidence_trace_files": True,
        "separate_pretty_answer_files": True,
        "retrieval_ran": False,
        "topk_ran": False,
        "intake_ran": False,
        "model_used": "none",
        "model_may_search": False,
        "backend_mutation": False,
        "input_mutation_detected": no_mutation["mutation_detected"],
        "records": [
            {
                "case_id": record["case_id"],
                "source_packet_path": record["source_packet_path"],
                "selected_answer_form": record["pretty_answer"].get("selected_answer_form"),
                "citation_count": len(record["evidence_trace"].get("citations", [])),
            }
            for record in records
        ],
    }

    _write_json(out_dir / "AW_PACKET_SPEECH_SUMMARY.json", summary)
    _write_summary_markdown(out_dir / "AW_PACKET_SPEECH_SUMMARY.md", summary)
    _write_json(out_dir / "receipts" / "run_receipt.json", {
        "schema": "awrag_packet_speech_run_receipt@0",
        "records_processed": len(records),
        "retrieval_ran": False,
        "topk_ran": False,
        "intake_ran": False,
        "answering_ran": False,
        "model_used": "none",
        "model_may_search": False,
        "backend_mutation": False,
        "separate_evidence_trace_files": True,
        "separate_pretty_answer_files": True,
    })
    _write_json(out_dir / "receipts" / "inputs_receipt.json", {
        "schema": "awrag_packet_speech_inputs_receipt@0",
        "packet_paths": [str(path) for path in packet_paths],
        "before": [state.__dict__ for state in before],
        "after": [state.__dict__ for state in after],
    })
    _write_json(out_dir / "receipts" / "no_mutation_receipt.json", no_mutation)
    return summary


def build_packet_speech_record(*, packet: dict[str, Any], packet_path: Path, index: int) -> dict[str, Any]:
    question = str(packet.get("question") or "").strip()
    question_anchors = [str(anchor) for anchor in packet.get("question_anchors") or anchorize(question)]
    answer_packet = dict(packet.get("answer_packet") or {})
    final_answer = dict(packet.get("final_answer") or {})
    locations = [dict(row) for row in answer_packet.get("locations") or []]
    qualification = dict(answer_packet.get("qualification") or {})
    citations = [_citation_record(location) for location in locations if location.get("citation")]
    qualification_receipts = [dict(row) for row in answer_packet.get("qualification_receipts") or []]
    document_answer = _document_only_answer(question=question, locations=locations)
    speech_trellis = _speech_output_trellis(question_anchors=question_anchors, locations=locations)
    support = _support_metrics(
        question_anchors=question_anchors,
        locations=locations,
        qualification=qualification,
        qualification_receipts=qualification_receipts,
    )
    selected_form, form_reasons = _select_answer_form(
        final_answer=final_answer,
        qualification=qualification,
        locations=locations,
        support=support,
        document_answer=document_answer,
    )
    pretty_text = _render_pretty_answer(
        selected_form=selected_form,
        document_answer=document_answer,
        citations=citations,
        form_reasons=form_reasons,
        location_count=len(locations),
        speech_trellis=speech_trellis,
    )
    case_id = _case_id(packet=packet, packet_path=packet_path, index=index)
    start_message_id = _first_metadata_value(locations, "CHAT_MESSAGE_ID")
    end_message_id = _last_metadata_value(locations, "CHAT_MESSAGE_ID")

    evidence_trace = {
        "schema": EVIDENCE_SCHEMA,
        "case_id": case_id,
        "source_packet_path": str(packet_path),
        "question": question,
        "question_anchors": question_anchors,
        "model_used": str(packet.get("model_used") or final_answer.get("model_used") or "none"),
        "model_may_search": bool(packet.get("model_may_search", final_answer.get("model_may_search", False))),
        "answer_packet_instruction": answer_packet.get("instruction"),
        "citations_owned_by": answer_packet.get("citations_owned_by"),
        "qualification": qualification,
        "qualification_receipts": qualification_receipts,
        "final_answer_status": final_answer.get("status"),
        "rank_key_order": RANK_KEY_ORDER,
        "support_metrics": support,
        "speech_output_trellis": speech_trellis,
        "citations": citations,
        "locations": [_location_trace(location) for location in locations],
        "rejected_locations": answer_packet.get("rejected_locations") or [],
        "receipt": {
            "retrieval_ran": False,
            "topk_ran": False,
            "intake_ran": False,
            "model_used": "none",
            "model_may_search": False,
            "evidence_authority": "awrag_locked_packet",
        },
    }
    pretty_answer = {
        "schema": PRETTY_SCHEMA,
        "case_id": case_id,
        "source_packet_path": str(packet_path),
        "question": question,
        "selected_answer_form": selected_form,
        "answer": pretty_text,
        "document_only_answer": document_answer,
        "speech_output_trellis": _pretty_trellis_summary(speech_trellis),
        "citations": [row["citation"] for row in citations],
        "rank_key_summary": [_rank_key_summary(location) for location in locations],
        "support_reasons": form_reasons,
        "start_message_id": start_message_id,
        "end_message_id": end_message_id,
        "model_used": "none",
        "model_may_search": False,
        "evidence_trace_file_required": True,
    }
    return {
        "schema": "awrag_packet_speech_case@0",
        "case_id": case_id,
        "source_packet_path": str(packet_path),
        "evidence_trace": evidence_trace,
        "pretty_answer": pretty_answer,
    }


def _select_answer_form(
    *,
    final_answer: dict[str, Any],
    qualification: dict[str, Any],
    locations: list[dict[str, Any]],
    support: dict[str, Any],
    document_answer: str,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    final_status = str(final_answer.get("status") or "")
    support_state = str(qualification.get("support_state") or "")
    if support_state == "no_qualified_evidence" or final_status == "not_enough_information" or not locations:
        reasons.append("no qualified cited locations were admitted")
        return "NO_SUPPORT_FOUND", reasons
    if not document_answer:
        reasons.append("cited locations exist but no readable cited sentence was found")
        return "HUMAN_REVIEW", reasons

    coverage = float(support.get("question_anchor_coverage", 0.0))
    required_coverage = float(support.get("qualification_required_term_coverage", 0.0))
    max_direct = int(support.get("max_direct_hit_count", 0))
    missing_values = list(support.get("missing_value_anchors") or [])
    required_terms = list(support.get("qualification_required_terms") or [])
    missing_required_terms = list(support.get("qualification_missing_terms") or [])
    if required_terms and required_coverage >= 0.80 and not missing_values:
        reasons.append("AW qualification receipts cover the required question terms")
        return "SUPPORTED_CLAIM", reasons
    if required_terms and missing_required_terms:
        reasons.append("AW qualification receipts are missing required question terms")
        return "RELATED_BUT_UNSUPPORTED", reasons
    if coverage < 0.34 or max_direct == 0:
        reasons.append("low question-anchor coverage in admitted cited locations")
        return "WEAK_GENERIC_EVIDENCE", reasons
    if missing_values:
        reasons.append("numeric/value anchors from the question are missing in admitted cited locations")
        return "RELATED_BUT_UNSUPPORTED", reasons
    if coverage < 0.60:
        reasons.append("partial question-anchor coverage only")
        return "RELATED_BUT_UNSUPPORTED", reasons
    reasons.append("cited locations carry sufficient question-anchor coverage")
    return "SUPPORTED_CLAIM", reasons


def _support_metrics(
    *,
    question_anchors: list[str],
    locations: list[dict[str, Any]],
    qualification: dict[str, Any],
    qualification_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    wanted = _unique(question_anchors)
    matched: set[str] = set()
    direct: set[str] = set()
    max_direct = 0
    for location in locations:
        direct_rows = {str(anchor) for anchor in location.get("direct_matched_anchors") or []}
        matched_rows = {str(anchor) for anchor in location.get("matched_anchors") or []}
        text_anchors = set(anchorize(str(location.get("text") or "")))
        direct.update(direct_rows)
        matched.update(matched_rows)
        matched.update(anchor for anchor in wanted if anchor in text_anchors)
        max_direct = max(max_direct, int(location.get("direct_hit_count") or 0))
    covered = [anchor for anchor in wanted if anchor in matched or anchor in direct]
    missing = [anchor for anchor in wanted if anchor not in covered]
    value_anchors = [anchor for anchor in wanted if any(ch.isdigit() for ch in anchor)]
    missing_values = [anchor for anchor in value_anchors if anchor not in covered]
    required_terms = [str(anchor) for anchor in qualification.get("required_terms") or []]
    qualified_covered = _unique(
        str(anchor)
        for receipt in qualification_receipts
        if receipt.get("qualified") is True
        for anchor in receipt.get("covered_terms") or []
    )
    qualified_missing = [
        anchor for anchor in required_terms
        if anchor not in set(qualified_covered)
    ]
    required_coverage = len([anchor for anchor in required_terms if anchor in set(qualified_covered)]) / max(1, len(required_terms))
    wider_context = [
        {
            "citation": location.get("citation"),
            "role": "verification_context",
            "used_for_answer_text": index == 0,
            "may_extend_answer": index > 0 and bool(set(location.get("direct_matched_anchors") or []) & set(required_terms)),
        }
        for index, location in enumerate(locations[:5])
    ]
    return {
        "question_anchor_count": len(wanted),
        "covered_question_anchors": covered,
        "missing_question_anchors": missing,
        "value_anchors": value_anchors,
        "missing_value_anchors": missing_values,
        "question_anchor_coverage": round(len(covered) / max(1, len(wanted)), 4),
        "max_direct_hit_count": max_direct,
        "qualification_required_terms": required_terms,
        "qualification_covered_terms": qualified_covered,
        "qualification_missing_terms": qualified_missing,
        "qualification_required_term_coverage": round(required_coverage, 4),
        "wider_context_policy": "verification_only_unless_additional_required_terms_are_supported",
        "wider_context": wider_context,
    }


def _document_only_answer(*, question: str, locations: list[dict[str, Any]]) -> str:
    question_terms = {anchor: 1 for anchor in anchorize(question)}
    candidates: list[str] = []
    for location in locations[:3]:
        text = _document_text(str(location.get("text") or ""))
        sentence = best_sentence(text, question_terms) if text else ""
        sentence = _clean_sentence(sentence)
        if sentence:
            candidates.append(sentence)
    return candidates[0] if candidates else ""


def _render_pretty_answer(
    *,
    selected_form: str,
    document_answer: str,
    citations: list[dict[str, Any]],
    form_reasons: list[str],
    location_count: int,
    speech_trellis: dict[str, Any],
) -> str:
    cite_text = _citation_text(citations)
    reason_text = "; ".join(form_reasons) if form_reasons else "no additional support note"
    selected_path = _selected_path_text(speech_trellis)
    if selected_form == "NO_SUPPORT_FOUND":
        return (
            "AW cannot support this from the admitted evidence packet. "
            f"Qualified cited locations: {location_count}. Reason: {reason_text}."
        )
    if selected_form == "WEAK_GENERIC_EVIDENCE":
        return (
            "AW found cited text, but the evidence is too generic to state the answer cleanly. "
            f"Selected speech path: {selected_path}. Document-only cited text: {document_answer} "
            f"Citations: {cite_text}. Reason: {reason_text}."
        )
    if selected_form == "RELATED_BUT_UNSUPPORTED":
        return (
            "AW found related cited evidence, but the packet does not support the full claim cleanly. "
            f"Selected speech path: {selected_path}. Document-only cited text: {document_answer} "
            f"Citations: {cite_text}. Reason: {reason_text}."
        )
    if selected_form == "SUPPORTED_CLAIM":
        return (
            f"AW supports this from the cited packet. Selected speech path: {selected_path}. "
            f"{document_answer} Citations: {cite_text}."
        )
    return (
        "Human review is required before turning this packet into a stronger answer. "
        f"Selected speech path: {selected_path}. Document-only cited text: {document_answer} "
        f"Citations: {cite_text}. Reason: {reason_text}."
    )


def _speech_output_trellis(*, question_anchors: list[str], locations: list[dict[str, Any]]) -> dict[str, Any]:
    positions: list[list[dict[str, Any]]] = []
    for location_index, location in enumerate(locations[:6], start=1):
        anchors = _unique(
            [str(anchor) for anchor in location.get("direct_matched_anchors") or []]
            + [str(anchor) for anchor in location.get("matched_anchors") or []]
            + anchorize(str(location.get("text") or ""))[:6]
        )[:6]
        if not anchors:
            continue
        direct = {str(anchor) for anchor in location.get("direct_matched_anchors") or []}
        location_candidates: list[dict[str, Any]] = []
        for rank, anchor in enumerate(anchors, start=1):
            location_candidates.append(
                {
                    "anchor": anchor,
                    "rank": rank,
                    "admitted": True,
                    "source_supported": bool(location.get("citation")),
                    "question_pressure": 1.0 if anchor in set(question_anchors) else 0.25,
                    "anchor_support_strength": 1.0 if anchor in direct else 0.5,
                    "citation_support_strength": 1.0 if location.get("citation") else 0.0,
                    "packet_admission_strength": 1.0,
                    "position_need_fit": max(0.0, 1.0 - ((rank - 1) * 0.1)),
                    "citation": location.get("citation"),
                    "source_location_index": location_index,
                }
            )
        positions.append(location_candidates)
    return build_topk_pressure_trellis(
        positions,
        question_anchors=question_anchors,
        future_window=6,
    )


def _pretty_trellis_summary(trellis: dict[str, Any]) -> dict[str, Any]:
    path = trellis.get("chosen_path") or []
    return {
        "role": trellis.get("role"),
        "chosen_anchors": [row.get("anchor") for row in path],
        "chosen_ranks": [row.get("rank") for row in path],
        "receipt": trellis.get("receipt"),
    }


def _selected_path_text(trellis: dict[str, Any]) -> str:
    anchors = [str(row.get("anchor")) for row in trellis.get("chosen_path") or [] if row.get("anchor")]
    return " -> ".join(anchors) if anchors else "none"


def _citation_record(location: dict[str, Any]) -> dict[str, Any]:
    return {
        "citation": str(location.get("citation") or ""),
        "file_path": location.get("file_path"),
        "line_start": location.get("line_start"),
        "line_end": location.get("line_end"),
        "score": location.get("score"),
        "density_score": location.get("density_score"),
        "direct_hit_count": location.get("direct_hit_count"),
        "block_anchor_count": location.get("block_anchor_count"),
        "message_id": _metadata_value(str(location.get("text") or ""), "CHAT_MESSAGE_ID"),
        "conversation_id": _metadata_value(str(location.get("text") or ""), "CHAT_CONVERSATION_ID"),
    }


def _location_trace(location: dict[str, Any]) -> dict[str, Any]:
    return {
        "citation": location.get("citation"),
        "file_path": location.get("file_path"),
        "line_start": location.get("line_start"),
        "line_end": location.get("line_end"),
        "rank_key": _rank_key_summary(location),
        "direct_matched_anchors": location.get("direct_matched_anchors") or [],
        "matched_anchors": location.get("matched_anchors") or [],
        "qualification": location.get("qualification"),
        "text": location.get("text"),
    }


def _rank_key_summary(location: dict[str, Any]) -> dict[str, Any]:
    return {
        "direct_hit_count": location.get("direct_hit_count"),
        "density_score": location.get("density_score"),
        "score": location.get("score"),
        "block_ordinal": location.get("block_ordinal"),
        "rank_key_order": RANK_KEY_ORDER,
    }


def _document_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("SCIFACT_DOC_ID:", "NFCORPUS_DOC_ID:", "CHAT_CONVERSATION_ID:", "CHAT_MESSAGE_ID:")):
            continue
        if line.startswith("TEXT:"):
            lines.append(line.split(":", 1)[1].strip())
            continue
        if METADATA_PREFIX_RE.match(line) and len(line) < 120:
            continue
        lines.append(line)
    return " ".join(lines).strip()


def _metadata_value(text: str, key: str) -> str | None:
    prefix = f"{key}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            value = line.split(":", 1)[1].strip()
            return value or None
    return None


def _first_metadata_value(locations: list[dict[str, Any]], key: str) -> str | None:
    for location in locations:
        value = _metadata_value(str(location.get("text") or ""), key)
        if value:
            return value
    return None


def _last_metadata_value(locations: list[dict[str, Any]], key: str) -> str | None:
    out: str | None = None
    for location in locations:
        value = _metadata_value(str(location.get("text") or ""), key)
        if value:
            out = value
    return out


def _citation_text(citations: list[dict[str, Any]]) -> str:
    values = [str(row.get("citation")) for row in citations if row.get("citation")]
    return ", ".join(_unique(values)) if values else "none"


def _clean_sentence(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _case_id(*, packet: dict[str, Any], packet_path: Path, index: int) -> str:
    question = str(packet.get("question") or packet_path.stem)
    digest = hashlib.sha1(f"{packet_path}|{question}|{index}".encode("utf-8")).hexdigest()[:10]
    return f"packet_{index:04d}_{digest}"


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
        "schema": "awrag_packet_speech_no_mutation_receipt@0",
        "mutation_detected": bool(changes),
        "checked_input_files": len(before),
        "changes": changes,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _write_markdown(path: Path, record: dict[str, Any]) -> None:
    pretty = record["pretty_answer"]
    evidence = record["evidence_trace"]
    lines = [
        f"# AW Packet Speech {record['case_id']}",
        "",
        f"Question: {pretty.get('question')}",
        f"Answer form: {pretty.get('selected_answer_form')}",
        f"Model used: {pretty.get('model_used')}",
        f"Model may search: {pretty.get('model_may_search')}",
        "",
        "## Pretty Answer",
        str(pretty.get("answer") or ""),
        "",
        "## Evidence Trace",
        f"Citation count: {len(evidence.get('citations', []))}",
        f"Rank key: {', '.join(RANK_KEY_ORDER)}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_pretty_markdown(path: Path, record: dict[str, Any]) -> None:
    pretty = record["pretty_answer"]
    lines = [
        f"# Pretty Answer {record['case_id']}",
        "",
        f"Form: {pretty.get('selected_answer_form')}",
        "",
        str(pretty.get("answer") or ""),
        "",
        "## Citations",
    ]
    citations = pretty.get("citations") or []
    lines.extend(f"- {citation}" for citation in citations) if citations else lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# AW Packet Speech Summary",
        "",
        f"Records processed: {summary.get('records_processed')}",
        f"Retrieval ran: {summary.get('retrieval_ran')}",
        f"TopK ran: {summary.get('topk_ran')}",
        f"Intake ran: {summary.get('intake_ran')}",
        f"Model used: {summary.get('model_used')}",
        f"Model may search: {summary.get('model_may_search')}",
        f"Input mutation detected: {summary.get('input_mutation_detected')}",
        "",
        "## Forms",
    ]
    for form, count in sorted((summary.get("selected_answer_form_counts") or {}).items()):
        lines.append(f"- {form}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
