"""netlog FastAPI router — mounts at /api/netlog on bridge port 5050."""

from __future__ import annotations
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wolf_engine.evidence.session_manager import EvidenceSessionManager
from wolf_engine.evidence.fusion import fuse_session
from netlog.api.models import SessionStartRequest, QueryRequest
from netlog.config import SESSIONS_DIR, NODE_ID

router = APIRouter(prefix="/api/netlog", tags=["netlog"])

_session_mgr: EvidenceSessionManager | None = None
_worker = None


def _get_session_mgr() -> EvidenceSessionManager:
    global _session_mgr
    if _session_mgr is None:
        _session_mgr = EvidenceSessionManager(str(SESSIONS_DIR), node_id=NODE_ID)
    return _session_mgr


@router.get("/status")
async def netlog_status() -> dict[str, Any]:
    mgr = _get_session_mgr()
    active = mgr.active_session
    return {
        "ok": True,
        "plugin": "netlog",
        "version": "0.1.0",
        "worker_running": _worker.is_running if _worker else False,
        "session_id": active.session_id if active else None,
        "event_count": active.event_count if active else 0,
        "ring_size": len(_worker.ring) if _worker else 0,
    }


@router.get("/health")
async def netlog_health() -> dict[str, Any]:
    return {"ok": True, "plugin": "netlog"}


@router.post("/session/start")
async def session_start(req: SessionStartRequest) -> dict[str, Any]:
    global _worker
    mgr = _get_session_mgr()
    if _worker and _worker.is_running:
        return JSONResponse({"ok": False, "error": "Session already running"}, 409)
    session = mgr.start(label=req.label or "netlog_session")
    from netlog.core.worker import NetlogWorker
    _worker = NetlogWorker(session_mgr=mgr)
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


@router.get("/connections/live")
async def live_connections(limit: int = 200) -> dict[str, Any]:
    """Return current ring buffer — all recent connection events."""
    if not _worker:
        return {"ok": False, "error": "Worker not running", "connections": []}
    ring = _worker.ring
    return {"ok": True, "total": len(ring), "connections": ring[-limit:]}


@router.get("/connections/alerts")
async def connection_alerts(limit: int = 100) -> dict[str, Any]:
    """Return only connections with non-empty alerts list."""
    if not _worker:
        return {"ok": False, "error": "Worker not running", "alerts": []}
    alerts = [c for c in _worker.ring if c.get("alerts")]
    return {"ok": True, "total": len(alerts), "alerts": alerts[-limit:]}


@router.post("/connections/query")
async def query_connections(req: QueryRequest) -> dict[str, Any]:
    """Filter ring buffer by proc name, raddr substring, or alert type."""
    if not _worker:
        return {"ok": False, "error": "Worker not running", "results": []}
    results = _worker.ring
    if req.proc:
        results = [c for c in results if req.proc.lower() in c.get("proc", "").lower()]
    if req.raddr_contains:
        results = [c for c in results if req.raddr_contains in (c.get("raddr") or "")]
    if req.alert_type:
        results = [c for c in results if req.alert_type in c.get("alerts", [])]
    return {"ok": True, "total": len(results), "results": results[-req.limit:]}


@router.get("/session/events")
async def session_events(limit: int = 200) -> dict[str, Any]:
    mgr = _get_session_mgr()
    active = mgr.active_session
    if not active:
        return {"ok": False, "error": "No active session", "events": []}
    events = fuse_session(active.session_dir)
    tail = [e.to_dict() for e in events[-limit:]]
    return {"ok": True, "session_id": active.session_id, "total": len(events), "events": tail}


@router.get("/help")
async def help_schema() -> dict[str, Any]:
    """Machine-readable API schema — usable by both AI and human."""
    return {
        "ok": True,
        "plugin": "netlog",
        "version": "0.1.0",
        "mount_prefix": "/api/netlog",
        "endpoints": {
            "GET /status": {
                "description": "Worker status, ring buffer size, event count",
                "params": {},
                "returns": "ok, plugin, version, worker_running, session_id, event_count, ring_size",
            },
            "GET /health": {
                "description": "Health check",
                "params": {},
                "returns": "ok, plugin",
            },
            "POST /session/start": {
                "description": "Start connection tracking session",
                "params": {"label": "str (optional)"},
                "returns": "ok, session_id, label",
            },
            "POST /session/stop": {
                "description": "Stop active tracking session",
                "params": {},
                "returns": "ok, events_emitted, session_id",
            },
            "GET /connections/live": {
                "description": "Current ring buffer — all recent connections",
                "params": {"limit": "int (default 200)"},
                "returns": "ok, total, connections[]",
            },
            "GET /connections/alerts": {
                "description": "Connections with non-empty alerts only",
                "params": {"limit": "int (default 100)"},
                "returns": "ok, total, alerts[]",
            },
            "POST /connections/query": {
                "description": "Filter ring buffer by proc, raddr, or alert type",
                "params": {"proc": "str (optional)", "raddr_contains": "str (optional)", "alert_type": "str (optional)", "limit": "int (default 100)"},
                "returns": "ok, total, results[]",
            },
            "GET /session/events": {
                "description": "JSONL events from active session",
                "params": {"limit": "int (default 200)"},
                "returns": "ok, session_id, total, events[]",
            },
            "GET /help": {
                "description": "This endpoint — machine-readable API schema",
                "params": {},
                "returns": "this object",
            },
        },
        "hooks": {
            "plugin_post": "Surfaces SUSPICIOUS_PORT and HIGH_CONNECTION_COUNT alerts into chat",
        },
        "alert_types": [
            "SUSPICIOUS_PORT",
            "NEW_PROCESS_CONNECTION",
            "HIGH_CONNECTION_COUNT",
        ],
        "requires": ["psutil"],
        "optional": ["scapy"],
    }


# ── plugin_post hook ───────────────────────────────────────────────────────────
async def plugin_post(ctx: dict) -> dict:
    """Surface suspicious port or high-connection-count alerts into chat contributions."""
    if not _worker:
        return ctx
    hot_alerts = [c for c in _worker.ring[-50:]
                  if any(a in c.get("alerts", []) for a in
                         ("SUSPICIOUS_PORT", "HIGH_CONNECTION_COUNT"))]
    if hot_alerts:
        contributions = ctx.setdefault("contributions", [])
        contributions.append({
            "source": "netlog",
            "type": "network_alert",
            "alert_count": len(hot_alerts),
            "sample": hot_alerts[-3:],
        })
    return ctx
