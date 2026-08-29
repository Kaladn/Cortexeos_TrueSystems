"""Harmless proof worker that emits one diagnostic heartbeat packet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from truecore.time import utc_now


@dataclass(frozen=True)
class HeartbeatWorker:
    worker_id: str = "worker_heartbeat"
    worker_type: str = "diagnostic"

    def packet(
        self,
        *,
        job_id: str | None = None,
        state: str = "idle",
        task_name: str = "heartbeat",
        progress: float = 0.0,
        cpu: float = 0.0,
        ram: float = 0.0,
        gpu: float = 0.0,
        queue_depth: int = 0,
        input_hash: str = "",
        output_hash: str | None = None,
        receipt_id: str | None = None,
        error_code: str | None = None,
        error_summary: str | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "job_id": job_id or f"job_{uuid4().hex[:12]}",
            "timestamp": utc_now(),
            "state": state,
            "task_name": task_name,
            "progress": progress,
            "cpu": cpu,
            "ram": ram,
            "gpu": gpu,
            "queue_depth": queue_depth,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "receipt_id": receipt_id,
            "error_code": error_code,
            "error_summary": error_summary,
        }
