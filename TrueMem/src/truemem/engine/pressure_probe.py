from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .anchors import anchorize
from .base import sha1_text, utc_now, with_protected_notice, write_json


SCHEMA = "truemem_pressure_probe_run@0"
QUESTION_SCHEMA = "truemem_pressure_probe_question@0"
RECEIPT_SCHEMA = "truemem_pressure_probe_run_receipt@0"
TMCIT_RE = re.compile(r"\[?TMCIT-[0-9A-Za-z]+\]?", re.IGNORECASE)
PUNCT_RE = re.compile(r"[^0-9A-Za-z_]+")
PRESSURE_META_TERMS = {
    "a", "about", "admitted", "appear", "appears", "around", "bridge",
    "change", "cited", "clarifies", "clarify", "condition", "conditions",
    "connect", "do", "does", "evidence", "exception", "exceptions", "in", "near",
    "nearby", "or", "passage", "rule", "say", "scenario", "term", "terms", "the",
    "to", "what",
}


@dataclass(frozen=True)
class ArtifactState:
    path: str
    exists: bool
    size: int
    sha256: str | None
    modified_ns: int | None


def run_pressure_probe(
    *,
    out_dir: str | Path,
    packet_paths: list[str | Path] | None = None,
    batch_summary_path: str | Path | None = None,
    max_questions_per_packet: int = 5,
) -> dict[str, Any]:
    """Build bounded second-layer pressure questions from existing packets.

    This is a sidecar lane. It reads admitted TrueMem evidence packets and writes
    pressure probe questions with source citations. It does not run retrieval,
    topK, intake, ranking changes, speech, or answer generation.
    """

    packets = _resolve_packet_paths(packet_paths=packet_paths, batch_summary_path=batch_summary_path)
    if not packets:
        raise ValueError("pressure-probe requires at least one --packet or a batch summary with packet outputs")

    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    for child in ("questions", "per_packet", "receipts"):
        (out / child).mkdir(parents=True, exist_ok=True)

    before = _artifact_states(packets)
    records: list[dict[str, Any]] = []
    question_rows: list[dict[str, Any]] = []
    for packet_path in packets:
        packet = _read_json(packet_path)
        record = build_pressure_probe_record(
            packet=packet,
            packet_path=packet_path,
            max_questions=max_questions_per_packet,
            starting_index=len(question_rows) + 1,
        )
        records.append(record)
        question_rows.extend(record["probe_questions"])
        write_json(out / "per_packet" / f"{record['case_id']}_pressure_probe.json", record)

    questions_jsonl = out / "questions" / "PRESSURE_PROBE_QUESTIONS.jsonl"
    hypotheses_jsonl = out / "questions" / "PRESSURE_HYPOTHESES.jsonl"
    _write_jsonl(questions_jsonl, question_rows)
    _write_jsonl(hypotheses_jsonl, question_rows)
    after = _artifact_states(packets)
    no_mutation = _compare_artifact_states(before, after)
    write_json(out / "receipts" / "no_mutation_receipt.json", no_mutation)

    run_receipt = {
        "schema": RECEIPT_SCHEMA,
        "created_at": utc_now(),
        "source": "existing_truemem_query_packets",
        "batch_summary_path": str(Path(batch_summary_path).expanduser().resolve()) if batch_summary_path else None,
        "packet_paths": [str(path) for path in packets],
        "output_dir": str(out),
        "questions_jsonl_path": str(questions_jsonl),
        "hypotheses_jsonl_path": str(hypotheses_jsonl),
        "records_processed": len(records),
        "probe_question_count": len(question_rows),
        "max_questions_per_packet": int(max_questions_per_packet),
        "sidecar_only": True,
        "retrieval_ran": False,
        "topk_ran": False,
        "intake_ran": False,
        "ranking_mutation": False,
        "dataset_mutation": False,
        "speech_generation_ran": False,
        "no_answer_generation": True,
        "no_answer_key_leakage": True,
        "no_raw_document_guessing": True,
        "model_used": "none",
        "model_may_search": False,
        "input_mutation_detected": bool(no_mutation["mutation_detected"]),
    }
    write_json(out / "receipts" / "run_receipt.json", run_receipt)

    summary = {
        "schema": SCHEMA,
        "created_at": utc_now(),
        "records_processed": len(records),
        "probe_question_count": len(question_rows),
        "batch_summary_path": run_receipt["batch_summary_path"],
        "output_dir": str(out),
        "summary_path": str(out / "PRESSURE_PROBE_SUMMARY.json"),
        "questions_jsonl_path": str(questions_jsonl),
        "hypotheses_jsonl_path": str(hypotheses_jsonl),
        "run_receipt_path": str(out / "receipts" / "run_receipt.json"),
        "no_mutation_receipt_path": str(out / "receipts" / "no_mutation_receipt.json"),
        "sidecar_only": True,
        "retrieval_ran": False,
        "topk_ran": False,
        "intake_ran": False,
        "ranking_mutation": False,
        "dataset_mutation": False,
        "speech_generation_ran": False,
        "model_used": "none",
        "model_may_search": False,
        "input_mutation_detected": bool(no_mutation["mutation_detected"]),
        "records": [
            {
                "case_id": record["case_id"],
                "packet_path": record["packet_path"],
                "question": record["question"],
                "probe_question_count": len(record["probe_questions"]),
                "citations": record["citations"],
            }
            for record in records
        ],
    }
    write_json(out / "PRESSURE_PROBE_SUMMARY.json", summary)
    _write_summary_markdown(out / "PRESSURE_PROBE_SUMMARY.md", summary)
    return with_protected_notice(summary)


