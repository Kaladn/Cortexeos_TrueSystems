"""System info, health, job management, cancel, and WebSocket stream routes."""
from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from bridges.state import BridgeState, VERSION
from bridges.models import CancelRequest
from bridges.services.system_control import SystemControlService
from bridges.services.system_info import SystemInfoService
from bridges.ws_manager import WebSocketManager


def make_router(
    state: BridgeState,
    ws_manager: WebSocketManager,
    metrics: dict,
    background_tasks: set,
    task_done_cb,
    base_dir: Path,
) -> APIRouter:
    """Create the system router."""
    router = APIRouter()

    system_control = SystemControlService(
        state=state,
        background_tasks=background_tasks,
        task_done_cb=task_done_cb,
        base_dir=base_dir,
    )
    system_info = SystemInfoService(
        state=state,
        ws_manager=ws_manager,
        metrics=metrics,
        base_dir=base_dir,
        version=VERSION,
    )

    # ── /api/metrics ────────────────────────────────────────────

    @router.get("/api/metrics")
    def api_metrics():
        return system_info.metrics_snapshot()

    # ── /api/stats ──────────────────────────────────────────────

    @router.get("/api/stats")
    async def get_stats():
        stats = await state.stats_snapshot()
        stats["version"] = VERSION
        return stats

    # ── /api/ollama/warmup ──────────────────────────────────────

    @router.post("/api/ollama/warmup")
    async def ollama_warmup():
        return await system_info.warmup_ollama()

    # ── /api/lookup ─────────────────────────────────────────────

    @router.get("/api/lookup")
    async def get_lookup(word: str):
        if not word:
            raise HTTPException(status_code=400, detail="word parameter is required")
        await state.ensure_bridge_loaded("lookup")
        result = state.bridge.lookup(word)
        result["version"] = VERSION
        return result

    # ── /api/cancel, /api/jobs ──────────────────────────────────

    @router.post("/api/cancel")
    async def post_cancel(body: CancelRequest):
        record = state.jobs.cancel(body.job_id)
        if not record:
            raise HTTPException(status_code=404, detail="Job not found")
        await ws_manager.broadcast({
            "evt": "job-cancel",
            "job_id": record.job_id,
            "job": record.job_type,
            "version": VERSION,
        })
        return {"status": record.status, "job_id": record.job_id, "version": VERSION}

    @router.get("/api/jobs")
    async def list_jobs():
        jobs = state.jobs.list_jobs()
        return {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "job": job.job_type,
                    "status": job.status,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "progress": job.progress,
                    "result_path": job.result_path,
                    "error": job.error,
                }
                for job in jobs
            ],
            "version": VERSION,
        }

    # ── /api/system ─────────────────────────────────────────────

    @router.get("/api/system")
    async def get_system_info():
        return await system_info.system_info()

    # ── /api/boot ───────────────────────────────────────────────

    @router.get("/api/boot")
    async def boot_payload():
        return await system_info.boot_payload()

    # ── /api/services/health ────────────────────────────────────

    @router.get("/api/services/health")
    async def services_health():
        """Probe all Clearbox AI Studio services and return combined health."""
        return await system_control.services_health()

    # ── /api/system/shutdown ─────────────────────────────────────

    @router.post("/api/system/shutdown")
    async def system_shutdown():
        """Shut down all Clearbox AI Studio services.

        Drops a sentinel file so the loop-based terminal scripts exit
        after the Python processes die → windows close automatically.
        """
        return await system_control.system_shutdown()

    # ── /api/system/restart ──────────────────────────────────────

    @router.post("/api/system/restart")
    async def system_restart():
        """Restart all Clearbox AI Studio services.

        Just kills the Python listeners. The loop-based terminal scripts
        detect the exit and relaunch the services in the SAME windows.
        No new windows, no clearbox_start.py needed.
        """
        return await system_control.system_restart()

    # ── /api/system/lock ─────────────────────────────────────────

    @router.post("/api/system/lock")
    async def system_lock():
        """Lock the Windows workstation (best-effort)."""
        return await system_control.system_lock()

    # ── /ws/stream WebSocket ─────────────────────────────────────

    @router.websocket("/ws/stream")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            # Network drop, ConnectionReset, etc. — clean up stale socket
            pass
        finally:
            await ws_manager.disconnect(websocket)

    return router
