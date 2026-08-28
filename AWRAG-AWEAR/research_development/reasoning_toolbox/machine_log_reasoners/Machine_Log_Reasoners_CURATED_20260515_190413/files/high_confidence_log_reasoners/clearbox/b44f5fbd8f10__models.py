"""Pydantic request/response models for the LakeSpeak API.

Matches bridge server patterns: BaseModel with defaults, inline error dict.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Query ────────────────────────────────────────────────────

class LakeSpeakQueryRequest(BaseModel):
    """Query the LakeSpeak retrieval pipeline."""
    query: str
    mode: str = "grounded"          # "grounded" | "allow_fallback"
    topk: int = 5
    session_id: Optional[str] = None


class LakeSpeakQueryResponse(BaseModel):
    """Response from a LakeSpeak query (lakespeak_answer@1)."""
    mode: str
    source: str = "lakespeak"
    response: str = ""
    grounded: bool = False
    refused: bool = False
    refusal_reason: Optional[str] = None
    citations: List[Dict[str, Any]] = []
    reasoning_trace: Optional[Dict[str, Any]] = None
    verdict: Optional[str] = None           # "acceptable" | "trash"
    verdict_reasons: List[str] = []
    suggested_next_mode: Optional[str] = None
    caveats: List[str] = []
    receipt: Optional[Dict[str, str]] = None  # lake_snapshot_id, index_hash, evidence_set_hash
    error: Optional[Dict[str, Any]] = None


# ── Ingest ───────────────────────────────────────────────────

class LakeSpeakIngestRequest(BaseModel):
    """Ingest text into the LakeSpeak data lake."""
    text: str
    source_type: str = "text"       # "text" | "file" | "url" | "chat_export"
    source_path: Optional[str] = None


class LakeSpeakIngestResponse(BaseModel):
    """Response from a LakeSpeak ingest operation."""
    receipt_id: str = ""
    chunk_count: int = 0
    anchor_count: int = 0
    relation_count: int = 0
    error: Optional[Dict[str, Any]] = None


# ── Index Status ─────────────────────────────────────────────

class LakeSpeakStatusResponse(BaseModel):
    """Status of the LakeSpeak indexes and configuration."""
    version: str = ""
    enabled: bool = False
    bm25_doc_count: int = 0
    census_available: bool = False
    census_doc_count: int = 0
    config: Dict[str, Any] = {}
    error: Optional[Dict[str, Any]] = None


# ── Reindex ──────────────────────────────────────────────────

class LakeSpeakReindexResponse(BaseModel):
    """Response from a LakeSpeak reindex operation."""
    chunks_indexed: int = 0
    receipts_processed: int = 0
    error: Optional[Dict[str, Any]] = None
