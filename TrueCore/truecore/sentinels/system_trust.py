"""System trust sentinel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from truecore.internal_watch import InternalSelfLogger
from truecore.sentinels.contracts import build_sentinel_result


def run(input_payload: dict[str, Any]) -> dict[str, Any]:
    receipt = InternalSelfLogger(input_payload["receipt_root"]).write_trust_receipt(
        host_id=str(input_payload.get("host_id", "local")),
        checks=[dict(item) for item in input_payload.get("checks", [])],
    )
    path = str(receipt["receipt_path"])
    status = "ok" if receipt["status"] == "green" else "alert"
    return build_sentinel_result(
        sentinel_id="system_trust_sentinel",
        status=status,
        facts=[f"system trust is {receipt['status']}"],
        evidence_refs=[f"internal_watch://{Path(path).name}"],
        warnings=receipt["reasons"],
        artifacts=[{"kind": "system_trust_receipt", "path": path}],
    )
