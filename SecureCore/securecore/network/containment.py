"""Trap-log-release containment plans.

Reaper/containment code must plan reversible forensic capture before any live
host action. This module does not mutate firewall, process, registry, service,
task, or network state.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
from typing import Any

from securecore.time import utc_now


MIN_TRAP_TTL_SECONDS = 1
MAX_TRAP_TTL_SECONDS = 3600


class ContainmentContractError(ValueError):
    """Raised when a trap-log-release plan violates the containment contract."""


def build_trap_log_release_plan(
    *,
    remote_ip: str,
    observed_event_refs: list[str],
    ttl_seconds: int = 300,
    protocol: str = "unknown",
    remote_ports: list[int] | None = None,
    local_endpoint: str = "",
    actor_process: str = "",
    reason: str = "observed network event requires bounded forensic capture",
) -> dict[str, Any]:
    """Build a reversible containment plan without executing the plan."""

    normalized_ip = _normalize_ip(remote_ip)
    _require_string_list("observed_event_refs", observed_event_refs)
    if not isinstance(ttl_seconds, int) or not MIN_TRAP_TTL_SECONDS <= ttl_seconds <= MAX_TRAP_TTL_SECONDS:
        raise ContainmentContractError(
            f"ttl_seconds must be between {MIN_TRAP_TTL_SECONDS} and {MAX_TRAP_TTL_SECONDS}"
        )
    ports = list(remote_ports or [])
    if not all(isinstance(port, int) and 0 < port <= 65535 for port in ports):
        raise ContainmentContractError("remote_ports must contain valid TCP/UDP port numbers")
    if not isinstance(protocol, str) or not protocol.strip():
        raise ContainmentContractError("protocol must be a non-empty string")
    if not isinstance(local_endpoint, str):
        raise ContainmentContractError("local_endpoint must be a string")
    if not isinstance(actor_process, str):
        raise ContainmentContractError("actor_process must be a string")
    if not isinstance(reason, str) or not reason.strip():
        raise ContainmentContractError("reason must be a non-empty string")

    payload = {
        "schema_version": 1,
        "kind": "securecore_trap_log_release_plan",
        "created_at_utc": utc_now(),
        "remote_ip": normalized_ip,
        "protocol": protocol.strip().lower(),
        "remote_ports": ports,
        "local_endpoint": local_endpoint,
        "actor_process": actor_process,
        "reason": reason,
        "ttl_seconds": ttl_seconds,
        "trap_required": True,
        "log_required": True,
        "release_required": True,
        "rollback_required": True,
        "permanent_action_authorized": False,
        "live_firewall_mutation_authorized": False,
        "approval_required_for_live_action": True,
        "required_receipts": [
            "trap_receipt",
            "evidence_hash_receipt",
            "release_receipt",
            "central_writer_report_receipt",
        ],
        "planned_steps": [
            "record_source_event_refs",
            "record_endpoint_trace_metadata",
            "write_evidence_hash_receipt",
            "expire_or_release_trap",
            "write_release_receipt",
            "request_central_writer_legal_ip_trace_report",
        ],
        "evidence_refs": list(observed_event_refs),
    }
    payload["plan_hash"] = _hash(payload)
    return payload


def _normalize_ip(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise ContainmentContractError("remote_ip must be a valid IPv4 or IPv6 address") from exc


def _require_string_list(name: str, values: list[str]) -> None:
    if not isinstance(values, list) or not values:
        raise ContainmentContractError(f"{name} must contain evidence refs")
    if not all(isinstance(item, str) and item.strip() for item in values):
        raise ContainmentContractError(f"{name} must contain only non-empty strings")


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
