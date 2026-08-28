"""Proof-of-life logger for TrueVision SC Edition.

This worker logs local presence metadata only. It does not store camera frames,
audio, keystrokes, mouse paths, screenshots, or model output. Camera probing is
best-effort and optional; local HID activity is the fallback.
"""

from __future__ import annotations

import argparse
import ctypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from securecore.sensors.contracts import build_sensor_event, validate_sensor_event
from securecore.sensors.forge_sink import SensorForgeSink
from securecore.time import utc_now


@dataclass(slots=True)
class LocalHIDSnapshot:
    available: bool
    idle_seconds: float
    local_hid_recent: bool
    foreground_process: str = ""

    def to_payload(self) -> dict:
        return {
            "available": self.available,
            "idle_seconds": round(max(0.0, float(self.idle_seconds)), 3),
            "local_hid_recent": bool(self.local_hid_recent),
            "foreground_process": self.foreground_process,
        }


@dataclass(slots=True)
class CameraPresenceSnapshot:
    available: bool
    human_present: bool
    confidence: float
    method: str
    error: str = ""

    def to_payload(self) -> dict:
        return {
            "available": bool(self.available),
            "human_present": bool(self.human_present),
            "confidence": round(max(0.0, min(1.0, float(self.confidence))), 3),
            "method": self.method,
            "error": self.error,
        }


class WindowsHIDProbe:
    """Read coarse local-HID proof without capturing input content."""

    def sample(self, *, recent_threshold_seconds: float = 15.0) -> LocalHIDSnapshot:
        idle = _windows_idle_seconds()
        return LocalHIDSnapshot(
            available=idle is not None,
            idle_seconds=idle if idle is not None else 0.0,
            local_hid_recent=idle is not None and idle <= recent_threshold_seconds,
            foreground_process=_foreground_process_name(),
        )


class OptionalCameraPresenceProbe:
    """Best-effort camera probe with no frame persistence."""

    def sample(self) -> CameraPresenceSnapshot:
        try:
            import cv2  # type: ignore
        except Exception:
            return CameraPresenceSnapshot(
                available=False,
                human_present=False,
                confidence=0.0,
                method="opencv_unavailable",
            )

        capture = cv2.VideoCapture(0)
        try:
            if not capture or not capture.isOpened():
                return CameraPresenceSnapshot(
                    available=False,
                    human_present=False,
                    confidence=0.0,
                    method="camera_unavailable",
                )
            ok, frame = capture.read()
            if not ok or frame is None:
                return CameraPresenceSnapshot(
                    available=True,
                    human_present=False,
                    confidence=0.1,
                    method="camera_no_frame",
                )
            face_count = _opencv_face_count(cv2, frame)
            return CameraPresenceSnapshot(
                available=True,
                human_present=face_count > 0,
                confidence=0.75 if face_count > 0 else 0.25,
                method="opencv_haar_metadata",
            )
        finally:
            if capture:
                capture.release()


class ProofOfLifeWorker:
    """One explicit logger worker: camera presence if possible, HID fallback always."""

    def __init__(
        self,
        *,
        forge_root: str | Path,
        host_id: str = "local-host",
        hid_probe: WindowsHIDProbe | None = None,
        camera_probe: OptionalCameraPresenceProbe | None = None,
        clock: Callable[[], str] = utc_now,
    ):
        self.sink = SensorForgeSink(forge_root)
        self.host_id = host_id
        self.hid_probe = hid_probe or WindowsHIDProbe()
        self.camera_probe = camera_probe or OptionalCameraPresenceProbe()
        self.clock = clock
        self.sequence = 0
        self.previous_event_hash = "GENESIS"

    def sample_once(self, *, batch_id: str = "pol-live", recent_threshold_seconds: float = 15.0) -> dict:
        observed_at = self.clock()
        hid = self.hid_probe.sample(recent_threshold_seconds=recent_threshold_seconds)
        camera = self.camera_probe.sample()
        event = build_proof_of_life_event(
            host_id=self.host_id,
            sequence=self.sequence,
            previous_event_hash=self.previous_event_hash,
            batch_id=batch_id,
            batch_index=self.sequence,
            observed_at_utc=observed_at,
            hid=hid,
            camera=camera,
        )
        self.sink.write_events("sensor_hid", [event])
        self.sequence += 1
        self.previous_event_hash = event["payload_hash"]
        return {"event": event, "payload": event["payload"]}

    def run(self, *, duration_seconds: float = 30.0, interval_seconds: float = 2.0) -> dict:
        deadline = time.monotonic() + max(0.0, float(duration_seconds))
        samples = 0
        human_present = 0
        max_confidence = 0.0
        while time.monotonic() < deadline:
            result = self.sample_once()
            samples += 1
            payload = result["payload"]
            if payload["human_present"]:
                human_present += 1
            max_confidence = max(max_confidence, float(payload["confidence"]))
            time.sleep(max(0.1, float(interval_seconds)))
        return {
            "samples_written": samples,
            "human_present_samples": human_present,
            "max_confidence": round(max_confidence, 3),
        }


def build_proof_of_life_event(
    *,
    host_id: str,
    sequence: int,
    previous_event_hash: str,
    batch_id: str,
    batch_index: int,
    observed_at_utc: str,
    hid: LocalHIDSnapshot,
    camera: CameraPresenceSnapshot,
) -> dict:
    source = "camera" if camera.available else "local_hid"
    human_present = camera.human_present if camera.available else hid.local_hid_recent
    confidence = camera.confidence if camera.available else (0.65 if hid.local_hid_recent else 0.15)
    payload = {
        "schema_version": 1,
        "kind": "securecore_proof_of_life",
        "observed_at_utc": observed_at_utc,
        "source": source,
        "human_present": bool(human_present),
        "confidence": round(float(confidence), 3),
        "camera": camera.to_payload(),
        "hid": hid.to_payload(),
        "payload_class": "small_metadata",
        "raw_content_stored": False,
    }
    event = build_sensor_event(
        sensor_id="securecore.proof_of_life",
        sensor_class="hid",
        host_id=host_id,
        event_type="snapshot",
        sequence=sequence,
        cursor={"sample": sequence, "source": source},
        subject={"source": source, "human_present": bool(human_present)},
        payload=payload,
        previous_event_hash=previous_event_hash,
        confidence="observed",
        privacy_level="metadata",
        writer_id="forge.sensor.pol",
        batch_id=batch_id,
        batch_index=batch_index,
        event_id=f"pol:{host_id}:{sequence}",
        observed_at_utc=observed_at_utc,
    )
    validate_sensor_event(event)
    return event


def _windows_idle_seconds() -> float | None:
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        tick_count = ctypes.windll.kernel32.GetTickCount()
        return max(0.0, (int(tick_count) - int(info.dwTime)) / 1000.0)
    except Exception:
        return None


def _foreground_process_name() -> str:
    try:
        import psutil  # type: ignore

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        return psutil.Process(int(pid.value)).name()
    except Exception:
        return ""


def _opencv_face_count(cv2, frame) -> int:
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return 0
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        return len(faces)
    except Exception:
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SecureCore proof-of-life logger")
    parser.add_argument("--forge-root", required=True)
    parser.add_argument("--host-id", default="local-host")
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    args = parser.parse_args(argv)
    worker = ProofOfLifeWorker(forge_root=args.forge_root, host_id=args.host_id)
    summary = worker.run(duration_seconds=args.duration_seconds, interval_seconds=args.interval_seconds)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
