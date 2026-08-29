"""Forest Node Daemon — STANDALONE single-file version (v0.3.0).

Copy this ONE file to any machine. Run it:
    pip install fastapi uvicorn
    python node_daemon_standalone.py

File access:
    By default the daemon starts LOCKED (no file access).
    The controller can switch to ALLOWLIST mode (reads within configured dirs).
    FULL mode requires the operator to start with --allow-full.

    python node_daemon_standalone.py                  # allowlist only
    python node_daemon_standalone.py --allow-full     # also allows full-system reads

Authentication (Phase 3B):
    All /node/fs/* endpoints require a valid session token.
    First run generates a pairing key and prints it to console.

    python node_daemon_standalone.py --print-pairing-key    # show existing key
    python node_daemon_standalone.py --generate-pairing-key # regenerate key

Env vars:
    PORT           — listen port (default 5052)
    ALLOWED_ROOTS  — comma-separated allowlist dirs (default: ~/Documents,~/Desktop,~/Downloads)
    MAX_READ_SIZE  — max file read in bytes (default 104857600 = 100 MB)
"""

import argparse
import ctypes
import hashlib
import hmac as hmac_mod
import os
import platform
import secrets
import socket
import stat as stat_module
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── Identity ──────────────────────────────────────────────────
_NODE_ID = uuid.uuid4().hex[:12]
_BOOT_TIME = time.time()
_VERSION = "0.5.0"

# ── Access mode state (daemon is the authority) ───────────────
_ACCESS_MODE = "locked"          # "locked" | "allowlist" | "full"
_MODE_EXPIRES_AT = 0.0           # epoch; 0 = no TTL
_ALLOW_FULL_FLAG = False         # set by --allow-full CLI flag (operator consent)
_SHARE_WRITE = False             # write access flag (Phase 3D)

# Allowlist roots — configurable via ALLOWED_ROOTS env var
_user_home = Path.home()
_DEFAULT_ROOTS = [
    str(_user_home / "Documents"),
    str(_user_home / "Desktop"),
    str(_user_home / "Downloads"),
]
_raw_roots = os.environ.get("ALLOWED_ROOTS", "")
_ALLOWLIST_ROOTS = [r.strip() for r in _raw_roots.split(",") if r.strip()] if _raw_roots else _DEFAULT_ROOTS

_MAX_READ_SIZE = int(os.environ.get("MAX_READ_SIZE", "104857600"))  # 100 MB
_MAX_WRITE_SIZE = int(os.environ.get("MAX_WRITE_SIZE", "10485760"))  # 10 MB

# ── Pairing state ─────────────────────────────────────────────
_pairing_secret: bytes = b""
_PAIRING_KEY_FILE: Path = Path()  # set in __main__

# ── Inlined HMAC auth (no forest_node imports) ────────────────

def _generate_pairing_secret() -> bytes:
    return secrets.token_bytes(32)

def _create_nonce() -> str:
    return secrets.token_hex(16)

def _verify_challenge_response(secret: bytes, nonce: str, response: str) -> bool:
    expected = hmac_mod.new(secret, nonce.encode(), hashlib.sha256).hexdigest()
    return hmac_mod.compare_digest(expected, response)

def _issue_session_token(secret: bytes, node_id: str, ttl_s: int = 3600):
    issued = int(time.time())
    expires = issued + ttl_s
    payload = f"session:{node_id}:{issued}:{expires}"
    sig = hmac_mod.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return f"{issued}:{expires}:{sig}", expires

def _verify_session_token(secret: bytes, node_id: str, token: str) -> bool:
    parts = token.split(":")
    if len(parts) != 3:
        return False
    issued_str, expires_str, sig = parts
    try:
        if time.time() > float(expires_str):
            return False
    except (ValueError, OverflowError):
        return False
    payload = f"session:{node_id}:{issued_str}:{expires_str}"
    expected = hmac_mod.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return hmac_mod.compare_digest(expected, sig)

