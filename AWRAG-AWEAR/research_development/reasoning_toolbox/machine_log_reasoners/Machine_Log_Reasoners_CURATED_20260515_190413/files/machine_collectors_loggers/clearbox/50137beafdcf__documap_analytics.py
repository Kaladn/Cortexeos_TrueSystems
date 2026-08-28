"""DocuMap analytics and ledger service."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from bridges.helpers import _append_documap_event, _read_documap_ledger
from bridges.state import LOGGER


class DocuMapAnalyticsService:
    """Owns stats/ledger queries and event writes for DocuMap."""

    def __init__(
        self,
        *,
        state: Any,
        version: str,
        chunks_dir: Path,
        index_dir: Path,
    ) -> None:
        self.state = state
        self.version = version
        self._chunks_dir = chunks_dir
        self._index_dir = index_dir

    async def stats(self) -> dict[str, Any]:
        ledger = _read_documap_ledger()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ledger_counts = {"queued": 0, "started": 0, "completed": 0, "failed": 0}
        mapped_today = 0
        for _fp, evt in ledger.items():
            status = evt.get("event", "")
            if status in ledger_counts:
                ledger_counts[status] += 1
            if status == "completed" and evt.get("ts", "")[:10] == today_str:
                mapped_today += 1

        grove_doc_count = 0
        try:
            if self._chunks_dir.exists():
                grove_doc_count = sum(
                    1
                    for d in self._chunks_dir.iterdir()
                    if d.is_dir() and (d / "chunks.jsonl").exists()
                )
        except Exception as exc:
            LOGGER.warning("Could not count grove receipts: %s", exc)

        grove_anchors = 0
        try:
            stats_path = self._index_dir / "anchor_stats.json"
            if stats_path.exists():
                with open(stats_path, "r", encoding="utf-8") as f:
                    anchor_data = json.load(f)
                grove_anchors = anchor_data.get("unique_anchors", 0)
        except Exception as exc:
            LOGGER.warning("Could not read anchor stats: %s", exc)

        sys_verified = self.state.bridge.slots_assigned if self.state.bridge.loaded else 0
        return {
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "uploads_queued": ledger_counts["queued"],
            "uploads_processing": ledger_counts["started"],
            "uploads_failed": ledger_counts["failed"],
            "docs_mapped_total": grove_doc_count,
            "mapped_today": mapped_today,
            "anchors_total_grove": grove_anchors,
            "anchors_sys_verified": sys_verified,
            "grove_label": "Data Lake",
            "documap_label": "DocuMap",
            "version": self.version,
        }

    def check_fingerprint(self, fingerprint: str) -> dict[str, Any]:
        ledger = _read_documap_ledger()
        evt = ledger.get(fingerprint)
        if not evt:
            return {"exists": False}
        return {"exists": True, "event": evt.get("event"), "fingerprint": fingerprint}

    def record_job_event(self, body: dict[str, Any]) -> dict[str, Any]:
        event = body.get("event")
        fingerprint = body.get("fingerprint")
        if not event or not fingerprint:
            raise HTTPException(400, "Missing event or fingerprint")
        body["ts"] = datetime.now(timezone.utc).isoformat()
        _append_documap_event(body)
        return {"ok": True}
