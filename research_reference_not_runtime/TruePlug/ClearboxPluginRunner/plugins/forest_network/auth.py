"""Forest Network — authentication.

All /api/network/serve/* endpoints require X-Forest-Node-Key header.
The key is validated against the peer key list in forest.config.json.

Uses hmac.compare_digest for constant-time comparison to prevent timing attacks.
Every auth result (pass/fail) is logged for auditability.
"""
from __future__ import annotations

import hmac
import logging
from typing import Optional

from fastapi import Header, HTTPException, status

from .config import get_peer_keys, is_auth_required

LOGGER = logging.getLogger("forest.network.auth")
_AUDIT = logging.getLogger("forest.network.audit")


def validate_node_key(provided_key: str) -> bool:
    """Return True if provided_key matches any configured peer key.

    Constant-time comparison via hmac.compare_digest prevents timing attacks.
    Returns False immediately if no peer keys are configured.
    """
    peer_keys = get_peer_keys()
    if not peer_keys:
        return False
    provided_bytes = provided_key.encode("utf-8")
    for k in peer_keys:
        if hmac.compare_digest(provided_bytes, k.encode("utf-8")):
            return True
    return False


async def require_node_key(
    x_forest_node_key: Optional[str] = Header(default=None),
) -> str:
    """FastAPI dependency — validates X-Forest-Node-Key header.

    Returns the provided key on success.
    Raises HTTP 401 if the key is missing or invalid.

    Auth is bypassed entirely if 'network.require_auth' is false in config
    (useful for dev/testing on a trusted LAN with no peer keys configured).
    """
    if not is_auth_required():
        # Auth disabled in config — pass through but log it
        _AUDIT.info("AUTH_BYPASS | auth disabled in config")
        return x_forest_node_key or ""

    if not x_forest_node_key:
        _AUDIT.warning("AUTH_REJECT | missing X-Forest-Node-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Forest-Node-Key header is required",
            headers={"WWW-Authenticate": "X-Forest-Node-Key"},
        )

    if not validate_node_key(x_forest_node_key):
        # Log a partial key hint (first 4 chars only) for diagnostics
        hint = x_forest_node_key[:4] + "..." if len(x_forest_node_key) > 4 else "???"
        _AUDIT.warning("AUTH_REJECT | invalid key hint=%r", hint)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid node key",
            headers={"WWW-Authenticate": "X-Forest-Node-Key"},
        )

    _AUDIT.info("AUTH_OK | key accepted")
    return x_forest_node_key