class _NonceStore:
    def __init__(self, max_pending: int = 50, ttl_s: float = 60.0):
        self._nonces = {}
        self._max = max_pending
        self._ttl = ttl_s

    def issue(self) -> str:
        self._evict()
        if len(self._nonces) >= self._max:
            oldest = min(self._nonces, key=self._nonces.get)
            del self._nonces[oldest]
        nonce = _create_nonce()
        self._nonces[nonce] = time.time()
        return nonce

    def consume(self, nonce: str) -> bool:
        self._evict()
        if nonce in self._nonces:
            del self._nonces[nonce]
            return True
        return False

    def _evict(self):
        cutoff = time.time() - self._ttl
        self._nonces = {k: v for k, v in self._nonces.items() if v > cutoff}

_nonce_store = _NonceStore()

# ── FastAPI app ───────────────────────────────────────────────
app = FastAPI(title="Forest Node Daemon", version=_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Auth dependency ───────────────────────────────────────────

async def _require_auth(authorization: str = Header(None)) -> None:
    if not _pairing_secret:
        raise HTTPException(401, detail="No pairing key configured")
    if not authorization:
        raise HTTPException(401, detail="Authentication required")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Forest":
        raise HTTPException(401, detail="Invalid authorization format (expected: Forest <token>)")
    token = parts[1]
    if not _verify_session_token(_pairing_secret, _NODE_ID, token):
        raise HTTPException(401, detail="Invalid or expired session token")


# ── Helpers: hardware caps ────────────────────────────────────

def _get_caps():
    ram = 0.0
    try:
        class MEMSTAT(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        ms = MEMSTAT()
        ms.dwLength = ctypes.sizeof(MEMSTAT)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
        ram = round(ms.ullTotalPhys / (1024 ** 3), 1)
    except Exception:
        pass

    gpu_name = None
    vram_gb = None
    gpu_backend_str = None
    try:
        # torch.cuda.* works for both NVIDIA CUDA and AMD ROCm builds
        from bridges.gpu_backend import gpu_available, gpu_device_name, gpu_version_string
        import torch
        if gpu_available():
            gpu_name = gpu_device_name(0)
            gpu_backend_str = gpu_version_string()
            vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
    except Exception:
        pass

    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "cpu_cores": os.cpu_count() or 0,
        "ram_gb": ram,
        "gpu_name": gpu_name,
        "vram_gb": vram_gb,
    }


# ── Helpers: access mode + path validation ────────────────────

def _revert_to_locked():
    """Reset to LOCKED. Called on TTL expiry."""
    global _ACCESS_MODE, _MODE_EXPIRES_AT, _SHARE_WRITE
    _ACCESS_MODE = "locked"
    _MODE_EXPIRES_AT = 0.0
    _SHARE_WRITE = False


def _is_reparse_point(p: Path) -> bool:
    """Check if path is a Windows reparse point (junction/symlink)."""
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
        if attrs == -1:  # INVALID_FILE_ATTRIBUTES
            return False
        return bool(attrs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except Exception:
        return False


def _path_within_roots(resolved: Path, roots: list) -> bool:
    """Check if resolved path falls within at least one root."""
    resolved_str = str(resolved)
    for root in roots:
        root_resolved = str(Path(root).resolve())
        if resolved_str.startswith(root_resolved):
            return True
    return False


def _validate_path(path_str: str) -> Path:
    """Resolve path, enforce access mode.

    Returns the validated resolved Path.
    Raises HTTPException(403) on any violation.
    """
    global _ACCESS_MODE, _MODE_EXPIRES_AT

    if _ACCESS_MODE == "locked":
        raise HTTPException(403, detail="File access is locked")

    # TTL check
    if _MODE_EXPIRES_AT > 0 and time.time() > _MODE_EXPIRES_AT:
        _revert_to_locked()
        raise HTTPException(403, detail="Access mode expired, reverted to locked")

    if not path_str or not path_str.strip():
        raise HTTPException(400, detail="Path is required")

    resolved = Path(path_str).resolve()

    if _ACCESS_MODE == "allowlist":
        if not _path_within_roots(resolved, _ALLOWLIST_ROOTS):
            raise HTTPException(403, detail="Path outside allowed roots")
        return resolved

    if _ACCESS_MODE == "full":
        return resolved

    raise HTTPException(403, detail="Unknown access mode")


def _list_directory(dir_path: Path) -> list:
    """List directory entries with junction/reparse detection."""
    entries = []
    try:
        for entry in sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            try:
                entry_stat = entry.stat()
                is_dir = entry.is_dir()
                is_junction = _is_reparse_point(entry)

                # Junction defense: check if resolved target escapes allowed roots
                traversable = True
                if is_junction and _ACCESS_MODE == "allowlist":
                    try:
                        junction_target = entry.resolve()
                        if not _path_within_roots(junction_target, _ALLOWLIST_ROOTS):
                            traversable = False
                    except Exception:
                        traversable = False

                entries.append({
                    "name": entry.name,
                    "is_dir": is_dir,
                    "size": entry_stat.st_size if not is_dir else 0,
                    "modified": entry_stat.st_mtime,
                    "is_junction": is_junction,
                    "traversable": traversable if is_dir else True,
                })
            except PermissionError:
                entries.append({
                    "name": entry.name,
                    "is_dir": False,
                    "size": 0,
                    "modified": 0.0,
                    "is_junction": False,
                    "traversable": False,
                })
            except Exception:
                pass
    except PermissionError:
        raise HTTPException(403, detail=f"Permission denied: {dir_path}")
    return entries


# ── Existing endpoints (always available) ─────────────────────

@app.get("/node/hello")
async def hello():
    return {"node_id": _NODE_ID, "version": _VERSION, "uptime_s": round(time.time() - _BOOT_TIME, 1)}


@app.get("/node/health")
async def health():
    return {
        "node_id": _NODE_ID,
        "status": "ok",
        "uptime_s": round(time.time() - _BOOT_TIME, 1),
        "timestamp": time.time(),
    }


@app.get("/node/caps")
async def caps():
    return {"node_id": _NODE_ID, "caps": _get_caps()}


# ── Auth endpoints (no auth required) ────────────────────────

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

    if not _nonce_store.consume(req.nonce):
        raise HTTPException(401, detail="Invalid or expired nonce")

    if not _verify_challenge_response(_pairing_secret, req.nonce, req.response):
        raise HTTPException(401, detail="Invalid HMAC response — wrong pairing key")

    token, expires_at = _issue_session_token(_pairing_secret, _NODE_ID)
    return {
        "session_token": token,
        "expires_in": 3600,
        "node_id": _NODE_ID,
    }


# ── File access mode endpoints (auth required) ───────────────

class ModeRequest(BaseModel):
    mode: str = "locked"   # "locked" | "allowlist" | "full"
    ttl_s: int = 0         # 0 = no TTL
    share_write: bool = False


@app.get("/node/fs/mode", dependencies=[Depends(_require_auth)])
async def fs_get_mode():
    """Return current access mode state."""
    # Auto-expire if TTL passed
    if _MODE_EXPIRES_AT > 0 and time.time() > _MODE_EXPIRES_AT:
        _revert_to_locked()
    return {
        "mode": _ACCESS_MODE,
        "share_write": _SHARE_WRITE,
        "expires_at": _MODE_EXPIRES_AT,
        "allowlist_roots": _ALLOWLIST_ROOTS,
        "full_requires_auth": not _ALLOW_FULL_FLAG,
    }


@app.post("/node/fs/mode", dependencies=[Depends(_require_auth)])
async def fs_set_mode(req: ModeRequest):
    """Set access mode. Daemon enforces transition rules."""
    global _ACCESS_MODE, _MODE_EXPIRES_AT, _SHARE_WRITE

    mode = req.mode.lower().strip()

    # Lock is always allowed (safe direction)
    if mode == "locked":
        _revert_to_locked()
        return {"ok": True, "mode": _ACCESS_MODE,
                "share_write": _SHARE_WRITE, "expires_at": _MODE_EXPIRES_AT}

    # Allowlist — allowed (pairing already verified by auth middleware)
    if mode == "allowlist":
        _ACCESS_MODE = "allowlist"
        _MODE_EXPIRES_AT = (time.time() + req.ttl_s) if req.ttl_s > 0 else 0.0
        _SHARE_WRITE = req.share_write
        return {"ok": True, "mode": _ACCESS_MODE,
                "share_write": _SHARE_WRITE, "expires_at": _MODE_EXPIRES_AT}

    # Full — requires --allow-full flag (daemon-side gate)
    if mode == "full":
        if not _ALLOW_FULL_FLAG:
            raise HTTPException(
                403,
                detail="FULL mode requires --allow-full flag on daemon startup (operator consent)",
            )
        _ACCESS_MODE = "full"
        _MODE_EXPIRES_AT = (time.time() + req.ttl_s) if req.ttl_s > 0 else 0.0
        _SHARE_WRITE = req.share_write
        return {"ok": True, "mode": _ACCESS_MODE,
                "share_write": _SHARE_WRITE, "expires_at": _MODE_EXPIRES_AT}

    raise HTTPException(400, detail=f"Unknown mode: {mode}")


# ── File system endpoints (auth required) ─────────────────────

@app.get("/node/fs/list", dependencies=[Depends(_require_auth)])
async def fs_list(path: str = Query(..., description="Directory path to list")):
    """List directory contents. Requires access mode != locked."""
    validated = _validate_path(path)
    if not validated.is_dir():
        raise HTTPException(400, detail=f"Not a directory: {path}")
    entries = _list_directory(validated)
    return {"entries": entries, "path": str(validated), "error": None}


@app.get("/node/fs/stat", dependencies=[Depends(_require_auth)])
async def fs_stat(path: str = Query(..., description="File or directory path")):
    """Stat a single file or directory."""
    validated = _validate_path(path)
    if not validated.exists():
        raise HTTPException(404, detail=f"Not found: {path}")
    s = validated.stat()
    return {
        "name": validated.name,
        "is_dir": validated.is_dir(),
        "size": s.st_size,
        "modified": s.st_mtime,
        "path": str(validated),
        "is_junction": _is_reparse_point(validated),
    }


@app.get("/node/fs/read", dependencies=[Depends(_require_auth)])
async def fs_read(path: str = Query(..., description="File path to read")):
    """Stream file bytes to the caller. Read-only, pull only."""
    validated = _validate_path(path)
    if not validated.is_file():
        raise HTTPException(400, detail=f"Not a regular file: {path}")

    file_size = validated.stat().st_size
    if file_size > _MAX_READ_SIZE:
        raise HTTPException(
            413,
            detail=f"File too large: {file_size} bytes (max {_MAX_READ_SIZE})",
        )

    def _stream():
        with open(validated, "rb") as f:
            while True:
                chunk = f.read(65536)  # 64 KB chunks
                if not chunk:
                    break
                yield chunk

    filename = validated.name
    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(file_size),
        },
    )


