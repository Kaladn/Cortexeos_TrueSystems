"""netlog operators — connection anomaly detectors."""

from __future__ import annotations
from typing import Any
from wolf_engine.modules.base import WolfModule
from netlog.config import FOREIGN_PORT_ALERTLIST, HIGH_CONNECTION_COUNT


class SuspiciousPortOperator(WolfModule):
    """Flags connections to known suspicious/RAT ports."""
    key = "op_suspicious_port"
    name = "Suspicious Port Operator"
    category = "operator"
    description = f"Flags connections to ports: {FOREIGN_PORT_ALERTLIST}"

    def analyze(self, conn_event: dict) -> dict | None:
        if "SUSPICIOUS_PORT" not in conn_event.get("alerts", []):
            return None
        return {
            "operator": self.key,
            "anomaly": "SUSPICIOUS_PORT",
            "proc": conn_event.get("proc"),
            "pid": conn_event.get("pid"),
            "raddr": conn_event.get("raddr"),
            "confidence": 0.9,
        }

    def info(self) -> dict:
        return {"key": self.key, "name": self.name,
                "category": self.category, "description": self.description}


class NewProcessOperator(WolfModule):
    """Flags first-seen processes opening network connections."""
    key = "op_new_process"
    name = "New Process Connection Operator"
    category = "operator"
    description = "Flags first-time process-to-network connections"

    def analyze(self, conn_event: dict) -> dict | None:
        if "NEW_PROCESS_CONNECTION" not in conn_event.get("alerts", []):
            return None
        return {
            "operator": self.key,
            "anomaly": "NEW_PROCESS_CONNECTION",
            "proc": conn_event.get("proc"),
            "pid": conn_event.get("pid"),
            "raddr": conn_event.get("raddr"),
            "confidence": 0.6,
        }

    def info(self) -> dict:
        return {"key": self.key, "name": self.name,
                "category": self.category, "description": self.description}
