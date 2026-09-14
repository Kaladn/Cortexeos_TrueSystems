"""Ed25519 request signing and verification for mobile nodes.

Keypair minted during USB pairing, private key delivered via USB bundle.
Public key stored DPAPI-encrypted on the controller.
Mobile requests carry: Authorization: Forest-Ed25519 {node_id}:{timestamp}:{signature}
"""

import base64
import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

LOGGER = logging.getLogger("forest.node.ed25519")

# Replay window: accept timestamps within +/-60 seconds
TIMESTAMP_WINDOW = 60

# Auth header prefix
AUTH_PREFIX = "Forest-Ed25519"


def generate_keypair() -> Tuple[bytes, bytes]:
    """Generate an Ed25519 keypair.

    Returns:
        (private_key_bytes, public_key_bytes) -- raw 32-byte keys, base64-encoded.
    """
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return (
        base64.b64encode(private_bytes).decode(),
        base64.b64encode(public_bytes).decode(),
    )


def verify_signature(public_key_b64: str, message: bytes, signature_b64: str) -> bool:
    """Verify an Ed25519 signature."""
    try:
        pub_bytes = base64.b64decode(public_key_b64)
        sig_bytes = base64.b64decode(signature_b64)
        public_key = Ed25519PublicKey.from_public_key_bytes(pub_bytes)
        public_key.verify(sig_bytes, message)
        return True
    except Exception:
        return False


def parse_auth_header(header_value: str) -> Optional[Tuple[str, str, str]]:
    """Parse Authorization: Forest-Ed25519 {node_id}:{timestamp}:{signature}

    Returns:
        (node_id, timestamp_str, signature_b64) or None if invalid format
    """
    if not header_value or not header_value.startswith(AUTH_PREFIX + " "):
        return None

    payload = header_value[len(AUTH_PREFIX) + 1:]
    parts = payload.split(":", 2)
    if len(parts) != 3:
        return None

    return parts[0], parts[1], parts[2]


def verify_request(header_value: str, public_keys: Dict[str, str]) -> Optional[str]:
    """Verify a mobile node request.

    Args:
        header_value: Full Authorization header value
        public_keys: Dict of node_id -> public_key_b64

    Returns:
        node_id if valid, None if invalid
    """
    parsed = parse_auth_header(header_value)
    if not parsed:
        return None

    node_id, ts_str, sig_b64 = parsed

    # Check node is known
    pub_key = public_keys.get(node_id)
    if not pub_key:
        LOGGER.debug("Unknown node_id: %s", node_id)
        return None

    # Check timestamp window
    try:
        ts = int(ts_str)
    except ValueError:
        return None
    now = int(time.time())
    if abs(now - ts) > TIMESTAMP_WINDOW:
        LOGGER.debug("Timestamp outside window: %d vs %d", ts, now)
        return None

    # Verify signature: sign(node_id:timestamp)
    message = f"{node_id}:{ts_str}".encode()
    if verify_signature(pub_key, message, sig_b64):
        return node_id

    LOGGER.debug("Signature verification failed for node %s", node_id)
    return None


class MobileKeyStore:
    """DPAPI-encrypted storage for mobile node public keys.

    One JSON file per node: mobile_keys/{node_id}.json
    """

    def __init__(self, keys_dir: Path):
        self._dir = keys_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, str] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all public keys from disk into cache."""
        try:
            from security.secure_storage import secure_json_load
        except ImportError:
            LOGGER.warning("secure_storage not available -- mobile keys will not persist")
            return

        for path in self._dir.glob("*.json"):
            try:
                data = secure_json_load(path)
                node_id = data.get("node_id", path.stem)
                pub_key = data.get("public_key")
                if node_id and pub_key:
                    self._cache[node_id] = pub_key
            except Exception as e:
                LOGGER.warning("Failed to load key %s: %s", path.name, e)

        LOGGER.info("Loaded %d mobile node key(s)", len(self._cache))

    def store(self, node_id: str, public_key_b64: str, device_info: dict = None) -> None:
        """Store a mobile node's public key (DPAPI-encrypted)."""
        try:
            from security.secure_storage import secure_json_dump
        except ImportError:
            LOGGER.warning("secure_storage not available -- storing in plain cache only")
            self._cache[node_id] = public_key_b64
            return

        record = {
            "node_id": node_id,
            "public_key": public_key_b64,
            "paired_at": int(time.time()),
        }
        if device_info:
            record["device"] = device_info

        path = self._dir / f"{node_id}.json"
        secure_json_dump(path, record)
        self._cache[node_id] = public_key_b64
        LOGGER.info("Stored public key for node %s", node_id)

    def remove(self, node_id: str) -> bool:
        """Remove a mobile node's key (unpair)."""
        path = self._dir / f"{node_id}.json"
        if path.exists():
            path.unlink()
        removed = self._cache.pop(node_id, None) is not None
        if removed:
            LOGGER.info("Removed key for node %s", node_id)
        return removed

    def get_all(self) -> Dict[str, str]:
        """Get all node_id -> public_key_b64 mappings."""
        return dict(self._cache)

    def get(self, node_id: str) -> Optional[str]:
        """Get a specific node's public key."""
        return self._cache.get(node_id)

    def list_nodes(self) -> list:
        """List all paired mobile node IDs with metadata."""
        nodes = []
        for node_id in self._cache:
            info = {"node_id": node_id}
            path = self._dir / f"{node_id}.json"
            if path.exists():
                try:
                    from security.secure_storage import secure_json_load
                    data = secure_json_load(path)
                    info["created"] = data.get("paired_at")
                    info["device"] = data.get("device", {})
                except Exception:
                    pass
            nodes.append(info)
        return nodes
