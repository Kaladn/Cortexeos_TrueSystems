"""Forest Network — main API router.

Mounted at /api/network/ on the Forest AI Bridge (port 5050).
Also includes the /api/network/serve/* sub-router for peer-to-peer calls.

Request flow:
  Browser → GET /api/network/files/{node_id}?path=...
                │
                ├─ node_id == "this" → serve locally (no outbound HTTP)
                │
                └─ node_id == <peer> → client.py → remote /api/network/serve/*
                                                    ← X-Forest-Node-Key auth →

Endpoints (public — for browser / UI):
    GET  /api/network/health
    GET  /api/network/files/{node_id}          ?path=   → browse directory
    GET  /api/network/files/{node_id}/read     ?path=   → stream file
    GET  /api/network/files/{node_id}/hash     ?path=   → SHA-256
    POST /api/network/files/{node_id}/write             → upload file

Endpoints (serve — for peer nodes, require X-Forest-Node-Key):
    GET  /api/network/serve/browse
    GET  /api/network/serve/read
    GET  /api/network/serve/hash
    POST /api/network/serve/write
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from . import client as _client
from .config import get_allow_root_paths, get_nodes
from .paths import resolve_and_validate
from .serve import router as _serve_router

LOGGER = logging.getLogger("forest.network")
_AUDIT = logging.getLogger("forest.network.audit")

router = APIRouter(prefix="/api/network", tags=["network"])
router.include_router(_serve_router)  # serve/* for peer traffic

_CHUNK = 65_536


def _is_local(node_id: str) -> bool:
    """True if node_id refers to this machine."""
    return node_id in ("this", "local")


def _audit(action: str, node: str, path: str, http_status: int, extra: str = "") -> None:
    _AUDIT.info(
        "%s | node=%r | path=%r | status=%d%s",
        action,
        node,
        path,
        http_status,
        f" | {extra}" if extra else "",
    )


def _wrap_remote_error(exc: Exception, node_id: str, action: str, path: str) -> HTTPException:
    """Convert client exceptions to HTTPException with consistent codes."""
    if isinstance(exc, _client.NodeNotFoundError):
        _audit(action, node_id, path, 404, str(exc))
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, _client.NodeAuthError):
        _audit(action, node_id, path, 500, str(exc))
        return HTTPException(status_code=500, detail=str(exc))
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        _audit(action, node_id, path, code, str(exc))
        return HTTPException(status_code=code, detail=f"Remote node error: {exc.response.text}")
    if isinstance(exc, httpx.RequestError):
        _audit(action, node_id, path, 502, str(exc))
        return HTTPException(
            status_code=502,
            detail=f"Cannot reach node {node_id!r}: {type(exc).__name__}",
        )
    _audit(action, node_id, path, 500, str(exc))
    return HTTPException(status_code=500, detail=f"Unexpected error: {exc}")


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health")
async def network_health() -> dict[str, Any]:
    """Plugin health check. Returns node count from config."""
    nodes = get_nodes()
    return {
        "ok": True,
        "plugin": "forest_network",
        "phase": 1,
        "nodes_configured": len(nodes),
    }


@router.get("/status")
async def network_status() -> dict[str, Any]:
    """Status alias used by plugin runner health polling."""
    health = await network_health()
    return {
        **health,
        "enabled": True,
        "mount": "/api/network",
    }


# ── Roots ──────────────────────────────────────────────────────────────────────

@router.get("/roots/{node_id}")
async def network_roots(node_id: str) -> dict[str, Any]:
    """Return the allow_roots for a node (local or remote).

    Used by the UI to populate the node tree sidebar.
    Response: { node_id, roots: ["docs/GENESIS", "Lexical Data/Canonical", ...] }
    """
    if _is_local(node_id):
        roots = get_allow_root_paths()
        _audit("ROOTS", node_id, "(all)", 200, f"count={len(roots)}")
        return {"node_id": node_id, "roots": roots}

    try:
        result = await _client.get_roots(node_id)
        result["node_id"] = node_id
        _audit("ROOTS", node_id, "(all)", 200, f"remote count={len(result.get('roots', []))}")
        return result
    except Exception as exc:
        raise _wrap_remote_error(exc, node_id, "ROOTS", "(all)") from exc


# ── Browse ─────────────────────────────────────────────────────────────────────

@router.get("/files/{node_id}")
async def network_browse(node_id: str, path: str = "/") -> dict[str, Any]:
    """Browse a directory on a node (local or remote proxy).

    Response: { node_id, path, entries: [{name, type, size|null, mtime}] }
    """
    if _is_local(node_id):
        resolved = resolve_and_validate(path)
        if not resolved.exists() or not resolved.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")

        entries: list[dict[str, Any]] = []
        for entry in sorted(resolved.iterdir(), key=lambda e: (e.is_file(), e.name)):
            try:
                st = entry.stat()
                entries.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": st.st_size if entry.is_file() else None,
                    "mtime": st.st_mtime,
                })
            except OSError:
                pass

        _audit("BROWSE", node_id, path, 200, f"entries={len(entries)}")
        return {"node_id": node_id, "path": path, "entries": entries}

    # Remote node — proxy via client
    try:
        result = await _client.browse(node_id, path)
        result["node_id"] = node_id
        _audit("BROWSE", node_id, path, 200, f"remote entries={len(result.get('entries', []))}")
        return result
    except Exception as exc:
        raise _wrap_remote_error(exc, node_id, "BROWSE", path) from exc


# ── Read ───────────────────────────────────────────────────────────────────────

@router.get("/files/{node_id}/read")
async def network_read(node_id: str, path: str) -> StreamingResponse:
    """Stream a file from a node (local or remote proxy)."""
    if _is_local(node_id):
        resolved = resolve_and_validate(path)
        if not resolved.exists() or not resolved.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        file_size = resolved.stat().st_size

        def _local_stream():
            with open(resolved, "rb") as fh:
                while chunk := fh.read(_CHUNK):
                    yield chunk

        _audit("READ", node_id, path, 200, f"bytes={file_size}")
        return StreamingResponse(
            _local_stream(),
            media_type="application/octet-stream",
            headers={"Content-Length": str(file_size), "X-Forest-Node": node_id},
        )

    # Remote node
    try:
        resp_headers, stream = await _client.read_stream(node_id, path)
        _audit("READ", node_id, path, 200, "remote stream")
        return StreamingResponse(
            stream,
            media_type="application/octet-stream",
            headers={k: v for k, v in resp_headers.items() if v},
        )
    except Exception as exc:
        raise _wrap_remote_error(exc, node_id, "READ", path) from exc


# ── Hash ───────────────────────────────────────────────────────────────────────

@router.get("/files/{node_id}/hash")
async def network_hash(node_id: str, path: str) -> dict[str, Any]:
    """Get SHA-256 of a file on a node (local or remote proxy).

    Response: { node_id, path, hash: "sha256:<hex>", size }
    """
    if _is_local(node_id):
        resolved = resolve_and_validate(path)
        if not resolved.exists() or not resolved.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        sha = hashlib.sha256()
        with open(resolved, "rb") as fh:
            while chunk := fh.read(_CHUNK):
                sha.update(chunk)

        digest = f"sha256:{sha.hexdigest()}"
        size = resolved.stat().st_size
        _audit("HASH", node_id, path, 200, f"{digest} size={size}")
        return {"node_id": node_id, "path": path, "hash": digest, "size": size}

    # Remote node
    try:
        result = await _client.hash_file(node_id, path)
        result["node_id"] = node_id
        _audit("HASH", node_id, path, 200, f"remote hash={result.get('hash', '?')}")
        return result
    except Exception as exc:
        raise _wrap_remote_error(exc, node_id, "HASH", path) from exc


# ── Write ──────────────────────────────────────────────────────────────────────

@router.post("/files/{node_id}/write", status_code=status.HTTP_200_OK)
async def network_write(
    node_id: str,
    path: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Write a file to a node (local or remote proxy).

    For "this" node: tmp → fsync → atomic rename (same as serve.serve_write).
    For remote nodes: read full upload body, forward via client.write_file.

    Response: { ok, node_id, path, bytes_written }
    """
    if _is_local(node_id):
        resolved = resolve_and_validate(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = resolved.parent / (resolved.name + ".forest_tmp")
        bytes_written = 0

        try:
            with open(tmp_path, "wb") as fh:
                while chunk := await file.read(_CHUNK):
                    fh.write(chunk)
                    bytes_written += len(chunk)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, resolved)
        except Exception as exc:
            LOGGER.error("Local write failed for %r: %s", path, exc)
            _audit("WRITE", node_id, path, 500, str(exc))
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Write failed: {exc}",
            )

        _audit("WRITE", node_id, path, 200, f"bytes={bytes_written}")
        return {"ok": True, "node_id": node_id, "path": path, "bytes_written": bytes_written}

    # Remote node — buffer upload then forward
    content = await file.read()
    filename = file.filename or Path(path).name

    try:
        result = await _client.write_file(node_id, path, content, filename)
        result["node_id"] = node_id
        _audit("WRITE", node_id, path, 200, f"remote bytes={result.get('bytes_written', '?')}")
        return result
    except Exception as exc:
        raise _wrap_remote_error(exc, node_id, "WRITE", path) from exc
