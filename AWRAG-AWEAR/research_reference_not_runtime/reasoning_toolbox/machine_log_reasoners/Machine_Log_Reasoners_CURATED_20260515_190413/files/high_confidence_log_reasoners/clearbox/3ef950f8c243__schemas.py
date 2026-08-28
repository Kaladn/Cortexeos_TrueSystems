"""Pinned schema definitions for LakeSpeak v0.

All schemas are pure Python dataclasses — no external deps.
Schema versions are immutable: breaking change = new version string.

Schemas:
    chunk_ref@1         Stable chunk identity
    anchors@1           Per-chunk anchor records
    relations@1         Per-chunk relation edges
    reasoning_trace@1   Per-query execution trace + quality verdict
    ingest_receipt@1    Provenance record for ingested data
    training_event@1    Append-only training/audit event
    eval_report@1       Evaluation harness results
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Schema Version Constants ─────────────────────────────────

CHUNK_REF_VERSION        = "chunk_ref@1"
ANCHORS_VERSION          = "anchors@1"
RELATIONS_VERSION        = "relations@1"
REASONING_TRACE_VERSION  = "reasoning_trace@1"
INGEST_RECEIPT_VERSION   = "ingest_receipt@1"
TRAINING_EVENT_VERSION   = "training_event@1"
EVAL_REPORT_VERSION      = "eval_report@1"


# ── chunk_ref@1 ──────────────────────────────────────────────

@dataclass
class ChunkRef:
    """Stable chunk identity — deterministic, hashable, debuggable.

    chunk_id is derived as: ch_{sha256(receipt_id + ":" + str(ordinal))[:16]}
    This ensures the same source ingested twice produces identical chunk IDs.
    """
    schema_version: str = CHUNK_REF_VERSION
    chunk_id: str = ""              # "ch_{hash[:16]}" — deterministic
    receipt_id: str = ""            # Parent ingest receipt
    ordinal: int = 0                # Sequential position in source
    source_hash: str = ""           # SHA-256 of raw source text
    span_start: int = 0             # Character offset in source
    span_end: int = 0               # Character offset end
    text_hash: str = ""             # SHA-256 of this chunk's text
    token_count: int = 0
    text: str = ""                  # Raw chunk text


# ── anchors@1 ────────────────────────────────────────────────

@dataclass
class AnchorRecord:
    """One anchor token found in a chunk.

    Anchors are tokens that exist in the Forest lexicon,
    have len >= 3, and are not in the deterministic stop list.
    """
    token: str = ""                 # Normalized token
    hex_addr: str = ""              # Lexicon hex address
    symbol: Optional[str] = None    # Lexicon symbol (if assigned)
    position: int = 0               # Token offset in chunk
    frequency: int = 0              # Lexicon frequency


@dataclass
class ChunkAnchors:
    """All anchors for a single chunk."""
    schema_version: str = ANCHORS_VERSION
    chunk_id: str = ""
    receipt_id: str = ""
    anchor_count: int = 0
    anchors: List[AnchorRecord] = field(default_factory=list)
    anchor_counts: Dict[str, int] = field(default_factory=dict)   # {token: count_in_chunk}
    window_counts: Dict[str, int] = field(default_factory=dict)   # {token: num_windows_appeared_in}
    created_at_utc: str = ""


# ── relations@1 ──────────────────────────────────────────────

@dataclass
class RelationEdge:
    """A co-occurrence relation between two anchor tokens within a 6-1-6 window."""
    source_token: str = ""
    target_token: str = ""
    distance: int = 0               # 1-6
    direction: str = ""             # "before" | "after"
    co_occurrence_count: int = 0
    source_hex: str = ""
    target_hex: str = ""


@dataclass
class ChunkRelations:
    """All relations for a single chunk."""
    schema_version: str = RELATIONS_VERSION
    chunk_id: str = ""
    receipt_id: str = ""
    relation_count: int = 0
    relations: List[RelationEdge] = field(default_factory=list)
    created_at_utc: str = ""


# ── reasoning_trace@1 ────────────────────────────────────────

@dataclass
class ReasoningTrace:
    """Full trace of a LakeSpeak query execution.

    Includes retrieval stats, reranking details, and Quality Gate verdict.
    """
    schema_version: str = REASONING_TRACE_VERSION
    query_id: str = ""
    query_text: str = ""
    mode: str = ""                              # "grounded" | "allow_fallback"
    timestamp_utc: str = ""
    # Lexicon phase
    lexicon_present: List[str] = field(default_factory=list)
    lexicon_absent: List[str] = field(default_factory=list)
    # Retrieval phase
    bm25_hits: int = 0
    census_hits: int = 0
    hybrid_candidates: int = 0
    # Reranking phase
    anchors_used: List[str] = field(default_factory=list)
    anchor_boost_applied: bool = False
    final_topk: int = 0
    # Quality Gate verdict
    verdict: str = ""                           # "acceptable" | "trash"
    verdict_reasons: List[str] = field(default_factory=list)
    grounded: bool = False
    refusal_reason: Optional[str] = None
    suggested_next_mode: Optional[str] = None
    # Timing
    retrieval_ms: int = 0
    rerank_ms: int = 0
    gate_ms: int = 0
    total_ms: int = 0


# ── ingest_receipt@1 ─────────────────────────────────────────

@dataclass
class IngestReceipt:
    """Immutable provenance record for an ingested data source.

    receipt_id format: rcpt_{YYYYMMDD}_{HHMMSS}_{random_hex8}
    """
    schema_version: str = INGEST_RECEIPT_VERSION
    receipt_id: str = ""
    source_type: str = ""                       # "file" | "text" | "url" | "chat_export"
    source_path: Optional[str] = None
    source_hash: str = ""                       # "sha256:..."
    source_size_bytes: int = 0
    chunk_count: int = 0
    anchor_count: int = 0
    relation_count: int = 0
    lexicon_version: str = ""
    created_at_utc: str = ""
    created_by: str = ""                        # "system" | "human"


# ── training_event@1 ─────────────────────────────────────────

@dataclass
class TrainingEvent:
    """Single training/audit event (append-only JSONL).

    event_id format: ev_{uuid4_hex[:16]}
    """
    schema_version: str = TRAINING_EVENT_VERSION
    event_id: str = ""
    event_type: str = ""                        # "query" | "feedback" | "ingest" | "reindex"
    timestamp_utc: str = ""
    session_id: Optional[str] = None
    query_id: Optional[str] = None
    receipt_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


# ── eval_report@1 ────────────────────────────────────────────

@dataclass
class EvalReport:
    """Results of an evaluation run."""
    schema_version: str = EVAL_REPORT_VERSION
    report_id: str = ""
    created_at_utc: str = ""
    query_count: int = 0
    grounded_count: int = 0
    refused_count: int = 0
    fallback_count: int = 0
    avg_retrieval_ms: float = 0.0
    avg_topk_anchor_overlap: float = 0.0
    precision_at_k: Dict[str, float] = field(default_factory=dict)
    coverage: float = 0.0
    queries: List[Dict[str, Any]] = field(default_factory=list)


# ── Scored chunk (internal, used by retrieval pipeline) ──────

@dataclass
class ScoredChunk:
    """A retrieval candidate with its score."""
    chunk_id: str = ""
    receipt_id: str = ""
    score: float = 0.0
    source: str = ""                            # "bm25" | "census" | "hybrid" | "reranked"
    bm25_score: float = 0.0
    census_score: float = 0.0
    anchor_score: float = 0.0
