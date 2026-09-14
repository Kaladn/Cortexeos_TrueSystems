"""Durable WAL-first Fusion Pack storage."""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any

from .model import FusionPack


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


class FusionStore:
    def __init__(self, state_dir: str | Path, *, create: bool = True) -> None:
        self.state_dir = Path(state_dir)
        self.packs_dir = self.state_dir / "packs"
        if create:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.packs_dir.mkdir(parents=True, exist_ok=True)
        self.wal_path = self.state_dir / "fusion.wal.jsonl"
        self.current_path = self.state_dir / "current.fusion.json"
        self.lock_path = self.state_dir / ".fusion-writer.lock"

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
        with self.lock_path.open("ab") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
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
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _read_regular(path: Path) -> bytes:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError(f"published path is not a regular file: {path}")
            return handle.read()

    @staticmethod
    def _validate_pack(pack: Any, line_number: int) -> tuple[str, int]:
        fields = {
            "schema", "run_id", "sequence", "cadence_ns", "timeline_ns",
            "time", "scheduling", "observations",
        }
        if not isinstance(pack, dict) or set(pack) != fields or pack.get("schema") != "truemachine.fusion@2":
            raise ValueError(f"invalid pack at WAL line {line_number}")
        run_id = pack.get("run_id")
        sequence = pack.get("sequence")
        if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", run_id):
            raise ValueError(f"invalid pack run_id at WAL line {line_number}")
        if type(sequence) is not int or sequence < 1:
            raise ValueError(f"invalid pack sequence at WAL line {line_number}")
        cadence = pack.get("cadence_ns")
        timeline = pack.get("timeline_ns")
        if (
            type(cadence) is not int or cadence <= 0 or type(timeline) is not int or
            timeline != (sequence - 1) * cadence
        ):
            raise ValueError(f"invalid pack timeline at WAL line {line_number}")
        scheduling = pack.get("scheduling")
        scheduling_fields = {
            "scheduled_monotonic_ns", "pulse_started_monotonic_ns",
            "scheduling_lateness_ns", "cadence_boundaries_missed_before_start",
        }
        if not isinstance(scheduling, dict) or set(scheduling) != scheduling_fields:
            raise ValueError(f"invalid scheduling timing at WAL line {line_number}")
        if any(type(scheduling[field]) is not int or scheduling[field] < 0 for field in scheduling_fields):
            raise ValueError(f"invalid scheduling timing at WAL line {line_number}")
        lateness = max(0, scheduling["pulse_started_monotonic_ns"] - scheduling["scheduled_monotonic_ns"])
        if (
            scheduling["scheduling_lateness_ns"] != lateness or
            scheduling["cadence_boundaries_missed_before_start"] != lateness // cadence
        ):
            raise ValueError(f"invalid scheduling timing at WAL line {line_number}")
        observations = pack.get("observations")
        if not isinstance(observations, list) or not observations:
            raise ValueError(f"invalid observations at WAL line {line_number}")
        previous_end: int | None = None
        for index, observation in enumerate(observations):
            if not isinstance(observation, dict) or not isinstance(observation.get("data"), dict):
                raise ValueError(f"invalid observation {index} at WAL line {line_number}")
            started = observation.get("collection_started_monotonic_ns")
            ended = observation.get("collection_ended_monotonic_ns")
            duration = observation.get("collection_duration_ns")
            if (
                type(started) is not int or started < 0 or
                type(ended) is not int or ended < started or
                type(duration) is not int or duration != ended - started or
                (previous_end is not None and started < previous_end)
            ):
                raise ValueError(f"invalid observation timing at WAL line {line_number} index {index}")
            previous_end = ended
            expected = observation.get("content_sha256")
            encoded = json.dumps(
                observation["data"], ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            actual = hashlib.sha256(encoded).hexdigest()
            if expected != actual:
                raise ValueError(f"observation hash mismatch at WAL line {line_number} index {index}")
        sampled_monotonic = pack.get("time", {}).get("monotonic_ns")
        first_started = observations[0]["collection_started_monotonic_ns"]
        if (
            type(sampled_monotonic) is not int or
            not scheduling["pulse_started_monotonic_ns"] <= sampled_monotonic <= first_started
        ):
            raise ValueError(f"invalid sampling timing at WAL line {line_number}")
        return run_id, sequence

    def verify(self) -> dict[str, int]:
        entries = 0
        runs: dict[str, int] = {}
        last_content: bytes | None = None
        descriptor = os.open(self.wal_path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as wal:
            if not stat.S_ISREG(os.fstat(wal.fileno()).st_mode):
                raise ValueError("WAL is not a regular file")
            for line_number, line in enumerate(wal, 1):
                envelope = json.loads(line)
                if not isinstance(envelope, dict) or set(envelope) != {"run_id", "sequence", "sha256", "pack"}:
                    raise ValueError(f"invalid WAL envelope at line {line_number}")
                content = canonical_json(envelope["pack"])
                actual = hashlib.sha256(content).hexdigest()
                if actual != envelope["sha256"]:
                    raise ValueError(f"WAL hash mismatch at line {line_number}")
                run_id, sequence = self._validate_pack(envelope["pack"], line_number)
                if envelope["run_id"] != run_id or envelope["sequence"] != sequence:
                    raise ValueError(f"WAL envelope identity mismatch at line {line_number}")
                expected = runs.get(run_id, 0) + 1
                if sequence != expected:
                    raise ValueError(f"sequence break for {run_id}: expected {expected}")
                pack_path = self.packs_dir / run_id / f"{sequence:012d}.fusion.json"
                if self._read_regular(pack_path) != content:
                    raise ValueError(f"published pack mismatch at WAL line {line_number}")
                runs[run_id] = expected
                entries += 1
                last_content = content
        if last_content is not None and self._read_regular(self.current_path) != last_content:
            raise ValueError("current Fusion Pack does not match the final WAL entry")
        return {"entries": entries, "runs": len(runs)}
