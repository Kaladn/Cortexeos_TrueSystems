"""Hash-preserving intake for sibling-system state artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


STATE_SUFFIXES = {".json", ".jsonl", ".npz", ".tvcells"}
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".mp4", ".mkv", ".wav", ".mp3", ".flac"}


class StateArtifactCollector:
    """Admit a state artifact without taking ownership from its source system."""

    def __init__(self, system: str, path: str | Path) -> None:
        normalized = system.strip().lower()
        if normalized not in {"truevision", "trueaudio", "awrag", "awear"}:
            raise ValueError(f"unsupported sibling system: {system}")
        self.path = Path(path).expanduser().resolve()
        if self.path.suffix.lower() in MEDIA_SUFFIXES:
            raise ValueError("rendered/raw media is not an authoritative state artifact")
        if self.path.suffix.lower() not in STATE_SUFFIXES:
            raise ValueError("unknown artifact type cannot be promoted to source truth")
        self.name = normalized
        self.schema = self._read_schema()
        self.source_coordinates = (str(self.path),)

    def _read_schema(self) -> str:
        if self.path.suffix.lower() == ".json":
            payload = json.loads(self.path.read_bytes())
        elif self.path.suffix.lower() == ".jsonl":
            first = next((line for line in self.path.read_bytes().splitlines() if line.strip()), None)
            if first is None:
                raise ValueError("empty state artifact has no source schema")
            payload = json.loads(first)
        else:
            raise ValueError("binary state artifacts require a source manifest with a declared schema")
        schema = payload.get("schema_version") or payload.get("schema")
        if not isinstance(schema, str) or not schema.strip():
            raise ValueError("state artifact does not declare its source-owned schema")
        return schema.strip()

    def collect(self) -> dict:
        payload = self.path.read_bytes()
        result = {
            "artifact_name": self.path.name,
            "artifact_size_bytes": len(payload),
            "artifact_sha256": hashlib.sha256(payload).hexdigest(),
            "authority": "source_system_retained",
        }
        if self.path.suffix.lower() == ".jsonl":
            rows = [line for line in payload.splitlines() if line.strip()]
            for line_number, line in enumerate(rows, 1):
                json.loads(line)
            result["coordinates"] = {"line_start": 1, "line_end": len(rows)}
        elif self.path.suffix.lower() == ".json":
            json.loads(payload)
            result["coordinates"] = {"document": self.path.name}
        return result
