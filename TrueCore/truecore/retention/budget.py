"""Storage budget guard for TrueCore runtime detail data.

TrueCore keeps receipts and evidence references. Heavy native TrueVision or
TrueAudio state belongs to those systems, not to the TrueCore runtime log
budget.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from truecore.time import utc_now


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

    def __post_init__(self) -> None:
        if self.max_runtime_bytes <= 0:
            raise ValueError("max_runtime_bytes must be positive")


class StorageBudgetGuard:
    """Enforce a bounded budget over runtime log/temp/detail roots."""

    def __init__(
        self,
        *,
        policy: StorageBudgetPolicy,
        managed_roots: Iterable[str | Path],
        receipt_root: str | Path,
        protected_roots: Iterable[str | Path] = (),
    ) -> None:
        self.policy = policy
        self.managed_roots = [_resolve(root) for root in managed_roots]
        self.receipt_root = _resolve(receipt_root)
        self.protected_roots = [_resolve(root) for root in protected_roots]
        self.protected_roots.append(self.receipt_root)

    def enforce(self) -> dict[str, Any]:
        files = self._scan_files()
        foreign = [_foreign_flag(row) for row in files if _is_foreign_heavy_state(row["path"])]
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
                "health_receipt_path": str(receipt),
                "deleted_file_count": 0,
            }

        eligible = [row for row in files if row["eligible"]]
        deleted: list[dict[str, Any]] = []
        current = total
        for row in sorted(eligible, key=lambda item: (item["mtime"], str(item["path"]))):
            if current <= self.policy.max_runtime_bytes:
                break
            path = row["path"]
            digest = _file_hash(path)
            size = row["size"]
            path.unlink()
            current -= size
            deleted.append({"path": str(path), "size": size, "sha256_before_delete": digest})

        skipped_preserved_count = sum(1 for row in files if row["preserved"])
        if deleted:
            receipt = self._write_receipt(
                "deletions",
                "budget_deletion",
                {
                    "runtime_bytes_before": total,
                    "runtime_bytes_after": current,
                    "max_runtime_bytes": self.policy.max_runtime_bytes,
                    "deleted_file_count": len(deleted),
                    "deleted_files": deleted,
                    "backed_up": False,
                    "zipped": False,
                    "deletion_mode": "permanent_unlinked_files",
                    "skipped_preserved_count": skipped_preserved_count,
                },
            )
            return {
                "decision": "pruned_to_budget" if current <= self.policy.max_runtime_bytes else "over_budget_partially_pruned",
                "max_runtime_bytes": self.policy.max_runtime_bytes,
                "runtime_bytes_before": total,
                "runtime_bytes_after": current,
                "deletion_receipt_path": str(receipt),
                "deleted_file_count": len(deleted),
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
        for root in self.managed_roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file():
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
                        "eligible": not preserved,
                    }
                )
        return rows

    def _write_receipt(self, folder: str, stem: str, payload: dict[str, Any]) -> Path:
        path = self.receipt_root / "budget" / folder / f"{_file_time(utc_now())}.{stem}.json"
        body = {
            "schema_version": 1,
            "kind": f"truecore_storage_{stem}_receipt",
            "created_at_utc": utc_now(),
            "permanent_receipt": True,
            **payload,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")
        return path


def _resolve(path: str | Path) -> Path:
    return Path(path).resolve()


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
