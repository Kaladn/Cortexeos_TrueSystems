"""Verify explicit concept assignments against frozen release records."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .coverage_matrix import AREAS, SCHEMA, canonical, digest, _write_json, _write_jsonl

ASSIGNMENT_SCHEMA = "truesystems_training_coverage_assignment@1"


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_bytes().splitlines() if line]


def build_assigned_coverage(release_root: Path, assignment_manifest: Path, output: Path, steering_root: Path | None = None) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    release_root = release_root.resolve()
    manifest_path = release_root / "release-set-manifest.json"
    release_raw = manifest_path.read_bytes()
    release_manifest = json.loads(release_raw)
    spec_raw = assignment_manifest.resolve().read_bytes()
    spec = json.loads(spec_raw)
    if spec.get("schema") != ASSIGNMENT_SCHEMA:
        raise ValueError("unsupported assignment manifest")

    release_index = {row["release_name"]: row for row in release_manifest["release_manifests"]}
    record_indexes: dict[str, dict[str, dict[str, Any]]] = {}
    verified = []
    seen = set()
    for assignment in spec["assignments"]:
        key = (assignment["area"], assignment["topic"], assignment["release"], assignment["selection_record_hash"])
        if key in seen:
            raise ValueError("duplicate concept assignment")
        seen.add(key)
        if assignment["area"] not in AREAS or assignment["topic"] not in AREAS[assignment["area"]]["topics"]:
            raise ValueError("assignment references an unknown requirement")
        release = assignment["release"]
        if release not in release_index or release == "RESEARCH_REFERENCE":
            raise ValueError("assignment references unavailable or research-only release")
        if release not in record_indexes:
            path = release_root / "releases" / release / release_index[release]["artifact"]["path"]
            raw = path.read_bytes()
            if digest(raw) != release_index[release]["artifact"]["sha256"]:
                raise ValueError(f"release artifact hash mismatch: {release}")
            rows = _rows(path)
            record_indexes[release] = {row["selection_record_hash"]: row for row in rows}
        record = record_indexes[release].get(assignment["selection_record_hash"])
        if record is None:
            raise ValueError("assigned source record is missing")
        if record["eligibility"] in {"EVALUATION_RESERVED", "NEVER_TRAIN"} or record["training_role"] == "RESEARCH_REFERENCE":
            raise ValueError("assigned source record is not eligible evidence")
        original = record["original_record"]
        verified.append({
            "schema": f"{ASSIGNMENT_SCHEMA}:verified_example",
            "area": assignment["area"], "topic": assignment["topic"], "reason": assignment["reason"],
            "evidence_scope": "LOCAL_SOURCE_SEED" if assignment["area"].endswith("_EXTERNAL") else "LOCAL_SOURCE_BACKED",
            "release_name": release, "release_id": release_index[release]["release_id"],
            "selection_record_hash": record["selection_record_hash"], "record_hash": record["record_hash"],
            "source_identity": record["source_identity"], "repository_identity": record["repository_identity"],
            "source_system": record["source_system"], "file_coordinates": record["file_coordinates"],
            "symbol": original.get("symbol"), "training_role": record["training_role"], "eligibility": record["eligibility"],
        })
    verified.sort(key=lambda row: (row["area"], row["topic"], row["selection_record_hash"]))

    reservation_evidence = []
    if steering_root is not None:
        steering_root = steering_root.resolve()
        steering_raw = (steering_root / "manifest.json").read_bytes(); steering = json.loads(steering_raw)
        eval_path = steering_root / "reservations/evaluation.jsonl"; refusal_path = steering_root / "reservations/refusal-evaluation.jsonl"
        eval_raw = eval_path.read_bytes(); refusal_raw = refusal_path.read_bytes()
        if digest(eval_raw) != steering["artifacts"]["evaluation_reservations"]["sha256"] or digest(refusal_raw) != steering["artifacts"]["refusal_reservations"]["sha256"]:
            raise ValueError("steering reservation artifact hash mismatch")
        eval_rows = _rows(eval_path); refusal_rows = _rows(refusal_path)
        for row in eval_rows:
            for topic in ("source_group_holdout", "paraphrase_family_holdout", "target_holdout"):
                reservation_evidence.append({"area":"EVALUATION_RESERVED","topic":topic,"evidence_scope":"SEALED_EVALUATION_RESERVATION",
                    "record_hash":row["sealed_record_sha256"],"record_id":row["record_id"],"source_group_id":row["source_group_id"],
                    "paraphrase_family_id":row["paraphrase_family_id"],"target_identity":row["target_identity"],"eligibility":"EVALUATION_RESERVED"})
        refusal_topics={"wrong_system":"wrong_system","wrong_symbol":"wrong_symbol","ambiguity":"ambiguous_target","stale":"stale_or_missing_hash",
            "missing":"stale_or_missing_hash","unsupported":"unsupported_meaning","visual_meaning":"unsupported_meaning"}
        for row in refusal_rows:
            topic=refusal_topics.get(row["category"])
            if topic:
                reservation_evidence.append({"area":"FAILURE_RESTRAINT","topic":topic,"evidence_scope":"SEALED_EVALUATION_RESERVATION",
                    "record_hash":row["sealed_record_sha256"],"record_id":row["reservation_id"],"category":row["category"],"eligibility":"EVALUATION_RESERVED"})
            reservation_evidence.append({"area":"EVALUATION_RESERVED","topic":"refusal_evaluation","evidence_scope":"SEALED_EVALUATION_RESERVATION",
                "record_hash":row["sealed_record_sha256"],"record_id":row["reservation_id"],"category":row["category"],"eligibility":"EVALUATION_RESERVED"})
        extension=steering.get("evaluation_paraphrase_extensions")
        if extension:
            reservation_evidence.append({"area":"EVALUATION_RESERVED","topic":"unseen_paraphrase","evidence_scope":"FROZEN_EVALUATION_EXTENSION_ARTIFACT",
                "record_hash":extension["sha256"],"record_id":extension["sha256"],"records":extension["records"],"eligibility":"EVALUATION_RESERVED"})
        reservation_evidence.sort(key=lambda row:(row["area"],row["topic"],row["record_id"]))

    counts = Counter((row["area"], row["topic"]) for row in verified)
    evaluation_counts = Counter((row["area"], row["topic"]) for row in reservation_evidence)
    by_system: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in verified:
        by_system[(row["area"], row["topic"])].add(row["source_system"])
    measured = []
    for area, definition in sorted(AREAS.items()):
        for topic in definition["topics"]:
            count = counts[(area, topic)]; eval_count=evaluation_counts[(area,topic)]
            external = area.endswith("_EXTERNAL")
            status = "GAP_NO_EXACT_EVIDENCE" if count == 0 and eval_count == 0 else "EVALUATION_ONLY_NOT_TRAINING_COVERAGE" if count == 0 else "SEEDED_LOCAL_ONLY_EXTERNAL_GAP" if external else "SEEDED_EXACT_EVIDENCE"
            measured.append({"schema": f"{SCHEMA}:measured_requirement", "area": area, "topic": topic,
                "authority": definition["authority"], "exact_examples": count, "reserved_evaluation_examples":eval_count,
                "source_systems": sorted(by_system[(area, topic)]), "status": status,
                "closed": False, "closure_law": "No requirement closes until training and independently reserved evaluation examples are explicitly assigned."})

    acquisition = []
    for row in measured:
        if row["area"].endswith("_EXTERNAL") and row["status"] != "SEEDED_EXACT_EVIDENCE":
            acquisition.append({"area": row["area"], "topic": row["topic"], "need": "EXTERNAL_SOURCE_REQUIRED",
                "authority": "NOT_LOCAL_TRUTH", "acquisition_status": "NOT_YET_ACQUIRED",
                "selection_gate": "immutable revision, clear license/schema, exact source preservation, small fixed pilot, quarantine/rejection ledgers, 1/24 semantic identity"})

    output.mkdir(parents=True)
    artifacts = {"examples": _write_jsonl(output / "verified-examples.jsonl", verified),
                 "reservation_evidence":_write_jsonl(output/"reservation-evidence.jsonl",reservation_evidence),
                 "requirements": _write_jsonl(output / "measured-requirements.jsonl", measured),
                 "acquisition": _write_jsonl(output / "external-acquisition-needs.jsonl", acquisition)}
    manifest = {"schema": ASSIGNMENT_SCHEMA, "classification": "MEASURED_COVERAGE_NOT_TRAINED",
        "sources": {"release_manifest_sha256": digest(release_raw), "assignment_manifest_sha256": digest(spec_raw),
                    "steering_manifest_sha256": digest(steering_raw) if steering_root is not None else None},
        "verified_examples": len(verified), "requirements": len(measured),
        "seeded_requirements": sum(row["exact_examples"] > 0 for row in measured),
        "closed_requirements": 0, "external_acquisition_needs": len(acquisition),
        "research_reference_used": False, "generic_external_data_used": False,
        "model_training_performed": False, "optimizer_updates": 0, "authority_created": False,
        "artifacts": artifacts}
    manifest["coverage_release_id"] = digest(manifest)
    _write_json(output / "manifest.json", manifest)
    return manifest
