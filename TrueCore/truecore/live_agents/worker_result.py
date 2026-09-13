"""Common processable result contract for every TrueCore worker execution."""

from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA = "truecore.worker_result@1"
STATUSES = frozenset({
    "COMPLETE",
    "PARTIAL",
    "AMBIGUOUS",
    "UNRESOLVED",
    "REFUSED",
    "NOT_IMPLEMENTED",
    "FAILED",
})
CONTINUATIONS = frozenset({
    "STOP_COMPLETE",
    "STOP_PARTIAL",
    "STOP_AMBIGUOUS",
    "STOP_NO_EVIDENCE",
    "STOP_REFUSED",
    "STOP_NOT_IMPLEMENTED",
    "STOP_FAILED",
    "NEXT_CALL",
    "RETRY_WITH_CORRECTED_BINDING",
    "ASK_HUMAN",
})
CLAIM_STATUSES = frozenset({
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "AMBIGUOUS",
    "CONTRADICTED",
    "NOT_FOUND",
    "UNAVAILABLE_FROM_SOURCE",
    "OPERATION_FAILED",
    "PROVEN_ABSENT",
})


class WorkerResultError(ValueError):
    """Raised when a worker result cannot enter the TrueCore result stream."""


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def build_result(
    *,
    worker_id: str,
    operation: str,
    status: str,
    result: Any = None,
    locations: list[dict[str, Any]] | None = None,
    relationships: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    claims: list[dict[str, Any]] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    unresolved: list[dict[str, Any]] | None = None,
    errors: list[dict[str, Any]] | None = None,
    receipts: list[dict[str, Any]] | None = None,
    continuation: str = "STOP_COMPLETE",
    reason_code: str = "OPERATION_COMPLETE",
) -> dict[str, Any]:
    packet = {
        "schema": SCHEMA,
        "worker_id": worker_id,
        "operation": operation,
        "status": status,
        "result": result,
        "locations": locations or [],
        "relationships": relationships or [],
        "evidence": evidence or [],
        "claims": claims or [],
        "artifacts": artifacts or [],
        "unresolved": unresolved or [],
        "errors": errors or [],
        "receipts": receipts or [],
        "continuation": {"state": continuation, "reason_code": reason_code},
    }
    validate_result(packet)
    packet["result_sha256"] = digest(packet)
    return packet


def validate_result(packet: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict) or packet.get("schema") != SCHEMA:
        raise WorkerResultError("unsupported worker-result schema")
    for field in ("worker_id", "operation", "status"):
        if not isinstance(packet.get(field), str) or not packet[field].strip():
            raise WorkerResultError(f"{field} must be a nonempty string")
    if packet["status"] not in STATUSES:
        raise WorkerResultError("unknown worker-result status")
    for field in ("locations", "relationships", "evidence", "claims", "artifacts", "unresolved", "errors", "receipts"):
        value = packet.get(field)
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise WorkerResultError(f"{field} must be a list of objects")
    continuation = packet.get("continuation")
    if not isinstance(continuation, dict) or continuation.get("state") not in CONTINUATIONS:
        raise WorkerResultError("invalid continuation state")
    if not isinstance(continuation.get("reason_code"), str) or not continuation["reason_code"]:
        raise WorkerResultError("continuation reason_code must be a nonempty string")
    if packet["status"] == "COMPLETE" and packet["errors"]:
        raise WorkerResultError("COMPLETE worker result cannot contain errors")
    evidence_ids = {
        item.get("evidence_id") for item in packet["evidence"]
        if isinstance(item.get("evidence_id"), str) and item["evidence_id"]
    }
    for claim in packet["claims"]:
        if claim.get("status") not in CLAIM_STATUSES:
            raise WorkerResultError("claim has invalid support status")
        bindings = claim.get("evidence_ids", [])
        if not isinstance(bindings, list) or not all(isinstance(item, str) for item in bindings):
            raise WorkerResultError("claim evidence_ids must be a list of strings")
        if claim["status"] == "SUPPORTED" and not bindings:
            raise WorkerResultError("SUPPORTED claim requires evidence binding")
        unknown = sorted(set(bindings) - evidence_ids)
        if unknown:
            raise WorkerResultError(f"claim binds unknown evidence: {unknown[0]}")
    expected = packet.get("result_sha256")
    if expected is not None:
        unsigned = dict(packet)
        unsigned.pop("result_sha256")
        if expected != digest(unsigned):
            raise WorkerResultError("worker-result hash mismatch")
    return packet


def normalize_process_result(
    *,
    worker_id: str,
    operation: str,
    returncode: int,
    stdout: bytes,
    stderr: bytes,
    entrypoint_hash: str,
    input_binding_hash: str,
) -> dict[str, Any]:
    """Wrap any legacy worker output; preserve native structured output when present."""
    parsed: Any = None
    stripped = stdout.strip()
    if stripped:
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = {"stdout_utf8": stdout.decode("utf-8", errors="replace")}
    if isinstance(parsed, dict) and parsed.get("schema") == SCHEMA:
        validate_result(parsed)
        if parsed["worker_id"] != worker_id:
            raise WorkerResultError("worker output identity does not match invoked worker")
        return parsed
    errors = []
    if stderr:
        errors.append({"kind": "PROCESS_STDERR", "text_utf8": stderr.decode("utf-8", errors="replace")})
    status = "COMPLETE" if returncode == 0 else "FAILED"
    continuation = "STOP_COMPLETE" if returncode == 0 else "STOP_FAILED"
    return build_result(
        worker_id=worker_id,
        operation=operation,
        status=status,
        result={"native_output": parsed},
        errors=errors,
        receipts=[{
            "receipt_type": "truecore.process_execution@1",
            "returncode": returncode,
            "entrypoint_hash": entrypoint_hash,
            "input_binding_hash": input_binding_hash,
            "stdout_sha256": "sha256:" + hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": "sha256:" + hashlib.sha256(stderr).hexdigest(),
        }],
        continuation=continuation,
        reason_code="PROCESS_EXIT_ZERO" if returncode == 0 else "PROCESS_EXIT_NONZERO",
    )
