"""
OpenRefine Plugin — Pydantic Models
All responses default every field — no required fields on responses.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Base ──────────────────────────────────────────────────────────────────────
class BaseResponse(BaseModel):
    ok: bool = False
    message: str = ""
    error: Optional[Dict[str, Any]] = None


# ── Status / Health ───────────────────────────────────────────────────────────
class OpenRefineStatusResponse(BaseResponse):
    plugin_id: str = "openrefine"
    version: str = "0.1.0"
    running: bool = False
    or_version: str = ""
    or_host: str = ""
    or_port: int = 3333
    install_dir: str = ""
    workspace_dir: str = ""
    project_count: int = 0


# ── Process Control ───────────────────────────────────────────────────────────
class StartResponse(BaseResponse):
    pid: Optional[int] = None
    or_port: int = 3333
    startup_ms: int = 0


class StopResponse(BaseResponse):
    pid: Optional[int] = None


# ── Projects ──────────────────────────────────────────────────────────────────
class ProjectMeta(BaseModel):
    id: str = ""
    name: str = ""
    created: str = ""
    modified: str = ""
    row_count: int = 0
    description: str = ""
    tags: List[str] = Field(default_factory=list)


class ListProjectsResponse(BaseResponse):
    projects: List[ProjectMeta] = Field(default_factory=list)


class ProjectDetailResponse(BaseResponse):
    project: Optional[ProjectMeta] = None
    columns: List[str] = Field(default_factory=list)
    key_column: str = ""
    total_rows: int = 0


class CreateProjectRequest(BaseModel):
    name: str
    format: str = "text/line-based/*sv"   # csv default
    data: Optional[str] = None            # inline CSV/JSON text
    url: Optional[str] = None             # remote URL to import


class CreateProjectResponse(BaseResponse):
    project_id: str = ""
    project_name: str = ""


class DeleteProjectResponse(BaseResponse):
    project_id: str = ""


# ── Rows ──────────────────────────────────────────────────────────────────────
class RowCell(BaseModel):
    v: Any = None   # value (matches OpenRefine's row schema)
    r: Optional[str] = None  # recon data if present


class Row(BaseModel):
    cells: List[RowCell] = Field(default_factory=list)
    starred: bool = False
    flagged: bool = False
    i: int = 0  # row index


class GetRowsResponse(BaseResponse):
    rows: List[Row] = Field(default_factory=list)
    start: int = 0
    limit: int = 50
    total: int = 0
    filtered: int = 0


# ── Operations ────────────────────────────────────────────────────────────────
class ApplyOperationsRequest(BaseModel):
    project_id: str
    operations: List[Dict[str, Any]]


class ApplyOperationsResponse(BaseResponse):
    history_entry_id: Optional[int] = None
    operations_applied: int = 0


class ExpressionPreviewRequest(BaseModel):
    project_id: str
    column_name: str
    expression: str
    language: str = "grel"


class ExpressionPreviewResponse(BaseResponse):
    results: List[Any] = Field(default_factory=list)


# ── Export ────────────────────────────────────────────────────────────────────
class ExportRequest(BaseModel):
    project_id: str
    format: str = "csv"  # csv | tsv | xlsx | html | json


# ── Cluster ──────────────────────────────────────────────────────────────────
class ClusterGroup(BaseModel):
    choices: List[Dict[str, Any]] = Field(default_factory=list)
    value: str = ""
    count: int = 0


class ClusterResponse(BaseResponse):
    column_name: str = ""
    method: str = ""
    clusters: List[ClusterGroup] = Field(default_factory=list)


# ── Config live update ────────────────────────────────────────────────────────
class UpdateConfigRequest(BaseModel):
    port: Optional[int] = None
    memory_mb: Optional[int] = None
    install_dir: Optional[str] = None


class UpdateConfigResponse(BaseResponse):
    config: Dict[str, Any] = Field(default_factory=dict)
