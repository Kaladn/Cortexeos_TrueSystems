"""Read-only deterministic resolver over a frozen language-to-local release."""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
import os
from pathlib import Path
import re
import resource
import time
from typing import Any, Iterable

from .external_source_intake import BRIDGE_RELEASE, SCHEMA as INTAKE_SCHEMA, canonical, digest


SCHEMA = "truesystems_language_local_bridge_resolver@1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ANCHOR_RE = re.compile(r"[^\W_]+(?:[_'’\-‐‑‒–—―][^\W_]+)*", re.UNICODE)
NEGATION_ANCHORS = frozenset({
    "not", "Not", "NOT", "never", "Never", "without", "Without",
    "exclude", "Exclude", "don't", "Don't", "doesn't", "Doesn't",
    "isn't", "Isn't", "cannot", "Cannot",
})


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


def word_anchors(text: str) -> tuple[str, ...]:
    """Return exact full-word anchors; never case-fold or rewrite source text."""
    return tuple(match.group(0) for match in ANCHOR_RE.finditer(text))


def _verify_record(row: dict[str, Any]) -> None:
    if row.get("schema") != f"{INTAKE_SCHEMA}:language_to_local_bridge":
        raise ValueError("resolver authority contains a non-bridge record")
    if row.get("namespace") != BRIDGE_RELEASE or row.get("local_authority") is not False:
        raise ValueError("resolver authority violates bridge namespace or authority boundary")
    record_id = row.get("record_id")
    if not isinstance(record_id, str) or digest({key: value for key, value in row.items() if key != "record_id"}) != record_id:
        raise ValueError("bridge record identity mismatch")
    target = row.get("local_target")
    if not isinstance(target, dict) or not SHA256_RE.fullmatch(str(target.get("record_hash", ""))) or not SHA256_RE.fullmatch(str(target.get("selection_record_hash", ""))):
        raise ValueError("bridge target hashes are invalid")
    path = row.get("local_relationship_path")
    if not isinstance(path, list) or not path:
        raise ValueError("bridge record lacks a frozen relationship path")
    current = target["record_hash"]
    for step in path:
        if step.get("from_record_hash") != current or not SHA256_RE.fullmatch(str(step.get("to_record_hash", ""))):
            raise ValueError("bridge relationship path is discontinuous")
        current = step["to_record_hash"]


class FrozenBridgeAuthority:
    """Verified in-memory view of one committed bridge release."""

    def __init__(self, release_root: Path):
        self.release_root = release_root.resolve()
        manifest_path = self.release_root / "manifest.json"
        records_path = self.release_root / "records.jsonl"
        self.manifest_bytes = manifest_path.read_bytes()
        self.manifest = json.loads(self.manifest_bytes)
        if self.manifest.get("release_name") != BRIDGE_RELEASE:
            raise ValueError("resolver accepts only LANGUAGE_TO_LOCAL_BRIDGES")
        records_bytes = records_path.read_bytes()
        artifact = self.manifest.get("artifact", {})
        if digest(records_bytes) != artifact.get("sha256") or len(records_bytes) != artifact.get("bytes"):
            raise ValueError("bridge release artifact hash or byte count mismatch")
        self.records = [json.loads(line) for line in records_bytes.splitlines() if line]
        if len(self.records) != self.manifest.get("record_count") or len(self.records) != artifact.get("records"):
            raise ValueError("bridge release record count mismatch")
        for row in self.records:
            _verify_record(row)
        identity = {
            "schema": f"{INTAKE_SCHEMA}:release_identity", "name": BRIDGE_RELEASE,
            "record_ids": [row["record_id"] for row in self.records],
        }
        if digest(identity) != self.manifest.get("release_id"):
            raise ValueError("bridge release identity mismatch")
        self.release_id = self.manifest["release_id"]
        self.records_by_target = {row["local_target"]["record_hash"]: row for row in self.records}
        if len(self.records_by_target) != len(self.records):
            raise ValueError("bridge release contains multiple bindings for one target hash")
        phrase_occurrence = Counter()
        self.catalog = []
        for row in self.records:
            phrase = row["phrase_unit"]["full_text"]
            anchors = word_anchors(phrase)
            phrase_occurrence.update(set(anchors))
            location = row["local_target"].get("file_coordinates") or {}
            location_anchors = word_anchors(str(location.get("path", "")))
            relation_anchors = (row["relation"], *(step["relationship"] for step in row["local_relationship_path"]))
            self.catalog.append({
                "record": row, "phrase": phrase, "phrase_anchors": anchors,
                "location_anchors": location_anchors, "relation_anchors": tuple(relation_anchors),
            })
        self.phrase_occurrence = dict(phrase_occurrence)

    def frozen_payload(self) -> dict[str, Any]:
        return {
            "release_id": self.release_id,
            "manifest_sha256": digest(self.manifest_bytes),
            "catalog": self.catalog,
            "phrase_occurrence": self.phrase_occurrence,
        }


def _result(status: str, query: str, reason: str, *, case_id: str | None = None, **values: Any) -> dict[str, Any]:
    result = {
        "schema": f"{SCHEMA}:resolution", "case_id": case_id,
        "query": query, "status": status, "reason": reason,
        "operation_executed": False, "local_record_modified": False,
        "model_training_performed": False, "generic_record_used_as_local_truth": False,
    }
    result.update(values)
    return result


def resolve_query(query_request: dict[str, Any], frozen: dict[str, Any]) -> dict[str, Any]:
    query = query_request.get("query")
    case_id = query_request.get("case_id")
    if not isinstance(query, str) or not query:
        return _result("unsupported", str(query or ""), "empty_or_non_string_query", case_id=case_id)
    expected_release = query_request.get("expected_release_id")
    if expected_release is not None and expected_release != frozen["release_id"]:
        return _result("stale", query, "expected_release_id_is_not_current_authority", case_id=case_id, expected_release_id=expected_release, authority_release_id=frozen["release_id"])
    target_hint = query_request.get("target_hash_hint")
    if target_hint is not None and (not isinstance(target_hint, str) or not SHA256_RE.fullmatch(target_hint) or all(item["record"]["local_target"]["record_hash"] != target_hint for item in frozen["catalog"])):
        return _result("missing", query, "target_hash_not_in_bridge_authority", case_id=case_id, target_hash_hint=target_hint, authority_release_id=frozen["release_id"])
    query_anchors = word_anchors(query)
    if any(anchor in NEGATION_ANCHORS for anchor in query_anchors):
        return _result("unsupported", query, "negated_request_is_not_a_positive_location_binding", case_id=case_id, evidence={"exact_query_anchors": list(query_anchors)})
    known_systems = {item["record"]["local_target"]["source_system"] for item in frozen["catalog"]}
    systems = sorted(system for system in known_systems if system in query_anchors or f"{system}'s" in query_anchors or f"{system}’s" in query_anchors)
    owner_systems = sorted(system for system in known_systems if f"{system}'s" in query_anchors or f"{system}’s" in query_anchors)
    candidates = [item for item in frozen["catalog"] if target_hint is None or item["record"]["local_target"]["record_hash"] == target_hint]
    if owner_systems:
        candidates = [item for item in candidates if item["record"]["local_target"]["source_system"] in owner_systems]
    query_set = set(query_anchors)
    evaluated = []
    for item in candidates:
        phrase_set = set(item["phrase_anchors"])
        phrase_matches = sorted(query_set & phrase_set)
        unique_matches = sorted(anchor for anchor in phrase_matches if frozen["phrase_occurrence"].get(anchor) == 1)
        uncommon_matches = sorted(anchor for anchor in phrase_matches if frozen["phrase_occurrence"].get(anchor, 0) <= 3)
        location_matches = sorted(query_set & set(item["location_anchors"]))
        relation_matches = sorted(query_set & set(item["relation_anchors"]))
        exact = query == item["phrase"]
        system_match = item["record"]["local_target"]["source_system"] in owner_systems
        vector = [int(exact), int(system_match), len(unique_matches), len(uncommon_matches), len(location_matches), len(relation_matches), len(phrase_matches)]
        qualifies = bool(
            exact or target_hint or len(unique_matches) >= 2
            or (unique_matches and len(uncommon_matches) >= 3)
            or len(location_matches) >= 2
        )
        evaluated.append({"item": item, "vector": vector, "qualifies": qualifies, "phrase_matches": phrase_matches, "unique_matches": unique_matches, "location_matches": location_matches, "relation_matches": relation_matches})
    qualified = [item for item in evaluated if item["qualifies"]]
    if qualified:
        best_vector = max(item["vector"] for item in qualified)
        best = [item for item in qualified if item["vector"] == best_vector]
        if len(best) == 1:
            chosen = best[0]
            bridge = chosen["item"]["record"]
            return _result(
                "resolved", query, "unique_frozen_bridge_evidence", case_id=case_id,
                authority_release_id=frozen["release_id"], authority_manifest_sha256=frozen["manifest_sha256"],
                target_hash=bridge["local_target"]["record_hash"],
                selection_record_hash=bridge["local_target"]["selection_record_hash"],
                relationship_path=bridge["local_relationship_path"],
                citation={
                    "source_system": bridge["local_target"]["source_system"],
                    "repository_identity": bridge["local_target"]["repository_identity"],
                    "source_identity": bridge["local_target"]["source_identity"],
                    "file_coordinates": bridge["local_target"]["file_coordinates"],
                    "relation_line": bridge["local_target"].get("relation_line"),
                },
                evidence={
                    "bridge_record_id": bridge["record_id"], "bridge_phrase": chosen["item"]["phrase"],
                    "exact_query_anchors": list(query_anchors), "matched_phrase_anchors": chosen["phrase_matches"],
                    "unique_phrase_anchors": chosen["unique_matches"], "matched_location_anchors": chosen["location_matches"],
                    "matched_relation_anchors": chosen["relation_matches"], "selection_vector": chosen["vector"],
                },
            )
        return _result("ambiguous", query, "multiple_frozen_bridges_share_best_evidence", case_id=case_id, authority_release_id=frozen["release_id"], candidate_target_hashes=sorted(item["item"]["record"]["local_target"]["record_hash"] for item in best))
    same_system = [item for item in candidates if systems and item["record"]["local_target"]["source_system"] in systems]
    if len(same_system) > 1:
        return _result("ambiguous", query, "system_reference_has_multiple_frozen_bridge_targets", case_id=case_id, authority_release_id=frozen["release_id"], candidate_target_hashes=sorted(item["record"]["local_target"]["record_hash"] for item in same_system))
    return _result("unsupported", query, "insufficient_unique_frozen_bridge_evidence", case_id=case_id, authority_release_id=frozen["release_id"], evidence={"exact_query_anchors": list(query_anchors)})


def _resolve_task(task: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    return resolve_query(*task)


class BridgeResolverEvaluation:
    def __init__(self, release_root: Path, cases_path: Path, output_root: Path, workers: int = 24):
        if workers < 1:
            raise ValueError("workers must be at least 1")
        self.authority = FrozenBridgeAuthority(release_root)
        self.cases_path = cases_path.resolve()
        self.output_root = output_root.resolve()
        if self.output_root.exists():
            raise FileExistsError(f"output root already exists: {self.output_root}")
        self.workers = workers
        self.case_bytes = self.cases_path.read_bytes()
        self.cases = [json.loads(line) for line in self.case_bytes.splitlines() if line]
        ids = [case.get("case_id") for case in self.cases]
        if len(ids) != len(set(ids)) or not all(isinstance(value, str) and value for value in ids):
            raise ValueError("evaluation cases require unique non-empty case_id values")

    def run(self) -> dict[str, Any]:
        self.output_root.mkdir(parents=True)
        wall_start = time.perf_counter()
        self_start = resource.getrusage(resource.RUSAGE_SELF)
        child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
        frozen = self.authority.frozen_payload()
        tasks = [(case, frozen) for case in self.cases]
        if self.workers == 1:
            results = list(map(_resolve_task, tasks))
        else:
            context = multiprocessing.get_context("fork")
            with ProcessPoolExecutor(max_workers=self.workers, mp_context=context) as executor:
                results = list(executor.map(_resolve_task, tasks, chunksize=max(1, len(tasks) // (self.workers * 4))))
        results.sort(key=lambda row: row["case_id"])
        cases_by_id = {case["case_id"]: case for case in self.cases}
        outcomes = []
        category_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        passed = 0
        target_hash_cases = 0
        target_hash_correct = 0
        relationship_path_cases = 0
        relationship_path_correct = 0
        status_counts: dict[str, int] = defaultdict(int)
        for result in results:
            case = cases_by_id[result["case_id"]]
            status_correct = result["status"] == case["expected_status"]
            target_correct = case.get("expected_target_hash") is None or result.get("target_hash") == case["expected_target_hash"]
            path_correct = case.get("expected_relationship_path") is None or result.get("relationship_path") == case["expected_relationship_path"]
            if case.get("expected_target_hash") is not None:
                target_hash_cases += 1
                target_hash_correct += int(target_correct)
            if case.get("expected_relationship_path") is not None:
                relationship_path_cases += 1
                relationship_path_correct += int(path_correct)
            status_counts[result["status"]] += 1
            success = status_correct and target_correct and path_correct
            passed += int(success)
            category_counts[case["category"]]["cases"] += 1
            category_counts[case["category"]]["passed"] += int(success)
            outcomes.append({
                "case_id": result["case_id"], "category": case["category"],
                "expected_status": case["expected_status"], "status_correct": status_correct,
                "target_hash_correct": target_correct, "relationship_path_correct": path_correct,
                "passed": success, "resolution": result,
            })
        outcomes.sort(key=lambda row: row["case_id"])
        results_artifact = _write_jsonl(self.output_root / "results.jsonl", outcomes)
        report = {
            "schema": f"{SCHEMA}:evaluation_report", "authority_release_id": self.authority.release_id,
            "authority_manifest_sha256": digest(self.authority.manifest_bytes),
            "cases_sha256": digest(self.case_bytes), "cases": len(outcomes), "passed": passed,
            "failed": len(outcomes) - passed,
            "category_counts": {key: dict(sorted(value.items())) for key, value in sorted(category_counts.items())},
            "resolution_status_counts": dict(sorted(status_counts.items())),
            "exact_target_hash_measurement": {"cases": target_hash_cases, "correct": target_hash_correct},
            "exact_relationship_path_measurement": {"cases": relationship_path_cases, "correct": relationship_path_correct},
            "operation_executed": False, "local_record_modified": False,
            "generic_hf_local_authority": False, "model_training_performed": False,
        }
        report_artifact = _write_json(self.output_root / "evaluation-report.json", report)
        manifest = {
            "schema": SCHEMA, "classification": "READ_ONLY_FROZEN_BRIDGE_EVALUATION_NOT_TRAINED",
            "authority": {"release_id": self.authority.release_id, "manifest_sha256": digest(self.authority.manifest_bytes)},
            "cases_sha256": digest(self.case_bytes), "workers_semantically_irrelevant": True,
            "operation_executed": False, "local_record_modified": False,
            "new_bridge_inferred": False, "generic_hf_local_authority": False, "model_training_performed": False,
            "artifacts": {"results": results_artifact, "report": report_artifact},
        }
        _write_json(self.output_root / "manifest.json", manifest)
        wall = time.perf_counter() - wall_start
        self_end = resource.getrusage(resource.RUSAGE_SELF)
        child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (self_end.ru_utime + self_end.ru_stime - self_start.ru_utime - self_start.ru_stime) + (child_end.ru_utime + child_end.ru_stime - child_start.ru_utime - child_start.ru_stime)
        _write_json(self.output_root / "performance-receipt.json", {
            "schema": f"{SCHEMA}:performance_receipt", "workers": self.workers,
            "logical_cpus": os.cpu_count(), "elapsed_wall_seconds": wall,
            "aggregate_cpu_seconds": cpu, "cases_per_second": len(self.cases) / wall if wall else 0.0,
            "maximum_resident_kib": max(self_end.ru_maxrss, child_end.ru_maxrss),
        })
        return manifest


def evaluate_bridge_resolver(release_root: Path, cases_path: Path, output_root: Path, workers: int = 24) -> dict[str, Any]:
    return BridgeResolverEvaluation(release_root, cases_path, output_root, workers).run()
