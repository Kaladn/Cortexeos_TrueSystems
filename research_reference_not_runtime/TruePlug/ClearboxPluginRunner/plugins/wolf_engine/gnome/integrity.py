"""
GNOME Integrity Module
Generate and verify integrity hashes for raw tokens.
"""

import hashlib


def compute_integrity_hash(token: str) -> str:
    """Compute SHA-256 hash of token (original case, UTF-8)."""
    hash_bytes = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return hash_bytes


def verify_integrity(token: str, integrity_hash: str) -> bool:
    """Verify token matches its integrity hash."""
    return compute_integrity_hash(token) == integrity_hash
