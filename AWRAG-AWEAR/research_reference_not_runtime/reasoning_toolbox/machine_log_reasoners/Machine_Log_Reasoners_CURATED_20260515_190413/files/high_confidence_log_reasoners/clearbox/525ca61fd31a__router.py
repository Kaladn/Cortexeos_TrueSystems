"""LakeSpeak API Router — FastAPI endpoints for retrieval-augmented grounding.

Mounted on the bridge server at /api/lakespeak.
All imports are lazy — bridge server boots fine even if LakeSpeak deps are missing.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Optional

from fastapi import APIRouter

from lakespeak.api.models import (
    LakeSpeakQueryRequest,
    LakeSpeakQueryResponse,
    LakeSpeakIngestRequest,
    LakeSpeakIngestResponse,
    LakeSpeakStatusResponse,
    LakeSpeakReindexResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lakespeak", tags=["lakespeak"])

# ── Singleton Engine ─────────────────────────────────────────

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """Get or create the LakeSpeakEngine singleton.

    Lazy-loaded: heavy deps only imported on first call.
    Thread-safe via double-checked locking.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from lakespeak.retrieval.query import LakeSpeakEngine
                _engine = LakeSpeakEngine()
    return _engine


# ── Query Endpoint ───────────────────────────────────────────

@router.post("/query", response_model=LakeSpeakQueryResponse)
async def lakespeak_query(req: LakeSpeakQueryRequest):
    """Query the LakeSpeak retrieval pipeline.

    Runs the full pipeline: retrieve → rerank → quality gate → policy → respond.
    """
    if not req.query.strip():
        return LakeSpeakQueryResponse(
            mode=req.mode,
            error={"type": "bad_request", "message": "Empty query"},
        )

    try:
        engine = get_engine()
        result = await asyncio.to_thread(
            engine.query,
            query=req.query,
            mode=req.mode,
            topk=req.topk,
            session_id=req.session_id,
        )
        return LakeSpeakQueryResponse(
            mode=req.mode,
            source="lakespeak",
            response=result.answer_text,
            grounded=result.grounded,
            refused=result.refused,
            refusal_reason=result.refusal_reason,
            citations=result.citations,
            reasoning_trace=result.trace,
            verdict=result.verdict,
            verdict_reasons=result.verdict_reasons,
            suggested_next_mode=result.suggested_next_mode,
            caveats=result.caveats,
            receipt=result.receipt,
        )
    except Exception as e:
        logger.error("LakeSpeak query error: %s", e, exc_info=True)
        return LakeSpeakQueryResponse(
            mode=req.mode,
            error={"type": "lakespeak_error", "message": str(e)},
        )


# ── Ingest Endpoint ──────────────────────────────────────────

@router.post("/ingest", response_model=LakeSpeakIngestResponse)
async def lakespeak_ingest(req: LakeSpeakIngestRequest):
    """Ingest text into the LakeSpeak data lake.

    Creates chunks, extracts anchors/relations, stores, and returns receipt.
    """
    if not req.text.strip():
        return LakeSpeakIngestResponse(
            error={"type": "bad_request", "message": "Empty text"},
        )

    try:
        from lakespeak.ingest.pipeline import ingest_text

        engine = get_engine()
        bridge = engine._ensure_bridge()

        receipt = await asyncio.to_thread(
            ingest_text,
            text=req.text,
            source_type=req.source_type,
            source_path=req.source_path,
            bridge=bridge,
        )

        if receipt.get("status") == "blocked":
            return LakeSpeakIngestResponse(
                error={"type": "blocked", "message": receipt.get("reason", "Document blocked from ingestion")},
            )

        return LakeSpeakIngestResponse(
            receipt_id=receipt.get("receipt_id", ""),
            chunk_count=receipt.get("chunk_count", 0),
            anchor_count=receipt.get("anchor_count", 0),
            relation_count=receipt.get("relation_count", 0),
        )
    except Exception as e:
        logger.error("LakeSpeak ingest error: %s", e, exc_info=True)
        return LakeSpeakIngestResponse(
            error={"type": "ingest_error", "message": str(e)},
        )


# ── Reindex Endpoint ─────────────────────────────────────────

@router.post("/reindex", response_model=LakeSpeakReindexResponse)
async def lakespeak_reindex():
    """Rebuild the BM25 index from all stored chunks."""
    try:
        engine = get_engine()
        stats = await asyncio.to_thread(engine.reindex)

        if "error" in stats:
            return LakeSpeakReindexResponse(
                error={"type": "reindex_error", "message": stats["error"]},
            )

        return LakeSpeakReindexResponse(
            chunks_indexed=stats.get("chunks_indexed", 0),
            receipts_processed=stats.get("receipts_processed", 0),
        )
    except Exception as e:
        logger.error("LakeSpeak reindex error: %s", e, exc_info=True)
        return LakeSpeakReindexResponse(
            error={"type": "reindex_error", "message": str(e)},
        )


# ── Status Endpoint ──────────────────────────────────────────

@router.get("/status", response_model=LakeSpeakStatusResponse)
async def lakespeak_status():
    """Get LakeSpeak system status."""
    try:
        from lakespeak import VERSION
        from lakespeak.config import load_config

        config = load_config()
        engine = get_engine()
        bm25 = engine._ensure_bm25()

        # Check dense index availability
        from lakespeak.index.dense import DenseIndex
        dense_avail = DenseIndex.is_available()
        dense_count = 0
        if dense_avail:
            try:
                dense = engine._ensure_dense()
                if dense:
                    dense_count = dense.doc_count
            except Exception:
                pass

        return LakeSpeakStatusResponse(
            version=VERSION,
            enabled=config.get("enabled", True),
            bm25_doc_count=bm25.doc_count,
            dense_available=dense_avail,
            dense_doc_count=dense_count,
            config=config,
        )
    except Exception as e:
        logger.error("LakeSpeak status error: %s", e, exc_info=True)
        return LakeSpeakStatusResponse(
            error={"type": "status_error", "message": str(e)},
        )
