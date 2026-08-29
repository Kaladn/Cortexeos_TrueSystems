"""Training Event Logger — append-only, daily-rotated, audit-grade JSONL.

Emits FROZEN training_event@1 records. Plugin #3 (LakeSpeak-Train) depends
on this exact structure. Do not change field names or nesting without bumping
the schema version.

Files rotate daily: training_events_{YYYY-MM-DD}.jsonl
Old files are immutable (append-only per day, then sealed).
All writes go through the gateway for audit trail.

Invariants (Plugin #3 contract):
  1. schema_version must equal "training_event@1" exactly
  2. Must always include query_text, requested_mode, retrieval.candidates, decision
  3. If retrieval.candidates is empty: decision.grounded must be false
  4. citations_emitted[] must match what was stored via Phase-1 intake
  5. index_hash and evidence_set_hash must be present even if candidates empty
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from lakespeak.schemas import TRAINING_EVENT_VERSION

logger = logging.getLogger(__name__)


class TrainingEventLogger:
    """Append-only JSONL writer with daily rotation.

    Uses gateway.append() when available, falls back to direct file I/O.
    """

    def __init__(self):
        self._gateway = None
        self._zone = None
        self._events_dir = None
        self._init_io()

    def _init_io(self) -> None:
        """Set up gateway or fallback I/O."""
        try:
            from security.gateway import gateway, WriteZone
            self._gateway = gateway
            self._zone = WriteZone.LAKESPEAK_EVENTS
        except ImportError:
            pass

        try:
            from security.data_paths import LAKESPEAK_EVENTS_DIR
            self._events_dir = LAKESPEAK_EVENTS_DIR
        except ImportError:
            pass

    def _today_filename(self) -> str:
        """Return today's event filename."""
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"training_events_{day}.jsonl"

    def _write_line(self, line: str) -> None:
        """Write a single JSONL line via gateway or fallback."""
        filename = self._today_filename()

        if self._gateway is not None and self._zone is not None:
            try:
                result = self._gateway.append(
                    caller="system",
                    zone=self._zone,
                    name=filename,
                    line=line,
                    encrypt=False,
                )
                if not getattr(result, "success", True):
                    logger.error("Training event gateway write failed: %s",
                                 getattr(result, "error", "unknown"))
            except Exception as e:
                logger.error("Training event gateway write error: %s", e)
                self._fallback_write(filename, line)
        else:
            self._fallback_write(filename, line)

    def _fallback_write(self, filename: str, line: str) -> None:
        """Direct file append when gateway is unavailable."""
        if self._events_dir is None:
            logger.error("No events directory configured — event dropped")
            return
        try:
            self._events_dir.mkdir(parents=True, exist_ok=True)
            filepath = self._events_dir / filename
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.error("Training event fallback write error: %s", e)

    # ── Low-level event writer ───────────────────────────────

    def log_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        query_id: Optional[str] = None,
        receipt_id: Optional[str] = None,
    ) -> str:
        """Log a generic training event. Returns event_id.

        For query events, prefer log_query_structured() which emits
        the frozen schema. This method is kept for ingest/reindex/feedback.
        """
        event_id = f"ev_{uuid.uuid4().hex[:16]}"

        event = {
            "schema_version": TRAINING_EVENT_VERSION,
            "event_id": event_id,
            "event_type": event_type,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "query_id": query_id,
            "receipt_id": receipt_id,
            "payload": payload,
        }

        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        self._write_line(line)
        return event_id

    # ── Frozen query event (Plugin #3 contract) ──────────────

    def log_query_structured(
        self,
        *,
        query_id: str,
        query_text: str,
        requested_mode: str,
        session_id: Optional[str] = None,
        user_id: str = "human",
        # Grounding policy
        grounded_required: bool = True,
        min_score: float = 0.1,
        topk: int = 8,
        # Lexicon probe
        lexicon_present: List[str],
        lexicon_absent: List[str],
        lexicon_version: str = "",
        probe_ms: int = 0,
        # Retrieval
        lake_snapshot_id: str = "snapshot_none",
        index_hash: str = "",
        retrieval_ms: int = 0,
        bm25_enabled: bool = True,
        bm25_hits: int = 0,
        dense_enabled: bool = False,
        dense_hits: int = 0,
        dense_model: Optional[str] = None,
        candidates: List[Dict[str, Any]] = None,
        evidence_set_hash: str = "",
        # Rerank
        anchor_rerank_enabled: bool = False,
        anchors_used: List[str] = None,
        rerank_ms: int = 0,
        final_topk: List[Dict[str, Any]] = None,
        # Decision
        grounded: bool = False,
        refused: bool = False,
        refusal_reason: Optional[str] = None,
        suggested_next_mode: Optional[str] = None,
        # Model (for future LLM-enhanced modes)
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        model_hash: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        # Output
        answer_text: str = "",
        answer_hash: str = "",
        citations_emitted: List[Dict[str, Any]] = None,
        # Timing
        total_ms: int = 0,
    ) -> str:
        """Log a FROZEN training_event@1 query record.

        This is the exact structure Plugin #3 (LakeSpeak-Train) reads.
        Do not add/remove/rename fields without bumping schema_version.
        """
        event_id = f"ev_{uuid.uuid4().hex[:16]}"

        event = {
            "schema_version": TRAINING_EVENT_VERSION,
            "event_id": event_id,
            "event_type": "query",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "user_id": user_id,

            "query_id": query_id,
            "query_text": query_text,
            "requested_mode": requested_mode,

            "grounding_policy": {
                "grounded_required": grounded_required,
                "min_score": min_score,
                "topk": topk,
            },

            "lexicon_probe": {
                "present": lexicon_present,
                "absent": lexicon_absent,
                "version": lexicon_version,
                "probe_ms": probe_ms,
            },

            "retrieval": {
                "lake_snapshot_id": lake_snapshot_id,
                "index_hash": index_hash,
                "retrieval_ms": retrieval_ms,
                "bm25": {
                    "enabled": bm25_enabled,
                    "hits": bm25_hits,
                },
                "dense": {
                    "enabled": dense_enabled,
                    "hits": dense_hits,
                    "embed_model": dense_model,
                },
                "candidates": candidates or [],
                "evidence_set_hash": evidence_set_hash,
            },

            "rerank": {
                "anchor_rerank_enabled": anchor_rerank_enabled,
                "anchors_used": anchors_used or [],
                "rerank_ms": rerank_ms,
                "final_topk": final_topk or [],
            },

            "decision": {
                "grounded": grounded,
                "refused": refused,
                "refusal_reason": refusal_reason,
                "suggested_next_mode": suggested_next_mode,
            },

            "model": {
                "provider": model_provider,
                "model_name": model_name,
                "model_hash": model_hash,
                "temperature": temperature,
                "top_p": top_p,
            },

            "output": {
                "answer_text": answer_text,
                "answer_hash": answer_hash,
                "citations_emitted": citations_emitted or [],
            },

            "timing": {
                "total_ms": total_ms,
            },
        }

        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        self._write_line(line)
        return event_id

    # ── Convenience methods (non-query events) ───────────────

    def log_query(
        self,
        query: str,
        mode: str,
        lexicon_present: List[str],
        lexicon_absent: List[str],
        candidates: List[Dict[str, Any]],
        chosen: List[str],
        response_text: str,
        citations: List[Dict[str, Any]],
        verdict: str,
        verdict_reasons: List[str],
        refused: bool,
        model_identity: Optional[str] = None,
        session_id: Optional[str] = None,
        query_id: Optional[str] = None,
    ) -> str:
        """Legacy log_query — kept for backward compat.

        New code should use log_query_structured() for frozen schema.
        """
        return self.log_event(
            event_type="query",
            payload={
                "query": query,
                "mode": mode,
                "lexicon_present": lexicon_present,
                "lexicon_absent": lexicon_absent,
                "candidates": candidates,
                "chosen": chosen,
                "response_text": response_text,
                "citations": citations,
                "verdict": verdict,
                "verdict_reasons": verdict_reasons,
                "refused": refused,
                "model_identity": model_identity,
            },
            session_id=session_id,
            query_id=query_id,
        )

    def log_ingest(self, receipt: Dict[str, Any]) -> str:
        """Log an ingest event from a receipt."""
        return self.log_event(
            event_type="ingest",
            payload={
                "source_type": receipt.get("source_type", ""),
                "chunk_count": receipt.get("chunk_count", 0),
                "anchor_count": receipt.get("anchor_count", 0),
                "relation_count": receipt.get("relation_count", 0),
                "source_hash": receipt.get("source_hash", ""),
            },
            receipt_id=receipt.get("receipt_id"),
        )

    def log_reindex(self, stats: Dict[str, Any]) -> str:
        """Log a reindex event."""
        return self.log_event(
            event_type="reindex",
            payload=stats,
        )
