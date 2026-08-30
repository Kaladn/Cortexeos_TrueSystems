"""Deterministic role selection and release construction for code intake."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import time
from typing import Any, Iterable


SELECTION_SCHEMA = "truesystems_training_selection@1"


class TrainingRole(StrEnum):
    RUNTIME_CODE = "RUNTIME_CODE"
    TEST_CODE = "TEST_CODE"
    SCHEMA_CONTRACT = "SCHEMA_CONTRACT"
    CONFIGURATION = "CONFIGURATION"
    DOCUMENTATION = "DOCUMENTATION"
    RESEARCH_REFERENCE = "RESEARCH_REFERENCE"
    SYSTEM_RELATIONSHIP = "SYSTEM_RELATIONSHIP"
    OPERATOR_TRAJECTORY = "OPERATOR_TRAJECTORY"
    FAILURE_RESTRAINT = "FAILURE_RESTRAINT"


class Eligibility(StrEnum):
    TRAIN_ELIGIBLE = "TRAIN_ELIGIBLE"
    VALIDATION_ELIGIBLE = "VALIDATION_ELIGIBLE"
    EVALUATION_RESERVED = "EVALUATION_RESERVED"
    NEVER_TRAIN = "NEVER_TRAIN"


RELEASE_NAMES = (
    "LEVEL_1_CODE_LITERACY",
    "LEVEL_2_SYSTEM_RELATIONSHIPS",
    "EXPECTED_BEHAVIOR",
    "LEVEL_3_OPERATOR_USAGE",
    "FAILURE_RESTRAINT",
    "DOCUMENTATION",
    "RESEARCH_REFERENCE",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: bytes | dict | list) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> dict[str, Any]:
    payload = canonical(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": path.name, "sha256": digest(payload), "bytes": len(payload), "records": 1}


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    payload = b"".join(canonical(row) + b"\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": path.name, "sha256": digest(payload), "bytes": len(payload), "records": payload.count(b"\n")}


def file_role(row: dict[str, Any]) -> tuple[TrainingRole, str]:
    original = row.get("role")
    relative = str(row.get("repository_relative_file", ""))
    payload = str(row.get("exact_payload", ""))
    if original == "research_reference":
        return TrainingRole.RESEARCH_REFERENCE, "explicit intake research/reference role"
    if original == "test":
        return TrainingRole.TEST_CODE, "explicit intake test role"
    if original == "schema":
        return TrainingRole.SCHEMA_CONTRACT, "explicit intake schema role"
    if "contract" in relative.lower() and any(marker in payload for marker in ("class ", "raise ", "# Contract", "# System contract", "## Contract")):
        return TrainingRole.SCHEMA_CONTRACT, "contract path corroborated by contract-shaped source content"
    if original == "configuration_or_manifest":
        try:
            decoded = json.loads(payload) if relative.lower().endswith((".json", ".jsonl")) else None
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict) and any(key in decoded for key in ("$schema", "schema", "contract")):
            return TrainingRole.SCHEMA_CONTRACT, "structured source declares schema/contract field"
        return TrainingRole.CONFIGURATION, "explicit intake configuration/manifest role"
    if original == "documentation":
        return TrainingRole.DOCUMENTATION, "explicit intake documentation role"
    return TrainingRole.RUNTIME_CODE, "source file admitted as runtime/source code"


def eligibility_for(role: TrainingRole, record_hash: str, reservations: dict[str, str]) -> tuple[str, bool, str]:
    if record_hash in reservations:
        value = Eligibility(reservations[record_hash])
        return value.value, value not in {Eligibility.EVALUATION_RESERVED, Eligibility.NEVER_TRAIN}, "explicit reservation manifest"
    if role == TrainingRole.RESEARCH_REFERENCE:
        return Eligibility.NEVER_TRAIN.value, False, "research requires an explicit future gated release decision"
    if role == TrainingRole.TEST_CODE:
        return "UNASSIGNED_SPLIT_REQUIRED", False, "test origin must be reserved or explicitly admitted before training"
    return Eligibility.TRAIN_ELIGIBLE.value, True, "default non-test operational eligibility"


def load_reservations(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records", payload)
    if not isinstance(rows, dict):
        raise ValueError("reservation manifest records must be an object")
    for value in rows.values():
        Eligibility(value)
    return {str(key): str(value) for key, value in rows.items()}


def duplicate_groups(level_one: list[tuple[str, dict[str, Any], dict[str, Any]]]) -> tuple[list[dict], dict[str, str]]:
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for component, row, provenance in level_one:
        schema = row.get("schema", "")
        if schema.endswith(":source_file"):
            key = ("exact_file_bytes", str(row["source_sha256"]))
        elif schema.endswith(":code_unit"):
            key = ("exact_symbol_payload", digest(str(row.get("source_payload", "")).encode("utf-8")))
        else:
            continue
        candidates[key].append({"component": component, "record_hash": digest(row), "symbol": row.get("symbol"), **provenance})
    groups = []
    member_to_group: dict[str, str] = {}
    for (kind, content_hash), members in sorted(candidates.items()):
        unique = sorted(members, key=canonical)
        if len(unique) < 2:
            continue
        roles = {member.get("original_role") for member in unique}
        if roles == {"test"}: group_kind = "repeated_test_fixture"
        elif roles == {"documentation"}: group_kind = "mirrored_documentation"
        else: group_kind = kind
        group_id = digest({"schema": SELECTION_SCHEMA, "kind": group_kind, "content_hash": content_hash, "members": unique})
        group = {"schema": f"{SELECTION_SCHEMA}:duplicate_group", "duplicate_group_id": group_id, "kind": group_kind, "content_hash": content_hash, "canonical_record_hash": unique[0]["record_hash"], "members": unique}
        groups.append(group)
        for member in unique: member_to_group[member["record_hash"]] = group_id
    return groups, member_to_group


def envelope(*, component: str, row: dict[str, Any], original_role: str, training_role: TrainingRole, reason: str, provenance: dict[str, Any], source: dict[str, Any] | None, reservations: dict[str, str], duplicate_group: str | None = None, parent_relationships: list[dict] | None = None) -> dict[str, Any]:
    record_hash = digest(row)
    eligibility, allowed, eligibility_reason = eligibility_for(training_role, record_hash, reservations)
    result = {
        "schema": f"{SELECTION_SCHEMA}:release_record",
        "record_hash": record_hash,
        "source_system": component,
        "repository_identity": source.get("repository_commit") if source else None,
        "source_identity": source.get("source_sha256") if source else row.get("source_sha256"),
        "file_coordinates": {
            "path": row.get("repository_relative_file") or (source or {}).get("repository_relative_file"),
            "line_start": row.get("line_start"), "line_end": row.get("line_end"),
        },
        "original_role": original_role,
        "training_role": training_role.value,
        "selection_reason": reason,
        "exclusion_reason": None,
        "eligibility": eligibility,
        "training_admission_allowed": allowed,
        "eligibility_reason": eligibility_reason,
        "duplicate_group_id": duplicate_group,
        "parent_source_relationships": parent_relationships or [],
        "input_provenance": provenance,
        "original_record": row,
    }
    result["selection_record_hash"] = digest(result)
    return result


_SELECT_UNITS: dict[tuple[str, str], dict] = {}
_SELECT_UNIT_ROLES: dict[tuple[str, str], tuple[TrainingRole, str, dict]] = {}
_SELECT_SOURCES: dict[tuple[str, str], dict] = {}
_SELECT_RESERVATIONS: dict[str, str] = {}


def _relationship_worker(task: tuple[str, str, dict, dict, str, str]) -> tuple[str, dict]:
    task_kind, component, row, provenance, identity, relation_kind = task
    if task_kind in {"call", "state"}:
        caller = _SELECT_UNITS[(component, identity)]
        role, _reason, source = _SELECT_UNIT_ROLES[(component, identity)]
        training_role = TrainingRole.RESEARCH_REFERENCE if role == TrainingRole.RESEARCH_REFERENCE else TrainingRole.SYSTEM_RELATIONSHIP
        selected = envelope(component=component, row=row, original_role=relation_kind, training_role=training_role, reason=f"source-observed {relation_kind} relationship", provenance=provenance, source=source, reservations=_SELECT_RESERVATIONS, parent_relationships=[{"relationship": "caller", "record_hash": digest(caller)}, {"relationship": "source_file", "record_hash": digest(source)}])
        return task_kind, selected
    source = _SELECT_SOURCES[(component, identity)]
    role, _reason = file_role(source)
    training_role = TrainingRole.RESEARCH_REFERENCE if role == TrainingRole.RESEARCH_REFERENCE else TrainingRole.SYSTEM_RELATIONSHIP
    selected = envelope(component=component, row=row, original_role=relation_kind, training_role=training_role, reason="source-observed import relationship", provenance=provenance, source=source, reservations=_SELECT_RESERVATIONS, parent_relationships=[{"relationship": "source_file", "record_hash": digest(source)}])
    return task_kind, selected


class SelectionBuilder:
    def __init__(self, corpus_root: Path, output_root: Path, reservation_manifest: Path | None = None, workers: int = 24):
        self.corpus_root = corpus_root.resolve()
        self.output_root = output_root.resolve()
        self.reservations = load_reservations(reservation_manifest)
        if workers < 1: raise ValueError("workers must be at least 1")
        self.workers = workers
        if self.output_root.exists():
            raise FileExistsError(f"output root already exists: {self.output_root}")
        self.input_manifest = json.loads((self.corpus_root / "manifest.json").read_text(encoding="utf-8"))
        self.releases: dict[str, list[dict]] = {name: [] for name in RELEASE_NAMES}
        self.exclusions: list[dict] = []
        self.level_one: list[tuple[str, dict, dict]] = []
        self.sources: dict[tuple[str, str], dict] = {}
        self.units: dict[tuple[str, str], dict] = {}
        self.unit_roles: dict[tuple[str, str], tuple[TrainingRole, str, dict]] = {}

    def verify_inputs(self) -> list[dict[str, Any]]:
        tasks = []
        for component in self.input_manifest["components"]:
            for artifact in component["artifacts"]:
                path = self.corpus_root / component["component"] / artifact["path"]
                tasks.append((component["component"], artifact, path))
        def verify(task: tuple[str, dict, Path]) -> dict[str, Any]:
            component, artifact, path = task; actual = digest(path.read_bytes())
            if actual != artifact["sha256"]: raise ValueError(f"input hash mismatch: {path}")
            return {"component": component, "path": artifact["path"], "sha256": actual}
        if self.workers == 1:
            verified = list(map(verify, tasks))
        else:
            with ThreadPoolExecutor(max_workers=min(8, self.workers)) as executor:
                verified = list(executor.map(verify, tasks))
        return verified

    def load_level_one(self) -> None:
        for component in sorted(item["component"] for item in self.input_manifest["components"]):
            path = self.corpus_root / component / "level-1-code-literacy.jsonl"
            artifact_hash = digest(path.read_bytes())
            for line_number, row in enumerate(read_jsonl(path), 1):
                provenance = {"artifact": f"{component}/{path.name}", "line": line_number, "artifact_sha256": artifact_hash, "original_role": row.get("role")}
                self.level_one.append((component, row, provenance))
                if row["schema"].endswith(":source_file"):
                    self.sources[(component, row["repository_relative_file"])] = row
                elif row["schema"].endswith(":code_unit"):
                    self.units[(component, row["record_id"])] = row

    def select_level_one(self, duplicate_map: dict[str, str]) -> None:
        for component, row, provenance in self.level_one:
            source = row if row["schema"].endswith(":source_file") else self.sources[(component, row["repository_relative_file"])]
            role, reason = file_role(source)
            original_role = str(source.get("role", "source"))
            if row["schema"].endswith(":code_unit") and role == TrainingRole.RUNTIME_CODE and row.get("classification", {}).get("test_evidence"):
                role, reason = TrainingRole.TEST_CODE, "code unit carries explicit test-evidence classification"
            parents = [] if row is source else [{"relationship": "defined_in", "record_hash": digest(source)}]
            selected = envelope(component=component, row=row, original_role=original_role, training_role=role, reason=reason, provenance=provenance, source=source, reservations=self.reservations, duplicate_group=duplicate_map.get(digest(row)), parent_relationships=parents)
            if row["schema"].endswith(":code_unit"):
                self.unit_roles[(component, row["record_id"])] = (role, reason, source)
            release = "RESEARCH_REFERENCE" if role == TrainingRole.RESEARCH_REFERENCE else ("DOCUMENTATION" if role == TrainingRole.DOCUMENTATION else "LEVEL_1_CODE_LITERACY")
            self.releases[release].append(selected)
            if role in {TrainingRole.TEST_CODE, TrainingRole.SCHEMA_CONTRACT, TrainingRole.CONFIGURATION}:
                self.releases["EXPECTED_BEHAVIOR"].append(selected)
            if role in {TrainingRole.RESEARCH_REFERENCE, TrainingRole.DOCUMENTATION}:
                self.exclusions.append({"record_hash": digest(row), "source_system": component, "excluded_from": ["LEVEL_1_CODE_LITERACY", "LEVEL_2_SYSTEM_RELATIONSHIPS", "LEVEL_3_OPERATOR_USAGE"], "exclusion_reason": f"primary role {role.value} is separately gated", "retained_in": release})

    def _relationship_envelope(self, component: str, row: dict, provenance: dict, caller: dict, relation_kind: str) -> dict:
        role, _reason, source = self.unit_roles[(component, caller["record_id"])]
        training_role = TrainingRole.RESEARCH_REFERENCE if role == TrainingRole.RESEARCH_REFERENCE else TrainingRole.SYSTEM_RELATIONSHIP
        return envelope(component=component, row=row, original_role=relation_kind, training_role=training_role, reason=f"source-observed {relation_kind} relationship", provenance=provenance, source=source, reservations=self.reservations, parent_relationships=[{"relationship": "caller", "record_hash": digest(caller)}, {"relationship": "source_file", "record_hash": digest(source)}])

    def select_relationships(self) -> None:
        global _SELECT_UNITS, _SELECT_UNIT_ROLES, _SELECT_SOURCES, _SELECT_RESERVATIONS
        _SELECT_UNITS = self.units; _SELECT_UNIT_ROLES = self.unit_roles; _SELECT_SOURCES = self.sources; _SELECT_RESERVATIONS = self.reservations
        for component in sorted(item["component"] for item in self.input_manifest["components"]):
            path = self.corpus_root / component / "level-2-operational-relationships.jsonl"; artifact_hash = digest(path.read_bytes())
            tasks: list[tuple[str, str, dict, dict, str, str]] = []
            for line_number, row in enumerate(read_jsonl(path), 1):
                tasks.append(("call", component, row, {"artifact": f"{component}/{path.name}", "line": line_number, "artifact_sha256": artifact_hash}, row["caller_record_id"], "call_edge"))
            for (owner, _record_id), unit in sorted(self.units.items()):
                if owner != component: continue
                for access in ("state_read", "state_written"):
                    for ordinal, target in enumerate(unit.get(access, [])):
                        row = {"schema": f"{SELECTION_SCHEMA}:state_edge", "caller_record_id": unit["record_id"], "relationship": access, "target": target, "ordinal": ordinal}
                        tasks.append(("state", component, row, {"derived_from_record_hash": digest(unit)}, unit["record_id"], access))
            for (owner, relative), source in sorted(self.sources.items()):
                if owner != component: continue
                for ordinal, imported in enumerate(source.get("imports", [])):
                    row = {"schema": f"{SELECTION_SCHEMA}:import_edge", "source_file_record_hash": digest(source), "relationship": "imports", "target": imported, "ordinal": ordinal}
                    tasks.append(("import", component, row, {"derived_from_record_hash": digest(source)}, relative, "import_edge"))
            if self.workers == 1:
                selected_rows = map(_relationship_worker, tasks)
            else:
                pool = multiprocessing.get_context("fork").Pool(processes=self.workers)
                selected_rows = pool.imap(_relationship_worker, tasks, chunksize=max(1, min(256, len(tasks) // max(1, self.workers * 12))))
            try:
                for task_kind, selected in selected_rows:
                    release = "RESEARCH_REFERENCE" if selected["training_role"] == TrainingRole.RESEARCH_REFERENCE else "LEVEL_2_SYSTEM_RELATIONSHIPS"
                    self.releases[release].append(selected)
                    if task_kind == "call" and release == "RESEARCH_REFERENCE":
                        self.exclusions.append({"record_hash": selected["record_hash"], "source_system": component, "excluded_from": ["LEVEL_2_SYSTEM_RELATIONSHIPS"], "exclusion_reason": "caller belongs to research/reference", "retained_in": release})
            finally:
                if self.workers != 1: pool.close(); pool.join()

    def select_trajectories(self) -> None:
        for component in sorted(item["component"] for item in self.input_manifest["components"]):
            path = self.corpus_root / component / "level-3-operator-trajectories.partial.jsonl"; artifact_hash = digest(path.read_bytes())
            for line_number, row in enumerate(read_jsonl(path), 1):
                provenance = {"artifact": f"{component}/{path.name}", "line": line_number, "artifact_sha256": artifact_hash}
                unit_id = row.get("component_result", {}).get("source_record_id")
                unit = self.units.get((component, unit_id))
                if unit is None:
                    training_role = TrainingRole.FAILURE_RESTRAINT
                    source = self.sources.get((component, row.get("path", "")))
                    reason = "intake failure record retained as failure/restraint evidence"
                    parents = []
                else:
                    source_role, _source_reason, source = self.unit_roles[(component, unit_id)]
                    failure_signal = bool(row.get("raises")) or any(str(call.get("name", "")).endswith("raises") for call in row.get("ordered_observed_calls", []))
                    if source_role == TrainingRole.RESEARCH_REFERENCE:
                        training_role, reason = TrainingRole.RESEARCH_REFERENCE, "trajectory source belongs to research/reference"
                    elif failure_signal:
                        training_role, reason = TrainingRole.FAILURE_RESTRAINT, "source trajectory contains explicit raise/failure evidence"
                    else:
                        training_role, reason = TrainingRole.OPERATOR_TRAJECTORY, "source-backed test or CLI partial trajectory"
                    parents = [{"relationship": "trajectory_source", "record_hash": digest(unit)}, {"relationship": "source_file", "record_hash": digest(source)}]
                selected = envelope(component=component, row=row, original_role=str(row.get("trajectory_source", "failure_record")), training_role=training_role, reason=reason, provenance=provenance, source=source, reservations=self.reservations, parent_relationships=parents)
                if training_role == TrainingRole.RESEARCH_REFERENCE:
                    self.releases["RESEARCH_REFERENCE"].append(selected)
                    self.exclusions.append({"record_hash": digest(row), "source_system": component, "excluded_from": ["LEVEL_3_OPERATOR_USAGE", "FAILURE_RESTRAINT"], "exclusion_reason": "trajectory belongs to research/reference", "retained_in": "RESEARCH_REFERENCE"})
                else:
                    self.releases["LEVEL_3_OPERATOR_USAGE"].append(selected)
                    if training_role == TrainingRole.FAILURE_RESTRAINT:
                        self.releases["FAILURE_RESTRAINT"].append(selected)

    def write_release(self, name: str) -> dict[str, Any]:
        rows = sorted(self.releases[name], key=lambda row: row["selection_record_hash"])
        directory = self.output_root / "releases" / name; directory.mkdir(parents=True, exist_ok=True)
        artifact = write_jsonl(directory / "records.jsonl", rows)
        role_counts: dict[str, int] = defaultdict(int); system_counts: dict[str, int] = defaultdict(int); eligibility_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            role_counts[row["training_role"]] += 1; system_counts[row["source_system"]] += 1; eligibility_counts[row["eligibility"]] += 1
        identity = {"schema": f"{SELECTION_SCHEMA}:release_identity", "name": name, "input_commit": self.input_manifest.get("repository_commit"), "record_hashes": [row["selection_record_hash"] for row in rows]}
        manifest = {"schema": f"{SELECTION_SCHEMA}:release_manifest", "release_name": name, "release_id": digest(identity), "record_count": len(rows), "role_counts": dict(sorted(role_counts.items())), "system_counts": dict(sorted(system_counts.items())), "eligibility_counts": dict(sorted(eligibility_counts.items())), "artifact": artifact}
        write_json(directory / "manifest.json", manifest)
        return manifest

    def run(self) -> dict[str, Any]:
        self.output_root.mkdir(parents=True)
        wall_start = time.perf_counter(); self_start = resource.getrusage(resource.RUSAGE_SELF); child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
        verified_inputs = self.verify_inputs(); self.load_level_one()
        groups, duplicate_map = duplicate_groups(self.level_one)
        self.select_level_one(duplicate_map); self.select_relationships(); self.select_trajectories()
        duplicate_artifact = write_jsonl(self.output_root / "duplicates" / "duplicate-groups.jsonl", groups)
        exclusions_artifact = write_jsonl(self.output_root / "audit" / "excluded-records.jsonl", sorted(self.exclusions, key=canonical))
        reservation_hook = {"schema": f"{SELECTION_SCHEMA}:reservation_hook", "allowed_values": [value.value for value in Eligibility], "default_test_policy": "UNASSIGNED_SPLIT_REQUIRED", "law": "EVALUATION_RESERVED and NEVER_TRAIN records cannot be admitted to later training.", "records": self.reservations}
        reservation_artifact = write_json(self.output_root / "eligibility" / "reservation-manifest.json", reservation_hook)
        releases = [self.write_release(name) for name in RELEASE_NAMES]
        release_by_name = {row["release_name"]: row for row in releases}
        curriculum = {
            "schema": f"{SELECTION_SCHEMA}:curriculum", "hyperparameters": None,
            "phases": [
                {"phase": 1, "purpose": "Local vocabulary / exact code literacy", "release_ids": [release_by_name["LEVEL_1_CODE_LITERACY"]["release_id"]]},
                {"phase": 2, "purpose": "System structure / call and state relationships", "release_ids": [release_by_name["LEVEL_2_SYSTEM_RELATIONSHIPS"]["release_id"]]},
                {"phase": 3, "purpose": "Tests, contracts, configuration, expected behavior", "release_ids": [release_by_name["EXPECTED_BEHAVIOR"]["release_id"]]},
                {"phase": 4, "purpose": "Operator trajectories", "release_ids": [release_by_name["LEVEL_3_OPERATOR_USAGE"]["release_id"]]},
                {"phase": 5, "purpose": "Failure, restraint, rollback, verification", "release_ids": [release_by_name["FAILURE_RESTRAINT"]["release_id"]]},
            ],
            "research_reference_gate": {"automatic": False, "release_id": release_by_name["RESEARCH_REFERENCE"]["release_id"]},
        }
        curriculum_artifact = write_json(self.output_root / "curriculum.json", curriculum)
        manifest = {"schema": SELECTION_SCHEMA, "classification": "ROLE_SELECTED_NOT_ADMITTED_NOT_TRAINED", "source_corpus": str(self.corpus_root), "source_manifest_sha256": digest((self.corpus_root / "manifest.json").read_bytes()), "verified_input_artifacts": verified_inputs, "source_text_normalization": "none", "agent_authority_created": False, "model_authority_created": False, "runtime_authority_created": False, "release_manifests": releases, "duplicate_statistics": {"groups": len(groups), "members": sum(len(group["members"]) for group in groups)}, "excluded_records": len(self.exclusions), "artifacts": {"duplicates": duplicate_artifact, "exclusions": exclusions_artifact, "reservation": reservation_artifact, "curriculum": curriculum_artifact}}
        write_json(self.output_root / "release-set-manifest.json", manifest)
        wall = time.perf_counter() - wall_start; self_end = resource.getrusage(resource.RUSAGE_SELF); child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (self_end.ru_utime + self_end.ru_stime - self_start.ru_utime - self_start.ru_stime) + (child_end.ru_utime + child_end.ru_stime - child_start.ru_utime - child_start.ru_stime)
        total_records = sum(release["record_count"] for release in releases)
        performance = {"schema": f"{SELECTION_SCHEMA}:performance_receipt", "workers": self.workers, "logical_cpus": os.cpu_count(), "elapsed_wall_seconds": wall, "aggregate_cpu_seconds": cpu, "effective_cpu_cores": cpu / wall if wall else 0.0, "machine_cpu_utilization_percent": cpu / wall / (os.cpu_count() or 1) * 100.0 if wall else 0.0, "records_per_second": total_records / wall if wall else 0.0, "maximum_resident_kib": max(self_end.ru_maxrss, child_end.ru_maxrss)}
        write_json(self.output_root / "performance-receipt.json", performance)
        return manifest


def build_releases(corpus_root: Path, output_root: Path, reservation_manifest: Path | None = None, workers: int = 24) -> dict[str, Any]:
    return SelectionBuilder(corpus_root, output_root, reservation_manifest, workers=workers).run()
