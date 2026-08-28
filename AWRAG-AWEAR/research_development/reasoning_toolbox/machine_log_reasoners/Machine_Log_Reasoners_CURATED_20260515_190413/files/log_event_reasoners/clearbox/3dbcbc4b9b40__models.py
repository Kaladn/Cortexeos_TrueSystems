"""Research Browser — Pydantic request/response models."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Requests ────────────────────────────────────────────────────────────────

class ArxivSearchRequest(BaseModel):
    query: str = ""
    category: str = ""                      # e.g. "cs.AI", "cs.LG", "cs.CL"
    sort: str = "submittedDate"             # submittedDate | relevance | lastUpdatedDate
    max_results: int = Field(default=10, ge=1, le=50)


class PubmedSearchRequest(BaseModel):
    query: str
    article_type: str = ""                  # review | clinical+trial | meta-analysis | ...
    sort: str = "relevance"                 # relevance | pub_date | JournalName
    max_results: int = Field(default=10, ge=1, le=50)


class HfSearchRequest(BaseModel):
    query: str = ""
    task: str = ""                          # HF task category slug
    sort: str = "trending"                  # trending | downloads | likes | created
    max_results: int = Field(default=10, ge=1, le=50)
    token: str = ""                         # HuggingFace Bearer token (optional)


class HfPreviewRequest(BaseModel):
    dataset: str                            # "owner/dataset-name"
    config: str = "default"
    split: str = "train"
    offset: int = Field(default=0, ge=0)
    length: int = Field(default=20, ge=1, le=100)
    token: str = ""


# ── Responses ───────────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    version: str = ""
    enabled: bool = False
    sources: List[str] = []
    hf_token_configured: bool = False
    timeout_seconds: int = 15
    error: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    source: str = ""
    query: str = ""
    count: int = 0
    results: List[Dict[str, Any]] = []
    error: Optional[Dict[str, Any]] = None


class AbstractResponse(BaseModel):
    source: str = ""
    id: str = ""
    title: str = ""
    authors: str = ""
    abstract: str = ""
    abstract_text: str = ""    # PubMed efetch plain-text
    published: str = ""
    pubdate: str = ""
    journal: str = ""
    pdf_url: str = ""
    pubmed_url: str = ""
    pmc_url: str = ""
    pmcid: str = ""
    categories: str = ""
    error: Optional[Dict[str, Any]] = None


class PreviewResponse(BaseModel):
    source: str = "huggingface"
    dataset: str = ""
    config: str = ""
    split: str = ""
    offset: int = 0
    columns: List[str] = []
    rows: List[Dict[str, Any]] = []
    error: Optional[Dict[str, Any]] = None


class SnapshotResponse(BaseModel):
    source: str = "commoncrawl"
    count: int = 0
    snapshots: List[Dict[str, Any]] = []
    error: Optional[Dict[str, Any]] = None


class ToolsResponse(BaseModel):
    """Tool manifests for LLM tool calling."""
    tools: List[Dict[str, Any]] = []
