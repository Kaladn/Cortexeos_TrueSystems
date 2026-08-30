"""Deterministic language bridges to a frozen TrueVision visual-identity release.

The bridge can select existing visual units and relationships.  It cannot add
visual facts, interpret appearance, execute TrueVision, or create authority.
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


SCHEMA = "truevision_language_visual_identity_bridges@1"
VISUAL_SCHEMA = "truevision_visual_identity_intake@1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
LOCATION = re.compile(r"\bframe (-?\d+), row (-?\d+), column (-?\d+)\b", re.IGNORECASE)
COORDINATE_ONLY = re.compile(r"\brow (\d+), column (\d+)\b", re.IGNORECASE)
RELATION_WORDS = {
    "contained_in": "contained in", "adjacent_to": "adjacent to",
    "before": "before", "after": "after", "persists_to": "persists",
    "changes_to": "changes",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: bytes | dict | list) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    raw = canonical(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    return {"path": path.name, "sha256": digest(raw), "bytes": len(raw), "records": 1}


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    material = list(rows); raw = b"".join(canonical(row) + b"\n" for row in material)
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    return {"path": path.name, "sha256": digest(raw), "bytes": len(raw), "records": len(material)}


def _artifact(item: dict[str, Any]) -> tuple[Path, bytes]:
    path = Path(str(item.get("path") or "")).resolve(); raw = path.read_bytes()
    if item.get("sha256") != digest(raw) or item.get("bytes") != len(raw):
        raise ValueError(f"frozen artifact mismatch: {path}")
    return path, raw


def _citation(unit: dict[str, Any]) -> dict[str, Any]:
    return {
        "unit_id": unit["unit_id"], "frame_id": unit["frame_id"],
        "frame_number": unit["frame_number"], "frame_order_index": unit["frame_order_index"],
        "observed_at_utc": unit["observed_at_utc"], "coordinates": unit["coordinates"],
        "native_state_sha256": unit["native_state"]["exact_bytes_sha256"],
        "native_state_byte_offset": unit["native_state"]["byte_offset_in_chunk"],
        "artifact_identity": unit["artifact_identity"],
    }


def _bridge_task(task: tuple[dict[str, Any], dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    row, frozen = task
    base = {"schema": f"{SCHEMA}:rejected", "case_id": row.get("case_id"), "phrase": row.get("phrase")}
    phrase = row.get("phrase"); span = row.get("phrase_span")
    if not isinstance(phrase, str) or not phrase or not isinstance(span, list) or len(span) != 2 or span != [0, len(phrase)]:
        return "rejected", {**base, "reason": "invalid_phrase_or_exact_span"}
    if row.get("unsupported_appearance_claim"):
        return "rejected", {**base, "reason": "unsupported_object_name_or_visual_meaning"}
    explicit_location = LOCATION.search(phrase)
    if explicit_location is not None:
        frame, grid_row, grid_column = map(int, explicit_location.groups())
        rows, columns = frozen["grid_shape"]
        if grid_row < 0 or grid_row >= rows or grid_column < 0 or grid_column >= columns:
            return "rejected", {**base, "reason": "invalid_coordinate", "coordinate": [grid_row, grid_column], "grid_shape": frozen["grid_shape"]}
    candidates = row.get("candidate_target_hashes")
    if candidates is not None:
        if not isinstance(candidates, list) or len(candidates) < 2 or any(value not in frozen["targets"] for value in candidates):
            return "rejected", {**base, "reason": "ambiguous_candidate_set_does_not_verify"}
        match = COORDINATE_ONLY.search(phrase)
        candidate_rows = [frozen["units"].get(value) for value in candidates]
        if match is None or any(value is None for value in candidate_rows):
            return "rejected", {**base, "reason": "ambiguous_phrase_does_not_locate_visual_units"}
        coordinate = tuple(map(int, match.groups()))
        if any((value["coordinates"]["grid_row"], value["coordinates"]["grid_column"]) != coordinate for value in candidate_rows):
            return "rejected", {**base, "reason": "ambiguous_candidates_do_not_share_phrase_coordinate"}
        return "quarantined", {
            "schema": f"{SCHEMA}:quarantined", "case_id": row.get("case_id"), "phrase": phrase,
            "phrase_span": span, "reason": "multiple_plausible_frozen_visual_targets",
            "candidate_target_hashes": sorted(candidates), "visual_release_sha256": frozen["manifest_sha256"],
        }
    target_hash = row.get("target_hash")
    if not isinstance(target_hash, str) or not SHA256.fullmatch(target_hash):
        return "rejected", {**base, "reason": "invalid_or_missing_target_hash", "target_hash": target_hash}
    target = frozen["targets"].get(target_hash)
    if target is None:
        match = LOCATION.search(phrase)
        reason = "target_hash_not_in_frozen_visual_release"
        if match is not None:
            frame, grid_row, grid_column = map(int, match.groups())
            rows, columns = frozen["grid_shape"]
            if frame not in frozen["frame_numbers"]: reason = "missing_frame"
            elif grid_row < 0 or grid_row >= rows or grid_column < 0 or grid_column >= columns: reason = "invalid_coordinate"
            elif (frame, grid_row, grid_column) not in frozen["units_by_coordinate"]: reason = "missing_visual_unit"
            else: reason = "stale_target_hash"
        return "rejected", {**base, "reason": reason, "target_hash": target_hash}

    target_kind = "visual_unit" if target.get("schema") == f"{VISUAL_SCHEMA}:visual_unit" else "visual_relationship"
    if row.get("target_kind") != target_kind:
        return "rejected", {**base, "reason": "target_kind_mismatch", "target_hash": target_hash}
    if target_kind == "visual_unit":
        match = LOCATION.search(phrase)
        coords = target["coordinates"]
        expected = (target["frame_number"], coords["grid_row"], coords["grid_column"])
        if match is None or tuple(map(int, match.groups())) != expected:
            return "rejected", {**base, "reason": "phrase_location_does_not_prove_target", "target_hash": target_hash}
        citations = [_citation(target)]; path = row.get("relationship_path") or []
    else:
        relation = target["relationship"]
        if RELATION_WORDS[relation] not in phrase.lower():
            return "rejected", {**base, "reason": "phrase_relation_does_not_prove_target", "target_hash": target_hash}
        path = row.get("relationship_path")
        if path != [target_hash]:
            return "rejected", {**base, "reason": "relationship_path_not_exact_frozen_path", "target_hash": target_hash}
        referenced = [target.get(key) for key in ("source_unit_id", "target_unit_id") if target.get(key)]
        citations = [_citation(frozen["units"][value]) for value in referenced]
        for frame_key in ("source_frame_id", "target_frame_id"):
            frame_id = target.get(frame_key)
            if frame_id:
                citations.append(frozen["frames"][frame_id])
    if any(step not in frozen["relationship_ids"] for step in path):
        return "rejected", {**base, "reason": "relationship_path_contains_unfrozen_relationship", "target_hash": target_hash}
    record = {
        "schema": f"{SCHEMA}:bridge", "namespace": "LANGUAGE_TO_VISUAL_IDENTITY_BRIDGES",
        "classification": "READ_ONLY_EXPLICIT_FROZEN_VISUAL_BINDING", "phrase": phrase,
        "phrase_span": span, "target_kind": target_kind, "target_hash": target_hash,
        "target_record": target, "verified_relationship_path": path, "citations": citations,
        "visual_release": {"manifest_sha256": frozen["manifest_sha256"], "accepted_ledger_sha256": frozen["accepted_sha256"]},
        "identity_classification": target.get("identity_classification"),
        "boundaries": {"object_name_inferred": False, "class_inferred": False, "caption_inferred": False,
                       "meaning_inferred": False, "appearance_identity_inferred": False,
                       "relationship_created": False, "operation_executed": False,
                       "generic_hf_used_as_truth": False, "model_training_performed": False},
    }
    record["bridge_id"] = digest(record)
    return "accepted", record


class LanguageVisualIdentityBridgeIntake:
    def __init__(self, source_manifest: Path, output_root: Path, workers: int = 24):
        if workers < 1: raise ValueError("workers must be at least 1")
        self.source_path = source_manifest.resolve(); self.source_bytes = self.source_path.read_bytes()
        self.source = json.loads(self.source_bytes); self.output = output_root.resolve(); self.workers = workers
        if self.output.exists(): raise FileExistsError(f"output root already exists: {self.output}")

    def _freeze(self) -> dict[str, Any]:
        if self.source.get("schema") != f"{SCHEMA}:source_manifest": raise ValueError("unsupported source manifest")
        if self.source.get("namespace") != "LANGUAGE_TO_VISUAL_IDENTITY_BRIDGES": raise ValueError("wrong bridge namespace")
        visual = self.source.get("frozen_visual_release") or {}
        manifest_path, manifest_raw = _artifact(visual.get("manifest") or {})
        accepted_path, accepted_raw = _artifact(visual.get("accepted_ledger") or {})
        manifest = json.loads(manifest_raw)
        if manifest.get("schema") != VISUAL_SCHEMA or manifest.get("classification") != "READ_ONLY_NATIVE_TRUEVISION_VISUAL_IDENTITY_NOT_TRAINED":
            raise ValueError("frozen release is not the required TrueVision visual identity authority")
        declared = manifest.get("artifacts", {}).get("accepted", {})
        if declared.get("sha256") != digest(accepted_raw) or declared.get("bytes") != len(accepted_raw):
            raise ValueError("accepted ledger is not bound by frozen visual manifest")
        rows = [json.loads(line) for line in accepted_raw.splitlines() if line]
        units = {row["unit_id"]: row for row in rows if row.get("schema") == f"{VISUAL_SCHEMA}:visual_unit"}
        relations = {row["relationship_id"]: row for row in rows if row.get("schema") == f"{VISUAL_SCHEMA}:relationship"}
        if len(units) + len(relations) != len(rows): raise ValueError("unsupported record in frozen accepted ledger")
        frames: dict[str, dict[str, Any]] = {}
        for unit in units.values():
            frames.setdefault(unit["frame_id"], {"frame_id": unit["frame_id"], "frame_number": unit["frame_number"],
                "frame_order_index": unit["frame_order_index"], "observed_at_utc": unit["observed_at_utc"]})
        unit_values = list(units.values())
        grid_shape = unit_values[0]["coordinates"]["grid_shape"] if unit_values else None
        if not grid_shape or any(unit["coordinates"]["grid_shape"] != grid_shape for unit in unit_values):
            raise ValueError("frozen visual units do not share one native grid geometry")
        units_by_coordinate = {(unit["frame_number"], unit["coordinates"]["grid_row"], unit["coordinates"]["grid_column"]): unit for unit in unit_values}
        return {"targets": {**units, **relations}, "units": units, "relationship_ids": set(relations), "frames": frames,
                "frame_numbers": {unit["frame_number"] for unit in unit_values}, "grid_shape": grid_shape,
                "units_by_coordinate": units_by_coordinate,
                "manifest_path": str(manifest_path), "accepted_path": str(accepted_path),
                "manifest_sha256": digest(manifest_raw), "accepted_sha256": digest(accepted_raw)}

    def run(self) -> dict[str, Any]:
        self.output.mkdir(parents=True); wall_start = time.perf_counter()
        self_start = resource.getrusage(resource.RUSAGE_SELF); child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
        frozen = self._freeze(); rows = self.source.get("bridge_cases")
        if not isinstance(rows, list) or not rows: raise ValueError("source manifest requires fixed bridge_cases")
        tasks = [(row, frozen) for row in rows]
        if self.workers == 1: results = list(map(_bridge_task, tasks))
        else:
            with ProcessPoolExecutor(max_workers=self.workers, mp_context=multiprocessing.get_context("fork")) as executor:
                results = list(executor.map(_bridge_task, tasks, chunksize=max(1, len(tasks) // (self.workers * 4))))
        ledgers = {name: sorted((row for status, row in results if status == name), key=canonical) for name in ("accepted", "quarantined", "rejected")}
        artifacts = {name: _write_jsonl(self.output / "ledgers" / f"{name}.jsonl", values) for name, values in ledgers.items()}
        relationship_counts: dict[str, int] = {}
        identity_counts: dict[str, int] = {}
        for row in ledgers["accepted"]:
            relation = row["target_record"].get("relationship")
            if relation: relationship_counts[relation] = relationship_counts.get(relation, 0) + 1
            identity = row.get("identity_classification")
            if identity: identity_counts[identity] = identity_counts.get(identity, 0) + 1
        report = {"schema": f"{SCHEMA}:verification_report", "accepted": len(ledgers["accepted"]),
            "quarantined": len(ledgers["quarantined"]), "rejected": len(ledgers["rejected"]),
            "relationship_counts": dict(sorted(relationship_counts.items())), "identity_classification_counts": dict(sorted(identity_counts.items())),
            "frozen_visual_release": {key: frozen[key] for key in ("manifest_path", "manifest_sha256", "accepted_path", "accepted_sha256")},
            "new_visual_relationships_created": 0, "appearance_meanings_inferred": 0, "operations_executed": 0,
            "generic_hf_records_used": 0, "model_training_performed": False}
        artifacts["report"] = _write_json(self.output / "verification-report.json", report)
        manifest = {"schema": SCHEMA, "namespace": "LANGUAGE_TO_VISUAL_IDENTITY_BRIDGES",
            "classification": "READ_ONLY_FROZEN_VISUAL_BINDINGS_NOT_TRAINED", "source_manifest_sha256": digest(self.source_bytes),
            "source_text_normalization": "none", "visual_state_normalization": "none", "artifacts": artifacts,
            "new_visual_relationships_created": 0, "operations_executed": 0, "generic_hf_data_mixed": False,
            "local_operation_authority_created": False, "model_training_performed": False}
        _write_json(self.output / "manifest.json", manifest)
        self_end = resource.getrusage(resource.RUSAGE_SELF); child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
        wall = time.perf_counter() - wall_start
        _write_json(self.output / "performance-receipt.json", {"schema": f"{SCHEMA}:performance_receipt", "workers": self.workers,
            "logical_cpus": os.cpu_count(), "elapsed_wall_seconds": wall,
            "aggregate_cpu_seconds": (self_end.ru_utime+self_end.ru_stime-self_start.ru_utime-self_start.ru_stime)+(child_end.ru_utime+child_end.ru_stime-child_start.ru_utime-child_start.ru_stime),
            "cases_per_second": len(rows)/wall if wall else 0.0, "maximum_resident_kib": max(self_end.ru_maxrss, child_end.ru_maxrss)})
        return manifest


def build_language_visual_identity_bridges(source_manifest: Path, output_root: Path, workers: int = 24) -> dict[str, Any]:
    return LanguageVisualIdentityBridgeIntake(source_manifest, output_root, workers).run()
