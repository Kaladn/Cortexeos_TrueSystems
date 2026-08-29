"""Clearbox Node Daemon v0.6.0 — standalone service for any machine on the LAN.

Zero Clearbox repo dependencies. Deploys as a zip + pip install.

Features:
  - Hardware machine_id (survives reboots, IP changes)
  - mDNS auto-discovery (_clearbox._tcp.local.)
  - HMAC challenge/response pairing + session tokens
  - File access state machine (locked/allowlist/full + TTL)
  - Live telemetry endpoint (CPU/RAM/GPU utilization)
  - Capability advertisement (cores, RAM, GPU name/VRAM)

Usage (on any machine):
    python -m core.clearbox_node                           # allowlist only
    python -m core.clearbox_node --allow-full              # also allows full-system reads
    python -m core.clearbox_node --port 5060 --host 0.0.0.0
    python -m core.clearbox_node --generate-pairing-key    # regenerate key
    python -m core.clearbox_node --print-pairing-key       # show existing key
    python -m core.clearbox_node --no-discovery            # disable mDNS
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .core.identity import get_hostname, get_machine_id
from .core.caps import get_local_caps, get_telemetry
from .core.fs_access import (
    AccessMode,
    FileAccessState,
    check_mode_transition,
    is_reparse_point,
    list_directory,
    validate_path,
    validate_write_path,
)
from .core.hmac_auth import (
    NonceStore,
    generate_pairing_secret,
    issue_session_token,
    verify_challenge_response,
    verify_session_token,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("clearbox_node.daemon")


def _resolve_cors_origins() -> list[str]:
    raw = os.environ.get("CLEARBOX_NODE_ALLOWED_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "http://127.0.0.1:5050",  "http://localhost:5050",
        "https://127.0.0.1:5050", "https://localhost:5050",
        "http://127.0.0.1:8080",  "http://localhost:8080",
        "https://127.0.0.1:8080", "https://localhost:8080",
    ]


# ── Identity (hardware-based, deterministic) ──────────────
_NODE_ID = get_machine_id()
_HOSTNAME = get_hostname()
_BOOT_TIME = time.time()
_VERSION = "0.6.0"

# ── File access state (singleton) ─────────────────────────
_fs_state = FileAccessState()

# ── Pairing state ─────────────────────────────────────────
_pairing_secret: bytes = b""
_nonce_store = NonceStore()
_PAIRING_KEY_FILE: Path = Path()  # set in main()

# ── Discovery (set in main()) ─────────────────────────────
_discovery = None

app = FastAPI(title="Clearbox Node Daemon", version=_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_resolve_cors_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Clearbox-CSRF", "X-Trace-Id"],
    allow_credentials=False,
)


# ── Auth dependency ───────────────────────────────────────

async def require_auth(authorization: str = Header(None)) -> None:
    if not _pairing_secret:
        raise HTTPException(401, detail="No pairing key configured")
    if not authorization:
        raise HTTPException(401, detail="Authentication required")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Clearbox":
        raise HTTPException(401, detail="Invalid authorization format")
    if not verify_session_token(_pairing_secret, _NODE_ID, parts[1]):
        raise HTTPException(401, detail="Invalid or expired session token")


# ══════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS (no auth)
# ══════════════════════════════════════════════════════════

@app.get("/node/hello")
async def node_hello():
    return {
        "node_id": _NODE_ID,
        "machine_id": _NODE_ID,
        "hostname": _HOSTNAME,
        "version": _VERSION,
        "uptime_s": round(time.time() - _BOOT_TIME, 1),
    }


@app.get("/node/health")
async def node_health():
    return {
        "node_id": _NODE_ID,
        "machine_id": _NODE_ID,
        "hostname": _HOSTNAME,
        "status": "ok",
        "uptime_s": round(time.time() - _BOOT_TIME, 1),
        "timestamp": time.time(),
    }


@app.get("/node/caps")
async def node_caps():
    caps = get_local_caps()
    return {"node_id": _NODE_ID, "machine_id": _NODE_ID, "caps": caps}


@app.get("/node/telemetry")
async def node_telemetry():
    """Live CPU/RAM/GPU utilization — IoT read-only, no auth required."""
    telem = get_telemetry()
    telem["node_id"] = _NODE_ID
    telem["machine_id"] = _NODE_ID
    telem["hostname"] = _HOSTNAME
    return telem


@app.get("/node/peers")
async def node_peers():
    """Other nodes this daemon sees via mDNS."""
    if _discovery:
        return {"peers": _discovery.peers(), "self": _NODE_ID}
    return {"peers": [], "self": _NODE_ID, "discovery": "disabled"}


# ══════════════════════════════════════════════════════════
#  AUTH ENDPOINTS (no auth — used to establish auth)
# ══════════════════════════════════════════════════════════

class SessionRequest(BaseModel):
    nonce: str
    response: str


@app.get("/node/auth/challenge")
async def auth_challenge():
    if not _pairing_secret:
        raise HTTPException(503, detail="No pairing key configured on this daemon")
    nonce = _nonce_store.issue()
    return {"nonce": nonce}


@app.post("/node/auth/session")
async def auth_session(req: SessionRequest):
    if not _pairing_secret:
        raise HTTPException(503, detail="No pairing key configured on this daemon")
    if not _nonce_store.consume(req.nonce):
        raise HTTPException(401, detail="Invalid or expired nonce")
    if not verify_challenge_response(_pairing_secret, req.nonce, req.response):
        raise HTTPException(401, detail="Invalid HMAC response — wrong pairing key")
    token, expires_at = issue_session_token(_pairing_secret, _NODE_ID)
    return {"session_token": token, "expires_in": 3600, "node_id": _NODE_ID}


# ══════════════════════════════════════════════════════════
#  FILE ACCESS (auth required)
# ══════════════════════════════════════════════════════════

class ModeRequest(BaseModel):
    mode: str = "locked"
    ttl_s: int = 0
    share_write: bool = False


@app.get("/node/fs/mode", dependencies=[Depends(require_auth)])
async def fs_get_mode():
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
    mode = req.mode.lower().strip()
    error = check_mode_transition(_fs_state, mode)
    if error:
        raise HTTPException(403, detail=error)

    if mode == "locked":
        _fs_state.revert_to_locked()
    elif mode == "allowlist":
        _fs_state.mode = AccessMode.ALLOWLIST
        _fs_state.expires_at = (time.time() + req.ttl_s) if req.ttl_s > 0 else 0.0
        _fs_state.share_write = req.share_write
    elif mode == "full":
        _fs_state.mode = AccessMode.FULL
        _fs_state.expires_at = (time.time() + req.ttl_s) if req.ttl_s > 0 else 0.0
        _fs_state.share_write = req.share_write

    return {"ok": True, "mode": _fs_state.mode.value,
            "share_write": _fs_state.share_write, "expires_at": _fs_state.expires_at}


def _validate(path_str: str):
    try:
        return validate_path(path_str, _fs_state)
    except PermissionError as e:
        raise HTTPException(403, detail=str(e))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@app.get("/node/fs/list", dependencies=[Depends(require_auth)])
async def fs_list(path: str = Query(...)):
    validated = _validate(path)
    if not validated.is_dir():
        raise HTTPException(400, detail=f"Not a directory: {path}")
    try:
        entries = list_directory(validated, _fs_state)
    except PermissionError as e:
        raise HTTPException(403, detail=str(e))
    return {"entries": entries, "path": str(validated), "error": None}


@app.get("/node/fs/stat", dependencies=[Depends(require_auth)])
async def fs_stat(path: str = Query(...)):
    validated = _validate(path)
    if not validated.exists():
        raise HTTPException(404, detail=f"Not found: {path}")
    s = validated.stat()
    return {
        "name": validated.name, "is_dir": validated.is_dir(),
        "size": s.st_size, "modified": s.st_mtime,
        "path": str(validated), "is_junction": is_reparse_point(validated),
    }


@app.get("/node/fs/read", dependencies=[Depends(require_auth)])
async def fs_read(path: str = Query(...)):
    validated = _validate(path)
    if not validated.is_file():
        raise HTTPException(400, detail=f"Not a regular file: {path}")
    file_size = validated.stat().st_size
    if file_size > _fs_state.max_read_size:
        raise HTTPException(413, detail=f"File too large: {file_size} bytes")

    def _stream():
        with open(validated, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        _stream(), media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{validated.name}"',
                 "Content-Length": str(file_size)},
    )


# ── File write endpoints ──────────────────────────────────

def _validate_write(path_str: str, size: int = 0):
    try:
        return validate_write_path(path_str, _fs_state, size)
    except PermissionError as e:
        msg = str(e)
        raise HTTPException(413 if "too large" in msg.lower() else 403, detail=msg)
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
    import base64
    try:
        raw = base64.b64decode(req.content_b64)
    except Exception:
        raise HTTPException(400, detail="Invalid base64 content")
    validated = _validate_write(req.path, len(raw))
    if not validated.parent.exists():
        raise HTTPException(400, detail=f"Parent directory does not exist")
    try:
        validated.write_bytes(raw)
    except PermissionError:
        raise HTTPException(403, detail=f"Permission denied: {validated}")
    logger.info("fs/write: %s (%d bytes)", validated, len(raw))
    return {"ok": True, "path": str(validated), "size": len(raw)}


@app.post("/node/fs/mkdir", dependencies=[Depends(require_auth)])
async def fs_mkdir(req: MkdirRequest):
    validated = _validate_write(req.path)
    if validated.exists():
        raise HTTPException(400, detail=f"Already exists: {validated}")
    if not validated.parent.exists():
        raise HTTPException(400, detail=f"Parent directory does not exist")
    try:
        validated.mkdir()
    except PermissionError:
        raise HTTPException(403, detail=f"Permission denied: {validated}")
    logger.info("fs/mkdir: %s", validated)
    return {"ok": True, "path": str(validated)}


@app.post("/node/fs/delete", dependencies=[Depends(require_auth)])
async def fs_delete(req: DeleteRequest):
    validated = _validate_write(req.path)
    if not validated.exists():
        raise HTTPException(404, detail=f"Not found: {validated}")
    try:
        if validated.is_dir():
            validated.rmdir()
        else:
            validated.unlink()
    except OSError as e:
        if "not empty" in str(e).lower():
            raise HTTPException(400, detail="Directory is not empty")
        raise HTTPException(403, detail=f"Delete failed: {e}")
    logger.info("fs/delete: %s", validated)
    return {"ok": True, "path": str(validated)}


# ══════════════════════════════════════════════════════════
#  PAIRING KEY MANAGEMENT
# ══════════════════════════════════════════════════════════

def _load_or_create_key(key_file: Path, force_create: bool = False) -> bytes:
    if key_file.exists() and not force_create:
        raw = key_file.read_bytes()
        logger.info("Pairing key loaded from %s", key_file)
        return raw
    secret = generate_pairing_secret()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(secret)
    print(f"\n  *** NEW PAIRING KEY ***")
    print(f"  {secret.hex()}")
    print(f"  Copy this key to the controller. It will not be shown again.")
    print(f"  Use --print-pairing-key to display it later.\n")
    logger.info("New pairing key generated and saved to %s", key_file)
    return secret


# ══════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ══════════════════════════════════════════════════════════

def main():
    global _pairing_secret, _PAIRING_KEY_FILE, _discovery

    parser = argparse.ArgumentParser(description="Clearbox Node Daemon v0.6.0")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5060)
    parser.add_argument("--allow-full", action="store_true",
                        help="Allow FULL filesystem mode (operator consent)")
    parser.add_argument("--generate-pairing-key", action="store_true")
    parser.add_argument("--print-pairing-key", action="store_true")
    parser.add_argument("--pairing-key-file", type=str, default=None)
    parser.add_argument("--no-discovery", action="store_true",
                        help="Disable mDNS broadcast/browse")
    args = parser.parse_args()

    # Resolve key file path — no Clearbox imports required
    if args.pairing_key_file:
        _PAIRING_KEY_FILE = Path(args.pairing_key_file)
    else:
        try:
            from security.data_paths import CLEARBOX_NODE_PAIRS_DIR
            _PAIRING_KEY_FILE = CLEARBOX_NODE_PAIRS_DIR / "daemon_secret.key"
        except ImportError:
            _PAIRING_KEY_FILE = Path.home() / ".clearbox" / "daemon_secret.key"

    if args.print_pairing_key:
        if _PAIRING_KEY_FILE.exists():
            print(_PAIRING_KEY_FILE.read_bytes().hex())
        else:
            print("No pairing key found. Start the daemon to generate one.")
        return

    _fs_state.allow_full_flag = args.allow_full
    _pairing_secret = _load_or_create_key(
        _PAIRING_KEY_FILE, force_create=args.generate_pairing_key)

    # Start mDNS discovery
    if not args.no_discovery:
        try:
            from .core.discovery import MeshDiscovery
            caps = get_local_caps()
            _discovery = MeshDiscovery(machine_id=_NODE_ID, port=args.port)
            _discovery.set_properties(
                hostname=_HOSTNAME, version=_VERSION,
                caps={"cpu": caps["cpu_cores"], "ram": caps["ram_gb"],
                      "gpu": caps.get("gpu_name") or "none"},
            )
            _discovery.start()
        except ImportError:
            logger.warning("zeroconf not installed — mDNS discovery disabled")
        except Exception as e:
            logger.warning("mDNS discovery failed to start: %s", e)

    mode_label = "allowlist + full" if args.allow_full else "allowlist only"
    caps_info = get_local_caps()

    print(f"\n  Clearbox Node Daemon v{_VERSION}")
    print(f"  Machine ID:  {_NODE_ID}")
    print(f"  Hostname:    {_HOSTNAME}")
    print(f"  Listening:   http://{args.host}:{args.port}")
    print(f"  File mode:   {mode_label}")
    print(f"  CPU cores:   {caps_info['cpu_cores']}")
    print(f"  RAM:         {caps_info['ram_gb']} GB")
    print(f"  GPU:         {caps_info.get('gpu_name') or 'none'}")
    print(f"  Discovery:   {'active' if _discovery else 'disabled'}")
    print()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
