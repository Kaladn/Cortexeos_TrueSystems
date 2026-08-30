"""Deterministic prerequisites for phrase-to-frozen-bridge selection.

This module prepares representations and reservations only.  It contains no
model, optimizer, checkpoint, training loop, operation execution, or authority.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from collections import Counter, defaultdict
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import time
from typing import Any, Iterable


SCHEMA = "truesystems_steering_prerequisites@1"
LOCAL_NAMESPACE = "LANGUAGE_TO_LOCAL_BRIDGES"
VISUAL_NAMESPACE = "LANGUAGE_TO_VISUAL_IDENTITY_BRIDGES"
SPLITS = ("train", "validation", "evaluation")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: bytes | dict | list) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def candidate_set_identity(candidate_ids: Iterable[str]) -> str:
    """Order-independent identity for a finite set of existing bridge IDs."""
    values = sorted(candidate_ids)
    if not values or len(values) != len(set(values)):
        raise ValueError("candidate set must contain unique existing bridge IDs")
    return digest({"schema": f"{SCHEMA}:candidate_set_identity", "candidate_ids": values})


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    raw = canonical(value) + b"\n"; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    return {"path": path.name, "sha256": digest(raw), "bytes": len(raw), "records": 1}


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = list(rows); raw = b"".join(canonical(row) + b"\n" for row in values)
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    return {"path": path.name, "sha256": digest(raw), "bytes": len(raw), "records": len(values)}


def _artifact(item: dict[str, Any]) -> tuple[Path, bytes]:
    path = Path(str(item.get("path") or "")).resolve(); raw = path.read_bytes()
    if item.get("sha256") != digest(raw) or item.get("bytes") != len(raw): raise ValueError(f"frozen artifact mismatch: {path}")
    return path, raw


def _local_assignment(row: dict[str, Any], release_id: str, manifest_hash: str) -> dict[str, Any]:
    target = row["local_target"]; phrase = row["phrase_unit"]["full_text"]
    source_key = {"domain": "local_operational", "source_system": target["source_system"],
                  "path": target["file_coordinates"]["path"]}
    family_key = {"domain": "local_operational", "target": row["record_id"], "relation": row["relation"]}
    return {"domain": "local_operational", "bridge_record_id": row["record_id"], "phrase": phrase,
        "phrase_sha256": digest(phrase.encode()), "target_identity": target["record_hash"],
        "relation_path_hash": digest(row["local_relationship_path"]), "source_group_id": "local-source-" + digest(source_key)[:24],
        "paraphrase_family_id": "local-family-" + digest(family_key)[:24],
        "assignment_evidence": {"kind": "documented_local_provenance_and_target_meaning", "source_key": source_key, "family_key": family_key},
        "authority": {"release_id": release_id, "manifest_sha256": manifest_hash, "local_authority": False},
        "candidate_payload": {"bridge_record_id": row["record_id"], "domain": "local_operational", "relation": row["relation"],
            "target_record_hash": target["record_hash"], "selection_record_hash": target["selection_record_hash"],
            "coordinates": target["file_coordinates"], "relationship_path": row["local_relationship_path"],
            "citation": {"source_system": target["source_system"], "repository_identity": target["repository_identity"],
                "source_identity": target["source_identity"], "file_coordinates": target["file_coordinates"]},
            "authority_status": "NOT_LOCAL_TRUTH_BRIDGE_SELECTS_FROZEN_LOCAL_RECORD"}}


def _visual_assignment(row: dict[str, Any], release_id: str, manifest_hash: str) -> dict[str, Any]:
    target = row["target_record"]; phrase = row["phrase"]
    relation = target.get("relationship") or "visual_unit"
    if relation == "visual_unit":
        coords = target["coordinates"]
        source_key = {"domain": "visual_identity", "kind": "native_frame_locations", "frame_number": target["frame_number"]}
        meaning_key = {"kind": "exact_native_location", "target": row["bridge_id"], "coordinate": [target["frame_number"], coords["grid_row"], coords["grid_column"]]}
    else:
        source_key = {"domain": "visual_identity", "kind": "verified_relationship_class", "relationship": relation}
        meaning_key = {"kind": relation, "target": row["bridge_id"], "identity_classification": row.get("identity_classification")}
    return {"domain": "visual_identity", "bridge_record_id": row["bridge_id"], "phrase": phrase,
        "phrase_sha256": digest(phrase.encode()), "target_identity": row["target_hash"],
        "relation_path_hash": digest(row["verified_relationship_path"]) if row["verified_relationship_path"] else None, "source_group_id": "visual-source-" + digest(source_key)[:24],
        "paraphrase_family_id": "visual-family-" + digest(meaning_key)[:24],
        "assignment_evidence": {"kind": "native_visual_provenance_and_explicit_relationship_meaning", "source_key": source_key, "family_key": meaning_key},
        "authority": {"release_id": release_id, "manifest_sha256": manifest_hash, "local_authority": False},
        "candidate_payload": {"bridge_record_id": row["bridge_id"], "domain": "visual_identity", "target_hash": row["target_hash"],
            "target_kind": row["target_kind"], "relationship": target.get("relationship"),
            "identity_classification": row.get("identity_classification"), "coordinates": [c.get("coordinates") for c in row["citations"]],
            "timestamps": [c["observed_at_utc"] for c in row["citations"]], "citations": row["citations"],
            "relationship_path": row["verified_relationship_path"],
            "authority_status": "READ_ONLY_FROZEN_TRUEVISION_BRIDGE"}}


def _candidate_record(task: tuple[dict[str, Any], list[dict[str, Any]], str]) -> dict[str, Any]:
    assignment, pool, split = task
    ordered_pool = sorted(pool, key=lambda row: row["bridge_record_id"])
    position = next(index for index, row in enumerate(ordered_pool) if row["bridge_record_id"] == assignment["bridge_record_id"])
    candidates = [ordered_pool[(position + offset) % len(ordered_pool)]["candidate_payload"] for offset in range(min(4, len(ordered_pool)))]
    candidates = sorted(candidates, key=lambda row: row["bridge_record_id"])
    candidate_ids = [row["bridge_record_id"] for row in candidates]
    candidate_set_id = candidate_set_identity(candidate_ids)
    record = {"schema": f"{SCHEMA}:supplied_candidate_record", "domain": assignment["domain"], "split": split,
        "phrase": assignment["phrase"], "phrase_sha256": assignment["phrase_sha256"],
        "source_group_id": assignment["source_group_id"], "paraphrase_family_id": assignment["paraphrase_family_id"],
        "candidate_set_id": candidate_set_id, "candidates": candidates,
        "expected_outcome": {"status": "selected", "bridge_record_id": assignment["bridge_record_id"]},
        "model_boundary": {"may_score_supplied_candidates_only": True, "may_generate_identifiers": False,
            "may_create_relationships": False, "may_create_operations": False, "may_create_evidence": False,
            "may_create_authority": False, "selection_requires_deterministic_resolver_verification": True},
        "authority": assignment["authority"]}
    record["record_id"] = digest(record)
    return record


def _assign_splits(assignments: list[dict[str, Any]]) -> dict[str, str]:
    by_domain: dict[str, list[str]] = defaultdict(list)
    for group in sorted({row["source_group_id"] for row in assignments}):
        domain = next(row["domain"] for row in assignments if row["source_group_id"] == group)
        by_domain[domain].append(group)
    result = {}
    for domain, groups in sorted(by_domain.items()):
        for index, group in enumerate(sorted(groups)):
            result[group] = "evaluation" if index % 5 == 0 else "validation" if index % 5 == 1 else "train"
    return result


def validate_assignments(assignments: list[dict[str, Any]], expected_domain_counts: dict[str, int]) -> None:
    """Reject incomplete, duplicate, conflicting, or cross-domain membership."""
    counts = Counter(row.get("domain") for row in assignments)
    if counts != Counter(expected_domain_counts): raise ValueError("missing or extra bridge membership")
    ids = [row.get("bridge_record_id") for row in assignments]
    if any(not value for value in ids) or len(ids) != len(set(ids)): raise ValueError("duplicate membership or cross-domain identity collision")
    if any(not row.get("source_group_id") or not row.get("paraphrase_family_id") for row in assignments): raise ValueError("missing source-group or paraphrase-family membership")
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in assignments: families[row["paraphrase_family_id"]].append(row)
    if any(len({item["target_identity"] for item in values}) != 1 for values in families.values()): raise ValueError("conflicting targets within paraphrase family")


class SteeringPrerequisiteBuilder:
    def __init__(self, source_manifest: Path, output_root: Path, workers: int = 24):
        if workers < 1: raise ValueError("workers must be at least 1")
        self.source_path = source_manifest.resolve(); self.source_bytes = self.source_path.read_bytes(); self.source = json.loads(self.source_bytes)
        self.output = output_root.resolve(); self.workers = workers
        if self.output.exists(): raise FileExistsError(f"output root already exists: {self.output}")

    def _load(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if self.source.get("schema") != f"{SCHEMA}:source_manifest": raise ValueError("unsupported source manifest")
        local = self.source["local_bridge_release"]; visual = self.source["visual_bridge_release"]
        _, local_manifest_raw = _artifact(local["manifest"]); _, local_records_raw = _artifact(local["records"])
        local_manifest = json.loads(local_manifest_raw)
        if local_manifest.get("release_name") != LOCAL_NAMESPACE or local_manifest.get("artifact", {}).get("sha256") != digest(local_records_raw):
            raise ValueError("local bridge release is not frozen authority")
        local_rows = [json.loads(line) for line in local_records_raw.splitlines() if line]
        _, visual_manifest_raw = _artifact(visual["manifest"]); _, visual_records_raw = _artifact(visual["accepted"])
        visual_manifest = json.loads(visual_manifest_raw)
        if visual_manifest.get("namespace") != VISUAL_NAMESPACE or visual_manifest.get("artifacts", {}).get("accepted", {}).get("sha256") != digest(visual_records_raw):
            raise ValueError("visual bridge release is not frozen authority")
        visual_rows = [json.loads(line) for line in visual_records_raw.splitlines() if line]
        refusal_path, refusal_raw = _artifact(self.source["sealed_refusal_evaluation"])
        category_index = self.source.get("refusal_category_index")
        required_categories = {"ambiguity", "negation", "stale", "missing", "unsupported", "wrong_system", "wrong_symbol", "visual_meaning"}
        if not isinstance(category_index, dict) or set(category_index) != required_categories or any(not isinstance(value, str) or len(value) != 64 for value in category_index.values()):
            raise ValueError("sealed refusal evaluation requires all fixed category identities")
        self.refusal_freeze = {"path": str(refusal_path), "sha256": digest(refusal_raw), "bytes": len(refusal_raw), "category_index": category_index}
        extension = self.source.get("evaluation_paraphrase_extensions")
        self.paraphrase_extensions: list[dict[str, Any]] = []
        self.paraphrase_extension_freeze = None
        if extension is not None:
            extension_path, extension_raw = _artifact(extension)
            self.paraphrase_extensions = [json.loads(line) for line in extension_raw.splitlines() if line]
            self.paraphrase_extension_freeze = {"path": str(extension_path), "sha256": digest(extension_raw), "bytes": len(extension_raw), "records": len(self.paraphrase_extensions)}
        local_id = local_manifest["release_id"]; visual_id = digest(visual_manifest_raw)
        assignments = [_local_assignment(row, local_id, digest(local_manifest_raw)) for row in local_rows]
        assignments += [_visual_assignment(row, visual_id, digest(visual_manifest_raw)) for row in visual_rows]
        return assignments, {"local": {"release_id": local_id, "manifest_sha256": digest(local_manifest_raw), "records_sha256": digest(local_records_raw)},
            "visual": {"release_id": visual_id, "manifest_sha256": digest(visual_manifest_raw), "records_sha256": digest(visual_records_raw)}}

    def run(self) -> dict[str, Any]:
        self.output.mkdir(parents=True); wall_start = time.perf_counter(); self_start = resource.getrusage(resource.RUSAGE_SELF); child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
        assignments, authorities = self._load()
        validate_assignments(assignments, {"local_operational": 20, "visual_identity": 14})
        families: dict[str, list[dict[str, Any]]] = defaultdict(list); groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in assignments: families[row["paraphrase_family_id"]].append(row); groups[row["source_group_id"]].append(row)
        split_by_group = _assign_splits(assignments)
        split_by_family = {family: split_by_group[values[0]["source_group_id"]] for family, values in families.items()}
        if any(len({split_by_group[row["source_group_id"]] for row in values}) != 1 for values in families.values()): raise ValueError("family crosses split")
        phrase_splits: dict[str, set[str]] = defaultdict(set); target_splits: dict[str, set[str]] = defaultdict(set); path_splits: dict[str, set[str]] = defaultdict(set)
        for row in assignments:
            split = split_by_group[row["source_group_id"]]
            phrase_splits[row["phrase_sha256"]].add(split); target_splits[row["target_identity"]].add(split)
            if row["relation_path_hash"] is not None: path_splits[row["relation_path_hash"]].add(split)
        if any(len(values) != 1 for mapping in (phrase_splits, target_splits, path_splits) for values in mapping.values()): raise ValueError("phrase, target, or path leakage")
        pools = {(domain, split): [row for row in assignments if row["domain"] == domain and split_by_group[row["source_group_id"]] == split]
                 for domain in {row["domain"] for row in assignments} for split in SPLITS}
        tasks = [(row, pools[(row["domain"], split_by_group[row["source_group_id"]])], split_by_group[row["source_group_id"]]) for row in assignments]
        if any(not pool for _, pool, _ in tasks): raise ValueError("empty supplied candidate pool")
        if self.workers == 1: records = list(map(_candidate_record, tasks))
        else:
            with ProcessPoolExecutor(max_workers=self.workers, mp_context=multiprocessing.get_context("fork")) as executor:
                records = list(executor.map(_candidate_record, tasks, chunksize=max(1, len(tasks)//(self.workers*4))))
        records.sort(key=lambda row: row["record_id"])
        assignment_by_id = {row["bridge_record_id"]: row for row in assignments}
        extension_assignments = []
        seen_extension_phrases = set()
        for extension in self.paraphrase_extensions:
            if extension.get("schema") != f"{SCHEMA}:evaluation_paraphrase_extension": raise ValueError("unsupported evaluation paraphrase extension")
            bridge_id = extension.get("canonical_bridge_record_id"); base = assignment_by_id.get(bridge_id)
            if base is None: raise ValueError("paraphrase extension bridge is not frozen authority")
            if split_by_group[base["source_group_id"]] != "evaluation": raise ValueError("paraphrase extension may bind only an evaluation-reserved family")
            if extension.get("source_group_id") != base["source_group_id"] or extension.get("paraphrase_family_id") != base["paraphrase_family_id"] or extension.get("domain") != base["domain"]:
                raise ValueError("paraphrase extension membership differs from canonical evaluation record")
            phrase = extension.get("phrase")
            if not isinstance(phrase, str) or not phrase or phrase == base["phrase"] or extension.get("phrase_sha256") != digest(phrase.encode()):
                raise ValueError("paraphrase extension must preserve a distinct exact phrase identity")
            if extension.get("assignment_evidence") != "explicit_user_authorized_evaluation_only_paraphrase": raise ValueError("paraphrase extension lacks explicit assignment evidence")
            if phrase in seen_extension_phrases or any(row["phrase"] == phrase for row in assignments): raise ValueError("duplicate paraphrase extension phrase")
            seen_extension_phrases.add(phrase); derived = dict(base); derived["phrase"] = phrase; derived["phrase_sha256"] = extension["phrase_sha256"]
            derived["extension_identity"] = digest(extension); extension_assignments.append(derived)
        extension_tasks = [(row, pools[(row["domain"], "evaluation")], "evaluation") for row in extension_assignments]
        if self.workers == 1: extension_records = list(map(_candidate_record, extension_tasks))
        else:
            with ProcessPoolExecutor(max_workers=self.workers, mp_context=multiprocessing.get_context("fork")) as executor:
                extension_records = list(executor.map(_candidate_record, extension_tasks, chunksize=max(1, len(extension_tasks)//(self.workers*4))))
        extension_records.sort(key=lambda row: row["record_id"])
        # Evaluation content stays sealed: checks receive identities and hashes only.
        published = {split: [row for row in records if row["split"] == split] for split in ("train", "validation")}
        evaluation = sorted([row for row in records if row["split"] == "evaluation"] + extension_records, key=lambda row: row["record_id"])
        evaluation_reservations = [{"record_id": row["record_id"], "domain": row["domain"], "source_group_id": row["source_group_id"],
            "paraphrase_family_id": row["paraphrase_family_id"], "phrase_sha256": row["phrase_sha256"],
            "target_identity": next(item["target_identity"] for item in assignments if item["bridge_record_id"] == row["expected_outcome"]["bridge_record_id"]),
            "sealed_record_sha256": digest(row), "eligibility": "EVALUATION_RESERVED"} for row in evaluation]
        refusal_reservations = [{"reservation_id": digest({"category": category, "sealed_record_sha256": record_hash, "source_artifact_sha256": self.refusal_freeze["sha256"]}),
            "category": category, "sealed_record_sha256": record_hash, "sealed_source_artifact_sha256": self.refusal_freeze["sha256"],
            "eligibility": "EVALUATION_RESERVED", "payload_status": "SEALED_NOT_OPENED_BY_PREREQUISITE_CHECKS"} for category, record_hash in sorted(self.refusal_freeze["category_index"].items())]
        assignment_manifest = {"schema": f"{SCHEMA}:assignment_manifest", "law": "explicit documented provenance and target meaning; no string-similarity assignment",
            "assignments": sorted([{key: row[key] for key in ("domain", "bridge_record_id", "phrase", "phrase_sha256", "target_identity", "relation_path_hash", "source_group_id", "paraphrase_family_id", "assignment_evidence")} for row in assignments], key=canonical)}
        if extension_assignments:
            assignment_manifest["evaluation_paraphrase_extensions"] = sorted([{key: row[key] for key in ("domain", "bridge_record_id", "phrase", "phrase_sha256", "target_identity", "relation_path_hash", "source_group_id", "paraphrase_family_id", "extension_identity")} for row in extension_assignments], key=canonical)
        split_manifest = {"schema": f"{SCHEMA}:split_manifest", "law": "source groups, families, exact phrases, targets, and relation paths never cross splits",
            "source_group_splits": dict(sorted(split_by_group.items())), "paraphrase_family_splits": dict(sorted(split_by_family.items())),
            "evaluation_content_opened": False, "domain_counts": {domain: {split: sum(row["domain"] == domain and split_by_group[row["source_group_id"]] == split for row in assignments) + (sum(row["domain"] == domain for row in extension_assignments) if split == "evaluation" else 0) for split in SPLITS} for domain in sorted({row["domain"] for row in assignments})}}
        if extension_assignments:
            split_manifest["evaluation_paraphrase_extension_count"] = len(extension_assignments)
            split_manifest["evaluation_paraphrase_family_pairs"] = {family: 1 + sum(row["paraphrase_family_id"] == family for row in extension_assignments) for family, split in sorted(split_by_family.items()) if split == "evaluation"}
        artifacts = {"assignments": _write_json(self.output/"assignment-manifest.json", assignment_manifest),
            "split_manifest": _write_json(self.output/"split-manifest.json", split_manifest),
            "train": _write_jsonl(self.output/"splits/train.jsonl", published["train"]),
            "validation": _write_jsonl(self.output/"splits/validation.jsonl", published["validation"]),
            "evaluation_reservations": _write_jsonl(self.output/"reservations/evaluation.jsonl", evaluation_reservations),
            "refusal_reservations": _write_jsonl(self.output/"reservations/refusal-evaluation.jsonl", refusal_reservations)}
        representation = {"schema": f"{SCHEMA}:representation_contract", "canonical_serialization": "UTF-8 JSON sorted keys compact separators no normalization; JSONL LF",
            "candidate_identity_law": "candidate_set identity hashes sorted bridge record IDs; input order is non-semantic",
            "expected_outcome_law": "selected existing bridge_record_id or explicit non-target status",
            "permitted_model_output": "index of one supplied candidate or non-target status only",
            "forbidden_model_outputs": ["identifier", "hash", "relationship", "operation", "evidence", "authority"],
            "resolver_verification_required": True}
        artifacts["representation"] = _write_json(self.output/"representation-contract.json", representation)
        manifest = {"schema": SCHEMA, "classification": "PREREQUISITES_ONLY_NOT_TRAINED", "source_manifest_sha256": digest(self.source_bytes),
            "authorities": authorities, "sealed_refusal_evaluation": {key: self.refusal_freeze[key] for key in ("path", "sha256", "bytes")},
            "records": len(records) + len(extension_records), "evaluation_records_opened": False,
            "training_performed": False, "optimizer_updates": 0, "checkpoints_created": 0, "training_execution_allowed_changed": False,
            "generic_hf_mixed": False, "artifacts": artifacts}
        if extension_assignments:
            manifest["evaluation_paraphrase_extensions"] = self.paraphrase_extension_freeze
            manifest["base_bridge_records"] = len(records)
            manifest["evaluation_paraphrase_records"] = len(extension_records)
        _write_json(self.output/"manifest.json", manifest)
        wall = time.perf_counter()-wall_start; self_end=resource.getrusage(resource.RUSAGE_SELF); child_end=resource.getrusage(resource.RUSAGE_CHILDREN)
        _write_json(self.output/"performance-receipt.json", {"schema": f"{SCHEMA}:performance_receipt", "workers": self.workers, "logical_cpus": os.cpu_count(), "elapsed_wall_seconds": wall,
            "aggregate_cpu_seconds": (self_end.ru_utime+self_end.ru_stime-self_start.ru_utime-self_start.ru_stime)+(child_end.ru_utime+child_end.ru_stime-child_start.ru_utime-child_start.ru_stime),
            "records_per_second": len(records)/wall if wall else 0, "maximum_resident_kib": max(self_end.ru_maxrss, child_end.ru_maxrss)})
        return manifest


def build_steering_prerequisites(source_manifest: Path, output_root: Path, workers: int = 24) -> dict[str, Any]:
    return SteeringPrerequisiteBuilder(source_manifest, output_root, workers).run()
