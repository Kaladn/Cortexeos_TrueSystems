"""Contracts for Central Reader and Central Writer separation."""

from __future__ import annotations

import hashlib
import ipaddress
import json
from typing import Any

from truecore.time import is_canonical_utc_timestamp, utc_now


SEVERITIES = {"info", "low", "medium", "high", "critical"}
WRITER_STATUSES = {"accepted", "rejected", "rendered", "failed"}
MODEL_WRITER_CONDITIONS = {
    "operator_requested_report",
    "anomaly_summary_requested",
    "incident_status_requested",
    "chain_recipe_report_step",
}
REPORT_LANGUAGE_TASKS = {
    "format_facts",
    "summarize_facts",
    "normalize_language",
}


class CentralContractError(ValueError):
    """Raised when central reader/writer contract boundaries are violated."""


def build_reader_bundle(
    *,
    request_id: str,
    requested_by: str,
    sources: list[str],
    facts: list[dict[str, Any]],
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "central_reader_bundle",
        "request_id": request_id,
        "created_at_utc": utc_now(),
        "requested_by": requested_by,
        "authority": "read_only",
        "sources": sources,
        "facts": facts,
        "evidence_refs": evidence_refs,
    }


def validate_reader_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    _require(bundle, "schema_version", 1)
    _require(bundle, "kind", "central_reader_bundle")
    _require(bundle, "authority", "read_only")
    for field in ("request_id", "created_at_utc", "requested_by"):
        _require_nonempty_string(bundle, field)
    _require_string_list(bundle, "sources")
    _require_list(bundle, "facts")
    _require_string_list(bundle, "evidence_refs")
    for forbidden in ("message_text", "recommended_actions", "approval_required", "enforcement_authorized"):
        if forbidden in bundle:
            raise CentralContractError(f"reader bundle cannot contain {forbidden}")
    return dict(bundle)


def build_writer_request(
    *,
    request_id: str,
    requested_by_agent: str,
    summary: str,
    severity: str,
    facts: list[str],
    inferences: list[str],
    evidence_refs: list[str],
    recommended_actions: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "central_writer_request",
        "request_id": request_id,
        "created_at_utc": utc_now(),
        "requested_by_agent": requested_by_agent,
        "summary": summary,
        "severity": severity,
        "facts": facts,
        "inferences": inferences,
        "evidence_refs": evidence_refs,
        "recommended_actions": recommended_actions,
        "report_format": "truecore_facts_report_v1",
        "approval_required": True,
        "enforcement_authorized": False,
        "destination": "operator",
    }


def validate_writer_request(request: dict[str, Any]) -> dict[str, Any]:
    _require(request, "schema_version", 1)
    _require(request, "kind", "central_writer_request")
    for field in ("request_id", "created_at_utc", "requested_by_agent", "summary", "destination"):
        _require_nonempty_string(request, field)
    if request.get("severity") not in SEVERITIES:
        raise CentralContractError(f"invalid severity: {request.get('severity')}")
    _require_string_list(request, "facts")
    _require_string_list(request, "inferences", allow_empty=True)
    _require_string_list(request, "evidence_refs")
    _require_string_list(request, "recommended_actions", allow_empty=True)
    if request["inferences"] or request["recommended_actions"]:
        raise CentralContractError("writer requests are facts-only report requests")
    _require(request, "report_format", "truecore_facts_report_v1")
    if request.get("approval_required") is not True:
        raise CentralContractError("writer requests must require approval for action handling")
    if request.get("enforcement_authorized") is not False:
        raise CentralContractError("writer request cannot authorize enforcement")
    return dict(request)


def build_model_writer_report_request(
    *,
    request_id: str,
    requested_by_model: str,
    condition: str,
    summary: str,
    severity: str,
    facts: list[str],
    evidence_refs: list[str],
    reader_bundle_refs: list[str],
    language_task: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "central_model_writer_report_request",
        "request_id": request_id,
        "created_at_utc": utc_now(),
        "requested_by_model": requested_by_model,
        "condition": condition,
        "writer_task": "facts_only_report",
        "report_format": "truecore_facts_report_v1",
        "summary": summary,
        "severity": severity,
        "facts": facts,
        "evidence_refs": evidence_refs,
        "reader_bundle_refs": reader_bundle_refs,
        "language_task": language_task,
        "fact_authority": False,
        "approval_required": False,
        "enforcement_authorized": False,
        "destination": "central_writer",
    }


