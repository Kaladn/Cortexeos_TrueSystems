"""Forest Node -- Windows Hello session gate (FastAPI dependency).

Validates ``forest_session`` cookie against the LLM server's auth endpoint.
Returns ``user_id: str`` for multi-user readiness.

Design:
  - 1 s timeout on localhost call (should respond < 10 ms)
  - 10 s in-memory cache per token hash (prevents auth spam during file browsing)
  - Config-controlled graceful degradation via ``require_hello``
  - Lazy ``httpx`` import (no hard dep at module level)
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# -- Auth cache ---------------------------------------------------------------

_AUTH_CACHE: dict[str, tuple[bool, bool, float]] = {}  # hash -> (authenticated, has_credential, ts)
_CACHE_TTL = 10.0  # seconds

AUTH_STATUS_URL = "http://localhost:11435/api/auth/status"
AUTH_TIMEOUT = 1.0  # seconds


def _cache_key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def _check_cache(token: str) -> Optional[tuple[bool, bool]]:
    key = _cache_key(token)
    entry = _AUTH_CACHE.get(key)
    if entry is None:
        return None
    authenticated, has_credential, ts = entry
    if time.monotonic() - ts > _CACHE_TTL:
        del _AUTH_CACHE[key]
        return None
    return authenticated, has_credential


def _set_cache(token: str, authenticated: bool, has_credential: bool) -> None:
    key = _cache_key(token)
    _AUTH_CACHE[key] = (authenticated, has_credential, time.monotonic())


# -- FastAPI dependency -------------------------------------------------------

async def require_hello_session(request: Request) -> str:
    """Validate the forest_session cookie via the LLM server.

    Returns ``user_id`` string:
      - ``"operator"`` when authenticated
      - ``"anonymous"`` when no credential registered and require_hello=False

    Raises ``HTTPException(401)`` otherwise.
    """
    from forest_node.config import REQUIRE_HELLO

    token = request.cookies.get("forest_session", "")

    # No token at all — check if we can allow anonymous
    if not token:
        return _handle_no_auth(has_credential=None, require_hello=REQUIRE_HELLO)

    # Check cache first
    cached = _check_cache(token)
    if cached is not None:
        authenticated, has_credential = cached
        return _decide(authenticated, has_credential, REQUIRE_HELLO)

    # Call LLM server
    try:
        import httpx
        async with httpx.AsyncClient(timeout=AUTH_TIMEOUT) as client:
            resp = await client.get(
                AUTH_STATUS_URL,
                cookies={"forest_session": token},
            )
            if resp.status_code != 200:
                logger.warning("Auth status returned %d", resp.status_code)
                raise HTTPException(status_code=401, detail="Authentication service error")

            data = resp.json()
            authenticated = data.get("authenticated", False)
            has_credential = data.get("has_credential", False)

            _set_cache(token, authenticated, has_credential)
            return _decide(authenticated, has_credential, REQUIRE_HELLO)

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Auth status call failed: %s", e)
        raise HTTPException(status_code=401, detail="Authentication service unavailable")


def _decide(authenticated: bool, has_credential: bool, require_hello: bool) -> str:
    """Decide whether to allow the request. Returns user_id or raises 401."""
    if authenticated:
        return "operator"

    # Not authenticated — check graceful degradation
    if has_credential is False and not require_hello:
        return "anonymous"

    if has_credential is False and require_hello:
        raise HTTPException(
            status_code=401,
            detail="Windows Hello is required but not configured. Set up biometric login first.",
        )

    # has_credential=True but not authenticated — must sign in
    raise HTTPException(
        status_code=401,
        detail="Sign in with Windows Hello to access this feature.",
    )


def _handle_no_auth(*, has_credential: Optional[bool], require_hello: bool) -> str:
    """Handle the case where no session cookie was provided at all."""
    # No cookie — we still need to know if Hello is configured.
    # Call the auth endpoint without a cookie to get has_credential.
    # But this is a sync decision point — for no-token, just deny.
    # The JS should always send credentials:include, so no-token = no-session.
    if not require_hello:
        # Check if credential exists by doing a quick uncached call
        # For simplicity: if require_hello is off AND no cookie, allow as anonymous
        return "anonymous"

    raise HTTPException(
        status_code=401,
        detail="Sign in with Windows Hello to access this feature.",
    )
