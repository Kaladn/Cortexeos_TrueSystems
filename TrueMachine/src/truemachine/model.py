"""Fusion Pack data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .clock import TimeSample


@dataclass(frozen=True, slots=True)
class Observation:
    source: str
    schema: str
    status: str
    data: dict[str, Any]
    source_coordinates: tuple[str, ...]
    content_sha256: str
    collection_started_monotonic_ns: int
    collection_ended_monotonic_ns: int
    collection_duration_ns: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FusionPack:
    schema: str
    run_id: str
    sequence: int
    cadence_ns: int
    timeline_ns: int
    time: TimeSample
    scheduling: dict[str, int]
    observations: tuple[Observation, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "run_id": self.run_id,
            "sequence": self.sequence,
            "cadence_ns": self.cadence_ns,
            "timeline_ns": self.timeline_ns,
            "time": self.time.to_dict(),
            "scheduling": self.scheduling,
            "observations": [item.to_dict() for item in self.observations],
        }
