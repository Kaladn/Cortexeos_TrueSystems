"""
NetlogWorker — Full connection-level internet traffic logger.
Extends wolf_engine WorkerBase.

Each collect() cycle snapshots all active TCP/UDP connections via psutil,
enriches with process name + pid, computes per-process connection counts,
emits one EvidenceEvent per new or changed connection.

Optional: scapy packet capture runs in a separate thread if enabled.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from wolf_engine.evidence.worker_base import WorkerBase
from wolf_engine.evidence.session_manager import EvidenceSessionManager
from netlog.config import (
    POLL_INTERVAL_SEC, IGNORE_LOCAL_LOOPBACK, IGNORE_STATUSES,
    MAX_EVENTS_IN_MEMORY, NODE_ID, SESSIONS_DIR,
    NEW_PROCESS_ALERT, HIGH_CONNECTION_COUNT, FOREIGN_PORT_ALERTLIST,
    PACKET_CAPTURE_ENABLED, PACKET_IFACE,
)

logger = logging.getLogger(__name__)

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    psutil = None
    _HAS_PSUTIL = False
    logger.warning("psutil not installed — netlog will emit empty events. pip install psutil")


def _conn_key(conn) -> str:
    """Stable string key for a connection tuple."""
    laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "?"
    raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "?"
    return f"{conn.pid}:{conn.type}:{laddr}->{raddr}"


class NetlogWorker(WorkerBase):
    """
    Full internet traffic logger using psutil connections.
    No packet sniffing — connection-level (no elevated privileges required).
    """

    worker_name = "netlog"

    def __init__(self, session_mgr: EvidenceSessionManager):
        super().__init__(session_mgr=session_mgr, interval_sec=POLL_INTERVAL_SEC)
        self._seen_keys: set[str] = set()
        self._seen_pids: set[int] = set()
        self._ring: list[dict] = []
        self._pid_names: dict[int, str] = {}
        self._packet_thread = None

    def start(self) -> None:
        super().start()
        if PACKET_CAPTURE_ENABLED:
            self._start_packet_capture()

    def stop(self) -> int:
        if self._packet_thread:
            try:
                self._packet_thread.join(timeout=3)
            except Exception:
                pass
        return super().stop()

    def collect(self) -> list[dict[str, Any]]:
        if not _HAS_PSUTIL:
            return [{"event_type": "netlog_error", "error": "psutil not installed"}]

        events = []
        try:
            conns = psutil.net_connections(kind="all")
        except Exception as exc:
            return [{"event_type": "netlog_error", "error": str(exc)}]

        for conn in conns:
            # Filter loopback
            if IGNORE_LOCAL_LOOPBACK and conn.raddr and conn.raddr.ip.startswith("127."):
                continue
            if conn.status in IGNORE_STATUSES:
                continue

            key = _conn_key(conn)
            pid = conn.pid or 0

            # Resolve process name
            proc_name = self._pid_names.get(pid, "unknown")
            if pid and pid not in self._pid_names:
                try:
                    proc_name = psutil.Process(pid).name()
                    self._pid_names[pid] = proc_name
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc_name = "unknown"
                    self._pid_names[pid] = proc_name

            # Build connection dict
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None
            rport = conn.raddr.port if conn.raddr else None

            is_new = key not in self._seen_keys
            self._seen_keys.add(key)

            # Operator checks
            alerts: list[str] = []
            if is_new and NEW_PROCESS_ALERT and pid not in self._seen_pids:
                alerts.append("NEW_PROCESS_CONNECTION")
                self._seen_pids.add(pid)
            if rport and rport in FOREIGN_PORT_ALERTLIST:
                alerts.append("SUSPICIOUS_PORT")

            ev: dict[str, Any] = {
                "event_type":  "connection",
                "is_new":      is_new,
                "pid":         pid,
                "proc":        proc_name,
                "type":        str(conn.type),
                "status":      conn.status,
                "laddr":       laddr,
                "raddr":       raddr,
                "alerts":      alerts,
            }
            events.append(ev)

            # Ring buffer for /latest API
            self._ring.append(ev)
            if len(self._ring) > MAX_EVENTS_IN_MEMORY:
                self._ring.pop(0)

        # Per-process connection count alert
        if events:
            from collections import Counter
            proc_counts = Counter(e["proc"] for e in events)
            for proc, count in proc_counts.items():
                if count >= HIGH_CONNECTION_COUNT:
                    events.append({
                        "event_type": "process_connection_alert",
                        "proc": proc,
                        "connection_count": count,
                        "alerts": ["HIGH_CONNECTION_COUNT"],
                    })

        return events

    def _start_packet_capture(self) -> None:
        """Optional scapy packet capture in background thread."""
        import threading
        def _capture():
            try:
                from scapy.all import sniff, IP
                def _pkt_handler(pkt):
                    if IP in pkt:
                        ev = {
                            "event_type": "packet",
                            "src": pkt[IP].src,
                            "dst": pkt[IP].dst,
                            "proto": pkt[IP].proto,
                            "len": pkt[IP].len,
                        }
                        self._ring.append(ev)
                        if len(self._ring) > MAX_EVENTS_IN_MEMORY:
                            self._ring.pop(0)
                sniff(iface=PACKET_IFACE, prn=_pkt_handler, store=False,
                      stop_filter=lambda _: not self._running)
            except ImportError:
                logger.warning("scapy not installed — packet capture disabled")
            except Exception as exc:
                logger.error("Packet capture error: %s", exc)
        self._packet_thread = threading.Thread(
            target=_capture, name="netlog-packet-capture", daemon=True
        )
        self._packet_thread.start()

    @property
    def ring(self) -> list[dict]:
        return list(self._ring)
