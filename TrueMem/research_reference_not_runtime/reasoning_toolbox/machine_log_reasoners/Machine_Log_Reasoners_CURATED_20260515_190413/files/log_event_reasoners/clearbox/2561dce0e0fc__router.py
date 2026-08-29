"""Forest Node API Router -- FastAPI endpoints for distributed computing.

Mounted on the bridge server at /api/nodes.
All imports are lazy -- bridge server boots fine even if forest_node deps are missing.

Security:  Protected endpoints live on _protected (sub-router) which requires a valid
Windows Hello session via require_hello_session (Phase 3C).
"""

from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, Depends

from fastapi.responses import Response

from forest_node.api.models import (
    FileAccessModeRequest,
    FileAccessModeResponse,
    FileDeleteRequest,
    FileListRequest,
    FileListResponse,
    FileMkdirRequest,
    FileReadRequest,
    FileWriteRequest,
    FileWriteResponse,
    NodeListResponse,
    NodeStatusResponse,
    PairRequest,
    PairResponse,
    RegisterRequest,
    RegisterResponse,
    RemoveNodeRequest,
    UnpairRequest,
)
from forest_node.core.session_gate import require_hello_session

logger = logging.getLogger(__name__)

# -- Public router (mounted by bridge) ----------------------------------------

router = APIRouter(prefix="/api/nodes", tags=["forest_node"])

# -- Protected sub-router (Windows Hello required) ----------------------------

_protected = APIRouter(dependencies=[Depends(require_hello_session)])


