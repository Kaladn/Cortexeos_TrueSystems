"""DocuMap routes — map, commit, intake, and grove query endpoints."""
from __future__ import annotations

from pathlib import Path as _Path
from typing import Callable, Set

from fastapi import APIRouter, Query, Request

from bridges.models import CommitMapRequest, IntakeScanRequest, MapFilesRequest, MapRequest
from bridges.services.documap_analytics import DocuMapAnalyticsService
from bridges.services.documap_ingestion import DocuMapIngestionService
from bridges.services.documap_query import DocuMapQueryService
from bridges.state import BridgeState
from bridges.ws_manager import WebSocketManager
from security.data_paths import LAKESPEAK_CHUNKS_DIR, LAKESPEAK_INDEX_DIR

_BASE_DIR = _Path(__file__).resolve().parent.parent.parent
VERSION = "clearbox-bridge-2.0.0"


def make_router(
    state: BridgeState,
    ws_manager: WebSocketManager,
    ensure_lexicon_loaded: Callable,
    background_tasks_set: Set,
    task_done_cb: Callable,
) -> APIRouter:
    router = APIRouter()

    ingestion_service = DocuMapIngestionService(
        state=state,
        ws_manager=ws_manager,
        base_dir=_BASE_DIR,
        version=VERSION,
    )
    query_service = DocuMapQueryService(
        chunks_dir=LAKESPEAK_CHUNKS_DIR,
        index_dir=LAKESPEAK_INDEX_DIR,
    )
    analytics_service = DocuMapAnalyticsService(
        state=state,
        version=VERSION,
        chunks_dir=LAKESPEAK_CHUNKS_DIR,
        index_dir=LAKESPEAK_INDEX_DIR,
    )

    @router.post("/api/map")
    async def post_map(body: MapRequest, request: Request):
        return await ingestion_service.post_map(body, request, ensure_lexicon_loaded)

    @router.post("/api/map/commit")
    async def post_map_commit(body: CommitMapRequest):
        return await ingestion_service.post_map_commit(body)

    @router.post("/api/intake/scan")
    async def post_intake_scan(body: IntakeScanRequest):
        return await ingestion_service.post_intake_scan(body)

    @router.post("/api/map_files")
    async def post_map_files(body: MapFilesRequest):
        return await ingestion_service.post_map_files(
            body,
            ensure_lexicon_loaded,
            background_tasks_set,
            task_done_cb,
        )

    @router.get("/api/documap/stats")
    async def documap_stats():
        return await analytics_service.stats()

    @router.get("/api/documap/fingerprint/{fingerprint}")
    async def documap_check_fingerprint(fingerprint: str):
        return analytics_service.check_fingerprint(fingerprint)

    @router.post("/api/documap/jobs/event")
    async def documap_job_event(body: dict):
        return analytics_service.record_job_event(body)

    @router.get("/api/documap/docs")
    async def documap_docs(limit: int = 50, offset: int = 0):
        return await query_service.docs(limit, offset)

    @router.get("/api/documap/docs/{receipt_id}")
    async def documap_doc_detail(receipt_id: str):
        return await query_service.doc_detail(receipt_id)

    @router.get("/api/documap/docs/{receipt_id}/reconstruct")
    async def documap_reconstruct(receipt_id: str):
        return await query_service.reconstruct(receipt_id)

    @router.get("/api/documap/docs/{receipt_id}/graph")
    async def documap_graph(receipt_id: str, max_nodes: int = 100, max_edges: int = 500):
        return await query_service.graph(receipt_id, max_nodes, max_edges)

    @router.get("/api/documap/anchors/{anchor}/cloud")
    async def documap_anchor_cloud(anchor: str, receipt_id: str = "", topk: int = 20):
        return await query_service.anchor_cloud(anchor, receipt_id, topk)

    @router.get("/api/documap/topk")
    async def documap_topk(limit: int = 200, sort: str = "cf"):
        """Return corpus-wide top anchors from anchor_stats.json."""
        return await query_service.topk(limit, sort)

    return router
