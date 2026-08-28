"""Forest Node API Router -- FastAPI endpoints for distributed computing.

Mounted on the bridge server at /api/nodes.
All imports are lazy -- bridge server boots fine even if forest_node deps are missing.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from forest_node.api.models import (
    DistributeRequest,
    DistributeResponse,
    NodeJobStatusResponse,
    NodeListResponse,
    NodeStatusResponse,
    PairRequest,
    PairResponse,
    RegisterRequest,
    RegisterResponse,
    RemoveNodeRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nodes", tags=["forest_node"])

# -- Singleton Engine ------------------------------------------------------

_engine = None


def get_engine():
    """Get or create the NodeEngine singleton. Lazy-loaded."""
    global _engine
    if _engine is None:
        from forest_node.core.engine import NodeEngine
        _engine = NodeEngine()
    return _engine


# -- Status ----------------------------------------------------------------

@router.get("/status", response_model=NodeStatusResponse)
async def node_status():
    try:
        from forest_node import VERSION
        engine = get_engine()
        return NodeStatusResponse(
            version=VERSION,
            enabled=True,
            node_count=engine.node_count,
            paired_count=engine.paired_count,
            discovery_active=engine.discovery_active,
            local_node_id=engine.local_node_id,
            caps=engine.get_local_caps(),
        )
    except Exception as e:
        logger.error("Forest Node status error: %s", e, exc_info=True)
        return NodeStatusResponse(error={"type": "status_error", "message": str(e)})


# -- Node List -------------------------------------------------------------

@router.get("/list", response_model=NodeListResponse)
async def node_list():
    try:
        engine = get_engine()
        return NodeListResponse(
            nodes=engine.list_nodes(),
            discovery_active=engine.discovery_active,
        )
    except Exception as e:
        logger.error("Forest Node list error: %s", e, exc_info=True)
        return NodeListResponse(error={"type": "list_error", "message": str(e)})


# -- Discovery Control -----------------------------------------------------

@router.post("/discover/start")
async def node_discover_start():
    """Start UDP broadcast discovery (Phase 2 will add actual networking)."""
    try:
        engine = get_engine()
        engine.start_discovery()
        return {"ok": True, "discovery_active": engine.discovery_active}
    except Exception as e:
        return {"ok": False, "discovery_active": False, "error": str(e)}


@router.post("/discover/stop")
async def node_discover_stop():
    """Stop UDP broadcast discovery."""
    try:
        engine = get_engine()
        engine.stop_discovery()
        return {"ok": True, "discovery_active": engine.discovery_active}
    except Exception as e:
        return {"ok": False, "discovery_active": False, "error": str(e)}


# -- Registration (Phase 2 — manual add by IP:port) -----------------------

@router.post("/register", response_model=RegisterResponse)
async def node_register(req: RegisterRequest):
    """Register a remote node by probing its daemon at ip:port."""
    try:
        engine = get_engine()
        node = await engine.register_node(req.ip, req.port, req.nickname)
        return RegisterResponse(ok=True, node=node)
    except Exception as e:
        logger.error("Node registration failed for %s:%d: %s", req.ip, req.port, e)
        return RegisterResponse(
            ok=False,
            error={"type": "register_error", "message": str(e)},
        )


@router.post("/remove")
async def node_remove(req: RemoveNodeRequest):
    """Remove a known node from the registry."""
    try:
        engine = get_engine()
        removed = engine.remove_node(req.node_id)
        return {"ok": removed, "node_id": req.node_id}
    except Exception as e:
        return {"ok": False, "node_id": req.node_id, "error": str(e)}


@router.post("/heartbeat")
async def node_heartbeat():
    """Ping all known nodes and return their reachability status."""
    try:
        engine = get_engine()
        results = await engine.heartbeat_all()
        return {"ok": True, "results": results}
    except Exception as e:
        logger.error("Heartbeat sweep failed: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}


# -- Pairing (Phase 3 stubs) -----------------------------------------------

@router.post("/pair", response_model=PairResponse)
async def node_pair(req: PairRequest):
    """Initiate pairing with a discovered node."""
    return PairResponse(
        node_id=req.node_id,
        pairing_state="not_implemented",
        error={"type": "not_implemented", "message": "Pairing available in Phase 3"},
    )


@router.post("/unpair", response_model=PairResponse)
async def node_unpair(req: PairRequest):
    """Remove pairing with a node."""
    return PairResponse(
        node_id=req.node_id,
        pairing_state="unpaired",
        error={"type": "not_implemented", "message": "Unpairing available in Phase 3"},
    )


# -- Job Distribution (Phase 4 stubs) --------------------------------------

@router.post("/distribute", response_model=DistributeResponse)
async def node_distribute(req: DistributeRequest):
    return DistributeResponse(
        error={"type": "not_implemented", "message": "Distribution available in Phase 4"},
    )


@router.get("/job/{job_id}", response_model=NodeJobStatusResponse)
async def node_job_status(job_id: str):
    return NodeJobStatusResponse(
        job_id=job_id,
        error={"type": "not_implemented", "message": "Job tracking available in Phase 4"},
    )


@router.post("/job/{job_id}/cancel")
async def node_job_cancel(job_id: str):
    return {"ok": False, "error": "Job cancellation available in Phase 4"}
