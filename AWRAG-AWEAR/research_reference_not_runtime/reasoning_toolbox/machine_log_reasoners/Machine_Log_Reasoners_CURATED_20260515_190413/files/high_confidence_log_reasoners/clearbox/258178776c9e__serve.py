"""Forest Network — local serve endpoints.

These endpoints are called BY remote peer nodes (bridge-to-bridge traffic).
They expose the local filesystem within allow_roots over authenticated HTTP.

All endpoints require X-Forest-Node-Key header validated by auth.require_node_key.
All paths are validated by paths.resolve_and_validate before any disk access.

Endpoints:
    GET  /api/network/serve/roots              → this node's allow_roots (for peer discovery)
    GET  /api/network/serve/browse  ?path=...  → JSON directory listing
    GET  /api/network/serve/read    ?path=...  → streamed file content
    GET  /api/network/serve/hash    ?path=...  → SHA-256 of file
    POST /api/network/serve/write              → write file (tmp → fsync → rename)

Write safety:
    1. Write to <filename>.forest_tmp in same directory
    2. os.fsync() to flush OS buffer to disk
    3. os.replace() atomic rename — destination is never half-written
    4. Temp file cleaned up on any error

Audit log:
    Every request (success or failure) emits one line to forest.network.audit logger.
    Format: ACTION | path=... | status=... | extra
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from .auth import require_node_key
from .config import get_allow_root_paths
from .paths import resolve_and_validate

LOGGER = logging.getLogger("forest.network.serve")
_AUDIT = logging.getLogger("forest.network.audit")

router = APIRouter(prefix="/api/network/serve", tags=["network-serve"])

_CHUNK = 65_536  # 64 KB read/write chunk


def _audit(action: str, path: str, http_status: int, extra: str = "") -> None:
    _AUDIT.info(
        "%s | path=%r | status=%d%s",
        action,
        path,
        http_status,
        f" | {extra}" if extra else "",
    )


# ── Roots (peer discovery) ────────────────────────────────────────────────────

@router.get("/roots")
async def serve_roots(
    _key: str = Depends(require_node_key),
) -> dict[str, Any]:
    """Return this node's allow_roots for peer discovery.

    Response: { roots: ["docs/GENESIS", "Lexical Data/Canonical", ...] }
    """
    roots = get_allow_root_paths()
    _audit("ROOTS", "(all)", 200, f"count={len(roots)}")
    return {"roots": roots}


# ── Browse ────────────────────────────────────────────────────────────────────

@router.get("/browse")
async def serve_browse(
    path: str = "/",
    _key: str = Depends(require_node_key),
) -> dict[str, Any]:
    """Return a JSON directory listing for the given path.

    Response: { path, entries: [{name, type, size|null, mtime}] }
    """
    resolved = resolve_and_validate(path)

    if not resolved.exists():
        _audit("BROWSE", path, 404)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found")

    if not resolved.is_dir():
        _audit("BROWSE", path, 400)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a directory",
        )

    entries: list[dict[str, Any]] = []
    try:
        for entry in sorted(resolved.iterdir(), key=lambda e: (e.is_file(), e.name)):
            try:
                st = entry.stat()
                entries.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": st.st_size if entry.is_file() else None,
                    "mtime": st.st_mtime,
                })
            except (PermissionError, OSError):
                pass  # skip unreadable entries silently
    except PermissionError as exc:
        _audit("BROWSE", path, 403, str(exc))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    _audit("BROWSE", path, 200, f"entries={len(entries)}")
    return {"path": path, "entries": entries}


# ── Read (stream) ──────────────────────────────────────────────────────────────

@router.get("/read")
async def serve_read(
    path: str,
    _key: str = Depends(require_node_key),
) -> StreamingResponse:
    """Stream the raw bytes of a file.

    Supports partial content via standard Range header (passthrough — httpx on
    the client side handles reassembly; full-file streaming in Phase 1).
    """
    resolved = resolve_and_validate(path)

    if not resolved.exists():
        _audit("READ", path, 404)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if not resolved.is_file():
        _audit("READ", path, 400)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a file",
        )

    file_size = resolved.stat().st_size

    def _stream():
        with open(resolved, "rb") as fh:
            while chunk := fh.read(_CHUNK):
                yield chunk

    _audit("READ", path, 200, f"bytes={file_size}")
    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={
            "Content-Length": str(file_size),
            "X-Forest-Path": path,
        },
    )


# ── Hash ──────────────────────────────────────────────────────────────────────

@router.get("/hash")
async def serve_hash(
    path: str,
    _key: str = Depends(require_node_key),
) -> dict[str, Any]:
    """Return SHA-256 digest of a file for integrity verification.

    Response: { path, hash: "sha256:<hex>", size }
    """
    resolved = resolve_and_validate(path)

    if not resolved.exists():
        _audit("HASH", path, 404)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if not resolved.is_file():
        _audit("HASH", path, 400)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a file",
        )

    sha = hashlib.sha256()
    with open(resolved, "rb") as fh:
        while chunk := fh.read(_CHUNK):
            sha.update(chunk)

    digest = f"sha256:{sha.hexdigest()}"
    size = resolved.stat().st_size
    _audit("HASH", path, 200, f"{digest} size={size}")
    return {"path": path, "hash": digest, "size": size}


# ── Write (tmp → fsync → atomic rename) ──────────────────────────────────────

@router.post("/write", status_code=status.HTTP_200_OK)
async def serve_write(
    path: str = Form(...),
    file: UploadFile = File(...),
    _key: str = Depends(require_node_key),
) -> dict[str, Any]:
    """Write a file atomically.

    Pipeline:
      1. Validate path is within allow_roots
      2. Write upload to <name>.forest_tmp in the same directory
      3. os.fsync() — flush OS write buffer to disk
      4. os.replace() — atomic rename (POSIX); best-effort on Windows
      5. On any error: delete tmp file, return 500

    Response: { ok, path, bytes_written }
    """
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

        os.replace(tmp_path, resolved)  # atomic on POSIX; best-effort on Windows

    except Exception as exc:
        LOGGER.error("Write failed for %r: %s", path, exc)
        _audit("WRITE", path, 500, str(exc))
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Write failed: {exc}",
        )

    _audit("WRITE", path, 200, f"bytes={bytes_written}")
    return {"ok": True, "path": path, "bytes_written": bytes_written}