def build_pressure_probe_record(
    *,
    packet: dict[str, Any],
    packet_path: Path,
    max_questions: int,
    starting_index: int = 1,
) -> dict[str, Any]:
    question = str(packet.get("question") or "").strip()
    answer_packet = packet.get("answer_packet") if isinstance(packet.get("answer_packet"), dict) else {}
    locations = [row for row in answer_packet.get("locations") or [] if isinstance(row, dict)]
    rejected = [row for row in answer_packet.get("rejected_locations") or [] if isinstance(row, dict)]
    case_id = _case_id(packet_path=packet_path, question=question)

    probe_rows: list[dict[str, Any]] = []
    seen_questions: set[str] = set()
    limit = max(0, int(max_questions))
    for location_index, location in enumerate(locations, start=1):
        for template in _probe_templates_for_location(location):
            if len(probe_rows) >= limit:
                break
            probe_question = " ".join(str(template["question"]).split())
            normalized = probe_question.casefold()
            if not probe_question or normalized in seen_questions:
                continue
            seen_questions.add(normalized)
            probe_rows.append({
                "schema": QUESTION_SCHEMA,
                "probe_index": starting_index + len(probe_rows),
                "case_id": case_id,
                "source_packet_path": str(packet_path),
                "source_question": question,
                "source_location_index": location_index,
                "source_citation": str(location.get("citation") or ""),
                "source_file_path": str(location.get("file_path") or ""),
                "source_line_start": location.get("line_start"),
                "source_line_end": location.get("line_end"),
                "source_block_ordinal": location.get("block_ordinal"),
                "probe_type": template["probe_type"],
                "pressure_reason": template["pressure_reason"],
                "question": probe_question,
                "clean_question": template.get("clean_question") or clean_pressure_hypothesis_question(probe_question),
                "source_evidence_anchors": template["source_evidence_anchors"],
                "missing_evidence_terms": template["missing_evidence_terms"],
                "missing_scenario_terms": template["missing_scenario_terms"],
                "bounded_depth": 1,
                "run_back_through": "truemem batch/query only; this sidecar does not run retrieval",
                "boundaries": {
                    "no_answer_generation": True,
                    "no_answer_key_leakage": True,
                    "no_raw_document_guessing": True,
                    "no_ranking_mutation": True,
                },
            })
        if len(probe_rows) >= limit:
            break

    return {
        "schema": "truemem_pressure_probe_case@0",
        "case_id": case_id,
        "packet_path": str(packet_path),
        "question": question,
        "support_state": (answer_packet.get("qualification") or {}).get("support_state"),
        "location_count": len(locations),
        "rejected_location_count": len(rejected),
        "pressure_candidate_count": _pressure_candidate_count(locations, rejected),
        "citations": [str(row.get("citation")) for row in locations if row.get("citation")],
        "probe_questions": probe_rows,
        "receipts": {
            "sidecar_only": True,
            "source": "admitted_packet_locations",
            "rejected_locations_read_for_context_only": True,
            "retrieval_ran": False,
            "topk_ran": False,
            "intake_ran": False,
            "ranking_mutation": False,
            "dataset_mutation": False,
            "no_answer_generation": True,
            "no_answer_key_leakage": True,
            "no_raw_document_guessing": True,
        },
    }


def clean_pressure_hypothesis_question(question: str) -> str:
    """Remove probe operator words from the query surface.

    The original pressure question remains in metadata. This cleaned form is
    only for rerunning misses where meta words such as cited/connect/nearby
    polluted retrieval and proof coverage.
    """

    without_citations = TMCIT_RE.sub(" ", str(question))
    terms = [
        term
        for term in PUNCT_RE.sub(" ", without_citations).casefold().split()
        if term and term not in PRESSURE_META_TERMS
    ]
    return " ".join(terms)


