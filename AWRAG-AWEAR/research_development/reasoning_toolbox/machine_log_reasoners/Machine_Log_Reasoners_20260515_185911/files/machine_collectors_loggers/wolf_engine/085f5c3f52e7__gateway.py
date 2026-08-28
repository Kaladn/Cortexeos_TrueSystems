"""
API Gateway — Flask HTTP on Node 3 (port 5000)

External HTTP API that proxies to Forge (Node 1) and Perception (Node 2)
over ZMQ REQ sockets. Handles ZMQ timeout + reconnect to prevent
"stuck REQ" deadlock.

Endpoints:
  POST /think         — Perceive text → ingest all anchors → return stats
  GET  /query/<id>    — Query ForgeMemory by symbol_id
  GET  /stats         — Forge statistics
  GET  /health        — All-node health check
"""

from __future__ import annotations

import json
import logging
import time

import zmq
from flask import Flask, Response, jsonify, request

from wolf_engine.services.protocol import decode_response, encode_request

logger = logging.getLogger(__name__)

_ZMQ_TIMEOUT_MS = 5000  # 5s timeout on REQ sockets


def _zmq_request(addr: str, action: str, payload: dict | None = None) -> tuple[str, any]:
    """
    Send a ZMQ REQ and wait for REP with timeout.

    On timeout: returns ("error", "Service timeout").
    On any error: returns ("error", str(exc)).
    """
    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.REQ)
    sock.RCVTIMEO = _ZMQ_TIMEOUT_MS
    sock.SNDTIMEO = _ZMQ_TIMEOUT_MS
    sock.setsockopt(zmq.LINGER, 0)
    try:
        sock.connect(addr)
        sock.send(encode_request(action, payload))
        reply = sock.recv()
        return decode_response(reply)
    except zmq.Again:
        return "error", "Service timeout"
    except zmq.ZMQError as exc:
        return "error", f"ZMQ error: {exc}"
    finally:
        sock.close()


def create_app(
    forge_addr: str = "tcp://localhost:5001",
    perception_addr: str = "tcp://localhost:5004",
) -> Flask:
    """Create the Flask gateway app wired to Forge and Perception services."""
    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health():
        results = {}
        for name, addr in [("forge", forge_addr), ("perception", perception_addr)]:
            status, data = _zmq_request(addr, "health")
            results[name] = data if status == "ok" else {"status": "down", "error": data}
        results["gateway"] = {"status": "healthy", "timestamp": time.time()}
        all_healthy = all(
            isinstance(v, dict) and v.get("status") == "healthy"
            for v in results.values()
        )
        return jsonify(results), 200 if all_healthy else 503

    @app.route("/think", methods=["POST"])
    def think():
        body = request.get_json(silent=True) or {}
        text = body.get("text", "")
        session_id = body.get("session_id", "")
        if not text:
            return jsonify({"error": "Missing 'text' field"}), 400

        # Step 1: Perceive
        status, data = _zmq_request(perception_addr, "perceive", {
            "text": text,
            "session_id": session_id,
        })
        if status != "ok":
            return jsonify({"error": f"Perception failed: {data}"}), 502

        anchors = data.get("anchors", [])
        ingested = 0

        # Step 2: Ingest each anchor into Forge
        for anchor_dict in anchors:
            s, d = _zmq_request(forge_addr, "ingest", anchor_dict)
            if s == "ok":
                ingested += 1
            else:
                logger.warning("Ingest failed for anchor: %s", d)

        return jsonify({
            "status": "ok",
            "tokens_perceived": data.get("token_count", 0),
            "anchors_ingested": ingested,
        })

    @app.route("/query/<int:symbol_id>", methods=["GET"])
    def query(symbol_id: int):
        status, data = _zmq_request(forge_addr, "query", {"symbol_id": symbol_id})
        if status != "ok":
            return jsonify({"error": data}), 502
        if data is None:
            return jsonify({"error": "Symbol not found"}), 404
        return jsonify(data)

    @app.route("/stats", methods=["GET"])
    def stats():
        status, data = _zmq_request(forge_addr, "stats")
        if status != "ok":
            return jsonify({"error": data}), 502
        return jsonify(data)

    return app
