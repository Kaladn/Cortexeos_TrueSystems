"""Single temporal authority for TrueMachine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import time


UTC = timezone.utc


def format_utc_ns(unix_time_ns: int) -> str:
    seconds, nanoseconds = divmod(unix_time_ns, 1_000_000_000)
    base = datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{base}.{nanoseconds:09d}Z"


@dataclass(frozen=True, slots=True)
class TimeSample:
    utc: str
    utc_date: str
    unix_time_ns: int
    monotonic_ns: int
    elapsed_ns: int
    clock_offset_ns: int
    boot_id: str

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


class Clock:
    """Pairs realtime with monotonic time and exposes observed clock movement."""

    def __init__(self) -> None:
        self._wall_anchor_ns = time.time_ns()
        self._mono_anchor_ns = time.monotonic_ns()
        boot_path = Path("/proc/sys/kernel/random/boot_id")
        self.boot_id = boot_path.read_text(encoding="ascii").strip()

    def sample(self) -> TimeSample:
        monotonic_ns = time.monotonic_ns()
        unix_time_ns = time.time_ns()
        elapsed_ns = monotonic_ns - self._mono_anchor_ns
        projected_wall_ns = self._wall_anchor_ns + elapsed_ns
        utc = format_utc_ns(unix_time_ns)
        return TimeSample(
            utc=utc,
            utc_date=utc[:10],
            unix_time_ns=unix_time_ns,
            monotonic_ns=monotonic_ns,
            elapsed_ns=elapsed_ns,
            clock_offset_ns=unix_time_ns - projected_wall_ns,
            boot_id=self.boot_id,
        )
