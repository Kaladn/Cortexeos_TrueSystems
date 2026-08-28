"""
Forge Service — ZMQ REP on Node 1 (port 5001)

Wraps the full dual-write pipeline: GNOME symbolization → SQLite persistence → ForgeMemory.
Also exposes query, stats, and health endpoints.

Actions:
  ingest  — Run full ingest_anchor() pipeline for a RawAnchor
  query   — Query ForgeMemory by symbol_id
  stats   — Return ForgeMemory statistics
  health  — Liveness check
"""

from __future__ import annotations

import logging
import time

import zmq

from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.gnome.gnome_service import GnomeService
from wolf_engine.pipeline import ingest_anchor
from wolf_engine.services.protocol import (
    decode_request,
    dict_to_raw_anchor,
    encode_response,
    forge_stats_to_dict,
    query_result_to_dict,
)
from wolf_engine.sql.sqlite_reader import SQLiteReader
from wolf_engine.sql.sqlite_writer import SQLiteWriter

logger = logging.getLogger(__name__)


class ForgeServiceRunner:
    """Runs the Forge ZMQ REP service."""

    def __init__(
        self,
        db_path: str,
        genome_path: str,
        bind_addr: str = "tcp://*:5001",
        forge_window_size: int = 10000,
    ):
        self.bind_addr = bind_addr
        self._running = False

        # Core components
        self.gnome = GnomeService(genome_path)
        self.sql_writer = SQLiteWriter(db_path)
        self.sql_reader = SQLiteReader(db_path)
        self.forge = ForgeMemory(window_size=forge_window_size)

        # Handlers
        self._handlers = {
            "ingest": self._handle_ingest,
            "query": self._handle_query,
            "stats": self._handle_stats,
            "health": self._handle_health,
        }

    def run(self) -> None:
        """Start the ZMQ REP loop. Blocks until stop() is called."""
        ctx = zmq.Context()
        socket = ctx.socket(zmq.REP)
        socket.bind(self.bind_addr)
        socket.RCVTIMEO = 1000  # 1s poll for shutdown check
        self._running = True
        logger.info("Forge service listening on %s", self.bind_addr)

        try:
            while self._running:
                try:
                    msg = socket.recv()
                except zmq.Again:
                    continue  # Timeout, check _running flag

                try:
                    action, payload = decode_request(msg)
                    handler = self._handlers.get(action)
                    if handler is None:
                        reply = encode_response("error", f"Unknown action: {action}")
                    else:
                        reply = handler(payload)
                except Exception as exc:
                    logger.error("Request handling error: %s", exc)
                    reply = encode_response("error", str(exc))

                socket.send(reply)
        finally:
            socket.close()
            ctx.term()

    def stop(self) -> None:
        """Signal the service to stop."""
        self._running = False

    def close(self) -> None:
        """Clean up resources."""
        self.sql_writer.close()
        self.sql_reader.close()

    # --- Handlers ---

    def _handle_ingest(self, payload: dict) -> bytes:
        raw_anchor = dict_to_raw_anchor(payload)
        ingest_anchor(raw_anchor, self.gnome, self.sql_writer, self.forge)
        return encode_response("ok", {"event_id": raw_anchor.event_id})

    def _handle_query(self, payload: dict) -> bytes:
        symbol_id = payload.get("symbol_id")
        if symbol_id is None:
            return encode_response("error", "Missing symbol_id")
        result = self.forge.query(int(symbol_id))
        if result is None:
            return encode_response("ok", None)
        return encode_response("ok", query_result_to_dict(result))

    def _handle_stats(self, payload: dict) -> bytes:
        stats = self.forge.stats()
        return encode_response("ok", forge_stats_to_dict(stats))

    def _handle_health(self, payload: dict) -> bytes:
        return encode_response("ok", {
            "service": "forge",
            "status": "healthy",
            "timestamp": time.time(),
            "forge_symbols": len(self.forge.symbols),
        })
