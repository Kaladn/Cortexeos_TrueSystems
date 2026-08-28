"""Wolf Engine Plugin API Router — FastAPI endpoints.

This is the ONLY file the Forest AI bridge server imports from wolf_engine.
Exports: router (APIRouter), get_engine() (lazy singleton).

Prefix: /api/wolf (per handoff contract).
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from wolf_engine.api.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    CascadeRequest,
    EvidenceStartRequest,
    ExportRequest,
    IngestRequest,
    ModuleToggleRequest,
    QueryResponse,
    SessionStartRequest,
    StatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wolf", tags=["wolf_engine"])

# ── Singleton Engine ─────────────────────────────────────────

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """Get or create the WolfEngine singleton. Lazy-loaded, thread-safe."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from wolf_engine.core.engine import WolfEngine
                _engine = WolfEngine()
    return _engine


# ── Helper ───────────────────────────────────────────────────

def _version() -> str:
    try:
        from wolf_engine import VERSION
        return VERSION
    except (ImportError, AttributeError):
        return "0.0.0"


# ── Status (required by plugin guide) ────────────────────────

@router.get("/status", response_model=StatusResponse)
async def wolf_status():
    try:
        engine = get_engine()
        stats = engine.forge.stats()
        # Include module enabled state
        try:
            modules = {
                m["key"]: m["enabled"]
                for m in _get_registry().list_modules()
            }
        except Exception:
            modules = {}
        return StatusResponse(
            version=_version(),
            enabled=True,
            modules=modules,
            forge_symbols=stats.total_symbols,
            uptime_sec=round(time.time() - engine._start_time, 1),
        )
    except Exception as e:
        logger.error("Wolf Engine status error: %s", e, exc_info=True)
        return StatusResponse(error={"type": "status_error", "message": str(e)})


# ── Core Actions ─────────────────────────────────────────────

@router.post("/ingest")
async def wolf_ingest(req: IngestRequest):
    if not req.text:
        return JSONResponse({"error": "Missing 'text' field"}, status_code=400)
    try:
        engine = get_engine()
        result = await asyncio.to_thread(
            engine.perceive_and_ingest, req.text, req.session_id
        )
        return result
    except Exception as e:
        logger.error("Wolf Engine ingest error: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/analyze", response_model=AnalyzeResponse)
async def wolf_analyze(req: AnalyzeRequest):
    """Run governed analysis. Returns handoff-contract shape."""
    try:
        engine = get_engine()
        raw = await asyncio.to_thread(
            engine.analyze, session_id=req.session_id, text=req.text
        )
        # Adapt internal format to handoff contract
        verdict = raw.get("verdict", {})
        return AnalyzeResponse(
            source="wolf_engine",
            summary=(
                f"Verdict: {verdict.get('status', 'unknown')} "
                f"(confidence: {verdict.get('adjusted_confidence', 0):.3f})"
            ),
            answer_frame=verdict,
            trace={
                "engine": raw.get("engine"),
                "patterns": raw.get("patterns"),
                "session_id": raw.get("session_id"),
            },
            citations=None,
        )
    except Exception as e:
        logger.error("Wolf Engine analyze error: %s", e, exc_info=True)
        return AnalyzeResponse(error={"type": "analyze_error", "message": str(e)})


@router.get("/query/{symbol_id}")
async def wolf_query(symbol_id: int):
    try:
        engine = get_engine()
        result = await asyncio.to_thread(engine.query_symbol, symbol_id)
        if result is None:
            return JSONResponse({"error": "Symbol not found"}, status_code=404)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/cascade")
async def wolf_cascade(req: CascadeRequest):
    try:
        engine = get_engine()
        result = await asyncio.to_thread(
            engine.trace_cascade, req.symbol_id, req.direction, req.max_depth
        )
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/symbols/top")
async def wolf_top_symbols(limit: int = Query(20)):
    try:
        engine = get_engine()
        return await asyncio.to_thread(engine.get_top_symbols, limit)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Monitoring ───────────────────────────────────────────────

