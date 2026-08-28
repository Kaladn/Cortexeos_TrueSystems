"""
OpenRefine Plugin — FastAPI Router
Prefix: /api/openrefine
All heavy work deferred to asyncio.to_thread() via the engine.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse

from .models import (
    ApplyOperationsRequest,
    ApplyOperationsResponse,
    ClusterResponse,
    CreateProjectRequest,
    CreateProjectResponse,
    DeleteProjectResponse,
    ExportRequest,
    ExpressionPreviewRequest,
    ExpressionPreviewResponse,
    GetRowsResponse,
    ListProjectsResponse,
    OpenRefineStatusResponse,
    ProjectDetailResponse,
    StartResponse,
    StopResponse,
    UpdateConfigRequest,
    UpdateConfigResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/openrefine", tags=["openrefine"])

# ── Singleton engine ──────────────────────────────────────────────────────────
_engine = None
_engine_lock = threading.Lock()


def get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from openrefine.core.engine import OpenRefineEngine
                _engine = OpenRefineEngine()
    return _engine


# ── UI serving ────────────────────────────────────────────────────────────────
@router.get("/ui", include_in_schema=False)
async def serve_ui():
    """Serve the full OpenRefine control panel."""
    ui_path = Path(__file__).parent.parent / "_preview_ui.html"
    if ui_path.exists():
        return FileResponse(str(ui_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="UI file not found")


# ── Status / Health ───────────────────────────────────────────────────────────
@router.get("/status", response_model=OpenRefineStatusResponse, summary="Plugin + OpenRefine health")
async def status():
    eng = get_engine()
    s = await asyncio.to_thread(eng.status)
    return OpenRefineStatusResponse(
        ok=s["ok"],
        message="OpenRefine is running" if s["running"] else "OpenRefine is stopped",
        running=s["running"],
        or_version=s["or_version"],
        or_host=s["or_host"],
        or_port=s["or_port"],
        install_dir=s["install_dir"],
        workspace_dir=s["workspace_dir"],
        project_count=s["project_count"],
        version="0.1.0",
    )


# ── Process control ───────────────────────────────────────────────────────────
@router.post("/start", response_model=StartResponse, summary="Launch OpenRefine")
async def start():
    eng = get_engine()
    s = await asyncio.to_thread(eng.start)
    return StartResponse(
        ok=s.get("ok", False),
        message=s.get("message", ""),
        pid=s.get("pid"),
        or_port=s.get("or_port", eng.port),
        startup_ms=s.get("startup_ms", 0),
        error=s.get("error"),
    )


@router.post("/stop", response_model=StopResponse, summary="Stop OpenRefine")
async def stop():
    eng = get_engine()
    s = await asyncio.to_thread(eng.stop)
    return StopResponse(ok=s.get("ok", False), message=s.get("message", ""), pid=s.get("pid"), error=s.get("error"))


# ── Projects ──────────────────────────────────────────────────────────────────
@router.get("/projects", response_model=ListProjectsResponse, summary="List all projects")
async def list_projects():
    eng = get_engine()
    result = await asyncio.to_thread(eng.list_projects)
    return ListProjectsResponse(
        ok=result["ok"],
        message=result.get("message", ""),
        projects=result.get("projects", []),
        error=result.get("error"),
    )


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse, summary="Project metadata + columns")
async def get_project(project_id: str):
    eng = get_engine()
    result = await asyncio.to_thread(eng.get_project, project_id)
    return ProjectDetailResponse(
        ok=result["ok"],
        message=result.get("message", ""),
        project=result.get("project"),
        columns=result.get("columns", []),
        key_column=result.get("key_column", ""),
        total_rows=result.get("total_rows", 0),
        error=result.get("error"),
    )


@router.post("/projects", response_model=CreateProjectResponse, summary="Create project from CSV/JSON text")
async def create_project(req: CreateProjectRequest):
    eng = get_engine()
    if req.data:
        result = await asyncio.to_thread(eng.create_project_from_text, req.name, req.data, req.format)
    elif req.url:
        return CreateProjectResponse(ok=False, message="URL import not yet implemented — paste CSV/JSON data directly.")
    else:
        return CreateProjectResponse(ok=False, message="Provide either 'data' (inline text) or 'url'.")
    return CreateProjectResponse(
        ok=result["ok"],
        message=result.get("message", ""),
        project_id=result.get("project_id", ""),
        project_name=result.get("project_name", req.name),
        error=result.get("error"),
    )


@router.delete("/projects/{project_id}", response_model=DeleteProjectResponse, summary="Delete a project")
async def delete_project(project_id: str):
    eng = get_engine()
    result = await asyncio.to_thread(eng.delete_project, project_id)
    return DeleteProjectResponse(
        ok=result["ok"],
        message=result.get("message", ""),
        project_id=project_id,
        error=result.get("error"),
    )


# ── Rows ──────────────────────────────────────────────────────────────────────
@router.get("/projects/{project_id}/rows", response_model=GetRowsResponse, summary="Paginated rows")
async def get_rows(
    project_id: str,
    start: int = Query(default=0, ge=0, description="Row offset"),
    limit: int = Query(default=50, ge=1, le=500, description="Max rows"),
):
    eng = get_engine()
    result = await asyncio.to_thread(eng.get_rows, project_id, start, limit)
    return GetRowsResponse(
        ok=result["ok"],
        message=result.get("message", ""),
        rows=result.get("rows", []),
        start=result.get("start", start),
        limit=result.get("limit", limit),
        total=result.get("total", 0),
        filtered=result.get("filtered", 0),
        error=result.get("error"),
    )


# ── Operations ────────────────────────────────────────────────────────────────
@router.post("/projects/{project_id}/operations", response_model=ApplyOperationsResponse, summary="Apply GREL operations")
async def apply_operations(project_id: str, req: ApplyOperationsRequest):
    eng = get_engine()
    result = await asyncio.to_thread(eng.apply_operations, project_id, req.operations)
    return ApplyOperationsResponse(
        ok=result["ok"],
        message=result.get("message", ""),
        history_entry_id=result.get("history_entry_id"),
        operations_applied=result.get("operations_applied", 0),
        error=result.get("error"),
    )


@router.post("/expression-preview", response_model=ExpressionPreviewResponse, summary="Preview GREL expression")
async def preview_expression(req: ExpressionPreviewRequest):
    eng = get_engine()
    result = await asyncio.to_thread(eng.preview_expression, req.project_id, req.column_name, req.expression, req.language)
    return ExpressionPreviewResponse(
        ok=result["ok"],
        results=result.get("results", []),
        error=result.get("error"),
    )


# ── Export ────────────────────────────────────────────────────────────────────
@router.get("/projects/{project_id}/export", summary="Export project data (csv/tsv/xlsx/html/json)")
async def export_project(
    project_id: str,
    format: str = Query(default="csv", description="Export format"),
):
    eng = get_engine()
    content, content_type = await asyncio.to_thread(eng.export_rows, project_id, format)

    filename_map = {
        "csv": f"project_{project_id}.csv",
        "tsv": f"project_{project_id}.tsv",
        "xlsx": f"project_{project_id}.xlsx",
        "html": f"project_{project_id}.html",
        "json": f"project_{project_id}.json",
    }
    filename = filename_map.get(format, f"project_{project_id}.dat")

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Clustering ────────────────────────────────────────────────────────────────
@router.get("/projects/{project_id}/clusters", response_model=ClusterResponse, summary="Compute clusters for a column")
async def compute_clusters(
    project_id: str,
    column: str = Query(..., description="Column name to cluster"),
    method: str = Query(default="binning", description="Clustering method"),
    keyer: str = Query(default="fingerprint", description="Keying function"),
):
    eng = get_engine()
    result = await asyncio.to_thread(eng.compute_clusters, project_id, column, method, keyer)
    return ClusterResponse(
        ok=result["ok"],
        column_name=result.get("column_name", column),
        method=result.get("method", method),
        clusters=result.get("clusters", []),
        error=result.get("error"),
    )


# ── Live config ───────────────────────────────────────────────────────────────
@router.patch("/config", response_model=UpdateConfigResponse, summary="Update runtime config (port, memory, install dir)")
async def update_config(req: UpdateConfigRequest):
    eng = get_engine()
    result = await asyncio.to_thread(eng.update_config, req.port, req.memory_mb, req.install_dir)
    return UpdateConfigResponse(
        ok=result["ok"],
        message=result.get("message", "Config updated"),
        config=result.get("config", {}),
        error=result.get("error"),
    )
