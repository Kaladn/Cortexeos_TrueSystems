"""Wolf Engine API — Pydantic request/response models.

All response fields have defaults — serialization never crashes.
Error shape is consistent: Optional[Dict[str, Any]].
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Request Models ───────────────────────────────────────────

class IngestRequest(BaseModel):
    text: str
    session_id: str = ""


class AnalyzeRequest(BaseModel):
    text: str = ""
    session_id: str = ""


class CascadeRequest(BaseModel):
    symbol_id: int
    direction: str = "both"
    max_depth: int = 5


class SessionStartRequest(BaseModel):
    label: str = ""


class EvidenceStartRequest(BaseModel):
    workers: Optional[List[str]] = None


class ModuleToggleRequest(BaseModel):
    key: str
    enabled: bool


class ExportRequest(BaseModel):
    what: str = "verdicts"


# ── Response Models ──────────────────────────────────────────

class StatusResponse(BaseModel):
    version: str = ""
    enabled: bool = False
    modules: Dict[str, bool] = {}
    forge_symbols: int = 0
    uptime_sec: float = 0.0
    error: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    source: str = "wolf_engine"
    response: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class AnalyzeResponse(BaseModel):
    """Handoff contract: summary, answer_frame, trace, citations."""
    source: str = "wolf_engine"
    summary: str = ""
    answer_frame: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    error: Optional[Dict[str, Any]] = None
