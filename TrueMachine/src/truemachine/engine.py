"""Temporal cognition engine."""

from __future__ import annotations

import time
import uuid
import hashlib
import json
from typing import Iterable, Protocol

from .clock import Clock
from .fusion import FusionStore
from .model import FusionPack, Observation


class Collector(Protocol):
    name: str
    schema: str
    source_coordinates: tuple[str, ...]

    def collect(self) -> dict: ...


class TemporalEngine:
    def __init__(self, store: FusionStore, collectors: Iterable[Collector], clock: Clock | None = None, cadence_ns: int = 1_000_000_000) -> None:
        self.store = store
        self.collectors = tuple(collectors)
        self.clock = clock or Clock()
        self.run_id = uuid.uuid4().hex
        self.sequence = 0
        self.cadence_ns = cadence_ns

    def pulse(self) -> FusionPack:
        sample = self.clock.sample()
        observations = []
        for collector in self.collectors:
            try:
                data = collector.collect()
                encoded = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
                observations.append(Observation(
                    collector.name,
                    collector.schema,
                    "ok",
                    data,
                    collector.source_coordinates,
                    hashlib.sha256(encoded).hexdigest(),
                ))
            except Exception as error:
                observations.append(Observation(
                    collector.name,
                    collector.schema,
                    "error",
                    {},
                    collector.source_coordinates,
                    hashlib.sha256(b"{}").hexdigest(),
                    f"{type(error).__name__}: {error}",
                ))
        self.sequence += 1
        pack = FusionPack(
            "truemachine.fusion@1",
            self.run_id,
            self.sequence,
            self.cadence_ns,
            (self.sequence - 1) * self.cadence_ns,
            sample,
            tuple(observations),
        )
        self.store.commit(pack)
        return pack

    def run(self, duration_seconds: float, interval_seconds: float) -> int:
        if duration_seconds <= 0 or interval_seconds <= 0:
            raise ValueError("duration and interval must be positive")
        requested_cadence_ns = int(interval_seconds * 1_000_000_000)
        if requested_cadence_ns != self.cadence_ns:
            raise ValueError("run interval must equal the engine's locked cadence")
        deadline = time.monotonic_ns() + int(duration_seconds * 1_000_000_000)
        next_pulse = time.monotonic_ns()
        count = 0
        while time.monotonic_ns() < deadline:
            self.pulse()
            count += 1
            next_pulse += int(interval_seconds * 1_000_000_000)
            remaining = next_pulse - time.monotonic_ns()
            if remaining > 0:
                time.sleep(remaining / 1_000_000_000)
        return count
