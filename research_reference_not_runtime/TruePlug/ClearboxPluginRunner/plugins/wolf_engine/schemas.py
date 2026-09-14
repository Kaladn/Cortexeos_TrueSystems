"""Wolf Engine — Pinned schema definitions.

All schemas are pure Python dataclasses — no external deps.
Schema versions are immutable: breaking change = new version string.

Re-exported from archon/schemas.py for backward compatibility.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Schema Versions ──────────────────────────────────────────

VERDICT_VERSION = "wolf_engine_verdict@1"
ENGINE_RESPONSE_VERSION = "wolf_engine_engine_response@1"
GOVERNANCE_FLAG_VERSION = "wolf_engine_governance_flag@1"


# ── Enums ────────────────────────────────────────────────────

class VerdictStatus(Enum):
    """Outcome of governance evaluation."""
    APPROVED = "approved"
    ADJUSTED = "adjusted"
    QUARANTINED = "quarantined"
    PENALIZED = "penalized"


class FlagSeverity(Enum):
    """How serious a governance flag is."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ── Dataclasses ──────────────────────────────────────────────

@dataclass(slots=True)
class EngineResponse:
    """Standardized output from the reasoning engine for Archon to evaluate."""

    schema_version: str = ENGINE_RESPONSE_VERSION
    session_id: str = ""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    confidence: float = 0.0
    total_windows: int = 0
    avg_consistency: float = 0.0
    pattern_breaks: int = 0
    causal_chains: int = 0
    anomalies: int = 0
    top_resonance: list[dict] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass(slots=True)
class GovernanceFlag:
    """A single flag raised by a governance module."""

    schema_version: str = GOVERNANCE_FLAG_VERSION
    module: str = ""
    severity: FlagSeverity = FlagSeverity.INFO
    code: str = ""
    message: str = ""
    adjustment: float = 0.0


@dataclass(slots=True)
class Verdict:
    """Final Archon verdict on an engine response."""

    schema_version: str = VERDICT_VERSION
    verdict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    session_id: str = ""
    status: VerdictStatus = VerdictStatus.APPROVED
    original_confidence: float = 0.0
    adjusted_confidence: float = 0.0
    flags: list[GovernanceFlag] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict_id": self.verdict_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "original_confidence": self.original_confidence,
            "adjusted_confidence": round(self.adjusted_confidence, 6),
            "flags": [
                {
                    "module": f.module,
                    "severity": f.severity.value,
                    "code": f.code,
                    "message": f.message,
                    "adjustment": f.adjustment,
                }
                for f in self.flags
            ],
            "timestamp": self.timestamp,
        }