def validate_model_writer_report_request(request: dict[str, Any]) -> dict[str, Any]:
    _require(request, "schema_version", 1)
    _require(request, "kind", "central_model_writer_report_request")
    _require(request, "writer_task", "facts_only_report")
    _require(request, "report_format", "truecore_facts_report_v1")
    for field in ("request_id", "created_at_utc", "requested_by_model", "summary", "destination"):
        _require_nonempty_string(request, field)
    if request.get("condition") not in MODEL_WRITER_CONDITIONS:
        raise CentralContractError(f"invalid model writer condition: {request.get('condition')}")
    if request.get("severity") not in SEVERITIES:
        raise CentralContractError(f"invalid severity: {request.get('severity')}")
    if request.get("language_task") not in REPORT_LANGUAGE_TASKS:
        raise CentralContractError(f"invalid language_task: {request.get('language_task')}")
    _require_string_list(request, "facts")
    _require_string_list(request, "evidence_refs")
    _require_string_list(request, "reader_bundle_refs")
    if not request["facts"]:
        raise CentralContractError("facts must not be empty")
    if not request["evidence_refs"]:
        raise CentralContractError("evidence_refs must not be empty")
    if not request["reader_bundle_refs"]:
        raise CentralContractError("reader_bundle_refs must not be empty")
    for forbidden in ("inferences", "recommended_actions", "adapter_action", "runner_command"):
        if forbidden in request:
            raise CentralContractError(f"model writer request cannot contain {forbidden}")
    if request.get("fact_authority") is not False:
        raise CentralContractError("model writer request is not fact authority")
    if request.get("approval_required") is not False:
        raise CentralContractError("model writer report request cannot request action approval")
    if request.get("enforcement_authorized") is not False:
        raise CentralContractError("model writer request cannot authorize enforcement")
    return dict(request)


def build_facts_report(
    *,
    report_id: str,
    title: str,
    severity: str,
    scope: str,
    facts: list[str],
    evidence_refs: list[str],
    source_refs: list[str],
    language_notes: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "truecore_facts_report",
        "format": "truecore_facts_report_v1",
        "report_id": report_id,
        "created_at_utc": utc_now(),
        "title": title,
        "severity": severity,
        "scope": scope,
        "facts": facts,
        "evidence_refs": evidence_refs,
        "source_refs": source_refs,
        "language_notes": language_notes,
        "fact_authority": False,
        "enforcement_authorized": False,
    }


def validate_facts_report(report: dict[str, Any]) -> dict[str, Any]:
    _require(report, "schema_version", 1)
    _require(report, "kind", "truecore_facts_report")
    _require(report, "format", "truecore_facts_report_v1")
    for field in ("report_id", "created_at_utc", "title", "scope"):
        _require_nonempty_string(report, field)
    if report.get("severity") not in SEVERITIES:
        raise CentralContractError(f"invalid severity: {report.get('severity')}")
    _require_string_list(report, "facts")
    _require_string_list(report, "evidence_refs")
    _require_string_list(report, "source_refs")
    _require_string_list(report, "language_notes", allow_empty=True)
    if not report["facts"]:
        raise CentralContractError("facts must not be empty")
    if not report["evidence_refs"]:
        raise CentralContractError("evidence_refs must not be empty")
    for forbidden in ("inferences", "recommended_actions", "actions", "conclusion", "verdict"):
        if forbidden in report:
            raise CentralContractError(f"facts report cannot contain inference/action field: {forbidden}")
    if report.get("fact_authority") is not False:
        raise CentralContractError("facts report does not create fact authority")
    if report.get("enforcement_authorized") is not False:
        raise CentralContractError("facts report cannot authorize enforcement")
    return dict(report)