# ── File write endpoints (auth required, Phase 3D) ───────────

def _validate_write_path(path_str: str, size: int = 0) -> Path:
    """Validate path for write operations. Checks share_write + mode + roots."""
    if not _SHARE_WRITE:
        raise HTTPException(403, detail="Write access is disabled")
    if size > _MAX_WRITE_SIZE:
        raise HTTPException(
            413,
            detail=f"Content too large: {size} bytes (max {_MAX_WRITE_SIZE})",
        )
    return _validate_path(path_str)


class WriteRequest(BaseModel):
    path: str
    content_b64: str


class MkdirRequest(BaseModel):
    path: str


class DeleteRequest(BaseModel):
    path: str


@app.post("/node/fs/write", dependencies=[Depends(_require_auth)])
async def fs_write(req: WriteRequest):
    """Write a file (create or overwrite). Requires share_write enabled."""
    import base64

    try:
        raw = base64.b64decode(req.content_b64)
    except Exception:
        raise HTTPException(400, detail="Invalid base64 content")

    validated = _validate_write_path(req.path, len(raw))

    if not validated.parent.exists():
        raise HTTPException(400, detail=f"Parent directory does not exist: {validated.parent}")

    try:
        validated.write_bytes(raw)
    except PermissionError:
        raise HTTPException(403, detail=f"Permission denied: {validated}")
    except Exception as e:
        raise HTTPException(500, detail=f"Write failed: {e}")

    return {"ok": True, "path": str(validated), "size": len(raw)}


