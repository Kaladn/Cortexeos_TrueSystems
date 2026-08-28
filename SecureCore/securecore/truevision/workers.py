"""TrueVision SC Edition worker set."""

from __future__ import annotations

from dataclasses import dataclass

from securecore.sensors.forge_sink import SensorForgeSink
from securecore.truevision.forge_adapter import state_change_to_sensor_event
from securecore.truevision.live_capture import TrueVisionSCLiveCapture


@dataclass(slots=True)
class TrueVisionSCWorkerStats:
    captured: int = 0
    written: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    max_change_ratio: float = 0.0

    def to_dict(self) -> dict:
        return {
            "captured": self.captured,
            "written": self.written,
            "low": self.low,
            "medium": self.medium,
            "high": self.high,
            "max_change_ratio": round(self.max_change_ratio, 6),
        }


class TrueVisionSCAnomalyWorker:
    """Cheap visual-change pressure classifier."""

    def classify(self, record: dict) -> dict:
        ratio = float(record.get("change_ratio", 0.0) or 0.0)
        if ratio >= 0.35:
            level = "high"
        elif ratio >= 0.10:
            level = "medium"
        elif ratio > 0.0:
            level = "low"
        else:
            level = "none"
        return {
            "change_id": record.get("change_id", ""),
            "level": level,
            "change_ratio": round(ratio, 6),
            "wake_recommended": level in {"medium", "high"},
        }


class TrueVisionSCForgeWorker:
    """Write compact TrueVision SC records to Forge through the sensor lane."""

    def __init__(self, forge_root: str, *, host_id: str = "local-host"):
        self.sink = SensorForgeSink(forge_root)
        self.host_id = host_id
        self.sequence = 0
        self.previous_event_hash = "GENESIS"

    def write_state_change(self, record: dict, *, batch_id: str, batch_index: int = 0) -> dict:
        event = state_change_to_sensor_event(
            record,
            host_id=self.host_id,
            sequence=self.sequence,
            previous_event_hash=self.previous_event_hash,
            batch_id=batch_id,
            batch_index=batch_index,
        )
        self.sink.write_events("sensor_vision", [event])
        self.sequence += 1
        self.previous_event_hash = event["payload_hash"]
        return event


class TrueVisionSCWorkerSet:
    """Capture, classify, and write TrueVision SC state changes on explicit calls."""

    def __init__(
        self,
        *,
        capture: TrueVisionSCLiveCapture,
        forge_worker: TrueVisionSCForgeWorker,
        anomaly_worker: TrueVisionSCAnomalyWorker | None = None,
    ):
        self.capture = capture
        self.forge_worker = forge_worker
        self.anomaly_worker = anomaly_worker or TrueVisionSCAnomalyWorker()
        self.stats = TrueVisionSCWorkerStats()

    def step(self, *, change_id: str | None = None, batch_id: str = "truevision-sc") -> dict:
        record = self.capture.capture_state_change(change_id=change_id)
        anomaly = self.anomaly_worker.classify(record)
        event = self.forge_worker.write_state_change(
            record,
            batch_id=batch_id,
            batch_index=self.stats.captured,
        )
        self._update_stats(record, anomaly)
        return {
            "record": record,
            "anomaly": anomaly,
            "event_id": event["event_id"],
        }

    def _update_stats(self, record: dict, anomaly: dict) -> None:
        self.stats.captured += 1
        self.stats.written += 1
        level = anomaly["level"]
        if level == "low":
            self.stats.low += 1
        elif level == "medium":
            self.stats.medium += 1
        elif level == "high":
            self.stats.high += 1
        self.stats.max_change_ratio = max(
            self.stats.max_change_ratio,
            float(record.get("change_ratio", 0.0) or 0.0),
        )
