"""Research Browser — FastAPI router.

Endpoints:
  GET  /api/research/status
  GET  /api/research/ui                    → redirect to /ui/index.html
  GET  /api/research/ui/{filename}         static HTML browser files
  GET  /api/research/proxy                 ?url=<encoded> server-side proxy (whitelisted hosts)
  POST /api/research/arxiv/search
  GET  /api/research/arxiv/abstract        ?id=<arxiv_id>
  POST /api/research/pubmed/search
  GET  /api/research/pubmed/abstract       ?pmid=<pmid>
  POST /api/research/hf/search
  POST /api/research/hf/preview
  GET  /api/research/cc/snapshots
  GET  /api/research/tools                 (LLM tool manifests)
"""
from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse, Response

from research_browser.api.models import (
    AbstractResponse,
    ArxivSearchRequest,
    HfPreviewRequest,
    HfSearchRequest,
    PreviewResponse,
    PubmedSearchRequest,
    SearchResponse,
    SnapshotResponse,
    StatusResponse,
    ToolsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research_browser"])

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from research_browser.config import load_config
                from research_browser.core.engine import ResearchEngine
                _engine = ResearchEngine(load_config())
    return _engine


_UI_DIR = Path(__file__).parent.parent / "ui"

_ALLOWED_PROXY_HOSTS = {
    "export.arxiv.org",
    "eutils.ncbi.nlm.nih.gov",
    "www.openml.org",
    "archive.ics.uci.edu",
    "dataverse.harvard.edu",
    "huggingface.co",
    "datasets-server.huggingface.co",
    "index.commoncrawl.org",
}

# ── Status ──────────────────────────────────────────────────────────────────

@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    try:
        return StatusResponse(**get_engine().status())
    except Exception as e:
        return StatusResponse(error={"type": "status_error", "message": str(e)})


# ── UI file serving ──────────────────────────────────────────────────────────

@router.get("/ui", include_in_schema=False)
async def plugin_ui_root():
    """Serve index.html directly so the plugin panel probe gets text/html."""
    p = _UI_DIR / "index.html"
    if not p.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(str(p), media_type="text/html")


@router.get("/ui/{filename}", include_in_schema=False)
async def plugin_ui_file(filename: str):
    p = (_UI_DIR / filename).resolve()
    if not str(p).startswith(str(_UI_DIR.resolve())):
        raise HTTPException(status_code=404)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found")
    return FileResponse(str(p), media_type="text/html")


# ── Proxy ────────────────────────────────────────────────────────────────────

@router.get("/proxy")
async def proxy(
    url: str = Query(..., description="Full URL to proxy (must be whitelisted host)"),
    authorization: str = Header(default=""),
):
    """Server-side proxy for whitelisted research API hosts.

    Solves CORS / 400 issues when HTML browsers call external APIs.
    The UI files call /api/research/proxy?url=<encoded> instead of
    the external API directly.
    """
    host = urlparse(url).netloc
    if not host or host not in _ALLOWED_PROXY_HOSTS:
        raise HTTPException(status_code=400, detail=f"Host not in allowlist: {host}")
    fwd_headers = {"Authorization": authorization} if authorization else {}
    try:
        engine = get_engine()
        body, ct = await asyncio.to_thread(engine.proxy_request, url, fwd_headers)
        return Response(content=body, media_type=ct.split(";")[0].strip())
    except Exception as e:
        logger.error("Proxy error for %s: %s", url, e)
        raise HTTPException(status_code=502, detail=str(e))


# ── arXiv ────────────────────────────────────────────────────────────────────

@router.post("/arxiv/search", response_model=SearchResponse)
async def arxiv_search(req: ArxivSearchRequest) -> SearchResponse:
    try:
        engine = get_engine()
        results = await asyncio.to_thread(
            engine.arxiv_search,
            query=req.query,
            category=req.category,
            sort=req.sort,
            max_results=req.max_results,
        )
        return SearchResponse(
            source="arxiv",
            query=req.query or req.category,
            count=len(results),
            results=results,
        )
    except Exception as e:
        logger.error("arXiv search error: %s", e, exc_info=True)
        return SearchResponse(error={"type": "arxiv_error", "message": str(e)})


@router.get("/arxiv/abstract", response_model=AbstractResponse)
async def arxiv_abstract(id: str = Query(..., description="arXiv paper ID")) -> AbstractResponse:
    try:
        engine = get_engine()
        data = await asyncio.to_thread(engine.arxiv_abstract, id)
        if "error" in data:
            return AbstractResponse(error={"type": "not_found", "message": data["error"]})
        return AbstractResponse(**data)
    except Exception as e:
        logger.error("arXiv abstract error: %s", e, exc_info=True)
        return AbstractResponse(error={"type": "arxiv_error", "message": str(e)})


# ── PubMed ───────────────────────────────────────────────────────────────────

@router.post("/pubmed/search", response_model=SearchResponse)
async def pubmed_search(req: PubmedSearchRequest) -> SearchResponse:
    try:
        engine = get_engine()
        results = await asyncio.to_thread(
            engine.pubmed_search,
            query=req.query,
            article_type=req.article_type,
            sort=req.sort,
            max_results=req.max_results,
        )
        return SearchResponse(
            source="pubmed",
            query=req.query,
            count=len(results),
            results=results,
        )
    except Exception as e:
        logger.error("PubMed search error: %s", e, exc_info=True)
        return SearchResponse(error={"type": "pubmed_error", "message": str(e)})


@router.get("/pubmed/abstract", response_model=AbstractResponse)
async def pubmed_abstract(pmid: str = Query(..., description="PubMed article ID")) -> AbstractResponse:
    try:
        engine = get_engine()
        data = await asyncio.to_thread(engine.pubmed_abstract, pmid)
        if "error" in data:
            return AbstractResponse(error={"type": "pubmed_error", "message": data["error"]})
        return AbstractResponse(**{k: v for k, v in data.items() if k in AbstractResponse.model_fields})
    except Exception as e:
        logger.error("PubMed abstract error: %s", e, exc_info=True)
        return AbstractResponse(error={"type": "pubmed_error", "message": str(e)})


# ── HuggingFace ──────────────────────────────────────────────────────────────

@router.post("/hf/search", response_model=SearchResponse)
async def hf_search(req: HfSearchRequest) -> SearchResponse:
    try:
        engine = get_engine()
        results = await asyncio.to_thread(
            engine.hf_search,
            query=req.query,
            task=req.task,
            sort=req.sort,
            max_results=req.max_results,
            token=req.token,
        )
        return SearchResponse(
            source="huggingface",
            query=req.query or req.task,
            count=len(results),
            results=results,
        )
    except Exception as e:
        logger.error("HF search error: %s", e, exc_info=True)
        return SearchResponse(error={"type": "hf_error", "message": str(e)})


@router.post("/hf/preview", response_model=PreviewResponse)
async def hf_preview(req: HfPreviewRequest) -> PreviewResponse:
    try:
        engine = get_engine()
        data = await asyncio.to_thread(
            engine.hf_preview,
            dataset=req.dataset,
            config=req.config,
            split=req.split,
            offset=req.offset,
            length=req.length,
            token=req.token,
        )
        return PreviewResponse(**data)
    except Exception as e:
        logger.error("HF preview error: %s", e, exc_info=True)
        return PreviewResponse(error={"type": "hf_error", "message": str(e)})


# ── Common Crawl ─────────────────────────────────────────────────────────────

@router.get("/cc/snapshots", response_model=SnapshotResponse)
async def cc_snapshots() -> SnapshotResponse:
    try:
        engine = get_engine()
        snaps = await asyncio.to_thread(engine.cc_snapshots)
        return SnapshotResponse(count=len(snaps), snapshots=snaps)
    except Exception as e:
        logger.error("Common Crawl snapshots error: %s", e, exc_info=True)
        return SnapshotResponse(error={"type": "cc_error", "message": str(e)})


# ── Tool Manifests ────────────────────────────────────────────────────────────

_TOOL_MANIFESTS = [
    {
        "name": "research_arxiv_search",
        "description": (
            "Search arXiv for academic papers by keyword query and/or category. "
            "Returns paper titles, authors, abstracts, published dates, and PDF links."
        ),
        "endpoint": "POST /api/research/arxiv/search",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms (e.g. 'transformer attention mechanism')"},
                "category": {
                    "type": "string",
                    "description": "arXiv category code: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.IR, stat.ML, etc.",
                },
                "sort": {
                    "type": "string",
                    "enum": ["submittedDate", "relevance", "lastUpdatedDate"],
                    "default": "submittedDate",
                    "description": "Sort order for results",
                },
                "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            },
        },
    },
    {
        "name": "research_arxiv_abstract",
        "description": (
            "Fetch the full abstract and metadata for a single arXiv paper by its ID. "
            "ID format: '2401.12345' or full URL 'https://arxiv.org/abs/2401.12345'."
        ),
        "endpoint": "GET /api/research/arxiv/abstract?id=<id>",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "arXiv paper ID (e.g. '2401.12345')"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "research_pubmed_search",
        "description": (
            "Search PubMed for biomedical literature. Returns titles, authors, journals, "
            "publication dates, and PMC open-access links when available."
        ),
        "endpoint": "POST /api/research/pubmed/search",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "PubMed search terms"},
                "article_type": {
                    "type": "string",
                    "enum": ["", "review", "clinical+trial", "meta-analysis", "systematic+review", "case+reports"],
                    "default": "",
                    "description": "Filter by article type",
                },
                "sort": {
                    "type": "string",
                    "enum": ["relevance", "pub_date", "JournalName"],
                    "default": "relevance",
                },
                "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            },
            "required": ["query"],
        },
    },
    {
        "name": "research_pubmed_abstract",
        "description": "Fetch the full abstract text for a PubMed article by PMID.",
        "endpoint": "GET /api/research/pubmed/abstract?pmid=<pmid>",
        "input_schema": {
            "type": "object",
            "properties": {
                "pmid": {"type": "string", "description": "PubMed ID (numeric string)"},
            },
            "required": ["pmid"],
        },
    },
    {
        "name": "research_hf_search",
        "description": (
            "Search HuggingFace for ML datasets by query and/or task category. "
            "Returns dataset IDs, descriptions, download counts, and HF URLs."
        ),
        "endpoint": "POST /api/research/hf/search",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms"},
                "task": {
                    "type": "string",
                    "description": "Task category slug: text-classification, question-answering, summarization, translation, text-generation, image-classification, etc.",
                },
                "sort": {
                    "type": "string",
                    "enum": ["trending", "downloads", "likes", "created"],
                    "default": "trending",
                },
                "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            },
        },
    },
    {
        "name": "research_hf_preview",
        "description": (
            "Preview rows from a HuggingFace dataset. Returns column names and sample rows."
        ),
        "endpoint": "POST /api/research/hf/preview",
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset": {"type": "string", "description": "Dataset ID in 'owner/name' format"},
                "config": {"type": "string", "default": "default"},
                "split": {"type": "string", "default": "train"},
                "offset": {"type": "integer", "default": 0, "minimum": 0},
                "length": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
            },
            "required": ["dataset"],
        },
    },
    {
        "name": "research_cc_snapshots",
        "description": (
            "List available Common Crawl web crawl snapshots with WET/WARC download paths. "
            "WET files contain pre-extracted text from billions of web pages."
        ),
        "endpoint": "GET /api/research/cc/snapshots",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


@router.get("/tools", response_model=ToolsResponse)
async def tools() -> ToolsResponse:
    """Return tool manifests for all research endpoints.

    LLM tool calling: use these schemas to define callable tools that
    map to the research_browser plugin endpoints.
    """
    return ToolsResponse(tools=_TOOL_MANIFESTS)
