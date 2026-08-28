"""Contracts for the AnchorWorks-callable SecureCore package boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_CALLERS = {"anchorworks", "securecore"}
ALLOWED_ROUTES = {
    "status.summary",
    "logs.health",
    "fusion.latest",
    "retention.close_window",
    "report.text_facts",
    "report.legal_ip_trace",
    "policy.check_action",
    "runtime.logging.run",
    "runtime.status",
    "runtime.verify_latest",
    "runtime.watch_latest",
}
RESPONSE_STATUSES = {"ok", "rejected", "approval_required", "error"}


class SecureCorePackageError(ValueError):
    """Raised when a package API request or response violates the boundary."""


@dataclass(frozen=True, slots=True)
class SecureCoreRequest:
    request_id: str
    caller: str
    route: str
    purpose: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SecureCoreResponse:
    request_id: str
    status: str
    facts: list[str]
    evidence_refs: list[str]
    warnings: list[str]
    action_required: bool = False
    approval_required: bool = False


def validate_request(request: SecureCoreRequest) -> SecureCoreRequest:
    for field_name in ("request_id", "caller", "route", "purpose"):
        value = getattr(request, field_name)
        if not isinstance(value, str) or not value.strip():
            raise SecureCorePackageError(f"{field_name} must be a non-empty string")
    if request.caller not in ALLOWED_CALLERS:
        raise SecureCorePackageError(f"unknown caller: {request.caller}")
    if request.route not in ALLOWED_ROUTES:
        raise SecureCorePackageError(f"unknown route: {request.route}")
    if not isinstance(request.payload, dict):
        raise SecureCorePackageError("payload must be an object")
    return request


def validate_response(response: SecureCoreResponse) -> SecureCoreResponse:
    if not isinstance(response.request_id, str) or not response.request_id.strip():
        raise SecureCorePackageError("request_id must be a non-empty string")
    if response.status not in RESPONSE_STATUSES:
        raise SecureCorePackageError(f"unknown response status: {response.status}")
    for field_name in ("facts", "evidence_refs", "warnings"):
        value = getattr(response, field_name)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise SecureCorePackageError(f"{field_name} must be a list of strings")
    if response.facts and not response.evidence_refs:
        raise SecureCorePackageError("facts require evidence_refs")
    return response
