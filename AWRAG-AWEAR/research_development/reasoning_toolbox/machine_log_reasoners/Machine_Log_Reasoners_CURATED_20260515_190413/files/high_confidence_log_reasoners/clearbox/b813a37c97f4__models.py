"""Pydantic request/response models — extracted from clearbox_bridge_server.py."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, validator


class MapRequest(BaseModel):
    text: str
    source: Optional[str] = "inline"
    device: Optional[str] = "cpu"


class MapFilesRequest(BaseModel):
    paths: List[str]
    source: Optional[str] = "batch"
    recursive: Optional[bool] = True
    pattern: Optional[str] = None
    ignore_missing: Optional[bool] = False


class IntakeScanRequest(BaseModel):
    source_path: str
    scan_mode: str = "root_only"   # root_only | full_directory


class ConfigUpdateRequest(BaseModel):
    min_len: Optional[int] = None
    topK: Optional[int] = None
    window: Optional[int] = None
    alpha_only: Optional[bool] = None
    regex_include: Optional[str] = None
    regex_exclude: Optional[str] = None
    gpu: Optional[str] = None


class CancelRequest(BaseModel):
    job_id: str


class SnapshotRequest(BaseModel):
    tag: Optional[str] = None


class RollbackRequest(BaseModel):
    path: str


class Get616Request(BaseModel):
    word: str
    topk: Optional[int] = None


class AnalyzeUnmappedRequest(BaseModel):
    """Request to analyze unmapped tokens from 616 reports."""
    reports_root: Optional[str] = None
    report_paths: Optional[List[str]] = None


class LexiconAppendRequest(BaseModel):
    word: str
    status: Optional[str] = None

class LexiconIgnoreRequest(BaseModel):
    word: str


class AssignSymbolRequest(BaseModel):
    word: str
    symbol: Optional[str] = None
    force: Optional[bool] = False


class SetStatusRequest(BaseModel):
    word: str
    status: Optional[str] = None


class LexiconImportRequest(BaseModel):
    words_dir: str


class ChainSlot(BaseModel):
    slot_id: int  # 1-10
    enabled: bool = False
    provider: str = ""  # "openai", "claude", "gemini", "grok"
    model: str = ""
    interrupt_after: bool = False  # Pause chain after this slot for user input


class ChatSendRequest(BaseModel):
    message: str
    mode: str = "llm"  # user-facing modes: "llm", "grounded", "multi_llm"
    model: Optional[str] = None  # Legacy: kept for backward compat (genesis, direct API callers)
    session_id: Optional[str] = None
    topk: int = 8
    inference_params: Optional[Dict[str, Any]] = None  # Per-model inference overrides
    tools_enabled: bool = False  # Enables tool calling in LLM mode (hub only)
    # ── Chain builder fields ──
    plugins_enabled: bool = False
    enabled_plugins: List[str] = []
    local_model: Optional[str] = None  # Hub model — sole model authority for all modes
    hub_provider: str = "ollama"  # Hub provider: "ollama", "openai", "claude", "gemini", "grok"
    hub_enabled: bool = True  # Whether hub (local) model participates in chain
    chain_slots: Optional[List[ChainSlot]] = None  # 1-10 API slots, sequential
    resolver_enabled: bool = False  # Final synthesis slot after all chain slots
    resolver_provider: str = ""  # Provider for resolver slot
    resolver_model: str = ""  # Model for resolver slot
    side_chat_id: Optional[str] = None  # Optional side-chat branch id for continue/deep work
    generation_contract: Optional[str] = None  # Contract rules from Inference page
    chain_resume: Optional[Dict[str, Any]] = None  # Resume interrupted chain with user steering

    @validator("message")
    def _cap_message_size(cls, v):
        if len(v) > 100_000:  # 100 KB max
            raise ValueError("Message exceeds 100 KB limit")
        return v


class ChatSendResponse(BaseModel):
    mode: str
    source: str
    response: str
    answer_frame: Optional[Dict[str, Any]] = None
    reasoning_trace: Optional[Dict[str, Any]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    grounded: bool = False
    verdict: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    seat: Optional[Dict[str, Any]] = None  # {provider, model, seat_id?, node_id?}
    contributions: Optional[List[Dict[str, Any]]] = None  # Chain: all mind outputs
    chain_state: Optional[Dict[str, Any]] = None  # Interrupted chain: state to resume


class LoadRequest(BaseModel):
    lexicon_root: Optional[str] = None
    reports_root: Optional[str] = None
    gpu: Optional[str] = None
    window: Optional[int] = None
    topK: Optional[int] = None
    min_len: Optional[int] = None


class CommitMapRequest(BaseModel):
    job_name: Optional[str] = "616_map"
    report: Optional[Dict[str, Any]] = None
    cite_id: Optional[str] = None


class PluginToggleRequest(BaseModel):
    connected: bool
