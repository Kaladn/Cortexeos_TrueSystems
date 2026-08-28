"""Durable WAL-first Fusion Pack storage."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .model import FusionPack


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


class FusionStore:
    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)
        self.packs_dir = self.state_dir / "packs"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        self.wal_path = self.state_dir / "fusion.wal.jsonl"
        self.current_path = self.state_dir / "current.fusion.json"

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def commit(self, pack: FusionPack) -> Path:
        content = canonical_json(pack.to_dict())
        digest = hashlib.sha256(content).hexdigest()
        envelope = canonical_json({
            "run_id": pack.run_id,
            "sequence": pack.sequence,
            "sha256": digest,
            "pack": pack.to_dict(),
        })
        with self.wal_path.open("ab", buffering=0) as wal:
            wal.write(envelope)
            os.fsync(wal.fileno())
        pack_path = self.packs_dir / pack.run_id / f"{pack.sequence:012d}.fusion.json"
        self._atomic_write(pack_path, content)
        self._atomic_write(self.current_path, content)
        return pack_path

    def verify(self) -> dict[str, int]:
        entries = 0
        runs: dict[str, int] = {}
        with self.wal_path.open("rb") as wal:
            for line_number, line in enumerate(wal, 1):
                envelope = json.loads(line)
                content = canonical_json(envelope["pack"])
                actual = hashlib.sha256(content).hexdigest()
                if actual != envelope["sha256"]:
                    raise ValueError(f"WAL hash mismatch at line {line_number}")
                run_id = envelope["run_id"]
                expected = runs.get(run_id, 0) + 1
                if envelope["sequence"] != expected:
                    raise ValueError(f"sequence break for {run_id}: expected {expected}")
                runs[run_id] = expected
                entries += 1
        return {"entries": entries, "runs": len(runs)}
