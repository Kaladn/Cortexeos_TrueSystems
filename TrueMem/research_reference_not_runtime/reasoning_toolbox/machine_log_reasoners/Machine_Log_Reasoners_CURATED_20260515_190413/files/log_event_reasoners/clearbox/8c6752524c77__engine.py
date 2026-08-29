"""Forest Node Engine -- manages discovery, registration, and job distribution.

Phase 2: Manual registration by IP:port, heartbeat probing, disk persistence.
Phase 3B: Pairing storage (DPAPI), session management, auth headers on proxies.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

from forest_node.api.models import NodeInfo

logger = logging.getLogger(__name__)

# Heartbeat timeout — if a node hasn't responded in this window, mark stale
HEARTBEAT_TIMEOUT_S = 30.0


class NodeEngine:
    """Singleton that holds the node registry and coordinates operations."""

    def __init__(self):
        self._nodes: Dict[str, NodeInfo] = {}
        self.local_node_id: str = uuid.uuid4().hex[:12]
        self._caps = None
        self._nodes_file: Optional[Path] = None
        self._sessions: Dict[str, Tuple[str, float]] = {}  # node_id → (token, expires_at)
        self._init_persistence()
        logger.info("NodeEngine initialized, local_node_id=%s", self.local_node_id)

    # ── Persistence ──────────────────────────────────────────

    def _init_persistence(self):
        """Load known nodes from disk on startup."""
        try:
            from security.data_paths import FOREST_NODE_DIR
            self._nodes_file = FOREST_NODE_DIR / "nodes.json"
            if self._nodes_file.exists():
                data = json.loads(self._nodes_file.read_text(encoding="utf-8"))
                for entry in data:
                    node = NodeInfo(**entry)
                    if node.node_id:
                        self._nodes[node.node_id] = node
                logger.info("Loaded %d known nodes from disk", len(self._nodes))
        except Exception as e:
            logger.warning("Could not load persisted nodes: %s", e)

    def _persist(self):
        """Write current node registry to disk."""
        if self._nodes_file is None:
            return
        try:
            data = [n.model_dump() for n in self._nodes.values()]
            self._nodes_file.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Could not persist nodes: %s", e)

    # ── Properties ───────────────────────────────────────────

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def paired_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.pairing_state == "paired")

    def get_local_caps(self) -> dict:
        if self._caps is None:
            from forest_node.core.caps import get_local_caps
            self._caps = get_local_caps()
        return self._caps

    # ── Node CRUD ────────────────────────────────────────────

    def list_nodes(self) -> List[NodeInfo]:
        return list(self._nodes.values())

    def add_or_update_node(self, info: NodeInfo) -> None:
        self._nodes[info.node_id] = info
        self._persist()

    def remove_node(self, node_id: str) -> bool:
        removed = self._nodes.pop(node_id, None)
        if removed:
            self._sessions.pop(node_id, None)
            self._persist()
            return True
        return False

    def get_node(self, node_id: str) -> NodeInfo | None:
        return self._nodes.get(node_id)

    # ── Registration (Phase 2) ───────────────────────────────

    async def register_node(self, ip: str, port: int, nickname: str = "") -> NodeInfo:
        """Probe a remote node daemon and register it if reachable.

        Steps:
        1. GET http://ip:port/node/health  → confirms alive
        2. GET http://ip:port/node/caps    → gets capabilities + node_id
        3. Store in registry + persist

        Raises httpx.HTTPError or ValueError on failure.
        """
        base = f"http://{ip}:{port}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Probe health
            health_resp = await client.get(f"{base}/node/health")
            health_resp.raise_for_status()
            health = health_resp.json()

            # Probe caps
            caps_resp = await client.get(f"{base}/node/caps")
            caps_resp.raise_for_status()
            caps_data = caps_resp.json()

        node_id = caps_data.get("node_id") or health.get("node_id")
        if not node_id:
            raise ValueError("Remote node did not return a node_id")

        caps = caps_data.get("caps", {})
        node = NodeInfo(
            node_id=node_id,
            hostname=nickname or caps.get("hostname", ""),
            ip=ip,
            port=port,
            caps_summary=caps,
            pairing_state="unpaired",
            last_seen=time.time(),
        )
        self.add_or_update_node(node)
        logger.info("Registered node %s at %s:%d", node_id, ip, port)
        return node

    # ── Heartbeat (Phase 2) ──────────────────────────────────

    async def heartbeat_all(self) -> Dict[str, str]:
        """Ping all known nodes, update last_seen, return {node_id: status}.

        Status is 'ok' or 'unreachable'.
        """
        results: Dict[str, str] = {}
        async with httpx.AsyncClient(timeout=3.0) as client:
            for node_id, node in list(self._nodes.items()):
                try:
                    resp = await client.get(f"http://{node.ip}:{node.port}/node/health")
                    resp.raise_for_status()
                    node.last_seen = time.time()
                    self._nodes[node_id] = node
                    results[node_id] = "ok"
                except Exception:
                    results[node_id] = "unreachable"

        self._persist()
        return results

    # ── Pairing (Phase 3B) ──────────────────────────────────

    def store_pairing_secret(self, node_id: str, secret_hex: str) -> None:
        """Store pairing secret for a node (DPAPI encrypted)."""
        from security.data_paths import FOREST_NODE_PAIRS_DIR
        from security.secure_storage import secure_json_dump

        pair_file = FOREST_NODE_PAIRS_DIR / f"{node_id}.json"
        secure_json_dump(pair_file, {"node_id": node_id, "secret_hex": secret_hex})

        node = self.get_node(node_id)
        if node:
            node.pairing_state = "paired"
            self.add_or_update_node(node)
        logger.info("Stored pairing secret for node %s", node_id)

    def get_pairing_secret(self, node_id: str) -> Optional[bytes]:
        """Load pairing secret for a node. Returns bytes or None."""
        from security.data_paths import FOREST_NODE_PAIRS_DIR
        from security.secure_storage import secure_json_load

        pair_file = FOREST_NODE_PAIRS_DIR / f"{node_id}.json"
        if not pair_file.exists():
            return None
        try:
            data = secure_json_load(pair_file)
            if data and "secret_hex" in data:
                return bytes.fromhex(data["secret_hex"])
        except Exception as e:
            logger.warning("Failed to load pairing secret for %s: %s", node_id, e)
        return None

    def remove_pairing(self, node_id: str) -> bool:
        """Remove pairing for a node."""
        from security.data_paths import FOREST_NODE_PAIRS_DIR

        pair_file = FOREST_NODE_PAIRS_DIR / f"{node_id}.json"
        if pair_file.exists():
            pair_file.unlink()

        node = self.get_node(node_id)
        if node:
            node.pairing_state = "unpaired"
            self.add_or_update_node(node)

        self._sessions.pop(node_id, None)
        logger.info("Removed pairing for node %s", node_id)
        return True

    async def verify_pairing(self, node_id: str, secret_hex: str) -> Optional[str]:
        """Verify a pairing key against the daemon via challenge/response.

        Returns session token if valid, None if rejected.
        """
        secret = bytes.fromhex(secret_hex)
        base = self._node_base(node_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            ch_resp = await client.get(f"{base}/node/auth/challenge")
            ch_resp.raise_for_status()
            nonce = ch_resp.json()["nonce"]

            response = hmac.new(secret, nonce.encode(), hashlib.sha256).hexdigest()
            sess_resp = await client.post(
                f"{base}/node/auth/session",
                json={"nonce": nonce, "response": response},
            )
            if sess_resp.status_code == 401:
                return None
            sess_resp.raise_for_status()
            data = sess_resp.json()
            token = data["session_token"]
            expires = time.time() + data["expires_in"]
            self._sessions[node_id] = (token, expires)
            return token

    # ── Session management ───────────────────────────────────

    async def _ensure_session(self, node_id: str) -> str:
        """Get or create a valid session token for a paired node.

        Refreshes 60s before expiry to avoid mid-request failures.
        """
        if node_id in self._sessions:
            token, expires = self._sessions[node_id]
            if time.time() < expires - 60:
                return token

        secret = self.get_pairing_secret(node_id)
        if not secret:
            raise ValueError(f"Node {node_id} is not paired")

        base = self._node_base(node_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            ch_resp = await client.get(f"{base}/node/auth/challenge")
            ch_resp.raise_for_status()
            nonce = ch_resp.json()["nonce"]

            response = hmac.new(secret, nonce.encode(), hashlib.sha256).hexdigest()
            sess_resp = await client.post(
                f"{base}/node/auth/session",
                json={"nonce": nonce, "response": response},
            )
            if sess_resp.status_code == 401:
                raise ValueError("Pairing key rejected by daemon — re-pair required")
            sess_resp.raise_for_status()
            data = sess_resp.json()
            token = data["session_token"]
            expires = time.time() + data["expires_in"]
            self._sessions[node_id] = (token, expires)
            return token

    def _auth_headers(self, token: str) -> dict:
        """Build Authorization header for a session token."""
        return {"Authorization": f"Forest {token}"}

    # ── File access proxy (Phase 3A + 3B auth) ───────────────

    def _node_base(self, node_id: str) -> str:
        """Get base URL for a registered node. Raises ValueError if not found."""
        node = self.get_node(node_id)
        if not node:
            raise ValueError(f"Node not found: {node_id}")
        return f"http://{node.ip}:{node.port}"

    async def proxy_get_mode(self, node_id: str) -> dict:
        """Get file access mode from a remote node."""
        base = self._node_base(node_id)
        token = await self._ensure_session(node_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base}/node/fs/mode",
                                    headers=self._auth_headers(token))
            resp.raise_for_status()
            data = resp.json()
            data["node_id"] = node_id
            return data

    async def proxy_set_mode(self, node_id: str, mode: str, ttl_s: int = 0,
                             share_write: bool = False) -> dict:
        """Set file access mode on a remote node."""
        base = self._node_base(node_id)
        token = await self._ensure_session(node_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{base}/node/fs/mode",
                json={"mode": mode, "ttl_s": ttl_s, "share_write": share_write},
                headers=self._auth_headers(token),
            )
            if resp.status_code == 403:
                return {"ok": False, "error": resp.json().get("detail", "Forbidden")}
            resp.raise_for_status()
            data = resp.json()
            data["node_id"] = node_id
            return data

    async def proxy_file_list(self, node_id: str, path: str) -> dict:
        """List directory on a remote node."""
        base = self._node_base(node_id)
        token = await self._ensure_session(node_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base}/node/fs/list", params={"path": path},
                                    headers=self._auth_headers(token))
            if resp.status_code == 401:
                # Session expired mid-flight — clear and surface
                self._sessions.pop(node_id, None)
                return {"entries": [], "path": path, "node_id": node_id,
                        "error": {"type": "auth_error", "message": "Session expired, retry"}}
            if resp.status_code in (400, 403, 404):
                return {"entries": [], "path": path, "node_id": node_id,
                        "error": {"type": "daemon_error", "message": resp.json().get("detail", "Error")}}
            resp.raise_for_status()
            data = resp.json()
            data["node_id"] = node_id
            return data

    async def proxy_file_read(self, node_id: str, path: str) -> tuple:
        """Read a file from a remote node.

        Returns (content_bytes, filename, content_length) or raises ValueError.
        Buffered read — file size is capped at 100MB by the daemon.
        """
        base = self._node_base(node_id)
        token = await self._ensure_session(node_id)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{base}/node/fs/read", params={"path": path},
                                    headers=self._auth_headers(token))
            if resp.status_code != 200:
                detail = "Unknown error"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    detail = resp.text[:200]
                raise ValueError(f"Daemon error ({resp.status_code}): {detail}")

            # Extract filename from Content-Disposition header
            cd = resp.headers.get("content-disposition", "")
            filename = "download"
            if 'filename="' in cd:
                filename = cd.split('filename="')[1].rstrip('"')

            return resp.content, filename, len(resp.content)

    # ── File write proxy (Phase 3D) ────────────────────────────

    async def _proxy_write_op(self, node_id: str, endpoint: str,
                               payload: dict, timeout: float = 60.0) -> dict:
        """Shared proxy logic for write operations (write/mkdir/delete)."""
        base = self._node_base(node_id)
        token = await self._ensure_session(node_id)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base}{endpoint}",
                                     json=payload,
                                     headers=self._auth_headers(token))
            if resp.status_code == 401:
                self._sessions.pop(node_id, None)
                return {"ok": False, "node_id": node_id,
                        "error": {"type": "auth_error", "message": "Session expired, retry"}}
            if resp.status_code in (400, 403, 404, 413, 500):
                detail = "Error"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    detail = resp.text[:200]
                return {"ok": False, "node_id": node_id,
                        "error": {"type": "daemon_error", "message": detail}}
            resp.raise_for_status()
            data = resp.json()
            data["node_id"] = node_id
            return data

    async def proxy_file_write(self, node_id: str, path: str, content_b64: str) -> dict:
        """Write a file on a remote node."""
        return await self._proxy_write_op(
            node_id, "/node/fs/write",
            {"path": path, "content_b64": content_b64},
        )

    async def proxy_file_mkdir(self, node_id: str, path: str) -> dict:
        """Create a directory on a remote node."""
        return await self._proxy_write_op(
            node_id, "/node/fs/mkdir", {"path": path}, timeout=10.0,
        )

    async def proxy_file_delete(self, node_id: str, path: str) -> dict:
        """Delete a file or empty directory on a remote node."""
        return await self._proxy_write_op(
            node_id, "/node/fs/delete", {"path": path}, timeout=10.0,
        )

