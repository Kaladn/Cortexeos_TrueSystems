"""Validation policy for worker diagnostic feed packets.

Worker feeds are operational diagnostics. They may describe worker state,
resource cost, queues, hashes, and receipts. They must not carry user content,
desktop replay, raw network payloads, secrets, or security enforcement commands.
"""

from __future__ import annotations

from typing import Any

from truecore.time import is_canonical_utc_timestamp


WORKER_STATES = {"idle", "running", "blocked", "failed", "complete"}
FORBIDDEN_KEYS = {
    "keystrokes",
    "keys",
    "password",
    "passwords",
    "token",
    "tokens",
    "secret",
    "secrets",
    "screen",
    "screenshot",
    "frame",
    "raw_frame",
    "desktop_replay",
    "browser_history",
    "document_text",
    "chat_content",
    "network_payload",
    "packet_body",
    "firewall_action",
    "execute",
    "command",
}


class WorkerFeedValidationError(ValueError):
    """Raised when a worker diagnostic packet violates feed policy."""


def validate_worker_packet(packet: dict[str, Any]) -> None:
    required = [
        "schema_version",
        "worker_id",
        "worker_type",
        "job_id",
        "timestamp",
        "state",
        "task_name",
        "progress",
        "cpu",
        "ram",
        "gpu",
        "queue_depth",
        "input_hash",
        "output_hash",
        "receipt_id",
        "error_code",
        "error_summary",
    ]
    for key in required:
        if key not in packet:
            raise WorkerFeedValidationError(f"missing field: {key}")
    if packet["schema_version"] != 1:
        raise WorkerFeedValidationError("schema_version must be 1")
    if not is_canonical_utc_timestamp(str(packet["timestamp"])):
        raise WorkerFeedValidationError("timestamp must use canonical UTC format")
    if packet["state"] not in WORKER_STATES:
        raise WorkerFeedValidationError(f"unknown worker state: {packet['state']}")
    if not 0 <= float(packet["progress"]) <= 1:
        raise WorkerFeedValidationError("progress must be between 0 and 1")
    if int(packet["queue_depth"]) < 0:
        raise WorkerFeedValidationError("queue_depth must be non-negative")
    _reject_forbidden(packet)


def _reject_forbidden(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_KEYS:
                raise WorkerFeedValidationError(f"forbidden diagnostic field: {path}{key}")
            _reject_forbidden(child, f"{path}{key}.")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden(child, f"{path}{index}.")
