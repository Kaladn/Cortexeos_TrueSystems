"""
System Pulse Plugin — FastAPI Router
Prefix: /api/system-pulse
"""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from .models import HistoryResponse, SnapshotResponse, StatusResponse

router = APIRouter(prefix="/api/system-pulse", tags=["system_pulse"])

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from system_pulse.core.engine import SystemPulseEngine
                _engine = SystemPulseEngine()
    return _engine


@router.get("/ui", include_in_schema=False)
async def serve_ui():
    ui = Path(__file__).parent.parent / "_preview_ui.html"
    if ui.exists():
        return FileResponse(str(ui), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="UI not found")


@router.get("/status", response_model=StatusResponse)
async def status():
    eng = get_engine()
    s = await asyncio.to_thread(eng.status)
    return StatusResponse(**s)


@router.get("/snapshot", response_model=SnapshotResponse, summary="Full system snapshot")
async def snapshot():
    eng = get_engine()
    snap = await asyncio.to_thread(eng.snapshot)
    return SnapshotResponse(ok=True, **snap)


@router.get("/history", response_model=HistoryResponse, summary="CPU/RAM history (last 2 min)")
async def history():
    eng = get_engine()
    pts = await asyncio.to_thread(eng.history)
    return HistoryResponse(ok=True, points=pts)
