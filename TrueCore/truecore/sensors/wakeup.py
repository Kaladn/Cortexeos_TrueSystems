"""Wake-up request contract for low-level readers."""

from __future__ import annotations

from typing import Any

from truecore.time import utc_now


class WakeupContractError(ValueError):
    """Raised when a wake-up request violates the cascade contract."""


def build_wake_request(
    *,
    request_id: str,
    source_reader: str,
    anomaly_type: str,
    observed_object: dict[str, Any],
    changed_fields: list[str],
    confidence: float,
    risk_seed: int,
    suggested_wake_agents: list[str],
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "wake_request",
        "request_id": request_id,
        "created_at_utc": utc_now(),
        "source_reader": source_reader,
        "anomaly_type": anomaly_type,
        "observed_object": observed_object,
        "changed_fields": changed_fields,
        "confidence": confidence,
        "risk_seed": risk_seed,
        "suggested_wake_agents": suggested_wake_agents,
        "evidence_refs": evidence_refs,
        "agents_launched": False,
        "supervisor_required": True,
    }


def validate_wake_request(request: dict[str, Any]) -> dict[str, Any]:
    if request.get("schema_version") != 1:
        raise WakeupContractError("schema_version must be 1")
    if request.get("kind") != "wake_request":
        raise WakeupContractError("kind must be wake_request")
    for field in ("request_id", "created_at_utc", "source_reader", "anomaly_type"):
        _require_nonempty_string(request, field)
    if not isinstance(request.get("observed_object"), dict) or not request["observed_object"]:
        raise WakeupContractError("observed_object must be a non-empty object")
    _require_string_list(request, "changed_fields")
    _require_string_list(request, "suggested_wake_agents")
    _require_string_list(request, "evidence_refs")
    if not request["evidence_refs"]:
        raise WakeupContractError("evidence_refs must not be empty")
    confidence = request.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        raise WakeupContractError("confidence must be between 0 and 1")
    risk_seed = request.get("risk_seed")
    if not isinstance(risk_seed, int) or not 0 <= risk_seed <= 5:
        raise WakeupContractError("risk_seed must be an integer from 0 to 5")
    if request.get("agents_launched") is not False:
        raise WakeupContractError("wake request may not launch agents directly")
    if request.get("supervisor_required") is not True:
        raise WakeupContractError("wake request must require supervisor review")
    return dict(request)


def _require_nonempty_string(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), str) or not row[field].strip():
        raise WakeupContractError(f"{field} must be a non-empty string")


def _require_string_list(row: dict[str, Any], field: str) -> None:
    value = row.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise WakeupContractError(f"{field} must be a list of non-empty strings")
