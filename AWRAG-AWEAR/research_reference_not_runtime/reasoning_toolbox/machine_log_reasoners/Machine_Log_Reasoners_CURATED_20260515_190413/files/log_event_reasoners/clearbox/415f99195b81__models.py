"""Chat Packs API models -- all fields have defaults for safe serialization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class PackMeta(BaseModel):
    """Metadata from a pack's metadata.json (no lesson/instructor content)."""
    pack_id: str = ""
    title: str = ""
    version: str = ""
    mode: str = "stepwise"
    tags: List[str] = []
    difficulty: str = ""
    total_sections: int = 0
    total_questions: int = 0
    has_assets: bool = False
    readme: str = ""


class PackSession(BaseModel):
    """Runtime state for an active pack session."""
    session_id: str = ""
    pack_id: str = ""
    model: str = ""
    phase: str = "lesson"  # "lesson" | "questions" | "complete"
    section_index: int = 0
    question_index: int = 0
    total_sections: int = 0
    total_questions: int = 0
    scores: List[Dict[str, Any]] = []
    started_utc: str = ""
    updated_utc: str = ""


class PackListResponse(BaseModel):
    packs: List[PackMeta] = []
    total: int = 0
    error: Optional[Dict[str, Any]] = None


class PackDetailResponse(BaseModel):
    """Pack metadata + section titles only (no full content)."""
    pack: Optional[PackMeta] = None
    section_titles: List[str] = []
    question_count: int = 0
    error: Optional[Dict[str, Any]] = None


class PackSessionResponse(BaseModel):
    session: Optional[PackSession] = None
    current_content: Optional[Dict[str, str]] = None  # {title, body}
    error: Optional[Dict[str, Any]] = None


class PackInstallRequest(BaseModel):
    source_path: str


class PackInstallResponse(BaseModel):
    pack_id: str = ""
    installed: bool = False
    error: Optional[Dict[str, Any]] = None


class PackStatusResponse(BaseModel):
    version: str = ""
    enabled: bool = False
    packs_dir: str = ""
    installed_count: int = 0
    active_sessions: int = 0
    error: Optional[Dict[str, Any]] = None


# ── Learning Center models ────────────────────────────────────


class SessionSummary(BaseModel):
    """Lightweight session info for the library resume cards."""
    session_id: str = ""
    pack_id: str = ""
    pack_title: str = ""
    phase: str = "lesson"
    section_index: int = 0
    total_sections: int = 0
    question_index: int = 0
    total_questions: int = 0
    started_utc: str = ""
    updated_utc: str = ""


class SessionListResponse(BaseModel):
    sessions: List[SessionSummary] = []
    total: int = 0
    error: Optional[Dict[str, Any]] = None


class SectionOutlineItem(BaseModel):
    """One entry in the section outline."""
    index: int = 0
    title: str = ""
    status: str = "locked"  # "completed" | "current" | "locked"


class LessonViewResponse(BaseModel):
    """Full workspace data: session + section outline + current content."""
    session: Optional[PackSession] = None
    pack_title: str = ""
    sections: List[SectionOutlineItem] = []
    current_content: Optional[Dict[str, str]] = None
    error: Optional[Dict[str, Any]] = None


class SectionContentResponse(BaseModel):
    """Single section content for re-reading completed sections."""
    title: str = ""
    body: str = ""
    error: Optional[Dict[str, Any]] = None
