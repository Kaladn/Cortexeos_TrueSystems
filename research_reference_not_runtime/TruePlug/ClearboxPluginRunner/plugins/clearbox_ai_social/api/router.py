from __future__ import annotations

import threading

from fastapi import APIRouter

from plugins.clearbox_ai_social.api.models import (
    CreateListingRequest,
    CreateListingResponse,
    IdentityResponse,
    PeerSyncRequest,
    PeerSyncResponse,
    SaveProfileRequest,
    SaveProfileResponse,
    SearchListingsResponse,
    StatusResponse,
)
from plugins.clearbox_ai_social.core.engine import ClearboxAISocialEngine


router = APIRouter(prefix="/api/clearbox-social", tags=["clearbox_ai_social"])

_engine: ClearboxAISocialEngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> ClearboxAISocialEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = ClearboxAISocialEngine()
    return _engine


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    data = get_engine().status()
    return StatusResponse(**data)


@router.get("/identity", response_model=IdentityResponse)
async def identity() -> IdentityResponse:
    data = get_engine().get_identity()
    return IdentityResponse(**data)


@router.get("/profile", response_model=SaveProfileResponse)
async def get_profile() -> SaveProfileResponse:
    data = get_engine().get_local_profile()
    return SaveProfileResponse(
        ok=data.get("ok", False),
        message=data.get("message", ""),
        profile=data.get("profile", {}),
        error=data.get("error"),
    )


@router.post("/profile", response_model=SaveProfileResponse)
async def save_profile(req: SaveProfileRequest) -> SaveProfileResponse:
    data = get_engine().save_profile(req.model_dump())
    return SaveProfileResponse(**data)


@router.post("/marketplace/listings", response_model=CreateListingResponse)
async def create_listing(req: CreateListingRequest) -> CreateListingResponse:
    data = get_engine().create_listing(req.model_dump())
    return CreateListingResponse(**data)


@router.get("/marketplace/listings", response_model=SearchListingsResponse)
async def search_listings(
    category: str = "",
    author_node_id: str = "",
    sort_by: str = "downloads",
) -> SearchListingsResponse:
    data = get_engine().search_listings(
        category=category,
        author_node_id=author_node_id,
        sort_by=sort_by,
    )
    return SearchListingsResponse(**data)


@router.post("/sync", response_model=PeerSyncResponse)
async def sync_peer(req: PeerSyncRequest) -> PeerSyncResponse:
    data = get_engine().sync_peer(
        node_id=req.node_id,
        host=req.host,
        port=req.port,
        scheme=req.scheme,
    )
    return PeerSyncResponse(**data)
