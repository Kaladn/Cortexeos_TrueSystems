"""Deterministic visual identity/continuity intake from native TrueVision state."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import resource
import struct
import time
from typing import Any, Iterable

from truevision_runtime.state_source_law import classify_artifact_authority


SCHEMA = "truevision_visual_identity_intake@1"
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


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


def _verify_artifact(artifact: dict[str, Any], *, allowed_suffixes: set[str]) -> tuple[Path, bytes]:
    path = Path(str(artifact.get("path") or "")).resolve()
    if path.suffix not in allowed_suffixes:
        raise ValueError(f"artifact type is outside native TrueVision authority: {path}")
    raw = path.read_bytes()
    if artifact.get("sha256") != digest(raw) or artifact.get("bytes") != len(raw):
        raise ValueError(f"artifact hash or byte count mismatch: {path}")
    authority = classify_artifact_authority(path)
    if not authority["source_truth_allowed"]:
        raise ValueError(f"artifact is not TrueVision source truth: {path}")
    return path, raw


def _cell_task(task: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    request, frozen = task
    row = request["row"]
    column = request["column"]
    frame_index = request["frame_index"]
    frame = frozen["frames"][frame_index]
    cell_bytes = frozen["cell_bytes"]
    frame_bytes = frozen["frame_bytes"]
    offset = frozen["payload_offset"] + frame_index * frame_bytes + (row * frozen["columns"] + column) * cell_bytes
    raw_state = frozen["chunk_bytes"][offset:offset + cell_bytes]
    timestamp = frozen["frame_records"][frame_index]["observed_at_utc"]
    frame_number = frozen["frame_numbers"][frame_index]
    unit = {
        "schema": f"{SCHEMA}:visual_unit", "classification": "existing_native_state_unit",
        "source_truth": "TrueVision_native_state", "appearance_semantics": None,
        "run_id": frozen["run_id"], "frame_number": frame_number,
        "frame_order_index": frame_index, "observed_at_utc": timestamp,
        "coordinates": {
            "grid_row": row, "grid_column": column,
            "grid_shape": [frozen["rows"], frozen["columns"]],
            "capture_pixel_bounds_xyxy": [
                column * frozen["cell_width"], row * frozen["cell_height"],
                (column + 1) * frozen["cell_width"], (row + 1) * frozen["cell_height"],
            ],
        },
        "native_state": {
            "format": "tvcells_f32le_v1", "feature_names": frozen["feature_names"],
            "feature_count": frozen["feature_count"], "byte_offset_in_chunk": offset,
            "byte_length": cell_bytes, "exact_bytes_sha256": digest(raw_state),
            "exact_bytes_hex": raw_state.hex(),
        },
        "artifact_identity": {
            "manifest_sha256": frozen["manifest_sha256"],
            "records_sha256": frozen["records_sha256"],
            "chunk_sha256": frozen["chunk_sha256"], "chunk_path": frozen["chunk_path"],
        },
        "boundaries": {
            "object_name_inferred": False, "class_inferred": False,
            "meaning_inferred": False, "appearance_identity_inferred": False,
        },
    }
    unit["unit_id"] = digest(unit)
    unit["frame_id"] = frame["frame_id"]
    return unit


class VisualIdentityIntake:
    def __init__(self, experiment_manifest: Path, output_root: Path, workers: int = 24):
        if workers < 1:
            raise ValueError("workers must be at least 1")
        self.experiment_manifest_path = experiment_manifest.resolve()
        self.experiment_manifest_bytes = self.experiment_manifest_path.read_bytes()
        self.experiment = json.loads(self.experiment_manifest_bytes)
        self.output_root = output_root.resolve()
        if self.output_root.exists():
            raise FileExistsError(f"output root already exists: {self.output_root}")
        self.workers = workers

    def _load_authority(self) -> dict[str, Any]:
        if self.experiment.get("schema") != f"{SCHEMA}:experiment_manifest":
            raise ValueError("unsupported visual identity experiment schema")
        contracts = self.experiment.get("authority_contracts")
        if not isinstance(contracts, list) or not contracts:
            raise ValueError("experiment requires frozen TrueVision contracts")
        verified_contracts = []
        for artifact in contracts:
            path = Path(str(artifact.get("path") or "")).resolve()
            raw = path.read_bytes()
            if digest(raw) != artifact.get("sha256") or len(raw) != artifact.get("bytes"):
                raise ValueError(f"TrueVision contract changed: {path}")
            verified_contracts.append({"path": str(path), "sha256": digest(raw), "bytes": len(raw)})
        manifest_path, manifest_bytes = _verify_artifact(self.experiment["source_manifest"], allowed_suffixes={".json"})
        records_path, records_bytes = _verify_artifact(self.experiment["source_records"], allowed_suffixes={".jsonl"})
        manifest = json.loads(manifest_bytes)
        if manifest.get("record_kind") != "truevision_native_rs_frame_state" or manifest.get("cell_state", {}).get("format") != "tvcells_f32le_v1":
            raise ValueError("source manifest is not native TrueVision frame state")
        if manifest.get("boundary", {}).get("raw_frame_saved") is not False or manifest.get("boundary", {}).get("generated_media_is_evidence") is not False:
            raise ValueError("source manifest violates TrueVision state boundary")
        records = [json.loads(line) for line in records_bytes.splitlines() if line]
        expected_frames = manifest.get("summary", {}).get("frame_count")
        if len(records) != expected_frames or [row.get("frame_number") for row in records] != list(range(len(records))):
            raise ValueError("records do not preserve complete zero-based frame order")
        if not all(UTC.fullmatch(str(row.get("observed_at_utc", ""))) for row in records):
            raise ValueError("records contain a non-canonical TrueVision timestamp")
        if any(row.get("raw_frame_saved") is not False or row.get("raw_grid_saved") is not False for row in records):
            raise ValueError("records claim raw frame/grid retention")
        chunks = manifest.get("cell_state", {}).get("chunks") or []
        if len(chunks) != 1:
            raise ValueError("first visual identity experiment requires one fixed native chunk")
        chunk_path, chunk_bytes = _verify_artifact(self.experiment["source_chunk"], allowed_suffixes={".tvcells"})
        declared_chunk = Path(str(chunks[0].get("path") or "")).resolve()
        if declared_chunk != chunk_path:
            raise ValueError("frozen chunk does not match source manifest")
        if chunk_bytes[:8] != b"TVCELL01" or len(chunk_bytes) < 24:
            raise ValueError("invalid native TrueVision chunk header")
        frame_count, rows, columns, feature_count = struct.unpack_from("<4I", chunk_bytes, 8)
        payload_offset = 24 + frame_count * 4
        frame_numbers = list(struct.unpack_from(f"<{frame_count}I", chunk_bytes, 24))
        cell_bytes = feature_count * 4
        frame_bytes = rows * columns * cell_bytes
        if payload_offset + frame_count * frame_bytes != len(chunk_bytes):
            raise ValueError("native chunk byte geometry mismatch")
        if frame_count != len(records) or frame_numbers != [row["frame_number"] for row in records]:
            raise ValueError("native chunk frame order differs from records")
        chunk_meta = chunks[0]
        if [rows, columns] != chunk_meta.get("grid_shape") or feature_count != chunk_meta.get("feature_count"):
            raise ValueError("native chunk geometry differs from manifest")
        resolution = manifest.get("config", {}).get("capture_resolution") or []
        if len(resolution) != 2 or resolution[0] % columns or resolution[1] % rows:
            raise ValueError("capture resolution does not divide exactly into native grid")
        frames = []
        for index, record in enumerate(records):
            frame = {
                "run_id": manifest["run_id"], "frame_number": record["frame_number"],
                "frame_order_index": index, "observed_at_utc": record["observed_at_utc"],
                "elapsed_seconds": record["elapsed_seconds"],
                "manifest_sha256": digest(manifest_bytes), "records_sha256": digest(records_bytes),
            }
            frame["frame_id"] = digest(frame)
            frames.append(frame)
        return {
            "verified_contracts": verified_contracts, "manifest": manifest,
            "manifest_path": str(manifest_path), "manifest_sha256": digest(manifest_bytes),
            "records_path": str(records_path), "records_sha256": digest(records_bytes),
            "chunk_path": str(chunk_path), "chunk_sha256": digest(chunk_bytes), "chunk_bytes": chunk_bytes,
            "run_id": manifest["run_id"], "frame_records": records, "frames": frames,
            "frame_numbers": frame_numbers, "rows": rows, "columns": columns,
            "feature_count": feature_count, "feature_names": manifest["cell_state"]["feature_names"],
            "payload_offset": payload_offset, "cell_bytes": cell_bytes, "frame_bytes": frame_bytes,
            "cell_width": resolution[0] // columns, "cell_height": resolution[1] // rows,
        }

    def run(self) -> dict[str, Any]:
        self.output_root.mkdir(parents=True)
        wall_start = time.perf_counter()
        self_start = resource.getrusage(resource.RUSAGE_SELF)
        child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
        frozen = self._load_authority()
        coordinates = self.experiment.get("selected_coordinates")
        if not isinstance(coordinates, list) or not coordinates:
            raise ValueError("experiment requires selected_coordinates")
        valid_coordinates = []
        rejected = []
        for index, coordinate in enumerate(coordinates):
            if not isinstance(coordinate, list) or len(coordinate) != 2 or not all(isinstance(value, int) for value in coordinate):
                rejected.append({"schema": f"{SCHEMA}:rejected", "case": "selected_coordinate", "coordinate_index": index, "reason": "invalid_coordinate_shape", "coordinate": coordinate})
                continue
            row, column = coordinate
            if row < 0 or row >= frozen["rows"] or column < 0 or column >= frozen["columns"]:
                rejected.append({"schema": f"{SCHEMA}:rejected", "case": "selected_coordinate", "coordinate_index": index, "reason": "invalid_coordinate", "coordinate": coordinate, "grid_shape": [frozen["rows"], frozen["columns"]]})
                continue
            valid_coordinates.append((row, column))
        valid_coordinates = sorted(set(valid_coordinates))
        tasks = [({"frame_index": frame, "row": row, "column": column}, frozen) for frame in range(len(frozen["frames"])) for row, column in valid_coordinates]
        if self.workers == 1:
            units = list(map(_cell_task, tasks))
        else:
            context = multiprocessing.get_context("fork")
            with ProcessPoolExecutor(max_workers=self.workers, mp_context=context) as executor:
                units = list(executor.map(_cell_task, tasks, chunksize=max(1, len(tasks) // (self.workers * 4))))
        units.sort(key=lambda row: (row["frame_order_index"], row["coordinates"]["grid_row"], row["coordinates"]["grid_column"]))
        by_key = {(row["frame_order_index"], row["coordinates"]["grid_row"], row["coordinates"]["grid_column"]): row for row in units}
        relations = []
        for unit in units:
            relations.append({
                "schema": f"{SCHEMA}:relationship", "relationship": "contained_in",
                "source_unit_id": unit["unit_id"], "target_frame_id": unit["frame_id"],
                "evidence": "native grid coordinate in manifest-declared frame geometry",
            })
        for frame_index in range(len(frozen["frames"])):
            frame_units = [unit for unit in units if unit["frame_order_index"] == frame_index]
            frame_map = {(unit["coordinates"]["grid_row"], unit["coordinates"]["grid_column"]): unit for unit in frame_units}
            for (row, column), unit in sorted(frame_map.items()):
                for neighbor in ((row, column + 1), (row + 1, column)):
                    if neighbor in frame_map:
                        relations.append({
                            "schema": f"{SCHEMA}:relationship", "relationship": "adjacent_to",
                            "source_unit_id": unit["unit_id"], "target_unit_id": frame_map[neighbor]["unit_id"],
                            "evidence": "cardinally adjacent native grid coordinates in the same frame",
                        })
        for index in range(len(frozen["frames"]) - 1):
            left, right = frozen["frames"][index], frozen["frames"][index + 1]
            relations.extend([
                {"schema": f"{SCHEMA}:relationship", "relationship": "before", "source_frame_id": left["frame_id"], "target_frame_id": right["frame_id"], "evidence": "native frame order"},
                {"schema": f"{SCHEMA}:relationship", "relationship": "after", "source_frame_id": right["frame_id"], "target_frame_id": left["frame_id"], "evidence": "native frame order"},
            ])
            for row, column in valid_coordinates:
                source = by_key[(index, row, column)]
                target = by_key[(index + 1, row, column)]
                same = source["native_state"]["exact_bytes_sha256"] == target["native_state"]["exact_bytes_sha256"]
                relations.append({
                    "schema": f"{SCHEMA}:relationship", "relationship": "persists_to" if same else "changes_to",
                    "identity_classification": "stable_identity" if same else "candidate_continuity",
                    "source_unit_id": source["unit_id"], "target_unit_id": target["unit_id"],
                    "coordinate": [row, column],
                    "evidence": "same coordinate and exact native state bytes" if same else "same coordinate with different exact native state bytes",
                })
        state_locations: dict[str, list[dict[str, int]]] = defaultdict(list)
        for unit in units:
            state_locations[unit["native_state"]["exact_bytes_sha256"]].append({
                "frame_number": unit["frame_number"], "grid_row": unit["coordinates"]["grid_row"], "grid_column": unit["coordinates"]["grid_column"],
            })
        quarantined = []
        for case in self.experiment.get("lookup_cases") or []:
            kind = case.get("kind")
            if kind == "state_hash_lookup":
                locations = state_locations.get(case.get("state_hash"), [])
                if len(locations) > 1:
                    quarantined.append({"schema": f"{SCHEMA}:quarantined", "case_id": case.get("case_id"), "reason": "state_hash_has_multiple_native_locations", "state_hash": case.get("state_hash"), "candidate_locations": locations})
                elif not locations:
                    rejected.append({"schema": f"{SCHEMA}:rejected", "case_id": case.get("case_id"), "reason": "state_hash_missing_from_selected_native_evidence", "state_hash": case.get("state_hash")})
            elif kind == "coordinate_lookup":
                frame = case.get("frame_number"); row = case.get("grid_row"); column = case.get("grid_column")
                if not isinstance(frame, int) or frame not in frozen["frame_numbers"]:
                    rejected.append({"schema": f"{SCHEMA}:rejected", "case_id": case.get("case_id"), "reason": "missing_frame", "frame_number": frame})
                elif not isinstance(row, int) or not isinstance(column, int) or row < 0 or row >= frozen["rows"] or column < 0 or column >= frozen["columns"]:
                    rejected.append({"schema": f"{SCHEMA}:rejected", "case_id": case.get("case_id"), "reason": "invalid_coordinate", "coordinate": [row, column], "grid_shape": [frozen["rows"], frozen["columns"]]})
                elif (frame, row, column) not in by_key:
                    rejected.append({"schema": f"{SCHEMA}:rejected", "case_id": case.get("case_id"), "reason": "coordinate_not_selected_for_experiment", "coordinate": [row, column], "frame_number": frame})
            else:
                rejected.append({"schema": f"{SCHEMA}:rejected", "case_id": case.get("case_id"), "reason": "unsupported_lookup_kind", "kind": kind})
        for relation in relations:
            relation["relationship_id"] = digest(relation)
        accepted = [*units, *sorted(relations, key=canonical)]
        quarantined.sort(key=canonical); rejected.sort(key=canonical)
        artifacts = {
            "accepted": _write_jsonl(self.output_root / "ledgers" / "accepted.jsonl", accepted),
            "quarantined": _write_jsonl(self.output_root / "ledgers" / "quarantined.jsonl", quarantined),
            "rejected": _write_jsonl(self.output_root / "ledgers" / "rejected.jsonl", rejected),
        }
        relation_counts: dict[str, int] = defaultdict(int)
        classification_counts: dict[str, int] = defaultdict(int)
        for row in relations:
            relation_counts[row["relationship"]] += 1
            if row.get("identity_classification"):
                classification_counts[row["identity_classification"]] += 1
        report = {
            "schema": f"{SCHEMA}:verification_report", "source_run_id": frozen["run_id"],
            "source_artifacts": {
                "manifest": {"path": frozen["manifest_path"], "sha256": frozen["manifest_sha256"]},
                "records": {"path": frozen["records_path"], "sha256": frozen["records_sha256"]},
                "chunk": {"path": frozen["chunk_path"], "sha256": frozen["chunk_sha256"]},
            },
            "frames": frozen["frames"], "visual_units": len(units),
            "relationship_counts": dict(sorted(relation_counts.items())),
            "identity_classification_counts": dict(sorted(classification_counts.items())),
            "quarantined": len(quarantined), "rejected": len(rejected),
            "unsupported_relationships": {
                "appears": "not emitted because the fixed native grid contains every selected coordinate in every frame",
                "disappears": "not emitted because the fixed native grid contains every selected coordinate in every frame",
            },
            "object_names_inferred": 0, "classes_inferred": 0, "meanings_inferred": 0,
            "operations_executed": 0, "model_training_performed": False,
            "language_bridge_mixed": False, "local_operation_authority_created": False,
        }
        report_artifact = _write_json(self.output_root / "verification-report.json", report)
        manifest = {
            "schema": SCHEMA, "classification": "READ_ONLY_NATIVE_TRUEVISION_VISUAL_IDENTITY_NOT_TRAINED",
            "experiment_manifest_sha256": digest(self.experiment_manifest_bytes),
            "source_text_or_state_normalization": "none", "native_state_bytes_preserved": True,
            "operations_executed": 0, "model_training_performed": False,
            "external_visual_data_used": False, "language_bridge_mixed": False,
            "local_operation_authority_created": False,
            "artifacts": {**artifacts, "report": report_artifact},
        }
        _write_json(self.output_root / "manifest.json", manifest)
        wall = time.perf_counter() - wall_start
        self_end = resource.getrusage(resource.RUSAGE_SELF); child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (self_end.ru_utime + self_end.ru_stime - self_start.ru_utime - self_start.ru_stime) + (child_end.ru_utime + child_end.ru_stime - child_start.ru_utime - child_start.ru_stime)
        _write_json(self.output_root / "performance-receipt.json", {
            "schema": f"{SCHEMA}:performance_receipt", "workers": self.workers,
            "logical_cpus": os.cpu_count(), "elapsed_wall_seconds": wall,
            "aggregate_cpu_seconds": cpu, "units_per_second": len(units) / wall if wall else 0.0,
            "maximum_resident_kib": max(self_end.ru_maxrss, child_end.ru_maxrss),
        })
        return manifest


def build_visual_identity_intake(experiment_manifest: Path, output_root: Path, workers: int = 24) -> dict[str, Any]:
    return VisualIdentityIntake(experiment_manifest, output_root, workers).run()
