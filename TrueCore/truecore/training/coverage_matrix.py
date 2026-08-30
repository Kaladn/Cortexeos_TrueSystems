"""Deterministic training-coverage inventory and gap manifest.

This module counts frozen evidence without claiming that untagged source records
teach a requested concept.  It performs no intake, selection, or training.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "truesystems_training_coverage@1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: bytes | dict | list) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def _read_verified(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.resolve().read_bytes()
    return json.loads(raw), {"path": str(path.resolve()), "bytes": len(raw), "sha256": digest(raw)}


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    raw = canonical(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": path.name, "bytes": len(raw), "sha256": digest(raw), "records": 1}


def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> dict[str, Any]:
    raw = b"".join(canonical(value) + b"\n" for value in values)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": path.name, "bytes": len(raw), "sha256": digest(raw), "records": len(values)}


AREAS = {
    "LOCAL_TRUESYSTEMS_TRUTH": {
        "authority": "LOCAL_SOURCE_BACKED",
        "topics": ["component_identity", "code_and_contracts", "system_relationships", "operator_trajectories", "receipts_and_failures"],
    },
    "SYMBOLIC_FOUNDATIONS_EXTERNAL": {
        "authority": "EXTERNAL_NOT_LOCAL_TRUTH",
        "topics": ["sets_relations_graphs", "logic", "formal_languages", "state_and_temporal_systems", "deterministic_search_and_backtracking", "identity_provenance_hashing", "signed_616_relationship_geometry"],
    },
    "LINUX_SYSTEMS_EXTERNAL": {
        "authority": "EXTERNAL_NOT_LOCAL_TRUTH",
        "topics": ["processes_memory_filesystems", "permissions_services_devices", "journald_procfs_sysfs", "ipc_networking", "clocks_timestamps_ordering", "wal_binary_storage_recovery", "deterministic_concurrency"],
    },
    "SECURITY_DEFENSIVE_EXTERNAL": {
        "authority": "EXTERNAL_NOT_LOCAL_TRUTH",
        "topics": ["threat_modeling", "authentication_authorization_integrity", "telemetry_and_forensics", "incident_response", "vulnerability_classes", "evidence_vs_inference", "containment_and_tool_boundaries"],
    },
    "LANGUAGE_STEERING_EXTERNAL": {
        "authority": "EXTERNAL_NOT_LOCAL_TRUTH",
        "topics": ["commands_and_questions", "negation_and_correction", "conditions_and_constraints", "reference_resolution", "inspect_vs_modify", "stop_continue_compare_broaden", "multiturn_continuity"],
    },
    "STRUCTURED_DATA_LITERACY": {
        "authority": "MIXED_ROLE_SEPARATED",
        "topics": ["json_jsonl_and_schemas", "logs_tables_graphs", "binary_records", "timestamps_paths_coordinates", "citations_and_source_reconstruction", "parent_and_containment_relations"],
    },
    "FAILURE_RESTRAINT": {
        "authority": "LOCAL_OR_EXPLICIT_EXTERNAL_EVIDENCE",
        "topics": ["wrong_system", "wrong_symbol", "ambiguous_target", "stale_or_missing_hash", "invalid_coordinate", "unsupported_meaning", "authority_denial", "verification_failure"],
    },
    "EVALUATION_RESERVED": {
        "authority": "NEVER_TRAIN",
        "topics": ["source_group_holdout", "paraphrase_family_holdout", "target_holdout", "system_holdout", "refusal_evaluation", "unseen_paraphrase"],
    },
}


def build_coverage_matrix(release_manifest: Path, syl_manifest: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    releases, release_source = _read_verified(release_manifest)
    syl, syl_source = _read_verified(syl_manifest)
    if releases.get("schema") != "truesystems_training_selection@1":
        raise ValueError("unsupported operational release manifest")
    if syl.get("schema") != "truesystems_syl_evidence@1":
        raise ValueError("unsupported SYL evidence manifest")

    release_rows = sorted(releases["release_manifests"], key=lambda row: row["release_name"])
    release_inventory = [{key: row[key] for key in ("release_name", "release_id", "record_count", "role_counts", "system_counts", "eligibility_counts")} for row in release_rows]
    system_totals: dict[str, int] = {}
    role_totals: dict[str, int] = {}
    for row in release_rows:
        if row["release_name"] == "RESEARCH_REFERENCE":
            continue
        for system, count in row["system_counts"].items():
            system_totals[system] = system_totals.get(system, 0) + count
        for role, count in row["role_counts"].items():
            role_totals[role] = role_totals.get(role, 0) + count

    matrix = []
    for area, definition in sorted(AREAS.items()):
        for topic in definition["topics"]:
            matrix.append({
                "schema": f"{SCHEMA}:coverage_requirement",
                "area": area,
                "topic": topic,
                "authority": definition["authority"],
                "tagged_training_examples": 0,
                "tagged_evaluation_examples": 0,
                "status": "UNTAGGED_NOT_MEASURED",
                "reason": "Existing records have not been explicitly assigned to this concept; raw record presence is not concept coverage.",
            })

    inventory = {
        "schema": f"{SCHEMA}:observed_inventory",
        "operational_releases": release_inventory,
        "non_research_system_record_memberships": dict(sorted(system_totals.items())),
        "non_research_role_record_memberships": dict(sorted(role_totals.items())),
        "research_reference_records": next(row["record_count"] for row in release_rows if row["release_name"] == "RESEARCH_REFERENCE"),
        "syl": {
            "source_objects": syl["source_objects"],
            "candidate_channel_records": syl["candidate_channel_records"],
            "fragments": syl["fragments"],
            "grouped_patterns": syl["grouped_patterns"],
            "channels": syl["channels"],
        },
        "interpretation_law": "Inventory counts prove available evidence records only; they do not prove concept coverage or model competence.",
    }
    output.mkdir(parents=True)
    artifacts = {
        "requirements": _write_jsonl(output / "coverage-requirements.jsonl", matrix),
        "inventory": _write_json(output / "observed-inventory.json", inventory),
    }
    manifest = {
        "schema": SCHEMA,
        "classification": "COVERAGE_AUDIT_NOT_DATASET_NOT_TRAINED",
        "sources": {"operational_release": release_source, "syl_release": syl_source},
        "areas": len(AREAS),
        "requirements": len(matrix),
        "measured_requirements": 0,
        "untagged_requirements": len(matrix),
        "research_reference_automatically_eligible": False,
        "source_text_normalization": "none",
        "model_training_performed": False,
        "optimizer_updates": 0,
        "authority_created": False,
        "artifacts": artifacts,
    }
    manifest["coverage_release_id"] = digest(manifest)
    _write_json(output / "manifest.json", manifest)
    return manifest
