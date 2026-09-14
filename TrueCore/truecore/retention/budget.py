"""Storage budget guard for TrueCore runtime detail data.

TrueCore keeps receipts and evidence references. Heavy native TrueVision or
TrueAudio state belongs to those systems, not to the TrueCore runtime log
budget.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from uuid import uuid4
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from truecore.time import utc_now
from truecore.receipt_store import atomic_json, read_json, record_lock, private_path
from truecore.retention.transaction import execute_details


HEAVY_FOREIGN_SUFFIXES = {
    ".tvcells",
    ".npz",
    ".mp4",
    ".mkv",
    ".wav",
    ".flac",
    ".png",
    ".jpg",
    ".jpeg",
}


@dataclass(frozen=True, slots=True)
class StorageBudgetPolicy:
    max_runtime_bytes: int = 5 * 1024 * 1024 * 1024
    max_receipt_bytes: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.max_runtime_bytes <= 0:
            raise ValueError("max_runtime_bytes must be positive")
        if self.max_receipt_bytes < 4096:
            raise ValueError("max_receipt_bytes must reserve at least 4096 bytes")


class StorageBudgetGuard:
    """Enforce a bounded budget over runtime log/temp/detail roots."""

    def __init__(
        self,
        *,
        policy: StorageBudgetPolicy,
        managed_roots: Iterable[str | Path],
        receipt_root: str | Path,
        protected_roots: Iterable[str | Path] = (),
        eligible_details: list[dict] | None = None,
    ) -> None:
        self.policy = policy
        self.managed_roots = [_resolve(root) for root in managed_roots]
        self.receipt_root = _resolve(receipt_root)
        self.protected_roots = [_resolve(root) for root in protected_roots]
        self.protected_roots.append(self.receipt_root)
        self.eligible_details = {str(private_path(row["path"])): row for row in (eligible_details or [])}
        self.scan_incomplete = False
        self._health_pending = None
        self._health_published_at = 0.0

    def enforce(self) -> dict[str, Any]:
        # Admission pressure includes bookkeeping. Essential evidence is not
        # deleted to make its own budget checker appear healthy.
        receipt_bytes, complete = _receipt_usage(self.receipt_root)
        if not complete or receipt_bytes > self.policy.max_receipt_bytes - 4096:
            state = {"decision": "blocked_receipt_capacity", "receipt_bytes_lower_bound": receipt_bytes,
                     "receipt_scan_complete": complete, "max_receipt_bytes": self.policy.max_receipt_bytes,
                     "deleted_file_count": 0, "created_at_utc": utc_now()}
            atomic_json(self.receipt_root / "budget" / "capacity.json", state, max_bytes=4096)
            return state
        files = self._scan_files()
        if self.scan_incomplete:
            return {"decision": "scan_incomplete", "runtime_bytes_lower_bound": _sum_size(files), "deleted_file_count": 0}
        foreign = [_foreign_flag(row["path"]) for row in files if _is_foreign_heavy_state(row["path"])]
        if foreign:
            receipt = self._write_receipt("violations", "foreign_heavy_state", {"flags": foreign})
            return {
                "decision": "blocked_foreign_heavy_state",
                "max_runtime_bytes": self.policy.max_runtime_bytes,
                "runtime_bytes": _sum_size(files),
                "flags": foreign,
                "violation_receipt_path": str(receipt),
                "deleted_file_count": 0,
            }

        total = _sum_size(files)
        if total <= self.policy.max_runtime_bytes:
            receipt = self._write_receipt(
                "health",
                "budget_health",
                {
                    "runtime_bytes": total,
                    "max_runtime_bytes": self.policy.max_runtime_bytes,
                    "managed_roots": [str(root) for root in self.managed_roots],
                },
            )
            return {
                "decision": "within_budget",
                "max_runtime_bytes": self.policy.max_runtime_bytes,
                "runtime_bytes": total,
                "health_receipt_path": str(receipt) if receipt else None,
                "health_receipt_publication": "published" if receipt else "buffered",
                "deleted_file_count": 0,
            }

        eligible = [row for row in files if row["eligible"]]
        selected = []
        current = total
        for row in sorted(eligible, key=lambda item: (item["mtime"], str(item["path"]))):
            if current <= self.policy.max_runtime_bytes:
                break
            if len(selected) >= 256 or sum(e["identity"]["size"] for e in selected) + row["size"] > 32 * 1024 * 1024:
                break
            selected.append(self.eligible_details[str(row["path"])])
            current -= row["size"]

        skipped_preserved_count = sum(1 for row in files if row["preserved"])
        if selected:
            transaction = execute_details(entries=selected, managed_roots=self.managed_roots,
                protected_roots=self.protected_roots, receipt_root=self.receipt_root,
                context={"kind": "storage_budget", "runtime_bytes_before": total,
                         "max_runtime_bytes": self.policy.max_runtime_bytes})
            current = total - sum(row["size"] for row in transaction["deleted_files"])
            return {
                "decision": "pruned_to_budget" if current <= self.policy.max_runtime_bytes and transaction["status"] == "complete" else "over_budget_partially_pruned",
                "max_runtime_bytes": self.policy.max_runtime_bytes,
                "runtime_bytes_before": total,
                "runtime_bytes_after": current,
                "deletion_receipt_path": transaction.get("receipt_path"),
                "deleted_file_count": transaction["deleted_file_count"],
                "transaction": transaction,
                "skipped_preserved_count": skipped_preserved_count,
            }

        receipt = self._write_receipt(
            "health",
            "budget_overage",
            {
                "runtime_bytes": total,
                "max_runtime_bytes": self.policy.max_runtime_bytes,
                "skipped_preserved_count": skipped_preserved_count,
            },
        )
        return {
            "decision": "over_budget_no_eligible_files",
            "max_runtime_bytes": self.policy.max_runtime_bytes,
            "runtime_bytes": total,
            "health_receipt_path": str(receipt),
            "deleted_file_count": 0,
            "skipped_preserved_count": skipped_preserved_count,
        }

    def _scan_files(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        self.scan_incomplete = False
        started, visited = time.monotonic(), set()
        for root in self.managed_roots:
            if not root.exists():
                continue
            for path in _bounded_paths(root):
                if len(visited) >= 10000 or time.monotonic() - started > 0.25:
                    self.scan_incomplete = True
                    return rows
                if path in visited:
                    continue
                visited.add(path)
                if path.is_symlink() or not path.is_file():
                    continue
                resolved = _resolve(path)
                if resolved.name.endswith(".preserve.json"):
                    continue
                if _is_under_any(resolved, self.protected_roots):
                    continue
                stat = resolved.stat()
                preserved = _is_preserved(resolved)
                rows.append(
                    {
                        "path": resolved,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "preserved": preserved,
                        "eligible": not preserved and str(resolved) in self.eligible_details,
                    }
                )
        return rows

    def _write_receipt(self, folder: str, stem: str, payload: dict[str, Any]) -> Path:
        routine = stem == "budget_health"
        path = self.receipt_root / "budget" / folder / ("current.json" if routine else f"{uuid4().hex}.{stem}.json")
        body = {
            "schema_version": 1,
            "kind": f"truecore_storage_{stem}_receipt",
            "created_at_utc": utc_now(),
            "permanent_receipt": not routine,
            **payload,
        }
        if routine:
            previous = self._health_pending or (read_json(path) if path.exists() else {})
            body["check_count"] = previous.get("check_count", 0) + 1
            body["peak_runtime_bytes"] = max(previous.get("peak_runtime_bytes", 0), payload["runtime_bytes"])
            self._health_pending = body
            if self._health_published_at and time.monotonic() - self._health_published_at < 1.0:
                return None
            return self.flush_health()
        else:
            atomic_json(path, body)
        return path

    def flush_health(self) -> Path | None:
        """Finalize coalesced routine checks; no deletion or full-tree scan."""
        if self._health_pending is None:
            return None
        path = self.receipt_root / "budget" / "health" / "current.json"
        with record_lock(path.with_suffix(".lock")):
            atomic_json(path, self._health_pending)
        self._health_published_at = time.monotonic()
        return path


def _resolve(path: str | Path) -> Path:
    return private_path(path)


def _bounded_paths(root):
    # Stream directory entries rather than materializing a sorted recursive tree.
    stack = [root]
    while stack:
        folder = stack.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                yield Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))


def _receipt_usage(root):
    total, count, started = 0, 0, time.monotonic()
    if not root.exists():
        return 0, True
    for path in _bounded_paths(root):
        count += 1
        if count > 10000 or time.monotonic() - started > 0.25:
            return total, False
        if path.is_symlink():
            return total, False
        if path.is_file():
            total += path.stat().st_size
    return total, True


def _sum_size(rows: list[dict[str, Any]]) -> int:
    return sum(int(row["size"]) for row in rows)


def _is_under_any(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _is_preserved(path: Path) -> bool:
    if path.name.endswith(".preserve.json"):
        return True
    return Path(str(path) + ".preserve.json").exists()


def _is_foreign_heavy_state(path: Path) -> bool:
    return path.suffix.lower() in HEAVY_FOREIGN_SUFFIXES


def _foreign_flag(path: Path) -> dict[str, str]:
    return {
        "path": str(path),
        "reason": "foreign_heavy_state_in_truecore_root",
        "action": "left_in_place",
    }


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_time(value: str) -> str:
    return value.replace(":", "").replace("-", "").replace(".", "").replace("Z", "Z")
