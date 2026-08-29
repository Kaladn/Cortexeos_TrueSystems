"""Genesis Citation Tool — FastAPI router.

Mounted on Clearbox AI Studio Bridge (port 5050) at /api/genesis/

Endpoints:
    GET  /api/genesis/health
    POST /api/genesis/cite                  { "mode": "direct"|"search", ...params }
    GET  /api/genesis/cite/{tag}            shorthand direct lookup
    GET  /api/genesis/list                  all 68 blocks (no bodies)
    GET  /api/genesis/ingestion/status      parse INGESTION_LOG.md → progress JSON
    POST /api/genesis/ingestion/mark        update a block's status in the log
"""

from __future__ import annotations

import re as _re
from datetime import date as _date
from pathlib import Path as _Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .config import DEFAULT_SEARCH_LIMIT, MAX_SEARCH_LIMIT
from .engine import CitationEngine

# INGESTION_LOG.md lives at docs/GENESIS/INGESTION_LOG.md from repo root
_LOG_PATH = _Path(__file__).parent.parent.parent / "docs" / "GENESIS" / "INGESTION_LOG.md"

# Matches table data rows: | G-XXXX | Title... | STATUS | DATE | NOTES |
_ROW_RE = _re.compile(r"^\|\s*(G-\d{4})\s*\|[^|]+\|\s*(\w+)\s*\|([^|]*)\|([^|]*)\|")

_VALID_STATUSES = {"PENDING", "INGESTED", "SKIPPED", "REJECTED"}


def _parse_log() -> list[dict]:
    """Parse INGESTION_LOG.md rows into list of dicts."""
    rows: list[dict] = []
    try:
        text = _LOG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return rows
    for line in text.splitlines():
        m = _ROW_RE.match(line)
        if m:
            rows.append({
                "tag":    m.group(1),
                "status": m.group(2).strip(),
                "date":   m.group(3).strip(),
                "notes":  m.group(4).strip(),
            })
    return rows

router = APIRouter(prefix="/api/genesis", tags=["genesis"])

# Module-level engine singleton (shared across requests)
_engine = CitationEngine()


# ── Request / Response models ─────────────────────────────────────────────────

class SearchFilters(BaseModel):
    series: Optional[str] = Field(None, description="Series number 1–12")
    derived: Optional[bool] = Field(None, description="Include/exclude derived blocks")
    source_contains: Optional[str] = Field(None, description="Substring match on SOURCE field")


class CiteRequest(BaseModel):
    mode: str = Field(..., description="'direct' or 'search'")
    # Direct mode
    tag: Optional[str] = Field(None, description="G-XXXX tag (direct mode)")
    include_body: bool = Field(True, description="Include body text in response")
    # Search mode
    query: Optional[str] = Field(None, description="Plain-text query (search mode)")
    filters: Optional[SearchFilters] = Field(None)
    limit: int = Field(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT)
    include_snippets: bool = Field(True)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health")
def genesis_health() -> dict[str, Any]:
    """Return index health and block count."""
    return _engine.health()


@router.get("/cite/{tag}")
def genesis_cite_get(tag: str) -> dict[str, Any]:
    """Shorthand direct lookup: GET /api/genesis/cite/G-0017"""
    result = _engine.direct(tag, include_body=True)
    if not result.get("ok"):
        error = result.get("error", "UNKNOWN")
        if error == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.get("detail"))
        raise HTTPException(status_code=400, detail=result.get("detail"))
    return result


@router.post("/cite")
def genesis_cite_post(req: CiteRequest) -> dict[str, Any]:
    """Full cite endpoint — direct lookup or search."""
    if req.mode == "direct":
        if not req.tag:
            raise HTTPException(status_code=422, detail="'tag' required for direct mode")
        result = _engine.direct(req.tag, include_body=req.include_body)

    elif req.mode == "search":
        if not req.query:
            raise HTTPException(status_code=422, detail="'query' required for search mode")
        filters = req.filters.model_dump(exclude_none=True) if req.filters else {}
        result = _engine.search(
            query=req.query,
            filters=filters,
            limit=req.limit,
            include_snippets=req.include_snippets,
        )

    else:
        raise HTTPException(status_code=422, detail=f"Unknown mode '{req.mode}' — use 'direct' or 'search'")

    if not result.get("ok"):
        error = result.get("error", "UNKNOWN")
        if error == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.get("detail"))
        raise HTTPException(status_code=400, detail=result.get("detail"))

    return result


@router.get("/list")
def genesis_list() -> list[dict[str, Any]]:
    """Return all 68 blocks (tag, title, source, series) — no bodies."""
    return _engine.list_all()


@router.post("/reload")
def genesis_reload() -> dict[str, Any]:
    """Force index rebuild (e.g., after corpus update). Internal use only."""
    _engine.reload()
    return _engine.health()


# ── Ingestion tracking ────────────────────────────────────────────────────────

class IngestionMarkRequest(BaseModel):
    tag: str = Field(..., description="G-XXXX tag to mark")
    status: str = Field(..., description="INGESTED | SKIPPED | REJECTED | PENDING")
    notes: str = Field("", description="Optional notes (pipe chars sanitised)")


@router.get("/ingestion/status")
def genesis_ingestion_status() -> dict[str, Any]:
    """Return ingestion progress parsed from INGESTION_LOG.md."""
    rows = _parse_log()
    counts: dict[str, int] = {"PENDING": 0, "INGESTED": 0, "SKIPPED": 0, "REJECTED": 0}
    statuses: dict[str, dict] = {}
    for row in rows:
        s = row["status"] if row["status"] in counts else "PENDING"
        counts[s] += 1
        statuses[row["tag"]] = {
            "status": row["status"],
            "date":   row["date"],
            "notes":  row["notes"],
        }
    return {
        "ok":       True,
        "total":    len(rows),
        "INGESTED": counts["INGESTED"],
        "PENDING":  counts["PENDING"],
        "SKIPPED":  counts["SKIPPED"],
        "REJECTED": counts["REJECTED"],
        "statuses": statuses,
    }


@router.post("/ingestion/mark")
def genesis_ingestion_mark(req: IngestionMarkRequest) -> dict[str, Any]:
    """Update one block's status row in INGESTION_LOG.md and write it back."""
    if req.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{req.status}' — must be one of {sorted(_VALID_STATUSES)}",
        )
    if not _re.match(r"^G-\d{4}$", req.tag):
        raise HTTPException(status_code=422, detail=f"Invalid tag format '{req.tag}'")

    try:
        text = _LOG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="INGESTION_LOG.md not found on server")

    today = _date.today().isoformat()
    notes_safe = (req.notes or "").replace("|", "/")

    found = False
    new_lines: list[str] = []
    for line in text.splitlines():
        m = _ROW_RE.match(line)
        if m and m.group(1) == req.tag:
            found = True
            # Split on | to preserve tag + title columns exactly
            cols = line.split("|")
            if len(cols) >= 7:
                line = f"|{cols[1]}|{cols[2]}| {req.status:<8}| {today:<10} | {notes_safe:<5} |"
        new_lines.append(line)

    if not found:
        raise HTTPException(
            status_code=404, detail=f"Tag '{req.tag}' not found in INGESTION_LOG.md"
        )

    _LOG_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {"ok": True, "tag": req.tag, "status": req.status, "date": today}
