"""
Wolf Engine Dashboard — Interactive Command Center.

Serves the dashboard from proper UI files:
  templates/index.html  — HTML structure
  static/css/dashboard.css — Styles
  static/js/dashboard.js   — Client-side logic

Panels:
  1. ANALYZE — text input, Analyze/Ingest buttons, live results
  2. SYMBOL EXPLORER — search by ID, top symbols table
  3. CASCADE TRACER — BFS trace visualization
  4. ACTIVITY LOG — real-time action feed
  5. MONITORING — node health, CPU/RAM, GPU, Forge, verdicts
  6. TOOLS — debug push, session recording, evidence workers, export/reset
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

logger = logging.getLogger(__name__)

# Resolve paths relative to this file
_HERE = os.path.dirname(os.path.abspath(__file__))
_TEMPLATES_DIR = os.path.join(_HERE, "templates")
_STATIC_DIR = os.path.join(_HERE, "static")


def _load_dashboard_html() -> str:
    """Read the dashboard HTML from the template file."""
    html_path = os.path.join(_TEMPLATES_DIR, "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()


def get_dashboard_html() -> str:
    """Public accessor — reads templates/index.html. Used by app.py and tests."""
    return _load_dashboard_html()


# Backward-compat: tests and app.py import DASHBOARD_HTML directly.
# Load once at import time so existing `assert "X" in DASHBOARD_HTML` tests work.
DASHBOARD_HTML = _load_dashboard_html()


# ---------------------------------------------------------------------------
# Flask Dashboard App (standalone, used by tests)
# ---------------------------------------------------------------------------


def create_dashboard_app(
    collector=None,
    verdict_store=None,
) -> Flask:
    """
    Create the Wolf Engine dashboard Flask application.

    Args:
        collector: MetricsCollector instance (provides node metrics)
        verdict_store: VerdictStore instance (provides verdicts)
    """
    app = Flask(
        __name__,
        static_folder=_STATIC_DIR,
        static_url_path="/static",
    )

    @app.route("/dashboard")
    def dashboard():
        html_path = os.path.join(_TEMPLATES_DIR, "index.html")
        with open(html_path, encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/html")

    @app.route("/api/metrics")
    def api_metrics():
        if collector is None:
            return jsonify({"nodes": {}, "summary": {}})

        nodes = collector.get_all_latest()
        summary = collector.summary()

        if verdict_store is not None:
            try:
                counts = verdict_store.count_by_status()
                summary["verdicts_approved"] = counts.get("approved", 0)
                summary["verdicts_adjusted"] = counts.get("adjusted", 0)
                summary["verdicts_quarantined"] = counts.get("quarantined", 0)
                summary["verdicts_penalized"] = counts.get("penalized", 0)
            except Exception:
                pass

        return jsonify({"nodes": nodes, "summary": summary})

    @app.route("/api/metrics/history")
    def api_metrics_history():
        minutes = request.args.get("minutes", 60, type=int)
        if collector is None:
            return jsonify({})
        return jsonify(collector.get_all_history(minutes=minutes))

    @app.route("/api/metrics/node/<node_id>")
    def api_metrics_node(node_id: str):
        if collector is None:
            return jsonify(None), 404
        latest = collector.get_latest(node_id)
        if latest is None:
            return jsonify({"error": "Node not found"}), 404
        return jsonify(latest)

    @app.route("/api/verdicts/recent")
    def api_verdicts_recent():
        limit = request.args.get("limit", 20, type=int)
        if verdict_store is None:
            return jsonify([])
        try:
            return jsonify(verdict_store.get_recent(limit=limit))
        except Exception:
            return jsonify([])

    @app.route("/api/verdicts/counts")
    def api_verdicts_counts():
        if verdict_store is None:
            return jsonify({})
        try:
            return jsonify(verdict_store.count_by_status())
        except Exception:
            return jsonify({})

    @app.route("/api/verdicts/session/<session_id>")
    def api_verdicts_session(session_id: str):
        if verdict_store is None:
            return jsonify([])
        try:
            return jsonify(verdict_store.get_by_session(session_id))
        except Exception:
            return jsonify([])

    @app.route("/api/summary")
    def api_summary():
        if collector is None:
            return jsonify({})
        return jsonify(collector.summary())

    @app.route("/api/stream")
    def api_stream():
        """Server-Sent Events stream for real-time dashboard updates."""
        def generate():
            while True:
                try:
                    if collector is not None:
                        nodes = collector.get_all_latest()
                        summary = collector.summary()
                        if verdict_store is not None:
                            try:
                                counts = verdict_store.count_by_status()
                                summary["verdicts_approved"] = counts.get("approved", 0)
                                summary["verdicts_adjusted"] = counts.get("adjusted", 0)
                                summary["verdicts_quarantined"] = counts.get("quarantined", 0)
                                summary["verdicts_penalized"] = counts.get("penalized", 0)
                            except Exception:
                                pass
                        payload = json.dumps({"nodes": nodes, "summary": summary})
                        yield f"event: metrics\ndata: {payload}\n\n"

                    if verdict_store is not None:
                        try:
                            recent = verdict_store.get_recent(limit=20)
                            yield f"event: verdicts\ndata: {json.dumps(recent)}\n\n"
                        except Exception:
                            pass

                    time.sleep(5)
                except GeneratorExit:
                    break
                except Exception as exc:
                    logger.error("SSE stream error: %s", exc)
                    time.sleep(5)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    return app
