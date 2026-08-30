"""Deterministically curate a frozen symbolic-foundations source pilot.

Curation retains exact source files and records adapter readiness.  It does not
convert foreign symbolic systems into TrueSystems semantics or training data.
"""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SCHEMA = "truesystems_symbolic_foundations_curation@1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(raw: bytes | dict | list) -> str:
    return hashlib.sha256(raw if isinstance(raw, bytes) else canonical(raw)).hexdigest()


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    raw = canonical(value) + b"\n"
    path.write_bytes(raw)
    return {"path": path.name, "bytes": len(raw), "sha256": digest(raw), "records": 1}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw = b"".join(canonical(row) + b"\n" for row in rows)
    path.write_bytes(raw)
    return {"path": path.name, "bytes": len(raw), "sha256": digest(raw), "records": len(rows)}


def _decision(family: str, path: str) -> tuple[str, list[str], str]:
    if family == "mathlib4" and path.startswith("Mathlib/Logic/") and path.endswith(".lean"):
        return "QUARANTINED", ["logic"], "Exact Lean source retained; declaration/proof spans require a verified Lean adapter."
    if family == "networkx" and path.startswith("networkx/algorithms/") and path.endswith(".py") and not path.endswith("/__init__.py"):
        topics = ["graphs_and_relations"]
        if "/traversal/" in path or "/shortest_paths/" in path:
            topics.append("deterministic_search")
        return "ACCEPTED", topics, "Executable implementation or test source with explicit graph/search constructions."
    if family == "despite" and path.startswith("demo_tasks/") and Path(path).suffix in {".py", ".pddl", ".json"}:
        return "QUARANTINED", ["state_machines", "deterministic_search"], "Declared objects, state, actions, and constraints retained; cross-file trace adapter is not yet verified."
    return "REJECTED", [], "License, documentation, package support, or unrelated sparse-checkout material; provenance remains in the source receipt."


def build_curation(source_root: Path, output: Path, workers: int = 1) -> dict[str, Any]:
    source_root = source_root.resolve()
    receipt_path = source_root / "source-receipt.json"
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw)
    if receipt.get("classification") != "EXTERNAL_NOT_LOCAL_TRUTH_NOT_TRAINED":
        raise ValueError("unsupported source receipt")
    if output.exists():
        raise FileExistsError(output)

    jobs = []
    family_commits = {}
    for family in receipt["families"]:
        family_commits[family["family"]] = family["commit"]
        for entry in family["tree"]:
            jobs.append((family["family"], family["commit"], entry))

    def inspect(job: tuple[str, str, dict[str, Any]]) -> dict[str, Any]:
        family, commit, entry = job
        path = source_root / family / entry["path"]
        raw = path.read_bytes()
        if len(raw) != entry["bytes"] or digest(raw) != entry["sha256"]:
            raise ValueError(f"frozen source mismatch: {family}/{entry['path']}")
        status, topics, reason = _decision(family, entry["path"])
        identity = {"family": family, "commit": commit, "path": entry["path"], "bytes": len(raw), "sha256": digest(raw)}
        return {
            "schema": f"{SCHEMA}:curation_record", "status": status,
            "truth_status": "NOT_LOCAL_TRUTH", "training_eligible": False,
            "source_identity": identity, "source_record_id": digest(identity),
            "curriculum_topics": topics, "reason": reason,
            "source_preservation": "EXACT_BYTES_AT_FROZEN_COMMIT",
            "semantic_claim": "NONE_UNTIL_DEDICATED_ADAPTER_VERIFICATION",
        }

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        rows = list(pool.map(inspect, jobs))
    rows.sort(key=lambda row: (row["status"], row["source_identity"]["family"], row["source_identity"]["path"]))
    ledgers = {status: [row for row in rows if row["status"] == status] for status in ("ACCEPTED", "QUARANTINED", "REJECTED")}

    output.mkdir(parents=True)
    artifacts = {
        "accepted": _write_jsonl(output / "accepted.jsonl", ledgers["ACCEPTED"]),
        "quarantined": _write_jsonl(output / "quarantined.jsonl", ledgers["QUARANTINED"]),
        "rejected": _write_jsonl(output / "rejected.jsonl", ledgers["REJECTED"]),
    }
    manifest = {
        "schema": SCHEMA, "classification": "CURATED_EXTERNAL_SOURCE_NOT_TRAINING_DATA",
        "source_receipt": {"path": str(receipt_path), "sha256": digest(receipt_raw)},
        "family_commits": dict(sorted(family_commits.items())),
        "counts": {key.lower(): len(value) for key, value in ledgers.items()},
        "curation_law": "Retaining a frozen file does not assert that its foreign symbols mean TrueSystems symbols.",
        "adapter_status": {"networkx": "READY_FOR_EXACT_AST_FIXTURE_ADAPTER", "mathlib4": "REQUIRES_VERIFIED_LEAN_DECLARATION_ADAPTER", "despite": "REQUIRES_VERIFIED_CROSS_FILE_STATE_TRACE_ADAPTER"},
        "truemem_616_source_law": "LOCAL_TRUESYSTEMS_ONLY; never derived from an external symbolic family.",
        "model_training_performed": False, "optimizer_updates": 0, "local_authority_created": False,
        "artifacts": artifacts,
    }
    manifest["curation_release_id"] = digest(manifest)
    _write_json(output / "manifest.json", manifest)
    return manifest
