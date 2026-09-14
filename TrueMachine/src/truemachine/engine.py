"""Temporal cognition engine."""

from __future__ import annotations

import time
import uuid
import hashlib
import json
from typing import Callable, Iterable, Protocol

from .clock import Clock
from .fusion import FusionStore
from .model import FusionPack, Observation


class Collector(Protocol):
    name: str
    schema: str
    source_coordinates: tuple[str, ...]

    def collect(self) -> dict: ...


class TemporalEngine:
    def __init__(
        self,
        store: FusionStore,
        collectors: Iterable[Collector],
        clock: Clock | None = None,
        cadence_ns: int = 1_000_000_000,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if type(cadence_ns) is not int or cadence_ns <= 0:
            raise ValueError("cadence_ns must be a positive integer")
        self.store = store
        self.collectors = tuple(collectors)
        self.clock = clock or Clock()
        self.run_id = uuid.uuid4().hex
        self.sequence = 0
        self.cadence_ns = cadence_ns
        self.monotonic_ns = monotonic_ns
        self.sleep = sleep

    def pulse(self, *, scheduled_monotonic_ns: int | None = None) -> FusionPack:
        pulse_started = self.monotonic_ns()
        scheduled = pulse_started if scheduled_monotonic_ns is None else scheduled_monotonic_ns
        if type(scheduled) is not int or scheduled < 0:
            raise ValueError("scheduled_monotonic_ns must be a nonnegative integer")
        lateness = max(0, pulse_started - scheduled)
        sample = self.clock.sample()
        observations = []
        for collector in self.collectors:
            collection_started = self.monotonic_ns()
            try:
                data = collector.collect()
                collection_ended = self.monotonic_ns()
                encoded = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
                observations.append(Observation(
                    source=collector.name,
                    schema=collector.schema,
                    status="ok",
                    data=data,
                    source_coordinates=collector.source_coordinates,
                    content_sha256=hashlib.sha256(encoded).hexdigest(),
                    collection_started_monotonic_ns=collection_started,
                    collection_ended_monotonic_ns=collection_ended,
                    collection_duration_ns=collection_ended - collection_started,
                ))
            except Exception as error:
                collection_ended = self.monotonic_ns()
                observations.append(Observation(
                    source=collector.name,
                    schema=collector.schema,
                    status="error",
                    data={},
                    source_coordinates=collector.source_coordinates,
                    content_sha256=hashlib.sha256(b"{}").hexdigest(),
                    collection_started_monotonic_ns=collection_started,
                    collection_ended_monotonic_ns=collection_ended,
                    collection_duration_ns=collection_ended - collection_started,
                    error=f"{type(error).__name__}: {error}",
                ))
        self.sequence += 1
        pack = FusionPack(
            "truemachine.fusion@2",
            self.run_id,
            self.sequence,
            self.cadence_ns,
            (self.sequence - 1) * self.cadence_ns,
            sample,
            {
                "scheduled_monotonic_ns": scheduled,
                "pulse_started_monotonic_ns": pulse_started,
                "scheduling_lateness_ns": lateness,
                "cadence_boundaries_missed_before_start": lateness // self.cadence_ns,
            },
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
        deadline = self.monotonic_ns() + int(duration_seconds * 1_000_000_000)
        next_pulse = self.monotonic_ns()
        count = 0
        while self.monotonic_ns() < deadline:
            self.pulse(scheduled_monotonic_ns=next_pulse)
            count += 1
            next_pulse += int(interval_seconds * 1_000_000_000)
            remaining = next_pulse - self.monotonic_ns()
            if remaining > 0:
                self.sleep(remaining / 1_000_000_000)
        return count
