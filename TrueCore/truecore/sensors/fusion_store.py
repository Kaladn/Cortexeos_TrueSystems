"""Binary append store for derived TrueCore temporal fusion blocks."""

from __future__ import annotations

import json
import struct
from pathlib import Path

from truecore.sensors.fusion import (
    decode_temporal_fusion_block,
    encode_temporal_fusion_block,
    validate_temporal_fusion_block,
)


FRAME_PREFIX = struct.Struct("<I")


class FusionBlockStore:
    """Append/read compact binary fusion blocks.

    Source events remain in Forge. This store keeps derived all-logger windows
    cheap to replay without carrying source payloads.
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.blocks_path = self.base_dir / "fusion_blocks.scfb"
        self.index_path = self.base_dir / "fusion_blocks.index.jsonl"

    def append(self, block: dict) -> dict:
        block = validate_temporal_fusion_block(block)
        frame = encode_temporal_fusion_block(block)
        offset = self.blocks_path.stat().st_size if self.blocks_path.exists() else 0
        with open(self.blocks_path, "ab") as handle:
            handle.write(FRAME_PREFIX.pack(len(frame)))
            handle.write(frame)
        metadata = {
            "block_id": block["block_id"],
            "source_id": block["source_id"],
            "window_start_utc": block["window_start_utc"],
            "event_count": block["event_count"],
            "source_mask": block["source_mask"],
            "anomaly_flags": block["anomaly_flags"],
            "block_hash": block["block_hash"],
            "previous_block_hash": block["previous_block_hash"],
            "offset": offset,
            "size": FRAME_PREFIX.size + len(frame),
        }
        with open(self.index_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(metadata, separators=(",", ":"), sort_keys=True) + "\n")
        return metadata

    def iter_blocks(self):
        if not self.blocks_path.exists():
            return
        with open(self.blocks_path, "rb") as handle:
            while True:
                prefix = handle.read(FRAME_PREFIX.size)
                if not prefix:
                    break
                if len(prefix) != FRAME_PREFIX.size:
                    raise ValueError("truncated fusion block prefix")
                (size,) = FRAME_PREFIX.unpack(prefix)
                frame = handle.read(size)
                if len(frame) != size:
                    raise ValueError("truncated fusion block frame")
                yield decode_temporal_fusion_block(frame)

    def verify(self) -> dict:
        count = 0
        previous_hash = "GENESIS"
        last_hash = ""
        for block in self.iter_blocks() or []:
            if block["previous_block_hash"] != previous_hash:
                return {
                    "intact": False,
                    "error": "previous_block_hash mismatch",
                    "checked": count,
                }
            previous_hash = block["block_hash"]
            last_hash = block["block_hash"]
            count += 1
        return {
            "intact": True,
            "checked": count,
            "last_block_hash": last_hash,
        }
