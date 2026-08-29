"""visual_io FastAPI router — mounts at /api/visual_io on bridge port 5050."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from visual_io.api.models import SessionStartRequest, ConfigUpdateRequest
from visual_io.config import SESSIONS_DIR, NODE_ID, DEFAULT_FPS, GRID_SIZE
from visual_io.core.operators import VectorOperator, EntropyOperator

router = APIRouter(prefix="/api/visual_io", tags=["visual_io"])

# ── Singletons ────────────────────────────────────────────────
_session_mgr = None
_worker = None
_operators: list = [VectorOperator(), EntropyOperator()]


def _get_session_mgr():
    global _session_mgr
    if _session_mgr is None:
        from wolf_engine.evidence.session_manager import EvidenceSessionManager
        _session_mgr = EvidenceSessionManager(str(SESSIONS_DIR), node_id=NODE_ID)
    return _session_mgr


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/status")
async def visual_io_status() -> dict[str, Any]:
    mgr = _get_session_mgr()
    active = mgr.active_session
    return {
        "ok": True,
        "plugin": "visual_io",
        "version": "0.1.0",
        "worker_running": _worker.is_running if _worker else False,
        "session_id": active.session_id if active else None,
        "event_count": active.event_count if active else 0,
        "latest_frame_id": _worker.latest_state.get("frame_id") if _worker and _worker.latest_state else None,
    }


@router.get("/health")
async def visual_io_health() -> dict[str, Any]:
    return {"ok": True, "plugin": "visual_io"}


@router.post("/session/start")
async def session_start(req: SessionStartRequest) -> dict[str, Any]:
    global _worker
    mgr = _get_session_mgr()
    if _worker and _worker.is_running:
        return JSONResponse({"ok": False, "error": "Session already running"}, 409)
    session = mgr.start(label=req.label or "visual_io_session")
    from visual_io.core.worker import VisualWorker
    _worker = VisualWorker(
        session_mgr=mgr,
        fps=req.fps,
        grid_size=req.grid_size,
        capture_region=req.capture_region,
    )
    _worker.start()
    return {"ok": True, "session_id": session.session_id, "label": session.label}


@router.post("/session/stop")
async def session_stop() -> dict[str, Any]:
    global _worker
    if not _worker or not _worker.is_running:
        return {"ok": False, "error": "No active session"}
    count = _worker.stop()
    mgr = _get_session_mgr()
    info = mgr.stop()
    _worker = None
    return {"ok": True, "events_emitted": count,
            "session_id": info.session_id if info else None}


@router.get("/session/events")
async def session_events(limit: int = 50) -> dict[str, Any]:
    mgr = _get_session_mgr()
    active = mgr.active_session
    if not active:
        return {"ok": False, "error": "No active session", "events": []}
    from wolf_engine.evidence.fusion import fuse_session
    events = fuse_session(active.session_dir)
    tail = [e.to_dict() for e in events[-limit:]]
    return {"ok": True, "session_id": active.session_id, "total": len(events), "events": tail}


@router.get("/frame/latest")
async def frame_latest() -> dict[str, Any]:
    if not _worker or not _worker.latest_state:
        return {"ok": False, "error": "No frame captured yet"}
    return {"ok": True, "state": _worker.latest_state}


@router.get("/operators")
async def list_operators() -> dict[str, Any]:
    return {"ok": True, "operators": [op.info() for op in _operators]}


@router.get("/help")
async def help_schema() -> dict[str, Any]:
    """Machine-readable API schema — usable by both AI and human."""
    return {
        "ok": True,
        "plugin": "visual_io",
        "version": "0.1.0",
        "mount_prefix": "/api/visual_io",
        "endpoints": {
            "GET /status": {
                "description": "Worker status, event count, latest frame ID",
                "params": {},
                "returns": "ok, plugin, version, worker_running, session_id, event_count, latest_frame_id",
            },
            "GET /health": {
                "description": "Health check",
                "params": {},
                "returns": "ok, plugin",
            },
            "POST /session/start": {
                "description": "Start screen capture session",
                "params": {"label": "str (optional)", "fps": "float (default 2.0)", "grid_size": "int (default 32)", "capture_region": "dict|null (optional)"},
                "returns": "ok, session_id, label",
            },
            "POST /session/stop": {
                "description": "Stop active capture session",
                "params": {},
                "returns": "ok, events_emitted, session_id",
            },
            "GET /session/events": {
                "description": "Retrieve JSONL events from active session",
                "params": {"limit": "int (default 50)"},
                "returns": "ok, session_id, total, events[]",
            },
            "GET /frame/latest": {
                "description": "Most recent ScreenVectorState",
                "params": {},
                "returns": "ok, state{frame_id, grid, core_block, sectors, ray_vectors, anomaly_metrics}",
            },
            "GET /operators": {
                "description": "List registered operators",
                "params": {},
                "returns": "ok, operators[{key, name, category, description}]",
            },
            "GET /help": {
                "description": "This endpoint — machine-readable API schema",
                "params": {},
                "returns": "this object",
            },
        },
        "hooks": {
            "plugin_post": "Injects visual anomaly flags into chat contributions",
        },
        "config": {
            "default_fps": 2.0,
            "grid_size": 32,
            "palette": "0-9 discrete (ARC-style)",
        },
        "requires": ["numpy", "mss"],
    }


# ── plugin_post hook — annotates chat context with latest visual state ────────
async def plugin_post(ctx: dict) -> dict:
    """
    Inject latest ScreenVectorState summary into chat response contributions
    if visual_io is running. Passive — only adds context, never blocks.
    """
    if not _worker or not _worker.is_running or not _worker.latest_state:
        return ctx
    state = _worker.latest_state
    flags = state.get("anomaly_metrics", {}).get("anomaly_flags", [])
    if flags:
        contributions = ctx.setdefault("contributions", [])
        contributions.append({
            "source": "visual_io",
            "type": "visual_anomaly",
            "frame_id": state.get("frame_id"),
            "flags": flags,
            "entropy": state.get("anomaly_metrics", {}).get("global_entropy"),
        })
    return ctx
