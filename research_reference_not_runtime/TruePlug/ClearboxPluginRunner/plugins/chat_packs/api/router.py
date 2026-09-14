"""Chat Packs Plugin API Router -- FastAPI endpoints.

Exports: router (APIRouter), get_engine() (lazy singleton).
Prefix: /api/chat-packs
"""

from __future__ import annotations

import logging
import threading

from fastapi import APIRouter

from chat_packs.api.models import (
    LessonViewResponse,
    PackDetailResponse,
    PackInstallRequest,
    PackInstallResponse,
    PackListResponse,
    PackSessionResponse,
    PackStatusResponse,
    SectionContentResponse,
    SessionListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat-packs", tags=["chat_packs"])

# ── Singleton Engine ─────────────────────────────────────────

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """Get or create the ChatPackEngine singleton. Lazy-loaded, thread-safe."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from chat_packs.core.engine import ChatPackEngine
                _engine = ChatPackEngine()
    return _engine


def _version() -> str:
    try:
        from chat_packs import VERSION
        return VERSION
    except (ImportError, AttributeError):
        return "0.0.0"


# ── Status ───────────────────────────────────────────────────

@router.get("/status", response_model=PackStatusResponse)
async def cp_status():
    """Plugin status and content stats."""
    try:
        engine = get_engine()
        stats = engine.get_stats()
        return PackStatusResponse(
            version=_version(),
            enabled=True,
            packs_dir=str(engine._packs_dir),
            installed_count=stats["installed_count"],
            active_sessions=stats["active_sessions"],
        )
    except Exception as e:
        logger.error("Chat Packs status error: %s", e, exc_info=True)
        return PackStatusResponse(error={"type": "status_error", "message": str(e)})


# ── List Packs ───────────────────────────────────────────────

@router.get("/list", response_model=PackListResponse)
async def cp_list():
    """List all installed packs (metadata only, no content)."""
    try:
        engine = get_engine()
        packs = engine.list_packs()
        return PackListResponse(packs=packs, total=len(packs))
    except Exception as e:
        logger.error("Chat Packs list error: %s", e, exc_info=True)
        return PackListResponse(error={"type": "list_error", "message": str(e)})


# ── List Sessions (Learning Center resume cards) ─────────────

@router.get("/sessions", response_model=SessionListResponse)
async def cp_sessions():
    """List all saved sessions for resume cards."""
    try:
        engine = get_engine()
        sessions = engine.list_sessions()
        return SessionListResponse(sessions=sessions, total=len(sessions))
    except Exception as e:
        logger.error("Chat Packs sessions list error: %s", e, exc_info=True)
        return SessionListResponse(error={"type": "sessions_error", "message": str(e)})


# ── Section Content (must register before greedy pack/:path) ─

@router.get("/pack/{pack_id:path}/section/{index}", response_model=SectionContentResponse)
async def cp_section_content(pack_id: str, index: int):
    """Get content for a specific section by index."""
    try:
        engine = get_engine()
        content = engine.get_section_content(pack_id, index)
        if content is None:
            return SectionContentResponse(
                error={"type": "not_found", "message": f"Section {index} not found in {pack_id}"}
            )
        return SectionContentResponse(**content)
    except Exception as e:
        logger.error("Chat Packs section content error: %s", e, exc_info=True)
        return SectionContentResponse(error={"type": "section_error", "message": str(e)})


# ── Pack Detail ──────────────────────────────────────────────

@router.get("/pack/{pack_id:path}", response_model=PackDetailResponse)
async def cp_detail(pack_id: str):
    """Pack metadata + section titles (no full content)."""
    try:
        engine = get_engine()
        pack = engine.get_pack(pack_id)
        if pack is None:
            return PackDetailResponse(error={"type": "not_found", "message": f"Pack {pack_id} not found"})
        return PackDetailResponse(
            pack={
                "pack_id": pack["pack_id"],
                "title": pack["title"],
                "version": pack["version"],
                "mode": pack["mode"],
                "tags": pack["tags"],
                "difficulty": pack["difficulty"],
                "total_sections": pack["total_sections"],
                "total_questions": pack["total_questions"],
                "has_assets": pack["has_assets"],
                "readme": pack["readme"],
            },
            section_titles=pack.get("section_titles", []),
            question_count=pack.get("question_count", 0),
        )
    except Exception as e:
        logger.error("Chat Packs detail error for %s: %s", pack_id, e, exc_info=True)
        return PackDetailResponse(error={"type": "detail_error", "message": str(e)})


# ── Install ──────────────────────────────────────────────────

@router.post("/install", response_model=PackInstallResponse)
async def cp_install(req: PackInstallRequest):
    """Install a pack from an external folder path."""
    try:
        engine = get_engine()
        result = engine.install_pack(req.source_path)
        return PackInstallResponse(**result)
    except Exception as e:
        logger.error("Chat Packs install error: %s", e, exc_info=True)
        return PackInstallResponse(error={"type": "install_error", "message": str(e)})


# ── Session: Start ───────────────────────────────────────────

@router.post("/session/start/{pack_id:path}", response_model=PackSessionResponse)
async def cp_start(pack_id: str, model: str = ""):
    """Start a new session for a pack. Returns session_id."""
    try:
        engine = get_engine()
        session = engine.start_session(pack_id, model=model)
        if session is None:
            return PackSessionResponse(
                error={"type": "not_found", "message": f"Pack {pack_id} not found"}
            )
        content = engine.get_current_content(session["session_id"])
        return PackSessionResponse(session=session, current_content=content)
    except Exception as e:
        logger.error("Chat Packs session start error: %s", e, exc_info=True)
        return PackSessionResponse(error={"type": "start_error", "message": str(e)})


# ── Session: Lesson View (Learning Center workspace) ─────────

@router.get("/session/{session_id}/view", response_model=LessonViewResponse)
async def cp_lesson_view(session_id: str):
    """Full workspace view: section outline with status + current content."""
    try:
        engine = get_engine()
        view = engine.get_lesson_view(session_id)
        if view is None:
            return LessonViewResponse(
                error={"type": "not_found", "message": f"Session {session_id} not found"}
            )
        return LessonViewResponse(**view)
    except Exception as e:
        logger.error("Chat Packs lesson view error: %s", e, exc_info=True)
        return LessonViewResponse(error={"type": "view_error", "message": str(e)})


# ── Session: Get State ───────────────────────────────────────

@router.get("/session/{session_id}", response_model=PackSessionResponse)
async def cp_session(session_id: str):
    """Get session state + current section/question content."""
    try:
        engine = get_engine()
        session = engine.get_session(session_id)
        if session is None:
            return PackSessionResponse(
                error={"type": "not_found", "message": f"Session {session_id} not found"}
            )
        content = engine.get_current_content(session_id)
        return PackSessionResponse(session=session, current_content=content)
    except Exception as e:
        logger.error("Chat Packs session get error: %s", e, exc_info=True)
        return PackSessionResponse(error={"type": "session_error", "message": str(e)})


# ── Session: Advance ─────────────────────────────────────────

@router.post("/session/advance/{session_id}", response_model=PackSessionResponse)
async def cp_advance(session_id: str):
    """Advance to next section or question."""
    try:
        engine = get_engine()
        session = engine.advance_session(session_id)
        if session is None:
            return PackSessionResponse(
                error={"type": "not_found", "message": f"Session {session_id} not found"}
            )
        content = engine.get_current_content(session_id)
        return PackSessionResponse(session=session, current_content=content)
    except Exception as e:
        logger.error("Chat Packs advance error: %s", e, exc_info=True)
        return PackSessionResponse(error={"type": "advance_error", "message": str(e)})


# ── Session: Reset ───────────────────────────────────────────

@router.post("/session/reset/{session_id}", response_model=PackSessionResponse)
async def cp_reset(session_id: str):
    """Reset session to beginning."""
    try:
        engine = get_engine()
        session = engine.reset_session(session_id)
        if session is None:
            return PackSessionResponse(
                error={"type": "not_found", "message": f"Session {session_id} not found"}
            )
        content = engine.get_current_content(session_id)
        return PackSessionResponse(session=session, current_content=content)
    except Exception as e:
        logger.error("Chat Packs reset error: %s", e, exc_info=True)
        return PackSessionResponse(error={"type": "reset_error", "message": str(e)})
