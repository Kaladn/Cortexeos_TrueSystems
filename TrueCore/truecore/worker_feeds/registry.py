"""Registry of coded worker diagnostic feeds."""

from __future__ import annotations

from typing import Any


def default_worker_registry() -> list[dict[str, Any]]:
    return [
        {
            "worker_id": "worker_heartbeat",
            "worker_type": "diagnostic",
            "runtime_language": "python",
            "entrypoint": "truecore.worker_feeds.heartbeat_worker.HeartbeatWorker",
            "status": "installed",
            "activation": "manual_call_only",
            "diagnostic_feed": "worker_heartbeat",
            "writes": ["forge:worker_diagnostics", "receipt:worker_feeds"],
            "param_contract": {
                "sample_interval_seconds": {"type": "float", "default": 1.0, "min": 0.1, "max": 60.0},
                "job_id": {"type": "string", "default": "heartbeat"},
            },
            "no_user_replay": True,
            "no_security_enforcement": True,
            "prompt_only": False,
        }
    ]
