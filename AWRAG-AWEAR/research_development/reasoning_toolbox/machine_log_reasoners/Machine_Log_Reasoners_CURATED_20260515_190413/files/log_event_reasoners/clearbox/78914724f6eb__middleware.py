"""FastAPI middleware for session-based authentication.

Checks every request for a valid session cookie. Unauthenticated
requests get 401 except for whitelisted paths (auth endpoints, health).
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import validate_session
from .runtime_log import log_event  # DEBUGWIRE:AUTH

# Paths that don't require authentication
_PUBLIC_PATHS = frozenset({
    "/api/auth/status",
    "/api/auth/register/begin",
    "/api/auth/register/complete",
    "/api/auth/login/begin",
    "/api/auth/login/complete",
    "/api/nodes/pair/enroll",  # Mobile enrollment (one-time token, rate-limited)
    "/health",
    "/",
    "/favicon.ico",
})

# Prefixes that are public (static assets served by bridge)
_PUBLIC_PREFIXES = (
    "/ui/",
    "/samples/",
)

# Paths open to loopback callers only (bridge → local_llm_server internal routing)
_LOOPBACK_PATHS = frozenset({
    "/api/generate",
    "/api/tags",
})

# Prefixes open to loopback callers (library endpoints on :11435, browser calls from localhost)
_LOOPBACK_PREFIXES = (
    "/api/library/",
    "/api/debugwire/",  # DEBUGWIRE:AUTH — bridge→LLM server toggle forwarding
)

_LOOPBACK_ADDRS = frozenset({"127.0.0.1", "::1", "localhost"})

COOKIE_NAME = "clearbox_session"

# CSRF: state-changing methods from loopback must carry this header.
# Browsers block cross-origin custom headers without CORS preflight,
# so any attacker page's request will fail the preflight check.
CSRF_HEADER = "X-Clearbox-CSRF"
_CSRF_REQUIRED_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})


class AuthMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated requests with 401."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Localhost auto-auth: skip Hello for loopback callers.
        # The operator already authenticated to Windows — DPAPI still protects
        # data at rest. Hello is only enforced for remote/Tailscale access.
        # CSRF: state-changing methods must include X-Clearbox-CSRF header to
        # prevent cross-origin request attacks from malicious websites.
        client_host = request.client.host if request.client else None
        if client_host in _LOOPBACK_ADDRS:
            if request.method in _CSRF_REQUIRED_METHODS:
                if not request.headers.get(CSRF_HEADER):
                    return JSONResponse(
                        status_code=403,
                        content={"error": "CSRF header required",
                                 "code": "CSRF_MISSING"},
                    )
            return await call_next(request)

        # Allow public paths
        if path in _PUBLIC_PATHS:
            return await call_next(request)

        # Allow public prefixes
        for prefix in _PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Allow loopback-only paths (internal service routing)
        if path in _LOOPBACK_PATHS:
            client_host = request.client.host if request.client else None
            if client_host in _LOOPBACK_ADDRS:
                return await call_next(request)

        # Allow loopback-only prefixes (library on :11435, browser from localhost)
        for prefix in _LOOPBACK_PREFIXES:
            if path.startswith(prefix):
                client_host = request.client.host if request.client else None
                if client_host in _LOOPBACK_ADDRS:
                    return await call_next(request)

        # Allow OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check session cookie
        token = request.cookies.get(COOKIE_NAME)
        if validate_session(token):
            return await call_next(request)

        # Check Ed25519 mobile node auth (no cookie = maybe a paired phone)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Clearbox-Ed25519 "):
            node_id = _verify_mobile_auth(auth_header)
            if node_id and _mobile_path_allowed(path):
                request.state.mobile_node_id = node_id
                return await call_next(request)

        _host = request.client.host if request.client else "?"  # DEBUGWIRE:AUTH
        log_event("auth", "denied", extra={"path": path, "host": _host, "reason": "no_valid_session"})  # DEBUGWIRE:AUTH
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required", "code": "AUTH_REQUIRED"},
        )


# ── Ed25519 mobile node verification ─────────────────────────

# Mobile nodes: restricted to chat, cite, note, history (no file proxy, no admin)
_MOBILE_ALLOWED_PREFIXES = (
    "/api/chat/",
    "/api/generate",
    "/api/cite/",
    "/api/note/",
    "/api/history/",
    "/api/boot",
    "/api/auth/status",
)

_mobile_key_store = None


def _get_mobile_keys():
    global _mobile_key_store
    if _mobile_key_store is None:
        try:
            from clearbox_node.core.ed25519_auth import MobileKeyStore
            from security.data_paths import CLEARBOX_NODE_MOBILE_KEYS
            _mobile_key_store = MobileKeyStore(CLEARBOX_NODE_MOBILE_KEYS)
        except Exception:
            return {}
    return _mobile_key_store.get_all()


def _verify_mobile_auth(header_value: str):
    """Verify Ed25519 signed mobile request. Returns node_id or None."""
    try:
        from clearbox_node.core.ed25519_auth import verify_request
        keys = _get_mobile_keys()
        return verify_request(header_value, keys)
    except Exception:
        return None


def _mobile_path_allowed(path: str) -> bool:
    """Check if path is allowed for mobile nodes."""
    for prefix in _MOBILE_ALLOWED_PREFIXES:
        if path.startswith(prefix):
            return True
    return False
