"""Read-only health watchers for TrueCore backend state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from truecore.time import utc_now


class HealthWatcher(Protocol):
    name: str

    def check(self) -> dict[str, Any]:
        """Return a health row. Must not mutate runtime state."""


@dataclass(slots=True)
class ForgeWatcher:
    root: Path
    expected_streams: list[str]
    name: str = "forge"

    def check(self) -> dict[str, Any]:
        missing = []
        streams = {}
        for stream in self.expected_streams:
            records = self.root / stream / "records.bin"
            index = self.root / stream / "records.index.jsonl"
            exists = records.exists()
            streams[stream] = {
                "records_exists": exists,
                "index_exists": index.exists(),
                "bytes": records.stat().st_size if exists else 0,
            }
            if not exists:
                missing.append(stream)
        return _row(
            self.name,
            "ok" if not missing else "alert",
            "forge streams present" if not missing else "missing forge streams",
            {"missing_streams": missing, "streams": streams},
        )


@dataclass(slots=True)
class FusionWatcher:
    root: Path
    name: str = "fusion"

    def check(self) -> dict[str, Any]:
        blocks = self.root / "fusion_blocks.scfb"
        index = self.root / "fusion_blocks.index.jsonl"
        exists = blocks.exists()
        return _row(
            self.name,
            "ok" if exists else "alert",
            "fusion block file present" if exists else "fusion block file missing",
            {
                "blocks_exists": exists,
                "index_exists": index.exists(),
                "bytes": blocks.stat().st_size if exists else 0,
            },
        )


@dataclass(slots=True)
class WorkerHealthWatcher:
    workers: dict[str, dict[str, Any]]
    name: str = "worker_health"

    def check(self) -> dict[str, Any]:
        stale = []
        for worker, row in self.workers.items():
            last_seen = float(row.get("last_seen_seconds", 0.0) or 0.0)
            timeout = float(row.get("timeout_seconds", 0.0) or 0.0)
            if timeout > 0 and last_seen > timeout:
                stale.append(worker)
        return _row(
            self.name,
            "ok" if not stale else "alert",
            "worker heartbeats within limits" if not stale else "worker heartbeat timeout",
            {"stale_workers": stale, "worker_count": len(self.workers)},
        )


@dataclass(slots=True)
class QueuePressureWatcher:
    queues: dict[str, dict[str, Any]]
    name: str = "queue_pressure"

    def check(self) -> dict[str, Any]:
        pressured = []
        for queue, row in self.queues.items():
            depth = int(row.get("depth", 0) or 0)
            max_depth = int(row.get("max_depth", 0) or 0)
            if max_depth > 0 and depth > max_depth:
                pressured.append(queue)
        return _row(
            self.name,
            "ok" if not pressured else "alert",
            "queue pressure within limits" if not pressured else "queue pressure exceeded",
            {"pressured_queues": pressured, "queue_count": len(self.queues)},
        )


@dataclass(slots=True)
class RetentionWatcher:
    receipt_root: Path
    name: str = "retention"

    def check(self) -> dict[str, Any]:
        health_root = self.receipt_root / "health"
        forensic_root = self.receipt_root / "forensic"
        health_count = len(list(health_root.glob("*.health.json"))) if health_root.exists() else 0
        forensic_count = len(list(forensic_root.glob("*.forensic.json"))) if forensic_root.exists() else 0
        return _row(
            self.name,
            "ok" if health_count or forensic_count else "alert",
            "retention receipts present" if health_count or forensic_count else "no retention receipts found",
            {"health_receipts": health_count, "forensic_manifests": forensic_count},
        )


def run_health_watchers(*, watchers: list[HealthWatcher], receipt_path: str | Path) -> dict[str, Any]:
    checks = [watcher.check() for watcher in watchers]
    anomaly_count = sum(1 for check in checks if check.get("status") != "ok")
    receipt = {
        "schema_version": 1,
        "kind": "truecore_watcher_health_receipt",
        "created_at_utc": utc_now(),
        "status": "ok" if anomaly_count == 0 else "alert",
        "watcher_count": len(checks),
        "anomaly_count": anomaly_count,
        "checks": checks,
        "recovery_action_taken": False,
    }
    path = Path(receipt_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    receipt["receipt_path"] = str(path)
    return receipt


def _row(name: str, status: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "watcher": name,
        "status": status,
        "message": message,
        "details": details,
    }