def _probe_templates_for_location(location: dict[str, Any]) -> list[dict[str, Any]]:
    qualification = location.get("qualification") if isinstance(location.get("qualification"), dict) else {}
    evidence_terms = _stable_terms(qualification.get("matched_evidence_terms") or anchorize(str(location.get("text") or "")), limit=6)
    missing_evidence = _stable_terms(qualification.get("missing_evidence_terms") or [], limit=4)
    missing_scenario = _stable_terms(qualification.get("missing_scenario_terms") or [], limit=4)
    citation = str(location.get("citation") or "the cited evidence")
    anchor_phrase = _join_terms(evidence_terms[:3]) or "the admitted cited evidence"
    anchor_clean_question = " ".join(evidence_terms[:5])
    templates = [
        {
            "probe_type": "evidence_support_pressure",
            "pressure_reason": "back up admitted evidence anchors from the cited location",
            "question": f"What does {citation} say about {anchor_phrase}?",
        },
    ]
    if missing_scenario:
        templates.append({
            "probe_type": "scenario_gap_pressure",
            "pressure_reason": "test story-wrapper gap without treating scenario terms as proof burden",
            "question": f"Do the scenario terms {_join_terms(missing_scenario)} change the cited rule about {anchor_phrase}?",
        })
    if missing_evidence:
        templates.append({
            "probe_type": "missing_evidence_bridge",
            "pressure_reason": "test whether admitted evidence can bridge a missing evidence-bearing term",
            "question": f"Does the cited evidence connect {anchor_phrase} to {_join_terms(missing_evidence)}?",
            "clean_question": anchor_clean_question,
        })
    templates.extend([
        {
            "probe_type": "local_condition_pressure",
            "pressure_reason": "look for conditions, exceptions, or limits near the admitted evidence",
            "question": f"What conditions or exceptions appear near {anchor_phrase} in {citation}?",
        },
        {
            "probe_type": "citation_neighborhood_pressure",
            "pressure_reason": "ask for same-citation/local-neighborhood clarification without changing ranking",
            "question": f"What nearby cited passage clarifies {anchor_phrase} around {citation}?",
        },
    ])
    return [
        {
            **template,
            "source_evidence_anchors": evidence_terms,
            "missing_evidence_terms": missing_evidence,
            "missing_scenario_terms": missing_scenario,
        }
        for template in templates
    ]


def _resolve_packet_paths(
    *,
    packet_paths: list[str | Path] | None,
    batch_summary_path: str | Path | None,
) -> list[Path]:
    resolved: list[Path] = []
    for packet in packet_paths or []:
        path = Path(packet).expanduser().resolve()
        if path not in resolved:
            resolved.append(path)
    if batch_summary_path:
        batch_path = Path(batch_summary_path).expanduser().resolve()
        batch = _read_json(batch_path)
        for row in batch.get("question_results") or []:
            if isinstance(row, dict) and row.get("status") == "completed" and row.get("output_path"):
                path = Path(str(row["output_path"])).expanduser().resolve()
                if path not in resolved:
                    resolved.append(path)
        for output_path in batch.get("output_paths") or []:
            path = Path(str(output_path)).expanduser().resolve()
            if path not in resolved:
                resolved.append(path)
    for path in resolved:
        if not path.exists():
            raise FileNotFoundError(f"packet not found: {path}")
    return resolved


def _pressure_candidate_count(locations: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> int:
    count = 0
    for row in [*locations, *rejected]:
        qualification = row.get("qualification") if isinstance(row.get("qualification"), dict) else {}
        values = {
            str(qualification.get("pressure_decision") or ""),
            str(qualification.get("candidate_status_before_pressure") or ""),
        }
        if any("pressure" in value or "promote" in value for value in values):
            count += 1
    return count


def _stable_terms(values: Any, *, limit: int) -> list[str]:
    terms: list[str] = []
    for value in values if isinstance(values, list) else []:
        term = str(value).strip().casefold()
        if term and term not in terms:
            terms.append(term)
    return terms[:limit]


def _join_terms(terms: list[str]) -> str:
    if not terms:
        return ""
    if len(terms) == 1:
        return terms[0]
    return ", ".join(terms[:-1]) + f", {terms[-1]}"


def _case_id(*, packet_path: Path, question: str) -> str:
    return f"pressure_probe_{sha1_text(str(packet_path) + question)[:12]}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def _artifact_states(paths: list[Path]) -> list[ArtifactState]:
    return [_artifact_state(path) for path in paths]


def _artifact_state(path: Path) -> ArtifactState:
    if not path.exists():
        return ArtifactState(str(path), False, 0, None, None)
    stat = path.stat()
    return ArtifactState(
        path=str(path),
        exists=True,
        size=int(stat.st_size),
        sha256=_sha256_file(path),
        modified_ns=int(stat.st_mtime_ns),
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compare_artifact_states(before: list[ArtifactState], after: list[ArtifactState]) -> dict[str, Any]:
    before_rows = [state.__dict__ for state in before]
    after_rows = [state.__dict__ for state in after]
    return {
        "schema": "truemem_pressure_probe_no_mutation_receipt@0",
        "before": before_rows,
        "after": after_rows,
        "mutation_detected": before_rows != after_rows,
    }


def _write_summary_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# TrueMem Pressure Probe Summary",
        "",
        f"Records processed: {summary['records_processed']}",
        f"Probe questions: {summary['probe_question_count']}",
        f"Questions JSONL: {summary['questions_jsonl_path']}",
        f"Pressure hypotheses JSONL: {summary['hypotheses_jsonl_path']}",
        "",
        "Receipts:",
        "- Sidecar only: true",
        "- Retrieval ran: false",
        "- TopK ran: false",
        "- Intake ran: false",
        "- Ranking mutation: false",
        "- Dataset mutation: false",
        "- Answer generation: false",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
