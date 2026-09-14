"""Rolling retention with forensic promotion.

Normal time becomes receipts. Suspicious time becomes evidence. Everything
else expires.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from truecore.time import is_canonical_utc_timestamp, utc_now
from truecore.receipt_store import atomic_json
from truecore.retention.transaction import execute_details


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    raw_retention_hours: int = 2
    sweep_interval_minutes: int = 60
    leadup_minutes: int = 30
    lookahead_minutes: int = 15


@dataclass(frozen=True, slots=True)
class RetentionWindow:
    start_utc: str
    end_utc: str

    def __post_init__(self) -> None:
        if not is_canonical_utc_timestamp(self.start_utc):
            raise ValueError("start_utc must use canonical UTC format")
        if not is_canonical_utc_timestamp(self.end_utc):
            raise ValueError("end_utc must use canonical UTC format")
        if _parse_utc(self.end_utc) <= _parse_utc(self.start_utc):
            raise ValueError("end_utc must be after start_utc")

    @classmethod
    def ending_at(cls, end_utc: str, *, hours: int = 2) -> "RetentionWindow":
        end = _parse_utc(end_utc)
        start = end - timedelta(hours=hours)
        return cls(start_utc=_format_utc(start), end_utc=_format_utc(end))

    @property
    def label(self) -> str:
        return f"{_file_time(self.start_utc)}__{_file_time(self.end_utc)}"


class RollingRetentionManager:
    """Close rolling windows by receipt or forensic preservation."""

    def __init__(
        self,
        *,
        policy: RetentionPolicy,
        fusion_store,
        managed_roots: Iterable[str | Path],
        receipt_root: str | Path,
        eligible_details: list[dict] | None = None,
        protected_roots: Iterable[str | Path] = (),
    ):
        self.policy = policy
        self.fusion_store = fusion_store
        self.managed_roots = [Path(root) for root in managed_roots]
        self.receipt_root = Path(receipt_root)
        self.eligible_details = list(eligible_details or [])
        self.protected_roots = list(protected_roots)

    def close_window(self, window: RetentionWindow, *, transaction_id: str | None = None) -> dict[str, Any]:
        verify = self.fusion_store.verify()
        if not verify.get("intact"):
            return {
                "decision": "blocked_verification_failed",
                "window": _window_dict(window),
                "error": str(verify.get("error", "fusion verification failed")),
                "deleted_file_count": 0,
            }

        blocks = [block for block in self.fusion_store.iter_blocks() or [] if _block_in_window(block, window)]
        summary = _summarize_blocks(blocks)
        if summary["anomaly_count"] > 0:
            manifest = self._write_forensic_manifest(window, summary, verify)
            return {
                "decision": "preserved_anomaly_window",
                "window": _window_dict(window),
                "forensic_manifest_path": str(manifest),
                "deleted_file_count": 0,
                **summary,
            }

        eligible = [entry for entry in self.eligible_details
                    if _parse_utc(window.start_utc) <= _parse_utc(entry["recorded_at_utc"]) < _parse_utc(window.end_utc)]
        result = execute_details(entries=eligible, managed_roots=self.managed_roots,
                                 protected_roots=self.protected_roots, receipt_root=self.receipt_root,
                                 transaction_id=transaction_id or window.label,
                                 context={"window": _window_dict(window), "fusion_verify": verify, **summary})
        return {
            "schema": "truecore.retention_window_result@2",
            "decision": ("deleted_clean_window" if eligible else "no_eligible_details") if result["status"] == "complete" else "partial_retention",
            "window": _window_dict(window),
            "job_receipt_path": result.get("receipt_path"),
            "deleted_file_count": result["deleted_file_count"],
            "transaction": result,
            **summary,
        }

    def _write_health_receipt(self, window: RetentionWindow, summary: dict, verify: dict) -> Path:
        path = self.receipt_root / "health" / f"{window.label}.health.json"
        payload = {
            "schema_version": 1,
            "kind": "truecore_retention_health_receipt",
            "created_at_utc": utc_now(),
            "window": _window_dict(window),
            "fusion_verify": verify,
            "permanent_receipt": True,
            **summary,
        }
        _write_json(path, payload)
        return path

    def _write_deletion_receipt(self, window: RetentionWindow, deleted: list[dict], health_receipt: Path) -> Path:
        path = self.receipt_root / "deletions" / f"{window.label}.deletion.json"
        payload = {
            "schema_version": 1,
            "kind": "truecore_retention_deletion_receipt",
            "created_at_utc": utc_now(),
            "window": _window_dict(window),
            "health_receipt_path": str(health_receipt),
            "deleted_file_count": len(deleted),
            "deleted_files": deleted,
            "backed_up": False,
            "zipped": False,
            "deletion_mode": "permanent_unlinked_files",
        }
        _write_json(path, payload)
        return path

    def _write_forensic_manifest(self, window: RetentionWindow, summary: dict, verify: dict) -> Path:
        path = self.receipt_root / "forensic" / f"{window.label}.forensic.json"
        payload = {
            "schema_version": 1,
            "kind": "truecore_forensic_preservation_manifest",
            "created_at_utc": utc_now(),
            "window": _window_dict(window),
            "preservation_reason": "anomaly_detected",
            "leadup_minutes": self.policy.leadup_minutes,
            "lookahead_minutes": self.policy.lookahead_minutes,
            "fusion_verify": verify,
            "managed_roots_preserved": [str(root) for root in self.managed_roots],
            **summary,
        }
        _write_json(path, payload)
        return path

def _summarize_blocks(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts: dict[str, int] = {}
    anomaly_count = 0
    highest_risk_score = 0.0
    block_hashes = []
    for block in blocks:
        block_hashes.append(block.get("block_hash", ""))
        flags = int(block.get("anomaly_flags", 0) or 0)
        if flags:
            anomaly_count += 1
            highest_risk_score = max(highest_risk_score, 1.0)
        for source, count in (block.get("source_counts") or {}).items():
            source_counts[source] = source_counts.get(source, 0) + int(count)
    return {
        "source_counts": source_counts,
        "fusion_block_count": len(blocks),
        "anomaly_count": anomaly_count,
        "highest_risk_score": highest_risk_score,
        "fusion_block_hashes": block_hashes,
        "summary_hash": hashlib.sha256(
            json.dumps(
                {
                    "source_counts": source_counts,
                    "fusion_block_hashes": block_hashes,
                    "anomaly_count": anomaly_count,
                    "highest_risk_score": highest_risk_score,
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
    }


def _block_in_window(block: dict[str, Any], window: RetentionWindow) -> bool:
    start = _parse_utc(window.start_utc)
    end = _parse_utc(window.end_utc)
    value = block.get("window_start_utc") or block.get("bucket_start_utc")
    if not isinstance(value, str) or not is_canonical_utc_timestamp(value):
        return False
    observed = _parse_utc(value)
    return start <= observed < end


def _delete_empty_dirs(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_json(path, payload)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _window_dict(window: RetentionWindow) -> dict[str, str]:
    return {"start_utc": window.start_utc, "end_utc": window.end_utc}


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _file_time(value: str) -> str:
    return value.replace(":", "").replace("-", "").replace(".", "").replace("Z", "Z")
