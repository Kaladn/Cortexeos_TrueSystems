"""Communicast contracts for small system-to-system handoffs.

Communicast is not a god bridge. It carries shaped receipts between systems.
AnchorWorks remains the user-facing system; SecureCore supplies support,
logging, policy, and agent/toolbox findings.
"""

from __future__ import annotations

from typing import Any

from securecore.time import is_canonical_utc_timestamp, utc_now


SYSTEMS = {"anchorworks", "securecore", "operator"}
TOPICS = {
    "anchorworks.task.request",
    "anchorworks.face.rendered",
    "securecore.agent.finding",
    "securecore.health",
    "securecore.security.event",
    "securecore.toolbox.capability",
    "securecore.toolbox.result",
}
AUTHORITIES = {
    "aw_face",
    "aw_task_conductor",
    "securecore_support",
    "securecore_policy",
    "securecore_logging",
}


class CommunicastContractError(ValueError):
    """Raised when a Communicast message violates AW/SC authority boundaries."""


def build_communicast_message(
    *,
    message_id: str,
    source_system: str,
    source_component: str,
    target_system: str,
    topic: str,
    authority: str,
    payload_schema: str,
    payload: dict[str, Any],
    evidence_refs: list[str],
    trace_refs: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "communicast_message",
        "message_id": message_id,
        "created_at_utc": utc_now(),
        "source_system": source_system,
        "source_component": source_component,
        "target_system": target_system,
        "topic": topic,
        "authority": authority,
        "payload_schema": payload_schema,
        "payload": payload,
        "evidence_refs": evidence_refs,
        "trace_refs": trace_refs,
        "user_facing": topic == "anchorworks.face.rendered",
    }


def validate_communicast_message(message: dict[str, Any]) -> dict[str, Any]:
    _require(message, "schema_version", 1)
    _require(message, "kind", "communicast_message")
    for field in ("message_id", "created_at_utc", "source_component", "payload_schema"):
        _require_nonempty_string(message, field)
    if not is_canonical_utc_timestamp(message["created_at_utc"]):
        raise CommunicastContractError("created_at_utc must use canonical UTC timestamp format")
    if message.get("source_system") not in SYSTEMS:
        raise CommunicastContractError(f"invalid source_system: {message.get('source_system')}")
    if message.get("target_system") not in SYSTEMS:
        raise CommunicastContractError(f"invalid target_system: {message.get('target_system')}")
    if message.get("topic") not in TOPICS:
        raise CommunicastContractError(f"invalid topic: {message.get('topic')}")
    if message.get("authority") not in AUTHORITIES:
        raise CommunicastContractError(f"invalid authority: {message.get('authority')}")
    if not isinstance(message.get("payload"), dict):
        raise CommunicastContractError("payload must be an object")
    _require_string_list(message, "evidence_refs")
    _require_string_list(message, "trace_refs")
    _validate_authority_boundary(message)
    return dict(message)


def _validate_authority_boundary(message: dict[str, Any]) -> None:
    topic = message["topic"]
    source = message["source_system"]
    authority = message["authority"]
    if topic == "anchorworks.face.rendered":
        if source != "anchorworks" or authority != "aw_face":
            raise CommunicastContractError("only AnchorWorks may publish user-facing speech")
        if message.get("user_facing") is not True:
            raise CommunicastContractError("AnchorWorks face messages must be marked user_facing")
        return
    if source == "securecore" and authority == "aw_face":
        raise CommunicastContractError("SecureCore cannot claim AnchorWorks face authority")
    if source == "securecore" and message.get("user_facing") is True:
        raise CommunicastContractError("SecureCore support messages cannot be user-facing")
    if topic.startswith("securecore.") and source != "securecore":
        raise CommunicastContractError("securecore topics must originate from SecureCore")


def _require(row: dict[str, Any], field: str, expected: Any) -> None:
    if row.get(field) != expected:
        raise CommunicastContractError(f"{field} must be {expected!r}")


def _require_nonempty_string(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), str) or not row[field].strip():
        raise CommunicastContractError(f"{field} must be a non-empty string")


def _require_string_list(row: dict[str, Any], field: str) -> None:
    values = row.get(field)
    if not isinstance(values, list) or not values:
        raise CommunicastContractError(f"{field} must be a non-empty list")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise CommunicastContractError(f"{field} must contain only non-empty strings")
