"""Deterministic causality chain receipts for captured TrueCore events."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from truecore.time import is_canonical_utc_timestamp, utc_now


CONFIDENCE_VALUES = {"observed", "derived", "gap"}


class CausalityError(ValueError):
    """Raised when a causality chain cannot be proven from captured events."""


def build_causality_chain(
    *,
    chain_id: str,
    trigger_event_id: str,
    fusion_block_id: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a replayable causality receipt from already captured events."""

    if not chain_id or not trigger_event_id or not fusion_block_id:
        raise CausalityError("chain_id, trigger_event_id, and fusion_block_id are required")
    if not events:
        raise CausalityError("events are required")

    event_ids: set[str] = set()
    previous_sequence: int | None = None
    unresolved_gaps: list[dict[str, str]] = []
    compact_events: list[dict[str, Any]] = []

    for event in events:
        event_id = _require_str(event, "event_id")
        observed_at = _require_str(event, "observed_at_utc")
        if not is_canonical_utc_timestamp(observed_at):
            raise CausalityError(f"event {event_id} timestamp is not canonical UTC")
        sequence = event.get("sequence")
        if not isinstance(sequence, int):
            raise CausalityError(f"event {event_id} sequence must be an integer")
        if previous_sequence is not None and sequence <= previous_sequence:
            raise CausalityError("event sequences must be strictly monotonic")
        previous_sequence = sequence
        cursor = event.get("cursor")
        if not isinstance(cursor, dict):
            raise CausalityError(f"event {event_id} cursor must be an object")
        payload_hash = _require_str(event, "payload_hash")
        previous_event_hash = _require_str(event, "previous_event_hash")
        confidence = str(event.get("confidence", "observed"))
        if confidence not in CONFIDENCE_VALUES:
            raise CausalityError(f"event {event_id} confidence is invalid")
        event_ids.add(event_id)
        compact_events.append(
            {
                "event_id": event_id,
                "observed_at_utc": observed_at,
                "sequence": sequence,
                "cursor": cursor,
                "payload_hash": payload_hash,
                "previous_event_hash": previous_event_hash,
                "confidence": confidence,
            }
        )

    for event in events:
        event_id = str(event["event_id"])
        for ref in list(event.get("parent_event_refs", []) or []) + list(event.get("related_event_refs", []) or []):
            if ref not in event_ids:
                unresolved_gaps.append({"missing_event_ref": str(ref), "referenced_by": event_id})

    if trigger_event_id not in event_ids:
        unresolved_gaps.append({"missing_event_ref": trigger_event_id, "referenced_by": "trigger"})

    confidence = "gap" if unresolved_gaps else "observed"
    chain = {
        "schema_version": 1,
        "kind": "truecore_causality_chain",
        "created_at_utc": utc_now(),
        "chain_id": chain_id,
        "trigger_event_id": trigger_event_id,
        "fusion_block_id": fusion_block_id,
        "event_refs": [event["event_id"] for event in compact_events],
        "events": compact_events,
        "sequence_range": {
            "first": compact_events[0]["sequence"],
            "last": compact_events[-1]["sequence"],
        },
        "unresolved_gaps": unresolved_gaps,
        "confidence": confidence,
    }
    chain["chain_hash"] = _hash(chain)
    return chain


def _require_str(event: dict[str, Any], key: str) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CausalityError(f"event missing required string field: {key}")
    return value


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
