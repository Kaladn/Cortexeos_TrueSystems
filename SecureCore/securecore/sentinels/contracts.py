"""Contracts for observer-only SecureCore sentinels."""

from __future__ import annotations

from typing import Any

from securecore.time import is_canonical_utc_timestamp, utc_now


class SentinelContractError(ValueError):
    """Raised when a sentinel tries to exceed observer authority."""


def validate_sentinel_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    required = {
        "sentinel_id",
        "version",
        "entrypoint",
        "allowed_reads",
        "allowed_writes",
        "mutation_authority",
        "policy_approval_authority",
        "temporal_write_authority",
        "direct_user_alert_authority",
    }
    missing = sorted(required.difference(manifest))
    if missing:
        raise SentinelContractError(f"sentinel manifest missing fields: {missing}")
    for field in ("sentinel_id", "version", "entrypoint"):
        if not str(manifest.get(field, "")):
            raise SentinelContractError(f"{field} is required")
    for field in ("allowed_reads", "allowed_writes"):
        if not isinstance(manifest[field], list):
            raise SentinelContractError(f"{field} must be a list")
    _require_false(manifest, "mutation_authority")
    _require_false(manifest, "policy_approval_authority")
    _require_false(manifest, "temporal_write_authority")
    _require_false(manifest, "direct_user_alert_authority")
    return manifest


def build_sentinel_result(
    *,
    sentinel_id: str,
    status: str,
    facts: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    warnings: list[str] | None = None,
    wake_requests: list[dict[str, Any]] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = {
        "schema_version": 1,
        "kind": "securecore_sentinel_result",
        "created_at_utc": utc_now(),
        "sentinel_id": sentinel_id,
        "status": status,
        "facts": [str(item) for item in facts or []],
        "evidence_refs": [str(item) for item in evidence_refs or []],
        "warnings": [str(item) for item in warnings or []],
        "wake_requests": [dict(item) for item in wake_requests or []],
        "artifacts": [dict(item) for item in artifacts or []],
        "engine_write_authorized": False,
        "mutation_authorized": False,
        "policy_approval_authority": False,
        "direct_user_alert_authority": False,
    }
    return validate_sentinel_result(result)


def validate_sentinel_result(result: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "kind",
        "created_at_utc",
        "sentinel_id",
        "status",
        "facts",
        "evidence_refs",
        "warnings",
        "wake_requests",
        "artifacts",
        "engine_write_authorized",
        "mutation_authorized",
        "policy_approval_authority",
        "direct_user_alert_authority",
    }
    missing = sorted(required.difference(result))
    if missing:
        raise SentinelContractError(f"sentinel result missing fields: {missing}")
    _require(result, "schema_version", 1)
    _require(result, "kind", "securecore_sentinel_result")
    _require_false(result, "engine_write_authorized")
    _require_false(result, "mutation_authorized")
    _require_false(result, "policy_approval_authority")
    _require_false(result, "direct_user_alert_authority")
    if result["status"] not in {"ok", "alert", "error"}:
        raise SentinelContractError("status must be ok, alert, or error")
    if not is_canonical_utc_timestamp(str(result["created_at_utc"])):
        raise SentinelContractError("created_at_utc must be canonical UTC")
    for field in ("facts", "evidence_refs", "warnings", "wake_requests", "artifacts"):
        if not isinstance(result[field], list):
            raise SentinelContractError(f"{field} must be a list")
    for wake in result["wake_requests"]:
        _validate_wake_request(wake)
    return result


def _validate_wake_request(wake: dict[str, Any]) -> None:
    if not str(wake.get("requested_engine", "")):
        raise SentinelContractError("wake request missing requested_engine")
    if not str(wake.get("reason", "")):
        raise SentinelContractError("wake request missing reason")
    if not isinstance(wake.get("evidence_refs", []), list):
        raise SentinelContractError("wake request evidence_refs must be a list")


def _require(row: dict[str, Any], field: str, expected: Any) -> None:
    if row.get(field) != expected:
        raise SentinelContractError(f"{field} must be {expected!r}")


def _require_false(row: dict[str, Any], field: str) -> None:
    _require(row, field, False)