@app.post("/node/fs/mkdir", dependencies=[Depends(_require_auth)])
async def fs_mkdir(req: MkdirRequest):
    """Create a directory. Requires share_write enabled."""
    validated = _validate_write_path(req.path)

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

    return {"ok": True, "path": str(validated)}


@app.post("/node/fs/delete", dependencies=[Depends(_require_auth)])
async def fs_delete(req: DeleteRequest):
    """Delete a file or empty directory. Requires share_write enabled."""
    validated = _validate_write_path(req.path)

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

    return {"ok": True, "path": str(validated)}


# ── Pairing key management ───────────────────────────────────

def _load_or_create_key(key_file: Path, force_create: bool = False) -> bytes:
    """Load pairing key from disk, or generate and save a new one.

    Prints the key hex ONLY when creating a new key (not on every boot).
    """
    if key_file.exists() and not force_create:
        raw = key_file.read_bytes()
        return raw

    secret = _generate_pairing_secret()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(secret)
    hex_key = secret.hex()
    print(f"\n  *** NEW PAIRING KEY ***")
    print(f"  {hex_key}")
    print(f"  Copy this key to the controller. It will not be shown again.")
    print(f"  Use --print-pairing-key to display it later.\n")
    return secret


# ── CLI entry point ───────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forest Node Daemon (standalone)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5052")),
                        help="Listen port (default: 5052)")
    parser.add_argument("--allow-full", action="store_true",
                        help="Allow FULL read-only mode (operator consent)")
    parser.add_argument("--generate-pairing-key", action="store_true",
                        help="Regenerate pairing key (invalidates existing sessions)")
    parser.add_argument("--print-pairing-key", action="store_true",
                        help="Print current pairing key and exit")
    parser.add_argument("--pairing-key-file", type=str,
                        default=str(Path(__file__).parent / "pairing_secret.key"),
                        help="Path to pairing key file (default: ./pairing_secret.key)")
    args = parser.parse_args()

    _PAIRING_KEY_FILE = Path(args.pairing_key_file)

    # --print-pairing-key: show key and exit
    if args.print_pairing_key:
        if _PAIRING_KEY_FILE.exists():
            print(_PAIRING_KEY_FILE.read_bytes().hex())
        else:
            print("No pairing key found. Start the daemon to generate one.")
        exit(0)

    _ALLOW_FULL_FLAG = args.allow_full

    # Load or create pairing key
    _pairing_secret = _load_or_create_key(_PAIRING_KEY_FILE, force_create=args.generate_pairing_key)

    mode_label = "allowlist + full" if _ALLOW_FULL_FLAG else "allowlist only"
    print(f"Forest Node Daemon v{_VERSION} starting on {args.host}:{args.port}")
    print(f"  node_id   = {_NODE_ID}")
    print(f"  file mode = {mode_label}")
    print(f"  roots     = {_ALLOWLIST_ROOTS}")
    print(f"  pairing   = active (key loaded)")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
