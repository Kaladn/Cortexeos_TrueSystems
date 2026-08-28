"""
Wolf Engine — Command Center (Dashboard).

Runs the full engine IN-PROCESS: Forge, GNOME, Reasoning, Archon.
No ZMQ required. Type text, get verdicts, explore symbols, trace cascades.

WolfEngine class lives in wolf_engine.core.engine — imported here for backward compat.

Run:
    python -m wolf_engine.dashboard.app [--port 5000]
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time

from flask import Flask, Response, jsonify, request, stream_with_context

from wolf_engine.core.engine import WolfEngine  # noqa: F401 — re-export for tests
from wolf_engine.dashboard.metrics_collector import MetricsCollector
from wolf_engine.dashboard.metrics_exporter import MetricsExporter
from wolf_engine.dashboard.web import _STATIC_DIR, _TEMPLATES_DIR, get_dashboard_html

logger = logging.getLogger(__name__)


def create_app(engine: WolfEngine | None = None) -> Flask:
    """Create the Wolf Engine command center Flask app."""
    if engine is None:
        engine = WolfEngine()

    # Local metrics: self-feeding exporter -> collector
    collector = MetricsCollector(os.path.join(engine._db_dir, "metrics.db"))
    exporter = MetricsExporter(node_id="local")
    exporter.set_forge_stats_provider(engine.get_forge_stats)
    exporter.set_verdict_counts_provider(engine.verdict_store.count_by_status)

    # Collect metrics immediately so dashboard has data on first load
    try:
        m = exporter.collect()
        collector.ingest(m.to_dict())
    except Exception:
        pass

    # Seed engine with sample data so dashboard isn't empty
    try:
        engine.perceive_and_ingest(
            "Wolf Engine initialized and ready for analysis",
            session_id="startup",
        )
        engine.analyze(session_id="startup", text="System self-test completed successfully")
        engine.debug_push()
        logger.info("Dashboard seeded with startup data")
    except Exception as exc:
        logger.warning("Startup seed failed (non-fatal): %s", exc)

    def _metrics_loop():
        while True:
            time.sleep(5)
            try:
                m = exporter.collect()
                collector.ingest(m.to_dict())
            except Exception:
                pass

    threading.Thread(target=_metrics_loop, daemon=True, name="metrics-feed").start()

    app = Flask(
        __name__,
        static_folder=_STATIC_DIR,
        static_url_path="/static",
    )

    _FAVICON_SVG = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
        b'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        b'<stop offset="0%" stop-color="#06b6d4"/>'
        b'<stop offset="100%" stop-color="#8b5cf6"/>'
        b'</linearGradient></defs>'
        b'<rect width="16" height="16" rx="3" fill="#0a0e17"/>'
        b'<text x="8" y="12.5" text-anchor="middle" '
        b'font-family="Arial,sans-serif" font-weight="800" '
        b'font-size="12" fill="url(#g)">W</text></svg>'
    )

    @app.route("/favicon.ico")
    def favicon():
        return Response(_FAVICON_SVG, mimetype="image/svg+xml")

    @app.route("/")
    def index():
        return Response(get_dashboard_html(), mimetype="text/html")

    @app.route("/dashboard")
    def dashboard():
        return Response(get_dashboard_html(), mimetype="text/html")

    # === CORE ACTIONS ===

    @app.route("/api/ingest", methods=["POST"])
    def api_ingest():
        body = request.get_json(silent=True) or {}
        text = body.get("text", "")
        session_id = body.get("session_id", "")
        if not text:
            return jsonify({"error": "Missing 'text' field"}), 400
        try:
            result = engine.perceive_and_ingest(text, session_id)
            exporter.record_request(ok=True)
            return jsonify(result)
        except Exception as exc:
            exporter.record_request(ok=False)
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/analyze", methods=["POST"])
    def api_analyze():
        body = request.get_json(silent=True) or {}
        text = body.get("text", "")
        session_id = body.get("session_id", "")
        try:
            result = engine.analyze(session_id=session_id, text=text)
            exporter.record_request(ok=True)
            return jsonify(result)
        except Exception as exc:
            exporter.record_request(ok=False)
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/query/<int:symbol_id>")
    def api_query(symbol_id: int):
        result = engine.query_symbol(symbol_id)
        if result is None:
            return jsonify({"error": "Symbol not found"}), 404
        return jsonify(result)

    @app.route("/api/cascade", methods=["POST"])
    def api_cascade():
        body = request.get_json(silent=True) or {}
        symbol_id = body.get("symbol_id")
        if symbol_id is None:
            return jsonify({"error": "Missing symbol_id"}), 400
        direction = body.get("direction", "both")
        max_depth = body.get("max_depth", 5)
        try:
            result = engine.trace_cascade(int(symbol_id), direction, max_depth)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/symbols/top")
    def api_top_symbols():
        limit = request.args.get("limit", 20, type=int)
        return jsonify(engine.get_top_symbols(limit))

    # === MONITORING ===

    @app.route("/api/snapshot")
    def api_snapshot():
        return jsonify(engine.get_system_snapshot())

    @app.route("/api/metrics")
    def api_metrics():
        nodes = collector.get_all_latest()
        summary = collector.summary()
        try:
            counts = engine.verdict_store.count_by_status()
            summary["verdicts_approved"] = counts.get("approved", 0)
            summary["verdicts_adjusted"] = counts.get("adjusted", 0)
            summary["verdicts_quarantined"] = counts.get("quarantined", 0)
            summary["verdicts_penalized"] = counts.get("penalized", 0)
        except Exception:
            pass
        summary["forge_symbols"] = engine.forge.stats().total_symbols
        summary["forge_resonance"] = round(engine.forge.stats().avg_resonance, 4)
        summary["total_ingested"] = engine.total_ingested
        summary["total_analyses"] = engine.total_analyses
        return jsonify({"nodes": nodes, "summary": summary})

    @app.route("/api/verdicts/recent")
    def api_verdicts_recent():
        limit = request.args.get("limit", 20, type=int)
        try:
            return jsonify(engine.verdict_store.get_recent(limit=limit))
        except Exception:
            return jsonify([])

    @app.route("/api/verdicts/counts")
    def api_verdicts_counts():
        try:
            return jsonify(engine.verdict_store.count_by_status())
        except Exception:
            return jsonify({})

    @app.route("/api/verdicts/session/<session_id>")
    def api_verdicts_session(session_id: str):
        try:
            return jsonify(engine.verdict_store.get_by_session(session_id))
        except Exception:
            return jsonify([])

    @app.route("/api/sessions")
    def api_sessions():
        try:
            recent = engine.verdict_store.get_recent(limit=200)
            sessions = {}
            for v in recent:
                sid = v.get("session_id", "")
                if sid and sid not in sessions:
                    sessions[sid] = {
                        "session_id": sid,
                        "last_verdict": v.get("timestamp", 0),
                        "last_status": v.get("status", ""),
                    }
            return jsonify(sorted(
                sessions.values(), key=lambda s: s["last_verdict"], reverse=True
            ))
        except Exception:
            return jsonify([])

    # === ROUND 1: DEBUG / SELF-TEST ===

    @app.route("/api/debug/push", methods=["POST"])
    def api_debug_push():
        try:
            result = engine.debug_push()
            exporter.record_request(ok=True)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # === ROUND 2: SESSION RECORDING ===

    @app.route("/api/session/start", methods=["POST"])
    def api_session_start():
        body = request.get_json(silent=True) or {}
        label = body.get("label", "")
        try:
            result = engine.start_recording(label=label)
            if "error" in result:
                return jsonify(result), 409
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/session/stop", methods=["POST"])
    def api_session_stop():
        try:
            result = engine.stop_recording()
            if "error" in result:
                return jsonify(result), 404
            return jsonify(result)
        except Exception:
            return jsonify([])

    @app.route("/api/session/status")
    def api_session_status():
        return jsonify(engine.get_recording_status())

    # === ROUND 3: EVIDENCE WORKERS ===

    @app.route("/api/evidence/start", methods=["POST"])
    def api_evidence_start():
        body = request.get_json(silent=True) or {}
        workers = body.get("workers", None)
        try:
            result = engine.start_evidence_workers(workers)
            if "error" in result:
                return jsonify(result), 400
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/evidence/stop", methods=["POST"])
    def api_evidence_stop():
        try:
            result = engine.stop_evidence_workers()
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/evidence/status")
    def api_evidence_status():
        return jsonify(engine.get_evidence_status())

    # === ROUND 4: EXPORT + RESET ===

    @app.route("/api/export")
    def api_export():
        what = request.args.get("what", "verdicts")
        try:
            data = engine.export_data(what)
            if isinstance(data, dict) and "error" in data:
                return jsonify(data), 400
            return jsonify(data)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/reset", methods=["POST"])
    def api_reset():
        try:
            result = engine.reset_state()
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/health")
    def health():
        stats = engine.forge.stats()
        return jsonify({
            "status": "healthy",
            "engine": "running",
            "forge_symbols": stats.total_symbols,
            "uptime_sec": round(time.time() - engine._start_time, 1),
        })

    # === SSE STREAM ===

    @app.route("/api/stream")
    def api_stream():
        def generate():
            while True:
                try:
                    nodes = collector.get_all_latest()
                    summary = collector.summary()
                    try:
                        counts = engine.verdict_store.count_by_status()
                        summary["verdicts_approved"] = counts.get("approved", 0)
                        summary["verdicts_adjusted"] = counts.get("adjusted", 0)
                        summary["verdicts_quarantined"] = counts.get("quarantined", 0)
                        summary["verdicts_penalized"] = counts.get("penalized", 0)
                    except Exception:
                        pass
                    summary["forge_symbols"] = engine.forge.stats().total_symbols
                    summary["forge_resonance"] = round(
                        engine.forge.stats().avg_resonance, 4
                    )
                    summary["total_ingested"] = engine.total_ingested
                    summary["total_analyses"] = engine.total_analyses

                    yield f"event: metrics\ndata: {json.dumps({'nodes': nodes, 'summary': summary})}\n\n"

                    try:
                        recent = engine.verdict_store.get_recent(limit=20)
                        yield f"event: verdicts\ndata: {json.dumps(recent)}\n\n"
                    except Exception:
                        pass

                    snapshot = engine.get_system_snapshot()
                    yield f"event: activity\ndata: {json.dumps(snapshot)}\n\n"

                    time.sleep(3)
                except GeneratorExit:
                    break
                except Exception as exc:
                    logger.error("SSE error: %s", exc)
                    time.sleep(3)

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


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Wolf Engine Command Center")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--db-dir", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    engine = WolfEngine(db_dir=args.db_dir)
    logger.info(
        "Wolf Engine initialized. Open http://localhost:%d", args.port
    )

    app = create_app(engine)
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