def build_legal_ip_trace_report(
    *,
    report_id: str,
    title: str,
    severity: str,
    remote_ip: str,
    observed_endpoint: str,
    facts: list[str],
    evidence_refs: list[str],
    source_refs: list[str],
    evidence_hashes: dict[str, str],
    chain_of_custody: list[dict[str, Any]],
    containment_plan: dict[str, Any],
    release_receipt_ref: str,
    unknowns: list[str],
) -> dict[str, Any]:
    report = {
        "schema_version": 1,
        "kind": "truecore_legal_ip_trace_report",
        "format": "truecore_legal_ip_trace_report_v1",
        "report_id": report_id,
        "created_at_utc": utc_now(),
        "title": title,
        "severity": severity,
        "remote_ip": remote_ip,
        "observed_endpoint": observed_endpoint,
        "scope": "bounded network trace",
        "facts": facts,
        "evidence_refs": evidence_refs,
        "source_refs": source_refs,
        "evidence_hashes": evidence_hashes,
        "chain_of_custody": chain_of_custody,
        "containment": {
            "mode": "trap_log_release",
            "plan_hash": containment_plan.get("plan_hash", ""),
            "ttl_seconds": containment_plan.get("ttl_seconds"),
            "trap_required": containment_plan.get("trap_required"),
            "log_required": containment_plan.get("log_required"),
            "release_required": containment_plan.get("release_required"),
            "rollback_required": containment_plan.get("rollback_required"),
        },
        "release_receipt_ref": release_receipt_ref,
        "unknowns": unknowns,
        "legal_notes": [
            "This report is an evidence-indexed technical record, not legal advice.",
            "Facts are limited to referenced observations and attached hashes.",
            "Containment actions require separate policy approval and receipts.",
        ],
        "fact_authority": False,
        "model_authority": False,
        "enforcement_authorized": False,
        "permanent_action_authorized": False,
    }
    report["report_hash"] = _payload_hash(report)
    return report


def validate_legal_ip_trace_report(report: dict[str, Any]) -> dict[str, Any]:
    _require(report, "schema_version", 1)
    _require(report, "kind", "truecore_legal_ip_trace_report")
    _require(report, "format", "truecore_legal_ip_trace_report_v1")
    for field in ("report_id", "created_at_utc", "title", "remote_ip", "observed_endpoint", "scope"):
        _require_nonempty_string(report, field)
    if not is_canonical_utc_timestamp(report["created_at_utc"]):
        raise CentralContractError("created_at_utc must use canonical UTC timestamp format")
    try:
        ipaddress.ip_address(report["remote_ip"])
    except ValueError as exc:
        raise CentralContractError("remote_ip must be a valid IPv4 or IPv6 address") from exc
    if report.get("severity") not in SEVERITIES:
        raise CentralContractError(f"invalid severity: {report.get('severity')}")
    _require_string_list(report, "facts")
    _require_string_list(report, "evidence_refs")
    _require_string_list(report, "source_refs")
    _require_string_list(report, "unknowns", allow_empty=True)
    _require_string_list(report, "legal_notes")
    _require_evidence_hashes(report.get("evidence_hashes"), report["evidence_refs"])
    _require_chain_of_custody(report.get("chain_of_custody"), set(report["evidence_refs"]))
    _require_containment_release(report.get("containment"))
    _require_nonempty_string(report, "release_receipt_ref")
    if "release" not in report["release_receipt_ref"].lower():
        raise CentralContractError("release_receipt_ref must reference release")
    for forbidden in ("inferences", "recommended_actions", "actions", "conclusion", "verdict"):
        if forbidden in report:
            raise CentralContractError(f"legal IP trace report cannot contain inference/action field: {forbidden}")
    if report.get("fact_authority") is not False:
        raise CentralContractError("legal IP trace report does not create fact authority")
    if report.get("model_authority") is not False:
        raise CentralContractError("legal IP trace report cannot grant model authority")
    if report.get("enforcement_authorized") is not False:
        raise CentralContractError("legal IP trace report cannot authorize enforcement")
    if report.get("permanent_action_authorized") is not False:
        raise CentralContractError("legal IP trace report cannot authorize permanent action")
    _require_nonempty_string(report, "report_hash")
    expected = _payload_hash({key: value for key, value in report.items() if key != "report_hash"})
    if report["report_hash"] != expected:
        raise CentralContractError("report_hash does not match report payload")
    return dict(report)


