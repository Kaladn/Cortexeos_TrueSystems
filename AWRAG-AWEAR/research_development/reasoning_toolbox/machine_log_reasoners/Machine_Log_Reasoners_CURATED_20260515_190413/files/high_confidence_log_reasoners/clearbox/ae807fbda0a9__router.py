"""Help System Plugin API Router -- FastAPI endpoints.

Exports: router (APIRouter), get_engine() (lazy singleton).
Prefix: /api/help
"""

from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, Query

from help_system.api.models import (
    HelpContentResponse,
    HelpIdsResponse,
    HelpSearchResponse,
    HelpStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/help", tags=["help_system"])

# ── Singleton Engine ─────────────────────────────────────────

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """Get or create the HelpSystemEngine singleton. Lazy-loaded, thread-safe."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from help_system.core.engine import HelpSystemEngine
                _engine = HelpSystemEngine()
    return _engine


def _version() -> str:
    try:
        from help_system import VERSION
        return VERSION
    except (ImportError, AttributeError):
        return "0.0.0"


# ── Status ───────────────────────────────────────────────────

@router.get("/status", response_model=HelpStatusResponse)
async def help_status():
    """Plugin status and content stats."""
    try:
        engine = get_engine()
        stats = engine.get_stats()
        return HelpStatusResponse(
            version=_version(),
            enabled=True,
            total_ids=stats["total_ids"],
            categories=stats["categories"],
            layers_coverage=stats["layers_coverage"],
        )
    except Exception as e:
        logger.error("Help System status error: %s", e, exc_info=True)
        return HelpStatusResponse(error={"type": "status_error", "message": str(e)})


# ── Content Lookup ───────────────────────────────────────────

@router.get("/content/{help_id:path}", response_model=HelpContentResponse)
async def help_content(help_id: str):
    """Get help entry for a specific data-help-id value."""
    try:
        engine = get_engine()
        entry = engine.get_entry(help_id)
        if entry is None:
            return HelpContentResponse(help_id=help_id, found=False)
        return HelpContentResponse(
            help_id=help_id,
            found=True,
            label=entry.get("label", ""),
            category=entry.get("category", ""),
            icon=entry.get("icon", ""),
            layer1=entry.get("layer1"),
            layer2=entry.get("layer2"),
            layer3=entry.get("layer3"),
            tutorial_available=entry.get("tutorial_available", False),
            difficulty=entry.get("difficulty", ""),
        )
    except Exception as e:
        logger.error("Help content lookup error for %s: %s", help_id, e, exc_info=True)
        return HelpContentResponse(
            help_id=help_id,
            error={"type": "content_error", "message": str(e)},
        )


# ── Search ───────────────────────────────────────────────────

@router.get("/search", response_model=HelpSearchResponse)
async def help_search(q: str = Query("", min_length=0)):
    """Search help content by text query."""
    if len(q.strip()) < 2:
        return HelpSearchResponse(query=q, results=[], total=0)
    try:
        engine = get_engine()
        results = engine.search(q.strip())
        return HelpSearchResponse(query=q, results=results, total=len(results))
    except Exception as e:
        logger.error("Help search error: %s", e, exc_info=True)
        return HelpSearchResponse(
            query=q,
            error={"type": "search_error", "message": str(e)},
        )


# ── IDs List ─────────────────────────────────────────────────

@router.get("/ids", response_model=HelpIdsResponse)
async def help_ids():
    """List all registered help IDs with label and category."""
    try:
        engine = get_engine()
        ids = engine.list_ids()
        return HelpIdsResponse(ids=ids, total=len(ids))
    except Exception as e:
        logger.error("Help IDs error: %s", e, exc_info=True)
        return HelpIdsResponse(error={"type": "ids_error", "message": str(e)})