@router.get("/snapshot")
async def wolf_snapshot():
    try:
        def _snapshot():
            engine = get_engine()
            return engine.get_system_snapshot()
        return await asyncio.to_thread(_snapshot)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/verdicts/recent")
async def wolf_verdicts_recent(limit: int = Query(20)):
    try:
        engine = get_engine()
        return await asyncio.to_thread(engine.verdict_store.get_recent, limit=limit)
    except Exception:
        return []


@router.get("/verdicts/counts")
async def wolf_verdicts_counts():
    try:
        engine = get_engine()
        return await asyncio.to_thread(engine.verdict_store.count_by_status)
    except Exception:
        return {}


@router.get("/verdicts/session/{session_id}")
async def wolf_verdicts_session(session_id: str):
    try:
        engine = get_engine()
        return await asyncio.to_thread(engine.verdict_store.get_by_session, session_id)
    except Exception:
        return []


@router.get("/sessions")
async def wolf_sessions():
    try:
        engine = get_engine()
        recent = await asyncio.to_thread(engine.verdict_store.get_recent, limit=200)
        sessions: dict[str, dict[str, Any]] = {}
        for v in recent:
            sid = v.get("session_id", "")
            if sid and sid not in sessions:
                sessions[sid] = {
                    "session_id": sid,
                    "last_verdict": v.get("timestamp", 0),
                    "last_status": v.get("status", ""),
                }
        return sorted(sessions.values(), key=lambda s: s["last_verdict"], reverse=True)
    except Exception:
        return []


# ── Debug ────────────────────────────────────────────────────

@router.post("/debug/push")
async def wolf_debug_push():
    try:
        engine = get_engine()
        return await asyncio.to_thread(engine.debug_push)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Session Recording ────────────────────────────────────────

@router.post("/session/start")
async def wolf_session_start(req: SessionStartRequest):
    try:
        engine = get_engine()
        result = await asyncio.to_thread(engine.start_recording, label=req.label)
        if "error" in result:
            return JSONResponse(result, status_code=409)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/session/stop")
async def wolf_session_stop():
    try:
        engine = get_engine()
        result = await asyncio.to_thread(engine.stop_recording)
        if "error" in result:
            return JSONResponse(result, status_code=404)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/session/status")
async def wolf_session_status():
    engine = get_engine()
    return engine.get_recording_status()


# ── Evidence Workers ─────────────────────────────────────────

@router.post("/evidence/start")
async def wolf_evidence_start(req: EvidenceStartRequest):
    try:
        engine = get_engine()
        result = await asyncio.to_thread(engine.start_evidence_workers, req.workers)
        if "error" in result:
            return JSONResponse(result, status_code=400)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/evidence/stop")
async def wolf_evidence_stop():
    try:
        engine = get_engine()
        return await asyncio.to_thread(engine.stop_evidence_workers)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/evidence/status")
async def wolf_evidence_status():
    engine = get_engine()
    return engine.get_evidence_status()


# ── Export + Reset ───────────────────────────────────────────

@router.get("/export")
async def wolf_export(what: str = Query("verdicts")):
    try:
        engine = get_engine()
        data = await asyncio.to_thread(engine.export_data, what)
        if isinstance(data, dict) and "error" in data:
            return JSONResponse(data, status_code=400)
        return data
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/reset")
async def wolf_reset():
    try:
        engine = get_engine()
        return await asyncio.to_thread(engine.reset_state)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Module Registry ──────────────────────────────────────────

_registry = None


def _get_registry():
    global _registry
    if _registry is None:
        from wolf_engine.config import load_config
        from wolf_engine.modules.registry import ModuleRegistry
        _registry = ModuleRegistry(config=load_config())
    return _registry


@router.get("/modules")
async def wolf_modules():
    """List all available modules with their enabled state."""
    try:
        return _get_registry().list_modules()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/modules/toggle")
async def wolf_modules_toggle(req: ModuleToggleRequest):
    """Toggle a module on/off."""
    try:
        result = _get_registry().toggle(req.key, req.enabled)
        if "error" in result:
            return JSONResponse(result, status_code=404)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
