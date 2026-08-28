"""Forest Node Engine -- manages discovery, registration, and job distribution.

Phase 2: Manual registration by IP:port, heartbeat probing, disk persistence.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

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
        self.discovery_active: bool = False
        self._caps = None
        self._nodes_file: Optional[Path] = None
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

    # ── Discovery (stubs → Phase 2b UDP) ─────────────────────

    def start_discovery(self) -> bool:
        """Start LAN discovery. Phase 2b will add actual UDP broadcast."""
        self.discovery_active = True
        logger.info("Discovery started (stub)")
        return True

    def stop_discovery(self) -> bool:
        """Stop LAN discovery."""
        self.discovery_active = False
        logger.info("Discovery stopped (stub)")
        return True
