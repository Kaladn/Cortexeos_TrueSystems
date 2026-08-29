"""Record validated worker diagnostic packets to Forge and receipts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from truecore.forge.reader import ForgeReader
from truecore.forge.writer import ForgeWriter
from truecore.worker_feeds.policy import validate_worker_packet
from truecore.worker_feeds.receipts import build_worker_receipt, stable_hash, write_receipt


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
        receipt_path = self.receipts_root / f"{receipt['receipt_id']}.json"
        write_receipt(receipt_path, receipt)
        return {
            "ok": True,
            "packet": packet,
            "forge_metadata": metadata,
            "receipt": receipt,
            "receipt_path": str(receipt_path),
        }
