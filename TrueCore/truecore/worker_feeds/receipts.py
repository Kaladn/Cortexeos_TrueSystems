"""Receipt helpers for worker diagnostic feeds."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from truecore.time import utc_now


def stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build_worker_receipt(
    *,
    packet: dict[str, Any],
    forge_metadata: dict[str, Any],
    receipt_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "worker_diagnostic_receipt",
        "receipt_id": receipt_id or f"worker_receipt_{uuid4().hex[:12]}",
        "created_at_utc": utc_now(),
        "worker_id": packet["worker_id"],
        "worker_type": packet["worker_type"],
        "job_id": packet["job_id"],
        "state": packet["state"],
        "packet_hash": stable_hash(packet),
        "forge_record_id": forge_metadata.get("record_id", ""),
        "forge_sequence": forge_metadata.get("sequence", -1),
        "forge_substrate": forge_metadata.get("substrate", "worker_diagnostics"),
        "raw_user_content_stored": False,
        "security_action_authorized": False,
    }


def write_receipt(path: str | Path, receipt: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
