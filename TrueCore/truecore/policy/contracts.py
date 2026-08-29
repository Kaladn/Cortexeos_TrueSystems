"""Contracts for approval-gated security action requests."""

from __future__ import annotations

from typing import Any

from truecore.time import utc_now


DECISIONS = {"approved", "denied", "expired"}
MIN_DANGEROUS_ACTION_COOLDOWN_SECONDS = 10


class PolicyContractError(ValueError):
    """Raised when a policy/enforcement contract is unsafe or malformed."""


def build_action_request(
    *,
    request_id: str,
    requested_by: str,
    action_type: str,
    target: dict[str, Any],
    evidence_refs: list[str],
    reason: str,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "policy_action_request",
        "request_id": request_id,
        "created_at_utc": utc_now(),
        "requested_by": requested_by,
        "action_type": action_type,
        "target": target,
        "evidence_refs": evidence_refs,
        "reason": reason,
        "dry_run": dry_run,
        "requires_user_approval": True,
        "adapter_execution_authorized": False,
    }


def validate_action_request(request: dict[str, Any]) -> dict[str, Any]:
    _require(request, "schema_version", 1)
    _require(request, "kind", "policy_action_request")
    for field in ("request_id", "created_at_utc", "requested_by", "action_type", "reason"):
        _require_nonempty_string(request, field)
    if not isinstance(request.get("target"), dict) or not request["target"]:
        raise PolicyContractError("target must be a non-empty object")
    _require_string_list(request, "evidence_refs")
    if not isinstance(request.get("dry_run"), bool):
        raise PolicyContractError("dry_run must be boolean")
    if request.get("requires_user_approval") is not True:
        raise PolicyContractError("action request must require user approval")
    if request.get("adapter_execution_authorized") is not False:
        raise PolicyContractError("action request cannot pre-authorize adapter execution")
    return dict(request)


def build_policy_decision(
    *,
    decision_id: str,
    request_id: str,
    decided_by_user: str,
    decision: str,
    approval_phrase: str,
) -> dict[str, Any]:
    if decision not in DECISIONS:
        raise PolicyContractError(f"invalid decision: {decision}")
    if not decided_by_user.strip():
        raise PolicyContractError("approved/denied policy decisions require user identity")
    authorized = decision == "approved"
    if authorized and not approval_phrase.strip():
        raise PolicyContractError("approval phrase required for approved policy decisions")
    return {
        "schema_version": 1,
        "kind": "policy_decision",
        "decision_id": decision_id,
        "request_id": request_id,
        "created_at_utc": utc_now(),
        "decided_by_user": decided_by_user,
        "decision": decision,
        "approval_phrase": approval_phrase,
        "adapter_execution_authorized": authorized,
    }


def validate_policy_decision(decision: dict[str, Any]) -> dict[str, Any]:
    _require(decision, "schema_version", 1)
    _require(decision, "kind", "policy_decision")
    for field in ("decision_id", "request_id", "created_at_utc", "decided_by_user"):
        _require_nonempty_string(decision, field)
    if decision.get("decision") not in DECISIONS:
        raise PolicyContractError(f"invalid decision: {decision.get('decision')}")
    if not isinstance(decision.get("adapter_execution_authorized"), bool):
        raise PolicyContractError("adapter_execution_authorized must be boolean")
    if decision["decision"] == "approved":
        _require_nonempty_string(decision, "approval_phrase")
        if decision["adapter_execution_authorized"] is not True:
            raise PolicyContractError("approved decision must authorize adapter execution")
    elif decision["adapter_execution_authorized"] is not False:
        raise PolicyContractError("non-approved decision cannot authorize adapter execution")
    return dict(decision)


def build_password_verified_action_decision(
    *,
    decision_id: str,
    request_id: str,
    decided_by_user: str,
    action_type: str,
    target: dict[str, Any],
    evidence_refs: list[str],
    password_verified: bool,
    password_verification_ref: str,
    cooldown_seconds: int = MIN_DANGEROUS_ACTION_COOLDOWN_SECONDS,
) -> dict[str, Any]:
    if not decided_by_user.strip():
        raise PolicyContractError("approved security actions require user identity")
    if password_verified is not True:
        raise PolicyContractError("password verification required for approved security actions")
    if not password_verification_ref.strip():
        raise PolicyContractError("password_verification_ref required for approved security actions")
    if cooldown_seconds < MIN_DANGEROUS_ACTION_COOLDOWN_SECONDS:
        raise PolicyContractError(
            f"cooldown_seconds must be at least {MIN_DANGEROUS_ACTION_COOLDOWN_SECONDS}"
        )
    _require_string_list({"evidence_refs": evidence_refs}, "evidence_refs")
    if not isinstance(target, dict) or not target:
        raise PolicyContractError("target must be a non-empty object")
    return {
        "schema_version": 1,
        "kind": "password_verified_policy_decision",
        "decision_id": decision_id,
        "request_id": request_id,
        "created_at_utc": utc_now(),
        "decided_by_user": decided_by_user,
        "decision": "approved",
        "action_type": action_type,
        "target": target,
        "evidence_refs": evidence_refs,
        "password_verified": True,
        "password_verification_ref": password_verification_ref,
        "cooldown_seconds": cooldown_seconds,
        "adapter_execution_authorized": True,
        "permanent_action_authorized": False,
    }


def validate_password_verified_action_decision(decision: dict[str, Any]) -> dict[str, Any]:
    _require(decision, "schema_version", 1)
    _require(decision, "kind", "password_verified_policy_decision")
    _require(decision, "decision", "approved")
    for field in (
        "decision_id",
        "request_id",
        "created_at_utc",
        "decided_by_user",
        "action_type",
        "password_verification_ref",
    ):
        _require_nonempty_string(decision, field)
    if not isinstance(decision.get("target"), dict) or not decision["target"]:
        raise PolicyContractError("target must be a non-empty object")
    _require_string_list(decision, "evidence_refs")
    if decision.get("password_verified") is not True:
        raise PolicyContractError("password_verified must be true")
    cooldown = decision.get("cooldown_seconds")
    if not isinstance(cooldown, int) or cooldown < MIN_DANGEROUS_ACTION_COOLDOWN_SECONDS:
        raise PolicyContractError(
            f"cooldown_seconds must be at least {MIN_DANGEROUS_ACTION_COOLDOWN_SECONDS}"
        )
    if decision.get("adapter_execution_authorized") is not True:
        raise PolicyContractError("approved password decision must authorize adapter execution")
    if decision.get("permanent_action_authorized") is not False:
        raise PolicyContractError("password verified decision cannot authorize permanent action")
    for forbidden in ("raw_password", "password", "password_hash", "secret"):
        if forbidden in decision:
            raise PolicyContractError(f"password decision cannot contain {forbidden}")
    return dict(decision)


def _require(row: dict[str, Any], field: str, expected: Any) -> None:
    if row.get(field) != expected:
        raise PolicyContractError(f"{field} must be {expected!r}")


def _require_nonempty_string(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), str) or not row[field].strip():
        raise PolicyContractError(f"{field} must be a non-empty string")


def _require_string_list(row: dict[str, Any], field: str) -> None:
    value = row.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise PolicyContractError(f"{field} must be a list of non-empty strings")
