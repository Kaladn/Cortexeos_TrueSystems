from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .base import dataset_paths, safe_id, unique_stamp, utc_now, with_protected_notice, write_json
from .querying import direct_question_query_baseline
from .storage import ensure_dataset, status


def determinism_receipt(
    runtime_root: str | Path,
    dataset_id: str,
    *,
    questions: list[str] | None = None,
    questions_path: str | Path | None = None,
    top_k: int = 5,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build a twin-machine comparison receipt without changing engine scoring."""
    paths = dataset_paths(runtime_root, dataset_id)
    ensure_dataset(runtime_root, dataset_id)
    question_rows = load_receipt_questions(questions=questions, questions_path=questions_path)
    query_rows = [
        query_receipt(runtime_root, dataset_id, question_text, top_k=top_k)
        for question_text in question_rows
    ]
    receipt = with_protected_notice({
        "schema": "truemem_twin_machine_determinism_receipt@1",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "purpose": "Compare same code, same data, same command across machines before comparing final wording.",
        "repo": repo_receipt(),
        "runtime": {
            "runtime_root": str(Path(runtime_root).expanduser().resolve()),
            "dataset_root": str(paths.root),
            "status": status(runtime_root, dataset_id),
        },
        "dataset_artifacts": dataset_artifact_hashes(paths),
        "questions": {
            "count": len(question_rows),
            "source_path": str(Path(questions_path).expanduser().resolve()) if questions_path else None,
            "source_sha256": sha256_file(Path(questions_path).expanduser().resolve()) if questions_path else None,
            "items": question_rows,
        },
        "query_packets": query_rows,
        "comparison_rule": {
            "raw_packets_match": "TrueMem/runtime/data/query path matched.",
            "raw_packets_differ": "Compare repo, artifact hashes, query list hash, and packet citation/order fields.",
            "raw_packets_match_but_words_differ": "Renderer or human interpretation differed, not native TrueMem retrieval.",
        },
    })
    target = Path(output_path).expanduser().resolve() if output_path else paths.receipts / f"determinism_{unique_stamp()}.json"
    write_json(target, receipt)
    receipt["receipt_path"] = str(target)
    return receipt


def load_receipt_questions(*, questions: list[str] | None, questions_path: str | Path | None) -> list[str]:
    out: list[str] = []
    if questions:
        out.extend(str(question).strip() for question in questions if str(question).strip())
    if questions_path:
        path = Path(questions_path).expanduser().resolve()
        out.extend(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return out


def query_receipt(runtime_root: str | Path, dataset_id: str, question_text: str, *, top_k: int) -> dict[str, Any]:
    packet = direct_question_query_baseline(runtime_root, dataset_id, question_text, top_k=top_k)
    locations = packet.get("answer_packet", {}).get("locations", [])
    raw_json = canonical_json(packet)
    return {
        "question": question_text,
        "top_k": top_k,
        "raw_packet_sha256": sha256_bytes(raw_json.encode("utf-8")),
        "output_path": packet.get("output_path"),
        "citation_order": [row.get("citation") for row in locations],
        "block_order": [
            {
                "citation": row.get("citation"),
                "file_path": row.get("file_path"),
                "line_start": row.get("line_start"),
                "line_end": row.get("line_end"),
                "score": row.get("score"),
                "density_score": row.get("density_score"),
                "direct_hit_count": row.get("direct_hit_count"),
                "text_hash": sha256_bytes(str(row.get("text", "")).encode("utf-8")),
            }
            for row in locations
        ],
        "final_answer_sha256": sha256_bytes(canonical_json(packet.get("final_answer", {})).encode("utf-8")),
    }


def dataset_artifact_hashes(paths: Any) -> dict[str, Any]:
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
    return {
        "files": {name: file_receipt(path) for name, path in files.items()},
        "incoming": directory_hashes(paths.incoming),
        "receipts": directory_hashes(paths.receipts, suffixes={".json"}),
    }


def directory_hashes(path: Path, *, suffixes: set[str] | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        if suffixes is not None and file_path.suffix.lower() not in suffixes:
            continue
        row = file_receipt(file_path)
        row["relative_path"] = str(file_path.relative_to(path))
        rows.append(row)
    return rows


def file_receipt(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "size_bytes": 0, "sha256": None}
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def repo_receipt() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[3]
    return {
        "repo_root": str(repo_root),
        "head": run_git(repo_root, "rev-parse", "HEAD"),
        "branch": run_git(repo_root, "branch", "--show-current"),
        "status_short": run_git(repo_root, "status", "--short"),
    }


def run_git(repo_root: Path, *args: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - environment receipt fallback
        return {"ok": False, "command": ["git", *args], "stdout": "", "stderr": str(exc)}
    return {
        "ok": completed.returncode == 0,
        "command": ["git", *args],
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "returncode": completed.returncode,
    }


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
