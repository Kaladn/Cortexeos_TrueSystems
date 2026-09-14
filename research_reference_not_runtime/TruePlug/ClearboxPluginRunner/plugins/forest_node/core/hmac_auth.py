"""Forest Node — HMAC-SHA256 pairing authentication (Phase 3B).

Auth model:
  1. PAIRING: Daemon generates 32-byte secret, prints hex once, stores to disk
  2. SESSION: Challenge/response — controller proves it knows the secret
  3. PER-REQUEST: Self-verifying Bearer token (stateless on daemon)

Token format:
  "{issued}:{expires}:{HMAC-SHA256(secret, 'session:{node_id}:{issued}:{expires}')}"

Replay protection:
  - Challenge nonces are single-use, 60s TTL, capped at 50 pending
  - Session tokens bind to node_id — not portable across nodes

Stdlib only — no external deps (hmac, hashlib, secrets).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Dict, Optional, Tuple


def generate_pairing_secret() -> bytes:
    """Generate 32-byte (256-bit) pairing secret."""
    return secrets.token_bytes(32)


def create_nonce() -> str:
    """Generate 128-bit random nonce for challenge/response (32 hex chars)."""
    return secrets.token_hex(16)


def verify_challenge_response(secret: bytes, nonce: str, response: str) -> bool:
    """Verify controller's HMAC response to a challenge nonce."""
    expected = hmac.new(secret, nonce.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, response)


def issue_session_token(secret: bytes, node_id: str, ttl_s: int = 3600) -> Tuple[str, int]:
    """Create self-verifying session token bound to node_id.

    Returns (token_string, expires_at_epoch).
    """
    issued = int(time.time())
    expires = issued + ttl_s
    payload = f"session:{node_id}:{issued}:{expires}"
    sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return f"{issued}:{expires}:{sig}", expires


def verify_session_token(secret: bytes, node_id: str, token: str) -> bool:
    """Verify session token signature and check expiry.

    Token must have been issued for this specific node_id.
    """
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
    expected = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


class NonceStore:
    """In-memory nonce store with TTL and cap.

    - Max 50 pending nonces (prevents memory bomb from challenge spam)
    - 60s TTL — unused nonces auto-evict
    - Each nonce consumed exactly once (removed after successful verify)
    """

    def __init__(self, max_pending: int = 50, ttl_s: float = 60.0):
        self._nonces: Dict[str, float] = {}
        self._max = max_pending
        self._ttl = ttl_s

    def issue(self) -> str:
        """Issue a new single-use nonce."""
        self._evict()
        if len(self._nonces) >= self._max:
            oldest = min(self._nonces, key=self._nonces.get)
            del self._nonces[oldest]
        nonce = create_nonce()
        self._nonces[nonce] = time.time()
        return nonce

    def consume(self, nonce: str) -> bool:
        """Consume a nonce. Returns True if valid, False if expired/unknown/replayed."""
        self._evict()
        if nonce in self._nonces:
            del self._nonces[nonce]
            return True
        return False

    def _evict(self):
        """Remove expired nonces."""
        cutoff = time.time() - self._ttl
        self._nonces = {k: v for k, v in self._nonces.items() if v > cutoff}
