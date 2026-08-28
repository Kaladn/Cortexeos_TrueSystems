from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Iterable

from .base import DatasetPaths, dataset_paths, safe_id, sha1_text, utc_now, with_protected_notice


def append_query_record(paths: DatasetPaths, query_result: dict[str, Any]) -> dict[str, Any]:
    """Append one dataset-local work-ledger row for a dataset question."""

    paths.qa.mkdir(parents=True, exist_ok=True)
    timestamp = utc_now()
    question = str(query_result.get("question") or "")
    normalized = normalize_question(question)
    final_answer = query_result.get("final_answer") if isinstance(query_result.get("final_answer"), dict) else {}
    answer_packet = query_result.get("answer_packet") if isinstance(query_result.get("answer_packet"), dict) else {}
    locations = answer_packet.get("locations") if isinstance(answer_packet, dict) else []
    if not isinstance(locations, list):
        locations = []

    record_id = f"QA-{sha1_text(f'{timestamp}|{question}')[:16]}"
    receipt_path = str(query_result.get("output_path") or "")
    record = with_protected_notice({
        "schema": "awrag_dataset_qa_record@1",
        "record_id": record_id,
        "timestamp": timestamp,
        "dataset_id": str(query_result.get("dataset_id") or paths.root.name),
        "question": question,
        "normalized_question": normalized,
        "answer": str(final_answer.get("text") or ""),
        "answer_status": str(final_answer.get("status") or ""),
        "evidence_trace": receipt_path,
        "citations": [str(location.get("citation")) for location in locations if location.get("citation")],
        "coordinates": [_coordinate_pointer(location) for location in locations],
        "receipt": receipt_path,
        "unsupported_or_refused": _is_unsupported_or_refused(query_result),
        "no_mutation": True,
        "counts_mutated": False,
        "raw_source_copied": False,
        "model_used": str(query_result.get("model_used") or final_answer.get("model_used") or "none"),
        "model_may_search": bool(query_result.get("model_may_search", final_answer.get("model_may_search", False))),
        "prior_same_question": _prior_same_question(paths.qa_ledger_path, normalized),
    })
    _append_jsonl(paths.qa_ledger_path, record)
    return {
        "schema": "awrag_dataset_qa_append_result@1",
        "record_id": record_id,
        "qa_ledger_path": str(paths.qa_ledger_path),
        "prior_same_question": record["prior_same_question"],
        "no_mutation": True,
    }


def recent_questions(runtime_root: str | Path, dataset_id: str, *, limit: int = 10) -> dict[str, Any]:
    paths = dataset_paths(runtime_root, dataset_id)
    rows = list(read_qa_rows(paths.qa_ledger_path))
    return with_protected_notice({
        "schema": "awrag_dataset_qa_recent@1",
        "dataset_id": safe_id(dataset_id),
        "qa_ledger_path": str(paths.qa_ledger_path),
        "limit": int(limit),
        "total_records": len(rows),
        "records": rows[-max(0, int(limit)):],
        "no_mutation": True,
    })


def show_record(runtime_root: str | Path, dataset_id: str, record_id: str) -> dict[str, Any]:
    paths = dataset_paths(runtime_root, dataset_id)
    for row in read_qa_rows(paths.qa_ledger_path):
        if str(row.get("record_id")) == str(record_id):
            return with_protected_notice({
                "schema": "awrag_dataset_qa_record_lookup@1",
                "dataset_id": safe_id(dataset_id),
                "record": row,
                "found": True,
                "no_mutation": True,
            })
    return with_protected_notice({
        "schema": "awrag_dataset_qa_record_lookup@1",
        "dataset_id": safe_id(dataset_id),
        "record_id": record_id,
        "found": False,
        "no_mutation": True,
    })


def export_ledger(runtime_root: str | Path, dataset_id: str, output: str | Path) -> dict[str, Any]:
    paths = dataset_paths(runtime_root, dataset_id)
    target = Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if paths.qa_ledger_path.exists():
        shutil.copyfile(paths.qa_ledger_path, target)
    else:
        target.write_text("", encoding="utf-8")
    return with_protected_notice({
        "schema": "awrag_dataset_qa_export@1",
        "dataset_id": safe_id(dataset_id),
        "qa_ledger_path": str(paths.qa_ledger_path),
        "export_path": str(target),
        "record_count": jsonl_count(target),
        "no_mutation": True,
    })


def read_qa_rows(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def normalize_question(question: str) -> str:
    return " ".join(str(question or "").casefold().split())


def jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _prior_same_question(path: Path, normalized_question: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for row in read_qa_rows(path):
        if str(row.get("normalized_question") or "") != normalized_question:
            continue
        matches.append({
            "record_id": row.get("record_id"),
            "timestamp": row.get("timestamp"),
            "receipt": row.get("receipt"),
            "answer_status": row.get("answer_status"),
        })
    return matches


def _coordinate_pointer(location: dict[str, Any]) -> dict[str, Any]:
    return {
        "citation": location.get("citation"),
        "file_path": location.get("file_path"),
        "line_start": location.get("line_start"),
        "line_end": location.get("line_end"),
        "block_ordinal": location.get("block_ordinal"),
        "block_id": location.get("block_id"),
        "rank_key": {
            "direct_hit_count": location.get("direct_hit_count"),
            "density_score": location.get("density_score"),
            "score": location.get("score"),
        },
    }


def _is_unsupported_or_refused(query_result: dict[str, Any]) -> bool:
    final_answer = query_result.get("final_answer") if isinstance(query_result.get("final_answer"), dict) else {}
    answer_packet = query_result.get("answer_packet") if isinstance(query_result.get("answer_packet"), dict) else {}
    qualification = answer_packet.get("qualification") if isinstance(answer_packet, dict) else {}
    status = str(final_answer.get("status") or "")
    support_state = str(qualification.get("support_state") or "")
    return status in {"not_enough_information", "dataset_cloud_mismatch"} or support_state in {
        "no_qualified_evidence",
        "dataset_cloud_mismatch",
    }


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")
