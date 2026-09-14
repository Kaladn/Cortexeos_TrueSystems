"""
Perception Service — ZMQ REP on Node 2 (port 5004)

Converts raw text input into RawAnchors with 6-1-6 context windows.
This is the entry point for all data — it tokenizes, windows, and emits
anchors ready for GNOME symbolization on Node 1.

Actions:
  perceive  — Tokenize text → list of RawAnchors with 6-1-6 context
  health    — Liveness check
"""

from __future__ import annotations

import logging
import re
import time
import uuid

from wolf_engine.config import CONTEXT_WINDOW_SIZE
from wolf_engine.contracts import RawAnchor
from wolf_engine.services.protocol import (
    decode_request,
    encode_response,
    raw_anchor_to_dict,
)

logger = logging.getLogger(__name__)


def tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens (words, preserving alphanumerics)."""
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def build_anchors(
    tokens: list[str],
    session_id: str,
    pulse_id: int = 0,
    window_size: int = CONTEXT_WINDOW_SIZE,
) -> list[RawAnchor]:
    """Build RawAnchors with 6-1-6 context windows from a token list."""
    anchors = []
    for i, token in enumerate(tokens):
        context_before = tokens[max(0, i - window_size):i]
        context_after = tokens[i + 1:i + 1 + window_size]
        anchor = RawAnchor(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            pulse_id=pulse_id,
            token=token,
            context_before=context_before,
            context_after=context_after,
            position=i,
        )
        anchors.append(anchor)
    return anchors


class PerceptionServiceRunner:
    """Runs the Perception ZMQ REP service."""

    def __init__(self, bind_addr: str = "tcp://*:5004"):
        self.bind_addr = bind_addr
        self._running = False
        self._handlers = {
            "perceive": self._handle_perceive,
            "health": self._handle_health,
        }

    def run(self) -> None:
        """Start the ZMQ REP loop. Blocks until stop() is called."""
        import zmq
        ctx = zmq.Context()
        socket = ctx.socket(zmq.REP)
        socket.bind(self.bind_addr)
        socket.RCVTIMEO = 1000
        self._running = True
        logger.info("Perception service listening on %s", self.bind_addr)

        try:
            while self._running:
                try:
                    msg = socket.recv()
                except zmq.Again:
                    continue

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
        self._running = False

    # --- Handlers ---

    def _handle_perceive(self, payload: dict) -> bytes:
        text = payload.get("text", "")
        session_id = payload.get("session_id", str(uuid.uuid4()))
        pulse_id = payload.get("pulse_id", 0)

        if not text:
            return encode_response("error", "Empty text")

        tokens = tokenize(text)
        anchors = build_anchors(tokens, session_id, pulse_id)
        return encode_response("ok", {
            "anchors": [raw_anchor_to_dict(a) for a in anchors],
            "token_count": len(tokens),
        })

    def _handle_health(self, payload: dict) -> bytes:
        return encode_response("ok", {
            "service": "perception",
            "status": "healthy",
            "timestamp": time.time(),
        })
