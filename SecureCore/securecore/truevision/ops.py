"""Explicit TrueVision SC Edition ops entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from securecore.forge.reader import ForgeReader
from securecore.truevision.config import TrueVisionRuntimeConfig
from securecore.truevision.live_capture import TrueVisionSCLiveCapture
from securecore.truevision.workers import TrueVisionSCForgeWorker, TrueVisionSCWorkerSet


def run_truevision_ops_once(
    *,
    forge_root: str | Path,
    host_id: str,
    config: TrueVisionRuntimeConfig,
    capture_backend: Callable[[], object | None],
) -> dict:
    """Capture and write one TrueVision state-change event when enabled."""

    if not config.enabled:
        return {
            "status": "skipped_disabled",
            "written": 0,
            "reason": "truevision_disabled",
        }
    capture = TrueVisionSCLiveCapture(
        source_id=config.source_id,
        session_id=config.session_id,
        grid_size=config.grid_size,
        capture_backend=capture_backend,
    )
    workers = TrueVisionSCWorkerSet(
        capture=capture,
        forge_worker=TrueVisionSCForgeWorker(str(forge_root), host_id=host_id),
    )
    result = workers.step(batch_id="truevision-ops")
    payload_bytes = len(json.dumps(result["record"], separators=(",", ":"), sort_keys=True).encode("utf-8"))
    if payload_bytes > config.max_payload_bytes:
        raise ValueError("TrueVision payload exceeds configured max_payload_bytes")
    verify = ForgeReader(Path(forge_root) / "sensor_vision").verify()
    return {
        "status": "written",
        "written": 1,
        "event_id": result["event_id"],
        "anomaly": result["anomaly"],
        "payload_bytes": payload_bytes,
        "forge_verify": verify,
    }
