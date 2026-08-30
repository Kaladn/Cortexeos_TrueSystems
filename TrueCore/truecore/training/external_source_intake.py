"""Deterministic intake for external language and code teaching material.

External records are never local TrueSystems truth. This builder verifies a
frozen source envelope, transforms a fixed JSONL slice, and publishes separate
accepted, quarantined, rejected, and release artifacts. It performs no model
training and creates no local operation, capability, behavior, or authority.
"""

from __future__ import annotations

import ast
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
import warnings


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
    if manifest.get("namespace") not in {LANGUAGE_RELEASE, CODE_RELEASE, BRIDGE_RELEASE}:
        raise ValueError("external source namespace must be a declared external release")
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
    local_release_freeze = None
    if manifest["namespace"] == BRIDGE_RELEASE:
        frozen = manifest.get("local_release_freeze")
        if not isinstance(frozen, dict):
            raise ValueError("bridge intake requires local_release_freeze")
        release_set = frozen.get("release_set_manifest")
        releases = frozen.get("releases")
        if not isinstance(release_set, dict) or not isinstance(releases, list) or not releases:
            raise ValueError("bridge freeze requires release-set and release artifacts")
        frozen_artifacts = []
        frozen_parts = [("release_set_manifest", release_set)]
        for item in releases:
            frozen_parts.extend((f"{item.get('release_name')}:{kind}", item.get(kind)) for kind in ("manifest", "records"))
        for name, artifact in frozen_parts:
            if not isinstance(artifact, dict):
                raise ValueError("bridge freeze artifact is missing")
            path = Path(_require_string(artifact, "path")).resolve()
            expected = _require_string(artifact, "sha256")
            raw = path.read_bytes()
            if digest(raw) != expected or artifact.get("bytes") != len(raw):
                raise ValueError(f"frozen local release artifact mismatch: {path}")
            frozen_artifacts.append({"name": name, "path": str(path), "sha256": expected, "bytes": len(raw)})
        declared = {item.get("release_name"): item for item in releases}
        if set(declared) != {"LEVEL_1_CODE_LITERACY", "LEVEL_2_SYSTEM_RELATIONSHIPS"}:
            raise ValueError("bridge freeze must name exactly Level 1 and Level 2")
        for name, item in declared.items():
            release_manifest = json.loads(Path(item["manifest"]["path"]).read_bytes())
            if release_manifest.get("release_name") != name or release_manifest.get("release_id") != item.get("release_id"):
                raise ValueError(f"frozen {name} identity mismatch")
            if release_manifest.get("artifact", {}).get("sha256") != item["records"]["sha256"]:
                raise ValueError(f"frozen {name} records hash is not manifest-bound")
        local_release_freeze = {"verified_artifacts": frozen_artifacts, "releases": releases}
    return {"verified_artifacts": verified_artifacts, "slice_start": start, "slice_count": count, "local_release_freeze": local_release_freeze}


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


def _expression_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _expression_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return type(node).__name__


def _code_row(task: tuple[bytes, int, dict[str, Any], str]) -> tuple[str, dict[str, Any]]:
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
    if row.get("row_index") != coordinate:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "row_coordinate_mismatch", "observed": row.get("row_index")}
    original = row.get("record")
    if not isinstance(original, dict):
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "missing_original_record"}
    prompt = original.get("text")
    code = original.get("code")
    tests = original.get("test_list")
    if not isinstance(prompt, str) or not isinstance(code, str) or not isinstance(tests, list) or not all(isinstance(test, str) for test in tests):
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "unsupported_code_record_shape", "original_record": original}
    if not prompt or not code:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "empty_prompt_or_code", "original_record": original}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(code)
    except (SyntaxError, ValueError, TypeError, MemoryError) as error:
        return "quarantined", {
            "schema": f"{SCHEMA}:quarantined", "provenance": provenance,
            "reason": "python_parser_failure", "detail": type(error).__name__,
            "original_record": original,
        }
    definitions = []
    calls = []
    raises = []
    assertions = []
    state_reads = []
    state_writes = []
    for node in ast.walk(tree):
        location = {"line": getattr(node, "lineno", None), "column": getattr(node, "col_offset", None)}
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.append({
                "name": node.name, "kind": type(node).__name__,
                "line_start": node.lineno, "line_end": getattr(node, "end_lineno", node.lineno),
                "column_start": node.col_offset, "column_end": getattr(node, "end_col_offset", None),
                "source": ast.get_source_segment(code, node),
            })
        elif isinstance(node, ast.Call):
            calls.append({"observed_callee": _expression_name(node.func), **location})
        elif isinstance(node, ast.Raise):
            raises.append({"exception": _expression_name(node.exc) if node.exc else None, **location})
        elif isinstance(node, ast.Assert):
            assertions.append({"source": ast.get_source_segment(code, node), **location})
        elif isinstance(node, ast.Name):
            target = state_writes if isinstance(node.ctx, (ast.Store, ast.Del)) else state_reads
            target.append({"name": node.id, **location})
    for values in (definitions, calls, raises, assertions, state_reads, state_writes):
        values.sort(key=canonical)
    record = {
        "schema": f"{SCHEMA}:code_unit", "namespace": CODE_RELEASE,
        "truth_status": "NOT_LOCAL_TRUTH", "local_authority": False,
        "resolution": "EXTERNAL_GENERIC_UNBOUND", "local_capability": False,
        "source_provenance": provenance,
        "source_properties": {"license": source["license"], "language": source["language"], "upstream_lineage": source.get("upstream_lineage", [])},
        "location": {"field": "code", "span": [0, len(code)], "external_task_id": original.get("task_id")},
        "source_payload": code, "source_payload_sha256": digest(code.encode("utf-8")),
        "prompt": {"text": prompt, "span": [0, len(prompt)], "evidence": "source_supplied_field"},
        "relations": {
            "definitions": definitions, "calls": calls, "raises": raises,
            "assertions": assertions, "state_read": state_reads, "state_written": state_writes,
        },
        "supplied_behavior": {
            "tests": tests, "test_setup_code": original.get("test_setup_code"),
            "challenge_tests": original.get("challenge_test_list", []),
            "evidence": "source_supplied_not_executed",
        },
        "original_record": original,
        "unsupported_claims": ["runtime_order", "correctness", "local_operation", "local_capability", "local_behavior", "local_authority"],
    }
    record["record_id"] = digest(record)
    return "accepted", record


