"""Forest Node Daemon -- standalone FastAPI service running on remote machines.

Listens on TCP :5052 (configurable).
Exposes /node/hello, /node/health, /node/caps for the controller to probe.
Exposes /node/auth/* for challenge/response pairing authentication.
Exposes /node/fs/* for file access (gated by pairing + access mode).

Usage (on the remote machine):
    python -m forest_node                           # allowlist only
    python -m forest_node --allow-full              # also allows full-system reads
    python -m forest_node --port 5052 --host 0.0.0.0
    python -m forest_node --generate-pairing-key    # regenerate key
    python -m forest_node --print-pairing-key       # show existing key
"""

from __future__ import annotations

import argparse
import logging
import os
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from forest_node.core.caps import get_local_caps
from forest_node.core.fs_access import (
    AccessMode,
    FileAccessState,
    check_mode_transition,
    is_reparse_point,
    list_directory,
    validate_path,
    validate_write_path,
)
from forest_node.core.hmac_auth import (
    NonceStore,
    generate_pairing_secret,
    issue_session_token,
    verify_challenge_response,
    verify_session_token,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("forest_node.daemon")

# ── Stable node identity ────────────────────────────────────
_NODE_ID = uuid.uuid4().hex[:12]
_BOOT_TIME = time.time()
_VERSION = "0.3.0"

# ── File access state (singleton) ───────────────────────────
_fs_state = FileAccessState()

# ── Pairing state ───────────────────────────────────────────
_pairing_secret: bytes = b""
_nonce_store = NonceStore()
_PAIRING_KEY_FILE: Path = Path()  # set in main()

app = FastAPI(title="Forest Node Daemon", version=_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Auth dependency ─────────────────────────────────────────

async def require_auth(authorization: str = Header(None)) -> None:
    """FastAPI dependency — verifies Forest session token.

    Expects: Authorization: Forest <token>
    Rejects with 401 if missing, malformed, expired, or invalid.
    """
    if not _pairing_secret:
        raise HTTPException(401, detail="No pairing key configured")
    if not authorization:
        raise HTTPException(401, detail="Authentication required")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Forest":
        raise HTTPException(401, detail="Invalid authorization format (expected: Forest <token>)")
    token = parts[1]
    if not verify_session_token(_pairing_secret, _NODE_ID, token):
        raise HTTPException(401, detail="Invalid or expired session token")


# ── /node/hello ─────────────────────────────────────────────
@app.get("/node/hello")
async def node_hello():
    """Quick liveness check — returns node identity."""
    return {
        "node_id": _NODE_ID,
        "version": _VERSION,
        "uptime_s": round(time.time() - _BOOT_TIME, 1),
    }


# ── /node/health ────────────────────────────────────────────
@app.get("/node/health")
async def node_health():
    """Health probe — used by controller heartbeat."""
    return {
        "node_id": _NODE_ID,
        "status": "ok",
        "uptime_s": round(time.time() - _BOOT_TIME, 1),
        "timestamp": time.time(),
    }


# ── /node/caps ──────────────────────────────────────────────
@app.get("/node/caps")
async def node_caps():
    """Return this machine's hardware capabilities."""
    caps = get_local_caps()
    return {"node_id": _NODE_ID, "caps": caps}


# ── Auth endpoints (no auth required) ──────────────────────

class SessionRequest(BaseModel):
    nonce: str
    response: str


@app.get("/node/auth/challenge")
async def auth_challenge():
    """Issue a single-use nonce for challenge/response auth."""
    if not _pairing_secret:
        raise HTTPException(503, detail="No pairing key configured on this daemon")
    nonce = _nonce_store.issue()
    return {"nonce": nonce}


@app.post("/node/auth/session")
async def auth_session(req: SessionRequest):
    """Verify challenge response, issue session token."""
    if not _pairing_secret:
        raise HTTPException(503, detail="No pairing key configured on this daemon")

    # Consume nonce (single-use, TTL-checked)
    if not _nonce_store.consume(req.nonce):
        raise HTTPException(401, detail="Invalid or expired nonce")

    # Verify HMAC response
    if not verify_challenge_response(_pairing_secret, req.nonce, req.response):
        raise HTTPException(401, detail="Invalid HMAC response — wrong pairing key")

    # Issue session token bound to this node
    token, expires_at = issue_session_token(_pairing_secret, _NODE_ID)
    return {
        "session_token": token,
        "expires_in": 3600,
        "node_id": _NODE_ID,
    }


# ── File access mode (auth required) ──────────────────────

class ModeRequest(BaseModel):
    mode: str = "locked"
    ttl_s: int = 0
    share_write: bool = False


@app.get("/node/fs/mode", dependencies=[Depends(require_auth)])
async def fs_get_mode():
    """Return current access mode state."""
    _fs_state.check_ttl()
    return {
        "mode": _fs_state.mode.value,
        "share_write": _fs_state.share_write,
        "expires_at": _fs_state.expires_at,
        "allowlist_roots": _fs_state.allowlist_roots,
        "full_requires_auth": not _fs_state.allow_full_flag,
    }


@app.post("/node/fs/mode", dependencies=[Depends(require_auth)])
async def fs_set_mode(req: ModeRequest):
    """Set access mode. Daemon enforces transition rules."""
    import time as _time

    mode = req.mode.lower().strip()
    error = check_mode_transition(_fs_state, mode)
    if error:
        raise HTTPException(403, detail=error)

    if mode == "locked":
        _fs_state.revert_to_locked()
    elif mode == "allowlist":
        _fs_state.mode = AccessMode.ALLOWLIST
        _fs_state.expires_at = (_time.time() + req.ttl_s) if req.ttl_s > 0 else 0.0
        _fs_state.share_write = req.share_write
    elif mode == "full":
        _fs_state.mode = AccessMode.FULL
        _fs_state.expires_at = (_time.time() + req.ttl_s) if req.ttl_s > 0 else 0.0
        _fs_state.share_write = req.share_write

    return {"ok": True, "mode": _fs_state.mode.value,
            "share_write": _fs_state.share_write, "expires_at": _fs_state.expires_at}


# ── File system endpoints (auth required) ──────────────────

def _validate(path_str: str):
    """Wrap fs_access.validate_path, translate exceptions to HTTP."""
    try:
        return validate_path(path_str, _fs_state)
    except PermissionError as e:
        raise HTTPException(403, detail=str(e))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@app.get("/node/fs/list", dependencies=[Depends(require_auth)])
async def fs_list(path: str = Query(..., description="Directory path to list")):
    """List directory contents. Requires access mode != locked."""
    validated = _validate(path)
    if not validated.is_dir():
        raise HTTPException(400, detail=f"Not a directory: {path}")
    try:
        entries = list_directory(validated, _fs_state)
    except PermissionError as e:
        raise HTTPException(403, detail=str(e))
    return {"entries": entries, "path": str(validated), "error": None}


@app.get("/node/fs/stat", dependencies=[Depends(require_auth)])
async def fs_stat(path: str = Query(..., description="File or directory path")):
    """Stat a single file or directory."""
    validated = _validate(path)
    if not validated.exists():
        raise HTTPException(404, detail=f"Not found: {path}")
    s = validated.stat()
    return {
        "name": validated.name,
        "is_dir": validated.is_dir(),
        "size": s.st_size,
        "modified": s.st_mtime,
        "path": str(validated),
        "is_junction": is_reparse_point(validated),
    }


@app.get("/node/fs/read", dependencies=[Depends(require_auth)])
async def fs_read(path: str = Query(..., description="File path to read")):
    """Stream file bytes to the caller. Read-only, pull only."""
    validated = _validate(path)
    if not validated.is_file():
        raise HTTPException(400, detail=f"Not a regular file: {path}")

    file_size = validated.stat().st_size
    if file_size > _fs_state.max_read_size:
        raise HTTPException(
            413,
            detail=f"File too large: {file_size} bytes (max {_fs_state.max_read_size})",
        )

    def _stream():
        with open(validated, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{validated.name}"',
            "Content-Length": str(file_size),
        },
    )


# ── File write endpoints (auth required) ──────────────────

def _validate_write(path_str: str, size: int = 0):
    """Wrap validate_write_path, translate exceptions to HTTP."""
    try:
        return validate_write_path(path_str, _fs_state, size)
    except PermissionError as e:
        msg = str(e)
        if "too large" in msg.lower():
            raise HTTPException(413, detail=msg)
        raise HTTPException(403, detail=msg)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


class WriteRequest(BaseModel):
    path: str
    content_b64: str


class MkdirRequest(BaseModel):
    path: str


class DeleteRequest(BaseModel):
    path: str


@app.post("/node/fs/write", dependencies=[Depends(require_auth)])
async def fs_write(req: WriteRequest):
    """Write a file (create or overwrite). Requires share_write enabled."""
    import base64

    try:
        raw = base64.b64decode(req.content_b64)
    except Exception:
        raise HTTPException(400, detail="Invalid base64 content")

    validated = _validate_write(req.path, len(raw))

    if not validated.parent.exists():
        raise HTTPException(400, detail=f"Parent directory does not exist: {validated.parent}")

    try:
        validated.write_bytes(raw)
    except PermissionError:
        raise HTTPException(403, detail=f"Permission denied: {validated}")
    except Exception as e:
        raise HTTPException(500, detail=f"Write failed: {e}")

    logger.info("fs/write: %s (%d bytes)", validated, len(raw))
    return {"ok": True, "path": str(validated), "size": len(raw)}


@app.post("/node/fs/mkdir", dependencies=[Depends(require_auth)])
async def fs_mkdir(req: MkdirRequest):
    """Create a directory. Requires share_write enabled."""
    validated = _validate_write(req.path)

    if validated.exists():
        raise HTTPException(400, detail=f"Already exists: {validated}")
    if not validated.parent.exists():
        raise HTTPException(400, detail=f"Parent directory does not exist: {validated.parent}")

    try:
        validated.mkdir()
    except PermissionError:
        raise HTTPException(403, detail=f"Permission denied: {validated}")
    except Exception as e:
        raise HTTPException(500, detail=f"mkdir failed: {e}")

    logger.info("fs/mkdir: %s", validated)
    return {"ok": True, "path": str(validated)}


@app.post("/node/fs/delete", dependencies=[Depends(require_auth)])
async def fs_delete(req: DeleteRequest):
    """Delete a file or empty directory. Requires share_write enabled."""
    validated = _validate_write(req.path)

    if not validated.exists():
        raise HTTPException(404, detail=f"Not found: {validated}")

    try:
        if validated.is_dir():
            validated.rmdir()  # fails if non-empty
        else:
            validated.unlink()
    except OSError as e:
        if "not empty" in str(e).lower() or "directory is not empty" in str(e).lower():
            raise HTTPException(400, detail="Directory is not empty")
        raise HTTPException(403, detail=f"Delete failed: {e}")

    logger.info("fs/delete: %s", validated)
    return {"ok": True, "path": str(validated)}


# ── Pairing key management ────────────────────────────────

def _load_or_create_key(key_file: Path, force_create: bool = False) -> bytes:
    """Load pairing key from disk, or generate and save a new one.

    Prints the key hex ONLY when creating a new key (not on every boot).
    """
    if key_file.exists() and not force_create:
        raw = key_file.read_bytes()
        logger.info("Pairing key loaded from %s", key_file)
        return raw

    secret = generate_pairing_secret()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(secret)
    hex_key = secret.hex()
    print(f"\n  *** NEW PAIRING KEY ***")
    print(f"  {hex_key}")
    print(f"  Copy this key to the controller. It will not be shown again.")
    print(f"  Use --print-pairing-key to display it later.\n")
    logger.info("New pairing key generated and saved to %s", key_file)
    return secret


# ── CLI entry point ─────────────────────────────────────────
def main():
    global _pairing_secret, _PAIRING_KEY_FILE

    parser = argparse.ArgumentParser(description="Forest Node Daemon")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5052, help="Listen port (default: 5052)")
    parser.add_argument("--allow-full", action="store_true",
                        help="Allow FULL read-only mode (operator consent)")
    parser.add_argument("--generate-pairing-key", action="store_true",
                        help="Regenerate pairing key (invalidates existing sessions)")
    parser.add_argument("--print-pairing-key", action="store_true",
                        help="Print current pairing key and exit")
    parser.add_argument("--pairing-key-file", type=str, default=None,
                        help="Path to pairing key file (default: data_paths/daemon_secret.key)")
    args = parser.parse_args()

    # Resolve key file path
    if args.pairing_key_file:
        _PAIRING_KEY_FILE = Path(args.pairing_key_file)
    else:
        try:
            from security.data_paths import FOREST_NODE_PAIRS_DIR
            _PAIRING_KEY_FILE = FOREST_NODE_PAIRS_DIR / "daemon_secret.key"
        except ImportError:
            _PAIRING_KEY_FILE = Path(__file__).parent / "daemon_secret.key"

    # --print-pairing-key: show key and exit
    if args.print_pairing_key:
        if _PAIRING_KEY_FILE.exists():
            print(_PAIRING_KEY_FILE.read_bytes().hex())
        else:
            print("No pairing key found. Start the daemon to generate one.")
        return

    _fs_state.allow_full_flag = args.allow_full

    # Load or create pairing key
    _pairing_secret = _load_or_create_key(_PAIRING_KEY_FILE, force_create=args.generate_pairing_key)

    mode_label = "allowlist + full" if args.allow_full else "allowlist only"
    logger.info("Starting Forest Node Daemon v%s on %s:%d (node_id=%s)",
                _VERSION, args.host, args.port, _NODE_ID)
    logger.info("  file mode = %s", mode_label)
    logger.info("  roots     = %s", _fs_state.allowlist_roots)
    logger.info("  pairing   = active (key loaded)")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
