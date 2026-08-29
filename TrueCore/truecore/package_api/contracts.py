"""Contracts for the AnchorWorks-callable TrueCore package boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_CALLERS = {"anchorworks", "truecore"}
ALLOWED_ROUTES = {
    "status.summary",
    "logs.health",
    "fusion.latest",
    "retention.close_window",
    "report.text_facts",
    "report.legal_ip_trace",
    "policy.check_action",
    "runtime.status",
    "runtime.verify_latest",
    "runtime.watch_latest",
}
RESPONSE_STATUSES = {"ok", "rejected", "approval_required", "error"}


class TrueCorePackageError(ValueError):
    """Raised when a package API request or response violates the boundary."""


@dataclass(frozen=True, slots=True)
class TrueCoreRequest:
    request_id: str
    caller: str
    route: str
    purpose: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TrueCoreResponse:
    request_id: str
    status: str
    facts: list[str]
    evidence_refs: list[str]
    warnings: list[str]
    action_required: bool = False
    approval_required: bool = False


def validate_request(request: TrueCoreRequest) -> TrueCoreRequest:
    for field_name in ("request_id", "caller", "route", "purpose"):
        value = getattr(request, field_name)
        if not isinstance(value, str) or not value.strip():
            raise TrueCorePackageError(f"{field_name} must be a non-empty string")
    if request.caller not in ALLOWED_CALLERS:
        raise TrueCorePackageError(f"unknown caller: {request.caller}")
    if request.route not in ALLOWED_ROUTES:
        raise TrueCorePackageError(f"unknown route: {request.route}")
    if not isinstance(request.payload, dict):
        raise TrueCorePackageError("payload must be an object")
    return request


def validate_response(response: TrueCoreResponse) -> TrueCoreResponse:
    if not isinstance(response.request_id, str) or not response.request_id.strip():
        raise TrueCorePackageError("request_id must be a non-empty string")
    if response.status not in RESPONSE_STATUSES:
        raise TrueCorePackageError(f"unknown response status: {response.status}")
    for field_name in ("facts", "evidence_refs", "warnings"):
        value = getattr(response, field_name)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise TrueCorePackageError(f"{field_name} must be a list of strings")
    if response.facts and not response.evidence_refs:
        raise TrueCorePackageError("facts require evidence_refs")
    return response
