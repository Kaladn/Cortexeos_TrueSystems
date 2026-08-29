"""TrueCore internal self-audit logger.

This logger is not part of the normal sensor/logging lane. It writes independent
receipts that let the operator verify TrueCore itself: watchers, runners,
policy gates, Forge health, seal state, queue drift, and unexpected mutations.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from truecore.time import is_canonical_utc_timestamp, utc_now


ALLOWED_TRUST_TARGETS = {
    "forge",
    "fusion",
    "retention",
    "policy",
    "runner",
    "queues",
    "mutation",
    "watchers",
}


class InternalSelfLogger:
    """Write independent TrueCore self-audit receipts."""

    def __init__(self, receipt_root: str | Path):
        self.receipt_root = Path(receipt_root)

    def write_receipt(
        self,
        *,
        host_id: str,
        checks: list[dict[str, Any]],
        observer_id: str = "sc_internal_logger",
        human_verification: dict[str, Any] | None = None,
        machine_growth: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        receipt = build_self_audit_receipt(
            host_id=host_id,
            observer_id=observer_id,
            checks=checks,
            human_verification=human_verification,
            machine_growth=machine_growth,
        )
        safe_time = receipt["created_at_utc"].replace(":", "").replace(".", "")
        path = self.receipt_root / f"{safe_time}-{receipt['receipt_id']}.self_audit.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        receipt["receipt_path"] = str(path)
        return receipt

    def write_trust_receipt(
        self,
        *,
        host_id: str,
        checks: list[dict[str, Any]],
        observer_id: str = "sc_internal_logger",
    ) -> dict[str, Any]:
        receipt = build_system_trust_receipt(
            host_id=host_id,
            checks=checks,
            observer_id=observer_id,
        )
        safe_time = receipt["created_at_utc"].replace(":", "").replace(".", "")
        path = self.receipt_root / f"{safe_time}-{receipt['receipt_id']}.system_trust.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        receipt["receipt_path"] = str(path)
        return receipt


def build_self_audit_receipt(
    *,
    host_id: str,
    checks: list[dict[str, Any]],
    observer_id: str = "sc_internal_logger",
    human_verification: dict[str, Any] | None = None,
    machine_growth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    created_at = utc_now()
    normalized_checks = [_normalize_check(check) for check in checks]
    anomaly_count = sum(1 for check in normalized_checks if check["status"] != "ok")
    receipt = {
        "schema_version": 1,
        "kind": "truecore_internal_self_audit_receipt",
        "receipt_id": "",
        "created_at_utc": created_at,
        "host_id": host_id,
        "observer_id": observer_id,
        "normal_logging_lane": False,
        "mutation_authorized": False,
        "policy_approval_authority": False,
        "runtime_recovery_action_taken": False,
        "suppression_authority": False,
        "retention_class": "internal_self_audit_keep",
        "status": "ok" if anomaly_count == 0 else "alert",
        "anomaly_count": anomaly_count,
        "checks": normalized_checks,
        "human_verification": _normalize_human_verification(human_verification),
        "machine_growth": _normalize_machine_growth(machine_growth),
    }
    receipt["receipt_id"] = _receipt_id(receipt)
    return validate_self_audit_receipt(receipt)


def validate_self_audit_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "kind",
        "receipt_id",
        "created_at_utc",
        "host_id",
        "observer_id",
        "normal_logging_lane",
        "mutation_authorized",
        "policy_approval_authority",
        "runtime_recovery_action_taken",
        "suppression_authority",
        "retention_class",
        "status",
        "anomaly_count",
        "checks",
        "human_verification",
        "machine_growth",
    }
    missing = sorted(required.difference(receipt))
    if missing:
        raise ValueError(f"self audit receipt missing fields: {missing}")
    _require(receipt, "schema_version", 1)
    _require(receipt, "kind", "truecore_internal_self_audit_receipt")
    _require(receipt, "normal_logging_lane", False)
    _require(receipt, "mutation_authorized", False)
    _require(receipt, "policy_approval_authority", False)
    _require(receipt, "runtime_recovery_action_taken", False)
    _require(receipt, "suppression_authority", False)
    _require(receipt, "retention_class", "internal_self_audit_keep")
    if not is_canonical_utc_timestamp(str(receipt["created_at_utc"])):
        raise ValueError("created_at_utc must be canonical UTC")
    if receipt["status"] not in {"ok", "alert"}:
        raise ValueError("status must be ok or alert")
    checks = receipt["checks"]
    if not isinstance(checks, list):
        raise ValueError("checks must be a list")
    for check in checks:
        _validate_check(check)
    expected_anomalies = sum(1 for check in checks if check["status"] != "ok")
    if int(receipt["anomaly_count"]) != expected_anomalies:
        raise ValueError("anomaly_count does not match checks")
    _validate_human_verification(receipt["human_verification"])
    _validate_machine_growth(receipt["machine_growth"])
    return receipt


def build_system_trust_receipt(
    *,
    host_id: str,
    checks: list[dict[str, Any]],
    observer_id: str = "sc_internal_logger",
) -> dict[str, Any]:
    normalized_checks = [_normalize_trust_check(check) for check in checks]
    reasons = [
        f"{check['target']}: {check['message']}"
        for check in normalized_checks
        if check["status"] != "ok"
    ]
    evidence_refs = []
    for check in normalized_checks:
        if check["status"] != "ok":
            evidence_refs.extend(check["evidence_refs"])
    status = _trust_status(normalized_checks)
    receipt = {
        "schema_version": 1,
        "kind": "truecore_system_trust_receipt",
        "receipt_id": "",
        "created_at_utc": utc_now(),
        "host_id": host_id,
        "observer_id": observer_id,
        "status": status,
        "reasons": reasons,
        "reason_count": len(reasons),
        "evidence_refs": sorted(set(evidence_refs)),
        "full_diary": False,
        "mutation_authorized": False,
        "policy_approval_authority": False,
        "runtime_recovery_action_taken": False,
        "suppression_authority": False,
        "checks": normalized_checks,
    }
    receipt["receipt_id"] = _receipt_id(receipt)
    return validate_system_trust_receipt(receipt)


def validate_system_trust_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "kind",
        "receipt_id",
        "created_at_utc",
        "host_id",
        "observer_id",
        "status",
        "reasons",
        "reason_count",
        "evidence_refs",
        "full_diary",
        "mutation_authorized",
        "policy_approval_authority",
        "runtime_recovery_action_taken",
        "suppression_authority",
        "checks",
    }
    missing = sorted(required.difference(receipt))
    if missing:
        raise ValueError(f"system trust receipt missing fields: {missing}")
    _require(receipt, "schema_version", 1)
    _require(receipt, "kind", "truecore_system_trust_receipt")
    _require(receipt, "full_diary", False)
    _require(receipt, "mutation_authorized", False)
    _require(receipt, "policy_approval_authority", False)
    _require(receipt, "runtime_recovery_action_taken", False)
    _require(receipt, "suppression_authority", False)
    if receipt["status"] not in {"green", "yellow", "red"}:
        raise ValueError("system trust status must be green, yellow, or red")
    if not is_canonical_utc_timestamp(str(receipt["created_at_utc"])):
        raise ValueError("created_at_utc must be canonical UTC")
    if not isinstance(receipt["reasons"], list):
        raise ValueError("reasons must be a list")
    if int(receipt["reason_count"]) != len(receipt["reasons"]):
        raise ValueError("reason_count does not match reasons")
    if not isinstance(receipt["evidence_refs"], list):
        raise ValueError("evidence_refs must be a list")
    checks = receipt["checks"]
    if not isinstance(checks, list):
        raise ValueError("checks must be a list")
    for check in checks:
        _validate_trust_check(check)
    if receipt["status"] != _trust_status(checks):
        raise ValueError("system trust status does not match checks")
    return receipt


def _normalize_check(check: dict[str, Any]) -> dict[str, Any]:
    row = {
        "target": str(check.get("target", "")),
        "status": str(check.get("status", "")),
        "message": str(check.get("message", "")),
        "evidence_refs": [str(item) for item in check.get("evidence_refs", [])],
    }
    details = check.get("details")
    if isinstance(details, dict):
        row["details"] = details
    _validate_check(row)
    return row


def _normalize_trust_check(check: dict[str, Any]) -> dict[str, Any]:
    row = _normalize_check(check)
    _validate_trust_check(row)
    return row


def _validate_check(check: dict[str, Any]) -> None:
    for field in ("target", "status", "message", "evidence_refs"):
        if field not in check:
            raise ValueError(f"check missing {field}")
    if not check["target"]:
        raise ValueError("check target is required")
    if check["status"] not in {"ok", "alert", "unknown"}:
        raise ValueError("check status must be ok, alert, or unknown")
    if not isinstance(check["evidence_refs"], list):
        raise ValueError("check evidence_refs must be a list")


def _validate_trust_check(check: dict[str, Any]) -> None:
    _validate_check(check)
    if check["target"] not in ALLOWED_TRUST_TARGETS:
        raise ValueError(f"unsupported trust target: {check['target']}")


def _trust_status(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "alert" in statuses:
        return "yellow"
    if "unknown" in statuses:
        return "yellow"
    return "green"


def _normalize_human_verification(value: dict[str, Any] | None) -> dict[str, Any]:
    value = dict(value or {})
    return {
        "signal": str(value.get("signal", "not_provided")),
        "method": str(value.get("method", "none")),
        "confidence": _clamp_float(value.get("confidence", 0.0)),
        "evidence_refs": [str(item) for item in value.get("evidence_refs", [])],
        "final_security_decision": False,
    }


def _validate_human_verification(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("human_verification must be an object")
    _require(value, "final_security_decision", False)
    confidence = float(value.get("confidence", -1.0))
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("human_verification confidence must be 0..1")
    if not isinstance(value.get("evidence_refs"), list):
        raise ValueError("human_verification evidence_refs must be a list")


def _normalize_machine_growth(value: dict[str, Any] | None) -> dict[str, Any]:
    value = dict(value or {})
    return {
        "lesson_refs": [str(item) for item in value.get("lesson_refs", [])],
        "notes": [str(item) for item in value.get("notes", [])],
        "fact_authority": False,
        "mutation_authority": False,
    }


def _validate_machine_growth(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("machine_growth must be an object")
    _require(value, "fact_authority", False)
    _require(value, "mutation_authority", False)
    if not isinstance(value.get("lesson_refs"), list):
        raise ValueError("machine_growth lesson_refs must be a list")
    if not isinstance(value.get("notes"), list):
        raise ValueError("machine_growth notes must be a list")


def _receipt_id(receipt: dict[str, Any]) -> str:
    row = dict(receipt)
    row["receipt_id"] = ""
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _require(row: dict[str, Any], field: str, expected: Any) -> None:
    if row.get(field) != expected:
        raise ValueError(f"{field} must be {expected!r}")


def _clamp_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 0.0
    return max(0.0, min(1.0, parsed))
