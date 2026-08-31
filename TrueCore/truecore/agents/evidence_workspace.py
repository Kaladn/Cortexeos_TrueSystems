"""Request-driven evidence workspace agent.

The agent coordinates declared, read-only TrueSystems evidence services.  It
does not search, rank, parse source material, or create evidence itself.
Services return verified records and may propose a continuation.  A proposed
continuation is eligible only when it is allowed by the work order and cites an
evidence record already present in the workspace.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


SCHEMA = "truecore_evidence_workspace_agent@1"
WORK_ORDER_SCHEMA = "truecore_evidence_work_order@1"
SERVICE_RESULT_SCHEMA = "truesystems_evidence_service_result@1"

TERMINAL_STATUSES = {
    "COMPLETE",
    "PARTIAL_FIXED_POINT",
    "AMBIGUOUS",
    "MISSING_IDENTITY",
    "STALE_REFERENCE",
    "RESOURCE_LIMIT",
    "SERVICE_UNAVAILABLE",
    "CONTRACT_ERROR",
}

SERVICE_STATUSES = {
    "VERIFIED",
    "PARTIAL",
    "AMBIGUOUS",
    "MISSING_IDENTITY",
    "STALE_REFERENCE",
    "SERVICE_UNAVAILABLE",
    "ERROR",
}


class EvidenceWorkspaceContractError(ValueError):
    """Raised when a work order or service packet violates the agent contract."""


@dataclass(frozen=True)
class EvidenceService:
    service_id: str
    invoke: Callable[[dict[str, Any]], dict[str, Any]]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_work_order(work_order: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(work_order, dict):
        raise EvidenceWorkspaceContractError("work order must be an object")
    required = {
        "schema",
        "task_id",
        "dataset_id",
        "obligations",
        "initial_requests",
        "allowed_services",
        "limits",
    }
    missing = sorted(required.difference(work_order))
    if missing:
        raise EvidenceWorkspaceContractError(f"work order missing fields: {missing}")
    if work_order["schema"] != WORK_ORDER_SCHEMA:
        raise EvidenceWorkspaceContractError("unsupported work-order schema")
    _nonempty_string(work_order, "task_id")
    _nonempty_string(work_order, "dataset_id")
    obligations = work_order["obligations"]
    if not isinstance(obligations, list) or not obligations:
        raise EvidenceWorkspaceContractError("obligations must be a non-empty list")
    obligation_ids: list[str] = []
    for row in obligations:
        if not isinstance(row, dict):
            raise EvidenceWorkspaceContractError("every obligation must be an object")
        _nonempty_string(row, "obligation_id")
        _nonempty_string(row, "evidence_role")
        obligation_ids.append(row["obligation_id"])
    if len(set(obligation_ids)) != len(obligation_ids):
        raise EvidenceWorkspaceContractError("obligation IDs must be unique")

    allowed_services = work_order["allowed_services"]
    if not isinstance(allowed_services, list) or not allowed_services:
        raise EvidenceWorkspaceContractError("allowed_services must be a non-empty list")
    if not all(isinstance(value, str) and value for value in allowed_services):
        raise EvidenceWorkspaceContractError("allowed_services contains an invalid service ID")
    if len(set(allowed_services)) != len(allowed_services):
        raise EvidenceWorkspaceContractError("allowed_services contains duplicates")

    requests = work_order["initial_requests"]
    if not isinstance(requests, list) or not requests:
        raise EvidenceWorkspaceContractError("initial_requests must be a non-empty list")
    for request in requests:
        _validate_request(request, set(allowed_services), set(obligation_ids))

    limits = work_order["limits"]
    if not isinstance(limits, dict):
        raise EvidenceWorkspaceContractError("limits must be an object")
    max_service_calls = limits.get("max_service_calls")
    if not isinstance(max_service_calls, int) or max_service_calls <= 0:
        raise EvidenceWorkspaceContractError("max_service_calls must be a positive integer")
    return json.loads(canonical_bytes(work_order))


def validate_service_result(
    result: dict[str, Any],
    *,
    allowed_services: set[str],
    obligation_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise EvidenceWorkspaceContractError("service result must be an object")
    required = {
        "schema",
        "service_id",
        "status",
        "resolved_obligation_ids",
        "evidence_records",
        "continuations",
        "receipt_ref",
    }
    missing = sorted(required.difference(result))
    if missing:
        raise EvidenceWorkspaceContractError(f"service result missing fields: {missing}")
    if result["schema"] != SERVICE_RESULT_SCHEMA:
        raise EvidenceWorkspaceContractError("unsupported service-result schema")
    if result["service_id"] not in allowed_services:
        raise EvidenceWorkspaceContractError("service result names an undeclared service")
    if result["status"] not in SERVICE_STATUSES:
        raise EvidenceWorkspaceContractError("service result has an invalid status")
    resolved = result["resolved_obligation_ids"]
    if not isinstance(resolved, list) or not all(value in obligation_ids for value in resolved):
        raise EvidenceWorkspaceContractError("service result resolves an unknown obligation")
    if not isinstance(result["evidence_records"], list):
        raise EvidenceWorkspaceContractError("evidence_records must be a list")
    for evidence in result["evidence_records"]:
        _validate_evidence_record(evidence)
    if not isinstance(result["continuations"], list):
        raise EvidenceWorkspaceContractError("continuations must be a list")
    for continuation in result["continuations"]:
        _validate_request(continuation, allowed_services, obligation_ids, require_basis=True)
    _nonempty_string(result, "receipt_ref")
    return json.loads(canonical_bytes(result))


class EvidenceWorkspaceAgent:
    """Coordinate one bounded evidence work order over supplied services."""

    agent_id = "evidence_workspace_agent"
    version = "1.0.0"

    def __init__(self, services: Mapping[str, EvidenceService | Callable[[dict[str, Any]], dict[str, Any]]]):
        normalized: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        for service_id, service in services.items():
            if not isinstance(service_id, str) or not service_id:
                raise EvidenceWorkspaceContractError("service registry contains an invalid ID")
            if isinstance(service, EvidenceService):
                if service.service_id != service_id:
                    raise EvidenceWorkspaceContractError("service registry ID mismatch")
                normalized[service_id] = service.invoke
            elif callable(service):
                normalized[service_id] = service
            else:
                raise EvidenceWorkspaceContractError("service registry value is not callable")
        self._services = normalized

    def run(self, work_order: dict[str, Any]) -> dict[str, Any]:
        try:
            order = validate_work_order(work_order)
        except EvidenceWorkspaceContractError as exc:
            return self._contract_error(work_order, str(exc))

        allowed_services = set(order["allowed_services"])
        obligation_ids = {row["obligation_id"] for row in order["obligations"]}
        unresolved = set(obligation_ids)
        evidence_by_id: dict[str, dict[str, Any]] = {}
        receipts: list[str] = []
        trace: list[dict[str, Any]] = []
        queue = deque(order["initial_requests"])
        seen_requests: set[str] = set()
        calls = 0
        observed_statuses: list[str] = []
        terminal_override: str | None = None

        while queue and unresolved:
            if calls >= order["limits"]["max_service_calls"]:
                terminal_override = "RESOURCE_LIMIT"
                break
            request = queue.popleft()
            request_hash = stable_hash(request)
            if request_hash in seen_requests:
                continue
            seen_requests.add(request_hash)
            service_id = request["service_id"]
            invoke = self._services.get(service_id)
            if invoke is None:
                observed_statuses.append("SERVICE_UNAVAILABLE")
                trace.append({
                    "step": len(trace) + 1,
                    "request_hash": request_hash,
                    "service_id": service_id,
                    "status": "SERVICE_UNAVAILABLE",
                    "new_evidence_ids": [],
                    "newly_resolved_obligation_ids": [],
                    "accepted_continuation_hashes": [],
                })
                continue

            calls += 1
            try:
                raw_result = invoke(json.loads(canonical_bytes(request["request"])))
                result = validate_service_result(
                    raw_result,
                    allowed_services=allowed_services,
                    obligation_ids=obligation_ids,
                )
            except EvidenceWorkspaceContractError as exc:
                return self._contract_error(order, str(exc), trace=trace)
            except Exception as exc:  # service boundary: preserve failure, do not infer
                observed_statuses.append("SERVICE_UNAVAILABLE")
                trace.append({
                    "step": len(trace) + 1,
                    "request_hash": request_hash,
                    "service_id": service_id,
                    "status": "SERVICE_UNAVAILABLE",
                    "failure_type": type(exc).__name__,
                    "new_evidence_ids": [],
                    "newly_resolved_obligation_ids": [],
                    "accepted_continuation_hashes": [],
                })
                continue

            observed_statuses.append(result["status"])
            new_evidence_ids: list[str] = []
            for evidence in result["evidence_records"]:
                evidence_id = evidence["evidence_id"]
                existing = evidence_by_id.get(evidence_id)
                if existing is not None and stable_hash(existing) != stable_hash(evidence):
                    return self._contract_error(order, f"conflicting evidence identity: {evidence_id}", trace=trace)
                if existing is None:
                    evidence_by_id[evidence_id] = evidence
                    new_evidence_ids.append(evidence_id)

            newly_resolved = sorted(unresolved.intersection(result["resolved_obligation_ids"]))
            unresolved.difference_update(newly_resolved)
            if result["receipt_ref"] not in receipts:
                receipts.append(result["receipt_ref"])

            accepted_continuations: list[str] = []
            evidence_ids = set(evidence_by_id)
            for continuation in result["continuations"]:
                basis = set(continuation["basis_evidence_refs"])
                if not basis or not basis.issubset(evidence_ids):
                    continue
                continuation_hash = stable_hash(continuation)
                if continuation_hash not in seen_requests:
                    queue.append(continuation)
                    accepted_continuations.append(continuation_hash)

            trace.append({
                "step": len(trace) + 1,
                "request_hash": request_hash,
                "service_id": service_id,
                "status": result["status"],
                "new_evidence_ids": sorted(new_evidence_ids),
                "newly_resolved_obligation_ids": newly_resolved,
                "accepted_continuation_hashes": sorted(accepted_continuations),
            })

        status = terminal_override or self._terminal_status(unresolved, observed_statuses)
        workspace_core = {
            "task_id": order["task_id"],
            "dataset_id": order["dataset_id"],
            "resolved_obligation_ids": sorted(obligation_ids - unresolved),
            "unresolved_obligation_ids": sorted(unresolved),
            "evidence_records": [evidence_by_id[key] for key in sorted(evidence_by_id)],
            "service_receipt_refs": receipts,
            "trace": trace,
        }
        return {
            "schema": SCHEMA,
            "agent_id": self.agent_id,
            "agent_version": self.version,
            "status": status,
            "work_order_hash": stable_hash(order),
            "workspace": workspace_core,
            "workspace_hash": stable_hash(workspace_core),
            "service_call_count": calls,
            "model_used": False,
            "evidence_services_executed": calls > 0,
            "selected_operations_executed": False,
            "evidence_authority_created": False,
            "relationship_authority_created": False,
            "mutation_authorized": False,
        }

    @staticmethod
    def _terminal_status(unresolved: set[str], statuses: list[str]) -> str:
        if not unresolved:
            return "COMPLETE"
        if "AMBIGUOUS" in statuses:
            return "AMBIGUOUS"
        if "STALE_REFERENCE" in statuses:
            return "STALE_REFERENCE"
        if "MISSING_IDENTITY" in statuses:
            return "MISSING_IDENTITY"
        if "SERVICE_UNAVAILABLE" in statuses or "ERROR" in statuses:
            return "SERVICE_UNAVAILABLE"
        return "PARTIAL_FIXED_POINT"

    def _contract_error(
        self,
        work_order: Any,
        reason: str,
        *,
        trace: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        safe_order_hash = stable_hash(work_order)
        workspace = {
            "task_id": work_order.get("task_id") if isinstance(work_order, dict) else None,
            "dataset_id": work_order.get("dataset_id") if isinstance(work_order, dict) else None,
            "resolved_obligation_ids": [],
            "unresolved_obligation_ids": [],
            "evidence_records": [],
            "service_receipt_refs": [],
            "trace": list(trace or []),
            "contract_error": reason,
        }
        return {
            "schema": SCHEMA,
            "agent_id": self.agent_id,
            "agent_version": self.version,
            "status": "CONTRACT_ERROR",
            "work_order_hash": safe_order_hash,
            "workspace": workspace,
            "workspace_hash": stable_hash(workspace),
            "service_call_count": len(trace or []),
            "model_used": False,
            "evidence_services_executed": bool(trace),
            "selected_operations_executed": False,
            "evidence_authority_created": False,
            "relationship_authority_created": False,
            "mutation_authorized": False,
        }


def _validate_request(
    request: Any,
    allowed_services: set[str],
    obligation_ids: set[str],
    *,
    require_basis: bool = False,
) -> None:
    if not isinstance(request, dict):
        raise EvidenceWorkspaceContractError("service request must be an object")
    required = {"service_id", "request", "supports_obligation_ids"}
    if require_basis:
        required.add("basis_evidence_refs")
    missing = sorted(required.difference(request))
    if missing:
        raise EvidenceWorkspaceContractError(f"service request missing fields: {missing}")
    if request["service_id"] not in allowed_services:
        raise EvidenceWorkspaceContractError("service request names an undeclared service")
    if not isinstance(request["request"], dict):
        raise EvidenceWorkspaceContractError("service request payload must be an object")
    supported = request["supports_obligation_ids"]
    if not isinstance(supported, list) or not supported or not all(value in obligation_ids for value in supported):
        raise EvidenceWorkspaceContractError("service request supports an unknown obligation")
    if require_basis:
        basis = request["basis_evidence_refs"]
        if not isinstance(basis, list) or not all(isinstance(value, str) and value for value in basis):
            raise EvidenceWorkspaceContractError("continuation basis must be a string list")


def _validate_evidence_record(evidence: Any) -> None:
    if not isinstance(evidence, dict):
        raise EvidenceWorkspaceContractError("evidence record must be an object")
    required = {"evidence_id", "source_hash", "citation", "coordinates", "authority_status"}
    missing = sorted(required.difference(evidence))
    if missing:
        raise EvidenceWorkspaceContractError(f"evidence record missing fields: {missing}")
    for field in ("evidence_id", "source_hash", "citation", "authority_status"):
        _nonempty_string(evidence, field)
    if not isinstance(evidence["coordinates"], dict) or not evidence["coordinates"]:
        raise EvidenceWorkspaceContractError("evidence coordinates must be a non-empty object")


def _nonempty_string(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), str) or not row[field].strip():
        raise EvidenceWorkspaceContractError(f"{field} must be a non-empty string")
