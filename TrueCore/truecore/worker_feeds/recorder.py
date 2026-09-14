"""Record validated worker diagnostic packets to Forge and receipts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from truecore.forge.reader import ForgeReader
from truecore.forge.writer import ForgeWriter
from truecore.worker_feeds.policy import validate_worker_packet
from truecore.worker_feeds.receipts import build_worker_receipt, stable_hash


class WorkerDiagnosticRecorder:
    """Append worker diagnostics on explicit call only."""

    def __init__(self, runtime_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root)
        self.forge_root = self.runtime_root / "forge" / "worker_diagnostics"
        self.receipts_root = self.runtime_root / "receipts" / "worker_feeds"

    def record(self, packet: dict[str, Any]) -> dict[str, Any]:
        validate_worker_packet(packet)
        reader = ForgeReader(self.forge_root)
        last = reader.last_record()
        sequence = (last.sequence + 1) if last else 0
        previous_hash = last.chain_hash if last else "GENESIS"
        chain_hash = stable_hash(packet)
        record = {
            "record_id": f"{packet['worker_id']}:{packet['job_id']}:{sequence}",
            "substrate": "worker_diagnostics",
            "sequence": sequence,
            "timestamp": packet["timestamp"],
            "cell_id": packet["worker_id"],
            "record_type": "worker_diagnostic_packet",
            "payload": {
                "packet": packet,
                "diagnostic_only": True,
                "security_action_authorized": False,
            },
            "previous_hash": previous_hash,
            "chain_hash": chain_hash,
        }
        metadata = ForgeWriter(self.forge_root).append_dict(record)
        receipt = build_worker_receipt(packet=packet, forge_metadata=metadata)
        return {
            "schema": "truecore.worker_diagnostic_result@2",
            "ok": True,
            "packet": packet,
            "forge_metadata": metadata,
            "receipt": receipt,
            "receipt_ref": {
                "kind": "forge_record", "substrate": "worker_diagnostics",
                "record_id": metadata["record_id"], "sequence": metadata["sequence"],
                "packet_sha256": chain_hash,
            },
        }

    def resolve_receipt(self, reference: dict[str, Any]) -> dict[str, Any]:
        """Resolve proof from its existing native record without a sidecar."""
        for record in ForgeReader(self.forge_root).iter_records():
            if record.record_id == reference.get("record_id") and record.sequence == reference.get("sequence"):
                packet = record.payload["packet"]
                if stable_hash(packet) != reference.get("packet_sha256"):
                    raise ValueError("diagnostic commitment mismatch")
                return packet
        raise ValueError("diagnostic record is unavailable")
