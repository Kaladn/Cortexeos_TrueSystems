"""Deterministic intake for external language and code teaching material.

External records are never local TrueSystems truth. This builder verifies a
frozen source envelope, transforms a fixed JSONL slice, and publishes separate
accepted, quarantined, rejected, and release artifacts. It performs no model
training and creates no local operation, capability, behavior, or authority.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import resource
import time
from typing import Any, Iterable


SCHEMA = "truesystems_external_source_intake@1"
LANGUAGE_RELEASE = "HF_LANGUAGE_GENERIC"
CODE_RELEASE = "HF_CODE_GENERIC"
BRIDGE_RELEASE = "LANGUAGE_TO_LOCAL_BRIDGES"
RELEASE_NAMES = (LANGUAGE_RELEASE, CODE_RELEASE, BRIDGE_RELEASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IMMUTABLE_REVISION_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
LANGUAGE_RELATIONS = {0: "entailment", 1: "neutral", 2: "contradiction"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: bytes | dict | list) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    payload = canonical(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": path.name, "sha256": digest(payload), "bytes": len(payload), "records": 1}


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    material = list(rows)
    payload = b"".join(canonical(row) + b"\n" for row in material)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": path.name, "sha256": digest(payload), "bytes": len(payload), "records": len(material)}


def _require_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"source manifest requires non-empty {field}")
    return value


def _verify_source_manifest(manifest: dict[str, Any], manifest_root: Path) -> dict[str, Any]:
    if manifest.get("schema") != f"{SCHEMA}:source_manifest":
        raise ValueError("unsupported source manifest schema")
    if manifest.get("namespace") not in {LANGUAGE_RELEASE, CODE_RELEASE}:
        raise ValueError("external source namespace must be a generic HF release")
    _require_string(manifest, "dataset_id")
    revision = _require_string(manifest, "revision")
    if not IMMUTABLE_REVISION_RE.fullmatch(revision):
        raise ValueError("revision must be an immutable lowercase Git commit hash")
    for field in ("configuration", "split", "license", "language"):
        _require_string(manifest, field)
    if manifest["license"].lower() in {"unknown", "none", "unspecified"}:
        raise ValueError("source license must be explicit")
    if not isinstance(manifest.get("dataset_schema"), dict) or not manifest["dataset_schema"]:
        raise ValueError("dataset_schema must be a non-empty object")
    coordinates = manifest.get("row_coordinates")
    if not isinstance(coordinates, dict) or coordinates.get("kind") != "zero_based_row_index":
        raise ValueError("row coordinates must use zero_based_row_index")
    start = coordinates.get("start"); count = coordinates.get("count")
    if not isinstance(start, int) or start < 0 or not isinstance(count, int) or count < 1:
        raise ValueError("row coordinate start/count must be bounded non-negative integers")
    verified_artifacts = []
    for name in ("dataset_card", "source_artifact", "raw_slice"):
        artifact = manifest.get(name)
        if not isinstance(artifact, dict):
            raise ValueError(f"source manifest requires {name}")
        relative = _require_string(artifact, "path")
        expected = _require_string(artifact, "sha256")
        if not SHA256_RE.fullmatch(expected):
            raise ValueError(f"{name} sha256 must be lowercase hexadecimal")
        path = (manifest_root / relative).resolve()
        try:
            path.relative_to(manifest_root.resolve())
        except ValueError as error:
            raise ValueError(f"{name} escapes source manifest directory") from error
        raw = path.read_bytes()
        actual = digest(raw)
        if actual != expected:
            raise ValueError(f"{name} hash mismatch: {path}")
        if artifact.get("bytes") != len(raw):
            raise ValueError(f"{name} byte count mismatch: {path}")
        verified_artifacts.append({"name": name, "path": relative, "sha256": actual, "bytes": len(raw)})
    adapter = manifest.get("adapter")
    if not isinstance(adapter, dict) or not adapter.get("name") or not adapter.get("version"):
        raise ValueError("source manifest requires a named, versioned adapter")
    return {"verified_artifacts": verified_artifacts, "slice_start": start, "slice_count": count}


def _language_row(task: tuple[bytes, int, dict[str, Any], str]) -> tuple[str, dict[str, Any]]:
    raw_line, line_number, source, source_manifest_sha256 = task
    raw_hash = digest(raw_line)
    coordinate = source["row_coordinates"]["start"] + line_number - 1
    provenance = {
        "dataset_id": source["dataset_id"], "revision": source["revision"],
        "configuration": source["configuration"], "split": source["split"],
        "row_coordinate": coordinate, "raw_record_sha256": raw_hash,
        "raw_slice_line": line_number, "source_manifest_sha256": source_manifest_sha256,
    }
    try:
        row = json.loads(raw_line)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "invalid_json", "detail": type(error).__name__}
    if not isinstance(row, dict):
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "record_not_object"}
    supplied_coordinate = row.get("row_index")
    if supplied_coordinate != coordinate:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "row_coordinate_mismatch", "observed": supplied_coordinate}
    original = row.get("record")
    if not isinstance(original, dict):
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "missing_original_record"}
    premise = original.get("premise"); hypothesis = original.get("hypothesis"); label = original.get("label")
    if not isinstance(premise, str) or not isinstance(hypothesis, str):
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "language_fields_not_strings", "original_record": original}
    if not premise or not hypothesis:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "empty_language_field", "original_record": original}
    if label not in LANGUAGE_RELATIONS:
        return "quarantined", {"schema": f"{SCHEMA}:quarantined", "provenance": provenance, "reason": "unresolved_source_label", "original_record": original}
    premise_id = digest({"coordinate": coordinate, "field": "premise", "text": premise})
    hypothesis_id = digest({"coordinate": coordinate, "field": "hypothesis", "text": hypothesis})
    record = {
        "schema": f"{SCHEMA}:language_relation", "namespace": LANGUAGE_RELEASE,
        "truth_status": "NOT_LOCAL_TRUTH", "local_authority": False,
        "source_provenance": provenance,
        "source_properties": {"license": source["license"], "language": source["language"], "upstream_lineage": source.get("upstream_lineage", [])},
        "units": [
            {"unit_id": premise_id, "location": {"field": "premise", "span": [0, len(premise)]}, "text": premise},
            {"unit_id": hypothesis_id, "location": {"field": "hypothesis", "span": [0, len(hypothesis)]}, "text": hypothesis},
        ],
        "relations": [{"source_unit_id": premise_id, "relationship": LANGUAGE_RELATIONS[label], "target_unit_id": hypothesis_id, "evidence": "source_supplied_label"}],
        "meaning_target": {"kind": "source_supplied_relation", "label_id": label, "label": LANGUAGE_RELATIONS[label]},
        "original_record": original,
        "forbidden_inferences": ["local_operation", "local_capability", "local_behavior", "local_authority"],
    }
    record["record_id"] = digest(record)
    return "accepted", record


class ExternalSourceIntakeBuilder:
    def __init__(self, source_manifest: Path, output_root: Path, workers: int = 24):
        self.source_manifest_path = source_manifest.resolve()
        self.output_root = output_root.resolve()
        if workers < 1:
            raise ValueError("workers must be at least 1")
        if self.output_root.exists():
            raise FileExistsError(f"output root already exists: {self.output_root}")
        self.workers = workers
        self.source_manifest_bytes = self.source_manifest_path.read_bytes()
        self.source = json.loads(self.source_manifest_bytes)
        self.verification = _verify_source_manifest(self.source, self.source_manifest_path.parent)

    def _transform(self) -> tuple[list[dict], list[dict], list[dict]]:
        slice_path = self.source_manifest_path.parent / self.source["raw_slice"]["path"]
        lines = [line for line in slice_path.read_bytes().splitlines() if line]
        if len(lines) != self.verification["slice_count"]:
            raise ValueError("raw slice line count does not match frozen source manifest")
        manifest_hash = digest(self.source_manifest_bytes)
        tasks = [(line, index, self.source, manifest_hash) for index, line in enumerate(lines, 1)]
        if self.source["namespace"] != LANGUAGE_RELEASE:
            raise NotImplementedError("HF_CODE_GENERIC adapter is reserved but not implemented")
        if self.workers == 1:
            results = map(_language_row, tasks)
        else:
            context = multiprocessing.get_context("fork")
            with ProcessPoolExecutor(max_workers=self.workers, mp_context=context) as executor:
                results = executor.map(_language_row, tasks, chunksize=max(1, len(tasks) // (self.workers * 4)))
        ledgers: dict[str, list[dict]] = {"accepted": [], "quarantined": [], "rejected": []}
        for status, row in results:
            ledgers[status].append(row)
        for rows in ledgers.values():
            rows.sort(key=canonical)
        return ledgers["accepted"], ledgers["quarantined"], ledgers["rejected"]

    def run(self) -> dict[str, Any]:
        self.output_root.mkdir(parents=True)
        wall_start = time.perf_counter(); usage_start = resource.getrusage(resource.RUSAGE_SELF); child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
        accepted, quarantined, rejected = self._transform()
        artifacts = {
            "accepted": _write_jsonl(self.output_root / "ledgers" / "accepted.jsonl", accepted),
            "quarantined": _write_jsonl(self.output_root / "ledgers" / "quarantined.jsonl", quarantined),
            "rejected": _write_jsonl(self.output_root / "ledgers" / "rejected.jsonl", rejected),
        }
        release_manifests = []
        for release_name in RELEASE_NAMES:
            rows = accepted if release_name == self.source["namespace"] else []
            release_artifact = _write_jsonl(self.output_root / "releases" / release_name / "records.jsonl", rows)
            identity = {"schema": f"{SCHEMA}:release_identity", "name": release_name, "record_ids": [row["record_id"] for row in rows]}
            release_manifest = {
                "schema": f"{SCHEMA}:release_manifest", "release_name": release_name,
                "release_id": digest(identity), "record_count": len(rows), "truth_status": "NOT_LOCAL_TRUTH",
                "local_records_mixed": False, "model_training_performed": False, "artifact": release_artifact,
            }
            _write_json(self.output_root / "releases" / release_name / "manifest.json", release_manifest)
            release_manifests.append(release_manifest)
        receipt = {
            "schema": f"{SCHEMA}:adapter_receipt", "adapter": self.source["adapter"],
            "source_manifest_sha256": digest(self.source_manifest_bytes),
            "verified_source_artifacts": self.verification["verified_artifacts"],
            "input_records": self.verification["slice_count"], "accepted": len(accepted),
            "quarantined": len(quarantined), "rejected": len(rejected),
            "source_text_normalization": "none", "truth_status": "NOT_LOCAL_TRUTH",
        }
        receipt_artifact = _write_json(self.output_root / "adapter-receipt.json", receipt)
        manifest = {
            "schema": SCHEMA, "classification": "EXTERNAL_GENERIC_NOT_LOCAL_TRUTH_NOT_TRAINED",
            "source_manifest_sha256": digest(self.source_manifest_bytes), "namespace_separation": True,
            "local_records_mixed": False, "local_authority_created": False, "model_training_performed": False,
            "release_manifests": release_manifests, "ledgers": artifacts, "adapter_receipt": receipt_artifact,
            "semantic_artifacts": [
                artifacts["accepted"], artifacts["quarantined"], artifacts["rejected"], receipt_artifact,
                *[release["artifact"] for release in release_manifests],
            ],
        }
        _write_json(self.output_root / "manifest.json", manifest)
        wall = time.perf_counter() - wall_start; usage_end = resource.getrusage(resource.RUSAGE_SELF); child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (usage_end.ru_utime + usage_end.ru_stime - usage_start.ru_utime - usage_start.ru_stime) + (child_end.ru_utime + child_end.ru_stime - child_start.ru_utime - child_start.ru_stime)
        _write_json(self.output_root / "performance-receipt.json", {
            "schema": f"{SCHEMA}:performance_receipt", "workers": self.workers, "logical_cpus": os.cpu_count(),
            "elapsed_wall_seconds": wall, "aggregate_cpu_seconds": cpu,
            "records_per_second": self.verification["slice_count"] / wall if wall else 0.0,
            "maximum_resident_kib": max(usage_end.ru_maxrss, child_end.ru_maxrss),
        })
        return manifest


def build_external_source_intake(source_manifest: Path, output_root: Path, workers: int = 24) -> dict[str, Any]:
    return ExternalSourceIntakeBuilder(source_manifest, output_root, workers=workers).run()
