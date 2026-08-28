"""mDNS service discovery — broadcast + listen for Clearbox nodes on LAN.

Uses zeroconf (python-zeroconf) to:
  1. Register this node as a service: _clearbox._tcp.local.
  2. Browse for other nodes on the same service type.

Service TXT record carries:
  machine_id, hostname, version, caps_summary (JSON-safe short string)

No Clearbox repo dependencies — standalone compatible.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("clearbox_node.discovery")

SERVICE_TYPE = "_clearbox._tcp.local."


def _get_local_ip() -> str:
    """Best-effort LAN IP (not 127.0.0.1)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


class MeshDiscovery:
    """Manages mDNS registration and browsing.

    Usage:
        disc = MeshDiscovery(machine_id="abc123def456", port=5060)
        disc.set_properties(hostname="Desktop-PC", version="0.6.0", caps={...})
        disc.start()          # register + browse
        peers = disc.peers()  # snapshot of discovered nodes
        disc.stop()           # unregister + close
    """

    def __init__(self, machine_id: str, port: int = 5060):
        self._machine_id = machine_id
        self._port = port
        self._props: Dict[str, str] = {}
        self._zc = None
        self._info = None
        self._browser = None
        self._peers: Dict[str, Dict[str, Any]] = {}  # machine_id -> info
        self._lock = threading.Lock()
        self._on_change: Optional[Callable] = None

    def set_properties(self, hostname: str = "", version: str = "",
                       caps: Optional[dict] = None) -> None:
        """Set TXT record properties before start()."""
        self._props = {
            "machine_id": self._machine_id,
            "hostname": hostname,
            "version": version,
            "caps": json.dumps(caps or {}, separators=(",", ":")),
        }

    def set_on_change(self, callback: Callable) -> None:
        """Optional callback when peer list changes."""
        self._on_change = callback

    def start(self) -> None:
        """Register this node and start browsing for peers."""
        try:
            from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
        except ImportError:
            logger.warning("zeroconf not installed — discovery disabled. "
                           "pip install zeroconf")
            return

        self._zc = Zeroconf()
        local_ip = _get_local_ip()

        # Build TXT record (zeroconf wants bytes values)
        txt = {k: v.encode() for k, v in self._props.items()}

        service_name = f"clearbox-{self._machine_id}.{SERVICE_TYPE}"
        self._info = ServiceInfo(
            SERVICE_TYPE,
            service_name,
            addresses=[socket.inet_aton(local_ip)],
            port=self._port,
            properties=txt,
            server=f"{self._machine_id}.local.",
        )

        self._zc.register_service(self._info)
        logger.info("mDNS registered: %s on %s:%d", service_name, local_ip, self._port)

        # Browse for peers
        self._browser = ServiceBrowser(self._zc, SERVICE_TYPE, self)
        logger.info("mDNS browsing for %s", SERVICE_TYPE)

    def stop(self) -> None:
        """Unregister and close."""
        if self._zc and self._info:
            try:
                self._zc.unregister_service(self._info)
            except Exception:
                pass
        if self._zc:
            try:
                self._zc.close()
            except Exception:
                pass
        self._zc = None
        self._info = None
        self._browser = None
        logger.info("mDNS stopped")

    # ── ServiceBrowser callbacks ──────────────────────────────

    def add_service(self, zc, service_type: str, name: str) -> None:
        """Called by ServiceBrowser when a new node appears."""
        self._resolve(zc, service_type, name)

    def update_service(self, zc, service_type: str, name: str) -> None:
        """Called by ServiceBrowser when a node updates its TXT record."""
        self._resolve(zc, service_type, name)

    def remove_service(self, zc, service_type: str, name: str) -> None:
        """Called by ServiceBrowser when a node disappears."""
        # Extract machine_id from service name: "clearbox-{machine_id}._clearbox._tcp.local."
        prefix = "clearbox-"
        short = name.split(".")[0]
        if short.startswith(prefix):
            mid = short[len(prefix):]
            with self._lock:
                removed = self._peers.pop(mid, None)
            if removed:
                logger.info("Peer removed: %s (%s)", mid, removed.get("hostname", "?"))
                if self._on_change:
                    self._on_change()

    def _resolve(self, zc, service_type: str, name: str) -> None:
        """Resolve service info and store in peers dict."""
        try:
            from zeroconf import ServiceInfo as _SI
        except ImportError:
            return

        info = zc.get_service_info(service_type, name)
        if not info:
            return

        txt = {}
        if info.properties:
            for k, v in info.properties.items():
                key = k.decode() if isinstance(k, bytes) else k
                val = v.decode() if isinstance(v, bytes) else v
                txt[key] = val

        peer_mid = txt.get("machine_id", "")
        if not peer_mid or peer_mid == self._machine_id:
            return  # skip self

        addresses = info.parsed_addresses()
        ip = addresses[0] if addresses else "?"

        peer = {
            "machine_id": peer_mid,
            "hostname": txt.get("hostname", "?"),
            "ip": ip,
            "port": info.port,
            "version": txt.get("version", "?"),
            "caps": txt.get("caps", "{}"),
            "last_seen": time.time(),
        }

        with self._lock:
            is_new = peer_mid not in self._peers
            self._peers[peer_mid] = peer

        if is_new:
            logger.info("Peer discovered: %s @ %s:%d (%s)",
                        peer_mid, ip, info.port, peer.get("hostname"))
        if self._on_change:
            self._on_change()

    # ── Public API ────────────────────────────────────────────

    def peers(self) -> List[Dict[str, Any]]:
        """Snapshot of all discovered peers (excluding self)."""
        with self._lock:
            return list(self._peers.values())

    def get_peer(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific peer by machine_id."""
        with self._lock:
            return self._peers.get(machine_id)
