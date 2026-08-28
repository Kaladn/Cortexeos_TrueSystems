"""audio_io FastAPI router — mounts at /api/audio_io on bridge port 5050."""

from __future__ import annotations
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wolf_engine.evidence.session_manager import EvidenceSessionManager
from wolf_engine.evidence.fusion import fuse_session
from audio_io.api.models import SessionStartRequest
from audio_io.config import SESSIONS_DIR, NODE_ID, DEVICE_INDEX
from audio_io.core.operators import FootstepDirectionOperator, SoundClassifierOperator

router = APIRouter(prefix="/api/audio_io", tags=["audio_io"])

_session_mgr: EvidenceSessionManager | None = None
_worker = None
_operators = [FootstepDirectionOperator(), SoundClassifierOperator()]


def _get_session_mgr() -> EvidenceSessionManager:
    global _session_mgr
    if _session_mgr is None:
        _session_mgr = EvidenceSessionManager(str(SESSIONS_DIR), node_id=NODE_ID)
    return _session_mgr


@router.get("/status")
async def audio_io_status() -> dict[str, Any]:
    mgr = _get_session_mgr()
    active = mgr.active_session
    return {
        "ok": True,
        "plugin": "audio_io",
        "version": "0.1.0",
        "worker_running": _worker.is_running if _worker else False,
        "session_id": active.session_id if active else None,
        "event_count": active.event_count if active else 0,
    }


@router.get("/health")
async def audio_io_health() -> dict[str, Any]:
    return {"ok": True, "plugin": "audio_io"}


@router.post("/session/start")
async def session_start(req: SessionStartRequest) -> dict[str, Any]:
    global _worker
    mgr = _get_session_mgr()
    if _worker and _worker.is_running:
        return JSONResponse({"ok": False, "error": "Session already running"}, 409)
    session = mgr.start(label=req.label or "audio_io_session")
    from audio_io.core.worker import AudioWorker
    _worker = AudioWorker(session_mgr=mgr, device_index=req.device_index)
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
    events = fuse_session(active.session_dir)
    tail = [e.to_dict() for e in events[-limit:]]
    return {"ok": True, "session_id": active.session_id, "total": len(events), "events": tail}


@router.get("/latest")
async def latest_event() -> dict[str, Any]:
    if not _worker or not _worker.latest_event:
        return {"ok": False, "error": "No event captured yet"}
    return {"ok": True, "event": _worker.latest_event}


@router.get("/operators")
async def list_operators() -> dict[str, Any]:
    return {"ok": True, "operators": [op.info() for op in _operators]}


@router.get("/help")
async def help_schema() -> dict[str, Any]:
    """Machine-readable API schema — usable by both AI and human."""
    return {
        "ok": True,
        "plugin": "audio_io",
        "version": "0.1.0",
        "mount_prefix": "/api/audio_io",
        "endpoints": {
            "GET /status": {
                "description": "Worker status, session info, event count",
                "params": {},
                "returns": "ok, plugin, version, worker_running, session_id, event_count",
            },
            "GET /health": {
                "description": "Health check",
                "params": {},
                "returns": "ok, plugin",
            },
            "POST /session/start": {
                "description": "Start live audio capture session",
                "params": {"label": "str (optional)", "device_index": "int|null (optional)"},
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
            "GET /latest": {
                "description": "Most recent captured audio event",
                "params": {},
                "returns": "ok, event{event_type, sound_type, duration_ms, direction_deg, rms, centroid, zcr, mfcc[]}",
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
            "plugin_post": "Injects gunshot/hitmarker/footstep detections into chat contributions",
        },
        "config": {
            "sample_rate": 44100,
            "channels": 2,
            "chunk_samples": 4096,
            "n_mfcc": 13,
            "sound_types": ["footstep", "gunshot", "hitmarker", "speech", "misc"],
        },
        "requires": ["numpy", "sounddevice", "librosa"],
    }


# ── plugin_post hook ───────────────────────────────────────────────────────────
async def plugin_post(ctx: dict) -> dict:
    """Inject latest audio classification into chat contributions if relevant."""
    if not _worker or not _worker.is_running or not _worker.latest_event:
        return ctx
    ev = _worker.latest_event
    stype = ev.get("sound_type", "misc")
    if stype in ("gunshot", "hitmarker", "footstep"):
        contributions = ctx.setdefault("contributions", [])
        contributions.append({
            "source": "audio_io",
            "type": "audio_detection",
            "sound_type": stype,
            "direction_deg": ev.get("direction_deg"),
            "rms": ev.get("rms"),
        })
    return ctx
