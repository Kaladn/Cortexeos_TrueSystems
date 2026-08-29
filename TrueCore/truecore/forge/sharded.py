"""Forge V2 sharded binary store.

This lives beside the existing ForgeWriter. It keeps payload records in binary
shard files and stores a rebuildable binary index for tail/seek operations.
"""

from __future__ import annotations

import os
import struct
import threading
from pathlib import Path
from typing import Iterator

from truecore.forge.record import ForgeRecord, PREFIX


SHARD_SUFFIX = ".scfgshard"
INDEX_MAGIC = b"SCIX"
INDEX_VERSION = 1
INDEX_HEADER = struct.Struct("<4sB")
INDEX_ROW = struct.Struct("<IQQQI")


class ShardedForgeWriter:
    """Single-writer sharded Forge append store."""

    def __init__(self, base_dir: str | Path, *, max_records_per_shard: int = 100_000):
        if max_records_per_shard <= 0:
            raise ValueError("max_records_per_shard must be positive")
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._max_records_per_shard = max_records_per_shard
        self._index_path = self._base_dir / "records.sidx"
        self._lock = threading.Lock()
        self._record_count = _index_count(self._index_path)

    @property
    def index_path(self) -> Path:
        return self._index_path

    def append_dict(self, data: dict) -> dict:
        record = ForgeRecord.from_substrate_dict(data)
        frame = record.encode()
        with self._lock:
            global_index = self._record_count
            shard_id = global_index // self._max_records_per_shard
            shard_index = global_index % self._max_records_per_shard
            shard_path = _shard_path(self._base_dir, shard_id)
            offset = shard_path.stat().st_size if shard_path.exists() else 0
            with open(shard_path, "ab") as handle:
                handle.write(frame)
            _append_index(
                self._index_path,
                shard_id=shard_id,
                shard_index=shard_index,
                offset=offset,
                size=len(frame),
            )
            self._record_count += 1
        return {
            "record_id": record.record_id,
            "substrate": record.substrate,
            "sequence": record.sequence,
            "timestamp": record.timestamp,
            "cell_id": record.cell_id,
            "record_type": record.record_type,
            "shard_id": shard_id,
            "shard_index": shard_index,
            "offset": offset,
            "size": len(frame),
        }


class ShardedForgeReader:
    """Read a sharded Forge V2 store."""

    def __init__(self, base_dir: str | Path):
        self._base_dir = Path(base_dir)
        self._index_path = self._base_dir / "records.sidx"

    @property
    def index_path(self) -> Path:
        return self._index_path

    def iter_records(self) -> Iterator[ForgeRecord]:
        entries = _read_index(self._index_path)
        if entries:
            for entry in entries:
                yield self._read_entry(entry)
            return

        for shard_path in sorted(self._base_dir.glob(f"*{SHARD_SUFFIX}")):
            with open(shard_path, "rb") as handle:
                while True:
                    prefix = handle.read(PREFIX.size)
                    if not prefix:
                        break
                    if len(prefix) != PREFIX.size:
                        raise ValueError("truncated forge shard record prefix")
                    _, _, header_len, payload_len, _ = PREFIX.unpack(prefix)
                    body = handle.read(header_len + payload_len)
                    if len(body) != header_len + payload_len:
                        raise ValueError("truncated forge shard record body")
                    yield ForgeRecord.decode(prefix + body)

    def tail(self, limit: int = 20) -> list[ForgeRecord]:
        if limit <= 0:
            return []
        entries = _read_index(self._index_path)
        if not entries:
            return list(self.iter_records())[-limit:]
        return [self._read_entry(entry) for entry in entries[-limit:]]

    def rebuild_index(self) -> dict:
        records_indexed = 0
        if self._index_path.exists():
            self._index_path.unlink()
        for shard_path in sorted(self._base_dir.glob(f"*{SHARD_SUFFIX}")):
            shard_id = _shard_id_from_path(shard_path)
            shard_index = 0
            with open(shard_path, "rb") as handle:
                while True:
                    offset = handle.tell()
                    prefix = handle.read(PREFIX.size)
                    if not prefix:
                        break
                    if len(prefix) != PREFIX.size:
                        raise ValueError("truncated forge shard record prefix")
                    _, _, header_len, payload_len, _ = PREFIX.unpack(prefix)
                    body = handle.read(header_len + payload_len)
                    if len(body) != header_len + payload_len:
                        raise ValueError("truncated forge shard record body")
                    size = PREFIX.size + header_len + payload_len
                    ForgeRecord.decode(prefix + body)
                    _append_index(
                        self._index_path,
                        shard_id=shard_id,
                        shard_index=shard_index,
                        offset=offset,
                        size=size,
                    )
                    records_indexed += 1
                    shard_index += 1
        return {"records_indexed": records_indexed, "index_path": str(self._index_path)}

    def verify(self) -> dict:
        count = 0
        last_sequence = -1
        last_chain_hash = None
        for record in self.iter_records():
            if record.sequence <= last_sequence:
                return {
                    "intact": False,
                    "error": "sequence regression",
                    "sequence": record.sequence,
                }
            if last_chain_hash is not None and record.previous_hash != last_chain_hash:
                return {
                    "intact": False,
                    "error": "previous_hash mismatch",
                    "sequence": record.sequence,
                }
            last_sequence = record.sequence
            last_chain_hash = record.chain_hash
            count += 1
        return {
            "intact": True,
            "total_records": count,
            "last_sequence": last_sequence,
            "index_path": str(self._index_path),
        }

    def _read_entry(self, entry: dict) -> ForgeRecord:
        shard_path = _shard_path(self._base_dir, int(entry["shard_id"]))
        with open(shard_path, "rb") as handle:
            handle.seek(int(entry["offset"]), os.SEEK_SET)
            raw = handle.read(int(entry["size"]))
        return ForgeRecord.decode(raw)


def _append_index(path: Path, *, shard_id: int, shard_index: int, offset: int, size: int) -> None:
    needs_header = not path.exists()
    with open(path, "ab") as handle:
        if needs_header:
            handle.write(INDEX_HEADER.pack(INDEX_MAGIC, INDEX_VERSION))
        handle.write(INDEX_ROW.pack(shard_id, shard_index, offset, size, 0))


def _read_index(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = path.read_bytes()
    if not data:
        return []
    if len(data) < INDEX_HEADER.size:
        raise ValueError("forge shard index too small")
    magic, version = INDEX_HEADER.unpack(data[: INDEX_HEADER.size])
    if magic != INDEX_MAGIC:
        raise ValueError("invalid forge shard index magic")
    if version != INDEX_VERSION:
        raise ValueError(f"unsupported forge shard index version: {version}")
    body = data[INDEX_HEADER.size :]
    if len(body) % INDEX_ROW.size != 0:
        raise ValueError("truncated forge shard index")
    entries = []
    for offset in range(0, len(body), INDEX_ROW.size):
        shard_id, shard_index, record_offset, size, flags = INDEX_ROW.unpack(body[offset : offset + INDEX_ROW.size])
        entries.append(
            {
                "shard_id": shard_id,
                "shard_index": shard_index,
                "offset": record_offset,
                "size": size,
                "flags": flags,
            }
        )
    return entries


def _index_count(path: Path) -> int:
    return len(_read_index(path))


def _shard_path(base_dir: Path, shard_id: int) -> Path:
    return base_dir / f"{shard_id:06d}{SHARD_SUFFIX}"


def _shard_id_from_path(path: Path) -> int:
    return int(path.name.split(".", 1)[0])