def build_writer_receipt(
    *,
    request_id: str,
    receipt_id: str,
    status: str,
    output_ref: str,
) -> dict[str, Any]:
    if status not in WRITER_STATUSES:
        raise CentralContractError(f"invalid writer receipt status: {status}")
    return {
        "schema_version": 1,
        "kind": "central_writer_receipt",
        "receipt_id": receipt_id,
        "request_id": request_id,
        "created_at_utc": utc_now(),
        "status": status,
        "output_ref": output_ref,
        "enforcement_authorized": False,
    }


def build_writer_rejection(
    *,
    request_id: str,
    receipt_id: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "central_writer_rejection",
        "receipt_id": receipt_id,
        "request_id": request_id,
        "created_at_utc": utc_now(),
        "status": "rejected",
        "reason": reason,
        "output_ref": "",
        "fact_authority": False,
        "enforcement_authorized": False,
    }


def validate_writer_rejection(rejection: dict[str, Any]) -> dict[str, Any]:
    _require(rejection, "schema_version", 1)
    _require(rejection, "kind", "central_writer_rejection")
    _require(rejection, "status", "rejected")
    for field in ("receipt_id", "request_id", "created_at_utc", "reason"):
        _require_nonempty_string(rejection, field)
    _require(rejection, "output_ref", "")
    if rejection.get("fact_authority") is not False:
        raise CentralContractError("writer rejection is not fact authority")
    if rejection.get("enforcement_authorized") is not False:
        raise CentralContractError("writer rejection cannot authorize enforcement")
    for forbidden in ("facts", "inferences", "recommended_actions", "actions", "adapter_action"):
        if forbidden in rejection:
            raise CentralContractError(f"writer rejection cannot contain {forbidden}")
    return dict(rejection)


def _require(row: dict[str, Any], field: str, expected: Any) -> None:
    if row.get(field) != expected:
        raise CentralContractError(f"{field} must be {expected!r}")


def _require_nonempty_string(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), str) or not row[field].strip():
        raise CentralContractError(f"{field} must be a non-empty string")


def _require_list(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), list):
        raise CentralContractError(f"{field} must be a list")


def _require_string_list(row: dict[str, Any], field: str, *, allow_empty: bool = False) -> None:
    _require_list(row, field)
    if not allow_empty and not row[field]:
        raise CentralContractError(f"{field} must not be empty")
    if not all(isinstance(item, str) and item.strip() for item in row[field]):
        raise CentralContractError(f"{field} must contain only non-empty strings")


def _require_evidence_hashes(value: Any, evidence_refs: list[str]) -> None:
    if not isinstance(value, dict):
        raise CentralContractError("evidence_hashes must be an object")
    for evidence_ref in evidence_refs:
        digest = value.get(evidence_ref)
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise CentralContractError(f"evidence_hashes must include sha256 for {evidence_ref}")


def _require_chain_of_custody(value: Any, evidence_refs: set[str]) -> None:
    if not isinstance(value, list) or not value:
        raise CentralContractError("chain_of_custody must not be empty")
    for row in value:
        if not isinstance(row, dict):
            raise CentralContractError("chain_of_custody entries must be objects")
        for field in ("step", "actor", "timestamp_utc", "evidence_ref", "hash"):
            _require_nonempty_string(row, field)
        if not is_canonical_utc_timestamp(row["timestamp_utc"]):
            raise CentralContractError("chain_of_custody timestamp_utc must use canonical UTC timestamp format")
        if row["evidence_ref"] not in evidence_refs:
            raise CentralContractError("chain_of_custody evidence_ref must match report evidence refs")
        if len(row["hash"]) != 64 or any(char not in "0123456789abcdef" for char in row["hash"]):
            raise CentralContractError("chain_of_custody hash must be sha256 hex")


def _require_containment_release(value: Any) -> None:
    if not isinstance(value, dict):
        raise CentralContractError("containment must be an object")
    _require(value, "mode", "trap_log_release")
    for field in ("plan_hash",):
        _require_nonempty_string(value, field)
    for field in ("trap_required", "log_required", "release_required", "rollback_required"):
        if value.get(field) is not True:
            raise CentralContractError(f"containment {field} must be true")
    ttl = value.get("ttl_seconds")
    if not isinstance(ttl, int) or ttl <= 0:
        raise CentralContractError("containment ttl_seconds must be positive")


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