# -- Singleton Engine ---------------------------------------------------------

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """Get or create the NodeEngine singleton. Lazy-loaded, thread-safe."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from forest_node.core.engine import NodeEngine
                _engine = NodeEngine()
    return _engine


# =============================================================================
# PUBLIC ENDPOINTS (no auth required)
# =============================================================================

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
        )
    except Exception as e:
        logger.error("Forest Node list error: %s", e, exc_info=True)
        return NodeListResponse(error={"type": "list_error", "message": str(e)})


# -- Registration (Phase 2 -- manual add by IP:port) -----------------------

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


# =============================================================================
# PROTECTED ENDPOINTS (Windows Hello session required)
# =============================================================================

# -- File Access Proxy (Phase 3A) ------------------------------------------

@_protected.get("/fs/mode/{node_id}", response_model=FileAccessModeResponse)
async def node_fs_get_mode(node_id: str, user_id: str = Depends(require_hello_session)):
    """Get file access mode from a remote node."""
    try:
        engine = get_engine()
        data = await engine.proxy_get_mode(node_id)
        return FileAccessModeResponse(**data)
    except ValueError as e:
        return FileAccessModeResponse(node_id=node_id,
                                      error={"type": "not_found", "message": str(e)})
    except Exception as e:
        logger.error("fs/mode GET failed for %s: %s", node_id, e)
        return FileAccessModeResponse(node_id=node_id,
                                      error={"type": "proxy_error", "message": str(e)})


@_protected.post("/fs/mode", response_model=FileAccessModeResponse)
async def node_fs_set_mode(req: FileAccessModeRequest, user_id: str = Depends(require_hello_session)):
    """Set file access mode on a remote node."""
    try:
        engine = get_engine()
        data = await engine.proxy_set_mode(req.node_id, req.mode, req.ttl_s, req.share_write)
        if data.get("error"):
            return FileAccessModeResponse(
                node_id=req.node_id,
                error={"type": "daemon_rejected", "message": data["error"]},
            )
        return FileAccessModeResponse(
            mode=data.get("mode", "locked"),
            expires_at=data.get("expires_at", 0.0),
            node_id=req.node_id,
            share_write=data.get("share_write", False),
        )
    except ValueError as e:
        return FileAccessModeResponse(node_id=req.node_id,
                                      error={"type": "not_found", "message": str(e)})
    except Exception as e:
        logger.error("fs/mode POST failed for %s: %s", req.node_id, e)
        return FileAccessModeResponse(node_id=req.node_id,
                                      error={"type": "proxy_error", "message": str(e)})


@_protected.post("/fs/list", response_model=FileListResponse)
async def node_fs_list(req: FileListRequest, user_id: str = Depends(require_hello_session)):
    """List directory on a remote node (proxied)."""
    try:
        engine = get_engine()
        data = await engine.proxy_file_list(req.node_id, req.path)
        return FileListResponse(**data)
    except ValueError as e:
        return FileListResponse(node_id=req.node_id, path=req.path,
                                error={"type": "not_found", "message": str(e)})
    except Exception as e:
        logger.error("fs/list failed for %s: %s", req.node_id, e)
        return FileListResponse(node_id=req.node_id, path=req.path,
                                error={"type": "proxy_error", "message": str(e)})


@_protected.post("/fs/read")
async def node_fs_read(req: FileReadRequest, user_id: str = Depends(require_hello_session)):
    """Read a file from a remote node (proxied). Returns raw bytes."""
    try:
        engine = get_engine()
        content, filename, size = await engine.proxy_file_read(req.node_id, req.path)
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(size),
            },
        )
    except ValueError as e:
        return {"error": {"type": "read_error", "message": str(e)}}
    except Exception as e:
        logger.error("fs/read failed for %s: %s", req.node_id, e)
        return {"error": {"type": "proxy_error", "message": str(e)}}


# -- File Write Proxy (Phase 3D) -------------------------------------------

@_protected.post("/fs/write", response_model=FileWriteResponse)
async def node_fs_write(req: FileWriteRequest, user_id: str = Depends(require_hello_session)):
    """Write a file on a remote node (proxied). Requires share_write enabled."""
    try:
        engine = get_engine()
        data = await engine.proxy_file_write(req.node_id, req.path, req.content_b64)
        return FileWriteResponse(**data)
    except ValueError as e:
        return FileWriteResponse(node_id=req.node_id,
                                 error={"type": "not_found", "message": str(e)})
    except Exception as e:
        logger.error("fs/write failed for %s: %s", req.node_id, e)
        return FileWriteResponse(node_id=req.node_id,
                                 error={"type": "proxy_error", "message": str(e)})


@_protected.post("/fs/mkdir", response_model=FileWriteResponse)
async def node_fs_mkdir(req: FileMkdirRequest, user_id: str = Depends(require_hello_session)):
    """Create a directory on a remote node (proxied). Requires share_write enabled."""
    try:
        engine = get_engine()
        data = await engine.proxy_file_mkdir(req.node_id, req.path)
        return FileWriteResponse(**data)
    except ValueError as e:
        return FileWriteResponse(node_id=req.node_id,
                                 error={"type": "not_found", "message": str(e)})
    except Exception as e:
        logger.error("fs/mkdir failed for %s: %s", req.node_id, e)
        return FileWriteResponse(node_id=req.node_id,
                                 error={"type": "proxy_error", "message": str(e)})


@_protected.post("/fs/delete", response_model=FileWriteResponse)
async def node_fs_delete(req: FileDeleteRequest, user_id: str = Depends(require_hello_session)):
    """Delete a file or empty directory on a remote node (proxied)."""
    try:
        engine = get_engine()
        data = await engine.proxy_file_delete(req.node_id, req.path)
        return FileWriteResponse(**data)
    except ValueError as e:
        return FileWriteResponse(node_id=req.node_id,
                                 error={"type": "not_found", "message": str(e)})
    except Exception as e:
        logger.error("fs/delete failed for %s: %s", req.node_id, e)
        return FileWriteResponse(node_id=req.node_id,
                                 error={"type": "proxy_error", "message": str(e)})


# -- Pairing (Phase 3B) ----------------------------------------------------

@_protected.post("/pair", response_model=PairResponse)
async def node_pair(req: PairRequest, user_id: str = Depends(require_hello_session)):
    """Pair with a node using its pairing secret.

    Validates the hex key, verifies it against the daemon via challenge/response,
    then stores it DPAPI-encrypted on the controller.
    """
    try:
        engine = get_engine()
        hex_key = req.secret_hex.strip().lower()

        # Validate hex string format
        if len(hex_key) != 64:
            return PairResponse(
                node_id=req.node_id, pairing_state="error",
                error={"type": "invalid_key",
                       "message": "Key must be 64 hex characters (32 bytes)"},
            )
        try:
            bytes.fromhex(hex_key)
        except ValueError:
            return PairResponse(
                node_id=req.node_id, pairing_state="error",
                error={"type": "invalid_key", "message": "Key contains invalid hex characters"},
            )

        # Verify against daemon (challenge/response)
        token = await engine.verify_pairing(req.node_id, hex_key)
        if token:
            engine.store_pairing_secret(req.node_id, hex_key)
            logger.info("Pair from user=%s node=%s", user_id, req.node_id)
            return PairResponse(node_id=req.node_id, pairing_state="paired")

        return PairResponse(
            node_id=req.node_id, pairing_state="rejected",
            error={"type": "pairing_rejected",
                   "message": "Daemon rejected the pairing key"},
        )
    except Exception as e:
        logger.error("Pairing failed for %s: %s", req.node_id, e)
        return PairResponse(
            node_id=req.node_id, pairing_state="error",
            error={"type": "pairing_error", "message": str(e)},
        )


@_protected.post("/unpair", response_model=PairResponse)
async def node_unpair(req: UnpairRequest, user_id: str = Depends(require_hello_session)):
    """Remove pairing with a node. Clears stored secret and cached session."""
    try:
        engine = get_engine()
        engine.remove_pairing(req.node_id)
        logger.info("Unpair from user=%s node=%s", user_id, req.node_id)
        return PairResponse(node_id=req.node_id, pairing_state="unpaired")
    except Exception as e:
        logger.error("Unpair failed for %s: %s", req.node_id, e)
        return PairResponse(
            node_id=req.node_id, pairing_state="error",
            error={"type": "unpair_error", "message": str(e)},
        )


# -- Mount protected sub-router into public router ----------------------------

router.include_router(_protected)
