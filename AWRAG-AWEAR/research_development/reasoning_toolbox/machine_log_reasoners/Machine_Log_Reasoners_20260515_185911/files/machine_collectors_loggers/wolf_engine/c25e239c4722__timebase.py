"""
Monotonic Timebase — Ordered event timestamps across the cluster.

Each node uses time.monotonic_ns() for ordering within a single process.
Wall-clock time.time() is recorded alongside for human-readable logs and
approximate cross-node alignment (±0.5ms typical on 1GbE with NTP).

Cross-node ordering: events carry both monotonic_ns (local ordering) and
wall_clock (global approximation). Fusion sorts by wall_clock with
monotonic_ns as tiebreaker within the same node.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class Timestamp:
    """Dual-clock timestamp for evidence events."""

    monotonic_ns: int = 0
    wall_clock: float = 0.0
    node_id: str = ""

    def __post_init__(self) -> None:
        if self.monotonic_ns == 0:
            self.monotonic_ns = time.monotonic_ns()
        if self.wall_clock == 0.0:
            self.wall_clock = time.time()

    def to_dict(self) -> dict:
        return {
            "monotonic_ns": self.monotonic_ns,
            "wall_clock": self.wall_clock,
            "node_id": self.node_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Timestamp:
        return cls(
            monotonic_ns=data.get("monotonic_ns", 0),
            wall_clock=data.get("wall_clock", 0.0),
            node_id=data.get("node_id", ""),
        )

    def __lt__(self, other: Timestamp) -> bool:
        """Sort by wall_clock first, then monotonic_ns within same node."""
        if self.wall_clock != other.wall_clock:
            return self.wall_clock < other.wall_clock
        if self.node_id == other.node_id:
            return self.monotonic_ns < other.monotonic_ns
        return self.wall_clock < other.wall_clock


@dataclass(slots=True)
class EvidenceEvent:
    """A single telemetry data point from any worker."""

    worker: str = ""
    event_type: str = ""
    timestamp: Timestamp = field(default_factory=Timestamp)
    data: dict = field(default_factory=dict)
    session_id: str = ""

    def to_dict(self) -> dict:
        return {
            "worker": self.worker,
            "event_type": self.event_type,
            "timestamp": self.timestamp.to_dict(),
            "data": self.data,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EvidenceEvent:
        return cls(
            worker=d.get("worker", ""),
            event_type=d.get("event_type", ""),
            timestamp=Timestamp.from_dict(d.get("timestamp", {})),
            data=d.get("data", {}),
            session_id=d.get("session_id", ""),
        )
