"""Observer-only handoff contracts for agent-to-agent work.

These packets are not open-ended conversations. They carry bounded work,
facts, evidence, receipts, and an allowed reply shape.
"""

from __future__ import annotations

from typing import Any

from securecore.time import is_canonical_utc_timestamp, utc_now


ALLOWED_REPLY_KINDS = {
    "verification_result",
    "finding_summary",
    "missing_evidence",
    "capability_unavailable",
    "error_report",
}


class AgentHandoffContractError(ValueError):
    """Raised when an agent handoff attempts to exceed its boundary."""


def build_agent_handoff_packet(
    *,
    handoff_id: str,
    task_id: str,
    from_agent: str,
    to_agent: str,
    input_refs: list[str],
    confirmed_facts: list[str],
    open_questions: list[str],
    requested_capability: str,
    receipt_refs: list[str],
    timeout_ms: int,
    allowed_reply_kind: str,
) -> dict[str, Any]:
    packet = {
        "schema_version": 1,
        "kind": "securecore_agent_handoff_packet",
        "created_at_utc": utc_now(),
        "handoff_id": handoff_id,
        "task_id": task_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "input_refs": list(input_refs),
        "confirmed_facts": list(confirmed_facts),
        "open_questions": list(open_questions),
        "requested_capability": requested_capability,
        "receipt_refs": list(receipt_refs),
        "timeout_ms": timeout_ms,
        "allowed_reply_kind": allowed_reply_kind,
        "open_conversation": False,
        "temporal_write_authorized": False,
        "mutation_authorized": False,
        "policy_approval_authority": False,
        "direct_user_alert_authority": False,
    }
    return validate_agent_handoff_packet(packet)


def validate_agent_handoff_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "kind",
        "created_at_utc",
        "handoff_id",
        "task_id",
        "from_agent",
        "to_agent",
        "input_refs",
        "confirmed_facts",
        "open_questions",
        "requested_capability",
        "receipt_refs",
        "timeout_ms",
        "allowed_reply_kind",
        "open_conversation",
        "temporal_write_authorized",
        "mutation_authorized",
        "policy_approval_authority",
        "direct_user_alert_authority",
    }
    _check_required(packet, required, "handoff packet")
    _require(packet, "schema_version", 1)
    _require(packet, "kind", "securecore_agent_handoff_packet")
    _require_false(packet, "open_conversation")
    _require_false(packet, "temporal_write_authorized")
    _require_false(packet, "mutation_authorized")
    _require_false(packet, "policy_approval_authority")
    _require_false(packet, "direct_user_alert_authority")
    _require_canonical_time(packet, "created_at_utc")
    for field in ("handoff_id", "task_id", "from_agent", "to_agent", "requested_capability"):
        _require_nonempty_string(packet, field)
    _require_string_list(packet, "input_refs", allow_empty=False)
    _require_string_list(packet, "confirmed_facts", allow_empty=False)
    _require_string_list(packet, "open_questions", allow_empty=True)
    _require_string_list(packet, "receipt_refs", allow_empty=False)
    if not isinstance(packet["timeout_ms"], int) or packet["timeout_ms"] <= 0:
        raise AgentHandoffContractError("timeout_ms must be a positive integer")
    _require_allowed_reply_kind(packet["allowed_reply_kind"])
    return dict(packet)


def build_agent_handoff_reply(
    *,
    reply_id: str,
    handoff_id: str,
    from_agent: str,
    to_agent: str,
    reply_kind: str,
    facts: list[str],
    evidence_refs: list[str],
    receipt_refs: list[str],
    unresolved_questions: list[str],
) -> dict[str, Any]:
    reply = {
        "schema_version": 1,
        "kind": "securecore_agent_handoff_reply",
        "created_at_utc": utc_now(),
        "reply_id": reply_id,
        "handoff_id": handoff_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "reply_kind": reply_kind,
        "facts": list(facts),
        "evidence_refs": list(evidence_refs),
        "receipt_refs": list(receipt_refs),
        "unresolved_questions": list(unresolved_questions),
        "engine_write_authorized": False,
        "mutation_authorized": False,
        "policy_approval_authority": False,
        "direct_user_alert_authority": False,
    }
    return validate_agent_handoff_reply(reply)


def validate_agent_handoff_reply(
    reply: dict[str, Any],
    handoff_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    required = {
        "schema_version",
        "kind",
        "created_at_utc",
        "reply_id",
        "handoff_id",
        "from_agent",
        "to_agent",
        "reply_kind",
        "facts",
        "evidence_refs",
        "receipt_refs",
        "unresolved_questions",
        "engine_write_authorized",
        "mutation_authorized",
        "policy_approval_authority",
        "direct_user_alert_authority",
    }
    _check_required(reply, required, "handoff reply")
    _require(reply, "schema_version", 1)
    _require(reply, "kind", "securecore_agent_handoff_reply")
    _require_false(reply, "engine_write_authorized")
    _require_false(reply, "mutation_authorized")
    _require_false(reply, "policy_approval_authority")
    _require_false(reply, "direct_user_alert_authority")
    _require_canonical_time(reply, "created_at_utc")
    for field in ("reply_id", "handoff_id", "from_agent", "to_agent"):
        _require_nonempty_string(reply, field)
    _require_allowed_reply_kind(reply["reply_kind"])
    _require_string_list(reply, "facts", allow_empty=True)
    _require_string_list(reply, "evidence_refs", allow_empty=False)
    _require_string_list(reply, "receipt_refs", allow_empty=False)
    _require_string_list(reply, "unresolved_questions", allow_empty=True)
    if handoff_packet is not None:
        validated_packet = validate_agent_handoff_packet(handoff_packet)
        if reply["handoff_id"] != validated_packet["handoff_id"]:
            raise AgentHandoffContractError("reply handoff_id does not match packet")
        if reply["from_agent"] != validated_packet["to_agent"]:
            raise AgentHandoffContractError("reply from_agent must match packet to_agent")
        if reply["to_agent"] != validated_packet["from_agent"]:
            raise AgentHandoffContractError("reply to_agent must match packet from_agent")
        if reply["reply_kind"] != validated_packet["allowed_reply_kind"]:
            raise AgentHandoffContractError("reply_kind does not match allowed_reply_kind")
    return dict(reply)


def _check_required(row: dict[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required.difference(row))
    if missing:
        raise AgentHandoffContractError(f"{label} missing fields: {missing}")


def _require(row: dict[str, Any], field: str, expected: Any) -> None:
    if row.get(field) != expected:
        raise AgentHandoffContractError(f"{field} must be {expected!r}")


def _require_false(row: dict[str, Any], field: str) -> None:
    _require(row, field, False)


def _require_nonempty_string(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), str) or not row[field].strip():
        raise AgentHandoffContractError(f"{field} must be a non-empty string")


def _require_string_list(row: dict[str, Any], field: str, *, allow_empty: bool) -> None:
    values = row.get(field)
    if not isinstance(values, list):
        raise AgentHandoffContractError(f"{field} must be a list")
    if not allow_empty and not values:
        raise AgentHandoffContractError(f"{field} must not be empty")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise AgentHandoffContractError(f"{field} must contain only non-empty strings")


def _require_canonical_time(row: dict[str, Any], field: str) -> None:
    if not is_canonical_utc_timestamp(str(row.get(field, ""))):
        raise AgentHandoffContractError(f"{field} must be canonical UTC")


def _require_allowed_reply_kind(value: Any) -> None:
    if value not in ALLOWED_REPLY_KINDS:
        raise AgentHandoffContractError(f"reply kind not allowed: {value!r}")
