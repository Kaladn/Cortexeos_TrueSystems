"""
Wolf Engine — ZMQ Serialization Protocol

All inter-service communication uses JSON over ZMQ REQ/REP.

Request:  {"action": "ingest"|"query"|"stats"|"health"|..., "payload": {...}}
Response: {"status": "ok"|"error", "data": {...}}

Contracts are serialized/deserialized through dataclass ↔ dict helpers.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from wolf_engine.contracts import ForgeStats, QueryResult, RawAnchor, SymbolEvent

# --- Serialization helpers ---


def encode_request(action: str, payload: dict[str, Any] | None = None) -> bytes:
    """Encode a request as JSON bytes for ZMQ send."""
    msg = {"action": action, "payload": payload or {}}
    return json.dumps(msg).encode("utf-8")


def decode_request(data: bytes) -> tuple[str, dict[str, Any]]:
    """Decode a ZMQ message into (action, payload)."""
    msg = json.loads(data.decode("utf-8"))
    return msg["action"], msg.get("payload", {})


def encode_response(status: str, data: Any = None) -> bytes:
    """Encode a response as JSON bytes for ZMQ send."""
    msg = {"status": status, "data": data}
    return json.dumps(msg, default=str).encode("utf-8")


def decode_response(data: bytes) -> tuple[str, Any]:
    """Decode a ZMQ response into (status, data)."""
    msg = json.loads(data.decode("utf-8"))
    return msg["status"], msg.get("data")


# --- Contract serialization ---


def raw_anchor_to_dict(anchor: RawAnchor) -> dict[str, Any]:
    """Serialize RawAnchor to dict for JSON transport."""
    return asdict(anchor)


def dict_to_raw_anchor(d: dict[str, Any]) -> RawAnchor:
    """Deserialize dict to RawAnchor."""
    return RawAnchor(**d)


def symbol_event_to_dict(event: SymbolEvent) -> dict[str, Any]:
    """Serialize SymbolEvent to dict for JSON transport."""
    return asdict(event)


def dict_to_symbol_event(d: dict[str, Any]) -> SymbolEvent:
    """Deserialize dict to SymbolEvent."""
    return SymbolEvent(**d)


def forge_stats_to_dict(stats: ForgeStats) -> dict[str, Any]:
    """Serialize ForgeStats to dict."""
    return asdict(stats)


def query_result_to_dict(result: QueryResult) -> dict[str, Any]:
    """Serialize QueryResult to dict (handles nested SymbolEvent)."""
    d = asdict(result)
    return d