def _bridge_row(task: tuple[bytes, int, dict[str, Any], str, dict[str, dict[str, Any]]]) -> tuple[str, dict[str, Any]]:
    raw_line, line_number, source, source_manifest_sha256, local_records = task
    coordinate = source["row_coordinates"]["start"] + line_number - 1
    provenance = {
        "dataset_id": source["dataset_id"], "revision": source["revision"],
        "configuration": source["configuration"], "split": source["split"],
        "row_coordinate": coordinate, "raw_record_sha256": digest(raw_line),
        "raw_slice_line": line_number, "source_manifest_sha256": source_manifest_sha256,
    }
    try:
        row = json.loads(raw_line)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "invalid_json", "detail": type(error).__name__}
    if not isinstance(row, dict) or row.get("row_index") != coordinate:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "row_coordinate_mismatch_or_non_object"}
    phrase = row.get("phrase")
    span = row.get("phrase_span")
    relation = row.get("relation")
    if not isinstance(phrase, str) or not phrase or not isinstance(span, list) or len(span) != 2 or not all(isinstance(value, int) for value in span):
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "invalid_phrase_or_span"}
    if span[0] < 0 or span[1] > len(phrase) or span[0] >= span[1]:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "phrase_span_out_of_bounds"}
    candidates = row.get("candidate_target_record_hashes", [])
    if candidates:
        if not isinstance(candidates, list) or len(candidates) < 2 or not all(isinstance(value, str) and value in local_records for value in candidates):
            return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "ambiguous_candidate_set_does_not_verify"}
        return "quarantined", {
            "schema": f"{SCHEMA}:quarantined", "provenance": provenance,
            "reason": "multiple_plausible_local_targets", "phrase": phrase,
            "phrase_span": span, "candidate_target_record_hashes": sorted(candidates),
        }
    target_hash = row.get("target_record_hash")
    target = local_records.get(target_hash)
    if target is None:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "target_hash_not_in_frozen_local_release", "target_record_hash": target_hash}
    if row.get("target_selection_record_hash") != target.get("selection_record_hash"):
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "target_selection_hash_mismatch", "target_record_hash": target_hash}
    role_relation = {"call_edge": "calls", "import_edge": "imports", "state_read": "state_read", "state_written": "state_written"}.get(target.get("original_role"))
    if relation not in {"refers_to", role_relation}:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "relation_not_proven_by_target_role", "relation": relation}
    path = row.get("local_relationship_path")
    if not isinstance(path, list) or not path:
        return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "missing_local_relationship_path"}
    current_hash = target_hash
    verified_path = []
    for step in path:
        if not isinstance(step, dict) or step.get("from_record_hash") != current_hash:
            return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "relationship_path_discontinuity"}
        current = local_records.get(current_hash)
        next_hash = step.get("to_record_hash")
        next_record = local_records.get(next_hash)
        expected = {item.get("record_hash"): item.get("relationship") for item in current.get("parent_source_relationships", [])}
        if next_record is None or expected.get(next_hash) != step.get("relationship"):
            return "rejected", {"schema": f"{SCHEMA}:rejected", "provenance": provenance, "reason": "relationship_path_not_in_frozen_records"}
        verified_path.append({
            "from_record_hash": current_hash, "relationship": step["relationship"],
            "to_record_hash": next_hash, "to_coordinates": next_record.get("file_coordinates"),
        })
        current_hash = next_hash
    relation_line = None
    if target.get("original_role") == "call_edge":
        relation_line = target["original_record"].get("call_line")
    elif target.get("original_role") == "import_edge":
        relation_line = target["original_record"].get("target", {}).get("line")
    record = {
        "schema": f"{SCHEMA}:language_to_local_bridge", "namespace": BRIDGE_RELEASE,
        "truth_status": "BRIDGE_DERIVED_LOCAL_TARGET_UNCHANGED", "local_authority": False,
        "source_provenance": provenance,
        "phrase_unit": {"text": phrase[span[0]:span[1]], "full_text": phrase, "span": span},
        "relation": relation,
        "local_target": {
            "record_hash": target_hash, "selection_record_hash": target["selection_record_hash"],
            "release_name": target["_frozen_release_name"], "source_system": target["source_system"],
            "repository_identity": target["repository_identity"], "source_identity": target["source_identity"],
            "file_coordinates": target.get("file_coordinates"), "relation_line": relation_line,
        },
        "local_relationship_path": verified_path,
        "binding_evidence": "explicit_curated_frozen_record_hash_and_verified_path",
        "forbidden_inferences": ["new_operation", "runtime_success", "local_truth_mutation", "name_similarity_binding"],
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

    def _load_bridge_local_records(self) -> dict[str, dict[str, Any]]:
        selected_path = self.source_manifest_path.parent / self.source["source_artifact"]["path"]
        selected = [json.loads(line) for line in selected_path.read_bytes().splitlines() if line]
        selected_by_hash: dict[str, dict[str, Any]] = {}
        for row in selected:
            record_hash = row.get("record_hash")
            if digest(row.get("original_record")) != record_hash:
                raise ValueError("frozen local record original hash mismatch")
            without_selection_hash = {key: value for key, value in row.items() if key not in {"selection_record_hash", "_frozen_release_name"}}
            if digest(without_selection_hash) != row.get("selection_record_hash"):
                raise ValueError("frozen local selection record hash mismatch")
            if record_hash in selected_by_hash:
                raise ValueError("duplicate local record hash in bridge freeze")
            selected_by_hash[record_hash] = row
        found: dict[str, dict[str, Any]] = {}
        for release in self.verification["local_release_freeze"]["releases"]:
            release_name = release["release_name"]
            records_path = Path(release["records"]["path"])
            with records_path.open("rb") as handle:
                for raw_line in handle:
                    candidate = json.loads(raw_line)
                    record_hash = candidate.get("record_hash")
                    if record_hash in selected_by_hash:
                        frozen = {key: value for key, value in selected_by_hash[record_hash].items() if key != "_frozen_release_name"}
                        if canonical(candidate) != canonical(frozen):
                            raise ValueError("selected local record differs from frozen release")
                        candidate["_frozen_release_name"] = release_name
                        found[record_hash] = candidate
        if set(found) != set(selected_by_hash):
            raise ValueError("selected bridge record is absent from frozen local releases")
        return found

    def _transform(self) -> tuple[list[dict], list[dict], list[dict]]:
        slice_path = self.source_manifest_path.parent / self.source["raw_slice"]["path"]
        lines = [line for line in slice_path.read_bytes().splitlines() if line]
        if len(lines) != self.verification["slice_count"]:
            raise ValueError("raw slice line count does not match frozen source manifest")
        manifest_hash = digest(self.source_manifest_bytes)
        tasks: list[tuple] = [(line, index, self.source, manifest_hash) for index, line in enumerate(lines, 1)]
        if self.source["namespace"] == BRIDGE_RELEASE:
            local_records = self._load_bridge_local_records()
            tasks = [(*task, local_records) for task in tasks]
            transformer = _bridge_row
        else:
            transformer = _language_row if self.source["namespace"] == LANGUAGE_RELEASE else _code_row
        if self.workers == 1:
            results = map(transformer, tasks)
        else:
            context = multiprocessing.get_context("fork")
            with ProcessPoolExecutor(max_workers=self.workers, mp_context=context) as executor:
                results = executor.map(transformer, tasks, chunksize=max(1, len(tasks) // (self.workers * 4)))
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
        if self.verification["local_release_freeze"] is not None:
            receipt["frozen_local_release_artifacts"] = self.verification["local_release_freeze"]["verified_artifacts"]
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
